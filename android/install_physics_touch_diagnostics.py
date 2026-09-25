#!/usr/bin/env python3
"""Add physics diagnostics to the generated Android touch scene without modifying touch-control logic or positions."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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

    nodes = r'''

[node name="PhysicsDiagnosticsBackground" type="ColorRect" parent="."]
layout_mode = 3
anchors_preset = 10
anchor_left = 0.5
anchor_right = 0.5
offset_left = -132.0
offset_top = 6.0
offset_right = 132.0
offset_bottom = 92.0
grow_horizontal = 2
mouse_filter = 2
color = Color(0, 0, 0, 0.86)
z_index = 5000

[node name="PhysicsDiagnosticsText" type="Label" parent="."]
layout_mode = 3
anchors_preset = 10
anchor_left = 0.5
anchor_right = 0.5
offset_left = -128.0
offset_top = 8.0
offset_right = 128.0
offset_bottom = 90.0
grow_horizontal = 2
mouse_filter = 2
theme_override_colors/font_color = Color(1, 1, 1, 1)
theme_override_colors/font_outline_color = Color(0, 0, 0, 1)
theme_override_constants/outline_size = 2
theme_override_font_sizes/font_size = 8
text = "PHYSICS DIAGNOSTICS\nTOUCH LAYER OK\nWAITING FOR PLAYER..."
horizontal_alignment = 1
vertical_alignment = 1
script = ExtResource("99_diag")
z_index = 5001
'''

    scene = scene.replace(marker, nodes + marker, 1)
    path.write_text(scene, encoding="utf-8")
    print("Added physics diagnostics as independent top-center children of OnScreenControls")


if __name__ == "__main__":
    main()
