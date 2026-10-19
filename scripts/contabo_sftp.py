"""Transfer only finished MP4 files to Contabo using verified SSH host keys."""
import os
import posixpath
from pathlib import Path

def uploader_from_env():
    if not os.environ.get("TW_SFTP_HOST"):
        return None
    return ContaboUploader()

class ContaboUploader:
    def __init__(self):
        import paramiko
        host=os.environ["TW_SFTP_HOST"]
        user=os.environ["TW_SFTP_USER"]
        self.base=os.environ["TW_SFTP_RESULTS_DIR"]
        if not self.base.startswith("/"):
            raise ValueError("TW_SFTP_RESULTS_DIR must be an absolute Linux path")
        known_hosts=os.environ.get("TW_SFTP_KNOWN_HOSTS","/root/.ssh/known_hosts")
        self.client=paramiko.SSHClient()
        self.client.load_host_keys(known_hosts)
        self.client.set_missing_host_key_policy(paramiko.RejectPolicy())
        self.client.connect(hostname=host,username=user,port=int(os.environ.get("TW_SFTP_PORT","22")),
                            key_filename=os.environ.get("TW_SFTP_KEY_PATH") or None,
                            look_for_keys=True,allow_agent=True,timeout=30)
        self.sftp=self.client.open_sftp()

    def mkdirs(self,path):
        current=""
        for part in path.strip("/").split("/"):
            if not part or part=="..":
                raise ValueError("Invalid remote directory")
            current+="/"+part
            try:self.sftp.stat(current)
            except FileNotFoundError:self.sftp.mkdir(current)

    def upload(self,project,source):
        if not project or not all(x.isalnum() or x in "_-" for x in project):
            raise ValueError("Unsafe project name")
        source=Path(source)
        directory=posixpath.join(self.base,project,"videos")
        self.mkdirs(directory)
        remote=posixpath.join(directory,source.name)
        temp=remote+".uploading"
        self.sftp.put(str(source),temp,confirm=True)
        if self.sftp.stat(temp).st_size!=source.stat().st_size:
            raise RuntimeError("Remote file size mismatch")
        self.sftp.rename(temp,remote)
        if self.sftp.stat(remote).st_size!=source.stat().st_size:
            raise RuntimeError("Remote post-transfer size mismatch")
        return remote
