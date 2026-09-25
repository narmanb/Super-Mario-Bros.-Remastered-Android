#!/usr/bin/env python3
"""Install the temporary Android physics diagnostics as an autoload.

The diagnostics are deliberately independent of OnScreenControls.tscn.  The
Android touch scene is generated during export and may be hidden/reparented by
the wrapper, so attaching diagnostics to it is not a reliable way to display a
runtime test readout.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "project.godot"
AUTOLOAD_NAME = "AndroidPhysicsDiagnostics"
SCRIPT_PATH = "res://Scripts/Parts/AndroidPhysicsDiagnosticsLabel.gd"
AUTOLOAD_LINE = f'{AUTOLOAD_NAME}="*{SCRIPT_PATH}"'


def main() -> None:
    text = PROJECT.read_text(encoding="utf-8")

    match = re.search(r"(?ms)^\[autoload\]\n(.*?)(?=^\[|\Z)", text)
    if match is None:
        raise RuntimeError("Could not locate [autoload] section in project.godot")

    section = match.group(0)
    if re.search(rf"(?m)^{re.escape(AUTOLOAD_NAME)}=", section):
        print("Android physics diagnostics autoload already installed")
        return

    # Append to the existing autoload section so Settings/Global are created
    # first.  project.godot is modified only in the CI checkout used to build
    # the Android APK; the source project keeps no permanent debug autoload.
    insertion = match.end()
    before = text[:insertion].rstrip("\n")
    after = text[insertion:].lstrip("\n")
    text = before + "\n" + AUTOLOAD_LINE + "\n\n" + after

    PROJECT.write_text(text, encoding="utf-8")

    # Fail the build immediately if the expected autoload was not written.
    verify = PROJECT.read_text(encoding="utf-8")
    if AUTOLOAD_LINE not in verify:
        raise RuntimeError("Physics diagnostics autoload verification failed")

    print(f"Installed Android physics diagnostics autoload: {AUTOLOAD_LINE}")


if __name__ == "__main__":
    main()
