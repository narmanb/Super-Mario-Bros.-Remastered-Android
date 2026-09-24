class_name PackSprite
extends Sprite2D

@onready var resource_getter = ResourceGetter.new()

func _android_can_keep_current_texture(current_texture: Resource) -> bool:
	if OS.get_name() != "Android" or current_texture == null or current_texture is AtlasTexture:
		return false
	if ResourceGetter.cache.has(current_texture.resource_path):
		return false
	return resource_getter.get_resource_path(current_texture.resource_path) == current_texture.resource_path

func _ready() -> void:
	update()
	Global.level_theme_changed.connect(update)

func update() -> void:
	var current_texture = texture
	if _android_can_keep_current_texture(current_texture):
		return
	texture = resource_getter.get_resource(current_texture)
