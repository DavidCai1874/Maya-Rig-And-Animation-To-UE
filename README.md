# Maya Rig and Animation to UE

A dockable Maya tool for exporting Unreal Engine-ready rig and animation FBX files.

## Features

- Captures joint hierarchies and polygon meshes from the current Maya selection.
- Detects optional joint chains containing standalone `IK` or `FK` name tokens.
- Groups numbered joints such as `L_Arm_IK_01` through `L_Arm_IK_04` into one `L_Arm_IK` checkbox.
- Exports a rig FBX containing the enabled joints and meshes, with animation disabled.
- Exports an animation FBX containing joints only, with the selected frame range baked at one sample per frame.
- Automatically generates and increments versioned filenames:
  - `Name_Rig_V001.fbx`
  - `Name_SequenceName_V001.fbx`
- Restores the original Maya selection and FBX export settings after each export.
- Writes through a temporary FBX before moving it to the final versioned path.

## Compatibility

- No third-party Python dependencies.
- Supports both PySide2 and PySide6 imports.
- Tested with Maya 2026.
- Designed for Maya 2022–2026.

## Installation and Launch

Open Maya's Script Editor, switch to the Python tab, and run:

```python
import sys

src_path = r"C:\path\to\Maya-Rig-And-Animation-To-UE\src"
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import maya_ue_exporter
maya_ue_exporter.show()
```

The same code can be saved as a Maya Shelf button. The exporter loads Maya's bundled `fbxmaya` plug-in when it is first needed.

## Usage

1. Select the skeleton root and one or more meshes. Alternatively, select a group containing both the skeleton and meshes.
2. Click `Use Current Selection`.
3. Enable or disable the detected chains under `Optional IK / FK chains`.
4. Enter `Name` and choose an output folder.
5. Click `Export Rig` to export a mesh-and-skeleton FBX without animation.
6. For animation, enter `Sequence Name`, set the start and end frames, and click `Export Animation`.

`Use Timeline Range` copies Maya's current playback range into the animation fields.

The exporter scans the output directory and uses the next available version instead of overwriting an existing FBX. After a successful rig export, the window also remembers its joint profile and prevents animation export if the IK/FK selection has changed. Click `Use Current Selection` again to begin a new profile.

## Naming Examples

With `Name` set to `Hero`:

```text
Hero_Rig_V001.fbx
```

With `Sequence Name` set to `Run_Fwd`:

```text
Hero_Run_Fwd_V001.fbx
```

Each rig and sequence has an independent version counter.

## Code Structure

```text
src/maya_ue_exporter/
  __init__.py    # Public show() entry point
  model.py       # Naming, IK/FK grouping, and version discovery
  maya_scene.py  # Maya selection and timeline access
  fbx_export.py  # Rig and animation FBX export profiles
  ui.py          # Dockable PySide2/PySide6 window
```

## Current Scope

This release implements the Maya exporter only. Automated Unreal Engine import, Skeleton matching, and Content Browser routing are planned for a later stage.
