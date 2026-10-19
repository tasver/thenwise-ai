import argparse
import json
import re
import time
import subprocess
from pathlib import Path

import requests

IMAGE_NODE = "395"
PROMPT_NODE = "398:376"
DURATION_NODE = "398:362"
MEGAPIXELS_NODE = "403"
SAVE_NODE = "75"
PROMPT_ENHANCE_NODE = "398:383"
NEGATIVE_NODE = "398:373"
CREATE_VIDEO_NODE = "398:370"

PROJECTS_ROOT = Path(r"D:\Work\AI\Thenwise")
PIPELINE_ROOT = Path(r"D:\Work\AI\Thenwise\THENWISE_PIPELINE")
WORKFLOW = PIPELINE_ROOT / "ltx" / "workflow_ltx25.json"

NEGATIVE = (
    "subtitles, captions, on-screen text, letters, words, logos, watermarks, "
    "narration, voiceover, dialogue, speaking, singing, music, soundtrack, "
    "morphing, extra limbs, hand deformation, face drift, duplicated people, "
    "floating objects, pc game, console game, video game, cartoon"
)

def args_parse():
    p = argparse.ArgumentParser()

    p.add_argument("project")

    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--range")
    g.add_argument("--scenes")
    g.add_argument("--all", action="store_true")

    p.add_argument("--version", type=int, default=1)
    p.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    p.add_argument("--dry-run", action="store_true")

    # automatic pacing / cooldown
    p.add_argument("--pause-scene", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=5)
    p.add_argument("--pause-batch", type=int, default=60)
    p.add_argument("--gpu-hot", type=int, default=84)
    p.add_argument("--gpu-cool", type=int, default=78)

    return p.parse_args()

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def scene_number(scene_id):
    m = re.search(r"(\d+)", scene_id)
    return int(m.group(1))

def select_scenes(rows, args):
    if args.all:
        return rows

    if args.range:
        a, b = map(int, args.range.split("-", 1))
        return [
            x for x in rows
            if a <= scene_number(x["scene_id"]) <= b
        ]

    wanted = {
        int(x.strip())
        for x in args.scenes.split(",")
        if x.strip()
    }

    return [
        x for x in rows
        if scene_number(x["scene_id"]) in wanted
    ]

def upload_image(url, path):
    with open(path, "rb") as f:
        r = requests.post(
            url.rstrip("/") + "/upload/image",
            files={"image": (path.name, f, "image/png")},
            data={"overwrite": "true"},
            timeout=120
        )
    r.raise_for_status()
    return r.json()

def queue_prompt(url, workflow):
    r = requests.post(
        url.rstrip("/") + "/prompt",
        json={"prompt": workflow},
        timeout=120
    )
    r.raise_for_status()
    return r.json()["prompt_id"]

def wait_history(url, prompt_id):
    while True:
        r = requests.get(
            url.rstrip("/") + f"/history/{prompt_id}",
            timeout=120
        )
        r.raise_for_status()

        data = r.json()

        if data:
            return data

        time.sleep(5)

def find_mp4(obj):
    found = []

    def walk(x):
        if isinstance(x, dict):
            if str(x.get("filename", "")).lower().endswith(".mp4"):
                found.append(x)

            for v in x.values():
                walk(v)

        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)

    return found

def download_video(url, history, target):
    files = find_mp4(history)

    if not files:
        raise RuntimeError("No MP4 found in ComfyUI history")

    item = files[0]

    params = {
        "filename": item["filename"],
        "subfolder": item.get("subfolder", ""),
        "type": item.get("type", "output")
    }

    r = requests.get(
        url.rstrip("/") + "/view",
        params=params,
        stream=True,
        timeout=300
    )
    r.raise_for_status()

    target.parent.mkdir(parents=True, exist_ok=True)

    with open(target, "wb") as f:
        for chunk in r.iter_content(1024 * 1024):
            if chunk:
                f.write(chunk)

def get_gpu_temp():
    try:
        r = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=temperature.gpu",
                "--format=csv,noheader,nounits"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if r.returncode != 0:
            return None

        lines = [
            x.strip() for x in r.stdout.splitlines()
            if x.strip()
        ]

        if not lines:
            return None

        return int(lines[0])
    except Exception:
        return None

def wait_for_gpu_cool(hot, cool):
    temp = get_gpu_temp()

    if temp is None:
        return

    if temp < hot:
        print(f"GPU temp OK: {temp}C")
        return

    print(f"GPU HOT: {temp}C >= {hot}C")
    print(f"Waiting until GPU cools to <= {cool}C ...")

    while True:
        time.sleep(15)
        temp = get_gpu_temp()

        if temp is None:
            print("GPU temp unavailable; continuing.")
            return

        print(f"Current GPU temp: {temp}C")

        if temp <= cool:
            print("GPU cooled down. Continuing.")
            return

def paced_sleep(seconds, label):
    if seconds <= 0:
        return

    print(f"Pause: {label} ({seconds}s)")
    time.sleep(seconds)

def main():
    args = args_parse()

    project = PROJECTS_ROOT / args.project

    prompts_file = project / "ltx" / "prompts" / "ltx_prompts.json"
    images_dir = project / "images"
    videos_dir = project / "videos"

    if not WORKFLOW.exists():
        raise FileNotFoundError(WORKFLOW)

    if not prompts_file.exists():
        raise FileNotFoundError(prompts_file)

    data = load_json(prompts_file)
    scenes = select_scenes(data["scenes"], args)

    if not scenes:
        raise RuntimeError("No scenes selected")

    print("SELECTED:", [x["scene_id"] for x in scenes])
    print(
        f"PACING: scene pause={args.pause_scene}s | "
        f"batch size={args.batch_size} | "
        f"batch pause={args.pause_batch}s"
    )
    print(
        f"GPU GUARD: hot={args.gpu_hot}C | cool={args.gpu_cool}C"
    )

    for idx, scene in enumerate(scenes, 1):
        sid = scene["scene_id"]

        image = images_dir / scene["image"]
        prompt = scene["motion_prompt"].strip()
        duration = int(scene["duration"])
        mp = float(scene["mp"])

        if not image.exists():
            print("SKIP - IMAGE MISSING:", image)
            continue

        if not prompt:
            print("SKIP - PROMPT EMPTY:", sid)
            continue

        output = videos_dir / f"{sid}_v{args.version}.mp4"

        print("")
        print(
            f"[{idx}/{len(scenes)}]",
            sid,
            "| duration:", duration,
            "| MP:", mp,
            "| version:", args.version
        )

        wait_for_gpu_cool(args.gpu_hot, args.gpu_cool)

        workflow = load_json(WORKFLOW)

        workflow[PROMPT_NODE]["inputs"]["value"] = prompt
        workflow[DURATION_NODE]["inputs"]["value"] = duration
        workflow[MEGAPIXELS_NODE]["inputs"]["megapixels"] = mp

        workflow[PROMPT_ENHANCE_NODE]["inputs"]["value"] = False
        workflow[NEGATIVE_NODE]["inputs"]["text"] = NEGATIVE
        workflow[CREATE_VIDEO_NODE]["inputs"].pop("audio", None)

        workflow[SAVE_NODE]["inputs"]["filename_prefix"] = (
            f"THENWISE/{args.project}/{sid}_v{args.version}"
        )

        if args.dry_run:
            print("DRY RUN OK")
        else:
            uploaded = upload_image(args.comfy_url, image)
            workflow[IMAGE_NODE]["inputs"]["image"] = uploaded["name"]

            prompt_id = queue_prompt(args.comfy_url, workflow)

            print("QUEUED:", prompt_id)

            history = wait_history(args.comfy_url, prompt_id)

            download_video(
                args.comfy_url,
                history,
                output
            )

            print("SAVED:", output)

        # pause after each scene except the last one
        if idx < len(scenes):
            if args.batch_size > 0 and idx % args.batch_size == 0:
                paced_sleep(args.pause_batch, f"after batch of {args.batch_size} scenes")
            else:
                paced_sleep(args.pause_scene, "between scenes")

if __name__ == "__main__":
    main()