extends Label

var max_abs_x_speed := 0.0
var last_level_id := 0
var cached_player: Node = null

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_set_diagnostics_visible(false)

func _process(_delta: float) -> void:
	_update_text()

func _set_diagnostics_visible(value: bool) -> void:
	visible = value
	var background := get_node_or_null("../PhysicsDiagnosticsBackground")
	if background != null:
		background.visible = value

func _is_player_node(node: Node) -> bool:
	if not is_instance_valid(node):
		return false
	var script = node.get_script()
	if script == null:
		return false
	return String(script.resource_path).ends_with("/Scripts/Classes/Entities/Player.gd")

func _find_player_recursive(node: Node):
	if not is_instance_valid(node):
		return null
	if _is_player_node(node):
		return node
	for child in node.get_children():
		var found = _find_player_recursive(child)
		if is_instance_valid(found):
			return found
	return null

func _find_player():
	if is_instance_valid(cached_player) and _is_player_node(cached_player):
		return cached_player

	# Fast path when the group survives the Android wrapper/subviewport setup.
	for candidate in get_tree().get_nodes_in_group("Players"):
		if _is_player_node(candidate):
			cached_player = candidate
			return cached_player

	# Search the current level directly; this is the most reliable source once a
	# level is running, regardless of the runtime player node name.
	if is_instance_valid(Global.current_level):
		var level_player = _find_player_recursive(Global.current_level)
		if is_instance_valid(level_player):
			cached_player = level_player
			return cached_player

	# Android keeps gameplay under this SubViewport. Scan it by script identity
	# rather than assuming the player node is literally named "Player".
	var viewport = get_tree().root.get_node_or_null("Wrapper/CenterContainer/SubViewportContainer/SubViewport")
	if viewport != null:
		var viewport_player = _find_player_recursive(viewport)
		if is_instance_valid(viewport_player):
			cached_player = viewport_player
			return cached_player

	# Last-resort full-tree scan. This is only reached while no cached player is
	# available, so it does not run every frame during normal gameplay.
	var root_player = _find_player_recursive(get_tree().root)
	if is_instance_valid(root_player):
		cached_player = root_player
		return cached_player

	return null

func _update_text() -> void:
	var player = _find_player()
	if not is_instance_valid(player):
		cached_player = null
		_set_diagnostics_visible(false)
		return

	_set_diagnostics_visible(true)

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
		"PHYSICS\n"
		+ "SET %s\n" % setting_name
		+ "ACTIVE %s\n" % active_name
		+ "RUN %.2f  A %.2f\n" % [float(player.physics_params("RUN_SPEED")), float(player.physics_params("GROUND_RUN_ACCEL"))]
		+ "WALK %.2f  A %.2f\n" % [float(player.physics_params("WALK_SPEED")), float(player.physics_params("GROUND_WALK_ACCEL"))]
		+ "JUMP %.2f  G %.2f\n" % [float(player.physics_params("JUMP_SPEED_IDLE")), float(player.physics_params("JUMP_GRAVITY_IDLE"))]
		+ "X %.2f\n" % current_abs_x
		+ "MAX %.2f" % max_abs_x_speed
	)
