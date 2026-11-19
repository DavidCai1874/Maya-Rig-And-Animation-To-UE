"""Pure-Python naming and IK/FK grouping helpers."""

from __future__ import absolute_import

import os
import re
from collections import OrderedDict


_OPTIONAL_TOKEN_RE = re.compile(r"(?:^|[_\-\s])(IK|FK)(?=$|[_\-\s])", re.IGNORECASE)
_INVALID_FILE_CHARS_RE = re.compile(r'[<>:"/\\|?*]')


def leaf_name(node_name):
    """Return a Maya DAG node's leaf name without its namespace."""
    leaf = node_name.rsplit("|", 1)[-1]
    return leaf.rsplit(":", 1)[-1]


def optional_chain_label(node_name):
    """Return the name through the first IK/FK token, or ``None``.

    For example, ``char:L_Arm_IK_01`` becomes ``L_Arm_IK``. Keeping the
    prefix through the token groups numbered members of the same optional
    chain without listing every joint in the UI.
    """
    name = leaf_name(node_name)
    match = _OPTIONAL_TOKEN_RE.search(name)
    if not match:
        return None
    return name[: match.end(1)].rstrip("_- ")


def group_optional_joints(joint_names):
    """Split joints into required joints and ordered IK/FK groups."""
    required = []
    groups = OrderedDict()
    canonical_labels = {}

    for joint_name in joint_names:
        label = optional_chain_label(joint_name)
        if label is None:
            required.append(joint_name)
            continue

        key = label.lower()
        display_label = canonical_labels.get(key)
        if display_label is None:
            display_label = label
            canonical_labels[key] = display_label
            groups[display_label] = []
        groups[display_label].append(joint_name)

    return required, groups


def validate_name_component(value, label):
    """Validate one user-controlled filename component and return it."""
    value = value.strip()
    if not value:
        raise ValueError("{} is required.".format(label))
    if _INVALID_FILE_CHARS_RE.search(value):
        raise ValueError("{} contains an invalid filename character.".format(label))
    if value.endswith((".", " ")):
        raise ValueError("{} cannot end with a dot or space.".format(label))
    return value


def rig_stem(name):
    """Return the unversioned rig filename stem."""
    return "{}_Rig".format(validate_name_component(name, "Name"))


def animation_stem(name, sequence_name):
    """Return the unversioned animation filename stem."""
    return "{}_{}".format(
        validate_name_component(name, "Name"),
        validate_name_component(sequence_name, "Sequence Name"),
    )


def next_version(output_directory, stem):
    """Return one plus the highest ``_V###.fbx`` version in a directory."""
    if not output_directory or not os.path.isdir(output_directory):
        return 1

    pattern = re.compile(
        r"^{}_V(\d+)\.fbx$".format(re.escape(stem)),
        re.IGNORECASE,
    )
    highest = 0
    for filename in os.listdir(output_directory):
        match = pattern.match(filename)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def versioned_filename(stem, version):
    """Build an FBX filename using at least three version digits."""
    return "{}_V{:03d}.fbx".format(stem, int(version))
