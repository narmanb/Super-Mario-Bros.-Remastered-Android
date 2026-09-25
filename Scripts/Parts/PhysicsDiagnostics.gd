extends Node

# Temporary diagnostics used to verify Classic vs Remastered physics on Android.
# This node is attached to the persistent Settings autoload so it can inspect the
# actual live Player instance without changing player movement/input code.

var overlay: CanvasLayer
var panel: PanelContainer
var label: Label

var max_abs_x_speed := 0.0
var last_level_key := ""

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	build_overlay()

func build_overlay() -> void:
	overlay = CanvasLayer.new()
	overlay.name = "PhysicsDiagnosticsOverlay"
	overlay.layer = 100
	add_child(overlay)

	panel = PanelContainer.new()
	panel.name = "PhysicsDiagnosticsPanel"
	panel.position = Vector2(4, 34)
	panel.custom_minimum_size = Vector2(176, 88)
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.z_index = 1000

	var background := StyleBoxFlat.new()
	background.bg_color = Color(0.0, 0.0, 0.0, 0.78)
	background.border_width_left = 1
	background.border_width_top = 1
	background.border_width_right = 1
	background.border_width_bottom = 1
	background.border_color = Color(1.0, 1.0, 1.0, 0.55)
	background.content_margin_left = 4.0
	background.content_margin_top = 3.0
	background.content_margin_right = 4.0
	background.content_margin_bottom = 3.0
	panel.add_theme_stylebox_override("panel", background)
	overlay.add_child(panel)

	label = Label.new()
	label.name = "PhysicsDiagnosticsText"
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.add_theme_font_size_override("font_size", 8)
	label.add_theme_color_override("font_color", Color.WHITE)
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 2)
	label.text = "PHYSICS TEST\nWaiting for player..."
	panel.add_child(label)

func _process(_delta: float) -> void:
	if not is_instance_valid(label):
		return

	var player = get_tree().get_first_node_in_group("Players")
	if not is_instance_valid(player):
		panel.visible = false
		return

	panel.visible = true

	var level_key := ""
	if is_instance_valid(Global.current_level):
		level_key = str(Global.current_level.scene_file_path)
	if level_key != "" and level_key != last_level_key:
		last_level_key = level_key
		max_abs_x_speed = 0.0

	var current_abs_x := abs(float(player.velocity.x))
	max_abs_x_speed = max(max_abs_x_speed, current_abs_x)

	var setting_value := int(Settings.file.gameplay.physics_style)
	var setting_name := "REMASTERED" if setting_value != 0 else "CLASSIC"
	var active_dict := "UNKNOWN"
	if player.physics_dict == player.PHYSICS_PARAMETERS:
		active_dict = "REMASTERED"
	elif player.physics_dict == player.CLASSIC_PARAMETERS:
		active_dict = "CLASSIC"

	label.text = (
		"PHYSICS TEST\n"
		+ "SETTING: %s (%d)\n" % [setting_name, setting_value]
		+ "ACTIVE DICT: %s\n" % active_dict
		+ "WALK MAX: %.2f  ACCEL: %.2f\n" % [float(player.physics_params("WALK_SPEED")), float(player.physics_params("GROUND_WALK_ACCEL"))]
		+ "RUN MAX: %.2f  ACCEL: %.2f\n" % [float(player.physics_params("RUN_SPEED")), float(player.physics_params("GROUND_RUN_ACCEL"))]
		+ "JUMP IDLE: %.2f  GRAV: %.2f\n" % [float(player.physics_params("JUMP_SPEED_IDLE")), float(player.physics_params("JUMP_GRAVITY_IDLE"))]
		+ "CURRENT |X|: %.2f\n" % current_abs_x
		+ "MAX |X| THIS LEVEL: %.2f" % max_abs_x_speed
	)
