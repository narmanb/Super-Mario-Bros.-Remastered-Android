class_name AndroidTitleScreenLifecycleProbe
extends TitleScreen

# Android-only diagnostic shim. The real TitleScreen.gd remains untouched.
enum ProbeMode {
	SKIP_BOTH,
	ENTER_ONLY,
	READY_ONLY,
}

static var probe_mode: ProbeMode = ProbeMode.SKIP_BOTH

func _enter_tree() -> void:
	print("[ANDROID_TITLE_ROOT_PROBE] subclass _enter_tree mode=", probe_mode)
	if probe_mode == ProbeMode.SKIP_BOTH or probe_mode == ProbeMode.READY_ONLY:
		return
	super._enter_tree()

func _ready() -> void:
	print("[ANDROID_TITLE_ROOT_PROBE] subclass _ready mode=", probe_mode)
	if probe_mode == ProbeMode.SKIP_BOTH or probe_mode == ProbeMode.ENTER_ONLY:
		return
	super._ready()
