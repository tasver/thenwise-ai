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
# Install the verified local-only LTX 2.5 production graph at container startup.
# The original workflow stays untouched under /opt/thenwise/workflows.
mkdir -p /opt/ComfyUI/user/default/workflows
cp /opt/thenwise/workflows/LTX-2.5_I2V_Speed_Control_INT8_LOCAL_PRODUCTION.json \
  /opt/ComfyUI/user/default/workflows/THENWISE_LTX25_LOCAL_PRODUCTION.json
cd /opt/ComfyUI
exec python main.py --listen 0.0.0.0 --port 8188 --input-directory /workspace/input --output-directory /workspace/output
