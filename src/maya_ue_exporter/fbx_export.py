"""Explicit FBX export profiles for rigs and baked skeleton animation."""

from __future__ import absolute_import

import os
from contextlib import contextmanager

try:
    import maya.cmds as cmds
    import maya.mel as mel
except ImportError:  # Keeps this module importable outside Maya.
    cmds = None
    mel = None


_PRESERVED_SETTINGS = (
    ("FBXExportAnimationOnly", "FBXExportAnimationOnly"),
    ("FBXExportBakeComplexAnimation", "FBXExportBakeComplexAnimation"),
    ("FBXExportBakeComplexStart", "FBXExportBakeComplexStart"),
    ("FBXExportBakeComplexEnd", "FBXExportBakeComplexEnd"),
    ("FBXExportBakeComplexStep", "FBXExportBakeComplexStep"),
    ("FBXExportBakeResampleAnimation", "FBXExportBakeResampleAnimation"),
    ("FBXExportSkins", "FBXExportSkins"),
    ("FBXExportShapes", "FBXExportShapes"),
    ("FBXExportConstraints", "FBXExportConstraints"),
    ("FBXExportCameras", "FBXExportCameras"),
    ("FBXExportLights", "FBXExportLights"),
    ("FBXExportInputConnections", "FBXExportInputConnections"),
    ("FBXExportIncludeChildren", "FBXExportIncludeChildren"),
    ("FBXExportEmbeddedTextures", "FBXExportEmbeddedTextures"),
    ("FBXExportSmoothingGroups", "FBXExportSmoothingGroups"),
)

_ANIMATION_PROPERTY = "Export|IncludeGrp|Animation"


def _require_maya():
    if cmds is None or mel is None:
        raise RuntimeError("FBX export must run inside Maya.")


def _mel_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _set_option(command, value):
    mel.eval("{} -v {};".format(command, _mel_value(value)))


def _set_animation_enabled(value):
    mel.eval(
        "FBXProperty {} -v {};".format(_ANIMATION_PROPERTY, _mel_value(value))
    )


@contextmanager
def _preserve_export_state():
    original_selection = cmds.ls(selection=True, long=True) or []
    saved_options = []
    saved_animation_enabled = mel.eval(
        "FBXProperty {} -q;".format(_ANIMATION_PROPERTY)
    )
    for query_command, set_command in _PRESERVED_SETTINGS:
        try:
            saved_options.append(
                (set_command, mel.eval("{} -q;".format(query_command)))
            )
        except RuntimeError:
            pass

    try:
        yield
    finally:
        try:
            _set_animation_enabled(saved_animation_enabled)
        except RuntimeError:
            pass
        for set_command, value in reversed(saved_options):
            try:
                _set_option(set_command, value)
            except RuntimeError:
                pass
        cmds.select(clear=True)
        if original_selection:
            cmds.select(original_selection, replace=True, noExpand=True)


def _ensure_fbx_plugin():
    if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
        cmds.loadPlugin("fbxmaya")


def _mesh_export_nodes(mesh_transforms):
    nodes = list(mesh_transforms)
    for transform in mesh_transforms:
        nodes.extend(
            cmds.listRelatives(
                transform,
                shapes=True,
                noIntermediate=True,
                fullPath=True,
                type="mesh",
            )
            or []
        )
    return nodes


def _prepare_common_options():
    _set_option("FBXExportConstraints", False)
    _set_option("FBXExportCameras", False)
    _set_option("FBXExportLights", False)
    _set_option("FBXExportEmbeddedTextures", False)
    _set_option("FBXExportIncludeChildren", False)


def _temporary_fbx_path(output_path):
    stem, extension = os.path.splitext(output_path)
    return "{}.tmp{}".format(stem, extension or ".fbx")


def _export_selected(output_path, nodes):
    if not nodes:
        raise ValueError("There are no nodes to export.")
    if os.path.exists(output_path):
        raise ValueError("The output FBX already exists: {}".format(output_path))

    output_directory = os.path.dirname(output_path)
    if not os.path.isdir(output_directory):
        os.makedirs(output_directory)

    temporary_path = _temporary_fbx_path(output_path)
    if os.path.exists(temporary_path):
        os.remove(temporary_path)

    try:
        cmds.select(clear=True)
        cmds.select(nodes, replace=True, noExpand=True)
        mel_path = temporary_path.replace("\\", "/").replace('"', '\\"')
        mel.eval('FBXExport -f "{}" -s;'.format(mel_path))
        if not os.path.isfile(temporary_path) or os.path.getsize(temporary_path) == 0:
            raise RuntimeError("Maya did not create a valid FBX file.")
        os.replace(temporary_path, output_path)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


def export_rig(output_path, joints, mesh_transforms):
    """Export selected mesh and skeleton without baking animation."""
    _require_maya()
    _ensure_fbx_plugin()
    nodes = list(joints) + _mesh_export_nodes(mesh_transforms)

    with _preserve_export_state():
        _prepare_common_options()
        _set_animation_enabled(False)
        _set_option("FBXExportAnimationOnly", False)
        _set_option("FBXExportBakeComplexAnimation", False)
        _set_option("FBXExportBakeResampleAnimation", False)
        _set_option("FBXExportSkins", True)
        _set_option("FBXExportShapes", True)
        _set_option("FBXExportSmoothingGroups", True)
        _set_option("FBXExportInputConnections", False)
        _export_selected(output_path, nodes)


def export_animation(output_path, joints, start_frame, end_frame):
    """Export only skeleton animation and bake the requested frame range."""
    _require_maya()
    if start_frame > end_frame:
        raise ValueError("Animation start frame must not exceed end frame.")
    _ensure_fbx_plugin()

    with _preserve_export_state():
        _prepare_common_options()
        _set_animation_enabled(True)
        _set_option("FBXExportAnimationOnly", False)
        _set_option("FBXExportBakeComplexAnimation", True)
        _set_option("FBXExportBakeComplexStart", int(start_frame))
        _set_option("FBXExportBakeComplexEnd", int(end_frame))
        _set_option("FBXExportBakeComplexStep", 1)
        _set_option("FBXExportBakeResampleAnimation", True)
        _set_option("FBXExportSkins", False)
        _set_option("FBXExportShapes", False)
        _set_option("FBXExportInputConnections", False)
        _export_selected(output_path, list(joints))
