#!/usr/bin/env python3
"""Android-only runtime fixes for SMB1R 1.1."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_COMMIT = "61fe0a6464101981cbee56701955fc0005f59664"
OLD_RAW = f"https://raw.githubusercontent.com/mircowuffwuff/super-mario-bros.-remastered-android/{OLD_COMMIT}"
TOUCH_ASSETS = (
    "A.png", "AHeld.png", "B.png", "BHeld.png", "Down.png", "DownHeld.png",
    "Left.png", "LeftHeld.png", "Right.png", "RightHeld.png", "RunLock.png",
    "RunLockOn.png", "Start.png", "StartHeld.png", "Up.png", "UpHeld.png",
)

TOUCH_SCRIPT = r'''extends CanvasLayer

const LEFT = preload("res://Assets/Sprites/UI/OnScreenControls/Left.png")
const LEFT_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/LeftHeld.png")
const RIGHT = preload("res://Assets/Sprites/UI/OnScreenControls/Right.png")
const RIGHT_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/RightHeld.png")
const UP = preload("res://Assets/Sprites/UI/OnScreenControls/Up.png")
const UP_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/UpHeld.png")
const DOWN = preload("res://Assets/Sprites/UI/OnScreenControls/Down.png")
const DOWN_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/DownHeld.png")
const A = preload("res://Assets/Sprites/UI/OnScreenControls/A.png")
const A_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/AHeld.png")
const B = preload("res://Assets/Sprites/UI/OnScreenControls/B.png")
const B_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/BHeld.png")
const START = preload("res://Assets/Sprites/UI/OnScreenControls/Start.png")
const START_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/StartHeld.png")
const RUN_LOCK = preload("res://Assets/Sprites/UI/OnScreenControls/RunLock.png")
const RUN_LOCK_ON = preload("res://Assets/Sprites/UI/OnScreenControls/RunLockOn.png")
const FAKE_JOYPAD_PREFIXES := ["uinput"]

@onready var left = $Control/LeftSprite
@onready var right = $Control/RightSprite
@onready var up = $Control/UpSprite
@onready var down = $Control/DownSprite
@onready var a = $Control2/ASprite
@onready var b = $Control2/BSprite
@onready var start = $Control2/StartSprite
@onready var run_lock = $Control2/RunLockSprite
var run_lock_on := false

func _ready() -> void:
    _ensure_ui_back_action()
    _update_visibility()

func _process(_delta: float) -> void:
    _update_visibility()

func _ensure_ui_back_action() -> void:
    # 1.1 menu scripts listen for ui_back, while project.godot exposes ui_cancel.
    if not InputMap.has_action(&"ui_back"):
        InputMap.add_action(&"ui_back", 0.2)
        for source_event in InputMap.action_get_events(&"ui_cancel"):
            InputMap.action_add_event(&"ui_back", source_event.duplicate())

func _update_visibility() -> void:
    var should_be_visible := not _has_real_controller()
    if visible and not should_be_visible:
        _release_all_actions()
        run_lock_on = false
        run_lock.texture = RUN_LOCK
    visible = should_be_visible

func _has_real_controller() -> bool:
    for device_id in Input.get_connected_joypads():
        var joy_name := Input.get_joy_name(device_id).to_lower()
        var fake := false
        for prefix in FAKE_JOYPAD_PREFIXES:
            if joy_name.begins_with(prefix):
                fake = true
                break
        if not fake:
            return true
    return false

func _haptic() -> void:
    Input.vibrate_handheld(12, 0.45)

func _emit_action(action: StringName, pressed: bool) -> void:
    # 1.1's just-pressed tracker is populated from Global._input(), so use a
    # real queued action event instead of Input.action_press()/release().
    var event := InputEventAction.new()
    event.action = action
    event.pressed = pressed
    event.strength = 1.0 if pressed else 0.0
    Input.parse_input_event(event)

func _press(actions: Array[StringName]) -> void:
    for action in actions:
        _emit_action(action, true)

func _release(actions: Array[StringName]) -> void:
    for action in actions:
        _emit_action(action, false)

func on_west_pressed() -> void:
    left.texture = LEFT_HELD
    _haptic()
    _press([&"move_left_0", &"ui_left"])
func on_west_released() -> void:
    left.texture = LEFT
    _release([&"move_left_0", &"ui_left"])
func on_east_pressed() -> void:
    right.texture = RIGHT_HELD
    _haptic()
    _press([&"move_right_0", &"ui_right"])
func on_east_released() -> void:
    right.texture = RIGHT
    _release([&"move_right_0", &"ui_right"])
func on_north_pressed() -> void:
    up.texture = UP_HELD
    _haptic()
    _press([&"move_up_0", &"ui_up"])
func on_north_released() -> void:
    up.texture = UP
    _release([&"move_up_0", &"ui_up"])
func on_south_pressed() -> void:
    down.texture = DOWN_HELD
    _haptic()
    _press([&"move_down_0", &"ui_down"])
func on_south_released() -> void:
    down.texture = DOWN
    _release([&"move_down_0", &"ui_down"])
func on_a_pressed() -> void:
    a.texture = A_HELD
    _haptic()
    _press([&"jump_0", &"ui_accept"])
func on_a_released() -> void:
    a.texture = A
    _release([&"jump_0", &"ui_accept"])
func on_b_pressed() -> void:
    b.texture = B_HELD
    _haptic()
    _press([&"action_0", &"ui_cancel", &"ui_back"])
    if not run_lock_on:
        _emit_action(&"run_0", true)
func on_b_released() -> void:
    b.texture = B
    _release([&"action_0", &"ui_cancel", &"ui_back"])
    if not run_lock_on:
        _emit_action(&"run_0", false)
func on_run_lock_pressed() -> void:
    run_lock_on = not run_lock_on
    run_lock.texture = RUN_LOCK_ON if run_lock_on else RUN_LOCK
    _emit_action(&"run_0", run_lock_on)
    _haptic()
func on_start_pressed() -> void:
    start.texture = START_HELD
    _haptic()
    _emit_action(&"pause", true)
func on_start_released() -> void:
    start.texture = START
    _emit_action(&"pause", false)
func on_select_pressed() -> void:
    pass
func on_select_released() -> void:
    pass

func _release_all_actions() -> void:
    _release([
        &"move_left_0", &"move_right_0", &"move_up_0", &"move_down_0",
        &"ui_left", &"ui_right", &"ui_up", &"ui_down", &"jump_0", &"ui_accept",
        &"action_0", &"ui_cancel", &"ui_back", &"run_0", &"pause",
    ])

func _exit_tree() -> void:
    _release_all_actions()
'''

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
    await get_tree().process_frame
    set_game_width(int(Settings.file.video.size))
    await change_scene_to("res://Scenes/Levels/Disclaimer.tscn")

func set_game_width(size_index: int) -> void:
    var max_index := Global.RESOLUTIONS.size() - 1
    size_index = clampi(size_index, 0, max_index)
    var available_width := maxi(256, int(floor(center_container.size.x)))
    var target_width := available_width
    if size_index != max_index:
        target_width = mini(int(Global.RESOLUTIONS[size_index].x), available_width)
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


def download_text(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def install_touch_controls() -> None:
    asset_dir = ROOT / "Assets" / "Sprites" / "UI" / "OnScreenControls"
    asset_dir.mkdir(parents=True, exist_ok=True)
    for name in TOUCH_ASSETS:
        dst = asset_dir / name
        if not dst.exists() or dst.stat().st_size == 0:
            urllib.request.urlretrieve(f"{OLD_RAW}/Assets/Sprites/UI/OnScreenControls/{name}", dst)
    scene = download_text(f"{OLD_RAW}/Scenes/Prefabs/UI/OnScreenControls.tscn")
    # The old scene has a few built-in action properties. Remove them so each
    # press is emitted exactly once by the corrected 1.1-aware script.
    scene = re.sub(r'^action = .*\n', '', scene, flags=re.MULTILINE)
    (ROOT / "Scenes" / "Prefabs" / "UI" / "OnScreenControls.tscn").write_text(scene, encoding="utf-8")
    (ROOT / "Scripts" / "UI" / "OnScreenControls.gd").write_text(TOUCH_SCRIPT, encoding="utf-8")


def install_wrapper() -> None:
    (ROOT / "Scenes" / "Prefabs" / "Wrapper.tscn").write_text(WRAPPER_SCENE, encoding="utf-8")
    (ROOT / "Scripts" / "Wrapper.gd").write_text(WRAPPER_SCRIPT, encoding="utf-8")


def patch_project() -> None:
    path = ROOT / "project.godot"
    text = path.read_text(encoding="utf-8")
    text, n = re.subn(r'^run/main_scene=.*$', 'run/main_scene="res://Scenes/Prefabs/Wrapper.tscn"', text, count=1, flags=re.MULTILINE)
    if n != 1:
        raise RuntimeError("Could not patch Android main scene")
    autoload = 'OnScreenControls="*res://Scenes/Prefabs/UI/OnScreenControls.tscn"'
    if autoload not in text:
        marker = "\n[debug]\n"
        if marker not in text:
            raise RuntimeError("Could not locate end of [autoload]")
        text = text.replace(marker, f"\n{autoload}\n{marker}", 1)
    path.write_text(text, encoding="utf-8")


def patch_global() -> None:
    path = ROOT / "Scripts" / "Classes" / "Singletons" / "Global.gd"
    text = path.read_text(encoding="utf-8")
    marker = "\tlevel_theme_changed.connect(load_default_translations)\n"
    addition = marker + '''\tawait get_tree().process_frame\n\tvar android_game_viewport = get_tree().root.get_node_or_null("Wrapper/CenterContainer/SubViewportContainer/SubViewport")\n\tif android_game_viewport != null and get_parent() != android_game_viewport:\n\t\treparent(android_game_viewport)\n'''
    if marker not in text:
        raise RuntimeError("Could not patch Global._ready()")
    text = text.replace(marker, addition, 1)
    old = '''\tif scene_path is String:\n\t\tget_tree().change_scene_to_file(scene_path)\n\telif scene_path is PackedScene:\n\t\tget_tree().change_scene_to_packed(scene_path)\n\tawait get_tree().scene_changed\n'''
    new = '''\tvar android_wrapper = get_tree().root.get_node_or_null("Wrapper")\n\tif android_wrapper != null:\n\t\tawait android_wrapper.change_scene_to(scene_path)\n\telse:\n\t\tif scene_path is String:\n\t\t\tget_tree().change_scene_to_file(scene_path)\n\t\telif scene_path is PackedScene:\n\t\t\tget_tree().change_scene_to_packed(scene_path)\n\t\tawait get_tree().scene_changed\n'''
    if old not in text:
        raise RuntimeError("Could not patch Global.transition_to_scene()")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_window_changer() -> None:
    path = ROOT / "Scripts" / "UI" / "WindowChanger.gd"
    text = path.read_text(encoding="utf-8")
    replacement = '''func window_size_changed(new_value := 0) -> void:\n\tSettings.file.video.size = new_value\n\tvar android_wrapper = get_tree().root.get_node_or_null("Wrapper")\n\tif android_wrapper == null:\n\t\tawait get_tree().process_frame\n\t\tandroid_wrapper = get_tree().root.get_node_or_null("Wrapper")\n\tif android_wrapper != null:\n\t\tandroid_wrapper.set_game_width(int(new_value))\n\nfunc vsync_changed'''
    text, n = re.subn(r'func window_size_changed\(new_value := 0\) -> void:\n.*?\nfunc vsync_changed', replacement, text, count=1, flags=re.DOTALL)
    if n != 1:
        raise RuntimeError("Could not patch window_size_changed()")
    text, n = re.subn(r'func set_window_size\(value := \[\]\) -> void:\n.*?\nfunc set_value', 'func set_window_size(_value := []) -> void:\n\tpass\n\nfunc set_value', text, count=1, flags=re.DOTALL)
    if n != 1:
        raise RuntimeError("Could not patch set_window_size()")
    path.write_text(text, encoding="utf-8")


def patch_drop_shadows() -> None:
    path = ROOT / "Scripts" / "Parts" / "DropShadowRenderer.gd"
    text = path.read_text(encoding="utf-8")
    old = '''\tif is_instance_valid(get_tree().current_scene):\n\t\tif is_instance_valid(get_tree().current_scene.get_viewport().get_camera_2d()):\n\t\t\t$SubViewportContainer/SubViewport.world_2d = get_tree().current_scene.get_viewport().get_camera_2d().get_world_2d()\n\t\telse:\n\t\t\treturn\n\telse:\n\t\treturn#\n'''
    new = '''\tvar source_viewport := get_viewport()\n\tif not is_instance_valid(source_viewport.get_camera_2d()):\n\t\treturn\n\t$SubViewportContainer/SubViewport.world_2d = source_viewport.get_camera_2d().get_world_2d()\n'''
    if old not in text:
        raise RuntimeError("Could not patch DropShadowRenderer")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    install_touch_controls()
    install_wrapper()
    patch_project()
    patch_global()
    patch_window_changer()
    patch_drop_shadows()
    print("Applied Android wrapper and 1.1 touch-input fixes")


if __name__ == "__main__":
    main()
