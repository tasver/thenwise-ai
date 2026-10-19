#!/usr/bin/env python3
"""Read-only production preflight: no models downloaded and no GPU job queued."""
import json
import pathlib
import sys
import urllib.request

BASE = pathlib.Path("/workspace-global/models")
WF = pathlib.Path("/opt/thenwise/workflows")
REQUIRED = {
    "MiniMax H3": WF / "video_minimax_h3_i2v.json",
    "YuE2": WF / "audio_yue2_text2music.json",
}
EXTRA = BASE / "loras/ltx-2.5-22b-lora-slow-motion-control-1.0.safetensors"

def main():
    failures = 0
    try:
        with urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=30) as response:
            registered = json.load(response)
        print("ComfyUI API: READY; node classes:", len(registered))
    except Exception as exc:
        print("ERROR: ComfyUI API unavailable:", exc)
        return 2
    manifest = json.loads(pathlib.Path("/opt/thenwise/config/model_manifest.json").read_text())
    missing_weights = [x["dest"] for x in manifest["files"] if not (BASE / x["dest"]).is_file()]
    if not EXTRA.is_file():
        missing_weights.append("loras/" + EXTRA.name)
    if missing_weights:
        failures += len(missing_weights)
        for x in missing_weights:
            print("MISSING MODEL:", x)
    else:
        print("Weights: all required local model files found")
    for name, path in REQUIRED.items():
        try:
            flow = json.loads(path.read_text())
            needed = sorted({node["class_type"] for node in flow.values()})
            missing = [cls for cls in needed if cls not in registered]
            if missing:
                failures += len(missing)
                print(name, "MISSING NODES:", ", ".join(missing))
            else:
                print(name, "NODES OK:", len(needed))
        except Exception as exc:
            failures += 1
            print(name, "ERROR:", exc)
    print("LTX workflow: saved as UI/subgraph JSON; requires an API-format export for batch generation")
    print("Result:", "PASS (H3/YuE)" if failures == 0 else "ACTION REQUIRED", "issues=", failures)
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
