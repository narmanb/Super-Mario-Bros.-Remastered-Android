class_name ResourceGetter
extends Node

var original_resource: Resource = null

static var cache := {}

const ANDROID_LISTENER_PROBE_PATH := "user://android_theme_listener_probe.json"
const STORY_PAUSE_LANGUAGE_FLAG_LISTENER := "/root/Wrapper/CenterContainer/SubViewportContainer/SubViewport/Global/GameHUD/StoryPause/SettingsMenu/PanelContainer/MarginContainer/VBoxContainer/Video/Language/HBoxContainer/Flag::update"

func _story_flag_probe_active() -> bool:
	if OS.get_name() != "Android" or not FileAccess.file_exists(ANDROID_LISTENER_PROBE_PATH):
		return false
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(ANDROID_LISTENER_PROBE_PATH))
	if parsed is not Dictionary:
		return false
	return str(parsed.get("listener", "")).begins_with(STORY_PAUSE_LANGUAGE_FLAG_LISTENER)

func _probe_story_flag(step: String) -> void:
	if not _story_flag_probe_active():
		return
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(ANDROID_LISTENER_PROBE_PATH))
	if parsed is not Dictionary:
		return
	var state: Dictionary = parsed
	state.status = "running"
	state.phase = "before"
	state.listener = STORY_PAUSE_LANGUAGE_FLAG_LISTENER + "\nRESOURCE_GETTER: " + step
	var file := FileAccess.open(ANDROID_LISTENER_PROBE_PATH, FileAccess.WRITE)
	if file == null:
		return
	file.store_string(JSON.stringify(state))
	file.flush()
	file.close()
	print("[ANDROID_RESOURCE_GETTER_PROBE] ", step)

func get_resource(resource: Resource, use_cache := true) -> Resource:
	_probe_story_flag("RG01 ENTER get_resource use_cache=" + str(use_cache))
	if resource == null:
		_probe_story_flag("RG02 resource is null / RETURN null")
		return null

	_probe_story_flag("RG03 input=" + resource.get_class() + " path=" + resource.resource_path)
	if not use_cache:
		_probe_story_flag("RG04 BEFORE original_resource reset")
		original_resource = null

	if original_resource == null:
		_probe_story_flag("RG05 BEFORE original_resource assignment")
		original_resource = resource
	_probe_story_flag("RG06 original=" + original_resource.get_class() + " path=" + original_resource.resource_path)

	_probe_story_flag("RG07 BEFORE cache lookup")
	if cache.has(original_resource.resource_path) and resource is not AtlasTexture and use_cache:
		_probe_story_flag("RG08 cache HIT / BEFORE RETURN")
		return cache.get(original_resource.resource_path)
	_probe_story_flag("RG09 cache MISS / BEFORE resource path resolution")

	var path := ""
	if original_resource is AtlasTexture:
		_probe_story_flag("RG10 AtlasTexture / BEFORE atlas access")
		var atlas_resource = original_resource.atlas
		_probe_story_flag("RG11 AFTER atlas access / atlas=" + ("<null>" if atlas_resource == null else atlas_resource.get_class() + " path=" + atlas_resource.resource_path))
		path = get_resource_path(atlas_resource.resource_path)
	else:
		_probe_story_flag("RG10 normal resource / BEFORE get_resource_path")
		path = get_resource_path(original_resource.resource_path)
	_probe_story_flag("RG12 AFTER get_resource_path resolved=" + path)

	_probe_story_flag("RG13 BEFORE unchanged-path comparison")
	if path == original_resource.resource_path:
		_probe_story_flag("RG14 unchanged path / BEFORE return selection")
		# Build 46 diagnostic experiment: for the isolated StoryPause flag only,
		# return the Resource passed into this call rather than the copy retained
		# in original_resource. Normally these should refer to the same Resource.
		# If this crosses the return boundary cleanly, it isolates the retained
		# member reference as part of the Android native-crash trigger.
		if _story_flag_probe_active():
			_probe_story_flag("RG14A Android experiment / RETURN current input")
			return resource
		_probe_story_flag("RG14B normal / RETURN original")
		return original_resource

	if original_resource is Texture:
		_probe_story_flag("RG15 Texture branch")
		var new_resource = null
		if path.contains(Global.config_path):
			_probe_story_flag("RG16 BEFORE Image.load_from_file path=" + path)
			var loaded_image := Image.load_from_file(path)
			_probe_story_flag("RG17 AFTER Image.load_from_file null=" + str(loaded_image == null))
			new_resource = ImageTexture.create_from_image(loaded_image)
			_probe_story_flag("RG18 AFTER ImageTexture.create_from_image")
		else:
			_probe_story_flag("RG16 BEFORE load path=" + path)
			new_resource = load(path)
			_probe_story_flag("RG17 AFTER load null=" + str(new_resource == null))
		_probe_story_flag("RG19 BEFORE send_to_cache")
		send_to_cache(original_resource.resource_path, new_resource)
		_probe_story_flag("RG20 AFTER send_to_cache")
		if original_resource is AtlasTexture:
			_probe_story_flag("RG21 BEFORE AtlasTexture rebuild")
			var atlas = AtlasTexture.new()
			atlas.atlas = new_resource
			atlas.region = original_resource.region
			_probe_story_flag("RG22 AFTER AtlasTexture rebuild / RETURN atlas")
			return atlas
		_probe_story_flag("RG23 RETURN loaded texture")
		return new_resource

	elif original_resource is AudioStream:
		_probe_story_flag("RG15 AudioStream branch")
		if path.get_file().contains(".wav"):
			var new_resource = AudioStreamWAV.load_from_file(path)
			send_to_cache(original_resource.resource_path, new_resource)
			return new_resource
		elif path.get_file().contains(".mp3"):
			var new_resource = AudioStreamMP3.load_from_file(path)
			send_to_cache(original_resource.resource_path, new_resource)
			return new_resource

	elif original_resource is Font:
		_probe_story_flag("RG15 Font branch")
		var new_font = FontFile.new()
		new_font.load_bitmap_font(path)
		send_to_cache(original_resource.resource_path, new_font)
		return new_font

	_probe_story_flag("RG24 fallback BEFORE send_to_cache")
	send_to_cache(original_resource.resource_path, original_resource)
	_probe_story_flag("RG25 fallback RETURN original")
	return original_resource

func send_to_cache(resource_path := "", resource_to_cache: Resource = null) -> void:
	if cache.has(resource_path) == false:
		cache.set(resource_path, resource_to_cache)

func get_resource_path(resource_path := "") -> String:
	_probe_story_flag("RGP01 ENTER get_resource_path input=" + resource_path)
	_probe_story_flag("RGP02 BEFORE Settings resource_packs access")
	var resource_packs = Settings.file.visuals.resource_packs
	_probe_story_flag("RGP03 AFTER resource_packs access count=" + str(resource_packs.size()))
	for i in resource_packs:
		_probe_story_flag("RGP04 pack=" + str(i) + " BEFORE Assets replacement")
		var test = resource_path.replace("res://Assets/", Global.config_path.path_join("resource_packs/" + i + "/"))
		_probe_story_flag("RGP05 AFTER Assets replacement test=" + test)
		test = test.replace(Global.config_path.path_join("custom_characters"), Global.config_path.path_join("resource_packs/" + test + "/Sprites/Players/CustomCharacters/"))
		_probe_story_flag("RGP06 AFTER custom-character replacement test=" + test)
		_probe_story_flag("RGP07 BEFORE FileAccess.file_exists")
		var exists := FileAccess.file_exists(test)
		_probe_story_flag("RGP08 AFTER FileAccess.file_exists exists=" + str(exists))
		if exists:
			_probe_story_flag("RGP09 matched pack / RETURN " + test)
			return test
	_probe_story_flag("RGP10 no pack match / RETURN original path")
	return resource_path

static func get_resource_pack_from_path(path := "") -> String:
	if path.contains("res://"):
		return ""
	var resource_pack := ""
	var split_1 = path.split("resource_packs")
	resource_pack = split_1[1].get_slice("/", 1)
	return resource_pack
