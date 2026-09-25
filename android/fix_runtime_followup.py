#!/usr/bin/env python3
"""Follow-up Android runtime fixes applied after fix_mobile_runtime.py.

This keeps the 1.1 Android wrapper aligned with the older proven Android port,
nudges the touch-control clusters outward, strips the desktop/native FileDialog
from the Android ROM-verification scene, and keeps expensive resource-pack
initialization out of synchronous scene insertion.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_global_transition() -> None:
    path = ROOT / "Scripts" / "Classes" / "Singletons" / "Global.gd"
    text = path.read_text(encoding="utf-8")
    old = '\tif android_wrapper != null:\n\t\tawait android_wrapper.change_scene_to(scene_path)\n'
    new = '\tif android_wrapper != null:\n\t\t# Android wrapper scene swaps are synchronous once requested. Do not\n\t\t# await a ready/tree_exited signal here; both can already have fired\n\t\t# by the time an await is registered and leave the transition stuck.\n\t\tandroid_wrapper.change_scene_to(scene_path)\n'
    if old not in text:
        raise RuntimeError("Could not find generated Android wrapper transition in Global.gd")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_wrapper() -> None:
    path = ROOT / "Scripts" / "Wrapper.gd"
    text = path.read_text(encoding="utf-8")
    old = '''func change_scene_to(scene) -> void:
    for child in game_viewport.get_children():
        if child == Global:
            continue
        child.queue_free()
        await child.tree_exited
    var packed_scene: PackedScene = null
    if scene is String:
        packed_scene = load(scene)
    elif scene is PackedScene:
        packed_scene = scene
    if packed_scene == null:
        push_error("Android Wrapper could not load scene: " + str(scene))
        return
    var new_scene := packed_scene.instantiate()
    game_viewport.add_child(new_scene)
    await new_scene.ready
'''
    new = '''func change_scene_to(scene) -> void:
    # Do not await tree_exited/ready here. The old scene can be detached
    # immediately, and add_child() enters/readies the replacement scene during
    # the call. Awaiting either signal after the operation can miss the one-shot
    # signal and permanently strand Android on the previous screen.
    for child in game_viewport.get_children():
        if child == Global:
            continue
        game_viewport.remove_child(child)
        child.queue_free()
    var packed_scene: PackedScene = null
    if scene is String:
        packed_scene = load(scene)
    elif scene is PackedScene:
        packed_scene = scene
    if packed_scene == null:
        push_error("Android Wrapper could not load scene: " + str(scene))
        return
    var new_scene := packed_scene.instantiate()
    if new_scene == null:
        push_error("Android Wrapper could not instantiate scene: " + str(scene))
        return
    game_viewport.add_child(new_scene)
'''
    if old not in text:
        raise RuntimeError("Could not locate generated Android Wrapper.change_scene_to()")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_android_resource_initialization() -> None:
    """Do not perform resource-pack disk/image work while add_child() enters TitleScreen.

    The title diagnostic that rendered successfully stripped child scripts. The intact
    scene hangs while its child lifecycle callbacks run synchronously during
    SubViewport.add_child(). ResourceSetterNew, PackTextureRect, PackNinePatch and
    PackButton all perform resource lookup/loading from _enter_tree()/_ready(). On
    Android, queue those initial refreshes until a later frame so scene insertion and
    the root title lifecycle can finish first. Theme-change callbacks use the same
    lightweight queue path.
    """

    setter_path = ROOT / "Scripts" / "Classes" / "Components" / "ResourceSetterNew.gd"
    setter = setter_path.read_text(encoding="utf-8")
    setter_old = '''func _ready() -> void:
\tif mode != ResourceMode.THEME:
\t\tGlobal.level_theme_changed.connect(update_resource)

func _enter_tree() -> void:
\tsafety_check()
\tif update_on_spawn:
\t\tupdate_resource()
'''
    setter_new = '''var _android_update_queued := false

func _ready() -> void:
\tif mode != ResourceMode.THEME:
\t\tif OS.has_feature("android"):
\t\t\tGlobal.level_theme_changed.connect(_queue_android_update_resource)
\t\telse:
\t\t\tGlobal.level_theme_changed.connect(update_resource)

func _enter_tree() -> void:
\tsafety_check()
\tif update_on_spawn:
\t\tif OS.has_feature("android"):
\t\t\t_queue_android_update_resource()
\t\telse:
\t\t\tupdate_resource()

func _queue_android_update_resource() -> void:
\tif _android_update_queued or not is_inside_tree():
\t\treturn
\t_android_update_queued = true
\tcall_deferred("_run_android_update_resource")

func _run_android_update_resource() -> void:
\tawait get_tree().process_frame
\t_android_update_queued = false
\tif is_inside_tree() and not is_queued_for_deletion():
\t\tupdate_resource()
'''
    if setter_old not in setter:
        raise RuntimeError("Could not locate ResourceSetterNew startup lifecycle")
    setter_path.write_text(setter.replace(setter_old, setter_new, 1), encoding="utf-8")

    for relative in (
        "Scripts/Classes/UI/PackTextureRect.gd",
        "Scripts/Classes/UI/PackNinePatch.gd",
    ):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        old = '''func _ready() -> void:
\tupdate()
\tGlobal.level_theme_changed.connect(update)
'''
        new = '''var _android_update_queued := false

func _ready() -> void:
\tif OS.has_feature("android"):
\t\tGlobal.level_theme_changed.connect(_queue_android_update)
\t\t_queue_android_update()
\t\treturn
\tupdate()
\tGlobal.level_theme_changed.connect(update)

func _queue_android_update() -> void:
\tif _android_update_queued or not is_inside_tree():
\t\treturn
\t_android_update_queued = true
\tcall_deferred("_run_android_update")

func _run_android_update() -> void:
\tawait get_tree().process_frame
\t_android_update_queued = false
\tif is_inside_tree() and not is_queued_for_deletion():
\t\tupdate()
'''
        if old not in text:
            raise RuntimeError(f"Could not locate startup lifecycle in {relative}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    button_path = ROOT / "Scripts" / "Classes" / "UI" / "PackButton.gd"
    button = button_path.read_text(encoding="utf-8")
    button_old = '''func _ready() -> void:
\tadd_child(resource_getter)
\tupdate()
\tGlobal.level_theme_changed.connect(update)
'''
    button_new = '''var _android_update_queued := false

func _ready() -> void:
\tadd_child(resource_getter)
\tif OS.has_feature("android"):
\t\tGlobal.level_theme_changed.connect(_queue_android_update)
\t\t_queue_android_update()
\t\treturn
\tupdate()
\tGlobal.level_theme_changed.connect(update)

func _queue_android_update() -> void:
\tif _android_update_queued or not is_inside_tree():
\t\treturn
\t_android_update_queued = true
\tcall_deferred("_run_android_update")

func _run_android_update() -> void:
\tawait get_tree().process_frame
\t_android_update_queued = false
\tif is_inside_tree() and not is_queued_for_deletion():
\t\tupdate()
'''
    if button_old not in button:
        raise RuntimeError("Could not locate PackButton startup lifecycle")
    button_path.write_text(button.replace(button_old, button_new, 1), encoding="utf-8")


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
                   '\tif OS.has_feature("android"):\n')
    if old_connect not in script:
        raise RuntimeError("Could not isolate desktop FileDialog connection in RomVerifier.gd")
    script = script.replace(old_connect, new_connect, 1)

    old_show = '\tfile_dialog.show()\n'
    new_show = '\tif file_dialog != null:\n\t\tfile_dialog.show()\n'
    if old_show not in script:
        raise RuntimeError("Could not guard desktop FileDialog show call")
    script = script.replace(old_show, new_show, 1)

    script_path.write_text(script, encoding="utf-8")


def main() -> None:
    patch_global_transition()
    patch_wrapper()
    patch_android_resource_initialization()
    patch_touch_positions()
    patch_rom_verifier()
    print("Applied Android wrapper, deferred-resource, touch-position, and ROM-verifier fixes")


if __name__ == "__main__":
    main()
