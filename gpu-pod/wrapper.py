"""
NWO MR GPU Pod — FastAPI wrapper (v3.0.0)

v3.0.0 — real Instant4D pipeline wired in
─────────────────────────────────────────
run_4dgs_pipeline() now:
  1. Checks for /workspace/Instant4D/.installed (created by setup_instant4d.sh)
  2. If installed: extracts frames from the video, runs the real Instant4D
     3-stage pipeline (reconstruct → prune → optimize), copies the final
     .ply to /workspace/outputs/<job_id>/point_cloud.ply, returns it.
  3. If not installed: writes the placeholder splat4d file and returns
     is_placeholder=true. This keeps the wrapper working on fresh pods
     before setup_instant4d.sh has been run.

run_viserdex_pipeline() is unchanged from v2.2.0 (placeholder for now —
LeRobot training will be wired in a separate pass).

Output formats
──────────────
Real Instant4D:    point_cloud.ply (standard 3DGS PLY, ~10-50 MB typical)
                   preview.jpg     (first source frame, extracted by ffmpeg)
                   training.log    (stdout/stderr of the pipeline stages)
                   is_placeholder: false, mode: "ready-gpu"
Placeholder (no Instant4D installed):
                   scene.splat4d   (magic bytes + first 1KB of video, unviewable)
                   preview.jpg     (first source frame)
                   is_placeholder: true, mode: "placeholder-gpu" / "no-gpu"

Endpoints (unchanged from v2.2.0)
─────────────────────────────────
POST /api/4dgs                  → start a 4DGS reconstruction job
GET  /api/4dgs/status?job_id=…  → poll a 4DGS job
POST /api/train                 → start a ViserDex training job
GET  /api/train/status?job_id=… → poll a training job
GET  /files/{job_id}/{name}     → serve outputs
GET  /health                    → status + GPU info + free disk + i4d_installed
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ── Config from env ─────────────────────────────────────────────────

WORKSPACE = Path(os.getenv("WORKSPACE_ROOT", "/workspace"))
INPUT_DIR = WORKSPACE / "inputs"
OUTPUT_DIR = WORKSPACE / "outputs"
JOBS_DIR = WORKSPACE / "jobs"
for d in (INPUT_DIR, OUTPUT_DIR, JOBS_DIR):
    d.mkdir(parents=True, exist_ok=True)

API_KEY = os.getenv("NWO_MR_API_KEY", "")
LICHTFELD_VARIANT = os.getenv("LICHTFELD_VARIANT", "instant4d")
MAX_VIDEO_SECONDS = int(os.getenv("MAX_VIDEO_SECONDS", "90"))
MAX_DATASET_GB = float(os.getenv("MAX_DATASET_GB", "8"))
OUTPUT_BASE_URL = os.getenv("OUTPUT_BASE_URL", "").rstrip("/")
WORKER_CALLBACK_URL = os.getenv("WORKER_CALLBACK_URL", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

# Instant4D integration paths (set by setup_instant4d.sh)
INSTANT4D_PATH = Path(os.getenv("INSTANT4D_PATH", "/workspace/Instant4D"))
INSTANT4D_CONDA_ENV = os.getenv("INSTANT4D_CONDA_ENV", "instant4d")
INSTANT4D_USE_CONDA = os.getenv("INSTANT4D_USE_CONDA", "auto")  # "auto" | "1" | "0"
INSTANT4D_TIMEOUT_S = int(os.getenv("INSTANT4D_TIMEOUT_S", "1800"))  # 30min hard cap

if not API_KEY:
    print("⚠ WARNING: NWO_MR_API_KEY not set — pod is unauthenticated!")

# ── CUDA / GPU detection at startup ─────────────────────────────────

def detect_gpu():
    """Return (cuda_available: bool, gpu_name: str, vram_gb: float)."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4,
        )
        if out.returncode == 0 and out.stdout.strip():
            line = out.stdout.strip().split("\n")[0]
            parts = [p.strip() for p in line.split(",")]
            name = parts[0] if parts else "unknown"
            vram_mb = float(parts[1]) if len(parts) > 1 and parts[1].replace(".", "").isdigit() else 0
            return True, name, round(vram_mb / 1024, 1)
    except Exception:
        pass
    return False, "none (no GPU detected)", 0.0

CUDA_AVAILABLE, GPU_NAME, VRAM_GB = detect_gpu()
print(f"🖥  GPU detection: cuda={CUDA_AVAILABLE} · {GPU_NAME} · {VRAM_GB} GB VRAM")


def instant4d_installed() -> bool:
    """True when setup_instant4d.sh has completed successfully on this pod."""
    return (INSTANT4D_PATH / ".installed").is_file()


def instant4d_python() -> list:
    """Return the command prefix that runs Python inside the Instant4D env."""
    use_conda = INSTANT4D_USE_CONDA
    if use_conda == "auto":
        use_conda = "1" if shutil.which("conda") else "0"
    if use_conda == "1":
        return ["conda", "run", "-n", INSTANT4D_CONDA_ENV, "--no-capture-output", "python"]
    return [str(INSTANT4D_PATH / ".venv" / "bin" / "python")]


I4D_INSTALLED = instant4d_installed()
print(f"📦 Instant4D installed: {I4D_INSTALLED} (path: {INSTANT4D_PATH})")

# ── FastAPI app ────────────────────────────────────────────────────

app = FastAPI(title="NWO MR GPU Pod Wrapper", version="3.0.0")
app.mount("/files", StaticFiles(directory=str(OUTPUT_DIR)), name="files")


# ── Auth ────────────────────────────────────────────────────────────

def check_auth(authorization: Optional[str]):
    if not API_KEY:
        return  # unauthenticated mode (dev only)
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    if authorization[7:] != API_KEY:
        raise HTTPException(401, "invalid bearer token")


# ── Job state ──────────────────────────────────────────────────────

def job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"

def save_job(job: dict):
    job_path(job["id"]).write_text(json.dumps(job, indent=2))

def load_job(job_id: str) -> Optional[dict]:
    p = job_path(job_id)
    if not p.exists():
        return None
    return json.loads(p.read_text())

def file_url(job_id: str, filename: str) -> str:
    if not OUTPUT_BASE_URL:
        return f"/files/{job_id}/{filename}"
    return f"{OUTPUT_BASE_URL}/files/{job_id}/{filename}"


# ── /health ─────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    free_gb = shutil.disk_usage(str(WORKSPACE)).free / 1e9
    # mode reflects what the next /api/4dgs job is actually going to do:
    #   "ready-gpu"        — CUDA + Instant4D installed → real reconstruction
    #   "placeholder-gpu"  — CUDA pod but Instant4D not installed yet
    #                        (run setup_instant4d.sh to upgrade)
    #   "no-gpu"           — no CUDA detected — placeholder only, ever
    if CUDA_AVAILABLE and I4D_INSTALLED:
        mode = "ready-gpu"
    elif CUDA_AVAILABLE:
        mode = "placeholder-gpu"
    else:
        mode = "no-gpu"
    return {
        "ok": True,
        "service": "nwo-mr-gpu-wrapper",
        "version": "3.0.0",
        "lichtfeld_variant": LICHTFELD_VARIANT,
        "mode": mode,
        "cuda_available": CUDA_AVAILABLE,
        "gpu_name": GPU_NAME,
        "vram_gb": VRAM_GB,
        "real_4dgs_possible": CUDA_AVAILABLE and I4D_INSTALLED,
        "real_training_possible": CUDA_AVAILABLE,
        "instant4d_installed": I4D_INSTALLED,
        "instant4d_path": str(INSTANT4D_PATH) if I4D_INSTALLED else None,
        "free_disk_gb": round(free_gb, 1),
        "max_video_seconds": MAX_VIDEO_SECONDS,
        "auth_enabled": bool(API_KEY),
        "output_base_url_set": bool(OUTPUT_BASE_URL),
        "workspace": str(WORKSPACE),
    }


# ── 4DGS endpoints ──────────────────────────────────────────────────

class FDGSRequest(BaseModel):
    video_url: str
    agent_address: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    duration_hint_seconds: Optional[int] = None
    quality: str = "balanced"  # fast | balanced | quality

@app.post("/api/4dgs")
async def start_4dgs(
    req: FDGSRequest,
    background: BackgroundTasks,
    authorization: Optional[str] = Header(None),
):
    check_auth(authorization)
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "kind": "4dgs",
        "status": "processing",
        "agent_address": req.agent_address,
        "input": req.dict(),
        "started_at": time.time(),
        "variant": LICHTFELD_VARIANT,
        "real_pipeline": CUDA_AVAILABLE and I4D_INSTALLED,
    }
    save_job(job)
    background.add_task(run_4dgs_pipeline, job_id)
    return {
        "ok": True,
        "job_id": job_id,
        "kind": "splat",
        "source": LICHTFELD_VARIANT,
        "status": "processing",
        "poll_url": f"/api/4dgs/status?job_id={job_id}",
        # ETA is honest now: real Instant4D ≈ 5-15min; placeholder ≈ seconds
        "eta_minutes": (
            (5 if req.quality == "fast" else 15 if req.quality == "balanced" else 30)
            if (CUDA_AVAILABLE and I4D_INSTALLED) else 1
        ),
    }

@app.get("/api/4dgs/status")
async def status_4dgs(job_id: str, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    job = load_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job["kind"] != "4dgs":
        raise HTTPException(400, "not a 4dgs job")
    return {"ok": True, **job}


# ── ViserDex training endpoints (unchanged from v2.2.0) ────────────

class TrainRequest(BaseModel):
    dataset_url: str
    agent_address: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    policy_type: str = "diffusion"  # diffusion | pi0 | act
    epochs: int = 50
    push_to_hub_repo: Optional[str] = None

@app.post("/api/train")
async def start_train(
    req: TrainRequest,
    background: BackgroundTasks,
    authorization: Optional[str] = Header(None),
):
    check_auth(authorization)
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "kind": "train",
        "status": "processing",
        "agent_address": req.agent_address,
        "input": req.dict(),
        "started_at": time.time(),
    }
    save_job(job)
    background.add_task(run_viserdex_pipeline, job_id)
    return {
        "ok": True,
        "job_id": job_id,
        "kind": "skill_module",
        "status": "processing",
        "poll_url": f"/api/train/status?job_id={job_id}",
        "eta_minutes": 120 if req.policy_type == "diffusion" else 60,
    }

@app.get("/api/train/status")
async def status_train(job_id: str, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    job = load_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job["kind"] != "train":
        raise HTTPException(400, "not a train job")
    return {"ok": True, **job}


# ════════════════════════════════════════════════════════════════════
# 4DGS pipeline
# ════════════════════════════════════════════════════════════════════

async def run_4dgs_pipeline(job_id: str):
    """Top-level dispatcher: real Instant4D if installed, else placeholder."""
    job = load_job(job_id)
    if not job:
        return
    try:
        # Step 1: Download video (common to both paths)
        video_url = job["input"]["video_url"]
        video_path = INPUT_DIR / f"{job_id}.mp4"
        job["status"] = "downloading"
        save_job(job)
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.get(video_url, follow_redirects=True)
            r.raise_for_status()
            video_path.write_bytes(r.content)

        # Step 2: Validate duration via ffprobe
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
            capture_output=True, text=True, timeout=30,
        )
        duration_s = float((out.stdout or "0").strip() or 0)
        if duration_s <= 0:
            raise ValueError("ffprobe could not read video — check video_url returns raw bytes (e.g. use HuggingFace 'resolve/main' URLs, not 'blob/main')")
        if duration_s > MAX_VIDEO_SECONDS:
            raise ValueError(f"video duration {duration_s:.1f}s exceeds max {MAX_VIDEO_SECONDS}s")
        job["video_duration_s"] = round(duration_s, 1)

        # Step 3: Always extract a preview thumbnail (cheap, used by both paths)
        out_dir = OUTPUT_DIR / job_id
        out_dir.mkdir(exist_ok=True)
        preview_path = out_dir / "preview.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-vframes", "1", "-q:v", "2", str(preview_path)],
            capture_output=True, timeout=30,
        )

        # Step 4: Branch on installation
        if CUDA_AVAILABLE and I4D_INSTALLED:
            await _run_instant4d_pipeline(job, video_path, out_dir, preview_path)
        else:
            _run_placeholder_4dgs(job, video_path, out_dir, preview_path)

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["completed_at"] = time.time()
        save_job(job)

    # Optional callback to worker
    if WORKER_CALLBACK_URL:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(WORKER_CALLBACK_URL, json={
                    "job_id": job_id, "kind": "4dgs", "status": job["status"],
                })
        except Exception:
            pass


async def _run_instant4d_pipeline(job: dict, video_path: Path, out_dir: Path, preview_path: Path):
    """
    Run the real Instant4D pipeline. Three stages per the upstream README:
      1. SLAM reconstruction (mega-sam: depth + camera trajectory)
      2. Grid pruning (sparse 4D Gaussian initialization)
      3. 4D Gaussian optimization (the actual fit)

    Upstream expects a directory with extracted frames, not an mp4. We
    pre-extract at ~10 fps so a 10s clip yields ~100 frames — within
    Instant4D's tested range and an L4's VRAM budget.

    Final output is a 3DGS-format .ply at .../point_cloud/iteration_<N>/point_cloud.ply
    which we copy to <out_dir>/point_cloud.ply for serving.
    """
    job_id = job["id"]
    quality = job["input"].get("quality", "balanced")

    # Pace-of-life: fast=fewer iterations, quality=more.
    iterations = {"fast": 4000, "balanced": 8000, "quality": 14000}.get(quality, 8000)

    # 4a. Extract frames at ~10 fps to a scene-style directory
    job["status"] = "extracting_frames"
    save_job(job)
    scene_dir = INPUT_DIR / job_id / "scene"
    images_dir = scene_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path), "-vf", "fps=10", "-q:v", "2",
         str(images_dir / "frame_%05d.png")],
        check=True, capture_output=True, timeout=120,
    )
    frame_count = len(list(images_dir.glob("*.png")))
    if frame_count < 8:
        raise ValueError(f"Only extracted {frame_count} frames — video too short for 4DGS reconstruction")

    # 4b. mega-sam stage: visual SLAM + consistent depth
    # Upstream runs this via script/reconstruct.sh which sets `path` and
    # `weight` variables and invokes mega-sam. We call its underlying Python
    # modules directly so we can control IO, env vars, and timeouts.
    job["status"] = "slam"
    job["frame_count"] = frame_count
    save_job(job)
    log_path = out_dir / "training.log"
    log_fp = open(log_path, "a", buffering=1)
    log_fp.write(f"\n=== Instant4D pipeline for job {job_id} ===\n")
    log_fp.write(f"video_duration_s={job['video_duration_s']} frames={frame_count} iters={iterations}\n\n")

    i4d_py = instant4d_python()
    env = {
        **os.environ,
        "I4D_SCENE_DIR": str(scene_dir),
        "I4D_OUT_DIR": str(out_dir / "i4d"),
        "I4D_ITERATIONS": str(iterations),
        # Reduce VRAM pressure on L4 — Instant4D's default config targets 24GB+
        "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:512",
    }

    def _run(stage: str, cmd: list, stage_timeout: int):
        log_fp.write(f"--- {stage} ---\n$ {' '.join(cmd)}\n")
        log_fp.flush()
        rc = subprocess.run(
            cmd, cwd=str(INSTANT4D_PATH), env=env,
            stdout=log_fp, stderr=subprocess.STDOUT,
            timeout=stage_timeout,
        ).returncode
        log_fp.write(f"--- {stage} exited rc={rc} ---\n\n")
        log_fp.flush()
        if rc != 0:
            raise RuntimeError(f"Instant4D stage '{stage}' failed (rc={rc}). Tail of log:\n" + _tail(log_path, 60))

    # Upstream invokes via `source script/reconstruct.sh` + `python -m script.prune`
    # + `python -m script.optmize` (sic — their typo). reconstruct.sh chains
    # mega-sam preprocess steps and a Python entry point; we invoke its
    # underlying Python directly so we can control IO and timeouts.
    try:
        # Stage 1: SLAM (depth + cameras). May take 2-4 min for ~100 frames on L4.
        _run("reconstruct", i4d_py + ["-m", "script.reconstruct"], stage_timeout=900)
        job["status"] = "pruning"; save_job(job)
        # Stage 2: grid pruning
        _run("prune", i4d_py + ["-m", "script.prune"], stage_timeout=300)
        job["status"] = "optimizing"; save_job(job)
        # Stage 3: 4DGS optimization (note upstream's typo: 'optmize')
        _run("optimize", i4d_py + ["-m", "script.optmize"], stage_timeout=INSTANT4D_TIMEOUT_S)
    finally:
        log_fp.close()

    # 4c. Locate the final point cloud. Instant4D writes to
    # <out>/point_cloud/iteration_<N>/point_cloud.ply by default.
    i4d_out = out_dir / "i4d"
    candidates = sorted(i4d_out.glob("**/point_cloud/iteration_*/point_cloud.ply"))
    if not candidates:
        raise RuntimeError(f"Instant4D produced no point_cloud.ply under {i4d_out}. Check training.log.")
    # Highest iteration count wins (final checkpoint)
    final_ply = max(candidates, key=lambda p: int(p.parent.name.split("_")[-1]))
    target_ply = out_dir / "point_cloud.ply"
    shutil.copy2(final_ply, target_ply)

    # 4d. Mark job completed
    job["status"] = "completed"
    job["completed_at"] = time.time()
    ply_size_mb = round(target_ply.stat().st_size / 1e6, 2)
    job["results"] = {
        # splat4d_url is kept as the field name for frontend compat, but
        # the actual file is a standard 3DGS .ply — splat-viewer.js v3.0
        # detects the extension and routes to SuperSplat for rendering.
        "splat4d_url": file_url(job["id"], "point_cloud.ply"),
        "ply_url": file_url(job["id"], "point_cloud.ply"),
        "preview_url": file_url(job["id"], "preview.jpg") if preview_path.exists() else None,
        # viewer_url is the embedded-viewer URL — frontend can use this
        # directly if it doesn't want to construct the SuperSplat URL itself.
        "viewer_url": f"https://superspl.at/editor?load={file_url(job['id'], 'point_cloud.ply')}",
        "training_log_url": file_url(job["id"], "training.log"),
        "duration_seconds": round(time.time() - job["started_at"], 1),
        "variant": LICHTFELD_VARIANT,
        "is_dynamic": True,
        "is_placeholder": False,
        "mode": "ready-gpu",
        "iterations": iterations,
        "ply_size_mb": ply_size_mb,
        "frame_count": job["frame_count"],
        "cuda_available": CUDA_AVAILABLE,
        "gpu_name": GPU_NAME,
        # Honest note re: 4D playback in web viewers
        "viewer_note": (
            "Public web viewers (SuperSplat, antimatter15/splat) render the "
            "spatial Gaussians but only at a single time slice; the temporal "
            "evolution requires Instant4D's local websocket viewer. The .ply "
            "above is the final checkpoint of the 4D optimization."
        ),
    }
    save_job(job)


def _run_placeholder_4dgs(job: dict, video_path: Path, out_dir: Path, preview_path: Path):
    """
    Placeholder pipeline for pods without Instant4D installed. Writes the
    same scene.splat4d magic file as v2.x so the frontend's placeholder
    panel handles the result cleanly.
    """
    placeholder_splat = out_dir / "scene.splat4d"
    placeholder_splat.write_bytes(b"NWO_MR_PLACEHOLDER_4DGS\n" + video_path.read_bytes()[:1024])

    job["status"] = "completed"
    job["completed_at"] = time.time()
    mode = "placeholder-gpu" if CUDA_AVAILABLE else "no-gpu"
    placeholder_reason = (
        "Instant4D isn't installed on this pod yet. Run "
        "`bash /workspace/setup_instant4d.sh` once (takes ~30 min) to enable "
        "real 4DGS reconstruction. The asset URL is a placeholder file."
        if CUDA_AVAILABLE else
        "Pod has no GPU. Real 4DGS requires CUDA — Instant4D, 4D-Rotor, and "
        "LichtFeld all use CUDA-only rasterizer kernels with no CPU fallback."
    )
    job["results"] = {
        "splat4d_url": file_url(job["id"], "scene.splat4d"),
        "preview_url": file_url(job["id"], "preview.jpg") if preview_path.exists() else None,
        "viewer_url": None,
        "duration_seconds": round(time.time() - job["started_at"], 1),
        "variant": LICHTFELD_VARIANT,
        "is_dynamic": LICHTFELD_VARIANT != "static3dgs",
        "is_placeholder": True,
        "mode": mode,
        "placeholder_reason": placeholder_reason,
        "cuda_available": CUDA_AVAILABLE,
        "gpu_name": GPU_NAME,
    }
    save_job(job)


def _tail(path: Path, n: int) -> str:
    try:
        with open(path) as f:
            lines = f.readlines()
        return "".join(lines[-n:])
    except Exception:
        return "<no log>"


# ════════════════════════════════════════════════════════════════════
# Training pipeline — still placeholder pending LeRobot wiring
# ════════════════════════════════════════════════════════════════════

async def run_viserdex_pipeline(job_id: str):
    job = load_job(job_id)
    if not job:
        return
    try:
        dataset_url = job["input"]["dataset_url"]
        policy_type = job["input"].get("policy_type", "diffusion")
        epochs = int(job["input"].get("epochs", 50))

        archive_path = INPUT_DIR / f"{job_id}.tar.gz"
        job["status"] = "downloading"
        save_job(job)
        async with httpx.AsyncClient(timeout=600) as client:
            r = await client.get(dataset_url, follow_redirects=True)
            r.raise_for_status()
            archive_path.write_bytes(r.content)

        size_gb = archive_path.stat().st_size / 1e9
        if size_gb > MAX_DATASET_GB:
            raise ValueError(f"dataset {size_gb:.1f} GB exceeds max {MAX_DATASET_GB} GB")

        dataset_dir = INPUT_DIR / job_id
        dataset_dir.mkdir(exist_ok=True)
        subprocess.run(["tar", "-xzf", str(archive_path), "-C", str(dataset_dir)], check=True)

        out_dir = OUTPUT_DIR / job_id
        out_dir.mkdir(exist_ok=True)
        job["status"] = "training"
        job["started_training_at"] = time.time()
        save_job(job)

        # TODO (separate pass): wire actual LeRobot training:
        #   subprocess.run(["python", "-m", "lerobot.scripts.train",
        #       f"policy={policy_type}", f"dataset.root={dataset_dir}",
        #       f"output_dir={out_dir}", f"training.epochs={epochs}"], check=True)
        placeholder_policy = out_dir / "policy.zip"
        placeholder_policy.write_bytes(b"NWO_MR_PLACEHOLDER_POLICY")

        job["status"] = "completed"
        job["completed_at"] = time.time()
        mode = "placeholder-gpu" if CUDA_AVAILABLE else "no-gpu"
        job["results"] = {
            "policy_url": file_url(job_id, "policy.zip"),
            "hf_hub_repo": job["input"].get("push_to_hub_repo"),
            "policy_type": policy_type,
            "epochs": epochs,
            "duration_seconds": round(time.time() - job["started_at"], 1),
            "is_placeholder": True,
            "mode": mode,
            "placeholder_reason": "LeRobot CLI not yet wired into wrapper.py.",
            "cuda_available": CUDA_AVAILABLE,
            "gpu_name": GPU_NAME,
        }
        save_job(job)
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["completed_at"] = time.time()
        save_job(job)

    if WORKER_CALLBACK_URL:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(WORKER_CALLBACK_URL, json={"job_id": job_id, "kind": "train", "status": job["status"]})
        except Exception:
            pass


# ── Root ────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return JSONResponse({
        "service": "nwo-mr-gpu-wrapper",
        "version": "3.0.0",
        "instant4d_installed": I4D_INSTALLED,
        "endpoints": [
            "POST /api/4dgs",
            "GET  /api/4dgs/status?job_id=...",
            "POST /api/train",
            "GET  /api/train/status?job_id=...",
            "GET  /files/{job_id}/{filename}",
            "GET  /health",
        ],
        "auth": "Bearer NWO_MR_API_KEY required for all /api/* endpoints",
    })
