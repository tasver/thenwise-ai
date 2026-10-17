# THENWISE AI — RunPod reusable environment
Builds two Docker images via GitHub Actions. Model weights are kept OUTSIDE the images on RunPod Global Volume mounted at `/workspace-global`.
## Images
- `ghcr.io/tasver/thenwise-video:latest` — ComfyUI LTX 2.5 / MiniMax H3 / YuE2.
- `ghcr.io/tasver/thenwise-audio:latest` — Chatterbox and faster-whisper, separate dependency environment.
## Status
Source code uploaded. **Not a validated production system.** Check Actions status, resolve build failures and GPU smoke-tests first. No GPU should be rented until a usable image is built.
## RunPod
Create a custom template with image above and mount Global Volume `THENWISE_TEST_MODELS` at `/workspace-global`. Expose port 8188 through authenticated access. Container disk ~150 GB.
## Models
Inside video Pod: `python /opt/thenwise/scripts/models.py --group ltx`. MiniMax/YuE require separate license clearance before commercial use.
## Security
Never commit passwords, SSH private keys or HuggingFace access tokens. Avoid exposing the ComfyUI REST API without authentication.
## Caveats
Docker and custom-node compatibility will only be known after Actions and GPU smoke tests. This repo contains original workflows and a separate INT8 adaptation. Some UI workflows need API export before headless automation.
