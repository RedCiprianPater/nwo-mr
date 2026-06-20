"""
NWO MR GPU Pod — FastAPI wrapper

Exposes a small REST API on port 8000 that the Cloudflare Worker
(`nwo-blaster.ciprianpater.workers.dev`) proxies to.

Endpoints
─────────
POST /api/4dgs                  → start a 4DGS reconstruction job
GET  /api/4dgs/status?job_id=…  → poll a 4DGS job
POST /api/train                 → start a ViserDex training job
GET  /api/train/status?job_id=… → poll a training job
GET  /files/{job_id}/{name}     → serve outputs (splat4d, splat, policy.zip)
GET  /health                    → status + GPU info + free disk

All endpoints (except /health) require:
  Authorization: Bearer <NWO_MR_API_KEY>

Job lifecycle
─────────────
1. Worker POSTs /api/4dgs with { video_url, agent_address, ... }
2. Wrapper validates, creates a job_id, persists job-state.json to disk,
   spawns an asyncio task that downloads + processes + writes outputs
3. Worker polls /api/4dgs/status?job_id=... until status == "completed"
4. (Optional) Wrapper POSTs WORKER_CALLBACK_URL when done so the worker
   can mark mr_jobs.completed_at in Supabase without polling

Pipeline integration is intentionally modular — the actual model-specific
training command lives in `run_4dgs_pipeline()` and `run_viserdex_pipeline()`
at the bottom of this file. Replace the shell commands with your tested
LichtFeld / Instant4D / 4D-Rotor / LeRobot CLI invocations.
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

if not API_KEY:
    print("⚠ WARNING: NWO_MR_API_KEY not set — pod is unauthenticated!")

# ── CUDA / GPU detection at startup ─────────────────────────────────
# Real 4DGS (Instant4D / 4D-Rotor / LichtFeld) and ViserDex training
# require CUDA. We detect that once at boot and expose it in /health so
# callers can see whether to expect real output or placeholder.

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
    return False, "none (CPU-only pod)", 0.0

CUDA_AVAILABLE, GPU_NAME, VRAM_GB = detect_gpu()
print(f"🖥  GPU detection: cuda={CUDA_AVAILABLE} · {GPU_NAME} · {VRAM_GB} GB VRAM")

# ── FastAPI app ────────────────────────────────────────────────────

app = FastAPI(title="NWO MR GPU Pod Wrapper", version="2.0.0")
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
    # CUDA_AVAILABLE / GPU_NAME / VRAM_GB are detected once at module load.
    # mode tells callers what to expect from /api/4dgs and /api/train:
    #   "ready-gpu"        : CUDA pod + real CLI wired → real model output
    #   "placeholder-gpu"  : CUDA pod, real CLI not yet wired → placeholder
    #   "placeholder-cpu"  : CPU pod → placeholder only, no real model can run here
    if CUDA_AVAILABLE:
        mode = "placeholder-gpu"   # flip to "ready-gpu" once real CLI is wired in
    else:
        mode = "placeholder-cpu"
    return {
        "ok": True,
        "service": "nwo-mr-gpu-wrapper",
        "version": "2.1.0",
        "lichtfeld_variant": LICHTFELD_VARIANT,
        "mode": mode,
        "cuda_available": CUDA_AVAILABLE,
        "gpu_name": GPU_NAME,
        "vram_gb": VRAM_GB,
        "real_4dgs_possible": CUDA_AVAILABLE,  # CUDA-only rasterizer kernels
        "real_training_possible": CUDA_AVAILABLE,  # PyTorch CPU impractically slow
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
        "eta_minutes": 15 if req.quality == "fast" else 45,
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


# ── ViserDex training endpoints ────────────────────────────────────

class TrainRequest(BaseModel):
    dataset_url: str
    agent_address: str = Field(pattern=r"^0x[0-9a-fA-F]{40}$")
    policy_type: str = "diffusion"  # diffusion | pi0 | act
    epochs: int = 50
    push_to_hub_repo: Optional[str] = None  # e.g. "ciprianpater/nwo-policy-abc"

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


# ── Pipelines ──────────────────────────────────────────────────────
# These are the only functions you'll need to edit when wiring real
# LichtFeld / Instant4D / LeRobot CLI commands. Everything above is generic.

async def run_4dgs_pipeline(job_id: str):
    """
    Run the 4DGS reconstruction pipeline.

    Flow:
      1. Download video_url → /workspace/inputs/<job_id>.mp4
      2. Validate duration ≤ MAX_VIDEO_SECONDS (ffprobe)
      3. Run the variant-specific training command
      4. Write outputs to /workspace/outputs/<job_id>/
      5. Mark job completed + emit callback

    Variants (set LICHTFELD_VARIANT env var):
      - instant4d: ~15 min on L40S, casual single-camera capture
      - 4d-rotor:  ~45 min, higher fidelity, longer clips
      - static3dgs: LichtFeld stock 3DGS, no time dimension
    """
    job = load_job(job_id)
    if not job:
        return
    try:
        # Step 1: Download video
        video_url = job["input"]["video_url"]
        video_path = INPUT_DIR / f"{job_id}.mp4"
        job["status"] = "downloading"
        save_job(job)
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.get(video_url, follow_redirects=True)
            r.raise_for_status()
            video_path.write_bytes(r.content)

        # Step 2: Validate duration
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                capture_output=True, text=True, timeout=30,
            )
            duration_s = float(out.stdout.strip() or 0)
            if duration_s > MAX_VIDEO_SECONDS:
                raise ValueError(f"video duration {duration_s:.1f}s exceeds max {MAX_VIDEO_SECONDS}s")
            job["video_duration_s"] = round(duration_s, 1)
        except Exception as e:
            raise ValueError(f"ffprobe failed: {e}")

        # Step 3: Run variant
        out_dir = OUTPUT_DIR / job_id
        out_dir.mkdir(exist_ok=True)
        job["status"] = "training"
        job["started_training_at"] = time.time()
        save_job(job)

        # ════════════════════════════════════════════════════════════
        # TODO: Replace this block with the real CLI command for your variant.
        # ════════════════════════════════════════════════════════════
        # Example for Instant4D (verify exact CLI syntax against the repo):
        #   cmd = [
        #       "python", "/workspace/models/Instant4D/train.py",
        #       "--video", str(video_path),
        #       "--output", str(out_dir),
        #       "--max-iterations", "30000",
        #   ]
        #
        # Example for 4D-Rotor:
        #   cmd = [
        #       "python", "/workspace/models/4D-Rotor-GS/train.py",
        #       "--source", str(video_path),
        #       "--model-path", str(out_dir),
        #   ]
        #
        # Example for LichtFeld Studio (static 3DGS):
        #   cmd = [
        #       "/workspace/models/LichtFeld/build/lichtfeld_train",
        #       "--input", str(video_path), "--output", str(out_dir),
        #   ]
        # ════════════════════════════════════════════════════════════
        #
        # For first deployment, this is a placeholder that copies the video
        # and writes a fake splat4d so the end-to-end flow works:
        placeholder_splat = out_dir / "scene.splat4d"
        placeholder_splat.write_bytes(b"NWO_MR_PLACEHOLDER_4DGS\n" + video_path.read_bytes()[:1024])
        preview_path = out_dir / "preview.jpg"
        # Extract a thumbnail frame with ffmpeg
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-vframes", "1", "-q:v", "2", str(preview_path)],
            capture_output=True, timeout=30,
        )

        # Step 4: Record outputs
        job["status"] = "completed"
        job["completed_at"] = time.time()
        # mode tells the caller exactly what they got:
        #   "placeholder-cpu" — pod has no GPU; this output is fake by necessity
        #   "placeholder-gpu" — pod has GPU but real CLI isn't wired yet
        #   "ready-gpu"       — real Instant4D/4D-Rotor output (flip when wired)
        mode = "placeholder-cpu" if not CUDA_AVAILABLE else "placeholder-gpu"
        placeholder_reason = (
            "Pod has no GPU. Real 4DGS requires CUDA — every open-source 4DGS "
            "pipeline (Instant4D, 4D-Rotor, LichtFeld) uses CUDA-only rasterizer "
            "kernels with no CPU fallback. The asset URL is a placeholder."
            if not CUDA_AVAILABLE else
            "Real Instant4D/4D-Rotor CLI is not yet wired into wrapper.py. "
            "Pod has GPU available; flip to real model once wired."
        )
        job["results"] = {
            "splat4d_url": file_url(job_id, "scene.splat4d"),
            "preview_url": file_url(job_id, "preview.jpg") if preview_path.exists() else None,
            "viewer_url": None,  # filled in when you wire LichtFeld's web viewer
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
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
        job["completed_at"] = time.time()
        save_job(job)

    # Optional callback to worker
    if WORKER_CALLBACK_URL:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(WORKER_CALLBACK_URL, json={"job_id": job_id, "kind": "4dgs", "status": job["status"]})
        except Exception:
            pass


async def run_viserdex_pipeline(job_id: str):
    """
    Run a ViserDex / LeRobot policy training.

    Flow:
      1. Download dataset_url → /workspace/inputs/<job_id>.tar.gz
      2. Extract, validate dataset is LeRobot format
      3. Run LeRobot training command for policy_type
      4. Push trained checkpoint to HF Hub (if push_to_hub_repo set)
      5. Write outputs to /workspace/outputs/<job_id>/
    """
    job = load_job(job_id)
    if not job:
        return
    try:
        dataset_url = job["input"]["dataset_url"]
        policy_type = job["input"].get("policy_type", "diffusion")
        epochs = int(job["input"].get("epochs", 50))

        # Step 1: Download
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

        # Step 2: Extract
        dataset_dir = INPUT_DIR / job_id
        dataset_dir.mkdir(exist_ok=True)
        subprocess.run(["tar", "-xzf", str(archive_path), "-C", str(dataset_dir)], check=True)

        # Step 3: Train
        out_dir = OUTPUT_DIR / job_id
        out_dir.mkdir(exist_ok=True)
        job["status"] = "training"
        job["started_training_at"] = time.time()
        save_job(job)

        # ════════════════════════════════════════════════════════════
        # TODO: Wire actual LeRobot training command, e.g.:
        #   cmd = [
        #       "python", "-m", "lerobot.scripts.train",
        #       f"policy={policy_type}",
        #       f"dataset.root={dataset_dir}",
        #       f"output_dir={out_dir}",
        #       f"training.epochs={epochs}",
        #   ]
        #   if job["input"].get("push_to_hub_repo"):
        #       cmd += [f"push_to_hub=true", f"hub.repo_id={job['input']['push_to_hub_repo']}"]
        #   subprocess.run(cmd, check=True, env={**os.environ, "HF_TOKEN": HF_TOKEN})
        # ════════════════════════════════════════════════════════════
        #
        # Placeholder for first deployment:
        placeholder_policy = out_dir / "policy.zip"
        placeholder_policy.write_bytes(b"NWO_MR_PLACEHOLDER_POLICY")

        job["status"] = "completed"
        job["completed_at"] = time.time()
        mode = "placeholder-cpu" if not CUDA_AVAILABLE else "placeholder-gpu"
        placeholder_reason = (
            "Pod has no GPU. LeRobot training on CPU is technically possible "
            "but takes weeks instead of hours; not practical. The policy URL is "
            "a placeholder until the pod is moved to a GPU."
            if not CUDA_AVAILABLE else
            "LeRobot CLI not yet wired into wrapper.py. Pod has GPU available; "
            "flip to real training once wired."
        )
        job["results"] = {
            "policy_url": file_url(job_id, "policy.zip"),
            "hf_hub_repo": job["input"].get("push_to_hub_repo"),
            "policy_type": policy_type,
            "epochs": epochs,
            "duration_seconds": round(time.time() - job["started_at"], 1),
            "is_placeholder": True,
            "mode": mode,
            "placeholder_reason": placeholder_reason,
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
