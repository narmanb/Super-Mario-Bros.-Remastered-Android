extends Node
const RESOURCE_PACK_CONTAINER = preload("res://Scenes/Prefabs/UI/ResourcePackContainer.tscn")
const SELECTABLE_OPTION_BUTTON = preload("res://Scenes/Parts/SelectableOptionButton.tscn")

const TEMP_IMPORT := "user://resource_pack_import_pending.zip"
const INSTALL_TITLE := "INSTALL ZIP"
const INSTALL_FOLDER_TITLE := "INSTALL FOLDER"

var resource_packs := []
var containers := []
var picker_open := false
var folder_install_option: Control = null


func _ready() -> void:
	if OS.get_name() == "Android":
		var install_option = get_node_or_null("../VBoxContainer/SelectableOptionNode")
		if install_option != null and install_option.has_method("set_title"):
			install_option.set_title(INSTALL_TITLE)
		_add_android_folder_install_option()
	get_resource_packs()

func _add_android_folder_install_option() -> void:
	if folder_install_option != null:
		return
	var option_parent := get_node_or_null("../VBoxContainer")
	if option_parent == null:
		return
	folder_install_option = SELECTABLE_OPTION_BUTTON.instantiate()
	folder_install_option.name = "InstallFolderOption"
	folder_install_option.set_title(INSTALL_FOLDER_TITLE)
	folder_install_option.button_pressed.connect(_choose_resource_pack_folder)
	option_parent.add_child(folder_install_option)
	option_parent.move_child(folder_install_option, 1)
	folder_install_option.add_to_group("Options")
	get_parent().options.insert(1, folder_install_option)

func open_folder() -> void:
	if OS.get_name() == "Android":
		_choose_resource_pack_zip()
		return
	OS.shell_show_in_file_manager(ProjectSettings.globalize_path(Global.config_path.path_join("resource_packs")), true)

func _choose_resource_pack_zip() -> void:
	if picker_open:
		return
	picker_open = true

	if DisplayServer.has_feature(DisplayServer.FEATURE_NATIVE_DIALOG_FILE):
		var result := DisplayServer.file_dialog_show(
			"Choose SMB1R Resource Pack ZIP",
			"",
			"",
			false,
			DisplayServer.FILE_DIALOG_MODE_OPEN_FILE,
			PackedStringArray(["*.zip;ZIP Resource Pack;application/zip"]),
			_on_native_file_dialog
		)
		if result != OK:
			picker_open = false
			_show_import_error("Could not open the Android file picker: %s" % error_string(result))
		return

	picker_open = false
	_open_fallback_file_dialog()

func _choose_resource_pack_folder() -> void:
	if picker_open:
		return
	if not DisplayServer.has_feature(DisplayServer.FEATURE_NATIVE_DIALOG_FILE):
		_show_import_error("This Android build does not provide the native folder picker.")
		return
	picker_open = true
	var result := DisplayServer.file_dialog_show(
		"Choose Extracted SMB1R Resource Pack Folder",
		"",
		"",
		false,
		DisplayServer.FILE_DIALOG_MODE_OPEN_DIR,
		PackedStringArray(),
		_on_native_folder_dialog
	)
	if result != OK:
		picker_open = false
		_show_import_error("Could not open the Android folder picker: %s" % error_string(result))

func _on_native_file_dialog(status: bool, selected_paths: PackedStringArray, _selected_filter_index: int) -> void:
	picker_open = false
	if not status or selected_paths.is_empty():
		return
	_install_resource_pack_zip(selected_paths[0])

func _on_native_folder_dialog(status: bool, selected_paths: PackedStringArray, _selected_filter_index: int) -> void:
	picker_open = false
	if not status or selected_paths.is_empty():
		return
	_install_resource_pack_folder(selected_paths[0])

func _open_fallback_file_dialog() -> void:
	var dialog := FileDialog.new()
	dialog.file_mode = FileDialog.FILE_MODE_OPEN_FILE
	dialog.access = FileDialog.ACCESS_FILESYSTEM
	dialog.filters = PackedStringArray(["*.zip ; ZIP Resource Pack"])
	dialog.file_selected.connect(_on_fallback_file_selected.bind(dialog))
	dialog.canceled.connect(_on_fallback_file_cancelled.bind(dialog))
	owner.add_child(dialog)
	dialog.popup_centered_ratio(0.85)

func _on_fallback_file_selected(path: String, dialog: FileDialog) -> void:
	dialog.queue_free()
	_install_resource_pack_zip(path)

func _on_fallback_file_cancelled(dialog: FileDialog) -> void:
	dialog.queue_free()

func _install_resource_pack_folder(tree_uri: String) -> void:
	var pack_info_path := tree_uri + "#pack_info.json"
	if not FileAccess.file_exists(pack_info_path):
		_show_import_error("The selected folder does not contain pack_info.json at its root. Select the resource-pack folder itself.")
		return

	var pack_info_text := FileAccess.get_file_as_string(pack_info_path)
	var parsed = JSON.parse_string(pack_info_text)
	if not parsed is Dictionary or parsed.is_empty():
		_show_import_error("The selected folder's pack_info.json is not valid JSON.")
		return

	var folder_name := _sanitise_folder_name(str(parsed.get("name", "Resource Pack")))
	if folder_name.is_empty() or folder_name == Global.ROM_PACK_NAME:
		_show_import_error("The resource pack has an invalid folder name.")
		return

	var destination: String = Global.config_path.path_join("resource_packs").path_join(folder_name)
	if DirAccess.dir_exists_absolute(destination):
		_show_import_error("A resource pack named '%s' is already installed." % folder_name)
		return

	var make_error := DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(destination))
	if make_error != OK:
		_show_import_error("Could not create the resource pack folder: %s" % error_string(make_error))
		return

	var copy_error := _copy_android_saf_tree(tree_uri, destination)
	if not copy_error.is_empty():
		_remove_dir_recursive(destination)
		_show_import_error(copy_error)
		return

	if not FileAccess.file_exists(destination.path_join("pack_info.json")):
		_remove_dir_recursive(destination)
		_show_import_error("Folder import finished without a pack_info.json file.")
		return

	get_resource_packs()
	OS.alert("Installed '%s' from its extracted folder. It is now available in the Resource Packs list." % folder_name, "Resource Pack Installed")

func _copy_android_saf_tree(tree_uri: String, destination: String) -> String:
	if OS.get_name() != "Android":
		return "Folder import through Android Storage Access Framework is only available on Android."

	var android_runtime = Engine.get_singleton("AndroidRuntime")
	if android_runtime == null:
		return "AndroidRuntime is unavailable, so the selected folder could not be copied."

	var Uri = JavaClassWrapper.wrap("android.net.Uri")
	var DocumentsContract = JavaClassWrapper.wrap("android.provider.DocumentsContract")
	var Document = JavaClassWrapper.wrap("android.provider.DocumentsContract$Document")
	var tree_uri_object = Uri.parse(tree_uri)
	if tree_uri_object == null:
		return "Android could not parse the selected folder URI."

	var resolver = android_runtime.getApplicationContext().getContentResolver()
	if resolver == null:
		return "Android's content resolver is unavailable."

	var root_document_id = DocumentsContract.getTreeDocumentId(tree_uri_object)
	var java_error := _take_java_exception()
	if not java_error.is_empty():
		return "Could not inspect the selected Android folder: %s" % java_error
	if root_document_id == null or str(root_document_id).is_empty():
		return "Android did not return a document ID for the selected folder."

	return _copy_android_document_children(tree_uri_object, str(root_document_id), destination, resolver, DocumentsContract, Document)

func _copy_android_document_children(tree_uri_object, parent_document_id: String, destination: String, resolver, DocumentsContract, Document) -> String:
	var children_uri = DocumentsContract.buildChildDocumentsUriUsingTree(tree_uri_object, parent_document_id)
	var java_error := _take_java_exception()
	if not java_error.is_empty():
		return "Could not enumerate the selected folder: %s" % java_error
	if children_uri == null:
		return "Android did not return the selected folder's contents."

	var projection := PackedStringArray([
		str(Document.COLUMN_DOCUMENT_ID),
		str(Document.COLUMN_DISPLAY_NAME),
		str(Document.COLUMN_MIME_TYPE)
	])
	var cursor = resolver.query(children_uri, projection, null, null, null)
	java_error = _take_java_exception()
	if not java_error.is_empty():
		return "Could not read the selected folder: %s" % java_error
	if cursor == null:
		return "Android could not read the selected folder."

	var id_index := cursor.getColumnIndex(str(Document.COLUMN_DOCUMENT_ID))
	var name_index := cursor.getColumnIndex(str(Document.COLUMN_DISPLAY_NAME))
	var mime_index := cursor.getColumnIndex(str(Document.COLUMN_MIME_TYPE))
	java_error = _take_java_exception()
	if not java_error.is_empty() or id_index < 0 or name_index < 0 or mime_index < 0:
		cursor.close()
		_take_java_exception()
		return "Android returned an unexpected folder listing format."

	while cursor.moveToNext():
		var document_id := str(cursor.getString(id_index))
		var display_name := str(cursor.getString(name_index))
		var mime_type := str(cursor.getString(mime_index))
		java_error = _take_java_exception()
		if not java_error.is_empty():
			cursor.close()
			_take_java_exception()
			return "Could not read an item in the selected folder: %s" % java_error

		if not _is_safe_android_filename(display_name):
			cursor.close()
			_take_java_exception()
			return "The selected folder contains an unsafe file or folder name and was not installed."
		if display_name == ".DS_Store" or display_name == "__MACOSX":
			continue

		var output_path := destination.path_join(display_name)
		if mime_type == str(Document.MIME_TYPE_DIR):
			var dir_error := DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output_path))
			if dir_error != OK:
				cursor.close()
				_take_java_exception()
				return "Could not create '%s' while importing the resource pack." % display_name
			var child_error := _copy_android_document_children(tree_uri_object, document_id, output_path, resolver, DocumentsContract, Document)
			if not child_error.is_empty():
				cursor.close()
				_take_java_exception()
				return child_error
		else:
			var document_uri = DocumentsContract.buildDocumentUriUsingTree(tree_uri_object, document_id)
			java_error = _take_java_exception()
			if not java_error.is_empty() or document_uri == null:
				cursor.close()
				_take_java_exception()
				return "Could not open '%s' from the selected folder." % display_name
			var parent_error := DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output_path.get_base_dir()))
			if parent_error != OK:
				cursor.close()
				_take_java_exception()
				return "Could not create a destination folder while importing '%s'." % display_name
			if not _copy_file(str(document_uri.toString()), output_path):
				cursor.close()
				_take_java_exception()
				return "Could not copy '%s' from the selected folder." % display_name

	cursor.close()
	java_error = _take_java_exception()
	if not java_error.is_empty():
		return "Android reported an error after reading the selected folder: %s" % java_error
	return ""

func _take_java_exception() -> String:
	var exception = JavaClassWrapper.get_exception()
	if exception == null:
		return ""
	return str(exception.toString())

func _is_safe_android_filename(value: String) -> bool:
	if value.is_empty() or value == "." or value == "..":
		return false
	return not value.contains("/") and not value.contains("\\") and not value.contains("\u0000")

func _install_resource_pack_zip(source_path: String) -> void:
	_delete_temp_import()
	if not _copy_file(source_path, TEMP_IMPORT):
		_show_import_error("The selected ZIP could not be read.")
		return

	var inspection := _inspect_resource_pack_zip(TEMP_IMPORT)
	if not inspection.get("ok", false):
		_delete_temp_import()
		_show_import_error(str(inspection.get("error", "This is not a valid SMB1R resource pack.")))
		return

	var folder_name := str(inspection.get("folder_name", ""))
	if folder_name.is_empty() or folder_name == Global.ROM_PACK_NAME:
		_delete_temp_import()
		_show_import_error("The resource pack has an invalid folder name.")
		return

	var destination: String = Global.config_path.path_join("resource_packs").path_join(folder_name)
	if DirAccess.dir_exists_absolute(destination):
		_delete_temp_import()
		_show_import_error("A resource pack named '%s' is already installed." % folder_name)
		return

	var extraction_error := _extract_resource_pack(TEMP_IMPORT, destination, str(inspection.get("prefix", "")))
	_delete_temp_import()
	if not extraction_error.is_empty():
		_remove_dir_recursive(destination)
		_show_import_error(extraction_error)
		return

	get_resource_packs()
	OS.alert("Installed '%s'. It is now available in the Resource Packs list." % folder_name, "Resource Pack Installed")

func _inspect_resource_pack_zip(path: String) -> Dictionary:
	var reader := ZIPReader.new()
	var open_error := reader.open(path)
	if open_error != OK:
		return {"ok": false, "error": "The ZIP could not be opened: %s" % error_string(open_error)}

	var files := reader.get_files()
	var pack_info_entry := ""
	var wrapper_candidates: Array[String] = []

	for raw_entry in files:
		var entry := _normalise_zip_path(raw_entry)
		if not _is_safe_zip_path(entry):
			reader.close()
			return {"ok": false, "error": "The ZIP contains an unsafe path and was not installed."}
		if _is_ignored_zip_entry(entry) or entry.ends_with("/"):
			continue
		if entry == "pack_info.json":
			pack_info_entry = entry
			break
		if entry.get_file() == "pack_info.json":
			var base_dir := entry.get_base_dir()
			if not base_dir.is_empty() and not base_dir.contains("/"):
				wrapper_candidates.append(entry)

	if pack_info_entry.is_empty():
		if wrapper_candidates.size() != 1:
			reader.close()
			return {"ok": false, "error": "Could not find a single pack_info.json at the ZIP root or inside one top-level pack folder."}
		pack_info_entry = wrapper_candidates[0]

	var pack_info_bytes := reader.read_file(pack_info_entry)
	if pack_info_bytes.is_empty():
		reader.close()
		return {"ok": false, "error": "pack_info.json could not be read."}

	var parsed = JSON.parse_string(pack_info_bytes.get_string_from_utf8())
	if not parsed is Dictionary or parsed.is_empty():
		reader.close()
		return {"ok": false, "error": "pack_info.json is not valid JSON."}

	var prefix := ""
	var folder_name := ""
	if pack_info_entry == "pack_info.json":
		folder_name = _sanitise_folder_name(str(parsed.get("name", "Resource Pack")))
	else:
		prefix = pack_info_entry.get_base_dir() + "/"
		folder_name = pack_info_entry.get_base_dir()

	reader.close()
	if folder_name.is_empty():
		return {"ok": false, "error": "The resource pack name could not be used as a folder name."}
	return {"ok": true, "prefix": prefix, "folder_name": folder_name}

func _extract_resource_pack(zip_path: String, destination: String, prefix: String) -> String:
	var make_error := DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(destination))
	if make_error != OK:
		return "Could not create the resource pack folder: %s" % error_string(make_error)

	var reader := ZIPReader.new()
	var open_error := reader.open(zip_path)
	if open_error != OK:
		return "The ZIP could not be reopened for extraction: %s" % error_string(open_error)

	for raw_entry in reader.get_files():
		var entry := _normalise_zip_path(raw_entry)
		if not _is_safe_zip_path(entry):
			reader.close()
			return "The ZIP contains an unsafe path and was not installed."
		if _is_ignored_zip_entry(entry):
			continue

		var relative := entry
		if not prefix.is_empty():
			if not entry.begins_with(prefix):
				continue
			relative = entry.trim_prefix(prefix)
		if relative.is_empty():
			continue

		var output_path := destination.path_join(relative)
		if entry.ends_with("/"):
			var dir_error := DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(output_path))
			if dir_error != OK:
				reader.close()
				return "Could not create a folder while extracting the resource pack."
			continue

		var parent_dir := output_path.get_base_dir()
		var parent_error := DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(parent_dir))
		if parent_error != OK:
			reader.close()
			return "Could not create a folder while extracting the resource pack."

		var output := FileAccess.open(output_path, FileAccess.WRITE)
		if output == null:
			reader.close()
			return "Could not write '%s' into the resource pack folder." % relative
		output.store_buffer(reader.read_file(entry))
		output.close()

	reader.close()
	if not FileAccess.file_exists(destination.path_join("pack_info.json")):
		return "Extraction finished without a pack_info.json file."
	return ""

func _normalise_zip_path(path: String) -> String:
	return path.replace("\\", "/").trim_prefix("./")

func _is_safe_zip_path(path: String) -> bool:
	if path.is_empty() or path.begins_with("/"):
		return false
	if path.length() >= 2 and path.substr(1, 1) == ":":
		return false
	for part in path.split("/", false):
		if part == "..":
			return false
	return true

func _is_ignored_zip_entry(path: String) -> bool:
	return path.begins_with("__MACOSX/") or path.get_file() == ".DS_Store"

func _sanitise_folder_name(value: String) -> String:
	var result := ""
	for character in value.strip_edges():
		var lower := character.to_lower()
		if "abcdefghijklmnopqrstuvwxyz0123456789-_. ".contains(lower):
			result += character
		else:
			result += "_"
	result = result.strip_edges().trim_suffix(".")
	if result == "." or result == "..":
		return ""
	return result

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

func _remove_dir_recursive(path: String) -> void:
	if not DirAccess.dir_exists_absolute(path):
		return
	for file_name in DirAccess.get_files_at(path):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(path.path_join(file_name)))
	for dir_name in DirAccess.get_directories_at(path):
		_remove_dir_recursive(path.path_join(dir_name))
	DirAccess.remove_absolute(ProjectSettings.globalize_path(path))

func _show_import_error(message: String) -> void:
	OS.alert(message, "Resource Pack Import Failed")

func get_resource_packs() -> void:
	for i in containers:
		get_parent().options.erase(i)
		i.queue_free()
	containers = []
	resource_packs = []
	for i in DirAccess.get_directories_at(Global.config_path.path_join("resource_packs")):
		resource_packs.append(i)
	for i in resource_packs:
		var pack_info_path = Global.config_path.path_join("resource_packs/" + i + "/pack_info.json")
		if FileAccess.file_exists(pack_info_path) and i != Global.ROM_PACK_NAME:
			create_container(Global.config_path.path_join("resource_packs/" + i))

func create_container(resource_pack := "") -> void:
	var container = RESOURCE_PACK_CONTAINER.instantiate()
	container.pack_json = JSONParser.parse_to_dict(resource_pack + "/pack_info.json")
	if FileAccess.file_exists(resource_pack + "/config.json"):
		container.config = JSONParser.parse_to_dict(resource_pack + "/config.json")
		container.config_path = resource_pack + "/config.json"
	if FileAccess.file_exists(resource_pack + "/icon.png"):
		var image = Image.new()
		image.load(resource_pack + "/icon.png")
		container.icon = ImageTexture.create_from_image(image)
	elif FileAccess.file_exists(resource_pack + "/icon.gif"):
		container.icon = GifManager.animated_texture_from_file(resource_pack + "/icon.gif")
	container.pack_id = resource_pack.replace(Global.config_path.path_join("resource_packs"), "").trim_prefix("/")
	$"../ScrollContainer/VBoxContainer".add_child(container)
	containers.append(container)
	container.add_to_group("Options")
	container.open_config.connect(owner.open_pack_config_menu)
	get_parent().options.append(container)
