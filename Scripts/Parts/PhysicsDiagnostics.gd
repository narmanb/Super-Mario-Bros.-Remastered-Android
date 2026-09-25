extends Node

# Temporary diagnostics used to verify Classic vs Remastered physics on Android.
# The manager persists under the Settings autoload, but the CanvasLayer itself is
# attached to the live Player so it renders in the exact same viewport as Mario.

var overlay: CanvasLayer
var panel: PanelContainer
var label: Label
var attached_player: Node

var max_abs_x_speed := 0.0
var last_level_instance_id := 0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS

func _process(_delta: float) -> void:
	var player = get_tree().get_first_node_in_group("Players")
	if not is_instance_valid(player):
		attached_player = null
		return

	if player != attached_player or not is_instance_valid(overlay):
		attach_overlay_to_player(player)

	if not is_instance_valid(label):
		return

	var level_instance_id := 0
	if is_instance_valid(Global.current_level):
		level_instance_id = int(Global.current_level.get_instance_id())
	if level_instance_id != 0 and level_instance_id != last_level_instance_id:
		last_level_instance_id = level_instance_id
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

func attach_overlay_to_player(player: Node) -> void:
	if is_instance_valid(overlay):
		overlay.queue_free()

	attached_player = player
	overlay = CanvasLayer.new()
	overlay.name = "PhysicsDiagnosticsOverlay"
	overlay.layer = 100
	player.add_child(overlay)

	panel = PanelContainer.new()
	panel.name = "PhysicsDiagnosticsPanel"
	panel.position = Vector2(4, 34)
	panel.custom_minimum_size = Vector2(176, 88)
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.z_index = 1000

	var background := StyleBoxFlat.new()
	background.bg_color = Color(0.0, 0.0, 0.0, 0.82)
	background.border_width_left = 1
	background.border_width_top = 1
	background.border_width_right = 1
	background.border_width_bottom = 1
	background.border_color = Color(1.0, 1.0, 1.0, 0.75)
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
	label.text = "PHYSICS TEST\nPLAYER FOUND\nReading live values..."
	panel.add_child(label)
