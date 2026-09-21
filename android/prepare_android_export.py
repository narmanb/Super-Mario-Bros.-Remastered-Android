#!/usr/bin/env python3
"""Prepare the upstream 1.1 project for a reproducible Godot 4.6 Android build.

The script intentionally keeps most Android-only changes out of upstream project files:
- downloads the proven native file-picker AARs from the previous Android port,
- disables the desktop Discord GDExtension for the Android export,
- applies the mobile layout/orientation settings used by the working 1.0.2 port,
- enables ETC2/ASTC imports required for Android export from an x86_64 host,
- appends a minimal ARM64 Android export preset if one is not present.
"""

from __future__ import annotations

import re
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_ANDROID_COMMIT = "61fe0a6464101981cbee56701955fc0005f59664"
OLD_ANDROID_RAW = (
    "https://raw.githubusercontent.com/"
    "mircowuffwuff/super-mario-bros.-remastered-android/"
    f"{OLD_ANDROID_COMMIT}"
)


def download_file_picker_aars() -> None:
    addon_dir = ROOT / "addons" / "AndroidFilePicker"
    addon_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("app-debug.aar", "app-release.aar"):
        destination = addon_dir / filename
        if destination.exists() and destination.stat().st_size > 0:
            continue
        url = f"{OLD_ANDROID_RAW}/addons/AndroidFilePicker/{filename}"
        print(f"Downloading {filename} from pinned Android-port commit")
        urllib.request.urlretrieve(url, destination)


def patch_project_settings() -> None:
    path = ROOT / "project.godot"
    text = path.read_text(encoding="utf-8")

    # DiscordRPC is a desktop GDExtension. The runtime manager also has an
    # Android-safe stub, but removing the plugin itself avoids loading an
    # incompatible native library during import/export.
    text = text.replace("use_discord=true", "use_discord=false")
    text = text.replace(', "res://addons/discord-rpc-gd/plugin.cfg"', "")
    text = text.replace('"res://addons/discord-rpc-gd/plugin.cfg", ', "")

    # Enable the Android export plugin without disturbing the other 1.1 tools.
    if 'res://addons/AndroidFilePicker/plugin.cfg' not in text:
        marker = "enabled=PackedStringArray("
        pos = text.find(marker)
        if pos == -1:
            raise RuntimeError("Could not find [editor_plugins] enabled list")
        insert_at = pos + len(marker)
        text = (
            text[:insert_at]
            + '"res://addons/AndroidFilePicker/plugin.cfg", '
            + text[insert_at:]
        )

    # Match the proven Android port's widescreen/landscape presentation while
    # retaining 1.1's gl_compatibility renderer.
    text = text.replace('window/stretch/mode="viewport"', 'window/stretch/mode="canvas_items"')
    if 'window/stretch/aspect="expand"' not in text:
        text = text.replace(
            'window/stretch/mode="canvas_items"',
            'window/stretch/mode="canvas_items"\nwindow/stretch/aspect="expand"',
        )
    if "window/handheld/orientation=4" not in text:
        text = text.replace(
            'window/stretch/aspect="expand"',
            'window/stretch/aspect="expand"\nwindow/handheld/orientation=4',
        )

    # Godot 4.6 Android export validates that ETC2/ASTC imports are enabled.
    # On an x86_64 Linux host, the default S3TC preference can otherwise yield
    # a blank "configuration errors" message (Godot issue #119895).
    etc2_setting = "textures/vram_compression/import_etc2_astc=true"
    if etc2_setting not in text:
        rendering_marker = "[rendering]\n"
        if rendering_marker in text:
            text = text.replace(rendering_marker, rendering_marker + "\n" + etc2_setting + "\n", 1)
        else:
            text = text.rstrip() + "\n\n[rendering]\n\n" + etc2_setting + "\n"

    path.write_text(text, encoding="utf-8")

    shutil.rmtree(ROOT / "addons" / "discord-rpc-gd", ignore_errors=True)


def append_android_export_preset() -> None:
    path = ROOT / "export_presets.cfg"
    text = path.read_text(encoding="utf-8")
    if re.search(r'^name="Android"$', text, flags=re.MULTILINE):
        print("Android export preset already present")
        return

    indices = [int(value) for value in re.findall(r"^\[preset\.(\d+)\]$", text, re.MULTILINE)]
    index = max(indices, default=-1) + 1

    preset = f'''\n\n[preset.{index}]\n\nname="Android"\nplatform="Android"\nrunnable=true\nadvanced_options=true\ndedicated_server=false\ncustom_features=""\nexport_filter="all_resources"\ninclude_filter="*.bgm, *.mp3, *.txt, *.fnt, version.txt"\nexclude_filter=""\nexport_path="build/SMB1R-1.1-android-debug.apk"\npatches=PackedStringArray()\nencryption_include_filters=""\nencryption_exclude_filters=""\nseed=0\nencrypt_pck=false\nencrypt_directory=false\nscript_export_mode=2\n\n[preset.{index}.options]\n\ncustom_template/debug=""\ncustom_template/release=""\ngradle_build/use_gradle_build=true\ngradle_build/gradle_build_directory=""\ngradle_build/android_source_template=""\ngradle_build/compress_native_libraries=false\ngradle_build/export_format=0\ngradle_build/min_sdk=""\ngradle_build/target_sdk=""\ngradle_build/custom_theme_attributes={{}}\narchitectures/armeabi-v7a=false\narchitectures/arm64-v8a=true\narchitectures/x86=false\narchitectures/x86_64=false\nversion/code=110\nversion/name="1.1-android-dev"\npackage/unique_name="com.narmanb.smb1r"\npackage/name="Super Mario Bros. Remastered"\npackage/signed=true\npackage/app_category=2\npackage/retain_data_on_uninstall=true\npackage/exclude_from_recents=false\npackage/show_in_android_tv=false\npackage/show_in_app_library=true\npackage/show_as_launcher_app=false\nlauncher_icons/main_192x192=""\nlauncher_icons/adaptive_foreground_432x432=""\nlauncher_icons/adaptive_background_432x432=""\nlauncher_icons/adaptive_monochrome_432x432=""\ngraphics/opengl_debug=false\nshader_baker/enabled=false\nxr_features/xr_mode=0\ngesture/swipe_to_dismiss=false\nscreen/immersive_mode=true\nscreen/support_small=true\nscreen/support_normal=true\nscreen/support_large=true\nscreen/support_xlarge=true\nscreen/edge_to_edge=true\nscreen/background_color=Color(0, 0, 0, 1)\nuser_data_backup/allow=true\ncommand_line/extra_args=""\napk_expansion/enable=false\napk_expansion/SALT=""\napk_expansion/public_key=""\npermissions/custom_permissions=PackedStringArray()\npermissions/internet=true\n'''

    path.write_text(text.rstrip() + preset + "\n", encoding="utf-8")
    print(f"Added Android export preset as preset.{index}")


def main() -> None:
    download_file_picker_aars()
    patch_project_settings()
    append_android_export_preset()
    (ROOT / "build").mkdir(exist_ok=True)
    print("Android export preparation complete")


if __name__ == "__main__":
    main()
