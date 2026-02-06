"""Minimal debug counter."""

from dataclasses import dataclass
from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.widgets import Button, Static, Label

from textual_reactive import use_reducer


class CounterState(BaseModel):
    count: int = 0


@dataclass
class Increment:
    pass


def reducer(state: CounterState, action) -> CounterState:
    match action:
        case Increment():
            return state.model_copy(update={"count": state.count + 1})
    return state


class DebugCounter(App):
    """Simplest possible - no context, no effect decorator."""

    CSS = """
    Screen {
        align: center middle;
    }
    #display {
        text-align: center;
        width: 100%;
        height: 3;
        background: blue;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Debug Counter", id="title")
        yield Static("Count: 0", id="display")
        yield Button("Increment", id="inc")

    def on_mount(self) -> None:
        self.counter = use_reducer(self, reducer, CounterState(), name="counter")
        self.log(f"Counter initialized: {self.counter.value}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.counter.dispatch(Increment())
        self.log(f"After dispatch: {self.counter.value}")
        # Manual update - no @effect
        self.query_one("#display", Static).update(f"Count: {self.counter.value.count}")


if __name__ == "__main__":
    DebugCounter().run()
