"""Dockable PySide user interface for Maya FBX publishing."""

from __future__ import absolute_import

import os

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
import maya.cmds as cmds

try:
    from PySide6 import QtWidgets
except ImportError:
    from PySide2 import QtWidgets

from . import fbx_export
from . import maya_scene
from . import model


WINDOW_OBJECT_NAME = "MayaUEFbxExporter"
_WINDOW = None


class ExporterWindow(MayaQWidgetDockableMixin, QtWidgets.QDialog):
    """Capture a Maya character selection and export rig or animation FBX."""

    def __init__(self, parent=None):
        super(ExporterWindow, self).__init__(parent=parent)
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle("Maya to UE FBX Exporter")
        self.setMinimumWidth(440)

        self._capture = None
        self._rig_profile = None
        self._group_checkboxes = {}
        self._build_ui()
        self._connect_signals()
        self._set_default_values()
        self._update_previews()

    def _build_ui(self):
        root_layout = QtWidgets.QVBoxLayout(self)

        output_group = QtWidgets.QGroupBox("Naming and Output")
        output_layout = QtWidgets.QGridLayout(output_group)
        self.name_edit = QtWidgets.QLineEdit()
        self.output_edit = QtWidgets.QLineEdit()
        self.browse_button = QtWidgets.QPushButton("Browse...")
        output_layout.addWidget(QtWidgets.QLabel("Name"), 0, 0)
        output_layout.addWidget(self.name_edit, 0, 1, 1, 2)
        output_layout.addWidget(QtWidgets.QLabel("Output Folder"), 1, 0)
        output_layout.addWidget(self.output_edit, 1, 1)
        output_layout.addWidget(self.browse_button, 1, 2)
        output_layout.setColumnStretch(1, 1)
        root_layout.addWidget(output_group)

        selection_group = QtWidgets.QGroupBox("Skeleton and Mesh Selection")
        selection_layout = QtWidgets.QVBoxLayout(selection_group)
        self.capture_button = QtWidgets.QPushButton("Use Current Selection")
        self.selection_summary = QtWidgets.QLabel("No selection captured")
        self.selection_summary.setWordWrap(True)
        selection_layout.addWidget(self.capture_button)
        selection_layout.addWidget(self.selection_summary)
        selection_layout.addWidget(QtWidgets.QLabel("Optional IK / FK chains"))

        self.optional_container = QtWidgets.QWidget()
        self.optional_layout = QtWidgets.QVBoxLayout(self.optional_container)
        self.optional_layout.setContentsMargins(12, 0, 0, 0)
        self.no_optional_label = QtWidgets.QLabel("No IK/FK naming groups found")
        self.optional_layout.addWidget(self.no_optional_label)
        selection_layout.addWidget(self.optional_container)
        root_layout.addWidget(selection_group)

        rig_group = QtWidgets.QGroupBox("Rig Export (No Animation Bake)")
        rig_layout = QtWidgets.QVBoxLayout(rig_group)
        self.rig_preview = QtWidgets.QLabel("-")
        self.export_rig_button = QtWidgets.QPushButton("Export Rig")
        rig_layout.addWidget(self.rig_preview)
        rig_layout.addWidget(self.export_rig_button)
        root_layout.addWidget(rig_group)

        animation_group = QtWidgets.QGroupBox(
            "Animation Export (Skeleton Only + Bake)"
        )
        animation_layout = QtWidgets.QGridLayout(animation_group)
        self.sequence_edit = QtWidgets.QLineEdit()
        self.start_spin = QtWidgets.QSpinBox()
        self.end_spin = QtWidgets.QSpinBox()
        for spinbox in (self.start_spin, self.end_spin):
            spinbox.setRange(-1000000, 1000000)
        self.timeline_button = QtWidgets.QPushButton("Use Timeline Range")
        self.animation_preview = QtWidgets.QLabel("-")
        self.export_animation_button = QtWidgets.QPushButton("Export Animation")
        animation_layout.addWidget(QtWidgets.QLabel("Sequence Name"), 0, 0)
        animation_layout.addWidget(self.sequence_edit, 0, 1, 1, 3)
        animation_layout.addWidget(QtWidgets.QLabel("Start"), 1, 0)
        animation_layout.addWidget(self.start_spin, 1, 1)
        animation_layout.addWidget(QtWidgets.QLabel("End"), 1, 2)
        animation_layout.addWidget(self.end_spin, 1, 3)
        animation_layout.addWidget(self.timeline_button, 2, 0, 1, 4)
        animation_layout.addWidget(self.animation_preview, 3, 0, 1, 4)
        animation_layout.addWidget(self.export_animation_button, 4, 0, 1, 4)
        animation_layout.setColumnStretch(1, 1)
        animation_layout.setColumnStretch(3, 1)
        root_layout.addWidget(animation_group)

        self.status_label = QtWidgets.QLabel("Ready")
        self.status_label.setWordWrap(True)
        root_layout.addWidget(self.status_label)
        root_layout.addStretch(1)

    def _connect_signals(self):
        self.browse_button.clicked.connect(self._browse_output)
        self.capture_button.clicked.connect(self._capture_selection)
        self.timeline_button.clicked.connect(self._use_timeline_range)
        self.export_rig_button.clicked.connect(self._export_rig)
        self.export_animation_button.clicked.connect(self._export_animation)
        self.name_edit.textChanged.connect(self._update_previews)
        self.sequence_edit.textChanged.connect(self._update_previews)
        self.output_edit.textChanged.connect(self._update_previews)

    def _set_default_values(self):
        self.output_edit.setText(maya_scene.default_output_directory())
        self._use_timeline_range()

    def _browse_output(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Choose FBX Output Folder",
            self.output_edit.text() or maya_scene.default_output_directory(),
        )
        if directory:
            self.output_edit.setText(directory)

    def _clear_optional_checkboxes(self):
        for checkbox in self._group_checkboxes.values():
            self.optional_layout.removeWidget(checkbox)
            checkbox.deleteLater()
        self._group_checkboxes = {}

    def _capture_selection(self):
        try:
            self._capture = maya_scene.capture_selection()
            self._rig_profile = None
            self._clear_optional_checkboxes()
            self.no_optional_label.setVisible(not bool(self._capture.optional_groups))

            for label, nodes in self._capture.optional_groups.items():
                checkbox = QtWidgets.QCheckBox(
                    "{}  ({} joints)".format(label, len(nodes))
                )
                checkbox.setChecked(True)
                checkbox.stateChanged.connect(self._update_selection_summary)
                self.optional_layout.addWidget(checkbox)
                self._group_checkboxes[label] = checkbox

            self._update_selection_summary()
            self._set_status("Selection captured.")
        except Exception as exc:
            self._show_error(str(exc))

    def _enabled_groups(self):
        return [
            label
            for label, checkbox in self._group_checkboxes.items()
            if checkbox.isChecked()
        ]

    def _selected_joints(self):
        if self._capture is None:
            raise ValueError("Capture the current skeleton and mesh selection first.")
        joints = self._capture.joints_for_groups(self._enabled_groups())
        if not joints:
            raise ValueError("No joints are enabled for export.")
        return joints

    def _update_selection_summary(self, *unused):
        if self._capture is None:
            self.selection_summary.setText("No selection captured")
            return
        selected_joint_count = len(
            self._capture.joints_for_groups(self._enabled_groups())
        )
        self.selection_summary.setText(
            "{} / {} joints enabled, {} mesh transforms captured".format(
                selected_joint_count,
                len(self._capture.joints),
                len(self._capture.mesh_transforms),
            )
        )

    def _use_timeline_range(self):
        start, end = maya_scene.timeline_range()
        self.start_spin.setValue(start)
        self.end_spin.setValue(end)

    def _output_directory(self):
        directory = self.output_edit.text().strip()
        if not directory:
            raise ValueError("Output Folder is required.")
        return os.path.normpath(directory)

    def _rig_output_path(self):
        directory = self._output_directory()
        stem = model.rig_stem(self.name_edit.text())
        version = model.next_version(directory, stem)
        return os.path.join(directory, model.versioned_filename(stem, version))

    def _animation_output_path(self):
        directory = self._output_directory()
        stem = model.animation_stem(self.name_edit.text(), self.sequence_edit.text())
        version = model.next_version(directory, stem)
        return os.path.join(directory, model.versioned_filename(stem, version))

    def _update_previews(self, *unused):
        try:
            self.rig_preview.setText(os.path.basename(self._rig_output_path()))
        except ValueError:
            self.rig_preview.setText("Name_Rig_V001.fbx")

        try:
            self.animation_preview.setText(
                os.path.basename(self._animation_output_path())
            )
        except ValueError:
            self.animation_preview.setText("Name_SequenceName_V001.fbx")

    def _export_rig(self):
        try:
            if self._capture is None or not self._capture.mesh_transforms:
                raise ValueError("Capture at least one mesh for Rig export.")
            output_path = self._rig_output_path()
            joints = self._selected_joints()
            fbx_export.export_rig(
                output_path,
                joints,
                self._capture.mesh_transforms,
            )
            self._rig_profile = tuple(joints)
            self._set_status("Exported rig: {}".format(output_path))
            self._update_previews()
        except Exception as exc:
            self._show_error(str(exc))

    def _export_animation(self):
        try:
            output_path = self._animation_output_path()
            joints = self._selected_joints()
            if self._rig_profile is not None and tuple(joints) != self._rig_profile:
                raise ValueError(
                    "IK/FK selection differs from the last Rig export. "
                    "Restore the same options or capture the selection again."
                )
            fbx_export.export_animation(
                output_path,
                joints,
                self.start_spin.value(),
                self.end_spin.value(),
            )
            self._set_status("Exported animation: {}".format(output_path))
            self._update_previews()
        except Exception as exc:
            self._show_error(str(exc))

    def _set_status(self, message):
        self.status_label.setText(message)

    def _show_error(self, message):
        self._set_status("Error: {}".format(message))
        QtWidgets.QMessageBox.critical(self, "Maya to UE FBX Exporter", message)


def show_window():
    """Create one dockable exporter window and return it."""
    global _WINDOW
    workspace_control = WINDOW_OBJECT_NAME + "WorkspaceControl"
    if cmds.workspaceControl(workspace_control, query=True, exists=True):
        cmds.deleteUI(workspace_control)

    _WINDOW = ExporterWindow()
    _WINDOW.show(dockable=True, floating=True, retain=False)
    return _WINDOW
