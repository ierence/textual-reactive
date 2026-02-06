"""Specialized context for reducers - no double wrapping."""

from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar
from weakref import WeakValueDictionary

from pydantic import BaseModel
from textual.widget import Widget
from textual.containers import Container

from .state import State
from .hooks import ReducerHandle
from .effects import connect_store_effects

T = TypeVar("T")
A = TypeVar("A")


class ReducerContext(Generic[T, A]):
    """
    A context specifically for sharing reducers.

    Unlike generic Context, this doesn't wrap the value - it expects
    a ReducerHandle and passes it through directly.
    """

    __slots__ = ("_name", "_providers")

    def __init__(self, name: str | None = None) -> None:
        self._name = name
        self._providers: WeakValueDictionary[int, ReducerProvider[T, A]] = (
            WeakValueDictionary()
        )

    @property
    def name(self) -> str | None:
        return self._name


def create_reducer_context(name: str | None = None) -> ReducerContext[Any, Any]:
    """
    Create a context for sharing a reducer.

    Example:
        ```python
        TodoContext = create_reducer_context("todos")
        ```
    """
    return ReducerContext(name=name)


class ReducerProvider(Container, Generic[T, A]):
    """
    Provider for reducer state - passes ReducerHandle through without wrapping.

    Example:
        ```python
        TodoContext = create_reducer_context("todos")

        class App(App):
            def compose(self):
                self.todos = use_reducer(self, todo_reducer, TodoState())

                yield ReducerProvider(TodoContext, self.todos,
                    Header(),
                    TodoList(),
                )

            def on_mount(self):
                # Can use directly
                self.todos.dispatch(AddTodo("Initial"))
        ```
    """

    DEFAULT_CSS = """
    ReducerProvider {
        width: 100%;
        height: 100%;
    }
    """

    def __init__(
        self,
        reactive_context: ReducerContext[T, A],
        reducer_handle: ReducerHandle[T, A],
        *children: Widget,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._rx_context = reactive_context
        self._reducer_handle = reducer_handle
        self._compose_children = children

    @property
    def handle(self) -> ReducerHandle[T, A]:
        """Get the reducer handle."""
        return self._reducer_handle

    @property
    def value(self) -> T:
        """Get current state value."""
        return self._reducer_handle.value

    def dispatch(self, action: A) -> None:
        """Dispatch an action."""
        self._reducer_handle.dispatch(action)

    def compose(self):
        yield from self._compose_children

    def on_mount(self) -> None:
        self._rx_context._providers[id(self)] = self


def use_reducer_context(
    widget: Widget,
    context: ReducerContext[T, A],
    *,
    subscribe: bool = True,
) -> ReducerHandle[T, A]:
    """
    Consume a reducer from context.

    Returns the ReducerHandle directly - no wrapping.

    Example:
        ```python
        class TodoList(Widget):
            def on_mount(self):
                self.todos = use_reducer_context(self, TodoContext)
                # self.todos.value -> state
                # self.todos.dispatch(action)
        ```
    """
    provider = _find_provider(widget, context)

    if provider is None:
        raise RuntimeError(
            f"ReducerContext '{context._name or 'unnamed'}' not found. "
            f"Make sure a ReducerProvider is mounted above {widget.__class__.__name__}."
        )

    handle = provider._reducer_handle

    if subscribe:
        handle.state.subscribe(widget)

    # Connect @effect decorated methods
    from .effects import connect_effects
    if handle.name:
        connect_effects(widget, handle.name, handle.state)

    return handle


def _find_provider(
    widget: Widget, context: ReducerContext[T, A]
) -> ReducerProvider[T, A] | None:
    """Find the nearest provider for this context."""
    current: Widget | None = widget

    while current is not None:
        if isinstance(current, ReducerProvider) and current._rx_context is context:
            return current

        if hasattr(current, "parent") and current.parent is not None:
            current = current.parent
        else:
            break

    return None
