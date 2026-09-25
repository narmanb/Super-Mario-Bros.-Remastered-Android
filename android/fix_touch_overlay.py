#!/usr/bin/env python3
"""Final Android touch-overlay fixes applied after runtime generation.

The Android touch scene is generated from the older working port by
fix_mobile_runtime.py. Keep the overlay on the root Window rather than the
256x240 game SubViewport, and mirror pressed actions into SMB1R 1.1's custom
just-pressed bookkeeping so pause menus continue to receive touch input while
the SceneTree is paused.
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
    # SubViewport. Explicitly bind the CanvasLayer to the root Window so a
    # level switching the game viewport back to 256x240 cannot pull the touch
    # controls into the middle of the screen.
    process_mode = Node.PROCESS_MODE_ALWAYS
    custom_viewport = get_tree().root

func _ready() -> void:
    _ensure_ui_back_action()
    _update_visibility()
'''
    if ready_marker not in text:
        raise RuntimeError("Could not locate OnScreenControls._ready()")
    text = text.replace(ready_marker, ready_replacement, 1)

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
    print("Applied Android touch overlay viewport and paused-input fixes")


def main() -> None:
    patch_touch_script()


if __name__ == "__main__":
    main()
