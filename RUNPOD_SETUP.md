# RunPod Setup — NWO MR GPU Services (Phase 2)

End-to-end guide to provision **one** RunPod pod that hosts both:

| Service | Endpoint (Worker proxy → Pod) | Output |
|---|---|---|
| 4DGS reconstruction (LichtFeld + 4D research models) | `POST /api/4dgs` | `.splat4d` file + viewer URL |
| ViserDex robot training (LeRobot · PI0/Diffusion) | `POST /api/train` | HF Hub policy ID |

One pod, two services, shared fixed cost. **Bundle them or the math doesn't work** — an A100 pod is ~$1700/month always-on, splitting it across both workloads halves the per-workload cost.

---

## 1 · Decide pod variant

Pick GPU based on your workload mix:

| GPU | RunPod price (community / secure, approx Jun 2026) | Good for |
|---|---|---|
| **RTX 4090 24 GB** | $0.50 / $0.70 per hr | 4DGS on ≤30 s clips, small ViserDex models. Will OOM on long videos or LeRobot >2B params |
| **L40S 48 GB** ⭐ | $1.10 / $1.50 per hr | Recommended starting point. Handles 60 s 4DGS clips + most LeRobot trainings |
| **A100 80 GB** | $2.30 / $3.40 per hr | Handles ≥90 s 4DGS, all ViserDex sizes. Standard research-grade |
| **H100 80 GB** | $4.50 / $5.50 per hr | Only if you're queuing multiple trainings/day and need throughput |

**Recommended for first deploy:** **L40S 48 GB**. ~$800/month always-on if you can't go scale-to-zero yet; can be paused via the RunPod API between jobs (see §6 below).

---

## 2 · Console form — exact values

Navigate to **https://console.runpod.io/templates → New Template**.

### Template name (Required)
```
nwo-mr-gpu-services
```

### Template type
```
Pod
```
*(not Serverless — Serverless cold-starts every job and has stricter time limits than 4DGS training tolerates)*

### Compute type
```
GPU
```

### Container image
Use the official RunPod PyTorch image (CUDA 12.4, includes Python 3.11, PyTorch 2.4, CUDA toolkit, build-essential):

```
runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
```

This is a public Docker Hub image — no auth needed. Don't tick "Private image."

> If you'd rather use the latest tag, `runpod/pytorch:latest` works but may upgrade behind your back. Pinning to the 2.4 cuda12.4 image is what NWO MR was tested against.

### Container image validation
After pasting the image name, click **Validate**. It pulls metadata from Docker Hub. Should return a green check within ~10 seconds. If it fails, your tag is wrong — copy-paste the line above exactly.

### Container disk
```
80 GB
```
*(Temporary scratch. CUDA libs + PyTorch + model weights eat 40–50 GB during training. 80 GB leaves headroom.)*

### Persistent storage
Enable. Mounted to `/workspace`, survives pod stop/start.

```
100 GB
```
*(Holds: cloned NWO MR repo, downloaded video inputs, generated splat outputs, ViserDex datasets, trained policies. 100 GB is enough for ~50–100 4DGS jobs cached.)*

### Persistent storage mount path
```
/workspace
```

### Container start command / Docker Command
**This is the critical field.** RunPod calls it "Docker Command" or "Container Start Command" depending on UI version. Paste this exactly:

```bash
bash -c "if [ ! -d /workspace/nwo-mr ]; then git clone https://github.com/RedCiprianPater/nwo-mr.git /workspace/nwo-mr; else cd /workspace/nwo-mr && git pull; fi && cd /workspace/nwo-mr/gpu-pod && bash startup.sh"
```

What this does:
- On **first boot**: clones the repo to `/workspace/nwo-mr` (persisted)
- On **subsequent boots**: pulls latest changes
- Runs `startup.sh` which installs deps + launches the FastAPI wrapper on port 8000

### Expose HTTP ports
```
8000
```
RunPod exposes this as `https://<pod-id>-8000.proxy.runpod.net`. **This is your `RUNPOD_GPU_URL`.**

### Expose TCP ports
Leave blank unless you want SSH. If you do want SSH for debugging:
```
22
```
Then add your public key to `Settings → SSH Public Keys` and connect via `ssh root@<pod-id>-22.proxy.runpod.net -p <port>`.

### Environment variables

> ⚠ **Use Secrets, not plain env vars, for any key.** Plain env vars are visible in the pod's logs and the RunPod console.

Click **+ Add Secret** for each:

| Name | Value | Why |
|---|---|---|
| `NWO_MR_API_KEY` | Generate a random 32-byte hex string (`openssl rand -hex 32`) | Worker → Pod auth header. **Save this — you'll paste it as a Cloudflare Worker secret too.** |
| `HF_TOKEN` | Your Hugging Face write token | For pushing trained ViserDex policies to HF Hub |
| `WORKER_CALLBACK_URL` | `https://nwo-blaster.ciprianpater.workers.dev/api/internal/job-complete` | Pod calls back to worker when a job finishes (avoids needing the worker to poll the pod) |
| `LICHTFELD_VARIANT` | `instant4d` (recommended) or `4d-rotor` or `static3dgs` | Which research pipeline to use for `/api/4dgs`. See §4 below |

Plain (non-secret) env vars — these can go in the regular env vars section:

| Name | Value |
|---|---|
| `WORKSPACE_ROOT` | `/workspace` |
| `OUTPUT_BASE_URL` | (filled in after pod starts — see §3 step 4) |
| `MAX_VIDEO_SECONDS` | `90` |
| `MAX_DATASET_GB` | `8` |

---

## 3 · Deploy the pod

1. **Save the template** at `console.runpod.io/templates`.
2. Go to `console.runpod.io/pods → Deploy → My Templates → nwo-mr-gpu-services`.
3. Pick the GPU you decided in §1. Pick a region near you (US-East has lowest latency to Cloudflare's Frankfurt/Ashburn edges).
4. Click **Deploy On-Demand** (skip Spot for now — Spot pods can be killed mid-training).
5. Wait ~3 minutes for the pod to boot. Watch the logs panel:
   - `Cloning into '/workspace/nwo-mr'...` — repo clone
   - `Installing requirements...` — pip
   - `Installing LichtFeld + 4D pipeline...` — heavy step (~5–10 min first time, cached afterwards)
   - `Starting NWO MR GPU wrapper on port 8000` — success
6. The pod's URL appears in the **HTTP Service** column — copy it. Looks like:
   ```
   https://abc123def456-8000.proxy.runpod.net
   ```
7. **Test the pod directly** (replace with your URL and your API key):
   ```bash
   curl -H "Authorization: Bearer YOUR_NWO_MR_API_KEY" \
        https://abc123def456-8000.proxy.runpod.net/health
   ```
   Should return:
   ```json
   {"ok": true, "lichtfeld_variant": "instant4d", "gpu": "NVIDIA L40S", "free_disk_gb": 92.4}
   ```
8. **Set `OUTPUT_BASE_URL`** in the pod's env vars to this same URL (the pod serves generated `.splat4d` files at `<OUTPUT_BASE_URL>/files/...`). Restart the pod for it to take effect.

---

## 4 · LichtFeld / 4D pipeline variant

The pod ships with three swappable implementations. Pick via `LICHTFELD_VARIANT`:

| Variant | What it runs | When to use |
|---|---|---|
| `instant4d` ⭐ | [Instant4D](https://arxiv.org/abs/2510.01119) — fastest casual-video → 4DGS. ~15 min on L40S for 30 s clip | Default. Best for iPhone clips |
| `4d-rotor` | [4D-Rotor Gaussian Splatting](https://arxiv.org/abs/2402.03307) — XYZT Gaussian primitives, higher fidelity, slower | When you have ≥60 s clips and want maximum quality |
| `static3dgs` | LichtFeld Studio's stock 3DGS (no time dimension) | Fallback if 4D models fail. Output is mintable as `is_dynamic: false` |

The `startup.sh` clones all three repos but only loads the one specified by `LICHTFELD_VARIANT`. Change the env var + restart pod to switch.

---

## 5 · Wire the Cloudflare Worker

Three new Worker secrets:

```bash
# The pod URL you copied in §3 step 6
wrangler secret put RUNPOD_GPU_URL
# → paste: https://abc123def456-8000.proxy.runpod.net

# The same API key you set on the pod as NWO_MR_API_KEY
wrangler secret put NWO_MR_API_KEY
# → paste: (your 32-byte hex string)

# Optional: keep the old RUNPOD_VISERDEX_URL as alias for back-compat
# (the worker checks RUNPOD_GPU_URL first, falls back to RUNPOD_VISERDEX_URL)
```

Then `wrangler deploy`. The worker's `/api/4dgs`, `/api/4dgs/status`, `/api/train`, and `/api/train/status` will now proxy to your pod.

---

## 6 · Scale-to-zero (optional, ~80 % cost saving)

Running an L40S 24/7 = ~$800/month. Most NWO MR shops will see ≤10 jobs/day, so most of that is idle.

RunPod doesn't have built-in serverless-style scaling for pod templates (Serverless is a separate product with cold-start penalties incompatible with 4DGS), but you can DIY:

1. Get a RunPod API key at `console.runpod.io/user/settings`.
2. Set `RUNPOD_API_KEY` (the RunPod console API key — different from `NWO_MR_API_KEY`!) on your Cloudflare Worker.
3. The worker's `/api/4dgs` handler will:
   - Check if pod is running (`POST https://api.runpod.io/graphql` query)
   - If stopped, start it (~90 s warmup)
   - Queue the job, return `job_id` with `pod_warming: true`
   - Pod processes job
   - Worker schedules a stop after 15 min of pod inactivity

This logic is **already scaffolded in `worker.js`** but disabled by default (set `RUNPOD_SCALE_TO_ZERO=true` to enable). With ~10 jobs/day at ~30 min each, your monthly bill drops from ~$800 → ~$50.

⚠ Spot pods + scale-to-zero is risky — Spot pods can be evicted mid-training. Stick with On-Demand even with scale-to-zero.

---

## 7 · Cost estimates (L40S, on-demand)

| Workload | Time | Cost per asset |
|---|---|---|
| 4DGS (Instant4D, 30 s clip) | ~15 min | ~$0.40 |
| 4DGS (4D-Rotor, 60 s clip) | ~45 min | ~$1.10 |
| ViserDex (LeRobot 200M, small dataset) | ~2 hr | ~$3.00 |
| ViserDex (LeRobot 1B, full dataset) | ~6 hr | ~$9.00 |

Mint each output as an NFT, set royalties at 5–10 %, recoup costs after ~3 sales per asset.

---

## 8 · Verification checklist

After §3 and §5 are done:

```bash
# Worker → Pod health
curl -X POST https://nwo-blaster.ciprianpater.workers.dev/api/4dgs \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://example.com/test.mp4", "agent_address": "0xYourAddress"}'
# Expected: {"ok": true, "job_id": "...", "status": "processing", "poll_url": "/api/4dgs/status?job_id=..."}

# Worker /discovery should now show 4DGS live
curl https://nwo-blaster.ciprianpater.workers.dev/discovery | jq '.capabilities[] | select(.kind=="volumetric-4dgs")'
# Expected: status: "live"

# Worker /health should show lichtfeld configured
curl https://nwo-blaster.ciprianpater.workers.dev/health | jq '.providers.lichtfeld'
# Expected: {configured: true, capability: "4dgs-volumetric", status: "live"}
```

If all three return as expected, Phase 2 is fully live. The HF Space `Create` tab's 4DGS card will auto-flip from **COMING SOON** to **LIVE** on next page load (it reads `/health`).

---

## 9 · Files in this delivery

| File | Where it goes | What it does |
|---|---|---|
| `gpu-pod/startup.sh` | Inside your nwo-mr repo, runs on pod boot | Installs deps, clones research repos, launches wrapper |
| `gpu-pod/wrapper.py` | Same | FastAPI service on port 8000 — `/api/4dgs`, `/api/train`, `/health`, `/files/*` |
| `gpu-pod/requirements.txt` | Same | Python deps (FastAPI, uvicorn, torch, etc.) |
| `worker.js` | Cloudflare Worker source | Replaces `handleFDGSStub` + `handleTrainStub` with real proxy handlers |
| `splat-viewer.js` | HF Space `src/` | Adds `.splat4d` URL detection → renders LichtFeld viewer iframe |

Push the `gpu-pod/` folder to your `nwo-mr` GitHub repo (the pod's `git clone` step pulls from there). Deploy the updated worker. Replace `splat-viewer.js` on the HF Space.
