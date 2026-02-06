"""Type definitions for textual-reactive."""

from typing import Any, Callable, Generic, TypeVar, Protocol
from pydantic import BaseModel

# Type variables
T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
S = TypeVar("S", bound=BaseModel)
A = TypeVar("A")  # Action type


class Action(Protocol[T_co]):
    """Protocol for reducer actions."""

    @property
    def type(self) -> str:
        """Action type identifier."""
        ...


class Reducer(Protocol[T, A]):
    """Protocol for reducer functions."""

    def __call__(self, state: T, action: A) -> T:
        """Process an action and return new state."""
        ...


class StateCallback(Protocol[T]):
    """Protocol for state change callbacks."""

    def __call__(self, old_value: T, new_value: T) -> None:
        """Called when state changes."""
        ...


class SetterFunc(Protocol[T]):
    """Protocol for state setter functions."""

    def __call__(self, value: T | Callable[[T], T]) -> None:
        """Set state to a value or use a function to compute new value."""
        ...


class DispatchFunc(Protocol[A]):
    """Protocol for dispatch functions."""

    def __call__(self, action: A) -> None:
        """Dispatch an action to the reducer."""
        ...
