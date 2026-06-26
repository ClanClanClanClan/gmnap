from __future__ import annotations

import os
import pathlib
import zipfile
from typing import Optional

from .metrics import ARCHIVE_UPLOADS_FAILED, ARCHIVE_UPLOADS_SUCCEEDED


def zip_dir(src_dir: str, out_zip: str) -> str:
    p = pathlib.Path(src_dir)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for base, _, fns in os.walk(p):
            for fn in fns:
                path = pathlib.Path(base) / fn
                zf.write(path, path.relative_to(p))
    return out_zip


def archive_snapshot(
    snapshot_dir: str, target_dir: Optional[str] = None, method: str = "local_zip"
) -> str:
    """
    Archive a snapshot directory. Default: create a local zip under `archive/`.
    If method == "sftp" and paramiko available, supports SFTP upload (best-effort).
    Returns the archived artifact path or remote URI.
    """
    snap = pathlib.Path(snapshot_dir)
    snap_name = snap.name
    archive_root = pathlib.Path(target_dir or "archive")
    archive_root.mkdir(parents=True, exist_ok=True)
    artifact = str(archive_root / f"{snap_name}.zip")

    try:
        zip_dir(str(snap), artifact)
        ARCHIVE_UPLOADS_SUCCEEDED.inc()
    except Exception:
        ARCHIVE_UPLOADS_FAILED.inc()
        raise

    # Optional SFTP upload
    if method == "sftp":
        try:
            import os  # type: ignore

            import paramiko

            host = os.getenv("SFTP_HOST")
            user = os.getenv("SFTP_USER")
            pw = os.getenv("SFTP_PASSWORD")
            remote_dir = os.getenv("SFTP_PATH", "/")
            if not all([host, user, pw]):
                return artifact  # missing creds → keep local zip
            transport = paramiko.Transport((host, 22))
            transport.connect(username=user, password=pw)
            sftp = paramiko.SFTPClient.from_transport(transport)
            try:
                try:
                    sftp.chdir(remote_dir)
                except IOError:
                    sftp.mkdir(remote_dir)
                    sftp.chdir(remote_dir)
                remote_path = f"{remote_dir.rstrip('/')}/{snap_name}.zip"
                sftp.put(artifact, remote_path)
                sftp.close()
                transport.close()
                return f"sftp://{host}{remote_path}"
            finally:
                try:
                    sftp.close()
                except Exception:
                    pass
                try:
                    transport.close()
                except Exception:
                    pass
        except Exception:
            # keep local artifact if remote upload fails
            return artifact

    return artifact
