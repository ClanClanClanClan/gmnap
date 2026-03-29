from __future__ import annotations

import pathlib

import paramiko
import yaml


def _load_cfg(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def push_directory_sftp(
    local_dir: str, config_path: str = "config/archive.yaml"
) -> None:
    cfg = _load_cfg(config_path)
    host = cfg.get("host")
    port = int(cfg.get("port", 22))
    user = cfg.get("username")
    key_path = cfg.get("private_key")
    remote_base = cfg.get("remote_base", "/lineage_snapshots")
    if not (host and user and key_path):
        raise RuntimeError("archive.yaml missing host/username/private_key")
    key = paramiko.Ed25519Key.from_private_key_file(key_path)
    transport = paramiko.Transport((host, port))
    transport.connect(username=user, pkey=key)
    sftp = paramiko.SFTPClient.from_transport(transport)
    try:
        local = pathlib.Path(local_dir)
        if not local.exists():
            raise FileNotFoundError(local_dir)
        remote_dir = pathlib.Path(remote_base) / local.name
        parts = str(remote_dir).split("/")
        cur = ""
        for p in parts:
            if not p:
                continue
            cur = (cur + "/" + p) if cur else ("/" + p)
            try:
                sftp.listdir(cur)
            except IOError:
                sftp.mkdir(cur)
        for path in local.rglob("*"):
            if path.is_file():
                target = str(remote_dir / path.relative_to(local))
                parent = "/".join(target.split("/")[:-1])
                try:
                    sftp.listdir(parent)
                except IOError:
                    sub = ""
                    for part in parent.split("/"):
                        if not part:
                            continue
                        sub = (sub + "/" + part) if sub else ("/" + part)
                        try:
                            sftp.listdir(sub)
                        except IOError:
                            sftp.mkdir(sub)
                sftp.put(str(path), target)
    finally:
        sftp.close()
        transport.close()
