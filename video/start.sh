#!/bin/bash
set -euo pipefail
test -d /workspace-global/models || { echo 'ERROR: mount weights at /workspace-global/models'; exit 2; }
mkdir -p /workspace/input /workspace/output /workspace/jobs /workspace/cache /workspace/logs
if [ -n "${CONTABO_SSH_KEY_B64:-}" ]; then
  install -d -m 700 /root/.ssh
  printf "%s" "$CONTABO_SSH_KEY_B64" | base64 --decode > /root/.ssh/thenwise_contabo
  chmod 600 /root/.ssh/thenwise_contabo
  unset CONTABO_SSH_KEY_B64
  echo "THENWISE SSH identity prepared"
fi
cat > /opt/ComfyUI/extra_model_paths.yaml <<'YAML'
thenwise:
  base_path: /workspace-global/models
  checkpoints: checkpoints
  diffusion_models: diffusion_models
  text_encoders: text_encoders
  clip: text_encoders
  vae: vae
  loras: loras
  latent_upscale_models: latent_upscale_models
  model_patches: model_patches
  audio_encoders: audio_encoders
YAML
# API workflow stays in /opt/thenwise/workflows: never load it as ComfyUI UI graph.
# Persist complete ComfyUI log across Pod stops when volume permits writes.
if mkdir -p /workspace-global/thenwise_logs 2>/dev/null && touch /workspace-global/thenwise_logs/.writetest 2>/dev/null; then
  LOG=/workspace-global/thenwise_logs/comfy_$(date -u +%Y%m%dT%H%M%SZ).log
else
  LOG=/workspace/logs/comfy_$(date -u +%Y%m%dT%H%M%SZ).log
fi
echo 'THENWISE COMFY LOG:' "$LOG"
cd /opt/ComfyUI
python -u main.py --listen 0.0.0.0 --port 8188 --input-directory /workspace/input --output-directory /workspace/output 2>&1 | tee -a "$LOG"
