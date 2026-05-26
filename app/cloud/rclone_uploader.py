import subprocess
from pathlib import Path
from typing import Any


def upload_file(local_path: str | Path, remote_path: str,
                logger: Any = None) -> dict:
    cmd = ["rclone", "copy", str(local_path), remote_path, "--verbose"]

    log = logger.debug if logger else print
    log(f"Uploading: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        error_msg = result.stderr.strip()
        log(f"Upload failed: {error_msg}")
        return {"success": False, "error": error_msg}

    log(f"Upload complete: {local_path} -> {remote_path}")
    return {"success": True, "remote_path": remote_path}


def upload_report(report_dir: str | Path, remote: str = "mega",
                  remote_path: str = "SignalForge",
                  logger: Any = None) -> dict:
    full_remote = f"{remote}:{remote_path}"
    return upload_file(report_dir, full_remote, logger)


def list_remote(remote: str = "mega", path: str = "",
                logger: Any = None) -> list[dict]:
    remote_path = f"{remote}:{path}" if path else f"{remote}:"
    cmd = ["rclone", "lsjson", remote_path]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        if logger:
            logger(f"Failed to list remote: {result.stderr.strip()}")
        return []

    import json
    return json.loads(result.stdout)
