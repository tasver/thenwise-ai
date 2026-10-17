import json,pathlib,sys
p=pathlib.Path("/workspace-global/models")
j=json.loads((pathlib.Path(__file__).resolve().parent.parent/"config/model_manifest.json").read_text())
missing=[r["dest"] for r in j["files"] if not (p/r["dest"]).exists()]
print("MISSING:",missing)
sys.exit(bool(missing))
