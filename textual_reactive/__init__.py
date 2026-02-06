"""
Textual Reactive - React-like state management for Textual TUI framework.

This module provides React-inspired hooks and patterns for managing state
in Textual applications, including support for Pydantic models.

Key Features:
- use_state: Simple reactive state
- use_reducer: Complex state with actions/reducers
- create_store: Shared stores with provider/consumer pattern
- use_derived: Computed values from state
- @effect: Decorator to watch state changes
- Context: Share any value across widget trees

Example:
    ```python
    from pydantic import BaseModel
    from textual.app import App, ComposeResult
    from textual.widgets import Button, Static
    from textual_reactive import create_store, effect

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

    CounterStore = create_store(reducer, CounterState())

    class Counter(App):
        def compose(self) -> ComposeResult:
            yield CounterStore.provider(
                Static(id="count"),
                Button("Increment"),
            )

        def on_mount(self) -> None:
            self.counter = CounterStore.use(self)

        @effect(CounterStore)
        def on_count_change(self, old: CounterState, new: CounterState):
            self.query_one("#count", Static).update(f"Count: {new.count}")

        def on_button_pressed(self, event: Button.Pressed) -> None:
            self.counter.dispatch(Increment())
    ```
"""

# State primitives
from .state import (
    State,
    ModelState,
    StateChanged,
)

# Hooks
from .hooks import (
    StateHandle,
    ModelStateHandle,
    ReducerHandle,
    DerivedHandle,
    use_state,
    use_model_state,
    use_reducer,
    use_model_reducer,
    use_derived,
)

# Store (reducer + context combined)
from .store import (
    Store,
    StoreHandle,
    StoreProvider,
    create_store,
)

# Effects
from .effects import (
    effect,
)

# Context (for non-reducer use cases)
from .context import (
    Context,
    ModelContext,
    ContextProvider,
    ContextHandle,
    ModelContextHandle,
    ContextNotFoundError,
    create_context,
    create_model_context,
    use_context,
    provide_context,
)

# Reducer context (specialized, no double-wrapping)
from .reducer_context import (
    ReducerContext,
    ReducerProvider,
    create_reducer_context,
    use_reducer_context,
)

# Types
from .types import (
    Action,
    Reducer,
    StateCallback,
    SetterFunc,
    DispatchFunc,
)

__version__ = "0.1.0a1"

__all__ = [
    # State
    "State",
    "ModelState",
    "StateChanged",
    # Hooks
    "StateHandle",
    "ModelStateHandle",
    "ReducerHandle",
    "DerivedHandle",
    "use_state",
    "use_model_state",
    "use_reducer",
    "use_model_reducer",
    "use_derived",
    # Store
    "Store",
    "StoreHandle",
    "StoreProvider",
    "create_store",
    # Effects
    "effect",
    # Context
    "Context",
    "ModelContext",
    "ContextProvider",
    "ContextHandle",
    "ModelContextHandle",
    "ContextNotFoundError",
    "create_context",
    "create_model_context",
    "use_context",
    "provide_context",
    # Reducer context
    "ReducerContext",
    "ReducerProvider",
    "create_reducer_context",
    "use_reducer_context",
    # Types
    "Action",
    "Reducer",
    "StateCallback",
    "SetterFunc",
    "DispatchFunc",
]
