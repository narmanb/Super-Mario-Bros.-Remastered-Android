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
		_write_android_update_checkpoint("PT03 AFTER reading texture / BEFORE ResourceGetter: " + current_desc)
	var resolved_texture = resource_getter.get_resource(current_texture, use_cache)
	if probe_target:
		var resolved_desc := "<null>" if resolved_texture == null else resolved_texture.get_class() + " path=" + resolved_texture.resource_path
		_write_android_update_checkpoint("PT04 AFTER ResourceGetter / BEFORE texture assignment: " + resolved_desc)
	texture = resolved_texture
	if probe_target:
		_write_android_update_checkpoint("PT05 AFTER texture assignment / update COMPLETE")
