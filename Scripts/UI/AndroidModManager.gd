extends Control

signal closed

const MOD_DIR := "user://mods"
const TEMP_IMPORT := "user://mod_import_pending.zip"
const GAMEBANANA_URL := "https://gamebanana.com/mods/games/22798"
const BLOCKED_WINDOWS_EXTENSIONS := ["dll", "exe"]

var mod_list_box: VBoxContainer
var status_label: Label
var restart_label: Label
var install_button: Button
var browse_button: Button
var refresh_button: Button
var back_button: Button
var picker_open := false
var restart_required := false

func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_ui()
	_ensure_mod_dir()
	hide()
	set_process(false)

func open() -> void:
	_ensure_mod_dir()
	_refresh_mod_list()
	show()
	set_process(true)
	await get_tree().process_frame
	install_button.grab_focus()

func close() -> void:
	if picker_open:
		return
	hide()
	set_process(false)
	closed.emit()

func _process(_delta: float) -> void:
	if visible and not picker_open and Global.multibind_action_just_pressed("ui_back"):
		close()

func _build_ui() -> void:
	var backdrop := ColorRect.new()
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	backdrop.color = Color(0.0, 0.0, 0.0, 0.92)
	backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(backdrop)

	var margin := MarginContainer.new()
	margin.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 10)
	margin.add_theme_constant_override("margin_top", 7)
	margin.add_theme_constant_override("margin_right", 10)
	margin.add_theme_constant_override("margin_bottom", 7)
	add_child(margin)

	var root_vbox := VBoxContainer.new()
	root_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	root_vbox.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root_vbox.add_theme_constant_override("separation", 3)
	margin.add_child(root_vbox)

	var title := Label.new()
	title.text = "MOD MANAGER"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	root_vbox.add_child(title)

	var help := Label.new()
	help.text = "GML MODS - CHANGES APPLY AFTER RESTART"
	help.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	help.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root_vbox.add_child(help)

	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", 3)
	root_vbox.add_child(actions)

	install_button = Button.new()
	install_button.text = "INSTALL ZIP"
	install_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	install_button.custom_minimum_size.y = 22
	install_button.pressed.connect(_choose_mod_zip)
	actions.add_child(install_button)

	browse_button = Button.new()
	browse_button.text = "BROWSE MODS"
	browse_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	browse_button.custom_minimum_size.y = 22
	browse_button.pressed.connect(_browse_mods)
	actions.add_child(browse_button)

	refresh_button = Button.new()
	refresh_button.text = "REFRESH"
	refresh_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	refresh_button.custom_minimum_size.y = 22
	refresh_button.pressed.connect(_refresh_mod_list)
	actions.add_child(refresh_button)

	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.custom_minimum_size.y = 62
	root_vbox.add_child(scroll)

	mod_list_box = VBoxContainer.new()
	mod_list_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	mod_list_box.add_theme_constant_override("separation", 2)
	scroll.add_child(mod_list_box)

	restart_label = Label.new()
	restart_label.text = ""
	restart_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	restart_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root_vbox.add_child(restart_label)

	status_label = Label.new()
	status_label.text = ""
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	root_vbox.add_child(status_label)

	back_button = Button.new()
	back_button.text = "BACK"
	back_button.custom_minimum_size.y = 22
	back_button.pressed.connect(close)
	root_vbox.add_child(back_button)

func _ensure_mod_dir() -> bool:
	if DirAccess.dir_exists_absolute(MOD_DIR):
		return true
	var result := DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(MOD_DIR))
	if result != OK:
		_set_status("Could not create the Android mods folder: %s" % error_string(result))
		return false
	return true

func _refresh_mod_list() -> void:
	if mod_list_box == null:
		return

	for child in mod_list_box.get_children():
		mod_list_box.remove_child(child)
		child.queue_free()

	var known_zip_names: Dictionary = {}
	var ids: Array = ModLoaderStore.mod_data.keys()
	ids.sort()

	for id_variant in ids:
		var mod_id := str(id_variant)
		var mod_data: ModData = ModLoaderStore.mod_data[mod_id]
		if not mod_data.zip_path.is_empty():
			known_zip_names[mod_data.zip_path.get_file().to_lower()] = true
		_add_loaded_mod_row(mod_id, mod_data)

	var pending_count := _add_pending_zip_rows(known_zip_names)
	if ids.is_empty() and pending_count == 0:
		var empty := Label.new()
		empty.text = "NO GML MODS INSTALLED"
		empty.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		mod_list_box.add_child(empty)

	if restart_required:
		restart_label.text = "RESTART THE GAME TO APPLY MOD CHANGES"
	else:
		restart_label.text = ""

func _add_loaded_mod_row(mod_id: String, mod_data: ModData) -> void:
	var checkbox := CheckBox.new()
	checkbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var display_name := mod_id
	var version := ""
	if mod_data.manifest != null:
		if not mod_data.manifest.name.is_empty():
			display_name = mod_data.manifest.name
		version = mod_data.manifest.version_number
		checkbox.tooltip_text = str(mod_data.manifest.description).to_upper()

	checkbox.text = display_name.to_upper()
	if not version.is_empty():
		checkbox.text += "  V" + version.to_upper()
	if not mod_data.is_loadable:
		checkbox.text += "  [ERROR]"

	checkbox.button_pressed = mod_data.is_active
	checkbox.disabled = mod_data.is_locked or not mod_data.is_loadable
	checkbox.toggled.connect(_on_mod_toggled.bind(mod_id, checkbox))
	mod_list_box.add_child(checkbox)

func _add_pending_zip_rows(known_zip_names: Dictionary) -> int:
	if not DirAccess.dir_exists_absolute(MOD_DIR):
		return 0

	var count := 0
	var files := Array(DirAccess.get_files_at(MOD_DIR))
	files.sort()
	for file_variant in files:
		var file_name := str(file_variant)
		if file_name.get_extension().to_lower() != "zip":
			continue
		if known_zip_names.has(file_name.to_lower()):
			continue

		count += 1
		var info := _inspect_mod_zip(MOD_DIR.path_join(file_name))
		var pending := Label.new()
		pending.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		pending.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		if info.get("ok", false):
			pending.text = "%s  V%s  [RESTART TO LOAD]" % [str(info.get("name", file_name)).to_upper(), str(info.get("version", "")).to_upper()]
		else:
			pending.text = "%s  [INVALID MOD ZIP]" % file_name.to_upper()
		mod_list_box.add_child(pending)
	return count

func _on_mod_toggled(pressed: bool, mod_id: String, checkbox: CheckBox) -> void:
	if not ModLoaderUserProfile.is_initialized():
		checkbox.set_pressed_no_signal(not pressed)
		_set_status("Mod profile is not initialized. Restart the game and try again.")
		return

	var success := false
	if pressed:
		success = ModLoaderUserProfile.enable_mod(mod_id)
	else:
		success = ModLoaderUserProfile.disable_mod(mod_id)

	if not success:
		checkbox.set_pressed_no_signal(not pressed)
		_set_status("Could not change %s. The mod may be locked or incompatible." % mod_id)
		return

	restart_required = true
	if pressed:
		_set_status("Enabled %s for the next game start." % mod_id)
	else:
		_set_status("Disabled %s for the next game start." % mod_id)
	restart_label.text = "RESTART THE GAME TO APPLY MOD CHANGES"

func _browse_mods() -> void:
	var result := OS.shell_open(GAMEBANANA_URL)
	if result != OK:
		_set_status("Could not open GameBanana: %s" % error_string(result))
	else:
		_set_status("Opened the SMB1R mods page in your browser.")

func _choose_mod_zip() -> void:
	picker_open = true
	_set_status("Choose a Godot Mod Loader ZIP.")

	if DisplayServer.has_feature(DisplayServer.FEATURE_NATIVE_DIALOG_FILE):
		var result := DisplayServer.file_dialog_show(
			"Choose SMB1R Mod ZIP",
			"",
			"",
			false,
			DisplayServer.FILE_DIALOG_MODE_OPEN_FILE,
			PackedStringArray(["*.zip;ZIP Mod;application/zip"]),
			_on_native_file_dialog
		)
		if result != OK:
			picker_open = false
			_set_status("Could not open Android file picker: %s" % error_string(result))
		return

	picker_open = false
	_open_fallback_file_dialog()

func _on_native_file_dialog(status: bool, selected_paths: PackedStringArray, _selected_filter_index: int) -> void:
	picker_open = false
	if not status or selected_paths.is_empty():
		_set_status("Install cancelled.")
		return
	_install_mod_zip(selected_paths[0])

func _open_fallback_file_dialog() -> void:
	var dialog := FileDialog.new()
	dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	dialog.access = FileDialog.ACCESS_FILESYSTEM
	dialog.filters = PackedStringArray(["*.zip ; ZIP Mod"])
	dialog.file_selected.connect(_on_fallback_file_selected.bind(dialog))
	dialog.canceled.connect(_on_fallback_file_cancelled.bind(dialog))
	add_child(dialog)
	dialog.popup_centered_ratio(0.85)

func _on_fallback_file_selected(path: String, dialog: FileDialog) -> void:
	dialog.queue_free()
	_install_mod_zip(path)

func _on_fallback_file_cancelled(dialog: FileDialog) -> void:
	dialog.queue_free()
	_set_status("Install cancelled.")

func _install_mod_zip(source_path: String) -> void:
	if not _ensure_mod_dir():
		return

	_set_status("Checking mod ZIP...")
	if not _copy_file(source_path, TEMP_IMPORT):
		_set_status("Could not read the selected ZIP.")
		return

	var info := _inspect_mod_zip(TEMP_IMPORT)
	if not info.get("ok", false):
		_delete_temp_import()
		_set_status("Not a usable GML mod: %s" % info.get("error", "invalid ZIP"))
		return

	var blocked_files: Array = info.get("blocked_files", [])
	if not blocked_files.is_empty():
		_delete_temp_import()
		_set_status("Android install blocked: this mod contains Windows .DLL/.EXE files.")
		return

	var mod_id := str(info.get("id", ""))
	if mod_id.is_empty():
		_delete_temp_import()
		_set_status("Mod manifest has no usable mod ID.")
		return

	var destination := MOD_DIR.path_join(mod_id + ".zip")
	if not _copy_file(TEMP_IMPORT, destination):
		_delete_temp_import()
		_set_status("Could not copy the mod into the Android mods folder.")
		return

	_delete_temp_import()
	restart_required = true
	_set_status("Installed/updated %s. Restart the game to load it." % info.get("name", mod_id))
	_refresh_mod_list()

func _inspect_mod_zip(path: String) -> Dictionary:
	var reader := ZIPReader.new()
	var open_error := reader.open(path)
	if open_error != OK:
		return {"ok": false, "error": "ZIP could not be opened (%s)" % error_string(open_error)}

	var blocked_files: Array = []
	for entry in reader.get_files():
		var extension := entry.get_extension().to_lower()
		if extension in BLOCKED_WINDOWS_EXTENSIONS:
			blocked_files.append(entry)
	reader.close()

	var manifest_data: Dictionary = _ModLoaderFile.load_manifest_file(path)
	if manifest_data.is_empty():
		return {"ok": false, "error": "manifest.json was not found or could not be read"}

	var manifest := ModManifest.new(manifest_data, path)
	var mod_data := ModData.new(manifest, path)
	var errors: Array[String] = []
	errors.append_array(manifest.validation_messages_error)
	errors.append_array(mod_data.load_errors)
	if not errors.is_empty():
		return {"ok": false, "error": "; ".join(errors)}

	return {
		"ok": true,
		"id": manifest.get_mod_id(),
		"name": manifest.name,
		"version": manifest.version_number,
		"description": manifest.description,
		"blocked_files": blocked_files,
	}

func _copy_file(source_path: String, destination_path: String) -> bool:
	var source := FileAccess.open(source_path, FileAccess.READ)
	if source == null:
		return false
	var destination := FileAccess.open(destination_path, FileAccess.WRITE)
	if destination == null:
		source.close()
		return false

	const CHUNK_SIZE := 1024 * 1024
	while source.get_position() < source.get_length():
		var remaining := source.get_length() - source.get_position()
		destination.store_buffer(source.get_buffer(min(CHUNK_SIZE, remaining)))

	source.close()
	destination.close()
	return true

func _delete_temp_import() -> void:
	if FileAccess.file_exists(TEMP_IMPORT):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(TEMP_IMPORT))

func _set_status(message: String) -> void:
	if status_label != null:
		status_label.text = message.to_upper()
