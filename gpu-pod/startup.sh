#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# NWO MR GPU Pod — Startup Script
# Runs every time the pod boots. Idempotent.
#
# What this does:
#   1. Installs Python deps for the FastAPI wrapper
#   2. Clones the chosen 4DGS research repo (Instant4D / 4D-Rotor / LichtFeld)
#   3. Clones LeRobot for ViserDex training
#   4. Launches wrapper.py on port 8000 under tmux so it survives detach
#
# Expected env vars (set on RunPod template):
#   NWO_MR_API_KEY        — auth for worker → pod requests
#   LICHTFELD_VARIANT     — instant4d | 4d-rotor | static3dgs
#   WORKSPACE_ROOT        — /workspace (where everything lives)
#   HF_TOKEN              — HuggingFace token for pushing ViserDex policies
#   WORKER_CALLBACK_URL   — Worker URL pod calls when jobs complete
#   OUTPUT_BASE_URL       — This pod's own URL, used to generate file URLs
# ──────────────────────────────────────────────────────────────────────
set -e

WORKSPACE="${WORKSPACE_ROOT:-/workspace}"
VARIANT="${LICHTFELD_VARIANT:-instant4d}"
POD_DIR="${WORKSPACE}/nwo-mr/gpu-pod"

echo "═══════════════════════════════════════════════════"
echo "  NWO MR GPU Pod startup"
echo "  Workspace: ${WORKSPACE}"
echo "  Variant:   ${VARIANT}"
echo "  Pod dir:   ${POD_DIR}"
echo "═══════════════════════════════════════════════════"

# ── 1. System deps (tmux + ffmpeg for video preprocessing) ──
echo "[1/5] Installing system packages..."
apt-get update -qq
apt-get install -y -qq tmux ffmpeg git wget curl

# ── 2. Python deps for wrapper ──
echo "[2/5] Installing wrapper Python deps..."
pip install --upgrade pip -q
pip install -q -r "${POD_DIR}/requirements.txt"

# ── 3. Clone whichever 4DGS variant is configured ──
mkdir -p "${WORKSPACE}/models"
cd "${WORKSPACE}/models"

case "${VARIANT}" in
    instant4d)
        if [ ! -d "Instant4D" ]; then
            echo "[3/5] Cloning Instant4D..."
            git clone https://github.com/ZhentaoLiu/Instant4D.git Instant4D || \
                echo "  ⚠ Instant4D repo unavailable — falling back to research scaffold"
        fi
        ;;
    4d-rotor)
        if [ ! -d "4D-Rotor-GS" ]; then
            echo "[3/5] Cloning 4D-Rotor Gaussian Splatting..."
            git clone https://github.com/weify627/4D-Rotor-Gaussians.git 4D-Rotor-GS || \
                echo "  ⚠ 4D-Rotor repo unavailable — falling back to research scaffold"
        fi
        ;;
    static3dgs)
        if [ ! -d "LichtFeld" ]; then
            echo "[3/5] Cloning LichtFeld Studio..."
            git clone https://github.com/MrNeRF/LichtFeld-Studio.git LichtFeld || \
                echo "  ⚠ LichtFeld repo unavailable — falling back to research scaffold"
        fi
        ;;
    *)
        echo "  ⚠ Unknown LICHTFELD_VARIANT='${VARIANT}'. Skipping clone."
        ;;
esac

# Install variant-specific Python deps if a requirements file exists
for d in Instant4D 4D-Rotor-GS LichtFeld; do
    if [ -f "${WORKSPACE}/models/${d}/requirements.txt" ]; then
        echo "  Installing ${d} deps..."
        pip install -q -r "${WORKSPACE}/models/${d}/requirements.txt" || true
    fi
done

# ── 4. Clone LeRobot for ViserDex training ──
if [ ! -d "${WORKSPACE}/models/lerobot" ]; then
    echo "[4/5] Cloning LeRobot..."
    git clone --depth 1 https://github.com/huggingface/lerobot.git "${WORKSPACE}/models/lerobot" || \
        echo "  ⚠ LeRobot clone failed — ViserDex training will return 503 until fixed"
fi
if [ -d "${WORKSPACE}/models/lerobot" ]; then
    pip install -q -e "${WORKSPACE}/models/lerobot" || true
fi

# ── 5. Launch the FastAPI wrapper on port 8000 under tmux ──
echo "[5/5] Starting NWO MR GPU wrapper on port 8000..."

# Kill any old wrapper instance
tmux kill-session -t nwo-wrapper 2>/dev/null || true

# Make output directories
mkdir -p "${WORKSPACE}/inputs" "${WORKSPACE}/outputs" "${WORKSPACE}/jobs"

# Launch wrapper in a detached tmux session so it persists when this script exits
tmux new-session -d -s nwo-wrapper \
    "cd ${POD_DIR} && \
     export PYTHONUNBUFFERED=1 && \
     uvicorn wrapper:app --host 0.0.0.0 --port 8000 --log-level info \
     2>&1 | tee ${WORKSPACE}/wrapper.log"

# Wait a moment, then verify
sleep 3
if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "═══════════════════════════════════════════════════"
    echo "  ✅ Wrapper is healthy on port 8000"
    echo "  Pod is ready. Worker can now proxy to:"
    echo "  https://<this-pod-id>-8000.proxy.runpod.net"
    echo "═══════════════════════════════════════════════════"
else
    echo "═══════════════════════════════════════════════════"
    echo "  ⚠ Wrapper failed to start. Check ${WORKSPACE}/wrapper.log"
    echo "  tail -50 ${WORKSPACE}/wrapper.log"
    echo "═══════════════════════════════════════════════════"
    tail -30 "${WORKSPACE}/wrapper.log"
    exit 1
fi

# Tail the log so RunPod's pod log view shows ongoing activity
tail -f "${WORKSPACE}/wrapper.log"
