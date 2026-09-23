class_name AndroidTitleScreenLifecycleProbe
extends TitleScreen

func _enter_tree() -> void:
	# Match Run 31's failing F phase: suppress TitleScreen._enter_tree().
	return

func _mark(code: String, description: String, seconds := 1.25) -> void:
	var generator := get_parent()
	var label := generator.get_node_or_null("MarginContainer/ProgressBar/Label") as Label
	if label != null:
		label.text = code + " " + description
	print("[ANDROID_TITLE_READY_PROBE] ", code, " ", description)
	await get_tree().create_timer(seconds, false).timeout

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
	await _mark("R22", "BEFORE update_theme")
	update_theme()
	await _mark("R23", "BEFORE physics_frame")
	await get_tree().physics_frame
	await _mark("R24", "BEFORE LevelBG time_of_day")
	$LevelBG.time_of_day = ["Day", "Night"].find(Global.theme_time)
	await _mark("R25", "BEFORE LevelBG update_visuals")
	$LevelBG.update_visuals()
	await _mark("R26", "READY COMPLETE", 10.0)
