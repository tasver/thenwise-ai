#!/usr/bin/env python3
"""Sequential, restart-aware ComfyUI production queue. Only accepts API-format workflows.

Jobs JSON:
{"jobs":[{"id":"H3_001","workflow":"video_minimax_h3_i2v.json",
"patch":{"114":{"image":"h3_first.png"},"121":{"image":"h3_reference.png"},
"105:104":{"prompt":"Subtle head movement, unchanged scene."}}}]}
"""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request
import uuid

COMFY = os.environ.get("TW_COMFY_API", "http://127.0.0.1:8188").rstrip("/")
WORKFLOW_DIR = Path("/opt/thenwise/workflows")
OUTPUT_DIR = Path("/workspace/output")
STATE_DIR = Path("/workspace-global/production/job_state")
IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,100}$")

def request(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        COMFY + path, data=data,
        headers={"Content-Type": "application/json"} if payload is not None else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")[:3500]
        raise RuntimeError(f"ComfyUI HTTP {error.code}: {message}") from error

def load_workflow(name):
    path = Path(name)
    if not path.is_absolute():
        path = WORKFLOW_DIR / path
    flow = json.loads(path.read_text())
    if not isinstance(flow, dict) or not flow:
        raise ValueError("Empty workflow")
    if any(not isinstance(x, dict) or "class_type" not in x or "inputs" not in x for x in flow.values()):
        raise ValueError(f"{path}: expected API-format workflow, not UI/subgraph workflow")
    return flow

def build_job(job):
    task_id = str(job["id"])
    if not IDENTIFIER.fullmatch(task_id):
        raise ValueError("Job id must contain only A-Z, a-z, 0-9, _ or -")
    flow = copy.deepcopy(load_workflow(job["workflow"]))
    patch = job.get("patch", {})
    if not isinstance(patch, dict):
        raise ValueError("patch must be an object")
    for node_id, fields in patch.items():
        if str(node_id) not in flow:
            raise ValueError(f"{task_id}: nonexistent node {node_id}")
        for key, value in fields.items():
            if key not in flow[str(node_id)]["inputs"]:
                raise ValueError(f"{task_id}: unknown input {node_id}.{key}")
            flow[str(node_id)]["inputs"][key] = value
    prefix = "thenwise/" + task_id
    save_count = 0
    for node in flow.values():
        if node["class_type"] in ("SaveVideo", "SaveAudioAdvanced", "SaveImage"):
            if "filename_prefix" not in node["inputs"]:
                raise ValueError(f"{task_id}: save node lacks filename_prefix")
            node["inputs"]["filename_prefix"] = prefix
            save_count += 1
        if node["class_type"] == "LoadImage":
            filename = node["inputs"].get("image")
            if not isinstance(filename, str) or not (Path("/workspace/input") / filename).is_file():
                raise ValueError(f"{task_id}: upload input image before queue: {filename}")
    if save_count == 0:
        raise ValueError(f"{task_id}: no output SaveVideo/SaveAudioAdvanced/SaveImage node")
    return flow

def outputs_for(task_id):
    target = OUTPUT_DIR / "thenwise"
    if not target.is_dir():
        return []
    files = [p for p in target.rglob("*") if p.is_file() and p.name.startswith(task_id) and p.stat().st_size > 0]
    return sorted(files)

def status_file(task_id):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / (task_id + ".json")

def state(task_id):
    p = status_file(task_id)
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except (ValueError, OSError):
        return {}

def store(task_id, value):
    # Global Volume does not guarantee POSIX atomic rename; avoid os.replace().
    status_file(task_id).write_text(json.dumps(value, indent=2) + "\n")

def wait_for(prompt_id, timeout):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        history = request("/history/" + prompt_id)
        if prompt_id in history:
            record = history[prompt_id]
            summary = record.get("status", {})
            if summary.get("status_str") == "error" or any(
                item.get("type") == "execution_error" for item in summary.get("messages", [])
                if isinstance(item, dict)
            ):
                raise RuntimeError("ComfyUI generation failed: " + json.dumps(summary)[:1800])
            if summary.get("completed") or summary.get("status_str") == "success":
                return record
        time.sleep(4)
    raise TimeoutError(f"ComfyUI prompt {prompt_id} exceeded {timeout}s; check history before retry")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", required=True, help="JSON file containing jobs array")
    parser.add_argument("--validate-only", action="store_true", help="No GPU jobs queued")
    parser.add_argument("--timeout", type=int, default=14400)
    args = parser.parse_args()
    tasks = json.loads(Path(args.jobs).read_text())["jobs"]
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("jobs must be a nonempty array")
    ids = [str(job["id"]) for job in tasks]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate job identifiers are forbidden")
    prepared = [(job, build_job(job)) for job in tasks]
    registered = request("/object_info")
    for job, flow in prepared:
        missing = sorted({n["class_type"] for n in flow.values() if n["class_type"] not in registered})
        if missing:
            raise RuntimeError(f"{job['id']}: unavailable ComfyUI node classes: {missing}")
    print("Validated", len(prepared), "jobs; required nodes available", flush=True)
    if args.validate_only:
        return 0
    if not Path("/workspace-global").is_dir():
        raise RuntimeError("Global Volume must be mounted at /workspace-global")
    for job, flow in prepared:
        task_id = str(job["id"])
        existing = state(task_id)
        if existing.get("status") == "complete" and all(Path(p).is_file() for p in existing.get("outputs", [])):
            print("SKIP completed:", task_id, flush=True)
            continue
        if existing.get("prompt_id") and existing.get("status") == "queued":
            # Do not silently enqueue the same paid GPU generation twice.
            print("STOP: job previously queued. Inspect ComfyUI history:", existing, flush=True)
            return 3
        if existing.get("status") == "generated" and existing.get("outputs"):
            print("SKIP already generated:", task_id, flush=True)
            continue
        response = request("/prompt", {"prompt": flow, "client_id": "thenwise-" + uuid.uuid4().hex})
        prompt_id = response.get("prompt_id")
        if not prompt_id or response.get("node_errors"):
            raise RuntimeError(f"{task_id}: ComfyUI queue rejected workflow: {response}")
        store(task_id, {"status": "queued", "prompt_id": prompt_id, "submitted": time.time()})
        print("QUEUED", task_id, prompt_id, flush=True)
        try:
            wait_for(prompt_id, args.timeout)
            files = outputs_for(task_id)
            if not files:
                raise RuntimeError("History completed but no nonempty output files were found")
            store(task_id, {"status": "complete", "prompt_id": prompt_id, "outputs": list(map(str, files))})
            print("DONE", task_id, "files:", len(files), flush=True)
        except Exception:
            # Remain queued to avoid duplicate paid execution on rerun.
            print("FAILED/INTERRUPTED", task_id, "history:", prompt_id, flush=True)
            raise
    return 0

if __name__ == "__main__":
    sys.exit(main())
