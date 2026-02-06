"""Tests for hooks (use_state, use_reducer)."""

import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from textual_reactive import use_state, use_reducer, use_model_state, use_model_reducer
from textual_reactive.hooks import StateHandle, ModelStateHandle, ReducerHandle


class Counter(BaseModel):
    """Test model for reducer."""
    count: int = 0


@dataclass
class Increment:
    amount: int = 1


@dataclass
class Decrement:
    amount: int = 1


@dataclass
class Reset:
    pass


Action = Increment | Decrement | Reset


def counter_reducer(state: int, action: Action) -> int:
    match action:
        case Increment(amount):
            return state + amount
        case Decrement(amount):
            return state - amount
        case Reset():
            return 0
    return state


def model_counter_reducer(state: Counter, action: Action) -> Counter:
    match action:
        case Increment(amount):
            return state.model_copy(update={"count": state.count + amount})
        case Decrement(amount):
            return state.model_copy(update={"count": state.count - amount})
        case Reset():
            return Counter()
    return state


class TestUseState:
    """Tests for use_state hook."""

    def test_creates_state_handle(self):
        mock_widget = MagicMock()
        handle = use_state(mock_widget, 0)

        assert isinstance(handle, StateHandle)
        assert handle.value == 0

    def test_subscribes_widget(self):
        mock_widget = MagicMock()
        handle = use_state(mock_widget, 42)

        # Check that the widget was subscribed
        assert mock_widget in handle.state._subscribers

    def test_set_updates_value(self):
        mock_widget = MagicMock()
        handle = use_state(mock_widget, 10)

        handle.set(20)
        assert handle.value == 20

    def test_set_with_function(self):
        mock_widget = MagicMock()
        handle = use_state(mock_widget, 5)

        handle.set(lambda x: x * 3)
        assert handle.value == 15

    def test_callable_returns_value(self):
        mock_widget = MagicMock()
        handle = use_state(mock_widget, 42)

        assert handle() == 42


class TestUseModelState:
    """Tests for use_model_state hook."""

    def test_creates_model_state_handle(self):
        mock_widget = MagicMock()
        handle = use_model_state(mock_widget, Counter(count=5))

        assert isinstance(handle, ModelStateHandle)
        assert handle.value.count == 5

    def test_update_field(self):
        mock_widget = MagicMock()
        handle = use_model_state(mock_widget, Counter(count=0))

        handle.update(count=10)
        assert handle.value.count == 10


class TestUseReducer:
    """Tests for use_reducer hook."""

    def test_creates_reducer_handle(self):
        mock_widget = MagicMock()
        handle = use_reducer(mock_widget, counter_reducer, 0)

        assert isinstance(handle, ReducerHandle)
        assert handle.value == 0

    def test_dispatch_increment(self):
        mock_widget = MagicMock()
        handle = use_reducer(mock_widget, counter_reducer, 0)

        handle.dispatch(Increment(5))
        assert handle.value == 5

    def test_dispatch_decrement(self):
        mock_widget = MagicMock()
        handle = use_reducer(mock_widget, counter_reducer, 10)

        handle.dispatch(Decrement(3))
        assert handle.value == 7

    def test_dispatch_reset(self):
        mock_widget = MagicMock()
        handle = use_reducer(mock_widget, counter_reducer, 100)

        handle.dispatch(Reset())
        assert handle.value == 0

    def test_multiple_dispatches(self):
        mock_widget = MagicMock()
        handle = use_reducer(mock_widget, counter_reducer, 0)

        handle.dispatch(Increment(5))
        handle.dispatch(Increment(3))
        handle.dispatch(Decrement(2))

        assert handle.value == 6


class TestUseModelReducer:
    """Tests for use_model_reducer hook."""

    def test_works_with_pydantic_models(self):
        mock_widget = MagicMock()
        handle = use_model_reducer(mock_widget, model_counter_reducer, Counter())

        handle.dispatch(Increment(10))
        assert handle.value.count == 10

        handle.dispatch(Decrement(3))
        assert handle.value.count == 7

        handle.dispatch(Reset())
        assert handle.value.count == 0
