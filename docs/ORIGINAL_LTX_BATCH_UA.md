# THENWISE — ORIGINAL LTX 2.5 batch workflow on RunPod

**Source:** user's actual ltx_runner.py + workflow_ltx25.json; original files retained unchanged.
No Speed Control, LoRA or external LTX API.

Projects root: /workspace/projects/THENWISE_XXX/
Required files: images/SC001.png (or filenames from JSON); ltx/prompts/ltx_prompts.json
Outputs: videos/SC001_v1.mp4 (according to scene.version).
Workflow: /opt/thenwise/workflows/workflow_ltx25.json
Run: python /opt/thenwise/scripts/ltx_runner_cloud.py THENWISE_XXX --all
Dry run (no GPU jobs): python /opt/thenwise/scripts/ltx_runner_cloud.py THENWISE_XXX --all --dry-run
Select scenes: --range 1-20 or --scenes 1,7,11

**Paid-run guard:** SFTP results destination must be set via environment variables
TW_SFTP_HOST, TW_SFTP_USER, TW_SFTP_RESULTS_DIR, TW_SFTP_KEY_PATH, TW_SFTP_KNOWN_HOSTS.
The SSH host key must already be trusted via a verified known_hosts entry.
Run refuses to spend GPU without a destination unless explicitly given --allow-local-only.
Results are saved to Contabo. Weights are NOT transferred there.

State of queued/generated/uploaded jobs is stored on Global Volume
/workspace-global/production/ltx_state; queued jobs are NEVER duplicated blindly.
Inputs and local outputs reside on Pod disk and must be uploaded/backed up separately.

Docker success is not proof of actual video inference. Complete preflight and test real inference before running hundreds of scenes.
