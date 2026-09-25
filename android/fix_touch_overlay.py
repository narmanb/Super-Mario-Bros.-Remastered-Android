#!/usr/bin/env python3
"""Android touch layout and menu input fixes applied after runtime generation."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_touch_script() -> None:
    path = ROOT / "Scripts" / "UI" / "OnScreenControls.gd"
    text = path.read_text(encoding="utf-8")

    ready_marker = '''func _ready() -> void:
    _ensure_ui_back_action()
    _update_visibility()
'''
    ready_replacement = '''func _enter_tree() -> void:
    # The controls are an Android-wide overlay, not part of the centered game
    # SubViewport. Keep them attached to the root Window.
    process_mode = Node.PROCESS_MODE_ALWAYS
    custom_viewport = get_tree().root

func _ready() -> void:
    _ensure_ui_back_action()
    _position_touch_controls()
    _update_visibility()

func _position_touch_controls() -> void:
    # Convert the actual window corners into root canvas coordinates. Both
    # the sprites and TouchScreenButton hit shapes share these parent Controls.
    var root := get_tree().root
    custom_viewport = root
    var screen_to_canvas := root.get_screen_transform().affine_inverse()
    var top_left := screen_to_canvas * Vector2.ZERO
    var bottom_right := screen_to_canvas * Vector2(DisplayServer.window_get_size())
    # Leave room for the left button; -10 clipped it on the S25+.
    $Control.position = Vector2(top_left.x + 8.0, bottom_right.y - 141.0)
    $Control2.position = Vector2(bottom_right.x - 105.0, bottom_right.y - 141.0)
'''
    if ready_marker not in text:
        raise RuntimeError("Could not locate OnScreenControls._ready()")
    text = text.replace(ready_marker, ready_replacement, 1)

    process_old = '''func _process(_delta: float) -> void:
    _update_visibility()
'''
    process_new = '''func _process(_delta: float) -> void:
    _position_touch_controls()
    _update_visibility()
'''
    if process_old not in text:
        raise RuntimeError("Could not locate OnScreenControls._process()")
    text = text.replace(process_old, process_new, 1)

    emit_old = '''func _emit_action(action: StringName, pressed: bool) -> void:
    # 1.1's just-pressed tracker is populated from Global._input(), so use a
    # real queued action event instead of Input.action_press()/release().
    var event := InputEventAction.new()
    event.action = action
    event.pressed = pressed
    event.strength = 1.0 if pressed else 0.0
    Input.parse_input_event(event)
'''
    emit_new = '''func _emit_action(action: StringName, pressed: bool) -> void:
    # StoryPause keeps processing while SceneTree.paused is true, but Global's
    # normal _input path is not reliable for synthetic touch events in that
    # state. Mirror a press directly into the exact dictionaries read by
    # Global.multibind_action_just_pressed(), then also queue the real action
    # event for normal gameplay/input consumers.
    if pressed:
        Global.unpressed_buttons[action] = false
        Global.process_multibind_pressed_buttons[action] = Engine.get_process_frames()
        Global.physics_multibind_pressed_buttons[action] = Engine.get_physics_frames() + 1

    var event := InputEventAction.new()
    event.action = action
    event.pressed = pressed
    event.strength = 1.0 if pressed else 0.0
    Input.parse_input_event(event)
'''
    if emit_old not in text:
        raise RuntimeError("Could not locate OnScreenControls._emit_action()")
    text = text.replace(emit_old, emit_new, 1)

    path.write_text(text, encoding="utf-8")
    print("Applied Android touch overlay full-window and paused-input fixes")


def patch_touch_scene_layout() -> None:
    """Replace the older port's logical-screen anchors with absolute parents."""
    path = ROOT / "Scenes" / "Prefabs" / "UI" / "OnScreenControls.tscn"
    scene = path.read_text(encoding="utf-8")
    old_left = '''[node name="Control" type="Control" parent="."]
layout_mode = 3
anchors_preset = 2
anchor_top = 1.0
anchor_bottom = 1.0
offset_left = -10.0
offset_top = -141.0
offset_right = 131.0
grow_vertical = 0
'''
    new_left = '''[node name="Control" type="Control" parent="."]
layout_mode = 3
offset_right = 141.0
offset_bottom = 141.0
'''
    old_right = '''[node name="Control2" type="Control" parent="."]
layout_mode = 3
anchors_preset = 3
anchor_left = 1.0
anchor_top = 1.0
anchor_right = 1.0
anchor_bottom = 1.0
offset_left = -105.0
offset_top = -141.0
offset_right = 10.0
grow_horizontal = 0
grow_vertical = 0
'''
    new_right = '''[node name="Control2" type="Control" parent="."]
layout_mode = 3
offset_right = 115.0
offset_bottom = 141.0
'''
    if scene.count(old_left) != 1 or scene.count(old_right) != 1:
        raise RuntimeError("Could not locate generated touch-control anchors")
    path.write_text(scene.replace(old_left, new_left, 1).replace(old_right, new_right, 1), encoding="utf-8")


def patch_selectable_label() -> None:
    """Require a fresh accept press after a SelectableLabel receives focus."""
    path = ROOT / "Scripts" / "UI" / "SelectableLabel.gd"
    # This is intentionally an Android-export replacement rather than a
    # fragile textual edit. The scene itself owns focus-entered/focus-exited
    # connections to toggle_process(); this script simply makes that method
    # arm acceptance only after focus has settled and ui_accept is released.
    replacement = '''extends Label

signal pressed

@export var accept_mouse_clicks := false

var accept_armed := false
var focus_frame := -1

func _ready() -> void:
\tif accept_mouse_clicks == false:
\t\tmouse_filter = Control.MOUSE_FILTER_IGNORE

func _gui_input(event: InputEvent) -> void:
\t# Only a pointer event delivered to this label can click it. The D-pad's
\t# emulated mouse press must not click whichever label gained focus.
\tif accept_mouse_clicks and event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
\t\tpressed.emit()
\t\taccept_event()

func _process(_delta: float) -> void:
\t# Do not let the same input frame that moved focus onto this label activate
\t# it. Require focus to survive at least one process frame with ui_accept
\t# released, then accept the next deliberate press.
\tif not accept_armed:
\t\tif Engine.get_process_frames() > focus_frame and not Input.is_action_pressed("ui_accept"):
\t\t\taccept_armed = true
\t\treturn

\tif Global.multibind_action_just_pressed("ui_accept"):
\t\taccept_armed = false
\t\tpressed.emit()

func toggle_process(enabled := false) -> void:
\tif enabled:
\t\tfocus_frame = Engine.get_process_frames()
\t\taccept_armed = false
\telse:
\t\taccept_armed = false
\tset_process(enabled)
'''
    path.write_text(replacement, encoding="utf-8")
    print("Applied Android SelectableLabel fresh-accept focus guard")


def patch_custom_level_container() -> None:
    """A D-pad touch must not click the newly focused level row."""
    path = ROOT / "Scripts" / "UI" / "CustomLevelContainer.gd"
    text = path.read_text(encoding="utf-8")
    old = '''func _process(_delta: float) -> void:
\tif (Global.multibind_action_just_pressed("ui_accept") || Input.is_action_just_pressed("mb_left")) and visible:
\t\tselected.emit(self)
'''
    new = '''func _process(_delta: float) -> void:
\tif Global.multibind_action_just_pressed("ui_accept") and visible:
\t\tselected.emit(self)

func _gui_input(event: InputEvent) -> void:
\t# Mouse clicks are local to this row. A touch on the D-pad can also create
\t# mb_left, but it must never activate the row that just received focus.
\tif visible and event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT and event.pressed:
\t\tselected.emit(self)
\t\taccept_event()
'''
    if text.count(old) != 1:
        raise RuntimeError("Could not locate CustomLevelContainer selection polling")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def install_paused_controller_bridge() -> None:
    """Stamp physical controller input while Global is paused with the game."""
    path = ROOT / "Scripts" / "Classes" / "Singletons" / "AndroidPauseInputBridge.gd"
    path.write_text('''extends Node

func _ready() -> void:
\tprocess_mode = Node.PROCESS_MODE_ALWAYS

func _process(_delta: float) -> void:
\tif get_tree().paused:
\t\t# Global._process() normally releases its multibind axis latch.
\t\tGlobal.handle_input()

func _input(event: InputEvent) -> void:
\tif not get_tree().paused or not event.is_action_type() or not event.is_pressed():
\t\treturn
\t# OnScreenControls already stamps InputEventAction presses, including while
\t# paused. Only physical controller input needs this bridge.
\tif not (event is InputEventJoypadButton or event is InputEventJoypadMotion):
\t\treturn
\tfor action in InputMap.get_actions():
\t\tif event.is_action_pressed(action):
\t\t\tif event is InputEventJoypadMotion and not Global.unpressed_buttons.get(action, true):
\t\t\t\tcontinue
\t\t\tGlobal.unpressed_buttons[action] = false
\t\t\tGlobal.process_multibind_pressed_buttons[action] = Engine.get_process_frames()
\t\t\tGlobal.physics_multibind_pressed_buttons[action] = Engine.get_physics_frames() + 1
''', encoding="utf-8")

    project_path = ROOT / "project.godot"
    project = project_path.read_text(encoding="utf-8")
    marker = '\n[debug]\n'
    autoload = 'AndroidPauseInputBridge="*res://Scripts/Classes/Singletons/AndroidPauseInputBridge.gd"'
    if project.count(marker) != 1 or autoload in project:
        raise RuntimeError("Could not register Android pause input bridge")
    project_path.write_text(project.replace(marker, f'\n{autoload}\n{marker}', 1), encoding="utf-8")


def patch_level_resolution() -> None:
    """The Android Wrapper controls game width; levels must not scale the root."""
    path = ROOT / "Scripts" / "Classes" / "LevelClass.gd"
    text = path.read_text(encoding="utf-8")
    for name in ("apply_resolution_enforcement", "reset_resolution"):
        marker = f"func {name}() -> void:\n"
        if text.count(marker) != 1:
            raise RuntimeError(f"Could not locate LevelClass.{name}()")
        text = text.replace(marker, marker + '\tif OS.has_feature("android"):\n\t\treturn\n', 1)
    path.write_text(text, encoding="utf-8")
    print("Kept level resolution changes inside the Android game viewport")


def main() -> None:
    patch_touch_script()
    patch_touch_scene_layout()
    patch_selectable_label()
    patch_custom_level_container()
    install_paused_controller_bridge()
    patch_level_resolution()


if __name__ == "__main__":
    main()
