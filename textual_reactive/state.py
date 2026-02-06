"""Core state management classes for textual-reactive."""

from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar, overload
from weakref import WeakSet

from pydantic import BaseModel
from textual.message import Message
from textual.widget import Widget

T = TypeVar("T")
S = TypeVar("S", bound=BaseModel)


class StateChanged(Message, Generic[T]):
    """Message posted when state changes."""

    def __init__(self, state: State[T], old_value: T, new_value: T) -> None:
        super().__init__()
        self.state = state
        self.old_value = old_value
        self.new_value = new_value


class State(Generic[T]):
    """
    A reactive state container that integrates with Textual's message system.

    State can hold any value type, including Pydantic models. When the state
    changes, it notifies all subscribed widgets via Textual messages.

    Example:
        ```python
        class MyWidget(Widget):
            def __init__(self):
                super().__init__()
                self.count = State(0)
                self.count.subscribe(self)

            def increment(self):
                self.count.set(lambda x: x + 1)

            def on_state_changed(self, event: StateChanged[int]) -> None:
                self.refresh()
        ```
    """

    __slots__ = ("_value", "_subscribers", "_watchers", "_name")

    def __init__(self, initial_value: T, *, name: str | None = None) -> None:
        """
        Initialize a new state container.

        Args:
            initial_value: The initial value of the state.
            name: Optional name for debugging purposes.
        """
        self._value: T = initial_value
        self._subscribers: WeakSet[Widget] = WeakSet()
        self._watchers: list[Callable[[T, T], None]] = []
        self._name = name

    @property
    def value(self) -> T:
        """Get the current state value."""
        return self._value

    @value.setter
    def value(self, new_value: T) -> None:
        """Set the state value directly."""
        self._set_value(new_value)

    def get(self) -> T:
        """Get the current state value."""
        return self._value

    @overload
    def set(self, value: T) -> None: ...

    @overload
    def set(self, value: Callable[[T], T]) -> None: ...

    def set(self, value: T | Callable[[T], T]) -> None:
        """
        Set the state value.

        Args:
            value: Either a new value or a function that takes the current
                   value and returns the new value.
        """
        if callable(value):
            new_value = value(self._value)
        else:
            new_value = value
        self._set_value(new_value)

    def _set_value(self, new_value: T) -> None:
        """Internal method to set value and notify subscribers."""
        old_value = self._value

        # For Pydantic models, compare by dict representation
        if isinstance(old_value, BaseModel) and isinstance(new_value, BaseModel):
            if old_value.model_dump() == new_value.model_dump():
                return
        elif old_value == new_value:
            return

        self._value = new_value

        # Notify watchers
        for watcher in self._watchers:
            watcher(old_value, new_value)

        # Post message to subscribed widgets
        message = StateChanged(self, old_value, new_value)
        for widget in self._subscribers:
            widget.post_message(message)

    def subscribe(self, widget: Widget) -> None:
        """
        Subscribe a widget to state changes.

        The widget will receive StateChanged messages when the state changes.

        Args:
            widget: The widget to subscribe.
        """
        self._subscribers.add(widget)

    def unsubscribe(self, widget: Widget) -> None:
        """
        Unsubscribe a widget from state changes.

        Args:
            widget: The widget to unsubscribe.
        """
        self._subscribers.discard(widget)

    def watch(self, callback: Callable[[T, T], None]) -> Callable[[], None]:
        """
        Add a watcher callback for state changes.

        Args:
            callback: A function that receives (old_value, new_value).

        Returns:
            A function to remove the watcher.
        """
        self._watchers.append(callback)

        def unwatch() -> None:
            self._watchers.remove(callback)

        return unwatch

    def __repr__(self) -> str:
        name = f" name={self._name!r}" if self._name else ""
        return f"State({self._value!r}{name})"


class ModelState(State[S], Generic[S]):
    """
    A state container specifically for Pydantic models with field-level updates.

    This provides convenient methods for updating individual fields of a
    Pydantic model without replacing the entire model.

    Example:
        ```python
        class User(BaseModel):
            name: str
            email: str
            age: int

        user_state = ModelState(User(name="John", email="john@example.com", age=30))
        user_state.update(name="Jane")  # Only updates the name field
        ```
    """

    def __init__(self, initial_value: S, *, name: str | None = None) -> None:
        super().__init__(initial_value, name=name)

    def update(self, **kwargs: Any) -> None:
        """
        Update specific fields of the Pydantic model.

        Args:
            **kwargs: Field names and their new values.
        """
        current = self._value
        new_value = current.model_copy(update=kwargs)
        self._set_value(new_value)

    def replace(self, new_model: S) -> None:
        """
        Replace the entire model.

        Args:
            new_model: The new Pydantic model instance.
        """
        self._set_value(new_model)

    @property
    def model(self) -> S:
        """Get the current model (alias for value)."""
        return self._value
