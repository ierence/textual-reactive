"""Tests for state management."""

import pytest
from pydantic import BaseModel

from textual_reactive import State, ModelState, StateChanged


class User(BaseModel):
    """Test model."""
    name: str
    age: int


class TestState:
    """Tests for State class."""

    def test_initial_value(self):
        state = State(42)
        assert state.value == 42
        assert state.get() == 42

    def test_set_value(self):
        state = State(0)
        state.set(10)
        assert state.value == 10

    def test_set_with_function(self):
        state = State(5)
        state.set(lambda x: x * 2)
        assert state.value == 10

    def test_value_setter(self):
        state = State(0)
        state.value = 100
        assert state.value == 100

    def test_no_update_if_same_value(self):
        changes = []
        state = State(5)
        state.watch(lambda old, new: changes.append((old, new)))

        state.set(5)  # Same value
        assert len(changes) == 0

        state.set(10)  # Different value
        assert len(changes) == 1
        assert changes[0] == (5, 10)

    def test_watch_callback(self):
        changes = []
        state = State(0)

        unwatch = state.watch(lambda old, new: changes.append((old, new)))

        state.set(1)
        state.set(2)

        assert changes == [(0, 1), (1, 2)]

        unwatch()
        state.set(3)

        assert len(changes) == 2  # No new changes after unwatch

    def test_repr(self):
        state = State(42, name="counter")
        assert "42" in repr(state)
        assert "counter" in repr(state)


class TestModelState:
    """Tests for ModelState class."""

    def test_initial_model(self):
        user = User(name="Alice", age=30)
        state = ModelState(user)

        assert state.value == user
        assert state.model == user

    def test_update_field(self):
        state = ModelState(User(name="Alice", age=30))
        state.update(age=31)

        assert state.value.name == "Alice"
        assert state.value.age == 31

    def test_update_multiple_fields(self):
        state = ModelState(User(name="Alice", age=30))
        state.update(name="Bob", age=25)

        assert state.value.name == "Bob"
        assert state.value.age == 25

    def test_replace_model(self):
        state = ModelState(User(name="Alice", age=30))
        new_user = User(name="Charlie", age=40)
        state.replace(new_user)

        assert state.value == new_user

    def test_no_update_if_same_model(self):
        changes = []
        user = User(name="Alice", age=30)
        state = ModelState(user)
        state.watch(lambda old, new: changes.append((old, new)))

        # Same values, should not trigger
        state.update(name="Alice", age=30)
        assert len(changes) == 0

        # Different value, should trigger
        state.update(age=31)
        assert len(changes) == 1
