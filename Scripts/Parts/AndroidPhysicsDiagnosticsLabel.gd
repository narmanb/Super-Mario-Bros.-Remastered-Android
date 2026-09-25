extends Node

const PANEL_WIDTH := 120.0
const PANEL_HEIGHT := 44.0
const PANEL_MARGIN := 4.0

var max_abs_x_speed: float = 0.0
var max_jump_up_speed: float = 0.0
var max_fall_speed: float = 0.0
var current_jump_up_speed: float = 0.0
var last_jump_up_speed: float = 0.0
var jump_count: int = 0
var was_on_floor: bool = true
var last_level_id: int = 0
var last_player_id: int = 0
var cached_player: CharacterBody2D = null
var search_cooldown: float = 0.0

var overlay_layer: CanvasLayer
var background: ColorRect
var readout: Label


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_create_overlay()
	_show_waiting()
	get_viewport().size_changed.connect(_position_overlay)


func _physics_process(delta: float) -> void:
	search_cooldown = maxf(0.0, search_cooldown - delta)
	_update_diagnostics()


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
	if not is_instance_valid(background) or not is_instance_valid(readout):
		return

	var visible_size: Vector2 = get_viewport().get_visible_rect().size
	var width: float = minf(PANEL_WIDTH, maxf(80.0, visible_size.x - PANEL_MARGIN * 2.0))
	var height: float = minf(PANEL_HEIGHT, maxf(40.0, visible_size.y - PANEL_MARGIN * 2.0))
	var panel_pos := Vector2(
		maxf(PANEL_MARGIN, (visible_size.x - width) * 0.5),
		PANEL_MARGIN
	)

	background.position = panel_pos
	background.size = Vector2(width, height)
	readout.position = panel_pos + Vector2(3.0, 2.0)
	readout.size = Vector2(maxf(1.0, width - 6.0), maxf(1.0, height - 4.0))


func _show_waiting() -> void:
	if is_instance_valid(background):
		background.visible = true
	if is_instance_valid(readout):
		readout.visible = true
		readout.text = "DIAG: WAITING FOR PLAYER"


func _is_player_node(node: Node) -> bool:
	if not is_instance_valid(node):
		return false
	if node is CharacterBody2D and node.is_in_group("Players"):
		return true
	var script: Script = node.get_script() as Script
	if script == null:
		return false
	return String(script.resource_path).ends_with("/Scripts/Classes/Entities/Player.gd")


func _find_player_recursive(node: Node) -> CharacterBody2D:
	if not is_instance_valid(node):
		return null
	if _is_player_node(node):
		return node as CharacterBody2D
	for child: Node in node.get_children():
		var found: CharacterBody2D = _find_player_recursive(child)
		if is_instance_valid(found):
			return found
	return null


func _find_player() -> CharacterBody2D:
	if is_instance_valid(cached_player) and _is_player_node(cached_player):
		return cached_player

	for candidate: Node in get_tree().get_nodes_in_group("Players"):
		if _is_player_node(candidate):
			cached_player = candidate as CharacterBody2D
			return cached_player

	if search_cooldown > 0.0:
		return null
	search_cooldown = 0.25

	if is_instance_valid(Global.current_level):
		var level_player: CharacterBody2D = _find_player_recursive(Global.current_level)
		if is_instance_valid(level_player):
			cached_player = level_player
			return cached_player

	var root_player: CharacterBody2D = _find_player_recursive(get_tree().root)
	if is_instance_valid(root_player):
		cached_player = root_player
		return cached_player

	return null


func _reset_measurements(start_on_floor: bool = true) -> void:
	max_abs_x_speed = 0.0
	max_jump_up_speed = 0.0
	max_fall_speed = 0.0
	current_jump_up_speed = 0.0
	last_jump_up_speed = 0.0
	jump_count = 0
	was_on_floor = start_on_floor


func _update_diagnostics() -> void:
	var body: CharacterBody2D = _find_player()
	if not is_instance_valid(body):
		cached_player = null
		last_level_id = 0
		last_player_id = 0
		_reset_measurements()
		_show_waiting()
		return

	var level_id: int = 0
	if is_instance_valid(Global.current_level):
		level_id = int(Global.current_level.get_instance_id())
	elif is_instance_valid(body.owner):
		level_id = int(body.owner.get_instance_id())
	else:
		level_id = int(body.get_instance_id())

	var player_id: int = int(body.get_instance_id())
	if level_id != last_level_id or player_id != last_player_id:
		last_level_id = level_id
		last_player_id = player_id
		_reset_measurements(body.is_on_floor())

	var vx: float = body.velocity.x
	var vy: float = body.velocity.y
	var abs_x: float = absf(vx)
	max_abs_x_speed = maxf(max_abs_x_speed, abs_x)

	if vy < 0.0:
		max_jump_up_speed = maxf(max_jump_up_speed, -vy)
	else:
		max_fall_speed = maxf(max_fall_speed, vy)

	var on_floor: bool = body.is_on_floor()
	if was_on_floor and not on_floor and vy < 0.0:
		jump_count += 1
		current_jump_up_speed = -vy
	elif not on_floor and vy < 0.0:
		current_jump_up_speed = maxf(current_jump_up_speed, -vy)
	elif not was_on_floor and on_floor:
		last_jump_up_speed = current_jump_up_speed
		current_jump_up_speed = 0.0
	was_on_floor = on_floor

	var shown_jump: float = current_jump_up_speed if not on_floor else last_jump_up_speed
	background.visible = true
	readout.visible = true
	readout.text = (
		"X %.1f  MAX %.1f\n" % [vx, max_abs_x_speed]
		+ "Y %.1f  FALL %.1f\n" % [vy, max_fall_speed]
		+ "JUMP %d  UP %.1f\n" % [jump_count, shown_jump]
		+ "UP MAX %.1f" % max_jump_up_speed
	)
