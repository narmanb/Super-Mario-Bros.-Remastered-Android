#!/usr/bin/env python3
"""Install temporary physics diagnostics into the proven Android touch overlay."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    path = ROOT / "Scripts" / "UI" / "OnScreenControls.gd"
    text = path.read_text(encoding="utf-8")

    var_marker = "var run_lock_on := false\n"
    var_addition = '''var run_lock_on := false
var physics_diag_panel: PanelContainer
var physics_diag_label: Label
var physics_diag_max_abs_x := 0.0
var physics_diag_level_id := 0
'''
    if text.count(var_marker) != 1:
        raise RuntimeError("Could not locate OnScreenControls diagnostic variable marker")
    text = text.replace(var_marker, var_addition, 1)

    ready_old = '''func _ready() -> void:
    _ensure_ui_back_action()
    _position_touch_controls()
    _update_visibility()
'''
    ready_new = '''func _ready() -> void:
    _ensure_ui_back_action()
    _build_physics_diagnostics()
    _position_touch_controls()
    _update_visibility()
    _update_physics_diagnostics()
'''
    if text.count(ready_old) != 1:
        raise RuntimeError("Could not locate patched OnScreenControls._ready()")
    text = text.replace(ready_old, ready_new, 1)

    process_old = '''func _process(_delta: float) -> void:
    _position_touch_controls()
    _update_visibility()
'''
    process_new = '''func _process(_delta: float) -> void:
    _position_touch_controls()
    _update_visibility()
    _update_physics_diagnostics()
'''
    if text.count(process_old) != 1:
        raise RuntimeError("Could not locate patched OnScreenControls._process()")
    text = text.replace(process_old, process_new, 1)

    position_marker = '''    $Control.position = Vector2(top_left.x + 8.0, bottom_right.y - 141.0)
    $Control2.position = Vector2(bottom_right.x - 105.0, bottom_right.y - 141.0)
'''
    position_replacement = '''    $Control.position = Vector2(top_left.x + 8.0, bottom_right.y - 141.0)
    $Control2.position = Vector2(bottom_right.x - 105.0, bottom_right.y - 141.0)
    if is_instance_valid(physics_diag_panel):
        var game_width := 256.0
        var game_viewport = root.get_node_or_null("Wrapper/CenterContainer/SubViewportContainer/SubViewport")
        if game_viewport != null:
            game_width = float(game_viewport.size.x)
        var logical_width := bottom_right.x - top_left.x
        var game_left := top_left.x + maxf(0.0, (logical_width - game_width) * 0.5)
        physics_diag_panel.position = Vector2(game_left + 4.0, top_left.y + 34.0)
'''
    if text.count(position_marker) != 1:
        raise RuntimeError("Could not locate touch-control positioning marker")
    text = text.replace(position_marker, position_replacement, 1)

    visibility_old = '''func _update_visibility() -> void:
    var should_be_visible := not _has_real_controller()
    if visible and not should_be_visible:
        _release_all_actions()
        run_lock_on = false
        run_lock.texture = RUN_LOCK
    visible = should_be_visible
'''
    visibility_new = '''func _update_visibility() -> void:
    var should_be_visible := not _has_real_controller()
    if $Control.visible and not should_be_visible:
        _release_all_actions()
        run_lock_on = false
        run_lock.texture = RUN_LOCK
    # Keep this CanvasLayer alive because the physics readout is hosted here.
    # Only the actual touch-control groups disappear when a real controller is used.
    visible = true
    $Control.visible = should_be_visible
    $Control2.visible = should_be_visible
'''
    if text.count(visibility_old) != 1:
        raise RuntimeError("Could not locate OnScreenControls._update_visibility()")
    text = text.replace(visibility_old, visibility_new, 1)

    diagnostics = r'''

func _build_physics_diagnostics() -> void:
    # Disable the earlier experimental diagnostics manager; this version lives
    # directly in the same CanvasLayer that already renders the touch controls.
    var legacy = Settings.get_node_or_null("PhysicsDiagnostics")
    if legacy != null:
        legacy.set_process(false)

    physics_diag_panel = PanelContainer.new()
    physics_diag_panel.name = "PhysicsDiagnosticsPanel"
    physics_diag_panel.custom_minimum_size = Vector2(190, 92)
    physics_diag_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
    physics_diag_panel.z_index = 5000

    var background := StyleBoxFlat.new()
    background.bg_color = Color(0.0, 0.0, 0.0, 0.90)
    background.border_width_left = 1
    background.border_width_top = 1
    background.border_width_right = 1
    background.border_width_bottom = 1
    background.border_color = Color(1.0, 1.0, 0.0, 1.0)
    background.content_margin_left = 4.0
    background.content_margin_top = 3.0
    background.content_margin_right = 4.0
    background.content_margin_bottom = 3.0
    physics_diag_panel.add_theme_stylebox_override("panel", background)
    add_child(physics_diag_panel)

    physics_diag_label = Label.new()
    physics_diag_label.name = "PhysicsDiagnosticsText"
    physics_diag_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
    physics_diag_label.add_theme_font_size_override("font_size", 7)
    physics_diag_label.add_theme_color_override("font_color", Color.WHITE)
    physics_diag_label.add_theme_color_override("font_outline_color", Color.BLACK)
    physics_diag_label.add_theme_constant_override("outline_size", 2)
    physics_diag_label.text = "PHYSICS DIAGNOSTICS\nTOUCH LAYER OK\nWAITING FOR PLAYER..."
    physics_diag_panel.add_child(physics_diag_label)

func _find_physics_player():
    var player = get_tree().get_first_node_in_group("Players")
    if is_instance_valid(player):
        return player
    var game_viewport = get_tree().root.get_node_or_null("Wrapper/CenterContainer/SubViewportContainer/SubViewport")
    if game_viewport != null:
        player = game_viewport.find_child("Player", true, false)
    return player

func _update_physics_diagnostics() -> void:
    if not is_instance_valid(physics_diag_label):
        return

    var player = _find_physics_player()
    if not is_instance_valid(player):
        physics_diag_label.text = "PHYSICS DIAGNOSTICS\nTOUCH LAYER OK\nWAITING FOR PLAYER..."
        return

    var level_id := 0
    if is_instance_valid(Global.current_level):
        level_id = int(Global.current_level.get_instance_id())
    elif is_instance_valid(player.owner):
        level_id = int(player.owner.get_instance_id())
    else:
        level_id = int(player.get_instance_id())

    if level_id != physics_diag_level_id:
        physics_diag_level_id = level_id
        physics_diag_max_abs_x = 0.0

    var current_abs_x := abs(float(player.velocity.x))
    physics_diag_max_abs_x = maxf(physics_diag_max_abs_x, current_abs_x)

    var setting_value := int(Settings.file.gameplay.physics_style)
    var setting_name := "REMASTERED" if setting_value != 0 else "CLASSIC"
    var active_dict := "UNKNOWN"
    if player.physics_dict == player.PHYSICS_PARAMETERS:
        active_dict = "REMASTERED"
    elif player.physics_dict == player.CLASSIC_PARAMETERS:
        active_dict = "CLASSIC"

    physics_diag_label.text = (
        "PHYSICS DIAGNOSTICS\n"
        + "SETTING: %s (%d)\n" % [setting_name, setting_value]
        + "ACTIVE: %s\n" % active_dict
        + "WALK: %.2f  ACCEL: %.2f\n" % [float(player.physics_params("WALK_SPEED")), float(player.physics_params("GROUND_WALK_ACCEL"))]
        + "RUN MAX: %.2f  ACCEL: %.2f\n" % [float(player.physics_params("RUN_SPEED")), float(player.physics_params("GROUND_RUN_ACCEL"))]
        + "JUMP: %.2f  GRAV: %.2f\n" % [float(player.physics_params("JUMP_SPEED_IDLE")), float(player.physics_params("JUMP_GRAVITY_IDLE"))]
        + "CURRENT |X|: %.2f\n" % current_abs_x
        + "MAX |X| THIS LEVEL: %.2f" % physics_diag_max_abs_x
    )
'''

    text = text.rstrip() + diagnostics + "\n"
    path.write_text(text, encoding="utf-8")
    print("Installed physics diagnostics into the proven OnScreenControls CanvasLayer")


if __name__ == "__main__":
    main()
