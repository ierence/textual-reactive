"""React-like Context system for sharing state across widget trees."""

from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar, overload
from weakref import WeakValueDictionary

from pydantic import BaseModel
from textual.widget import Widget
from textual.containers import Container
from textual.app import App

from .state import ModelState, State, StateChanged

T = TypeVar("T")
S = TypeVar("S", bound=BaseModel)


class ContextNotFoundError(Exception):
    """Raised when a context is not found in the widget tree."""

    def __init__(self, context: Context[Any], widget: Widget) -> None:
        self.context = context
        self.widget = widget
        name = context.name or "unnamed"
        super().__init__(
            f"Context '{name}' not found in widget tree for {widget.__class__.__name__}. "
            f"Make sure a ContextProvider is mounted above this widget."
        )


class Context(Generic[T]):
    """
    A context for sharing state across widget trees.

    Contexts allow you to share state with deeply nested widgets without
    explicitly passing props through every level of the tree.

    Example:
        ```python
        # Create a context with a default value
        ThemeContext = create_context("light")

        # In a parent widget, provide the context value
        class App(Widget):
            def compose(self):
                with ContextProvider(ThemeContext, "dark"):
                    yield ChildWidget()

        # In any descendant, consume the context
        class ChildWidget(Widget):
            def on_mount(self):
                theme = use_context(self, ThemeContext)
                # theme.value == "dark"
        ```
    """

    __slots__ = ("_default_value", "_name", "_providers")

    def __init__(self, default_value: T, *, name: str | None = None) -> None:
        """
        Create a new context.

        Args:
            default_value: Default value when no provider is found.
            name: Optional name for debugging.
        """
        self._default_value = default_value
        self._name = name
        # Map from app/screen ID to provider
        self._providers: WeakValueDictionary[int, ContextProvider[T]] = (
            WeakValueDictionary()
        )

    @property
    def name(self) -> str | None:
        """Get the context name."""
        return self._name

    @property
    def default_value(self) -> T:
        """Get the default value."""
        return self._default_value


class ModelContext(Context[S], Generic[S]):
    """
    A context specifically for Pydantic models.

    Provides the same functionality as Context but ensures the value
    is a Pydantic model with field-level update support.
    """

    pass


def create_context(default_value: T, *, name: str | None = None) -> Context[T]:
    """
    Create a new context.

    Args:
        default_value: Default value when no provider is found.
        name: Optional name for debugging.

    Returns:
        A new Context instance.

    Example:
        ```python
        # For primitive values
        CounterContext = create_context(0, name="counter")

        # For complex objects
        UserContext = create_context(None, name="user")
        ```
    """
    return Context(default_value, name=name)


def create_model_context(
    default_value: S, *, name: str | None = None
) -> ModelContext[S]:
    """
    Create a context for a Pydantic model.

    Args:
        default_value: Default Pydantic model.
        name: Optional name for debugging.

    Returns:
        A new ModelContext instance.

    Example:
        ```python
        class Theme(BaseModel):
            primary: str = "#007bff"
            background: str = "#ffffff"

        ThemeContext = create_model_context(Theme(), name="theme")
        ```
    """
    return ModelContext(default_value, name=name)


class ContextProvider(Container, Generic[T]):
    """
    A widget that provides a context value to its descendants.

    Example:
        ```python
        ThemeContext = create_context("light")

        class MyApp(App):
            def compose(self):
                yield ContextProvider(
                    ThemeContext,
                    "dark",
                    id="theme-provider",
                    children=[
                        Header(),
                        MainContent(),
                        Footer(),
                    ]
                )
        ```
    """

    DEFAULT_CSS = """
    ContextProvider {
        width: 100%;
        height: auto;
    }
    """

    def __init__(
        self,
        reactive_context: Context[T],
        value: T,
        *children: Widget,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """
        Create a context provider.

        Args:
            reactive_context: The context to provide.
            value: The value to provide.
            *children: Child widgets.
            name: Widget name.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._rx_context = reactive_context
        self._state = State(value, name=context.name)
        self._compose_children = children

    @property
    def provided_value(self) -> T:
        """Get the current provided value."""
        return self._state.value

    @provided_value.setter
    def provided_value(self, value: T) -> None:
        """Set the provided value."""
        self._state.set(value)

    @property
    def state(self) -> State[T]:
        """Get the underlying state object."""
        return self._state

    @property
    def context(self) -> Context[T]:
        """Get the context being provided."""
        return self._rx_context

    def compose(self):
        """Compose child widgets."""
        yield from self._compose_children

    def on_mount(self) -> None:
        """Register this provider when mounted."""
        self._rx_context._providers[id(self)] = self


class ContextHandle(Generic[T]):
    """
    A handle to a consumed context value.

    Provides access to the context value and allows subscribing to changes.
    """

    __slots__ = ("_state", "_widget", "_context", "_is_default")

    def __init__(
        self,
        state: State[T],
        widget: Widget,
        context: Context[T],
        is_default: bool = False,
    ) -> None:
        self._state = state
        self._widget = widget
        self._rx_context = context
        self._is_default = is_default

    @property
    def value(self) -> T:
        """Get the current context value."""
        return self._state.value

    @property
    def is_default(self) -> bool:
        """Check if this is using the default value (no provider found)."""
        return self._is_default

    def set(self, value: T | Callable[[T], T]) -> None:
        """
        Update the context value.

        This updates the value at the provider level, affecting all
        consumers of this context.

        Args:
            value: New value or function (current -> new).
        """
        self._state.set(value)

    def __call__(self) -> T:
        """Shorthand to get the current value."""
        return self._state.value


class ModelContextHandle(ContextHandle[S], Generic[S]):
    """
    A handle to a consumed Pydantic model context.

    Provides field-level updates in addition to full value updates.
    """

    def update(self, **kwargs: Any) -> None:
        """
        Update specific fields of the model.

        Args:
            **kwargs: Field names and new values.
        """
        current = self._state.value
        new_value = current.model_copy(update=kwargs)
        self._state.set(new_value)


def _find_provider(widget: Widget, context: Context[T]) -> ContextProvider[T] | None:
    """Find the nearest provider for a context in the widget tree."""
    current: Widget | None = widget

    while current is not None:
        if isinstance(current, ContextProvider) and current._rx_context is context:
            return current

        # Move up the tree
        if hasattr(current, "parent") and current.parent is not None:
            current = current.parent
        else:
            break

    return None


@overload
def use_context(
    widget: Widget,
    context: ModelContext[S],
    *,
    subscribe: bool = True,
    required: bool = False,
) -> ModelContextHandle[S]: ...


@overload
def use_context(
    widget: Widget,
    context: Context[T],
    *,
    subscribe: bool = True,
    required: bool = False,
) -> ContextHandle[T]: ...


def use_context(
    widget: Widget,
    context: Context[T] | ModelContext[S],
    *,
    subscribe: bool = True,
    required: bool = False,
) -> ContextHandle[T] | ModelContextHandle[S]:
    """
    Consume a context value from the nearest provider.

    Traverses up the widget tree to find the nearest ContextProvider
    for the given context. If none is found, returns the default value.

    Args:
        widget: The widget consuming the context.
        context: The context to consume.
        subscribe: Whether to subscribe to value changes (default True).
        required: If True, raise ContextNotFoundError when no provider found.

    Returns:
        A ContextHandle (or ModelContextHandle for ModelContext).

    Raises:
        ContextNotFoundError: If required=True and no provider is found.

    Example:
        ```python
        class MyWidget(Widget):
            def on_mount(self):
                self.theme = use_context(self, ThemeContext)
                # self.theme.value contains the current theme

            def on_state_changed(self, event: StateChanged) -> None:
                # Called when context value changes
                self.refresh()
        ```
    """
    provider = _find_provider(widget, context)

    if provider is not None:
        state = provider._state
        is_default = False
    else:
        if required:
            raise ContextNotFoundError(context, widget)
        # Create a local state with the default value
        state = State(context.default_value, name=context.name)
        is_default = True

    if subscribe:
        state.subscribe(widget)

    if isinstance(context, ModelContext):
        return ModelContextHandle(state, widget, context, is_default)
    return ContextHandle(state, widget, context, is_default)


def provide_context(
    reactive_context: Context[T],
    value: T,
    *children: Widget,
    **kwargs: Any,
) -> ContextProvider[T]:
    """
    Convenience function to create a ContextProvider.

    Args:
        reactive_context: The context to provide.
        value: The value to provide.
        *children: Child widgets.
        **kwargs: Additional widget arguments (name, id, classes).

    Returns:
        A ContextProvider widget.

    Example:
        ```python
        def compose(self):
            yield provide_context(
                ThemeContext,
                "dark",
                Header(),
                Content(),
                Footer(),
            )
        ```
    """
    return ContextProvider(reactive_context, value, *children, **kwargs)
