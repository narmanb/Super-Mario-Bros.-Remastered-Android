class_name PackNinePatch
extends NinePatchRect

@onready var resource_getter = ResourceGetter.new()

const ANDROID_LISTENER_PROBE_PATH := "user://android_theme_listener_probe.json"

func _active_android_probe_listener() -> String:
	if OS.get_name() != "Android" or not is_inside_tree() or not FileAccess.file_exists(ANDROID_LISTENER_PROBE_PATH):
		return ""
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(ANDROID_LISTENER_PROBE_PATH))
	if parsed is not Dictionary:
		return ""
	return str(parsed.get("listener", "")).get_slice("\n", 0)

func _is_active_probe_target() -> bool:
	return _active_android_probe_listener() == str(get_path()) + "::update"

func _write_android_update_checkpoint(step: String) -> void:
	if not _is_active_probe_target():
		return
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(ANDROID_LISTENER_PROBE_PATH))
	if parsed is not Dictionary:
		return
	var state: Dictionary = parsed
	state.status = "running"
	state.phase = "before"
	state.listener = str(get_path()) + "::update\nPACKNINEPATCH: " + step
	var file := FileAccess.open(ANDROID_LISTENER_PROBE_PATH, FileAccess.WRITE)
	if file == null:
		return
	file.store_string(JSON.stringify(state))
	file.flush()
	file.close()
	print("[ANDROID_PACKNINEPATCH_PROBE] ", step)

# Godot 4.6 Android has repeatedly died while a GDScript helper returns a
# Texture Resource to a UI update callback. Resolve and apply the texture
# in-place on Android so no Resource crosses that GDScript return boundary.
func _android_apply_texture_without_resource_return(current_texture: Resource) -> void:
	_write_android_update_checkpoint("N01 ENTER direct texture apply")
	if current_texture == null:
		_write_android_update_checkpoint("N02 current texture null / BEFORE clear")
		texture = null
		_write_android_update_checkpoint("N03 current texture null / COMPLETE")
		return

	if resource_getter.original_resource == null:
		_write_android_update_checkpoint("N04 BEFORE original_resource assignment")
		resource_getter.original_resource = current_texture

	var source: Resource = resource_getter.original_resource
	_write_android_update_checkpoint("N05 source=" + source.get_class() + " path=" + source.resource_path)

	if current_texture is not AtlasTexture and ResourceGetter.cache.has(source.resource_path):
		_write_android_update_checkpoint("N06 cache HIT / BEFORE direct texture assignment")
		texture = ResourceGetter.cache.get(source.resource_path)
		_write_android_update_checkpoint("N07 cache HIT / assignment COMPLETE")
		return

	_write_android_update_checkpoint("N08 cache MISS / BEFORE path resolution")
	var path := ""
	if source is AtlasTexture:
		var atlas_source = source.atlas
		_write_android_update_checkpoint("N09 AtlasTexture atlas null=" + str(atlas_source == null))
		if atlas_source == null:
			_write_android_update_checkpoint("N10 AtlasTexture has no atlas / KEEP current / COMPLETE")
			return
		path = resource_getter.get_resource_path(atlas_source.resource_path)
	else:
		path = resource_getter.get_resource_path(source.resource_path)
	_write_android_update_checkpoint("N11 resolved path=" + path)

	if path == source.resource_path:
		_write_android_update_checkpoint("N12 unchanged path / KEEP current / COMPLETE")
		return

	if source is not Texture:
		_write_android_update_checkpoint("N13 source is not Texture / KEEP current / COMPLETE")
		return

	var new_resource = null
	if path.contains(Global.config_path):
		_write_android_update_checkpoint("N14 BEFORE Image.load_from_file")
		var loaded_image := Image.load_from_file(path)
		_write_android_update_checkpoint("N15 AFTER Image.load_from_file null=" + str(loaded_image == null))
		if loaded_image != null:
			new_resource = ImageTexture.create_from_image(loaded_image)
	else:
		_write_android_update_checkpoint("N14 BEFORE load path=" + path)
		new_resource = load(path)
	_write_android_update_checkpoint("N16 AFTER load null=" + str(new_resource == null))

	resource_getter.send_to_cache(source.resource_path, new_resource)
	_write_android_update_checkpoint("N17 AFTER cache store / BEFORE direct assignment")
	if source is AtlasTexture:
		var atlas := AtlasTexture.new()
		atlas.atlas = new_resource
		atlas.region = source.region
		texture = atlas
	else:
		texture = new_resource
	_write_android_update_checkpoint("N18 direct assignment COMPLETE")

func _ready() -> void:
	update()
	Global.level_theme_changed.connect(update)

func update() -> void:
	var probe_target := _is_active_probe_target()
	if probe_target:
		_write_android_update_checkpoint("P01 ENTER update")
		_write_android_update_checkpoint("P02 BEFORE reading texture property")
	var current_texture = texture
	if probe_target:
		var current_desc := "<null>" if current_texture == null else current_texture.get_class() + " path=" + current_texture.resource_path
		_write_android_update_checkpoint("P03 AFTER reading texture: " + current_desc)

	if OS.get_name() == "Android":
		_android_apply_texture_without_resource_return(current_texture)
		return

	texture = resource_getter.get_resource(current_texture)

func _exit_tree() -> void:
	resource_getter.free()
