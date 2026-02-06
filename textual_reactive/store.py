"""Store - combines reducer, initial state, and context into one object."""

from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar
from weakref import WeakValueDictionary

from pydantic import BaseModel
from textual.widget import Widget
from textual.containers import Container

from .state import State, ModelState
from .effects import connect_store_effects

T = TypeVar("T")
S = TypeVar("S", bound=BaseModel)
A = TypeVar("A")


class StoreHandle(Generic[T, A]):
    """
    Handle returned by Store.use() - provides access to state and dispatch.

    Works with use_derived and @effect.
    """

    __slots__ = ("_state", "_dispatch", "_store")

    def __init__(
        self,
        state: State[T],
        dispatch: Callable[[A], None],
        store: Store[T, A],
    ) -> None:
        self._state = state
        self._dispatch = dispatch
        self._store = store

    @property
    def value(self) -> T:
        """Get the current state value."""
        return self._state.value

    def dispatch(self, action: A) -> None:
        """Dispatch an action to the reducer."""
        self._dispatch(action)

    @property
    def state(self) -> State[T]:
        """Get the underlying state (for use_derived and advanced use)."""
        return self._state

    @property
    def store(self) -> Store[T, A]:
        """Get the store this handle belongs to."""
        return self._store

    def __call__(self) -> T:
        """Shorthand to get current value."""
        return self._state.value


class StoreProvider(Container, Generic[T, A]):
    """Widget that provides a store to its descendants."""

    DEFAULT_CSS = """
    StoreProvider {
        width: 100%;
        height: auto;
    }
    """

    def __init__(
        self,
        store: Store[T, A],
        *children: Widget,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        self._store = store
        self._compose_children = children

        # Create the state and dispatch for this provider
        if isinstance(store._initial, BaseModel):
            self._state: State[T] = ModelState(store._initial, name=store._name)
        else:
            self._state = State(store._initial, name=store._name)

        def dispatch(action: A) -> None:
            current = self._state.value
            new_value = store._reducer(current, action)
            self._state.set(new_value)

        self._dispatch = dispatch

    @property
    def state(self) -> State[T]:
        """Get the state."""
        return self._state

    @property
    def value(self) -> T:
        """Get current state value."""
        return self._state.value

    def dispatch(self, action: A) -> None:
        """Dispatch an action."""
        self._dispatch(action)

    def compose(self):
        yield from self._compose_children

    def on_mount(self) -> None:
        """Register this provider."""
        self._store._providers[id(self)] = self


class Store(Generic[T, A]):
    """
    A store combining reducer, initial state, and context.

    Usage:
        ```python
        # Define the store
        TodoStore = create_store(todo_reducer, TodoState())

        # Provide it
        class App(App):
            def compose(self):
                yield TodoStore.provider(
                    Header(),
                    TodoList(),
                )

        # Consume it
        class TodoList(Widget):
            def on_mount(self):
                self.todos = TodoStore.use(self)
                # self.todos.value -> current state
                # self.todos.dispatch(action) -> dispatch
        ```
    """

    __slots__ = ("_reducer", "_initial", "_name", "_providers")

    def __init__(
        self,
        reducer: Callable[[T, A], T],
        initial: T,
        *,
        name: str | None = None,
    ) -> None:
        self._reducer = reducer
        self._initial = initial
        self._name = name
        self._providers: WeakValueDictionary[int, StoreProvider[T, A]] = (
            WeakValueDictionary()
        )

    @property
    def name(self) -> str | None:
        """Get store name."""
        return self._name

    def provider(
        self,
        *children: Widget,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> StoreProvider[T, A]:
        """
        Create a provider widget for this store.

        Args:
            *children: Child widgets.
            name: Widget name.
            id: Widget ID.
            classes: CSS classes.

        Returns:
            A StoreProvider widget.
        """
        return StoreProvider(self, *children, name=name, id=id, classes=classes)

    def use(self, widget: Widget, *, subscribe: bool = True) -> StoreHandle[T, A]:
        """
        Consume this store from a widget.

        Finds the nearest provider in the widget tree and returns a handle
        to access state and dispatch actions.

        Args:
            widget: The widget consuming the store.
            subscribe: Whether to subscribe to changes (default True).

        Returns:
            A StoreHandle with .value and .dispatch().

        Raises:
            RuntimeError: If no provider is found in the widget tree.
        """
        provider = self._find_provider(widget)

        if provider is None:
            raise RuntimeError(
                f"Store '{self._name or 'unnamed'}' not found in widget tree. "
                f"Make sure a provider is mounted above {widget.__class__.__name__}."
            )

        if subscribe:
            provider._state.subscribe(widget)

        # Connect @effect decorated methods for this store
        connect_store_effects(widget, self, provider._state)

        return StoreHandle(provider._state, provider._dispatch, self)

    def _find_provider(self, widget: Widget) -> StoreProvider[T, A] | None:
        """Find the nearest provider for this store."""
        current: Widget | None = widget

        while current is not None:
            if isinstance(current, StoreProvider) and current._store is self:
                return current

            if hasattr(current, "parent") and current.parent is not None:
                current = current.parent
            else:
                break

        return None


def create_store(
    reducer: Callable[[T, A], T],
    initial: T,
    *,
    name: str | None = None,
) -> Store[T, A]:
    """
    Create a new store.

    Args:
        reducer: Function (state, action) -> new_state.
        initial: Initial state value.
        name: Optional name for debugging.

    Returns:
        A Store instance.

    Example:
        ```python
        from dataclasses import dataclass
        from pydantic import BaseModel

        class TodoState(BaseModel):
            items: list[str] = []

        @dataclass
        class AddItem:
            text: str

        def reducer(state: TodoState, action) -> TodoState:
            match action:
                case AddItem(text):
                    return state.model_copy(update={
                        "items": [*state.items, text]
                    })
            return state

        TodoStore = create_store(reducer, TodoState())
        ```
    """
    return Store(reducer, initial, name=name)
