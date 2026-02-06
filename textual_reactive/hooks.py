"""React-like hooks for Textual widgets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar, overload

from pydantic import BaseModel
from textual.widget import Widget

from .state import ModelState, State, StateChanged
from .effects import connect_effects

T = TypeVar("T")
S = TypeVar("S", bound=BaseModel)
A = TypeVar("A")  # Action type


@dataclass(frozen=True, slots=True)
class StateHandle(Generic[T]):
    """
    A handle to a state value and its setter function.

    Attributes:
        value: The current state value (read-only snapshot).
        set: Function to update the state.
        state: The underlying State object for advanced usage.
    """

    state: State[T]
    _name: str | None = None

    @property
    def value(self) -> T:
        """Get the current state value."""
        return self.state.value

    @property
    def name(self) -> str | None:
        """Get the state name."""
        return self._name

    def set(self, value: T | Callable[[T], T]) -> None:
        """Set the state value."""
        self.state.set(value)

    def __call__(self) -> T:
        """Shorthand to get the current value."""
        return self.state.value


@dataclass(frozen=True, slots=True)
class ModelStateHandle(Generic[S]):
    """
    A handle to a Pydantic model state with field-level updates.

    Attributes:
        value: The current model (read-only snapshot).
        set: Function to replace the entire model.
        update: Function to update specific fields.
        state: The underlying ModelState object.
    """

    state: ModelState[S]
    _name: str | None = None

    @property
    def value(self) -> S:
        """Get the current model."""
        return self.state.value

    @property
    def name(self) -> str | None:
        """Get the state name."""
        return self._name

    def set(self, value: S | Callable[[S], S]) -> None:
        """Replace the entire model."""
        self.state.set(value)

    def update(self, **kwargs: Any) -> None:
        """Update specific fields of the model."""
        self.state.update(**kwargs)

    def __call__(self) -> S:
        """Shorthand to get the current model."""
        return self.state.value


@dataclass(frozen=True, slots=True)
class ReducerHandle(Generic[T, A]):
    """
    A handle to a reducer state and its dispatch function.

    Attributes:
        value: The current state value.
        dispatch: Function to dispatch actions.
        state: The underlying State object.
    """

    state: State[T]
    _dispatch: Callable[[A], None]
    _name: str | None = None

    @property
    def value(self) -> T:
        """Get the current state value."""
        return self.state.value

    @property
    def name(self) -> str | None:
        """Get the state name."""
        return self._name

    def dispatch(self, action: A) -> None:
        """Dispatch an action to the reducer."""
        self._dispatch(action)

    def __call__(self) -> T:
        """Shorthand to get the current value."""
        return self.state.value


@dataclass(frozen=True, slots=True)
class DerivedHandle(Generic[T]):
    """
    A handle to a derived (computed) value.

    Derived values are automatically recomputed when their source changes,
    but only trigger effects if the computed result is different.
    """

    state: State[T]
    _name: str | None = None

    @property
    def value(self) -> T:
        """Get the current computed value."""
        return self.state.value

    @property
    def name(self) -> str | None:
        """Get the derived state name."""
        return self._name

    def __call__(self) -> T:
        """Shorthand to get the current value."""
        return self.state.value


def use_state(
    widget: Widget,
    initial_value: T,
    *,
    name: str | None = None,
) -> StateHandle[T]:
    """
    Create a reactive state bound to a widget.

    Args:
        widget: The widget that owns this state.
        initial_value: The initial state value.
        name: Optional name for @effect decorator matching.

    Returns:
        A StateHandle with value property and set method.

    Example:
        ```python
        class Counter(Widget):
            def on_mount(self):
                self.count = use_state(self, 0, name="count")

            @effect("count")
            def on_count_change(self, old: int, new: int):
                self.refresh()
        ```
    """
    state = State(initial_value, name=name)
    state.subscribe(widget)

    handle = StateHandle(state=state, _name=name)

    # Connect @effect decorated methods
    if name:
        connect_effects(widget, name, state)

    return handle


def use_model_state(
    widget: Widget,
    initial_value: S,
    *,
    name: str | None = None,
) -> ModelStateHandle[S]:
    """
    Create a reactive Pydantic model state bound to a widget.

    Args:
        widget: The widget that owns this state.
        initial_value: The initial Pydantic model.
        name: Optional name for @effect decorator matching.

    Returns:
        A ModelStateHandle with value, set, and update methods.
    """
    state = ModelState(initial_value, name=name)
    state.subscribe(widget)

    handle = ModelStateHandle(state=state, _name=name)

    if name:
        connect_effects(widget, name, state)

    return handle


def use_reducer(
    widget: Widget,
    reducer: Callable[[T, A], T],
    initial_value: T,
    *,
    name: str | None = None,
) -> ReducerHandle[T, A]:
    """
    Create a reducer-based state bound to a widget.

    Args:
        widget: The widget that owns this state.
        reducer: Function (state, action) -> new_state.
        initial_value: The initial state value.
        name: Optional name for @effect decorator matching.

    Returns:
        A ReducerHandle with value property and dispatch method.

    Example:
        ```python
        class Counter(Widget):
            def on_mount(self):
                self.counter = use_reducer(self, counter_reducer, 0, name="counter")

            @effect("counter")
            def on_counter_change(self, old: int, new: int):
                self.query_one("#display").update(f"{new}")
        ```
    """
    state = State(initial_value, name=name)
    state.subscribe(widget)

    def dispatch(action: A) -> None:
        current = state.value
        new_value = reducer(current, action)
        state.set(new_value)

    handle = ReducerHandle(state=state, _dispatch=dispatch, _name=name)

    if name:
        connect_effects(widget, name, state)

    return handle


def use_model_reducer(
    widget: Widget,
    reducer: Callable[[S, A], S],
    initial_value: S,
    *,
    name: str | None = None,
) -> ReducerHandle[S, A]:
    """
    Create a reducer for Pydantic model state.

    Args:
        widget: The widget that owns this state.
        reducer: Function (model, action) -> new_model.
        initial_value: The initial Pydantic model.
        name: Optional name for @effect decorator matching.

    Returns:
        A ReducerHandle for the Pydantic model.
    """
    state = ModelState(initial_value, name=name)
    state.subscribe(widget)

    def dispatch(action: A) -> None:
        current = state.value
        new_value = reducer(current, action)
        state.replace(new_value)

    handle = ReducerHandle(state=state, _dispatch=dispatch, _name=name)

    if name:
        connect_effects(widget, name, state)

    return handle


# Type for source handles
SourceHandle = StateHandle[Any] | ModelStateHandle[Any] | ReducerHandle[Any, Any] | DerivedHandle[Any]


@overload
def use_derived(
    widget: Widget,
    source: SourceHandle,
    selector: Callable[[Any], T],
    *,
    name: str | None = None,
) -> DerivedHandle[T]: ...


@overload
def use_derived(
    widget: Widget,
    sources: list[SourceHandle],
    selector: Callable[..., T],
    *,
    name: str | None = None,
) -> DerivedHandle[T]: ...


def use_derived(
    widget: Widget,
    source: SourceHandle | list[SourceHandle],
    selector: Callable[..., T],
    *,
    name: str | None = None,
) -> DerivedHandle[T]:
    """
    Create a derived (computed) value from one or more sources.

    The derived value is recomputed when any source changes, but only
    triggers effects if the result is different.

    Args:
        widget: The widget that owns this derived state.
        source: Source state handle(s) to derive from.
        selector: Function to compute the derived value.
        name: Optional name for @effect decorator matching.

    Returns:
        A DerivedHandle with the computed value.

    Example:
        ```python
        class TodoList(Widget):
            def on_mount(self):
                self.todos = TodoStore.use(self)

                # Derived values
                self.count = use_derived(
                    self,
                    self.todos,
                    lambda t: len(t.items),
                    name="count"
                )
                self.active = use_derived(
                    self,
                    self.todos,
                    lambda t: [i for i in t.items if not i.completed],
                    name="active"
                )

            @effect("count")
            def on_count_change(self, old: int, new: int):
                self.query_one("#count").update(f"{new} items")
        ```
    """
    # Normalize to list
    sources = source if isinstance(source, list) else [source]

    # Get current values and compute initial
    def get_values() -> list[Any]:
        return [s.value for s in sources]

    initial_values = get_values()
    if len(sources) == 1:
        initial_computed = selector(initial_values[0])
    else:
        initial_computed = selector(*initial_values)

    # Create derived state
    derived_state = State(initial_computed, name=name)
    derived_state.subscribe(widget)

    # Watch each source
    def on_source_change(old: Any, new: Any) -> None:
        values = get_values()
        if len(sources) == 1:
            new_computed = selector(values[0])
        else:
            new_computed = selector(*values)
        derived_state.set(new_computed)

    for src in sources:
        src.state.watch(on_source_change)

    handle = DerivedHandle(state=derived_state, _name=name)

    if name:
        connect_effects(widget, name, derived_state)

    return handle
