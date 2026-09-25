class_name TitleScreenOptions
extends VBoxContainer

const ANDROID_MOD_MANAGER_SCRIPT = preload("res://Scripts/UI/AndroidModManager.gd")

@export var active := false

@export var can_exit := true

var selected_index := 0

@export var options: Array[Label] = []
@onready var title_screen_parent := owner

signal option_1_selected
signal option_2_selected
signal option_3_selected

signal closed

func _ready() -> void:
	if name == "Extras":
		_add_android_mod_manager_option()

func _process(_delta: float) -> void:
	if active:
		handle_inputs()

func open() -> void:
	title_screen_parent.active_options = self
	show()
	await get_tree().physics_frame
	active = true

func close() -> void:
	active = false
	hide()

func handle_inputs() -> void:
	if Global.multibind_action_just_pressed("ui_down"):
		selected_index += 1
		if Settings.file.audio.extra_sfx == 1:
			AudioManager.play_global_sfx("menu_move")
	if Global.multibind_action_just_pressed("ui_up"):
		selected_index -= 1
		if Settings.file.audio.extra_sfx == 1:
			AudioManager.play_global_sfx("menu_move")
	var amount := []
	for i in options:
		if i.visible:
			amount.append(i)
	selected_index = clamp(selected_index, 0, amount.size() - 1)
	if Global.multibind_action_just_pressed("ui_accept"):
		option_selected()
	elif can_exit and Global.multibind_action_just_pressed("ui_back"):
		close()
		closed.emit()

func option_selected() -> void:
	if name == "Extras" and selected_index == 2:
		_open_android_mod_manager()
		return
	active = false
	emit_signal("option_" + str(selected_index + 1) + "_selected")

func _add_android_mod_manager_option() -> void:
	if get_node_or_null("Mods") != null:
		return
	var mods_label := Label.new()
	mods_label.name = "Mods"
	mods_label.text = "MODS"
	mods_label.uppercase = true
	mods_label.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
	mods_label.add_theme_color_override("font_shadow_color", Color.BLACK)
	add_child(mods_label)
	var buffer := get_node_or_null("Buffer")
	if buffer != null:
		move_child(mods_label, buffer.get_index())
	options.append(mods_label)

func _open_android_mod_manager() -> void:
	close()
	var manager := get_parent().get_node_or_null("AndroidModManager")
	if manager == null:
		manager = ANDROID_MOD_MANAGER_SCRIPT.new()
		manager.name = "AndroidModManager"
		get_parent().add_child(manager)
		manager.closed.connect(_on_android_mod_manager_closed)
	manager.open()

func _on_android_mod_manager_closed() -> void:
	open()
