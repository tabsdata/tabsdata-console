from rich.spinner import Spinner
from textual.widgets import Static


class SpinnerWidget(Static):
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+b", "go_back", "Go Back"),
    ]

    def __init__(self, spinner_name: str = "dots", *args, **kwargs) -> None:
        super().__init__("", *args, **kwargs)
        self._spinner = Spinner(spinner_name)

    def on_mount(self) -> None:
        self.set_interval(1 / 20, self.update_spinner)

    def update_spinner(self) -> None:
        self.update(self._spinner)
