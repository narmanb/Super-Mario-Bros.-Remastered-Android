#!/usr/bin/env python3
"""Follow-up Android runtime fixes applied after fix_mobile_runtime.py.

This keeps the 1.1 Android wrapper aligned with the older proven Android port,
nudges the touch-control clusters outward, and strips the desktop/native
FileDialog from the Android ROM-verification scene.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_global_transition() -> None:
    path = ROOT / "Scripts" / "Classes" / "Singletons" / "Global.gd"
    text = path.read_text(encoding="utf-8")
    old = '\tif android_wrapper != null:\n\t\tawait android_wrapper.change_scene_to(scene_path)\n'
    new = '\tif android_wrapper != null:\n\t\t# Match the older working Android wrapper: start the viewport scene\n\t\t# transition without awaiting the wrapper coroutine itself.\n\t\tandroid_wrapper.change_scene_to(scene_path)\n'
    if old not in text:
        raise RuntimeError("Could not find generated Android wrapper transition in Global.gd")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_wrapper() -> None:
    path = ROOT / "Scripts" / "Wrapper.gd"
    text = path.read_text(encoding="utf-8")
    old = '    game_viewport.add_child(new_scene)\n    await new_scene.ready\n'
    new = ('    game_viewport.add_child(new_scene)\n'
           '    # add_child() enters the scene tree immediately; do not await ready here.\n'
           '    # Awaiting a signal that may already have fired can strand this coroutine.\n')
    if old not in text:
        raise RuntimeError("Could not find generated new-scene ready wait in Wrapper.gd")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_touch_positions() -> None:
    path = ROOT / "Scenes" / "Prefabs" / "UI" / "OnScreenControls.tscn"
    text = path.read_text(encoding="utf-8")

    left_old = ('[node name="Control" type="Control" parent="."]\n'
                'layout_mode = 3\n'
                'anchors_preset = 2\n'
                'anchor_top = 1.0\n'
                'anchor_bottom = 1.0\n'
                'offset_top = -141.0\n'
                'offset_right = 141.0\n')
    left_new = ('[node name="Control" type="Control" parent="."]\n'
                'layout_mode = 3\n'
                'anchors_preset = 2\n'
                'anchor_top = 1.0\n'
                'anchor_bottom = 1.0\n'
                'offset_left = -10.0\n'
                'offset_top = -141.0\n'
                'offset_right = 131.0\n')
    if left_old not in text:
        raise RuntimeError("Could not locate left touch-control container")
    text = text.replace(left_old, left_new, 1)

    right_old = ('[node name="Control2" type="Control" parent="."]\n'
                 'layout_mode = 3\n'
                 'anchors_preset = 3\n'
                 'anchor_left = 1.0\n'
                 'anchor_top = 1.0\n'
                 'anchor_right = 1.0\n'
                 'anchor_bottom = 1.0\n'
                 'offset_left = -115.0\n'
                 'offset_top = -141.0\n')
    right_new = ('[node name="Control2" type="Control" parent="."]\n'
                 'layout_mode = 3\n'
                 'anchors_preset = 3\n'
                 'anchor_left = 1.0\n'
                 'anchor_top = 1.0\n'
                 'anchor_right = 1.0\n'
                 'anchor_bottom = 1.0\n'
                 'offset_left = -105.0\n'
                 'offset_top = -141.0\n'
                 'offset_right = 10.0\n')
    if right_old not in text:
        raise RuntimeError("Could not locate right touch-control container")
    text = text.replace(right_old, right_new, 1)

    path.write_text(text, encoding="utf-8")


def patch_rom_verifier() -> None:
    scene_path = ROOT / "Scenes" / "Levels" / "RomVerifier.tscn"
    scene = scene_path.read_text(encoding="utf-8")

    # FileDialog is a desktop/native popup Window. The proven Android port does
    # not instantiate it; Android uses GodotFilePicker instead. In our wrapper,
    # gameplay scenes live inside a SubViewport, so keep native popup windows
    # out of the Android scene tree entirely.
    scene, node_count = re.subn(
        r'\n\[node name="FileDialog" type="FileDialog" parent="\."[^\n]*\]\n.*?(?=\n\[connection|\Z)',
        '\n',
        scene,
        count=1,
        flags=re.DOTALL,
    )
    if node_count != 1:
        raise RuntimeError("Could not remove FileDialog node from RomVerifier.tscn")

    scene, connection_count = re.subn(
        r'^\[connection [^\n]*from="FileDialog"[^\n]*\]\n?',
        '',
        scene,
        flags=re.MULTILINE,
    )
    if connection_count < 1:
        raise RuntimeError("Could not remove FileDialog connections from RomVerifier.tscn")
    scene_path.write_text(scene, encoding="utf-8")

    script_path = ROOT / "Scripts" / "UI" / "RomVerifier.gd"
    script = script_path.read_text(encoding="utf-8")

    old_decl = '@onready var file_dialog = $FileDialog\n'
    new_decl = '@onready var file_dialog = get_node_or_null("FileDialog")\n'
    if old_decl not in script:
        raise RuntimeError("Could not locate RomVerifier FileDialog declaration")
    script = script.replace(old_decl, new_decl, 1)

    old_connect = '\tfile_dialog.canceled.connect(file_prompt_closed)\n\n\tif OS.has_feature("android"):\n'
    new_connect = ('\tif not OS.has_feature("android") and file_dialog != null:\n'
                   '\t\tfile_dialog.canceled.connect(file_prompt_closed)\n\n'
                   '\tif OS.has_feature("android"):\n'
                   '\t\tOnScreenControls.should_show = false\n')
    if old_connect not in script:
        raise RuntimeError("Could not isolate desktop FileDialog connection in RomVerifier.gd")
    script = script.replace(old_connect, new_connect, 1)

    old_show = '\tfile_dialog.show()\n'
    new_show = '\tif file_dialog != null:\n\t\tfile_dialog.show()\n'
    if old_show not in script:
        raise RuntimeError("Could not guard desktop FileDialog show call")
    script = script.replace(old_show, new_show, 1)

    old_exit = ('func _exit_tree() -> void:\n'
                '\tGlobal.get_node("GameHUD").show()\n')
    new_exit = ('func _exit_tree() -> void:\n'
                '\tGlobal.get_node("GameHUD").show()\n'
                '\tif OS.has_feature("android"):\n'
                '\t\tOnScreenControls.should_show = true\n')
    if old_exit not in script:
        raise RuntimeError("Could not patch RomVerifier exit handling")
    script = script.replace(old_exit, new_exit, 1)

    script_path.write_text(script, encoding="utf-8")


def main() -> None:
    patch_global_transition()
    patch_wrapper()
    patch_touch_positions()
    patch_rom_verifier()
    print("Applied Android wrapper, touch-position, and ROM-verifier fixes")


if __name__ == "__main__":
    main()
