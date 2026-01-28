from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll, Center
from textual.widgets import Button, Static

from tdconsole.textual_assets.spinners import SpinnerWidget


class BSOD(Static):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("left", "focus_back", "Focus Back"),
        ("right", "focus_exit", "Focus Exit"),
    ]

    CSS = """
    BSOD { background: blue; color: white; align: center middle; width: auto; }
    #wrapper { align: center middle; }
    #title { content-align: center middle; text-style: reverse; margin-bottom: 1; }
    #spinner { content-align: center middle; align: center middle; }
    #message { content-align: center middle; margin-bottom: 1; }
    #buttons { align: center middle; height: 3; }
    Button { margin: 0 2; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.ERROR_TEXT = "uh-oh, you've stumbled upon something Daniel hasn't built out yet :("

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="wrapper"):
            yield Static(" Bad News :() ", id="title")
            yield Horizontal(Center(SpinnerWidget("material", id="spinner")))
            yield Static(self.ERROR_TEXT, id="message")
            with Horizontal(id="buttons"):
                yield Button("Back", id="back-btn")
                yield Button("Exit", id="exit-btn")

    def on_mount(self) -> None:
        self.query_one("#back-btn", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "exit-btn":
            self.app.exit()

    def action_focus_back(self) -> None:
        self.query_one("#back-btn", Button).focus()

    def action_focus_exit(self) -> None:
        self.query_one("#exit-btn", Button).focus()
