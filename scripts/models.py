import argparse,json,pathlib,os,hashlib,shutil
from huggingface_hub import hf_hub_download
def digest(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""):h.update(b)
 return h.hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument("--group",choices=["ltx","h3","yue","all"],default="ltx");a.add_argument("--list",action="store_true");a.add_argument("--verify-only",action="store_true");args=a.parse_args()
 manifest=json.loads((pathlib.Path(__file__).resolve().parent.parent/"config/model_manifest.json").read_text())
 root=pathlib.Path("/workspace-global/models")
 for v in manifest["files"]:
  if args.group not in ("all",v["group"]):continue
  path=root/v["dest"]
  if args.list:print(v);continue
  minimum=int(v["min_gib"]*1024**3)
  if path.is_file() and path.stat().st_size>=minimum:
   print("EXISTS",path,flush=True);continue
  if args.verify_only:raise RuntimeError("MISSING "+str(path))
  if not root.parent.is_dir():raise RuntimeError("Mount missing: "+str(root.parent))
  src=pathlib.Path(hf_hub_download(repo_id=v["repo"],filename=v["remote"],cache_dir="/workspace/cache/hf",token=os.environ.get("HF_TOKEN")))
  if src.stat().st_size<minimum:raise RuntimeError("Too small: "+str(src))
  path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(".partial")
  shutil.copyfile(src,tmp)
  if digest(src)!=digest(tmp):raise RuntimeError("checksum mismatch")
  tmp.replace(path);print("SAVED",path,flush=True)
if __name__=="__main__":main()
