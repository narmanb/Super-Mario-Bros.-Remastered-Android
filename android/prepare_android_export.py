#!/usr/bin/env python3
"""Prepare the upstream 1.1 project for a reproducible Godot 4.6 Android build.

The script intentionally keeps most Android-only changes out of upstream project files:
- downloads the proven native file-picker AARs from the previous Android port,
- installs a first-pass phone touch overlay using the previous Android port's sprites,
- disables the desktop Discord GDExtension for the Android export,
- applies the mobile layout/orientation settings used by the working 1.0.2 port,
- enables ETC2/ASTC imports required for Android export from an x86_64 host,
- appends a minimal ARM64 Android export preset if one is not present.
"""

from __future__ import annotations

import re
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_ANDROID_COMMIT = "61fe0a6464101981cbee56701955fc0005f59664"
OLD_ANDROID_RAW = (
    "https://raw.githubusercontent.com/"
    "mircowuffwuff/super-mario-bros.-remastered-android/"
    f"{OLD_ANDROID_COMMIT}"
)

TOUCH_ASSETS = (
    "A.png",
    "AHeld.png",
    "B.png",
    "BHeld.png",
    "Down.png",
    "DownHeld.png",
    "Left.png",
    "LeftHeld.png",
    "Right.png",
    "RightHeld.png",
    "RunLock.png",
    "RunLockOn.png",
    "Start.png",
    "StartHeld.png",
    "Up.png",
    "UpHeld.png",
)

TOUCH_SCRIPT = r'''extends CanvasLayer

# First-pass Android touch layer for 1.1. The layout/sprites come from the
# established 1.0.2 Android port, while the input handling targets 1.1's
# current action map directly.

const LEFT = preload("res://Assets/Sprites/UI/OnScreenControls/Left.png")
const LEFT_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/LeftHeld.png")
const RIGHT = preload("res://Assets/Sprites/UI/OnScreenControls/Right.png")
const RIGHT_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/RightHeld.png")
const UP = preload("res://Assets/Sprites/UI/OnScreenControls/Up.png")
const UP_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/UpHeld.png")
const DOWN = preload("res://Assets/Sprites/UI/OnScreenControls/Down.png")
const DOWN_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/DownHeld.png")
const A = preload("res://Assets/Sprites/UI/OnScreenControls/A.png")
const A_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/AHeld.png")
const B = preload("res://Assets/Sprites/UI/OnScreenControls/B.png")
const B_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/BHeld.png")
const START = preload("res://Assets/Sprites/UI/OnScreenControls/Start.png")
const START_HELD = preload("res://Assets/Sprites/UI/OnScreenControls/StartHeld.png")
const RUN_LOCK = preload("res://Assets/Sprites/UI/OnScreenControls/RunLock.png")
const RUN_LOCK_ON = preload("res://Assets/Sprites/UI/OnScreenControls/RunLockOn.png")

# Android exposes some touchscreen/input drivers as joypads. Do not let those
# hide the phone controls. A real RP5/Bluetooth controller still hides them.
const FAKE_JOYPAD_PREFIXES := ["uinput"]

@onready var left: Sprite2D = $LeftControls/LeftSprite
@onready var right: Sprite2D = $LeftControls/RightSprite
@onready var up: Sprite2D = $LeftControls/UpSprite
@onready var down: Sprite2D = $LeftControls/DownSprite
@onready var a: Sprite2D = $RightControls/ASprite
@onready var b: Sprite2D = $RightControls/BSprite
@onready var start: Sprite2D = $RightControls/StartSprite
@onready var run_lock: Sprite2D = $RightControls/RunLockSprite

var run_lock_on := false

func _ready() -> void:
    _update_visibility()

func _process(_delta: float) -> void:
    _update_visibility()

func _update_visibility() -> void:
    var should_be_visible := not _has_real_controller()
    if visible and not should_be_visible:
        _release_all_actions()
        run_lock_on = false
        run_lock.texture = RUN_LOCK
    visible = should_be_visible

func _has_real_controller() -> bool:
    for device_id in Input.get_connected_joypads():
        var joy_name := Input.get_joy_name(device_id).to_lower()
        var fake := false
        for prefix in FAKE_JOYPAD_PREFIXES:
            if joy_name.begins_with(prefix):
                fake = true
                break
        if not fake:
            return true
    return false

func _haptic() -> void:
    Input.vibrate_handheld(12, 0.45)

func _press(actions: Array[StringName]) -> void:
    for action in actions:
        Input.action_press(action)

func _release(actions: Array[StringName]) -> void:
    for action in actions:
        Input.action_release(action)

func on_west_pressed() -> void:
    left.texture = LEFT_HELD
    _haptic()
    _press([&"move_left_0", &"ui_left"])

func on_west_released() -> void:
    left.texture = LEFT
    _release([&"move_left_0", &"ui_left"])

func on_east_pressed() -> void:
    right.texture = RIGHT_HELD
    _haptic()
    _press([&"move_right_0", &"ui_right"])

func on_east_released() -> void:
    right.texture = RIGHT
    _release([&"move_right_0", &"ui_right"])

func on_north_pressed() -> void:
    up.texture = UP_HELD
    _haptic()
    _press([&"move_up_0", &"ui_up"])

func on_north_released() -> void:
    up.texture = UP
    _release([&"move_up_0", &"ui_up"])

func on_south_pressed() -> void:
    down.texture = DOWN_HELD
    _haptic()
    _press([&"move_down_0", &"ui_down"])

func on_south_released() -> void:
    down.texture = DOWN
    _release([&"move_down_0", &"ui_down"])

func on_a_pressed() -> void:
    a.texture = A_HELD
    _haptic()
    _press([&"jump_0", &"ui_accept"])

func on_a_released() -> void:
    a.texture = A
    _release([&"jump_0", &"ui_accept"])

func on_b_pressed() -> void:
    b.texture = B_HELD
    _haptic()
    Input.action_press(&"action_0")
    Input.action_press(&"ui_cancel")
    if not run_lock_on:
        Input.action_press(&"run_0")

func on_b_released() -> void:
    b.texture = B
    Input.action_release(&"action_0")
    Input.action_release(&"ui_cancel")
    if not run_lock_on:
        Input.action_release(&"run_0")

func on_run_lock_pressed() -> void:
    run_lock_on = not run_lock_on
    run_lock.texture = RUN_LOCK_ON if run_lock_on else RUN_LOCK
    if run_lock_on:
        Input.action_press(&"run_0")
    else:
        Input.action_release(&"run_0")
    _haptic()

func on_start_pressed() -> void:
    start.texture = START_HELD
    _haptic()
    Input.action_press(&"pause")

func on_start_released() -> void:
    start.texture = START
    Input.action_release(&"pause")

func _release_all_actions() -> void:
    _release([
        &"move_left_0", &"move_right_0", &"move_up_0", &"move_down_0",
        &"ui_left", &"ui_right", &"ui_up", &"ui_down",
        &"jump_0", &"ui_accept", &"action_0", &"ui_cancel", &"run_0", &"pause",
    ])

func _exit_tree() -> void:
    _release_all_actions()
'''

TOUCH_SCENE = r'''[gd_scene load_steps=18 format=3]

[ext_resource type="Script" path="res://Scripts/UI/OnScreenControls.gd" id="1_script"]
[ext_resource type="Texture2D" path="res://Assets/Sprites/UI/OnScreenControls/Left.png" id="2_left"]
[ext_resource type="Texture2D" path="res://Assets/Sprites/UI/OnScreenControls/Right.png" id="3_right"]
[ext_resource type="Texture2D" path="res://Assets/Sprites/UI/OnScreenControls/Up.png" id="4_up"]
[ext_resource type="Texture2D" path="res://Assets/Sprites/UI/OnScreenControls/Down.png" id="5_down"]
[ext_resource type="Texture2D" path="res://Assets/Sprites/UI/OnScreenControls/A.png" id="6_a"]
[ext_resource type="Texture2D" path="res://Assets/Sprites/UI/OnScreenControls/B.png" id="7_b"]
[ext_resource type="Texture2D" path="res://Assets/Sprites/UI/OnScreenControls/RunLock.png" id="8_lock"]
[ext_resource type="Texture2D" path="res://Assets/Sprites/UI/OnScreenControls/Start.png" id="9_start"]

[sub_resource type="RectangleShape2D" id="left_shape"]
size = Vector2(54, 66)

[sub_resource type="RectangleShape2D" id="right_shape"]
size = Vector2(54, 66)

[sub_resource type="RectangleShape2D" id="up_shape"]
size = Vector2(28, 46)

[sub_resource type="RectangleShape2D" id="down_shape"]
size = Vector2(28, 46)

[sub_resource type="RectangleShape2D" id="a_shape"]
size = Vector2(54, 54)

[sub_resource type="RectangleShape2D" id="b_shape"]
size = Vector2(54, 54)

[sub_resource type="RectangleShape2D" id="lock_shape"]
size = Vector2(44, 24)

[sub_resource type="RectangleShape2D" id="start_shape"]
size = Vector2(40, 24)

[node name="OnScreenControls" type="CanvasLayer"]
layer = 100
process_mode = 3
script = ExtResource("1_script")

[node name="LeftControls" type="Control" parent="."]
layout_mode = 3
anchors_preset = 2
anchor_top = 1.0
anchor_bottom = 1.0
offset_top = -141.0
offset_right = 141.0
grow_vertical = 0
mouse_filter = 2

[node name="LeftSprite" type="Sprite2D" parent="LeftControls"]
modulate = Color(1, 1, 1, 0.7058824)
position = Vector2(48, 61)
texture = ExtResource("2_left")

[node name="LeftButton" type="TouchScreenButton" parent="LeftControls"]
position = Vector2(39, 61)
shape = SubResource("left_shape")
passby_press = true

[node name="RightSprite" type="Sprite2D" parent="LeftControls"]
modulate = Color(1, 1, 1, 0.7058824)
position = Vector2(112, 61)
texture = ExtResource("3_right")

[node name="RightButton" type="TouchScreenButton" parent="LeftControls"]
position = Vector2(121, 61)
shape = SubResource("right_shape")
passby_press = true

[node name="UpSprite" type="Sprite2D" parent="LeftControls"]
modulate = Color(1, 1, 1, 0.7058824)
position = Vector2(80, 29)
texture = ExtResource("4_up")

[node name="UpButton" type="TouchScreenButton" parent="LeftControls"]
position = Vector2(80, 26)
shape = SubResource("up_shape")
passby_press = true

[node name="DownSprite" type="Sprite2D" parent="LeftControls"]
modulate = Color(1, 1, 1, 0.7058824)
position = Vector2(80, 93)
texture = ExtResource("5_down")

[node name="DownButton" type="TouchScreenButton" parent="LeftControls"]
position = Vector2(80, 96)
shape = SubResource("down_shape")
passby_press = true

[node name="RightControls" type="Control" parent="."]
layout_mode = 3
anchors_preset = 3
anchor_left = 1.0
anchor_top = 1.0
anchor_right = 1.0
anchor_bottom = 1.0
offset_left = -115.0
offset_top = -141.0
grow_horizontal = 0
grow_vertical = 0
mouse_filter = 2

[node name="ASprite" type="Sprite2D" parent="RightControls"]
modulate = Color(1, 1, 1, 0.7058824)
position = Vector2(43, 71)
texture = ExtResource("6_a")

[node name="AButton" type="TouchScreenButton" parent="RightControls"]
position = Vector2(50, 78)
shape = SubResource("a_shape")
passby_press = true

[node name="BSprite" type="Sprite2D" parent="RightControls"]
modulate = Color(1, 1, 1, 0.7058824)
position = Vector2(3, 51)
texture = ExtResource("7_b")

[node name="BButton" type="TouchScreenButton" parent="RightControls"]
position = Vector2(-4, 58)
shape = SubResource("b_shape")
passby_press = true

[node name="RunLockSprite" type="Sprite2D" parent="RightControls"]
modulate = Color(1, 1, 1, 0.7058824)
position = Vector2(43, 32)
texture = ExtResource("8_lock")

[node name="RunLockButton" type="TouchScreenButton" parent="RightControls"]
position = Vector2(45, 32)
shape = SubResource("lock_shape")

[node name="StartSprite" type="Sprite2D" parent="RightControls"]
modulate = Color(1, 1, 1, 0.7058824)
position = Vector2(-5, 101)
texture = ExtResource("9_start")

[node name="StartButton" type="TouchScreenButton" parent="RightControls"]
position = Vector2(-5, 101)
shape = SubResource("start_shape")

[connection signal="pressed" from="LeftControls/LeftButton" to="." method="on_west_pressed"]
[connection signal="released" from="LeftControls/LeftButton" to="." method="on_west_released"]
[connection signal="pressed" from="LeftControls/RightButton" to="." method="on_east_pressed"]
[connection signal="released" from="LeftControls/RightButton" to="." method="on_east_released"]
[connection signal="pressed" from="LeftControls/UpButton" to="." method="on_north_pressed"]
[connection signal="released" from="LeftControls/UpButton" to="." method="on_north_released"]
[connection signal="pressed" from="LeftControls/DownButton" to="." method="on_south_pressed"]
[connection signal="released" from="LeftControls/DownButton" to="." method="on_south_released"]
[connection signal="pressed" from="RightControls/AButton" to="." method="on_a_pressed"]
[connection signal="released" from="RightControls/AButton" to="." method="on_a_released"]
[connection signal="pressed" from="RightControls/BButton" to="." method="on_b_pressed"]
[connection signal="released" from="RightControls/BButton" to="." method="on_b_released"]
[connection signal="pressed" from="RightControls/RunLockButton" to="." method="on_run_lock_pressed"]
[connection signal="pressed" from="RightControls/StartButton" to="." method="on_start_pressed"]
[connection signal="released" from="RightControls/StartButton" to="." method="on_start_released"]
'''


def download_file_picker_aars() -> None:
    addon_dir = ROOT / "addons" / "AndroidFilePicker"
    addon_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("app-debug.aar", "app-release.aar"):
        destination = addon_dir / filename
        if destination.exists() and destination.stat().st_size > 0:
            continue
        url = f"{OLD_ANDROID_RAW}/addons/AndroidFilePicker/{filename}"
        print(f"Downloading {filename} from pinned Android-port commit")
        urllib.request.urlretrieve(url, destination)


def install_touch_controls() -> None:
    asset_dir = ROOT / "Assets" / "Sprites" / "UI" / "OnScreenControls"
    asset_dir.mkdir(parents=True, exist_ok=True)
    for filename in TOUCH_ASSETS:
        destination = asset_dir / filename
        if destination.exists() and destination.stat().st_size > 0:
            continue
        url = f"{OLD_ANDROID_RAW}/Assets/Sprites/UI/OnScreenControls/{filename}"
        print(f"Downloading touch-control sprite {filename}")
        urllib.request.urlretrieve(url, destination)

    script_path = ROOT / "Scripts" / "UI" / "OnScreenControls.gd"
    scene_path = ROOT / "Scenes" / "Prefabs" / "UI" / "OnScreenControls.tscn"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    scene_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(TOUCH_SCRIPT, encoding="utf-8")
    scene_path.write_text(TOUCH_SCENE, encoding="utf-8")


def patch_project_settings() -> None:
    path = ROOT / "project.godot"
    text = path.read_text(encoding="utf-8")

    # DiscordRPC is a desktop GDExtension. The runtime manager also has an
    # Android-safe stub, but removing the plugin itself avoids loading an
    # incompatible native library during import/export.
    text = text.replace("use_discord=true", "use_discord=false")
    text = text.replace(', "res://addons/discord-rpc-gd/plugin.cfg"', "")
    text = text.replace('"res://addons/discord-rpc-gd/plugin.cfg", ', "")

    # Autoload the phone overlay only in the generated Android project. The
    # overlay hides itself when a real controller (including the RP5 controls)
    # is connected, while ignoring Android's fake uinput joypads.
    touch_autoload = 'OnScreenControls="*res://Scenes/Prefabs/UI/OnScreenControls.tscn"'
    if touch_autoload not in text:
        debug_marker = "\n[debug]\n"
        if debug_marker not in text:
            raise RuntimeError("Could not locate end of [autoload] section")
        text = text.replace(debug_marker, f"\n{touch_autoload}\n{debug_marker}", 1)

    # Enable the Android export plugin without disturbing the other 1.1 tools.
    if 'res://addons/AndroidFilePicker/plugin.cfg' not in text:
        marker = "enabled=PackedStringArray("
        pos = text.find(marker)
        if pos == -1:
            raise RuntimeError("Could not find [editor_plugins] enabled list")
        insert_at = pos + len(marker)
        text = (
            text[:insert_at]
            + '"res://addons/AndroidFilePicker/plugin.cfg", '
            + text[insert_at:]
        )

    # Match the proven Android port's widescreen/landscape presentation while
    # retaining 1.1's gl_compatibility renderer.
    text = text.replace('window/stretch/mode="viewport"', 'window/stretch/mode="canvas_items"')
    if 'window/stretch/aspect="expand"' not in text:
        text = text.replace(
            'window/stretch/mode="canvas_items"',
            'window/stretch/mode="canvas_items"\nwindow/stretch/aspect="expand"',
        )
    if "window/handheld/orientation=4" not in text:
        text = text.replace(
            'window/stretch/aspect="expand"',
            'window/stretch/aspect="expand"\nwindow/handheld/orientation=4',
        )

    # Godot 4.6 Android export validates that ETC2/ASTC imports are enabled.
    # On an x86_64 Linux host, the default S3TC preference can otherwise yield
    # a blank "configuration errors" message (Godot issue #119895).
    etc2_setting = "textures/vram_compression/import_etc2_astc=true"
    if etc2_setting not in text:
        rendering_marker = "[rendering]\n"
        if rendering_marker in text:
            text = text.replace(rendering_marker, rendering_marker + "\n" + etc2_setting + "\n", 1)
        else:
            text = text.rstrip() + "\n\n[rendering]\n\n" + etc2_setting + "\n"

    path.write_text(text, encoding="utf-8")

    shutil.rmtree(ROOT / "addons" / "discord-rpc-gd", ignore_errors=True)


def append_android_export_preset() -> None:
    path = ROOT / "export_presets.cfg"
    text = path.read_text(encoding="utf-8")
    if re.search(r'^name="Android"$', text, flags=re.MULTILINE):
        print("Android export preset already present")
        return

    indices = [int(value) for value in re.findall(r"^\[preset\.(\d+)\]$", text, re.MULTILINE)]
    index = max(indices, default=-1) + 1

    preset = f'''\n\n[preset.{index}]\n\nname="Android"\nplatform="Android"\nrunnable=true\nadvanced_options=true\ndedicated_server=false\ncustom_features=""\nexport_filter="all_resources"\ninclude_filter="*.bgm, *.mp3, *.txt, *.fnt, version.txt"\nexclude_filter=""\nexport_path="build/SMB1R-1.1-android-debug.apk"\npatches=PackedStringArray()\nencryption_include_filters=""\nencryption_exclude_filters=""\nseed=0\nencrypt_pck=false\nencrypt_directory=false\nscript_export_mode=2\n\n[preset.{index}.options]\n\ncustom_template/debug=""\ncustom_template/release=""\ngradle_build/use_gradle_build=true\ngradle_build/gradle_build_directory=""\ngradle_build/android_source_template=""\ngradle_build/compress_native_libraries=false\ngradle_build/export_format=0\ngradle_build/min_sdk=""\ngradle_build/target_sdk=""\ngradle_build/custom_theme_attributes={{}}\narchitectures/armeabi-v7a=false\narchitectures/arm64-v8a=true\narchitectures/x86=false\narchitectures/x86_64=false\nversion/code=110\nversion/name="1.1-android-dev"\npackage/unique_name="com.narmanb.smb1r"\npackage/name="Super Mario Bros. Remastered"\npackage/signed=true\npackage/app_category=2\npackage/retain_data_on_uninstall=true\npackage/exclude_from_recents=false\npackage/show_in_android_tv=false\npackage/show_in_app_library=true\npackage/show_as_launcher_app=false\nlauncher_icons/main_192x192=""\nlauncher_icons/adaptive_foreground_432x432=""\nlauncher_icons/adaptive_background_432x432=""\nlauncher_icons/adaptive_monochrome_432x432=""\ngraphics/opengl_debug=false\nshader_baker/enabled=false\nxr_features/xr_mode=0\ngesture/swipe_to_dismiss=false\nscreen/immersive_mode=true\nscreen/support_small=true\nscreen/support_normal=true\nscreen/support_large=true\nscreen/support_xlarge=true\nscreen/edge_to_edge=true\nscreen/background_color=Color(0, 0, 0, 1)\nuser_data_backup/allow=true\ncommand_line/extra_args=""\napk_expansion/enable=false\napk_expansion/SALT=""\napk_expansion/public_key=""\npermissions/custom_permissions=PackedStringArray()\npermissions/internet=true\n'''

    path.write_text(text.rstrip() + preset + "\n", encoding="utf-8")
    print(f"Added Android export preset as preset.{index}")


def main() -> None:
    download_file_picker_aars()
    install_touch_controls()
    patch_project_settings()
    append_android_export_preset()
    (ROOT / "build").mkdir(exist_ok=True)
    print("Android export preparation complete")


if __name__ == "__main__":
    main()
