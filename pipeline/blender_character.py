"""Blender 2D Flat Toon Character Generator (Kurzgesagt / Vox style) for YoutubeShortsInc.

Uses Blender 5.2 headlessly via Python (bpy) with ORTHO projection and clean emission shaders
to render vector-style transparent PNG character poses. Completely replaces third-party stock scraping.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

BLENDER_EXE = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
ROOT = Path(__file__).resolve().parent.parent
CHAR_DIR = ROOT / "assets" / "characters"

BLENDER_RENDER_SCRIPT = """
import bpy
import math

def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def setup_camera_and_render(out_path):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1080

    cam_data = bpy.data.cameras.new(name="ToonCam")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 3.3
    cam = bpy.data.objects.new(name="ToonCam", object_data=cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0, -6, 0.35)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.camera = cam
    scene.render.filepath = out_path

def toon_mat(name, rgba):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emi = nodes.new("ShaderNodeEmission")
    emi.inputs['Color'].default_value = rgba
    emi.inputs['Strength'].default_value = 1.0
    mat.node_tree.links.new(emi.outputs['Emission'], out.inputs['Surface'])
    return mat

def build_character(pose="explain", outfit="explorer"):
    # Vibrant, modern vector palette (Kurzgesagt / Vox inspired)
    c_skin = (1.0, 0.85, 0.74, 1.0)
    c_skin_shadow = (0.92, 0.75, 0.65, 1.0)
    c_hair = (0.13, 0.15, 0.25, 1.0)
    c_hair_highlight = (0.24, 0.27, 0.42, 1.0)
    c_hoodie = (0.08, 0.48, 0.94, 1.0) if outfit != "space" else (0.92, 0.94, 0.98, 1.0)
    c_hoodie_shadow = (0.05, 0.38, 0.78, 1.0) if outfit != "space" else (0.80, 0.82, 0.88, 1.0)
    c_hoodie_trim = (1.0, 0.55, 0.10, 1.0) if outfit != "space" else (0.2, 0.7, 1.0, 1.0)
    c_eye_dark = (0.08, 0.09, 0.14, 1.0)
    c_white = (1.0, 1.0, 1.0, 1.0)
    c_blush = (1.0, 0.48, 0.54, 1.0)
    c_mouth = (0.85, 0.18, 0.25, 1.0)
    c_mouth_inside = (0.45, 0.08, 0.12, 1.0)
    c_teeth = (0.98, 0.98, 0.98, 1.0)
    c_phone_case = (0.08, 0.08, 0.12, 1.0)
    c_phone_screen = (0.10, 0.85, 0.95, 1.0)
    c_helmet_rim = (0.75, 0.78, 0.85, 1.0)
    c_visor = (0.15, 0.75, 0.95, 0.8)

    m_skin = toon_mat("Skin", c_skin)
    m_hair = toon_mat("Hair", c_hair)
    m_hoodie = toon_mat("Hoodie", c_hoodie)
    m_hoodie_shadow = toon_mat("HoodieShadow", c_hoodie_shadow)
    m_hoodie_trim = toon_mat("HoodieTrim", c_hoodie_trim)
    m_eye = toon_mat("Eye", c_eye_dark)
    m_white = toon_mat("White", c_white)
    m_blush = toon_mat("Blush", c_blush)
    m_mouth = toon_mat("Mouth", c_mouth)

    # 1. Torso (Curved tapered hoodie body)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.72, depth=1.2, location=(0, 0, -0.4))
    torso = bpy.context.active_object
    torso.scale = (1.0, 0.28, 1.0)
    torso.data.materials.append(m_hoodie)

    # Hoodie base hem
    bpy.ops.mesh.primitive_cylinder_add(radius=0.74, depth=0.15, location=(0, 0, -0.95))
    hem = bpy.context.active_object
    hem.scale = (1.0, 0.28, 1.0)
    hem.data.materials.append(m_hoodie_shadow)

    # Hoodie collar trim / drawstrings
    bpy.ops.mesh.primitive_torus_add(major_radius=0.42, minor_radius=0.08, location=(0, -0.05, 0.18))
    collar = bpy.context.active_object
    collar.scale = (1.0, 0.35, 1.0)
    collar.data.materials.append(m_hoodie_shadow)

    # Hoodie chest badge / channel icon emblem
    bpy.ops.mesh.primitive_cylinder_add(radius=0.14, depth=0.06, location=(0.35, -0.22, -0.25))
    emblem = bpy.context.active_object
    emblem.rotation_euler = (math.radians(90), 0, 0)
    emblem.scale = (1.0, 1.0, 0.1)
    emblem.data.materials.append(m_hoodie_trim)

    # 2. Neck
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.4, location=(0, 0, 0.28))
    neck = bpy.context.active_object
    neck.scale = (1.0, 0.3, 1.0)
    neck.data.materials.append(m_skin)

    # 3. Head (Cute stylized egg/oval head)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.78, location=(0, 0, 0.88))
    head = bpy.context.active_object
    head.scale = (1.0, 0.28, 1.08)
    head.data.materials.append(m_skin)

    # 4. Hair & Helmet
    if outfit == "space":
        # White Astronaut Helmet Outer Dome (behind head)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.96, location=(0, 0.08, 0.95))
        helmet_back = bpy.context.active_object
        helmet_back.scale = (1.08, 0.35, 1.08)
        helmet_back.data.materials.append(toon_mat("SpaceHelmet", (0.95, 0.96, 0.98, 1.0)))

        # Helmet collar ring
        bpy.ops.mesh.primitive_torus_add(major_radius=0.78, minor_radius=0.10, location=(0, -0.06, 0.22))
        ring = bpy.context.active_object
        ring.scale = (1.0, 0.35, 1.0)
        ring.data.materials.append(toon_mat("HelmetRim", (0.2, 0.7, 1.0, 1.0)))

        # Cute Antenna on helmet
        bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.45, location=(0.4, 0.05, 1.95))
        ant = bpy.context.active_object
        ant.rotation_euler = (0, math.radians(20), 0)
        ant.data.materials.append(toon_mat("Antenna", (0.7, 0.75, 0.85, 1.0)))

        # Glowing antenna beacon tip
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=(0.48, 0.05, 2.15))
        tip = bpy.context.active_object
        tip.data.materials.append(toon_mat("Beacon", (1.0, 0.25, 0.25, 1.0)))

        # Cute space explorer hair fringe
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.48, location=(0.1, -0.22, 1.35))
        fringe = bpy.context.active_object
        fringe.scale = (1.1, 0.22, 0.7)
        fringe.data.materials.append(m_hair)
    else:
        # Modern swept swoosh hairstyle
        # Back hair mass
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.84, location=(0, 0.08, 1.02))
        hair_back = bpy.context.active_object
        hair_back.scale = (1.05, 0.32, 1.02)
        hair_back.data.materials.append(m_hair)

        # Front fringe / stylish side bangs
        for side, x, rot_z, sc in (("Left", -0.42, 18, 0.44), ("Right", 0.45, -22, 0.48), ("Top", 0.1, 8, 0.52)):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=sc, location=(x, -0.22, 1.35))
            fringe = bpy.context.active_object
            fringe.rotation_euler = (0, 0, math.radians(rot_z))
            fringe.scale = (1.1, 0.22, 0.7)
            fringe.data.materials.append(m_hair)

        # Sideburn puffs
        for x in (-0.72, 0.72):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(x, -0.05, 0.88))
            puff = bpy.context.active_object
            puff.scale = (0.7, 0.25, 1.0)
            puff.data.materials.append(m_hair)

    # 5. Expressive Vector Eyes (Wide anime / Kurzgesagt vector eyes)
    for x in (-0.28, 0.28):
        # Eye white / sclera
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.17, location=(x, -0.24, 0.95))
        eye_w = bpy.context.active_object
        eye_w.scale = (1.0, 0.15, 1.35)
        eye_w.data.materials.append(m_white)

        # Iris
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.13, location=(x, -0.27, 0.95))
        iris = bpy.context.active_object
        iris.scale = (1.0, 0.12, 1.25)
        iris.data.materials.append(m_eye)

        # Main specular highlight (sparkle)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.045, location=(x - 0.04, -0.29, 1.03))
        hi1 = bpy.context.active_object
        hi1.scale = (1.0, 0.1, 1.0)
        hi1.data.materials.append(m_white)

        # Secondary cute reflection dot
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.025, location=(x + 0.04, -0.29, 0.90))
        hi2 = bpy.context.active_object
        hi2.scale = (1.0, 0.1, 1.0)
        hi2.data.materials.append(m_white)

        # Eyebrow
        eyebrow_y = 1.20 if pose != "shock" else 1.26
        bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.28, location=(x, -0.24, eyebrow_y))
        brow = bpy.context.active_object
        brow.rotation_euler = (0, math.radians(90 + (12 if x < 0 else -12)), 0)
        brow.scale = (1.0, 0.2, 1.0)
        brow.data.materials.append(m_hair)

        # Soft blush pill on cheeks
        bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=0.22, location=(x * 1.35, -0.25, 0.74))
        blush = bpy.context.active_object
        blush.rotation_euler = (0, math.radians(90), 0)
        blush.scale = (1.0, 0.1, 0.55)
        blush.data.materials.append(m_blush)

    # 6. Mouth based on pose
    if pose == "shock":
        # Big shocked open mouth (oval 'O')
        bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.08, location=(0, -0.27, 0.65))
        mouth = bpy.context.active_object
        mouth.rotation_euler = (math.radians(90), 0, 0)
        mouth.scale = (0.75, 1.1, 0.2)
        mouth.data.materials.append(toon_mat("ShockMouth", c_mouth_inside))
        # Mouth rim
        bpy.ops.mesh.primitive_torus_add(major_radius=0.16, minor_radius=0.03, location=(0, -0.27, 0.65))
        mouth_rim = bpy.context.active_object
        mouth_rim.rotation_euler = (math.radians(90), 0, 0)
        mouth_rim.scale = (0.75, 1.1, 0.2)
        mouth_rim.data.materials.append(m_mouth)
    elif pose in ("celebrate", "point"):
        # Wide happy open smile
        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.06, location=(0, -0.27, 0.68))
        mouth = bpy.context.active_object
        mouth.rotation_euler = (math.radians(90), 0, 0)
        mouth.scale = (1.1, 0.7, 0.2)
        mouth.data.materials.append(m_mouth)
        # Upper teeth line
        bpy.ops.mesh.primitive_cylinder_add(radius=0.14, depth=0.07, location=(0, -0.28, 0.73))
        teeth = bpy.context.active_object
        teeth.rotation_euler = (math.radians(90), 0, 0)
        teeth.scale = (1.0, 0.3, 0.2)
        teeth.data.materials.append(m_white)
    elif pose == "think":
        # Puzzled thoughtful smirk / small curved mouth
        bpy.ops.mesh.primitive_torus_add(major_radius=0.12, minor_radius=0.025, location=(0.06, -0.27, 0.68))
        mouth = bpy.context.active_object
        mouth.rotation_euler = (math.radians(90), math.radians(15), 0)
        mouth.scale = (0.9, 0.35, 0.2)
        mouth.data.materials.append(m_mouth)
    else:  # "explain"
        # Friendly welcoming smile arc
        bpy.ops.mesh.primitive_torus_add(major_radius=0.15, minor_radius=0.028, location=(0, -0.27, 0.68))
        mouth = bpy.context.active_object
        mouth.rotation_euler = (math.radians(90), 0, 0)
        mouth.scale = (1.1, 0.45, 0.2)
        mouth.data.materials.append(m_mouth)

    # 7. Arms, Sleeves & Hands with proper connections and gestures
    def add_hand(x, y, z, rot_z=0, scale=0.16):
        # Palm
        bpy.ops.mesh.primitive_uv_sphere_add(radius=scale, location=(x, y, z))
        palm = bpy.context.active_object
        palm.scale = (1.0, 0.3, 1.0)
        palm.data.materials.append(m_skin)
        # Thumb
        thumb_dir = -1 if x < 0 else 1
        bpy.ops.mesh.primitive_uv_sphere_add(radius=scale * 0.48, location=(x + thumb_dir * scale * 0.7, y - 0.04, z + scale * 0.35))
        thumb = bpy.context.active_object
        thumb.scale = (1.0, 0.3, 1.2)
        thumb.data.materials.append(m_skin)

    if pose == "point":
        # Right arm pointing up/across towards center
        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.88, location=(0.88, -0.15, 0.15))
        arm_r = bpy.context.active_object
        arm_r.rotation_euler = (0, math.radians(-40), 0)
        arm_r.scale = (1.0, 0.28, 1.0)
        arm_r.data.materials.append(m_hoodie)

        # Sleeve cuff
        bpy.ops.mesh.primitive_cylinder_add(radius=0.19, depth=0.12, location=(1.16, -0.16, 0.44))
        cuff_r = bpy.context.active_object
        cuff_r.rotation_euler = (0, math.radians(-40), 0)
        cuff_r.scale = (1.0, 0.28, 1.0)
        cuff_r.data.materials.append(m_hoodie_shadow)

        # Pointing hand with extended index finger
        add_hand(1.28, -0.22, 0.58, scale=0.15)
        # Index finger
        bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.28, location=(1.40, -0.23, 0.72))
        finger = bpy.context.active_object
        finger.rotation_euler = (0, math.radians(-40), 0)
        finger.scale = (1.0, 0.3, 1.0)
        finger.data.materials.append(m_skin)

        # Left arm relaxed at side
        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.82, location=(-0.82, -0.05, -0.32))
        arm_l = bpy.context.active_object
        arm_l.rotation_euler = (0, math.radians(12), 0)
        arm_l.scale = (1.0, 0.28, 1.0)
        arm_l.data.materials.append(m_hoodie)
        add_hand(-0.92, -0.08, -0.78, scale=0.15)

    elif pose == "shock":
        # Both hands clutching cheeks in disbelief!
        for side, x, rot in (("Left", -0.75, 48), ("Right", 0.75, -48)):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.85, location=(x, -0.12, 0.32))
            arm = bpy.context.active_object
            arm.rotation_euler = (0, math.radians(rot), 0)
            arm.scale = (1.0, 0.28, 1.0)
            arm.data.materials.append(m_hoodie)
            # Cuff
            bpy.ops.mesh.primitive_cylinder_add(radius=0.19, depth=0.10, location=(x * 0.88, -0.16, 0.62))
            cuff = bpy.context.active_object
            cuff.rotation_euler = (0, math.radians(rot), 0)
            cuff.scale = (1.0, 0.28, 1.0)
            cuff.data.materials.append(m_hoodie_shadow)
            # Hand on cheek
            add_hand(x * 0.78, -0.28, 0.78, scale=0.17)

    elif pose == "think":
        # Right hand on chin, left arm crossed holding elbow
        # Left arm crossed across waist
        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.85, location=(-0.25, -0.18, -0.35))
        arm_l = bpy.context.active_object
        arm_l.rotation_euler = (0, math.radians(80), 0)
        arm_l.scale = (1.0, 0.28, 1.0)
        arm_l.data.materials.append(m_hoodie)
        add_hand(0.20, -0.22, -0.32, scale=0.14)

        # Right arm bent upward with hand resting under chin
        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.80, location=(0.60, -0.16, 0.12))
        arm_r = bpy.context.active_object
        arm_r.rotation_euler = (0, math.radians(-35), 0)
        arm_r.scale = (1.0, 0.28, 1.0)
        arm_r.data.materials.append(m_hoodie)
        # Hand under chin
        add_hand(0.32, -0.28, 0.52, scale=0.15)

    elif pose == "phone":
        # Holding glowing tech smartphone with both hands
        # Right arm
        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.75, location=(0.65, -0.16, -0.05))
        arm_r = bpy.context.active_object
        arm_r.rotation_euler = (0, math.radians(-32), 0)
        arm_r.scale = (1.0, 0.28, 1.0)
        arm_r.data.materials.append(m_hoodie)
        # Left arm
        bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.75, location=(-0.65, -0.16, -0.05))
        arm_l = bpy.context.active_object
        arm_l.rotation_euler = (0, math.radians(32), 0)
        arm_l.scale = (1.0, 0.28, 1.0)
        arm_l.data.materials.append(m_hoodie)

        # Phone body
        bpy.ops.mesh.primitive_cube_add(size=0.45, location=(0, -0.35, 0.18))
        phone = bpy.context.active_object
        phone.scale = (0.75, 0.1, 1.25)
        phone.data.materials.append(toon_mat("PhoneCase", c_phone_case))

        # Glowing screen
        bpy.ops.mesh.primitive_cube_add(size=0.42, location=(0, -0.37, 0.18))
        screen = bpy.context.active_object
        screen.scale = (0.70, 0.05, 1.18)
        screen.data.materials.append(toon_mat("PhoneScreen", c_phone_screen))

        # Hands holding sides of phone
        add_hand(-0.35, -0.34, 0.18, scale=0.14)
        add_hand(0.35, -0.34, 0.18, scale=0.14)

    elif pose == "celebrate":
        # Both arms raised high in triumph!
        for side, x, rot in (("Left", -0.88, -35), ("Right", 0.88, 35)):
            bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.92, location=(x, -0.10, 0.45))
            arm = bpy.context.active_object
            arm.rotation_euler = (0, math.radians(rot), 0)
            arm.scale = (1.0, 0.28, 1.0)
            arm.data.materials.append(m_hoodie)
            add_hand(x * 1.35, -0.15, 0.95, scale=0.16)

    else:  # "explain" (default friendly presenter)
        for side, x, rot in (("Left", -0.82, 22), ("Right", 0.82, -22)):
            # Arm
            bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.82, location=(x, -0.10, -0.10))
            arm = bpy.context.active_object
            arm.rotation_euler = (0, math.radians(rot), 0)
            arm.scale = (1.0, 0.28, 1.0)
            arm.data.materials.append(m_hoodie)
            # Cuff
            bpy.ops.mesh.primitive_cylinder_add(radius=0.19, depth=0.10, location=(x * 1.18, -0.12, 0.12))
            cuff = bpy.context.active_object
            cuff.rotation_euler = (0, math.radians(rot), 0)
            cuff.scale = (1.0, 0.28, 1.0)
            cuff.data.materials.append(m_hoodie_shadow)
            # Welcoming open hand
            add_hand(x * 1.35, -0.18, 0.28, scale=0.16)

def render(out_file, pose="explain", outfit="explorer"):
    clear_scene()
    setup_camera_and_render(out_file)
    build_character(pose=pose, outfit=outfit)
    bpy.ops.render.render(write_still=True)

import sys
argv = sys.argv
if "--" in argv:
    args = argv[argv.index("--") + 1:]
    out = args[0]
    p = args[1] if len(args) > 1 else "explain"
    o = args[2] if len(args) > 2 else "explorer"
    render(out, pose=p, outfit=o)
"""


def render_toon_pose(pose: str = "explain", outfit: str = "explorer", filename: str | None = None) -> Path:
    """Render a single 2D vector toon pose from Blender into assets/characters/."""
    CHAR_DIR.mkdir(parents=True, exist_ok=True)
    filename = filename or f"toon_nik_{pose}.png"
    out_path = CHAR_DIR / filename
    script_path = CHAR_DIR / "_toon_render_worker.py"
    script_path.write_text(BLENDER_RENDER_SCRIPT, encoding="utf-8")

    cmd = [
        str(BLENDER_EXE),
        "-b",
        "--python", str(script_path),
        "--",
        str(out_path).replace("\\", "/"),
        pose,
        outfit,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"Blender render failed: {proc.stderr[:400]}")
    if script_path.exists():
        script_path.unlink()
    return out_path


def generate_all_toon_poses() -> list[Path]:
    """Generates the full mascot pose library for the channel."""
    CHAR_DIR.mkdir(parents=True, exist_ok=True)
    poses = [
        ("explain", "explorer", "toon_nik_explain.png"),
        ("point", "explorer", "toon_nik_point.png"),
        ("shock", "explorer", "toon_nik_shock.png"),
        ("think", "explorer", "toon_nik_think.png"),
        ("phone", "explorer", "toon_nik_phone.png"),
        ("celebrate", "explorer", "toon_nik_celebrate.png"),
        ("explain", "space", "toon_nik_astronaut.png"),
    ]
    results = []
    print(f"Generating Blender 2D Toon Mascot Character Suite in: {CHAR_DIR}")
    for pose, outfit, fname in poses:
        path = render_toon_pose(pose, outfit, fname)
        kb = path.stat().st_size // 1024
        print(f" [OK] {fname} ({kb} KB)")
        results.append(path)
    return results


if __name__ == "__main__":
    generate_all_toon_poses()
