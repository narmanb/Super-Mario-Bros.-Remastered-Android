#!/usr/bin/env python3
"""Apply Android-only runtime fixes after prepare_android_export.py.

This layer keeps the upstream 1.1 sources untouched in git while adapting the
export workspace for Android:
- inject touch actions as real InputEventAction events so 1.1's custom
  multibind input tracker sees them,
- provide a ui_back alias for the upstream menus,
- run gameplay in a centered SubViewport so touch controls live in the full
  phone window/black-bar area instead of the game viewport,
- route scene changes through the Android wrapper,
- resize only the game SubViewport for NES/SP/Widescreen/Unlocked modes.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

WRAPPER_SCENE = r'''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://Scripts/Wrapper.gd" id="1_wrapper"]

[node name="Wrapper" type="Node"]
script = ExtResource("1_wrapper")

[node name="CenterContainer" type="CenterContainer" parent="."]
anchors_preset = 15
anchor_right = 1.0
anchor_bottom = 1.0
grow_horizontal = 2
grow_vertical = 2
size_flags_horizontal = 0
size_flags_vertical = 8

[node name="SubViewportContainer" type="SubViewportContainer" parent="CenterContainer"]
layout_mode = 2

[node name="SubViewport" type="SubViewport" parent="CenterContainer/SubViewportContainer"]
handle_input_locally = false
snap_2d_transforms_to_pixel = true
snap_2d_vertices_to_pixel = true
canvas_item_default_texture_filter = 0
size = Vector2i(256, 240)
render_target_update_mode = 4
'''

WRAPPER_SCRIPT = r'''extends Node

@onready var game_viewport: SubViewport = $CenterContainer/SubViewportContainer/SubViewport
@onready var game_viewport_container: SubViewportContainer = $CenterContainer/SubViewportContainer
@onready var center_container: CenterContainer = $CenterContainer

func _ready() -> void:
    # Give the root Window one frame to resolve its expanded landscape size,
    # and give the Global autoload a chance to reparent into this viewport.
    await get_tree().process_frame
    set_game_width(int(Settings.file.video.size))
    await change_scene_to("res://Scenes/Levels/Disclaimer.tscn")

func set_game_width(size_index: int) -> void:
    var max_index := Global.RESOLUTIONS.size() - 1
    size_index = clampi(size_index, 0, max_index)

    # The root Window remains 240 logical pixels tall with EXPAND aspect. Its
    # CenterContainer therefore exposes the full phone width in game pixels.
    var available_width := maxi(256, int(floor(center_container.size.x)))
    var target_width := available_width
    if size_index != max_index:
        target_width = int(Global.RESOLUTIONS[size_index].x)
        target_width = mini(target_width, available_width)

    game_viewport.size = Vector2i(target_width, 240)
    game_viewport_container.custom_minimum_size = Vector2(target_width, 240)
    game_viewport_container.size = Vector2(target_width, 240)

func change_scene_to(scene) -> void:
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

func get_game_viewport() -> SubViewport:
    return game_viewport
'''


def patch_touch_controls() -> None:
    path = ROOT / "Scripts" / "UI" / "OnScreenControls.gd"
    text = path.read_text(encoding="utf-8")

    text = text.replace(
        "func _ready() -> void:\n    _update_visibility()",
        "func _ready() -> void:\n    _ensure_ui_back_action()\n    _update_visibility()",
        1,
    )

    old_helpers = '''func _press(actions: Array[StringName]) -> void:\n    for action in actions:\n        Input.action_press(action)\n\nfunc _release(actions: Array[StringName]) -> void:\n    for action in actions:\n        Input.action_release(action)\n'''
    new_helpers = '''func _ensure_ui_back_action() -> void:\n    # 1.1 menu scripts use ui_back, while project.godot still exposes the\n    # built-in ui_cancel action. Mirror ui_cancel so physical controllers and\n    # injected touch events both follow the menu code's expected action name.\n    if not InputMap.has_action(&"ui_back"):\n        InputMap.add_action(&"ui_back", 0.2)\n        for source_event in InputMap.action_get_events(&"ui_cancel"):\n            InputMap.action_add_event(&"ui_back", source_event.duplicate())\n\nfunc _emit_action(action: StringName, pressed: bool) -> void:\n    # Input.action_press() changes state but does not pass through Global._input.\n    # 1.1's multibind_action_just_pressed() is populated from real input events,\n    # so touch controls must inject an InputEventAction through the input queue.\n    var event := InputEventAction.new()\n    event.action = action\n    event.pressed = pressed\n    event.strength = 1.0 if pressed else 0.0\n    Input.parse_input_event(event)\n\nfunc _press(actions: Array[StringName]) -> void:\n    for action in actions:\n        _emit_action(action, true)\n\nfunc _release(actions: Array[StringName]) -> void:\n    for action in actions:\n        _emit_action(action, false)\n'''
    if old_helpers not in text:
        raise RuntimeError("Could not find Run 10 touch input helpers")
    text = text.replace(old_helpers, new_helpers, 1)

    # Convert the few direct action calls (B, run lock, Start) to real events.
    text = re.sub(r'Input\.action_press\(([^\n]+)\)', r'_emit_action(\1, true)', text)
    text = re.sub(r'Input\.action_release\(([^\n]+)\)', r'_emit_action(\1, false)', text)

    # Title/menu code in 1.1 listens for ui_back; keep ui_cancel too for any
    # standard Godot controls which still consume it.
    text = text.replace(
        '    _emit_action(&"ui_cancel", true)\n',
        '    _emit_action(&"ui_cancel", true)\n    _emit_action(&"ui_back", true)\n',
        1,
    )
    text = text.replace(
        '    _emit_action(&"ui_cancel", false)\n',
        '    _emit_action(&"ui_cancel", false)\n    _emit_action(&"ui_back", false)\n',
        1,
    )
    text = text.replace(
        '&"jump_0", &"ui_accept", &"action_0", &"ui_cancel", &"run_0", &"pause",',
        '&"jump_0", &"ui_accept", &"action_0", &"ui_cancel", &"ui_back", &"run_0", &"pause",',
        1,
    )

    path.write_text(text, encoding="utf-8")


def install_wrapper() -> None:
    scene_path = ROOT / "Scenes" / "Prefabs" / "Wrapper.tscn"
    script_path = ROOT / "Scripts" / "Wrapper.gd"
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.write_text(WRAPPER_SCENE, encoding="utf-8")
    script_path.write_text(WRAPPER_SCRIPT, encoding="utf-8")


def patch_project_main_scene() -> None:
    path = ROOT / "project.godot"
    text = path.read_text(encoding="utf-8")
    text, count = re.subn(
        r'^run/main_scene=.*$',
        'run/main_scene="res://Scenes/Prefabs/Wrapper.tscn"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError("Could not patch Android main scene to Wrapper")
    path.write_text(text, encoding="utf-8")


def patch_global_scene_routing() -> None:
    path = ROOT / "Scripts" / "Classes" / "Singletons" / "Global.gd"
    text = path.read_text(encoding="utf-8")

    ready_marker = "\tlevel_theme_changed.connect(load_default_translations)\n"
    ready_patch = ready_marker + '''\t# Android keeps gameplay inside Wrapper/SubViewport so the touch overlay can\n\t# use the full device window, including pillarbox space.\n\tawait get_tree().process_frame\n\tvar android_game_viewport = get_tree().root.get_node_or_null("Wrapper/CenterContainer/SubViewportContainer/SubViewport")\n\tif android_game_viewport != null and get_parent() != android_game_viewport:\n\t\treparent(android_game_viewport)\n'''
    if ready_patch not in text:
        if ready_marker not in text:
            raise RuntimeError("Could not find Global._ready() insertion point")
        text = text.replace(ready_marker, ready_patch, 1)

    old_transition = '''\tif scene_path is String:\n\t\tget_tree().change_scene_to_file(scene_path)\n\telif scene_path is PackedScene:\n\t\tget_tree().change_scene_to_packed(scene_path)\n\tawait get_tree().scene_changed\n'''
    new_transition = '''\tvar android_wrapper = get_tree().root.get_node_or_null("Wrapper")\n\tif android_wrapper != null:\n\t\tawait android_wrapper.change_scene_to(scene_path)\n\telse:\n\t\t# Safety fallback for editor/non-wrapper execution.\n\t\tif scene_path is String:\n\t\t\tget_tree().change_scene_to_file(scene_path)\n\t\telif scene_path is PackedScene:\n\t\t\tget_tree().change_scene_to_packed(scene_path)\n\t\tawait get_tree().scene_changed\n'''
    if new_transition not in text:
        if old_transition not in text:
            raise RuntimeError("Could not find Global.transition_to_scene() scene-change block")
        text = text.replace(old_transition, new_transition, 1)

    path.write_text(text, encoding="utf-8")


def patch_window_changer() -> None:
    path = ROOT / "Scripts" / "UI" / "WindowChanger.gd"
    text = path.read_text(encoding="utf-8")

    replacement = '''func window_size_changed(new_value := 0) -> void:\n\tSettings.file.video.size = new_value\n\tvar android_wrapper = get_tree().root.get_node_or_null("Wrapper")\n\tif android_wrapper == null:\n\t\t# Settings is an autoload and can apply one frame before the main scene.\n\t\tawait get_tree().process_frame\n\t\tandroid_wrapper = get_tree().root.get_node_or_null("Wrapper")\n\tif android_wrapper != null:\n\t\tandroid_wrapper.set_game_width(int(new_value))\n\nfunc vsync_changed'''
    text, count = re.subn(
        r'func window_size_changed\(new_value := 0\) -> void:\n.*?\nfunc vsync_changed',
        replacement,
        text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("Could not patch WindowChanger.window_size_changed()")

    # Saved desktop window dimensions should never resize an Android activity.
    text, count = re.subn(
        r'func set_window_size\(value := \[\]\) -> void:\n.*?\nfunc set_value',
        'func set_window_size(_value := []) -> void:\n\tpass\n\nfunc set_value',
        text,
        count=1,
        flags=re.DOTALL,
    )
    if count != 1:
        raise RuntimeError("Could not patch WindowChanger.set_window_size()")

    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_touch_controls()
    install_wrapper()
    patch_project_main_scene()
    patch_global_scene_routing()
    patch_window_changer()
    print("Applied Android runtime input and full-window wrapper fixes")


if __name__ == "__main__":
    main()
