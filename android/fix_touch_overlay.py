#!/usr/bin/env python3
"""Final Android touch-overlay and menu-input fixes applied after runtime generation.

The Android touch scene is generated from the older working port by
fix_mobile_runtime.py. Keep the overlay on the root Window rather than the
game SubViewport, preserve a full-landscape root coordinate space even when
levels change display settings, mirror pressed actions into SMB1R 1.1's
custom just-pressed bookkeeping so pause menus continue to receive touch input
while the SceneTree is paused, and prevent a focus-navigation event from being
mistaken for activation by a newly focused SelectableLabel.
"""

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
    _enforce_full_window_coordinate_space()

func _ready() -> void:
    _ensure_ui_back_action()
    _enforce_full_window_coordinate_space()
    _update_visibility()

func _enforce_full_window_coordinate_space() -> void:
    # SMB1R changes Window content scaling when a level/aspect ratio becomes
    # active. That is correct on desktop but on Android it also makes this
    # CanvasLayer inherit the centered game area's width, pulling both touch
    # clusters into the middle of the phone. The actual game renders in its
    # own SubViewport, so keep the root Window at the fixed 256x240 reference
    # size with EXPAND; Godot then exposes the extra landscape width to these
    # left/right anchored Controls while the Wrapper independently controls
    # the game viewport width.
    var root := get_tree().root
    custom_viewport = root
    if root.content_scale_size != Vector2i(256, 240):
        root.content_scale_size = Vector2i(256, 240)
    if root.content_scale_mode != Window.CONTENT_SCALE_MODE_CANVAS_ITEMS:
        root.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
    if root.content_scale_aspect != Window.CONTENT_SCALE_ASPECT_EXPAND:
        root.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_EXPAND
'''
    if ready_marker not in text:
        raise RuntimeError("Could not locate OnScreenControls._ready()")
    text = text.replace(ready_marker, ready_replacement, 1)

    process_old = '''func _process(_delta: float) -> void:
    _update_visibility()
'''
    process_new = '''func _process(_delta: float) -> void:
    _enforce_full_window_coordinate_space()
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

func _process(_delta: float) -> void:
\t# Direct mouse/touch activation is independent of the controller debounce.
\tif Input.is_action_just_pressed("mb_left") and accept_mouse_clicks:
\t\tpressed.emit()
\t\treturn

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


def main() -> None:
    patch_touch_script()
    patch_selectable_label()


if __name__ == "__main__":
    main()
