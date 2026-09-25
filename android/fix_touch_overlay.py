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
    """Require a fresh accept press after keyboard/controller focus changes.

    SelectableLabel starts processing on the same frame it receives focus. On
    Android, the synthetic input bridge can leave ui_accept's custom
    just-pressed bookkeeping valid for that frame, so merely navigating onto a
    label can emit pressed. Arm activation only after focus has survived a
    process frame with ui_accept released. Mouse/touch _gui_input remains
    unchanged and can still activate an option directly.
    """
    path = ROOT / "Scripts" / "UI" / "SelectableLabel.gd"
    text = path.read_text(encoding="utf-8")

    old = '''func _ready() -> void:
\ttoggle_process(has_focus())
\tfocus_entered.connect(toggle_process.bind(true))
\tfocus_exited.connect(toggle_process.bind(false))

func _process(_delta: float) -> void:
\tif Global.multibind_action_just_pressed("ui_accept"):
\t\tpressed.emit()
\telif Global.multibind_action_just_pressed("ui_back"):
\t\tget_viewport().set_input_as_handled()
'''
    new = '''var accept_armed := false
var focus_frame := -1

func _ready() -> void:
\tif has_focus():
\t\t_on_focus_entered()
\telse:
\t\ttoggle_process(false)
\tfocus_entered.connect(_on_focus_entered)
\tfocus_exited.connect(_on_focus_exited)

func _on_focus_entered() -> void:
\tfocus_frame = Engine.get_process_frames()
\taccept_armed = false
\ttoggle_process(true)

func _on_focus_exited() -> void:
\taccept_armed = false
\ttoggle_process(false)

func _process(_delta: float) -> void:
\t# Do not allow the input frame that moved focus onto this label to also
\t# activate it. A fresh accept press is required after focus settles.
\tif not accept_armed:
\t\tif Engine.get_process_frames() > focus_frame and not Input.is_action_pressed("ui_accept"):
\t\t\taccept_armed = true
\t\treturn
\tif Global.multibind_action_just_pressed("ui_accept"):
\t\taccept_armed = false
\t\tpressed.emit()
\telif Global.multibind_action_just_pressed("ui_back"):
\t\tget_viewport().set_input_as_handled()
'''
    if old not in text:
        raise RuntimeError("Could not locate SelectableLabel focus/input block")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("Applied Android SelectableLabel fresh-accept focus guard")


def main() -> None:
    patch_touch_script()
    patch_selectable_label()


if __name__ == "__main__":
    main()
