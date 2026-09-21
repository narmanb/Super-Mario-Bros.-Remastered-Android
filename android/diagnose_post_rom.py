#!/usr/bin/env python3
"""Android-only isolation for the crash immediately after ROM asset generation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_resource_generator() -> None:
    path = ROOT / "Scripts" / "UI" / "RomResourceGenerator.gd"
    text = path.read_text(encoding="utf-8")

    old = '''func done() -> void:\n\tif not Settings.file.visuals.resource_packs.has(Global.ROM_PACK_NAME):\n\t\tSettings.file.visuals.resource_packs.insert(0, Global.ROM_PACK_NAME)\n\t\t\n\tawait get_tree().create_timer(0.5).timeout\n\tGlobal.transition_to_scene("res://Scenes/Levels/TitleScreen.tscn")\n'''

    new = '''func done() -> void:\n\tif not Settings.file.visuals.resource_packs.has(Global.ROM_PACK_NAME):\n\t\tSettings.file.visuals.resource_packs.insert(0, Global.ROM_PACK_NAME)\n\n\t# Android diagnostic: stop before the TitleScreen transition. If the app\n\t# remains alive here, generation itself is good and the crash is in the\n\t# title/resource-pack initialization path.\n\tGlobal.rom_assets_exist = true\n\tprogress_bar.value = progress_bar.max_value\n\t$MarginContainer/ProgressBar/Label.text = "ASSETS COMPLETE - DIAGNOSTIC"\n\tprint("[ANDROID_DIAG] ROM asset generation completed; title transition intentionally suppressed")\n'''

    if old not in text:
        raise RuntimeError("Could not locate RomResourceGenerator.done() for Android diagnostic")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    patch_resource_generator()
    print("Applied Android post-ROM crash isolation")


if __name__ == "__main__":
    main()
