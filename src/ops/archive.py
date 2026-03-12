
from __future__ import annotations
import logging
import os, pathlib, time, zipfile
from typing import Optional
from .metrics import ARCHIVE_UPLOADS_SUCCEEDED, ARCHIVE_UPLOADS_FAILED

logger = logging.getLogger(__name__)

def zip_dir(src_dir: str, out_zip: str) -> str:
    p = pathlib.Path(src_dir)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for base, _, fns in os.walk(p):
            for fn in fns:
                path = pathlib.Path(base) / fn
                zf.write(path, path.relative_to(p))
    return out_zip

def archive_snapshot(snapshot_dir: str, target_dir: Optional[str] = None, method: str = "local_zip") -> str:
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

    if method == "sftp":
        try:
            import paramiko  # type: ignore
            host = os.getenv("SFTP_HOST"); user = os.getenv("SFTP_USER"); pw = os.getenv("SFTP_PASSWORD")
            remote_dir = os.getenv("SFTP_PATH", "/")
            if not all([host, user, pw]):
                return artifact
            transport = paramiko.Transport((host, 22))
            transport.connect(username=user, password=pw)
            sftp = paramiko.SFTPClient.from_transport(transport)
            try:
                try: sftp.chdir(remote_dir)
                except IOError:
                    sftp.mkdir(remote_dir); sftp.chdir(remote_dir)
                remote_path = f"{remote_dir.rstrip('/')}/{snap_name}.zip"
                sftp.put(artifact, remote_path)
                return f"sftp://{host}{remote_path}"
            finally:
                try: sftp.close()
                except Exception: pass
                try: transport.close()
                except Exception: pass
        except Exception:
            return artifact

    # Run retention cleanup after successful archive (V7 spec §12: retention_days: 30)
    cleanup_old_snapshots(str(archive_root))

    return artifact


def cleanup_old_snapshots(archive_dir: str, retention_days: int = 30) -> int:
    """Remove snapshot archives older than retention_days.

    V7 spec §12: backups.retention_days = 30.

    Args:
        archive_dir: Directory containing snapshot zip files.
        retention_days: Maximum age in days before deletion.

    Returns:
        Number of files removed.
    """
    archive_path = pathlib.Path(archive_dir)
    if not archive_path.exists():
        return 0

    cutoff = time.time() - (retention_days * 86400)
    removed = 0

    for f in archive_path.glob("*.zip"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
                logger.info(f"Removed expired snapshot: {f.name}")
        except OSError as e:
            logger.warning(f"Failed to remove {f.name}: {e}")

    if removed:
        logger.info(f"Cleaned up {removed} snapshots older than {retention_days} days")

    return removed
