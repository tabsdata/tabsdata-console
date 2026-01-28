from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Awaitable, Callable, Iterable, List, Optional

from textual import on
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.events import ScreenResume
from textual.screen import Screen
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Label,
    ListView,
    RichLog,
    Static,
)
from textual.widgets._tree import TreeNode

from tdconsole.textual_assets.spinners import SpinnerWidget


class BSOD(Screen):
    """Basic error screen placeholder; consider moving full implementation here."""


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskSpec:
    description: str
    func: Callable[[str | None], Awaitable[Optional[int]]]
    background: bool = False


class TaskRow(Horizontal):
    STATUS_ICONS = {
        TaskStatus.PENDING: "●",
        TaskStatus.RUNNING: "⏳",
        TaskStatus.SUCCEEDED: "✅",
        TaskStatus.FAILED: "❌",
        TaskStatus.SKIPPED: "⤴",
    }

    STATUS_STYLES = {
        TaskStatus.PENDING: "dim",
        TaskStatus.RUNNING: "bold cyan",
        TaskStatus.SUCCEEDED: "green",
        TaskStatus.FAILED: "red",
        TaskStatus.SKIPPED: "yellow",
    }

    def __init__(self, description: str, task_id: str) -> None:
        super().__init__(id=task_id, classes="task-row")
        self.description = description
        self.status = TaskStatus.PENDING

    def compose(self):
        spinner = SpinnerWidget("dots", id=f"{self.id}-spinner", classes="task-spinner")
        spinner.display = False
        yield spinner
        yield Label(self.description, id=f"{self.id}-label", classes="task-label")

    def set_status(self, status: TaskStatus, exit_code: Optional[int] = None) -> None:
        self.status = status
        spinner = self.query_one(f"#{self.id}-spinner")
        spinner.display = status == TaskStatus.RUNNING

        icon = self.STATUS_ICONS.get(status, "●")
        style = self.STATUS_STYLES.get(status, "dim")
        text = (
            f"{icon} {self.description} (exit {exit_code})"
            if status == TaskStatus.FAILED and exit_code not in (None, 0)
            else f"{icon} {self.description}"
        )
        self.query_one(f"#{self.id}-label", Label).update(f"[{style}]{text}[/]")


class SequentialTasksScreenTemplate(Screen):
    BINDINGS = [("enter", "press_close", "Done")]

    CSS = """
    Screen { background: #111316; }
    * { height: auto; color: #e5e7eb; }
    #tasks-wrapper { background: #111316; padding: 1 0; }
    #tasks-header { padding: 1 2; text-style: bold; color: #e5e7eb; background: #1a1f27; border: round #22c55e; }
    #tasks-subtitle { color: #9ca3af; padding: 0 2 1 2; }
    .task-row { height: 3; content-align: left middle; background: #1a1f27; border: heavy #22c55e; margin: 0 2 1 2; padding: 0 1; border-title-align: left; }
    .task-spinner { width: 5; }
    .task-label { padding-left: 1; }
    #task-log { padding: 1 2; border: panel round #22c55e; overflow-y: auto; height: 20; width: 85%; background: #0f1117; }
    #task-box { align: center top; }
    #done-row { height: 3; content-align: center middle; }
    VerticalScroll { height: 1fr; overflow-y: auto; background: transparent; }
    """

    def __init__(self, tasks: List[TaskSpec] | None = None) -> None:
        super().__init__()
        self.tasks = tasks or []
        self.task_rows: List[TaskRow] = []
        self.log_widget: RichLog | None = None
        self.failed: bool = False
        self._background_tasks: list[asyncio.Task] = []

    def compose(self):
        for index, task in enumerate(self.tasks):
            row = TaskRow(task.description, task_id=f"task-{index}")
            self.task_rows.append(row)

        self.done_button = Button("Done", id="close-btn")
        self.done_button.display = False
        self.done_row = Horizontal(self.done_button, id="done-row")
        self.done_row.display = False

        yield VerticalScroll(
            Vertical(
                Static("Task Runner", id="tasks-header"),
                Static(
                    "We’ll run each step and stream logs below.", id="tasks-subtitle"
                ),
                *self.task_rows,
                Static(""),
                Container(
                    RichLog(
                        id="task-log", auto_scroll=False, max_lines=500, markup=True
                    ),
                    id="task-box",
                ),
                Static(""),
                self.done_row,
                Footer(),
            ),
            id="tasks-wrapper",
        )

    def conclude_tasks(self) -> None:
        self.query_one(VerticalScroll).scroll_end(animate=False)

    async def on_mount(self) -> None:
        self.log_widget = self.query_one("#task-log", RichLog)
        self.log_line(None, "Starting setup tasks…")
        asyncio.create_task(self.run_tasks())

    def log_line(self, task: str | None, msg: str) -> None:
        line = f"[bold]{task}[/]: {msg}" if task else msg
        if self.log_widget:
            self.log_widget.write(line)

    async def run_logged_subprocess(self, label: str | None, *args: str) -> int:
        self.log_line(label, f"Running: {' '.join(args)}")
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            text = line.decode().rstrip("\n")
            self.log_line(label, text)
        code = await process.wait()
        self.log_line(label, f"Exited with code {code}")
        return code

    async def run_single_task(self, idx: int, task: TaskSpec) -> int | None:
        row = self.task_rows[idx]
        row.set_status(TaskStatus.RUNNING)
        self.log_line(task.description, "Starting")
        code: int | None = None
        try:
            result = await task.func(task.description)
            code = result if isinstance(result, int) else None
            self.log_line(task.description, "Finished")
            row.set_status(
                TaskStatus.SUCCEEDED if code in (0, None) else TaskStatus.FAILED, code
            )
        except Exception as e:
            self.log_line(task.description, f"Error: {e!r}")
            row.set_status(TaskStatus.FAILED, exit_code=1)
            code = 1
        return code

    async def abort_all_tasks(self) -> None:
        if self.failed:
            return
        self.failed = True
        self.log_line(None, "❌ Aborting remaining tasks due to failure.")
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        for row in self.task_rows:
            spinner = row.query_one(f"#{row.id}-spinner")
            if getattr(spinner, "display", False):
                row.set_status(TaskStatus.FAILED, exit_code=1)
            elif row.status == TaskStatus.PENDING:
                row.set_status(TaskStatus.SKIPPED)

    async def _background_wrapper(self, idx: int, task: TaskSpec) -> None:
        try:
            code = await self.run_single_task(idx, task)
        except asyncio.CancelledError:
            self.log_line(task.description, "Cancelled")
            return
        if code not in (0, None):
            await self.abort_all_tasks()

    def action_press_close(self) -> None:
        try:
            btn = self.query_one("#close-btn", Button)
        except Exception:
            return
        btn.press()

    async def run_tasks(self) -> None:
        self._background_tasks = []
        for i, t in enumerate(self.tasks):
            if t.background:
                self.log_line(t.description, "Scheduling background task")
                self._background_tasks.append(
                    asyncio.create_task(self._background_wrapper(i, t))
                )

        for i, t in enumerate(self.tasks):
            if self.failed:
                break
            if not t.background:
                code = await self.run_single_task(i, t)
                if code not in (0, None):
                    await self.abort_all_tasks()
                    break

        if self.failed:
            for row in self.task_rows:
                if row.status == TaskStatus.PENDING:
                    row.set_status(TaskStatus.SKIPPED)

        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        self.log_line(
            None,
            (
                "⚠️ Tasks aborted due to failure."
                if self.failed
                else "🎉 All tasks complete."
            ),
        )
        self.conclude_tasks()

        if getattr(self, "done_row", None):
            self.done_row.display = True
            self.done_button.display = True
            self.done_button.focus()


class ListScreenTemplate(Screen):
    def __init__(self, choice_dict=None, header="Select a File: "):
        super().__init__()
        self.choice_dict = choice_dict or {}
        self.choices = list(self.choice_dict.keys())
        self.header = header

    def compose(self):
        with VerticalScroll():
            if self.header is not None:
                yield Label(self.header, id="listHeader")
            yield CurrentInstanceWidget(
                self.app.working_instance, id="CurrentInstanceWidget"
            )
            yield self.list_items()
            yield Footer()

    def on_show(self) -> None:
        self.set_focus(self.list)

    def list_items(self):
        choice_labels = [LabelItem(i) for i in self.choices]
        self.list = ListView(*choice_labels)
        return self.list

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        selected = event.item.label
        if selected in self.choices and self.choice_dict[selected] is not None:
            screen = self.choice_dict[selected]
            self.app.push_screen(screen())
        else:
            self.app.push_screen(BSOD())

    @on(ScreenResume)
    def refresh_current_instance_widget(self, event: ScreenResume):
        widget = self.query_one("#CurrentInstanceWidget")
        widget.resolve_working_instance()


class PyOnlyDirectoryTree(DirectoryTree):
    DEFAULT_CSS = """
    DirectoryTree {
        & > .directory-tree--folder { text-style: bold; color: green; }
        & > .directory-tree--extension { text-style: italic; }
        & > .directory-tree--file { text-style: italic; color: green; }
        & > .directory-tree--hidden { text-style: dim; }
        &:ansi {
            & > .tree--guides { color: transparent; }
            & > .directory-tree--folder { text-style: bold; }
            & > .directory-tree--extension { text-style: italic; }
            & > .directory-tree--hidden { color: ansi_default; text-style: dim; }
        }
    }
    """

    def __init__(
        self, path: str | Path, *, auto_expand_depth: int = 5, **kwargs
    ) -> None:
        self.auto_expand_depth = auto_expand_depth
        super().__init__(path, **kwargs)

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        result: list[Path] = []
        for p in paths:
            if p.is_file() and p.suffix == ".py":
                if self._file_is_tabsdata_function(p):
                    result.append(p)
            elif p.is_dir():
                if self._dir_has_py(p, depth=0, max_depth=self.auto_expand_depth):
                    result.append(p)
        return result

    def _file_is_tabsdata_function(self, path: Path) -> bool:
        if path.suffix != ".py":
            return False
        try:
            source = path.read_text()
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError):
            return False
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for deco in node.decorator_list:
                    func = deco.func if isinstance(deco, ast.Call) else deco
                    if isinstance(func, ast.Attribute) and isinstance(
                        func.value, ast.Name
                    ):
                        if func.value.id == "td" and func.attr in {
                            "publisher",
                            "subscriber",
                            "transformer",
                        }:
                            return True
        return False

    def _dir_has_py(self, path: Path, depth: int = 0, max_depth: int = 5) -> bool:
        if depth > max_depth:
            return False
        try:
            for entry in path.iterdir():
                if entry.is_file() and entry.suffix == ".py":
                    if self._file_is_tabsdata_function(entry):
                        return True
                elif entry.is_dir():
                    if self._dir_has_py(entry, depth + 1, max_depth):
                        return True
        except PermissionError:
            return False
        return False

    async def on_mount(self) -> None:
        await self._expand_to_depth(
            self.root, depth=0, max_depth=self.auto_expand_depth
        )

    async def _expand_to_depth(
        self, node: TreeNode, depth: int, max_depth: int
    ) -> None:
        if depth >= max_depth:
            return
        await self._add_to_load_queue(node)
        for child in node.children:
            data = child.data
            if data is None:
                continue
            path = getattr(data, "path", None)
            if isinstance(path, Path) and path.is_dir():
                await self._expand_to_depth(child, depth + 1, max_depth)

    @on(DirectoryTree.NodeExpanded)
    def set_file_color(self, event: DirectoryTree.NodeExpanded):
        for i in event.node.children:
            if i.data.path.is_file():
                i.label.stylize("green")
        self.refresh()
