class_name PackTextureRect
extends TextureRect

@export var use_cache := true
@onready var resource_getter = ResourceGetter.new()

const ANDROID_LISTENER_PROBE_PATH := "user://android_theme_listener_probe.json"
const STORY_PAUSE_LANGUAGE_FLAG_PATH := "/root/Wrapper/CenterContainer/SubViewportContainer/SubViewport/Global/GameHUD/StoryPause/SettingsMenu/PanelContainer/MarginContainer/VBoxContainer/Video/Language/HBoxContainer/Flag"

func _is_story_pause_language_flag() -> bool:
	return OS.get_name() == "Android" and is_inside_tree() and str(get_path()) == STORY_PAUSE_LANGUAGE_FLAG_PATH

func _write_android_update_checkpoint(step: String) -> void:
	if not _is_story_pause_language_flag():
		return

	var state: Dictionary = {}
	if FileAccess.file_exists(ANDROID_LISTENER_PROBE_PATH):
		var parsed = JSON.parse_string(FileAccess.get_file_as_string(ANDROID_LISTENER_PROBE_PATH))
		if parsed is Dictionary:
			state = parsed
	state.status = "running"
	state.phase = "before"
	state.listener = STORY_PAUSE_LANGUAGE_FLAG_PATH + "::update\nPACKTEXTURE: " + step
	var file := FileAccess.open(ANDROID_LISTENER_PROBE_PATH, FileAccess.WRITE)
	if file == null:
		return
	file.store_string(JSON.stringify(state))
	file.flush()
	file.close()
	print("[ANDROID_FLAG_UPDATE_PROBE] ", step)

func _android_can_keep_current_texture(current_texture: Resource) -> bool:
	if OS.get_name() != "Android" or current_texture == null or current_texture is AtlasTexture:
		return false
	if use_cache and ResourceGetter.cache.has(current_texture.resource_path):
		return false
	return resource_getter.get_resource_path(current_texture.resource_path) == current_texture.resource_path

func _ready() -> void:
	update()
	Global.level_theme_changed.connect(update)

func update() -> void:
	var probe_target := _is_story_pause_language_flag()
	if probe_target:
		_write_android_update_checkpoint("PT01 ENTER update use_cache=" + str(use_cache))
		_write_android_update_checkpoint("PT02 BEFORE reading texture property")
	var current_texture = texture
	if probe_target:
		var current_desc := "<null>" if current_texture == null else current_texture.get_class() + " path=" + current_texture.resource_path
		_write_android_update_checkpoint("PT03 AFTER reading texture / BEFORE Android unchanged-resource check: " + current_desc)

	# Android 4.6 has been dying while returning an unchanged Resource from
	# ResourceGetter. If there is no cached replacement and path resolution says
	# this exact texture is unchanged, get_resource() can only return the same
	# Resource. Keep the existing property instead and avoid that return boundary.
	if _android_can_keep_current_texture(current_texture):
		if probe_target:
			_write_android_update_checkpoint("PT03A Android unchanged resource / BYPASS ResourceGetter / update COMPLETE")
		return

	var resolved_texture = resource_getter.get_resource(current_texture, use_cache)
	if probe_target:
		_write_android_update_checkpoint("PT04A ResourceGetter CALL RETURNED")
		_write_android_update_checkpoint("PT04B BEFORE returned-resource null test")
		var resolved_is_null := resolved_texture == null
		_write_android_update_checkpoint("PT04C AFTER returned-resource null test null=" + str(resolved_is_null))

		var current_is_null := current_texture == null
		var same_reference := false
		if not resolved_is_null and not current_is_null:
			_write_android_update_checkpoint("PT04D BEFORE returned get_instance_id")
			var resolved_id := resolved_texture.get_instance_id()
			_write_android_update_checkpoint("PT04E AFTER returned get_instance_id id=" + str(resolved_id) + " / BEFORE current get_instance_id")
			var current_id := current_texture.get_instance_id()
			same_reference = resolved_id == current_id
			_write_android_update_checkpoint("PT04F AFTER current get_instance_id id=" + str(current_id) + " same=" + str(same_reference))

		if same_reference:
			_write_android_update_checkpoint("PT04G SAME RESOURCE / SKIP redundant texture assignment / COMPLETE")
			return

		_write_android_update_checkpoint("PT04H BEFORE returned get_class")
		var resolved_class := "<null>" if resolved_is_null else resolved_texture.get_class()
		_write_android_update_checkpoint("PT04I AFTER returned get_class=" + resolved_class + " / BEFORE resource_path")
		var resolved_path := "" if resolved_is_null else resolved_texture.resource_path
		_write_android_update_checkpoint("PT04J AFTER resource_path=" + resolved_path + " / BEFORE texture assignment")

	texture = resolved_texture
	if probe_target:
		_write_android_update_checkpoint("PT05 AFTER texture assignment / update COMPLETE")
