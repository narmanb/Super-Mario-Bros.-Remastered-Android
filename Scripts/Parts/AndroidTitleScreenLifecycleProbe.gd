class_name AndroidTitleScreenLifecycleProbe
extends TitleScreen

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

	var label := layer.get_node_or_null("Marker") as Label
	if label == null:
		label = Label.new()
		label.name = "Marker"
		label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		label.add_theme_font_size_override("font_size", 26)
		label.add_theme_constant_override("outline_size", 8)
		label.set_anchors_preset(Control.PRESET_TOP_WIDE)
		label.offset_left = 0
		label.offset_top = 72
		label.offset_right = 0
		label.offset_bottom = 132
		layer.add_child(label)
	return label

func _mark(code: String, description: String, seconds := 1.25) -> void:
	var label := _get_probe_overlay_label()
	label.text = code + "  " + description
	print("[ANDROID_TITLE_READY_PROBE] ", code, " ", description)
	# Allow the top-level overlay to render before executing the operation.
	await get_tree().process_frame
	await get_tree().create_timer(seconds, false).timeout

func _probe_global_update_theme() -> void:
	# Inline Global.update_theme() exactly so T01 can be narrowed to one operation.
	await _mark("U01", "BEFORE theme_override reset")
	Global.theme_override = ""
	await _mark("U02", "BEFORE time_override reset")
	Global.time_override = ""
	await _mark("U03", "BEFORE ThemeGetter.update_resource")
	Global.get_node("ThemeGetter").update_resource()
	await _mark("U04", "BEFORE ResourceSetterNew.clear_cache")
	ResourceSetterNew.clear_cache()
	await _mark("U05", "BEFORE level_theme_changed emit")
	Global.level_theme_changed.emit()
	await _mark("U06", "Global.update_theme COMPLETE")

func _probe_update_theme() -> void:
	# Inline Level.update_theme() so the Android crash can be isolated to one
	# exact operation. Each marker is rendered before the following statement.
	await _mark("T01", "BEFORE Global.update_theme internals")
	await _probe_global_update_theme()

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
	await _probe_update_theme()
	await _mark("R23", "BEFORE physics_frame")
	await get_tree().physics_frame
	await _mark("R24", "BEFORE LevelBG time_of_day")
	$LevelBG.time_of_day = ["Day", "Night"].find(Global.theme_time)
	await _mark("R25", "BEFORE LevelBG update_visuals")
	$LevelBG.update_visuals()
	await _mark("R26", "READY COMPLETE", 10.0)
