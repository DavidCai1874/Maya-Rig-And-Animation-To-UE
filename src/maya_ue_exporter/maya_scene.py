"""Maya scene selection discovery for exportable joints and meshes."""

from __future__ import absolute_import

import os

from .model import group_optional_joints

try:
    import maya.cmds as cmds
except ImportError:  # Allows pure-Python modules to be imported outside Maya.
    cmds = None


class CapturedSelection(object):
    """The stable full DAG paths captured from the user's Maya selection."""

    def __init__(self, joints, mesh_transforms, required_joints, optional_groups):
        self.joints = joints
        self.mesh_transforms = mesh_transforms
        self.required_joints = required_joints
        self.optional_groups = optional_groups

    def joints_for_groups(self, enabled_group_labels):
        """Return required joints plus the enabled optional IK/FK groups."""
        enabled = set(enabled_group_labels)
        result = list(self.required_joints)
        for label, nodes in self.optional_groups.items():
            if label in enabled:
                result.extend(nodes)
        return _sort_dag_paths(_include_joint_ancestors(result, self.joints))


def _maya_cmds(cmds_module=None):
    module = cmds_module or cmds
    if module is None:
        raise RuntimeError("This operation must run inside Maya.")
    return module


def _unique(items):
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _sort_dag_paths(items):
    return sorted(items, key=lambda item: (item.count("|"), item.lower()))


def _include_joint_ancestors(selected_joints, all_joints):
    """Keep every selected joint's joint ancestors so hierarchy stays valid."""
    all_joint_set = set(all_joints)
    result = set(selected_joints)
    for joint in list(selected_joints):
        parent_path = joint.rsplit("|", 1)[0]
        while parent_path:
            if parent_path in all_joint_set:
                result.add(parent_path)
            parent_path = parent_path.rsplit("|", 1)[0]
    return list(result)


def _mesh_parent(mesh_shape, maya_cmds):
    parents = maya_cmds.listRelatives(mesh_shape, parent=True, fullPath=True) or []
    return parents[0] if parents else None


def _mesh_shapes_below(node, maya_cmds):
    shapes = []
    if maya_cmds.nodeType(node) == "mesh":
        shapes.append(node)
    else:
        shapes.extend(
            maya_cmds.listRelatives(
                node,
                shapes=True,
                noIntermediate=True,
                fullPath=True,
                type="mesh",
            )
            or []
        )
        shapes.extend(
            maya_cmds.listRelatives(
                node,
                allDescendents=True,
                noIntermediate=True,
                fullPath=True,
                type="mesh",
            )
            or []
        )
    return shapes


def capture_selection(cmds_module=None):
    """Expand selected roots/groups into joints and polygon mesh transforms."""
    maya_cmds = _maya_cmds(cmds_module)
    selected = maya_cmds.ls(selection=True, long=True, objectsOnly=True) or []
    if not selected:
        raise ValueError("Select at least one skeleton root and mesh.")

    joints = []
    mesh_transforms = []

    for node in selected:
        node_type = maya_cmds.nodeType(node)
        if node_type == "joint":
            joints.append(node)
            joints.extend(
                maya_cmds.listRelatives(
                    node,
                    allDescendents=True,
                    fullPath=True,
                    type="joint",
                )
                or []
            )
        elif node_type != "mesh":
            joints.extend(
                maya_cmds.listRelatives(
                    node,
                    allDescendents=True,
                    fullPath=True,
                    type="joint",
                )
                or []
            )

        for mesh_shape in _mesh_shapes_below(node, maya_cmds):
            parent = _mesh_parent(mesh_shape, maya_cmds)
            if parent:
                mesh_transforms.append(parent)

    joints = _sort_dag_paths(_unique(joints))
    mesh_transforms = _sort_dag_paths(_unique(mesh_transforms))
    if not joints:
        raise ValueError("The selection does not contain a joint hierarchy.")

    required_joints, optional_groups = group_optional_joints(joints)
    return CapturedSelection(
        joints=joints,
        mesh_transforms=mesh_transforms,
        required_joints=required_joints,
        optional_groups=optional_groups,
    )


def timeline_range(cmds_module=None):
    """Return Maya's current playback range as whole frames."""
    maya_cmds = _maya_cmds(cmds_module)
    start = int(round(maya_cmds.playbackOptions(query=True, minTime=True)))
    end = int(round(maya_cmds.playbackOptions(query=True, maxTime=True)))
    return start, end


def default_output_directory(cmds_module=None):
    """Use the scene directory, falling back to the Maya project root."""
    maya_cmds = _maya_cmds(cmds_module)
    scene_path = maya_cmds.file(query=True, sceneName=True) or ""
    if scene_path:
        return os.path.dirname(scene_path)
    return maya_cmds.workspace(query=True, rootDirectory=True) or ""
