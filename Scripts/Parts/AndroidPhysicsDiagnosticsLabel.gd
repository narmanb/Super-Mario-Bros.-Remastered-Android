extends Node

const PANEL_WIDTH := 116.0
const PANEL_HEIGHT := 40.0
const PANEL_MARGIN := 4.0

var max_abs_x_speed := 0.0
var max_jump_up_speed := 0.0
var max_fall_speed := 0.0
var jump_count := 0
var was_on_floor := true
var last_level_id := 0
var cached_player = null
var search_cooldown := 0.0

var overlay_layer: CanvasLayer
var background: ColorRect
var readout: Label


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_create_overlay()
	_set_diagnostics_visible(false)
	get_viewport().size_changed.connect(_position_overlay)


func _process(delta: float) -> void:
	search_cooldown = maxf(0.0, search_cooldown - delta)
	_update_text()


func _create_overlay() -> void:
	overlay_layer = CanvasLayer.new()
	overlay_layer.name = "AndroidPhysicsDiagnosticsOverlay"
	overlay_layer.layer = 100
	add_child(overlay_layer)

	background = ColorRect.new()
	background.name = "Background"
	background.color = Color(0.0, 0.0, 0.0, 0.30)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	overlay_layer.add_child(background)

	readout = Label.new()
	readout.name = "Readout"
	readout.mouse_filter = Control.MOUSE_FILTER_IGNORE
	readout.add_theme_color_override("font_color", Color.WHITE)
	readout.add_theme_color_override("font_outline_color", Color.BLACK)
	readout.add_theme_constant_override("outline_size", 1)
	readout.add_theme_font_size_override("font_size", 4)
	overlay_layer.add_child(readout)

	_position_overlay()


func _position_overlay() -> void:
	if background == null or readout == null:
		return

	var visible_size := get_viewport().get_visible_rect().size
	var width := minf(PANEL_WIDTH, maxf(80.0, visible_size.x - PANEL_MARGIN * 2.0))
	var height := minf(PANEL_HEIGHT, maxf(40.0, visible_size.y - PANEL_MARGIN * 2.0))
	var panel_pos := Vector2(
		maxf(PANEL_MARGIN, (visible_size.x - width) * 0.5),
		PANEL_MARGIN
	)

	background.position = panel_pos
	background.size = Vector2(width, height)
	readout.position = panel_pos + Vector2(3.0, 2.0)
	readout.size = Vector2(maxf(1.0, width - 6.0), maxf(1.0, height - 4.0))


func _set_diagnostics_visible(value: bool) -> void:
	if is_instance_valid(background):
		background.visible = value
	if is_instance_valid(readout):
		readout.visible = value


func _is_player_node(node: Node) -> bool:
	if not is_instance_valid(node):
		return false

	# The live player is normally in the Players group. Accept that first so
	# this diagnostic does not depend on a particular runtime node name.
	if node is CharacterBody2D and node.is_in_group("Players"):
		return true

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

	# Fast path once a level has instantiated a real player.
	for candidate in get_tree().get_nodes_in_group("Players"):
		if _is_player_node(candidate):
			cached_player = candidate
			return cached_player

	# Avoid doing recursive fallbacks every rendered frame on the title screen.
	# As soon as a level begins, this retries four times per second.
	if search_cooldown > 0.0:
		return null
	search_cooldown = 0.25

	if is_instance_valid(Global.current_level):
		var level_player = _find_player_recursive(Global.current_level)
		if is_instance_valid(level_player):
			cached_player = level_player
			return cached_player

	# Android gameplay can live below a wrapper/subviewport. A root-tree scan
	# catches that layout without hard-coding the wrapper's node names.
	var root_player = _find_player_recursive(get_tree().root)
	if is_instance_valid(root_player):
		cached_player = root_player
		return cached_player

	return null


func _update_text() -> void:
	var player = _find_player()
	if not is_instance_valid(player):
		cached_player = null
		max_abs_x_speed = 0.0
		max_jump_up_speed = 0.0
		max_fall_speed = 0.0
		jump_count = 0
		was_on_floor = true
		last_level_id = 0
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
		max_jump_up_speed = 0.0
		max_fall_speed = 0.0
		jump_count = 0
		was_on_floor = true

	# Keep runtime access dynamic here. The concrete Player script owns
	# physics_dict/physics_params, while CharacterBody2D owns velocity.
	var velocity_value = player.get("velocity")
	var current_abs_x := 0.0
	if velocity_value is Vector2:
		current_abs_x = absf(velocity_value.x)
	max_abs_x_speed = maxf(max_abs_x_speed, current_abs_x)

	var current_y := 0.0
	if velocity_value is Vector2:
		current_y = velocity_value.y
		if current_y < 0.0:
			max_jump_up_speed = maxf(max_jump_up_speed, -current_y)
		else:
			max_fall_speed = maxf(max_fall_speed, current_y)
	var on_floor := player.is_on_floor()
	if was_on_floor and not on_floor and current_y < 0.0:
		jump_count += 1
	was_on_floor = on_floor

	readout.text = (
		"SPEED X %.1f  MAX %.1f\n" % [current_abs_x, max_abs_x_speed]
		+ "Y %.1f  JUMP MAX %.1f\n" % [current_y, max_jump_up_speed]
		+ "FALL MAX %.1f  JUMPS %d" % [max_fall_speed, jump_count]
	)


func _physics_value(player, key: String) -> float:
	if player == null:
		return 0.0
	if player.has_method("physics_params"):
		return float(player.call("physics_params", key))
	var physics = player.get("physics_dict")
	if physics is Dictionary:
		return float(physics.get(key, 0.0))
	return 0.0
