extends Label

var max_abs_x_speed := 0.0
var last_level_id := 0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_update_text()

func _process(_delta: float) -> void:
	_update_text()

func _find_player():
	var player = get_tree().get_first_node_in_group("Players")
	if is_instance_valid(player):
		return player
	var viewport = get_tree().root.get_node_or_null("Wrapper/CenterContainer/SubViewportContainer/SubViewport")
	if viewport != null:
		player = viewport.find_child("Player", true, false)
	return player

func _update_text() -> void:
	var player = _find_player()
	if not is_instance_valid(player):
		text = "PHYSICS DIAGNOSTICS\nTOUCH LAYER OK\nWAITING FOR PLAYER..."
		return

	var level_id := 0
	if is_instance_valid(Global.current_level):
		level_id = int(Global.current_level.get_instance_id())
	elif is_instance_valid(player.owner):
		level_id = int(player.owner.get_instance_id())
	else:
		level_id = int(player.get_instance_id())

	if level_id != last_level_id:
		last_level_id = level_id
		max_abs_x_speed = 0.0

	var current_abs_x := abs(float(player.velocity.x))
	max_abs_x_speed = maxf(max_abs_x_speed, current_abs_x)

	var setting_value := int(Settings.file.gameplay.physics_style)
	var setting_name := "REMASTERED" if setting_value != 0 else "CLASSIC"
	var active_name := "UNKNOWN"
	if player.physics_dict == player.PHYSICS_PARAMETERS:
		active_name = "REMASTERED"
	elif player.physics_dict == player.CLASSIC_PARAMETERS:
		active_name = "CLASSIC"

	text = (
		"PHYSICS DIAGNOSTICS\n"
		+ "SETTING: %s (%d)   ACTIVE: %s\n" % [setting_name, setting_value, active_name]
		+ "WALK MAX: %.2f   ACCEL: %.2f\n" % [float(player.physics_params("WALK_SPEED")), float(player.physics_params("GROUND_WALK_ACCEL"))]
		+ "RUN MAX: %.2f   ACCEL: %.2f\n" % [float(player.physics_params("RUN_SPEED")), float(player.physics_params("GROUND_RUN_ACCEL"))]
		+ "JUMP IDLE: %.2f   GRAV: %.2f\n" % [float(player.physics_params("JUMP_SPEED_IDLE")), float(player.physics_params("JUMP_GRAVITY_IDLE"))]
		+ "CURRENT |X|: %.2f   MAX THIS LEVEL: %.2f" % [current_abs_x, max_abs_x_speed]
	)
