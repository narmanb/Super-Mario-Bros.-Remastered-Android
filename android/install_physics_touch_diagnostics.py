#!/usr/bin/env python3
"""Add compact physics diagnostics to the generated Android touch scene without modifying touch-control logic or positions."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Deliberately leave OnScreenControls.gd untouched; only add independent scene children.


def main() -> None:
    path = ROOT / "Scenes" / "Prefabs" / "UI" / "OnScreenControls.tscn"
    scene = path.read_text(encoding="utf-8")

    if "PhysicsDiagnosticsText" in scene:
        raise RuntimeError("Physics diagnostics already installed")

    header = '[gd_scene load_steps=21 format=3 uid="uid://fjrcs2mshn2x"]'
    if header not in scene:
        raise RuntimeError("Could not locate OnScreenControls scene header")
    scene = scene.replace(
        header,
        '[gd_scene load_steps=22 format=3 uid="uid://fjrcs2mshn2x"]',
        1,
    )

    first_gap = scene.find("\n\n")
    if first_gap == -1:
        raise RuntimeError("Could not locate OnScreenControls resource section")
    ext = '\n[ext_resource type="Script" path="res://Scripts/Parts/AndroidPhysicsDiagnosticsLabel.gd" id="99_diag"]'
    scene = scene[:first_gap] + ext + scene[first_gap:]

    marker = "\n[connection signal=\"pressed\" from=\"Control/TouchScreenButton\""
    if marker not in scene:
        raise RuntimeError("Could not locate OnScreenControls connection section")

    # Keep the readout in the otherwise-unused upper-right margin. It starts
    # hidden and the label script only reveals both nodes while a live Player.gd
    # instance exists, so menus/settings stay completely unobstructed.
    nodes = r'''

[node name="PhysicsDiagnosticsBackground" type="ColorRect" parent="."]
visible = false
layout_mode = 3
anchor_left = 1.0
anchor_right = 1.0
offset_left = -100.0
offset_top = 6.0
offset_right = -4.0
offset_bottom = 84.0
grow_horizontal = 0
mouse_filter = 2
color = Color(0, 0, 0, 0.30)
z_index = 5000

[node name="PhysicsDiagnosticsText" type="Label" parent="."]
visible = false
layout_mode = 3
anchor_left = 1.0
anchor_right = 1.0
offset_left = -97.0
offset_top = 8.0
offset_right = -5.0
offset_bottom = 82.0
grow_horizontal = 0
mouse_filter = 2
theme_override_colors/font_color = Color(1, 1, 1, 1)
theme_override_colors/font_outline_color = Color(0, 0, 0, 1)
theme_override_constants/outline_size = 1
theme_override_font_sizes/font_size = 4
text = ""
horizontal_alignment = 0
vertical_alignment = 0
script = ExtResource("99_diag")
z_index = 5001
'''

    scene = scene.replace(marker, nodes + marker, 1)
    path.write_text(scene, encoding="utf-8")
    print("Added compact right-side physics diagnostics without changing touch controls")


if __name__ == "__main__":
    main()
