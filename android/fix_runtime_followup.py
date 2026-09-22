#!/usr/bin/env python3
'''Follow-up Android runtime fixes applied after fix_mobile_runtime.py.

This keeps the 1.1 Android wrapper aligned with the older proven Android port,
nudges the touch-control clusters outward, strips the desktop/native FileDialog
from the Android ROM-verification scene, and adds a temporary staged TitleScreen
probe so hardware testing can isolate the crash to load/instantiate/add_child.
'''

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

    func_marker = "func change_scene_to(scene) -> void:\n"
    if func_marker not in text:
        raise RuntimeError("Could not find generated Wrapper.change_scene_to()")

    probe_start = '''func change_scene_to(scene) -> void:
    var title_probe := OS.has_feature("android") and scene is String and scene == "res://Scenes/Levels/TitleScreen.tscn"
    if title_probe:
        _set_android_title_probe("TITLE PROBE 1/5\\nBEFORE TITLE LOAD")
        await get_tree().create_timer(3.0, false).timeout
'''
    text = text.replace(func_marker, probe_start, 1)

    old_load_block = '''    var packed_scene: PackedScene = null
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
    new_load_block = '''    if title_probe:
        _set_android_title_probe("TITLE PROBE 1/5\\nOLD SCENE FREED - ABOUT TO LOAD")
        await get_tree().create_timer(2.0, false).timeout

    var packed_scene: PackedScene = null
    if scene is String:
        packed_scene = load(scene)
    elif scene is PackedScene:
        packed_scene = scene
    if packed_scene == null:
        push_error("Android Wrapper could not load scene: " + str(scene))
        return

    if title_probe:
        _set_android_title_probe("TITLE PROBE 2/5\\nTITLE LOAD OK")
        await get_tree().create_timer(3.0, false).timeout

    var new_scene := packed_scene.instantiate()

    if title_probe:
        _set_android_title_probe("TITLE PROBE 3/5\\nTITLE INSTANTIATE OK")
        await get_tree().create_timer(3.0, false).timeout

    game_viewport.add_child(new_scene)

    if title_probe:
        _set_android_title_probe("TITLE PROBE 4/5\\nADD_CHILD RETURNED")
        await get_tree().create_timer(3.0, false).timeout

    if not new_scene.is_node_ready():
        await new_scene.ready

    if title_probe:
        _set_android_title_probe("TITLE PROBE 5/5\\nTITLE NODE READY")
        await get_tree().create_timer(3.0, false).timeout
        _clear_android_title_probe()
'''
    if old_load_block not in text:
        raise RuntimeError("Could not find generated Wrapper load/instantiate/add_child block")
    text = text.replace(old_load_block, new_load_block, 1)

    helper_marker = "func get_game_viewport() -> SubViewport:\n"
    if helper_marker not in text:
        raise RuntimeError("Could not locate Wrapper.get_game_viewport()")

    helper = '''func _set_android_title_probe(message: String) -> void:
    var layer := get_node_or_null("AndroidTitleProbe") as CanvasLayer
    if layer == null:
        layer = CanvasLayer.new()
        layer.name = "AndroidTitleProbe"
        layer.layer = 200
        add_child(layer)

        var background := ColorRect.new()
        background.name = "Background"
        background.color = Color(0, 0, 0, 1)
        layer.add_child(background)

        var label := Label.new()
        label.name = "Label"
        label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
        label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
        label.add_theme_font_size_override("font_size", 28)
        background.add_child(label)

    var viewport_size := get_viewport().get_visible_rect().size
    var background := layer.get_node("Background") as ColorRect
    background.position = Vector2.ZERO
    background.size = viewport_size
    var probe_label := background.get_node("Label") as Label
    probe_label.position = Vector2.ZERO
    probe_label.size = viewport_size
    probe_label.text = message
    layer.visible = true
    print("[ANDROID_TITLE_PROBE] ", message.replace("\\n", " - "))


func _clear_android_title_probe() -> void:
    var layer := get_node_or_null("AndroidTitleProbe")
    if layer != null:
        layer.queue_free()


'''
    text = text.replace(helper_marker, helper + helper_marker, 1)
    path.write_text(text, encoding="utf-8")


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
    patch_touch_positions()
    patch_rom_verifier()
    print("Applied Android wrapper, TitleScreen probe, touch-position, and ROM-verifier fixes")


if __name__ == "__main__":
    main()
