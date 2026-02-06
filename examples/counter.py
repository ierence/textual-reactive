"""
Simple Counter Example - Demonstrates use_state hook.

This is the simplest example of using textual-reactive.
"""

from textual.app import App, ComposeResult
from textual.widgets import Button, Static

from textual_reactive import StateChanged, StateHandle, use_state


class Counter(App):
    """A simple counter application using use_state."""

    CSS = """
    Screen {
        align: center middle;
    }

    #counter {
        width: 100%;
        height: 3;
        text-align: center;
        text-style: bold;
        background: $primary;
        color: $text;
    }

    Button {
        margin: 1;
    }
    """

    count: StateHandle[int]

    def compose(self) -> ComposeResult:
        yield Static("Count: 0", id="counter")
        yield Button("Increment (+1)", id="inc")
        yield Button("Decrement (-1)", id="dec")
        yield Button("Reset", id="reset")

    def on_mount(self) -> None:
        # Create reactive state using the use_state hook
        self.count = use_state(self, 0, name="counter")
        self._update_display()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "inc":
                # Use functional update for safety
                self.count.set(lambda x: x + 1)
            case "dec":
                self.count.set(lambda x: x - 1)
            case "reset":
                # Direct value update
                self.count.set(0)

    def on_state_changed(self, event: StateChanged[int]) -> None:
        """Called automatically when state changes."""
        self._update_display()

    def _update_display(self) -> None:
        self.query_one("#counter", Static).update(f"Count: {self.count.value}")


if __name__ == "__main__":
    Counter().run()
