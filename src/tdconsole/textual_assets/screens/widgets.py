from __future__ import annotations

from typing import Optional

from rich.align import Align
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.text import Text
from textual import on
from textual.reactive import reactive
from textual.widgets import Label, ListItem, ListView, Static

from tdconsole.core.find_instances import instance_name_to_instance, sync_filesystem_instances_to_db


class BSOD(Static):
    """Minimal placeholder; import from screens.bsod for full screen."""


class InstanceWidget(Static):
    """Rich panel showing the current working instance."""

    def __init__(self, inst: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        if isinstance(inst, str):
            inst = instance_name_to_instance(inst)
        if isinstance(inst, list):
            inst = inst[0] if inst else None
        self.inst = inst

    def _make_instance_panel(self) -> Panel:
        inst = self.inst
        if isinstance(inst, list):
            inst = inst[0] if inst else None

        status_color = "#e4e4e6"
        status_line = "○ No Instance Selected"
        line1 = "No External Running Port"
        line2 = "No Internal Running Port"

        if inst is None:
            pass
        elif inst.name == "_Create_Instance":
            status_color = "#1F66D1"
            status_line = "Create a New Instance"
            line1 = ""
            line2 = ""
        elif inst.status == "Running":
            status_color = "#22c55e"
            status_line = f"{inst.name}  ● Running"
            line1 = f"running on → ext: {inst.arg_ext}"
            line2 = f"running on → int: {inst.arg_int}"
        elif inst.status == "Not Running":
            status_color = "#ef4444"
            status_line = f"{inst.name}  ○ Not running"
            line1 = f"configured on → ext: {inst.cfg_ext}"
            line2 = f"configured on → int: {inst.cfg_int}"

        header = Text(status_line, style=f"bold {status_color}")
        body = Text(f"{line1}\n{line2}", style="#f9f9f9")

        return Panel(Group(header, body), border_style=status_color, expand=False)

    def render(self) -> RenderableType:
        return self._make_instance_panel()


class CurrentInstanceWidget(InstanceWidget):
    inst = reactive(None)

    def __init__(self, instance: Optional[str] = None, **kwargs):
        super().__init__(instance, **kwargs)
        self.instance = instance

    def render(self) -> RenderableType:
        instance_panel = self._make_instance_panel()
        header = Align.center(Text("Current Working Instance:", style="bold #22c55e"))
        inner = Group(header, Align.center(instance_panel))
        outer = Panel(inner, border_style="#0f766e", expand=False)
        return Align.center(outer)

    def resolve_working_instance(self, instance=None):
        if isinstance(instance, str):
            instance = instance_name_to_instance(instance)
        if isinstance(instance, list):
            instance = instance[0] if instance else None
        sync_filesystem_instances_to_db(app=self.app)
        working_instance = self.app.app_query_one("instances", working=True)
        self.inst = working_instance or instance


class LabelItem(ListItem):
    def __init__(self, label: str, override_label=None) -> None:
        super().__init__()
        if isinstance(label, str):
            self.front = Label(label)
        else:
            self.front = label
        self.label = override_label if override_label is not None else label

    def compose(self):
        yield self.front


class ListScreenMixin:
    """Shared behavior for list-based screens."""

    def list_items(self, choices):
        choice_labels = [LabelItem(i) for i in choices]
        self.list = ListView(*choice_labels)
        return self.list
