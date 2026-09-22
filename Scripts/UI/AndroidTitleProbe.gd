extends CanvasLayer

const TITLE_PATH := "res://Scenes/Levels/TitleScreen.tscn"

@onready var label: Label = $Background/Label

func _ready() -> void:
	Global.get_node("GameHUD").hide()
	call_deferred("_run_probe")

func _exit_tree() -> void:
	Global.get_node("GameHUD").show()

func _show_stage(message: String, seconds := 2.5) -> void:
	label.text = message
	print("[ANDROID_TITLE_PROBE] ", message.replace("\n", " - "))
	await get_tree().create_timer(seconds, false).timeout

func _run_probe() -> void:
	await _show_stage("TITLE PROBE 1/8\nPROBE SCENE READY")
	await _show_stage("TITLE PROBE 2/8\nBEFORE TITLE LOAD")

	var packed := ResourceLoader.load(TITLE_PATH) as PackedScene
	if packed == null:
		label.text = "TITLE PROBE FAILED\nTITLE LOAD RETURNED NULL"
		push_error("[ANDROID_TITLE_PROBE] TitleScreen load returned null")
		return

	await _show_stage("TITLE PROBE 3/8\nTITLE LOAD RETURNED")
	await _show_stage("TITLE PROBE 4/8\nBEFORE INSTANTIATE")

	var title_scene := packed.instantiate()
	if title_scene == null:
		label.text = "TITLE PROBE FAILED\nINSTANTIATE RETURNED NULL"
		push_error("[ANDROID_TITLE_PROBE] TitleScreen instantiate returned null")
		return

	await _show_stage("TITLE PROBE 5/8\nINSTANTIATE RETURNED")
	await _show_stage("TITLE PROBE 6/8\nBEFORE ADD_CHILD")

	var host := get_parent()
	host.add_child(title_scene)

	await _show_stage("TITLE PROBE 7/8\nADD_CHILD RETURNED", 3.0)
	await get_tree().process_frame
	label.text = "TITLE PROBE 8/8\nTITLE SURVIVED FIRST FRAME"
	print("[ANDROID_TITLE_PROBE] TitleScreen survived first frame")
