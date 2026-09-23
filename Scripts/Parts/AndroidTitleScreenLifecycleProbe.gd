class_name AndroidTitleScreenLifecycleProbe
extends TitleScreen

const LISTENER_PROBE_PATH := "user://android_theme_listener_probe.json"
const LISTENER_GROUP_SIZE := 64

func _enter_tree() -> void:
	# Match Run 31's failing F phase: suppress TitleScreen._enter_tree().
	return

func _get_probe_overlay_label() -> Label:
	var root := get_tree().root
	var layer := root.get_node_or_null("AndroidReadyProbeOverlay") as CanvasLayer
	if layer == null:
		layer = CanvasLayer.new()
		layer.name = "AndroidReadyProbeOverlay"
		layer.layer = 10000
		root.add_child(layer)

	# The corrupted TitleScreen can be visually noisy. Put the diagnostic on
	# a fully opaque panel so a saved callback path/method is readable after
	# relaunch without executing the crashing listener again.
	var panel := layer.get_node_or_null("OpaqueBackground") as ColorRect
	if panel == null:
		panel = ColorRect.new()
		panel.name = "OpaqueBackground"
		panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
		panel.color = Color(0.0, 0.0, 0.0, 1.0)
		panel.set_anchors_preset(Control.PRESET_TOP_WIDE)
		panel.offset_left = 0
		panel.offset_top = 24
		panel.offset_right = 0
		panel.offset_bottom = 330
		layer.add_child(panel)

	var label := layer.get_node_or_null("Marker") as Label
	if label == null:
		label = Label.new()
		label.name = "Marker"
		label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		label.add_theme_font_size_override("font_size", 26)
		label.add_theme_constant_override("outline_size", 8)
		label.set_anchors_preset(Control.PRESET_TOP_WIDE)
		label.offset_left = 24
		label.offset_top = 40
		label.offset_right = -24
		label.offset_bottom = 314
		layer.add_child(label)
	return label

func _mark(code: String, description: String, seconds := 0.1) -> void:
	var label := _get_probe_overlay_label()
	label.text = code + "  " + description
	print("[ANDROID_TITLE_READY_PROBE] ", code, " ", description)
	# Allow the top-level overlay to render before executing the operation.
	await get_tree().process_frame
	await get_tree().create_timer(seconds, false).timeout

func _listener_description(callback: Callable) -> String:
	var target = callback.get_object()
	var target_desc := "<invalid>"
	if is_instance_valid(target):
		if target is Node:
			target_desc = str((target as Node).get_path())
		else:
			target_desc = str(target)
	return target_desc + "::" + str(callback.get_method())

func _read_listener_checkpoint() -> Dictionary:
	if not FileAccess.file_exists(LISTENER_PROBE_PATH):
		return {}
	var parsed = JSON.parse_string(FileAccess.get_file_as_string(LISTENER_PROBE_PATH))
	return parsed if parsed is Dictionary else {}

func _write_listener_checkpoint(state: Dictionary) -> bool:
	var file := FileAccess.open(LISTENER_PROBE_PATH, FileAccess.WRITE)
	if file == null:
		push_error("Could not persist Android theme probe: " + str(FileAccess.get_open_error()))
		return false
	file.store_string(JSON.stringify(state))
	file.flush() # This must reach storage before the potentially fatal call.
	file.close()
	return true

func _probe_level_theme_listeners() -> bool:
	# Keep the original connection order, but remove the per-listener render
	# delay. A durable before/after checkpoint identifies a synchronous crash
	# on the next launch, without logcat or another build.
	var connections := Global.get_signal_connection_list("level_theme_changed")
	var previous := _read_listener_checkpoint()
	if previous.get("status", "") == "running":
		var index := int(previous.get("index", -1))
		var last := str(previous.get("listener", "<unknown>"))
		var phase := str(previous.get("phase", "unknown"))
		var current := "<missing from new snapshot>"
		if index >= 0 and index < connections.size():
			current = _listener_description(connections[index].get("callable", Callable()))
		var verdict := "LAST STARTED" if phase == "before" else "LAST RETURNED"
		await _mark("V FOUND", "%s %d/%d\n%s\nNow: %s" % [verdict, index + 1, int(previous.get("count", 0)), last, current], 3600.0)
		return false
	if previous.get("status", "") == "complete":
		await _mark("V DONE", "All %d listeners returned in previous run" % int(previous.get("count", 0)), 3600.0)
		return false
	await _mark("V00", "TESTING %d LISTENERS IN FAST GROUPS" % connections.size(), 0.8)
	for group_start in range(0, connections.size(), LISTENER_GROUP_SIZE):
		var group_end := mini(group_start + LISTENER_GROUP_SIZE, connections.size())
		# One visible group marker; callbacks within it run with no timer.
		_get_probe_overlay_label().text = "V %d-%d/%d  TESTING" % [group_start + 1, group_end, connections.size()]
		await get_tree().process_frame
		for i in range(group_start, group_end):
			var callback: Callable = connections[i].get("callable", Callable())
			var state := {"status": "running", "phase": "before", "index": i,
				"count": connections.size(), "listener": _listener_description(callback)}
			if not _write_listener_checkpoint(state):
				await _mark("V ERROR", "Could not write probe checkpoint", 3600.0)
				return false
			print("[ANDROID_TITLE_READY_PROBE] BEFORE ", i + 1, "/", connections.size(), " ", state.listener)
			if callback.is_valid():
				callback.call()
			state.phase = "after"
			if not _write_listener_checkpoint(state):
				await _mark("V ERROR", "Could not write returned checkpoint", 3600.0)
				return false
	if not _write_listener_checkpoint({"status": "complete", "count": connections.size()}):
		await _mark("V ERROR", "Could not write completion checkpoint", 3600.0)
		return false
	await _mark("V99", "ALL %d LISTENERS RETURNED" % connections.size(), 1.5)
	return true

func _probe_global_update_theme() -> bool:
	# Inline Global.update_theme() exactly so T01 can be narrowed to one operation.
	await _mark("U01", "BEFORE theme_override reset")
	Global.theme_override = ""
	await _mark("U02", "BEFORE time_override reset")
	Global.time_override = ""
	await _mark("U03", "BEFORE ThemeGetter.update_resource")
	Global.get_node("ThemeGetter").update_resource()
	await _mark("U04", "BEFORE ResourceSetterNew.clear_cache")
	ResourceSetterNew.clear_cache()
	await _mark("U05", "BEFORE level_theme_changed listeners")
	if not await _probe_level_theme_listeners():
		return false
	await _mark("U06", "Global.update_theme COMPLETE")
	return true

func _probe_update_theme() -> bool:
	# Inline Level.update_theme() so the Android crash can be isolated to one
	# exact operation. Each marker is rendered before the following statement.
	await _mark("T01", "BEFORE Global.update_theme internals")
	if not await _probe_global_update_theme():
		return false

	await _mark("T02", "AFTER Global.update_theme")
	if auto_set_theme:
		await _mark("T03", "BEFORE campaign validity check")
		if Global.CAMPAIGNS.has(Global.current_campaign) == false and first_load:
			Global.current_campaign = "SMB1"

		await _mark("T04", "BEFORE custom campaign check")
		if Global.in_custom_campaign() == false:
			await _mark("T05", "BEFORE WORLD_THEMES lookup")
			theme = WORLD_THEMES[Global.current_campaign][Global.world_num]

			await _mark("T06", "BEFORE theme_time selection")
			if Global.world_num > 4 and Global.world_num < 9:
				theme_time = "Night"
			else:
				theme_time = "Day"
			if Global.current_campaign == "SMBANN":
				theme_time = "Night"
		else:
			await _mark("T07", "BEFORE custom theme lookup")
			theme = Global.custom_campaign_jsons[Global.current_custom_campaign].world_themes[Global.world_num - 1][0]
			theme_time = Global.custom_campaign_jsons[Global.current_custom_campaign].world_themes[Global.world_num - 1][1]

		await _mark("T08", "BEFORE campaign assignment")
		campaign = Global.current_campaign
		await _mark("T09", "BEFORE ResourceSetterNew.clear_cache")
		ResourceSetterNew.clear_cache()

	await _mark("T10", "BEFORE Global.current_campaign assignment")
	Global.current_campaign = campaign
	await _mark("T11", "BEFORE Global.level_theme assignment")
	Global.level_theme = theme
	await _mark("T12", "BEFORE Global.theme_time assignment")
	Global.theme_time = theme_time
	await _mark("T13", "BEFORE TitleScreen.last_theme assignment")
	TitleScreen.last_theme = theme
	await _mark("T14", "BEFORE LevelBG lookup")
	if get_node_or_null("LevelBG") != null:
		await _mark("T15", "BEFORE LevelBG.update_visuals")
		$LevelBG.update_visuals()
	await _mark("T16", "update_theme COMPLETE")
	return true

func _ready() -> void:
	await _mark("R01", "BEFORE setup_stars")
	setup_stars()
	await _mark("R02", "BEFORE DevBuildWarning")
	%DevBuildWarning.visible = Global.is_snapshot
	await _mark("R03", "BEFORE level_theme connect")
	Global.level_theme_changed.connect(setup_stars)
	await _mark("R04", "BEFORE DiscoLevel false")
	DiscoLevel.in_disco_level = false
	await _mark("R05", "BEFORE unpause")
	get_tree().paused = false
	await _mark("R06", "BEFORE stop_all_music")
	AudioManager.stop_all_music()
	await _mark("R07", "BEFORE stop_music_override")
	AudioManager.stop_music_override(AudioManager.MUSIC_OVERRIDES.NONE, true)
	await _mark("R08", "BEFORE Global.reset_values")
	Global.reset_values()
	await _mark("R09", "BEFORE second_quest false")
	Global.second_quest = false
	await _mark("R10", "BEFORE speedrun timer zero")
	SpeedrunHandler.timer = 0
	await _mark("R11", "BEFORE timer_active false")
	SpeedrunHandler.timer_active = false
	await _mark("R12", "BEFORE show_timer false")
	SpeedrunHandler.show_timer = false
	await _mark("R13", "BEFORE ghost_active false")
	SpeedrunHandler.ghost_active = false
	await _mark("R14", "BEFORE ghost_enabled false")
	SpeedrunHandler.ghost_enabled = false
	await _mark("R15", "BEFORE player_ghost.apply_data")
	Global.player_ghost.apply_data()
	await _mark("R16", "BEFORE PlayerGhosts delete")
	get_tree().call_group("PlayerGhosts", "delete")
	await _mark("R17", "BEFORE current_level null")
	Global.current_level = null
	await _mark("R18", "BEFORE get_world_count clamp")
	Global.world_num = clamp(Global.world_num, 1, get_world_count())

	# Inline update_title() so its individual operations are isolated too.
	await _mark("R19", "BEFORE load/apply save")
	SaveManager.apply_save(SaveManager.load_save(Global.current_campaign))
	await _mark("R20", "BEFORE level_id")
	level_id = Global.level_num - 1
	await _mark("R21", "BEFORE world_id")
	world_id = Global.world_num
	await _mark("R22", "BEFORE update_theme probe")
	if not await _probe_update_theme():
		return
	await _mark("R23", "BEFORE physics_frame")
	await get_tree().physics_frame
	await _mark("R24", "BEFORE LevelBG time_of_day")
	$LevelBG.time_of_day = ["Day", "Night"].find(Global.theme_time)
	await _mark("R25", "BEFORE LevelBG update_visuals")
	$LevelBG.update_visuals()
	await _mark("R26", "READY COMPLETE", 10.0)
