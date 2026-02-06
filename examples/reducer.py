"""
Reducer Example - Demonstrates use_reducer hook.

Shows how to manage complex state using actions and reducers,
similar to Redux or React's useReducer.
"""

from dataclasses import dataclass

from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Input, Static

from textual_reactive import StateChanged, use_model_reducer


# --- State Model ---


class CounterState(BaseModel):
    """State for the counter with history."""

    count: int = 0
    history: list[str] = []
    step: int = 1


# --- Actions ---


@dataclass
class Increment:
    """Increment the counter by step amount."""

    pass


@dataclass
class Decrement:
    """Decrement the counter by step amount."""

    pass


@dataclass
class SetStep:
    """Change the step size."""

    step: int


@dataclass
class Reset:
    """Reset to initial state."""

    pass


@dataclass
class Undo:
    """Undo last action."""

    pass


Action = Increment | Decrement | SetStep | Reset | Undo


# --- Reducer ---


def counter_reducer(state: CounterState, action: Action) -> CounterState:
    """Process actions and return new state."""
    match action:
        case Increment():
            new_count = state.count + state.step
            return state.model_copy(
                update={
                    "count": new_count,
                    "history": [*state.history, f"+{state.step} = {new_count}"],
                }
            )

        case Decrement():
            new_count = state.count - state.step
            return state.model_copy(
                update={
                    "count": new_count,
                    "history": [*state.history, f"-{state.step} = {new_count}"],
                }
            )

        case SetStep(step):
            if step > 0:
                return state.model_copy(update={"step": step})
            return state

        case Reset():
            return CounterState()

        case Undo():
            if len(state.history) > 0:
                # Parse last history entry to get previous count
                # This is a simplified undo - in real apps you'd store snapshots
                return state.model_copy(
                    update={"history": state.history[:-1]}
                )
            return state

    return state


class ReducerCounter(App):
    """Counter app using useReducer pattern."""

    CSS = """
    Screen {
        layout: vertical;
        align: center middle;
        padding: 2;
    }

    #count-display {
        width: 100%;
        height: 5;
        text-align: center;
        text-style: bold;
        background: $primary;
        content-align: center middle;
    }

    #step-display {
        width: 100%;
        height: 3;
        text-align: center;
        background: $surface;
    }

    #history {
        width: 100%;
        height: 10;
        border: solid $secondary;
        padding: 1;
        overflow-y: auto;
    }

    Horizontal {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 1;
    }

    Button {
        margin: 0 1;
    }

    Input {
        width: 10;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Count: 0", id="count-display")
        yield Static("Step: 1", id="step-display")

        with Horizontal():
            yield Button("-", id="dec", variant="error")
            yield Button("+", id="inc", variant="success")
            yield Button("Reset", id="reset", variant="warning")

        with Horizontal():
            yield Static("Step size: ")
            yield Input(value="1", id="step-input", type="integer")
            yield Button("Set", id="set-step")

        yield Static("History:", id="history-label")
        yield Static("", id="history")

    def on_mount(self) -> None:
        # Initialize reducer state
        self.counter = use_model_reducer(self, counter_reducer, CounterState())
        self._update_display()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "inc":
                self.counter.dispatch(Increment())
            case "dec":
                self.counter.dispatch(Decrement())
            case "reset":
                self.counter.dispatch(Reset())
            case "set-step":
                try:
                    step = int(self.query_one("#step-input", Input).value)
                    self.counter.dispatch(SetStep(step))
                except ValueError:
                    pass

    def on_state_changed(self, event: StateChanged[CounterState]) -> None:
        self._update_display()

    def _update_display(self) -> None:
        state = self.counter.value

        self.query_one("#count-display", Static).update(
            f"Count: {state.count}"
        )
        self.query_one("#step-display", Static).update(
            f"Step: {state.step}"
        )

        history_text = "\n".join(state.history[-10:]) if state.history else "(empty)"
        self.query_one("#history", Static).update(history_text)


if __name__ == "__main__":
    ReducerCounter().run()
