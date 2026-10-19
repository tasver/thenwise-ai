#!/bin/bash
set -euo pipefail
test -d /workspace-global || { echo 'ERROR: mount Global Volume at /workspace-global'; exit 2; }
mkdir -p /workspace/input /workspace/output /workspace/jobs /workspace/cache
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
YAML
# Use the user's original 50-node I2V workflow only (no Speed Control).
mkdir -p /opt/ComfyUI/user/default/workflows
# The original user's simple 50-node I2V workflow is the primary workflow.
cp /opt/thenwise/workflows/workflow_ltx25.json \
  /opt/ComfyUI/user/default/workflows/THENWISE_ORIGINAL_LTX25_API.json
cd /opt/ComfyUI
exec python main.py --listen 0.0.0.0 --port 8188 --input-directory /workspace/input --output-directory /workspace/output
