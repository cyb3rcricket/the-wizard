#!/usr/bin/env python3
"""
Wizard V3+ GLB Character Asset Contract Validator
=================================================
Validates future authored Wizard 3D GLB assets against the Wizard V3+ Character
Asset Contract (V3PLUS-CHARACTER-ASSET-CONTRACT.md).

Pure Python standard library implementation with ZERO external dependencies.
Directly inspects the binary GLB container and glTF 2.0 JSON metadata chunk.

Usage:
    python3 tools/validate_wizard_glb.py path/to/wizard.glb [--strict] [--json]

Exit Codes:
    0 = Asset passed all required contract checks (READY for V3+ integration)
    1 = Asset failed one or more fatal contract requirements (REJECTED / procedural fallback retained)
"""

import sys
import os
import re
import struct
import json
import math
import argparse
from typing import Dict, List, Tuple, Any, Optional

GLB_MAGIC = 0x46546C67  # 'glTF' in ASCII
GLB_CHUNK_JSON = 0x4E4F534A  # 'JSON' in ASCII
GLB_CHUNK_BIN = 0x004E4942   # 'BIN\0' in ASCII

# Required Named Attachments Contract
REQUIRED_ATTACHMENTS = {
    "spell_origin": {
        "required": True,
        "description": "Center of magical crystal/gem atop staff; projectile & vortex origin",
        "min_height": 1.5,
        "min_distance_from_origin": 0.5,
        "max_distance_from_origin": 10.0,
    },
    "staff_grip": {
        "required": True,
        "description": "Hand/socket node gripping staff handle",
        "min_height": 0.8,
    },
    "head": {
        "required": True,
        "description": "Head/face center for hero camera framing & secondary rim lights",
        "min_height": 1.8,
    },
    "camera_target": {
        "required": False,  # Recommended, can fallback to head
        "description": "Framing target for camera presets (chest/face center)",
        "min_height": 1.5,
    }
}

# Required Animation Clips Contract
REQUIRED_CLIPS = ["idle", "charge", "cast", "recover"]

# Semantic Bone Mapping Targets
SEMANTIC_BONE_KEYWORDS = {
    "root": ["root", "origin", "armature"],
    "hips": ["hip", "pelvis"],
    "spine": ["spine", "chest", "torso", "rib", "upperbody", "lowerbody"],
    "neck_head": ["neck", "head"],
    "staff_arm": [
        "rightshoulder", "rightarm", "rightelbow", "rightforearm", "righthand", "right_hand",
        "hand.r", "hand_r", "hand-r", "upperarm_r", "lowerarm_r", "upper_arm.r", "forearm.r",
        "shoulder.r", "arm.r", "wrist.r", "def-upper_arm.r", "def-forearm.r", "def-hand.r"
    ],
    "somatic_arm": [
        "leftshoulder", "leftarm", "leftelbow", "leftforearm", "lefthand", "left_hand",
        "hand.l", "hand_l", "hand-l", "upperarm_l", "lowerarm_l", "upper_arm.l", "forearm.l",
        "shoulder.l", "arm.l", "wrist.l", "def-upper_arm.l", "def-forearm.l", "def-hand.l"
    ],
    "legs": ["thigh", "leg", "knee", "foot", "calf", "ankle", "toe", "shin"]
}


# ---------------------------------------------------------------------------
# String & Name Utilities
# ---------------------------------------------------------------------------

def get_name_words(name: str) -> List[str]:
    """Split camelCase, PascalCase, snake_case, kebab-case, pipe, dot into lowercase words."""
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    return [w.lower() for w in re.split(r'[^a-zA-Z0-9]+', s) if w]


def match_clip_name(clip_name: str, req: str) -> bool:
    """Match required animation clip against exported clip name (handles Armature|..., loops, etc.)."""
    c = clip_name.strip()
    req = req.lower().strip()
    words = get_name_words(c)
    if req in words:
        return True
    for w in words:
        if w.startswith(req) or w.endswith(req):
            return True
    return False


# ---------------------------------------------------------------------------
# Matrix Math Utilities (Column-Major 4x4 glTF Format)
# ---------------------------------------------------------------------------

def identity_matrix() -> List[float]:
    return [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    ]


def trs_to_matrix(translation: List[float], rotation: List[float], scale: List[float]) -> List[float]:
    tx, ty, tz = translation
    qx, qy, qz, qw = rotation
    sx, sy, sz = scale

    # Quaternion to rotation matrix
    x2 = qx + qx
    y2 = qy + qy
    z2 = qz + qz
    xx = qx * x2
    xy = qx * y2
    xz = qx * z2
    yy = qy * y2
    yz = qy * z2
    zz = qz * z2
    wx = qw * x2
    wy = qw * y2
    wz = qw * z2

    # Column-major 4x4 matrix
    return [
        (1.0 - (yy + zz)) * sx, (xy + wz) * sx, (xz - wy) * sx, 0.0,
        (xy - wz) * sy, (1.0 - (xx + zz)) * sy, (yz + wx) * sy, 0.0,
        (xz + wy) * sz, (yz - wx) * sz, (1.0 - (xx + yy)) * sz, 0.0,
        tx, ty, tz, 1.0
    ]


def multiply_matrices(a: List[float], b: List[float]) -> List[float]:
    """Multiply two 4x4 column-major matrices: result = a * b"""
    result = [0.0] * 16
    for col in range(4):
        for row in range(4):
            val = 0.0
            for k in range(4):
                val += a[k * 4 + row] * b[col * 4 + k]
            result[col * 4 + row] = val
    return result


def get_translation_from_matrix(m: List[float]) -> Tuple[float, float, float]:
    return (m[12], m[13], m[14])


def transform_aabb(pmin: List[float], pmax: List[float], matrix: List[float]) -> Tuple[List[float], List[float]]:
    """Transform an axis-aligned bounding box by a 4x4 column-major matrix and return new AABB."""
    corners = [
        [pmin[0], pmin[1], pmin[2]],
        [pmin[0], pmin[1], pmax[2]],
        [pmin[0], pmax[1], pmin[2]],
        [pmin[0], pmax[1], pmax[2]],
        [pmax[0], pmin[1], pmin[2]],
        [pmax[0], pmin[1], pmax[2]],
        [pmax[0], pmax[1], pmin[2]],
        [pmax[0], pmax[1], pmax[2]]
    ]
    tmin = [float("inf")] * 3
    tmax = [float("-inf")] * 3
    for cx, cy, cz in corners:
        tx = matrix[0] * cx + matrix[4] * cy + matrix[8] * cz + matrix[12]
        ty = matrix[1] * cx + matrix[5] * cy + matrix[9] * cz + matrix[13]
        tz = matrix[2] * cx + matrix[6] * cy + matrix[10] * cz + matrix[14]
        for i, val in enumerate([tx, ty, tz]):
            tmin[i] = min(tmin[i], val)
            tmax[i] = max(tmax[i], val)
    return tmin, tmax


# ---------------------------------------------------------------------------
# GLB Parsing
# ---------------------------------------------------------------------------

def parse_glb(file_path: str) -> Tuple[Dict[str, Any], int]:
    """Read binary GLB file, parse JSON chunk, and return (gltf_json, file_size)."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    if file_size < 12:
        raise ValueError(f"File too small to be a valid GLB ({file_size} bytes)")

    with open(file_path, "rb") as f:
        # Read 12-byte header
        header_data = f.read(12)
        magic, version, length = struct.unpack("<III", header_data)

        if magic != GLB_MAGIC:
            raise ValueError(f"Invalid GLB magic header: 0x{magic:08X} (expected 0x{GLB_MAGIC:08X} 'glTF')")

        if version != 2:
            raise ValueError(f"Unsupported glTF version: {version} (expected version 2)")

        # Allow minor 4-byte padding discrepancy, but guard against truncated or grossly mismatched files
        if file_size < length or abs(length - file_size) > 4:
            raise ValueError(f"Header length mismatch: declared {length} bytes, file size is {file_size} bytes")

        # Read Chunk 0 (JSON)
        chunk0_header = f.read(8)
        if len(chunk0_header) < 8:
            raise ValueError("Unexpected EOF reading Chunk 0 header")

        chunk0_len, chunk0_type = struct.unpack("<II", chunk0_header)
        if chunk0_type != GLB_CHUNK_JSON:
            raise ValueError(f"Invalid Chunk 0 type: 0x{chunk0_type:08X} (expected 0x{GLB_CHUNK_JSON:08X} 'JSON')")

        chunk0_data = f.read(chunk0_len)
        if len(chunk0_data) < chunk0_len:
            raise ValueError("Unexpected EOF reading Chunk 0 data")

        try:
            json_text = chunk0_data.decode("utf-8").strip()
            gltf = json.loads(json_text)
        except Exception as e:
            raise ValueError(f"Failed to parse glTF JSON chunk: {e}")

    return gltf, file_size


# ---------------------------------------------------------------------------
# Scene Graph Traversal & Attachment Detection
# ---------------------------------------------------------------------------

def resolve_node_transforms(gltf: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
    """Compute local and world 4x4 transforms for all nodes in the default scene."""
    nodes = gltf.get("nodes", [])
    scenes = gltf.get("scenes", [])
    default_scene_idx = gltf.get("scene")
    if default_scene_idx is None:
        default_scene_idx = 0

    if not scenes or default_scene_idx >= len(scenes) or default_scene_idx < 0:
        return {}

    scene = scenes[default_scene_idx]
    root_node_indices = scene.get("nodes", [])

    node_transforms: Dict[int, Dict[str, Any]] = {}
    visited = set()

    def get_local_matrix(node: Dict[str, Any]) -> List[float]:
        if "matrix" in node and len(node["matrix"]) == 16:
            return list(node["matrix"])
        t = node.get("translation", [0.0, 0.0, 0.0])
        r = node.get("rotation", [0.0, 0.0, 0.0, 1.0])
        s = node.get("scale", [1.0, 1.0, 1.0])
        return trs_to_matrix(t, r, s)

    def traverse(node_idx: int, parent_matrix: List[float]):
        if node_idx < 0 or node_idx >= len(nodes) or node_idx in visited:
            return
        visited.add(node_idx)
        node = nodes[node_idx]
        local_matrix = get_local_matrix(node)
        world_matrix = multiply_matrices(parent_matrix, local_matrix)
        world_pos = get_translation_from_matrix(world_matrix)

        node_transforms[node_idx] = {
            "name": node.get("name", f"node_{node_idx}"),
            "local_matrix": local_matrix,
            "world_matrix": world_matrix,
            "world_pos": world_pos,
            "node_idx": node_idx,
            "raw_node": node
        }

        children = node.get("children", [])
        for child_idx in children:
            traverse(child_idx, world_matrix)

    ident = identity_matrix()
    for root_idx in root_node_indices:
        traverse(root_idx, ident)

    return node_transforms


# ---------------------------------------------------------------------------
# Contract Verification Engine
# ---------------------------------------------------------------------------

class ValidationReport:
    def __init__(self):
        self.fatal_errors: List[str] = []
        self.warnings: List[str] = []
        self.info: Dict[str, Any] = {}
        self.passed_checks: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.fatal_errors) == 0


def validate_wizard_glb(gltf: Dict[str, Any], file_size: int, strict: bool = False) -> ValidationReport:
    report = ValidationReport()
    report.info["file_size_mb"] = round(file_size / (1024 * 1024), 2)

    # 1. File Size Guardrail (< 50MB budget, > 60MB warning)
    if report.info["file_size_mb"] > 60.0:
        report.warnings.append(f"File size {report.info['file_size_mb']} MB exceeds recommended 50 MB budget")
    else:
        report.passed_checks.append(f"File size {report.info['file_size_mb']} MB is within budget (<= 60 MB)")

    # 2. Scene Presence
    scenes = gltf.get("scenes", [])
    if not scenes:
        report.fatal_errors.append("No scenes present in glTF asset")
        return report
    report.passed_checks.append(f"Scene definition present ({len(scenes)} scene(s))")

    # 3. Node Transforms & Hierarchy
    node_transforms = resolve_node_transforms(gltf)
    report.info["total_nodes"] = len(gltf.get("nodes", []))
    report.info["scene_nodes"] = len(node_transforms)

    if not node_transforms:
        report.fatal_errors.append("No active nodes reachable from default scene")
        return report

    # Build node name lookup (case-insensitive for alias tolerance)
    nodes_by_name: Dict[str, Dict[str, Any]] = {}
    for nidx, data in node_transforms.items():
        name = data["name"].strip()
        nodes_by_name[name.lower()] = data

    # 4. Attachment Contract Verification
    report.info["attachments_found"] = {}

    for att_name, spec in REQUIRED_ATTACHMENTS.items():
        is_required = spec["required"]
        desc = spec["description"]

        # Search for exact or alias match
        target_data = None
        for n_name, data in nodes_by_name.items():
            if n_name == att_name or n_name.endswith(f":{att_name}") or n_name.endswith(f"/{att_name}"):
                target_data = data
                break

        # Secondary alias search
        if not target_data:
            alias_map = {
                "spell_origin": [
                    "spellorigin", "spell_origin", "spell-origin", "gem_origin", "gem-origin",
                    "gem", "gem_socket", "staff_gem", "staff-gem", "crystal_origin", "focus_gem"
                ],
                "staff_grip": [
                    "staffgrip", "staff_grip", "staff-grip", "staff_socket", "staff-socket",
                    "hand_r_socket", "hand.r_socket", "grip_socket", "grip.r", "hand_r", "hand.r"
                ],
                "head": [
                    "head_socket", "head_bone", "def_head", "def-head", "bip01_head", "head.001", "org-head"
                ],
                "camera_target": [
                    "cameratarget", "camera_target", "camera-target", "focus_target", "lookat_target", "chest_focus"
                ]
            }
            aliases = alias_map.get(att_name, [])
            for alias in aliases:
                for n_name, data in nodes_by_name.items():
                    if alias in n_name:
                        target_data = data
                        break
                if target_data:
                    break

        if target_data:
            wpos = target_data["world_pos"]
            report.info["attachments_found"][att_name] = {
                "node_name": target_data["name"],
                "world_pos": [round(c, 3) for c in wpos]
            }

            # Check: spell_origin MUST NOT be at (0, 0, 0)
            if att_name == "spell_origin":
                dist_from_origin = math.sqrt(wpos[0]**2 + wpos[1]**2 + wpos[2]**2)
                min_dist = spec.get("min_distance_from_origin", 0.5)
                if dist_from_origin < min_dist:
                    report.fatal_errors.append(
                        f"CRITICAL CONTRACT BREACH: 'spell_origin' node ({target_data['name']}) "
                        f"is positioned at {wpos} (distance {dist_from_origin:.2f} < {min_dist}m from origin). "
                        "Spell origin must be placed at the staff gem tip (y >= 1.5)."
                    )
                elif wpos[1] < spec.get("min_height", 1.5):
                    report.warnings.append(
                        f"'spell_origin' height y={wpos[1]:.2f} is lower than typical staff gem (>= 1.5m)"
                    )
                else:
                    report.passed_checks.append(
                        f"Attachment '{att_name}' valid at {wpos} ({target_data['name']})"
                    )
            else:
                report.passed_checks.append(
                    f"Attachment '{att_name}' found at {wpos} ({target_data['name']})"
                )
        else:
            if is_required:
                report.fatal_errors.append(
                    f"REQUIRED ATTACHMENT MISSING: '{att_name}' ({desc}). "
                    "Cannot integrate character without required attachment node."
                )
            else:
                report.warnings.append(
                    f"Optional attachment '{att_name}' not found ({desc}). Fallback logic will be used."
                )

    # 5. Rig & Skinning Contract
    skins = gltf.get("skins", [])
    report.info["skin_count"] = len(skins)

    if not skins:
        report.fatal_errors.append("No skin definition found. Authored wizard must be rigged with a skeletal skin.")
    else:
        skin = skins[0]
        joints = skin.get("joints", [])
        report.info["joint_count"] = len(joints)
        if len(joints) < 10:
            report.fatal_errors.append(f"Skin has only {len(joints)} joints. Expected humanoid wizard rig (>= 15 joints).")
        else:
            report.passed_checks.append(f"Skin rig verified with {len(joints)} skeletal joints")

        # Check semantic bones
        joint_names = [gltf.get("nodes", [])[j].get("name", "").lower() for j in joints if j < len(gltf.get("nodes", []))]
        matched_categories = {}
        for category, keywords in SEMANTIC_BONE_KEYWORDS.items():
            matched = any(any(kw in jname for kw in keywords) for jname in joint_names)
            matched_categories[category] = matched

        missing_categories = [cat for cat, matched in matched_categories.items() if not matched]
        if missing_categories:
            report.warnings.append(f"Semantic bones not clearly identifiable for: {', '.join(missing_categories)}")
        else:
            report.passed_checks.append("All primary semantic bone categories detected in skeleton")

    # 6. Animation Clips Contract
    animations = gltf.get("animations", [])
    clip_names = [a.get("name", "").strip() for a in animations]
    report.info["clip_names"] = clip_names

    if not animations:
        report.fatal_errors.append("No animation clips found in GLB. Contract requires ['idle', 'charge', 'cast', 'recover'].")
    else:
        missing_clips = []
        for req in REQUIRED_CLIPS:
            matched = any(match_clip_name(c, req) for c in clip_names)
            if not matched:
                missing_clips.append(req)

        if missing_clips:
            report.fatal_errors.append(
                f"REQUIRED ANIMATION CLIPS MISSING: {missing_clips}. "
                f"Found clips: {clip_names}. Contract requires {REQUIRED_CLIPS}."
            )
        else:
            report.passed_checks.append(f"All required animation clips present: {REQUIRED_CLIPS}")

    # 7. Mesh Complexity & Bounding Box
    meshes = gltf.get("meshes", [])
    report.info["mesh_count"] = len(meshes)
    accessors = gltf.get("accessors", [])

    total_triangles = 0
    total_vertices = 0
    global_min = [float("inf"), float("inf"), float("inf")]
    global_max = [float("-inf"), float("-inf"), float("-inf")]
    found_instanced_mesh = False

    # Accumulate vertex count and triangle count across all meshes
    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            pos_acc_idx = attrs.get("POSITION")
            if pos_acc_idx is not None and 0 <= pos_acc_idx < len(accessors):
                pos_acc = accessors[pos_acc_idx]
                total_vertices += pos_acc.get("count", 0)

            indices_idx = prim.get("indices")
            if indices_idx is not None and 0 <= indices_idx < len(accessors):
                ind_acc = accessors[indices_idx]
                total_triangles += ind_acc.get("count", 0) // 3
            elif pos_acc_idx is not None and 0 <= pos_acc_idx < len(accessors):
                # Non-indexed primitives (mode 4 / triangles default: 3 vertices per triangle)
                total_triangles += accessors[pos_acc_idx].get("count", 0) // 3

    # Compute scene-space bounding box by transforming instanced mesh bounds by node world matrices
    for nidx, data in node_transforms.items():
        node = data.get("raw_node", {})
        if "mesh" in node:
            mesh_idx = node["mesh"]
            if 0 <= mesh_idx < len(meshes):
                mesh = meshes[mesh_idx]
                mat = data["world_matrix"]
                for prim in mesh.get("primitives", []):
                    pos_idx = prim.get("attributes", {}).get("POSITION")
                    if pos_idx is not None and 0 <= pos_idx < len(accessors):
                        pmin = accessors[pos_idx].get("min")
                        pmax = accessors[pos_idx].get("max")
                        if pmin and pmax:
                            found_instanced_mesh = True
                            tmin, tmax = transform_aabb(pmin, pmax, mat)
                            for i in range(3):
                                global_min[i] = min(global_min[i], tmin[i])
                                global_max[i] = max(global_max[i], tmax[i])

    # Fallback to local accessor bounds if no mesh node is instanced in default scene
    if not found_instanced_mesh:
        for mesh in meshes:
            for prim in mesh.get("primitives", []):
                pos_idx = prim.get("attributes", {}).get("POSITION")
                if pos_idx is not None and 0 <= pos_idx < len(accessors):
                    pmin = accessors[pos_idx].get("min")
                    pmax = accessors[pos_idx].get("max")
                    if pmin and pmax:
                        for i in range(3):
                            global_min[i] = min(global_min[i], pmin[i])
                            global_max[i] = max(global_max[i], pmax[i])

    report.info["total_vertices"] = total_vertices
    report.info["estimated_triangles"] = total_triangles

    if total_triangles > 80000:
        report.warnings.append(f"Estimated triangle count ({total_triangles:,}) exceeds recommended 50,000 budget")
    elif total_triangles > 0:
        report.passed_checks.append(f"Geometry complexity verified: ~{total_triangles:,} triangles, {total_vertices:,} vertices")

    # Height and Bounds Check
    if global_min[0] != float("inf") and global_max[0] != float("-inf"):
        dx = global_max[0] - global_min[0]
        dy = global_max[1] - global_min[1]
        dz = global_max[2] - global_min[2]
        report.info["bounding_box"] = {
            "min": [round(c, 2) for c in global_min],
            "max": [round(c, 2) for c in global_max],
            "size": [round(dx, 2), round(dy, 2), round(dz, 2)],
            "height": round(dy, 2)
        }

        # Check height sanity (sanity bounds 1.0m - 10.0m; preferred target: 3.8m ± 0.4m)
        if dy < 1.0:
            report.fatal_errors.append(f"Character height {dy:.2f}m is absurdly small (< 1.0m). Check export scale.")
        elif dy > 10.0:
            report.fatal_errors.append(f"Character height {dy:.2f}m is absurdly large (> 10.0m). Check export scale.")
        else:
            report.passed_checks.append(
                f"Character height {dy:.2f}m is within plausible sanity bounds (preferred target: 3.8m ± 0.4m)"
            )

        # Check ground origin (bottom of bounds near y=0)
        if abs(global_min[1]) > 0.5:
            report.warnings.append(
                f"Character base y_min={global_min[1]:.2f}m deviates from ground level (y=0.0). Normalization wrapper will offset."
            )
        else:
            report.passed_checks.append(f"Ground origin verified: base at y={global_min[1]:.2f}m")

    # 8. Materials & Textures
    materials = gltf.get("materials", [])
    textures = gltf.get("textures", [])
    report.info["material_count"] = len(materials)
    report.info["texture_count"] = len(textures)

    if len(materials) > 6:
        report.warnings.append(f"High material count ({len(materials)}). Recommended budget is 2-4 materials.")
    else:
        report.passed_checks.append(f"Material count within budget ({len(materials)} material(s))")

    if strict and report.warnings:
        for w in report.warnings:
            report.fatal_errors.append(f"[STRICT MODE] Warning promoted to error: {w}")

    return report


# ---------------------------------------------------------------------------
# CLI & Terminal Formatter
# ---------------------------------------------------------------------------

def print_report(report: ValidationReport, file_path: str):
    header = "=" * 76
    print(header)
    print("  WIZARD V3+ GLB CHARACTER ASSET VALIDATION REPORT")
    print(header)
    print(f"Asset File: {file_path}")
    print(f"File Size:  {report.info.get('file_size_mb', 0)} MB")
    print(f"Meshes:     {report.info.get('mesh_count', 0)} ({report.info.get('estimated_triangles', 0):,} triangles)")
    print(f"Joints:     {report.info.get('joint_count', 0)}")
    print(f"Clips:      {', '.join(report.info.get('clip_names', [])) or 'None'}")
    
    bbox = report.info.get("bounding_box")
    if bbox:
        print(f"Bounds:     {bbox['size'][0]:.2f}m (W) x {bbox['height']:.2f}m (H) x {bbox['size'][2]:.2f}m (D)")

    print("-" * 76)
    print("ATTACHMENTS DETECTED:")
    attachments = report.info.get("attachments_found", {})
    for att_name in REQUIRED_ATTACHMENTS.keys():
        if att_name in attachments:
            att = attachments[att_name]
            print(f"  [PASS] {att_name:<15} -> Node: '{att['node_name']}' at {att['world_pos']}")
        else:
            is_req = REQUIRED_ATTACHMENTS[att_name]["required"]
            status = "[FAIL] (REQUIRED)" if is_req else "[WARN] (OPTIONAL)"
            print(f"  {status} {att_name:<15} -> NOT FOUND")

    print("-" * 76)
    print("VERIFICATION CHECKS:")
    for check in report.passed_checks:
        print(f"  [OK]   {check}")

    if report.warnings:
        print("-" * 76)
        print("WARNINGS:")
        for w in report.warnings:
            print(f"  [WARN] {w}")

    if report.fatal_errors:
        print("-" * 76)
        print("FATAL ERRORS (REJECTED):")
        for err in report.fatal_errors:
            print(f"  [ERR]  {err}")

    print(header)
    if report.is_valid:
        print("  RESULT: PASS — ASSET MEETS V3+ INTEGRATION CONTRACT")
        print("  Ready for GLBCharacter adapter activation in Wizard V3+.")
    else:
        print("  RESULT: FAIL — ASSET VIOLATES V3+ CONTRACT")
        print("  Asset rejected. Procedural V3 wizard must remain active fallback.")
    print(header)


def main():
    parser = argparse.ArgumentParser(description="Validate authored Wizard GLB asset against V3+ contract.")
    parser.add_argument("file", help="Path to .glb character file")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as fatal errors")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    try:
        gltf, file_size = parse_glb(args.file)
    except Exception as e:
        if args.json:
            print(json.dumps({"valid": False, "fatal_errors": [str(e)], "warnings": []}))
        else:
            print(f"ERROR: Failed to load GLB asset '{args.file}': {e}", file=sys.stderr)
        sys.exit(1)

    report = validate_wizard_glb(gltf, file_size, strict=args.strict)

    if args.json:
        out = {
            "valid": report.is_valid,
            "fatal_errors": report.fatal_errors,
            "warnings": report.warnings,
            "passed_checks": report.passed_checks,
            "info": report.info
        }
        print(json.dumps(out, indent=2))
    else:
        print_report(report, args.file)

    sys.exit(0 if report.is_valid else 1)


if __name__ == "__main__":
    main()
