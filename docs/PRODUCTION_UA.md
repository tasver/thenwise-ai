# THENWISE production batch queue

RunPod video image includes a preflight checker and sequential queue runner. This is a runner for **ComfyUI API-format JSON only**; nested UI/subgraph JSON needs API-format export first.

- Production preflight: `python /opt/thenwise/scripts/production_check.py`
- Validate a batch without generating: `python /opt/thenwise/scripts/run_jobs.py --jobs /workspace/jobs/batch.json --validate-only`
- Run generation: `python -u /opt/thenwise/scripts/run_jobs.py --jobs /workspace/jobs/batch.json`

Example batch is in `config/jobs.production.example.json`. Images named in the task must first be uploaded to `/workspace/input`; never use dummy image names for paid GPU execution.

Each job uses a stable unique ID and writes output files in `/workspace/output/thenwise/`. Job state lives on the Global Volume under `/workspace-global/production/job_state/`. A previously queued job is NOT blindly rerun after a connection loss; inspect its ComfyUI history to avoid double GPU charges.

**Caution**: Results in `/workspace/output` and source images in `/workspace/input` are on the Pod container disk and must be transferred to Contabo or elsewhere before Pod deletion. The Global Volume only persists models and small job state records. The SFTP production uploader is a separate integration still requiring the destination and credential setup; do not treat output as backed up before confirming successful transfer.

**Important**: The current LTX 2.5 `LTX-2.5_I2V_Speed_Control_INT8_ADAPTED.json` is a ComfyUI UI/subgraph workflow, **not** directly queueable. Export it in ComfyUI API format after resolving all nodes. H3 and YuE2 workflows are API format.
