"""Maya UI entry point for the Maya to Unreal FBX exporter."""

from __future__ import absolute_import


def show():
    """Open the dockable exporter window inside Maya."""
    from .ui import show_window

    return show_window()


__all__ = ["show"]
