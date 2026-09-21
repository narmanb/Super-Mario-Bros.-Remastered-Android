#!/usr/bin/env python3
"""Follow-up Android runtime fixes applied after fix_mobile_runtime.py.

This keeps the 1.1 Android wrapper aligned with the older proven Android port:
wrapper scene changes are started without awaiting the wrapper coroutine itself,
and the wrapper does not await a scene's already-emitted ready signal after
add_child(). It also nudges the two touch-control clusters outward slightly.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_global_transition() -> None:
    path = ROOT / "Scripts" / "Classes" / "Singletons" / "Global.gd"
    text = path.read_text(encoding="utf-8")
    old = '\tif android_wrapper != null:\n\t\tawait android_wrapper.change_scene_to(scene_path)\n'
    new = '\tif android_wrapper != null:\n\t\t# Match the older working Android wrapper: start the viewport scene\n\t\t# transition without awaiting the wrapper coroutine itself.\n\t\tandroid_wrapper.change_scene_to(scene_path)\n'
    if old not in text:
        raise RuntimeError("Could not find generated Android wrapper transition in Global.gd")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_wrapper() -> None:
    path = ROOT / "Scripts" / "Wrapper.gd"
    text = path.read_text(encoding="utf-8")
    old = '\tgame_viewport.add_child(new_scene)\n\tawait new_scene.ready\n'
    new = ('\tgame_viewport.add_child(new_scene)\n'
           '\t# add_child() enters the scene tree immediately; do not await ready here.\n'
           '\t# Awaiting a signal that may already have fired can strand this coroutine.\n')
    if old not in text:
        raise RuntimeError("Could not find generated new-scene ready wait in Wrapper.gd")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_touch_positions() -> None:
    path = ROOT / "Scenes" / "Prefabs" / "UI" / "OnScreenControls.tscn"
    text = path.read_text(encoding="utf-8")

    # Shift the whole D-pad cluster 10 logical pixels toward the left edge.
    left_old = ('[node name="Control" type="Control" parent="."]\n'
                'layout_mode = 3\n'
                'anchors_preset = 2\n'
                'anchor_top = 1.0\n'
                'anchor_bottom = 1.0\n'
                'offset_top = -141.0\n'
                'offset_right = 141.0\n')
    left_new = ('[node name="Control" type="Control" parent="."]\n'
                'layout_mode = 3\n'
                'anchors_preset = 2\n'
                'anchor_top = 1.0\n'
                'anchor_bottom = 1.0\n'
                'offset_left = -10.0\n'
                'offset_top = -141.0\n'
                'offset_right = 131.0\n')
    if left_old not in text:
        raise RuntimeError("Could not locate left touch-control container")
    text = text.replace(left_old, left_new, 1)

    # Shift the whole A/B/Run/Start cluster 10 logical pixels toward the right edge.
    right_old = ('[node name="Control2" type="Control" parent="."]\n'
                 'layout_mode = 3\n'
                 'anchors_preset = 3\n'
                 'anchor_left = 1.0\n'
                 'anchor_top = 1.0\n'
                 'anchor_right = 1.0\n'
                 'anchor_bottom = 1.0\n'
                 'offset_left = -115.0\n'
                 'offset_top = -141.0\n')
    right_new = ('[node name="Control2" type="Control" parent="."]\n'
                 'layout_mode = 3\n'
                 'anchors_preset = 3\n'
                 'anchor_left = 1.0\n'
                 'anchor_top = 1.0\n'
                 'anchor_right = 1.0\n'
                 'anchor_bottom = 1.0\n'
                 'offset_left = -105.0\n'
                 'offset_top = -141.0\n'
                 'offset_right = 10.0\n')
    if right_old not in text:
        raise RuntimeError("Could not locate right touch-control container")
    text = text.replace(right_old, right_new, 1)

    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_global_transition()
    patch_wrapper()
    patch_touch_positions()
    print("Applied Android wrapper transition and touch-position follow-up fixes")


if __name__ == "__main__":
    main()
