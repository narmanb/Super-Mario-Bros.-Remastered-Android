class_name PackNinePatch
extends NinePatchRect

@onready var resource_getter = ResourceGetter.new()

const ANDROID_LISTENER_PROBE_PATH := "user://android_theme_listener_probe.json"
const BOO_RACE_SETTINGS_ICON_PATH := "/root/Wrapper/CenterContainer/SubViewportContainer/SubViewport/Global/GameHUD/BooRacePause/SettingsMenu/PanelContainer/Control/Icon"

func _is_boo_race_settings_icon() -> bool:
	return OS.get_name() == "Android" and is_inside_tree() and str(get_path()) == BOO_RACE_SETTINGS_ICON_PATH

func _write_android_update_checkpoint(step: String) -> void:
	if not _is_boo_race_settings_icon():
		return

	var state: Dictionary = {}
	if FileAccess.file_exists(ANDROID_LISTENER_PROBE_PATH):
		var parsed = JSON.parse_string(FileAccess.get_file_as_string(ANDROID_LISTENER_PROBE_PATH))
		if parsed is Dictionary:
			state = parsed
	state.status = "running"
	state.phase = "before"
	state.listener = BOO_RACE_SETTINGS_ICON_PATH + "::update\nINTERNAL: " + step
	var file := FileAccess.open(ANDROID_LISTENER_PROBE_PATH, FileAccess.WRITE)
	if file == null:
		return
	file.store_string(JSON.stringify(state))
	file.flush()
	file.close()
	print("[ANDROID_ICON_UPDATE_PROBE] ", step)

func _android_can_keep_current_texture(current_texture: Resource) -> bool:
	if OS.get_name() != "Android" or current_texture == null or current_texture is AtlasTexture:
		return false
	if ResourceGetter.cache.has(current_texture.resource_path):
		return false
	return resource_getter.get_resource_path(current_texture.resource_path) == current_texture.resource_path

func _ready() -> void:
	update()
	Global.level_theme_changed.connect(update)

func update() -> void:
	var probe_target := _is_boo_race_settings_icon()
	if probe_target:
		_write_android_update_checkpoint("01 ENTER update")
		_write_android_update_checkpoint("02 BEFORE reading texture property")
	var current_texture = texture
	if probe_target:
		_write_android_update_checkpoint("03 AFTER reading texture / BEFORE Android unchanged-resource check")

	if _android_can_keep_current_texture(current_texture):
		if probe_target:
			_write_android_update_checkpoint("03A Android unchanged resource / BYPASS ResourceGetter / update COMPLETE")
		return

	var resolved_texture = resource_getter.get_resource(current_texture)
	if probe_target:
		_write_android_update_checkpoint("04 AFTER get_resource / BEFORE texture assignment")
	texture = resolved_texture
	if probe_target:
		_write_android_update_checkpoint("05 AFTER texture assignment / update COMPLETE")

func _exit_tree() -> void:
	resource_getter.free()
