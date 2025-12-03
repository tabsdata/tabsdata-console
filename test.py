from textual.app import App
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual.widgets import Static

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class OverflowApp(App):
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+b", "go_back", "Go Back"),
    ]
    CSS = """Screen {
    background: $background;
    color: black;
}

VerticalScroll {
    width: 1fr;
}

Static {
    margin: 1 2;
    background: green 80%;
    border: green wide;
    color: white 90%;
    height: auto;
}

#ab {
    height: auto;
}

#bc {
    height: auto;
    width: 60%;
}
#bc1 {
    height: auto;
    width: 60%;
}
"""

    def compose(self):
        yield VerticalScroll(
            VerticalScroll(Static(TEXT), Static(TEXT), Static(TEXT), id="bc"),
            VerticalScroll(Static(TEXT), Static(TEXT), Static(TEXT), id="bc1"),
            id="ab",
        )


if __name__ == "__main__":
    app = OverflowApp()
    app.run()
