"""
Connected Hardware & Test Device Auto-Detection
Detects Android devices over ADB and queries model/API specs.
"""

import os
import shutil
import subprocess
from typing import List, Optional


def detect_connected_devices(
    workspace_dir: str, adb_path: Optional[str] = None
) -> List[dict]:
    adb = (
        adb_path
        or shutil.which("adb")
        or shutil.which("adb.exe")
        or os.path.join(
            os.environ.get("ANDROID_HOME", ""), "platform-tools", "adb.exe"
        )
    )

    if not adb or not os.path.exists(adb):
        return []

    try:
        res = subprocess.run(
            [adb, "devices"],
            capture_output=True,
            text=True,
            cwd=workspace_dir,
            timeout=5,
        )
        if res.returncode != 0:
            return []

        devices = []
        for line in res.stdout.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                serial = parts[0]
                model = _get_prop(adb, serial, "ro.product.model")
                brand = _get_prop(adb, serial, "ro.product.brand")
                api = _get_prop(adb, serial, "ro.build.version.sdk")
                devices.append(
                    {
                        "serial": serial,
                        "brand": brand or "Generic",
                        "model": model or serial,
                        "api_level": int(api) if api and api.isdigit() else 0,
                    }
                )
        return devices
    except Exception:
        return []


def _get_prop(adb: str, serial: str, prop: str) -> str:
    try:
        r = subprocess.run(
            [adb, "-s", serial, "shell", "getprop", prop],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return r.stdout.strip()
    except Exception:
        return ""
