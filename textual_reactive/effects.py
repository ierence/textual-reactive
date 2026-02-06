"""Effect decorator for watching state changes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar, Union

if TYPE_CHECKING:
    from .store import Store

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

# Attribute name to store effect metadata on methods
EFFECT_ATTR = "__textual_reactive_effects__"


class EffectRegistration:
    """Stores effect registration info on a method."""

    __slots__ = ("targets",)

    def __init__(self) -> None:
        self.targets: list[str | Store[Any, Any]] = []

    def add(self, target: str | Store[Any, Any]) -> None:
        self.targets.append(target)


def get_effect_registration(method: Callable[..., Any]) -> EffectRegistration | None:
    """Get effect registration from a method, if any."""
    return getattr(method, EFFECT_ATTR, None)


def effect(*targets: str | Store[Any, Any]) -> Callable[[F], F]:
    """
    Decorator to mark a method as an effect that responds to state changes.

    Args:
        *targets: State names (strings) or Store references to watch.

    Example:
        ```python
        class MyWidget(Widget):
            def on_mount(self):
                self.count = use_state(self, 0, name="count")
                self.todos = TodoStore.use(self)

            @effect("count")
            def on_count_change(self, old: int, new: int):
                self.query_one("#display").update(f"Count: {new}")

            @effect(TodoStore)
            def on_todos_change(self, old: TodoState, new: TodoState):
                self.refresh()

            @effect("count", "name")  # multiple targets
            def on_either_change(self, old, new):
                self.save_state()
        ```
    """
    if not targets:
        raise ValueError("@effect requires at least one target")

    def decorator(method: F) -> F:
        # Get or create registration
        registration = get_effect_registration(method)
        if registration is None:
            registration = EffectRegistration()
            setattr(method, EFFECT_ATTR, registration)

        # Add all targets
        for target in targets:
            registration.add(target)

        return method

    return decorator


def connect_effects(widget: Any, state_name: str, state: Any) -> None:
    """
    Connect effects for a named state to a widget.

    Called internally by use_state, use_reducer, etc.

    Args:
        widget: The widget instance.
        state_name: The name of the state.
        state: The State object.
    """
    from .state import State

    if not isinstance(state, State):
        # Get underlying state from handles
        if hasattr(state, "state"):
            state = state.state
        elif hasattr(state, "_state"):
            state = state._state
        else:
            return

    # Find all methods with @effect decorator targeting this state
    # Only look at the widget's own class, not inherited
    for attr_name in dir(type(widget)):
        if attr_name.startswith("_"):
            continue

        try:
            # Get from class first to check for effect decorator
            class_attr = getattr(type(widget), attr_name, None)
            if class_attr is None:
                continue

            registration = get_effect_registration(class_attr)
            if registration is None:
                continue

            # Now get the bound method
            method = getattr(widget, attr_name)
            if not callable(method):
                continue

            # Check if this state is a target
            if state_name in registration.targets:
                # Register the method as a watcher
                state.watch(lambda old, new, m=method: m(old, new))
        except (AttributeError, AssertionError, TypeError):
            continue


def connect_store_effects(widget: Any, store: Store[Any, Any], state: Any) -> None:
    """
    Connect effects for a store to a widget.

    Called internally by Store.use().

    Args:
        widget: The widget instance.
        store: The Store being used.
        state: The State object.
    """
    from .state import State

    if not isinstance(state, State):
        if hasattr(state, "state"):
            state = state.state
        elif hasattr(state, "_state"):
            state = state._state
        else:
            return

    # Find all methods with @effect decorator targeting this store
    for attr_name in dir(type(widget)):
        if attr_name.startswith("_"):
            continue

        try:
            # Get from class first to check for effect decorator
            class_attr = getattr(type(widget), attr_name, None)
            if class_attr is None:
                continue

            registration = get_effect_registration(class_attr)
            if registration is None:
                continue

            # Now get the bound method
            method = getattr(widget, attr_name)
            if not callable(method):
                continue

            # Check if this store is a target
            if store in registration.targets:
                state.watch(lambda old, new, m=method: m(old, new))
        except (AttributeError, AssertionError, TypeError):
            continue
