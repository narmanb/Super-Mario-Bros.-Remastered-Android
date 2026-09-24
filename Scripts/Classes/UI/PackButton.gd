class_name PackButton
extends Button

@onready var resource_getter = ResourceGetter.new()

func _android_can_keep_current_icon(current_icon: Resource) -> bool:
	if OS.get_name() != "Android" or current_icon == null or current_icon is AtlasTexture:
		return false
	if ResourceGetter.cache.has(current_icon.resource_path):
		return false
	return resource_getter.get_resource_path(current_icon.resource_path) == current_icon.resource_path

func _ready() -> void:
	add_child(resource_getter)
	update()
	Global.level_theme_changed.connect(update)

func update() -> void:
	var current_icon = icon
	if _android_can_keep_current_icon(current_icon):
		return
	icon = resource_getter.get_resource(current_icon)
