@tool
extends EditorPlugin

var export_plugin: AndroidExportPlugin

func _enter_tree() -> void:
	export_plugin = AndroidExportPlugin.new()
	add_export_plugin(export_plugin)

func _exit_tree() -> void:
	remove_export_plugin(export_plugin)
	export_plugin = null

class AndroidExportPlugin extends EditorExportPlugin:
	var _plugin_name := "AndroidFilePicker"

	func _supports_platform(platform) -> bool:
		return platform is EditorExportPlatformAndroid

	func _get_android_libraries(_platform, debug: bool) -> PackedStringArray:
		if debug:
			return PackedStringArray(["AndroidFilePicker/app-debug.aar"])
		return PackedStringArray(["AndroidFilePicker/app-release.aar"])

	func _get_android_dependencies(_platform, _debug: bool) -> PackedStringArray:
		# Godot 4.6's Android SAF implementation uses DocumentFile when opening
		# a picked folder's children. Gradle exports need it in the app module.
		return PackedStringArray(["androidx.documentfile:documentfile:1.1.0"])

	func _get_name() -> String:
		return _plugin_name
