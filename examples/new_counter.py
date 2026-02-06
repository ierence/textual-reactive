"""
Simple Counter - Demonstrates the reducer context API.

Shows:
- use_reducer: Create reducer at parent level
- ReducerProvider: Share it with children
- use_reducer_context: Consume in children
- @effect: React to changes
"""

from dataclasses import dataclass

from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Button, Static

from textual_reactive import (
    create_reducer_context,
    effect,
    use_reducer,
    use_reducer_context,
    ReducerProvider,
)


# --- State ---

class CounterState(BaseModel):
    count: int = 0


# --- Actions ---

@dataclass
class Increment:
    pass


@dataclass
class Decrement:
    pass


@dataclass
class Reset:
    pass


# --- Reducer ---

def counter_reducer(state: CounterState, action) -> CounterState:
    match action:
        case Increment():
            return state.model_copy(update={"count": state.count + 1})
        case Decrement():
            return state.model_copy(update={"count": state.count - 1})
        case Reset():
            return CounterState()
    return state


# --- Context (defined once, imported where needed) ---

CounterContext = create_reducer_context("counter")


# --- Child Widget ---

class CounterDisplay(Container):
    """Display that consumes counter from context."""

    DEFAULT_CSS = """
    CounterDisplay {
        width: 100%;
        height: 100%;
        align: center middle;
    }

    #display {
        width: 100%;
        height: 5;
        text-align: center;
        text-style: bold;
        background: $primary;
        content-align: center middle;
    }

    Button {
        margin: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Count: 0", id="display")
        yield Button("+ Increment", id="inc", variant="success")
        yield Button("- Decrement", id="dec", variant="error")
        yield Button("Reset", id="reset")

    def on_mount(self) -> None:
        # Consume from context - no double wrapping!
        self.counter = use_reducer_context(self, CounterContext)

    @effect("counter")
    def on_counter_change(self, old: CounterState, new: CounterState) -> None:
        self.query_one("#display", Static).update(f"Count: {new.count}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "inc":
                self.counter.dispatch(Increment())
            case "dec":
                self.counter.dispatch(Decrement())
            case "reset":
                self.counter.dispatch(Reset())


# --- App ---

class Counter(App):
    """Counter app - creates reducer and provides to children."""

    CSS = """
    Screen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        # Create reducer at app level
        self.counter = use_reducer(self, counter_reducer, CounterState(), name="counter")

        # Provide to children - they consume via use_reducer_context
        yield ReducerProvider(CounterContext, self.counter,
            CounterDisplay(),
        )

    def on_mount(self) -> None:
        # App can use reducer directly too
        self.counter.dispatch(Increment())  # Start at 1


if __name__ == "__main__":
    Counter().run()
