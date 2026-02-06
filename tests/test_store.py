"""Tests for Store and @effect."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from textual_reactive import create_store, effect
from textual_reactive.store import Store, StoreHandle


class BaseMockWidget:
    """Base mock widget with post_message."""

    def post_message(self, message):
        pass


class CounterState(BaseModel):
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


def counter_reducer(state: CounterState, action: Action) -> CounterState:
    match action:
        case Increment(amount):
            return state.model_copy(update={"count": state.count + amount})
        case Decrement(amount):
            return state.model_copy(update={"count": state.count - amount})
        case Reset():
            return CounterState()
    return state


class TestCreateStore:
    """Tests for create_store."""

    def test_creates_store(self):
        store = create_store(counter_reducer, CounterState())

        assert isinstance(store, Store)
        assert store._reducer is counter_reducer
        assert store._initial == CounterState()

    def test_store_with_name(self):
        store = create_store(counter_reducer, CounterState(), name="counter")

        assert store.name == "counter"


class TestEffect:
    """Tests for @effect decorator."""

    def test_marks_method(self):
        class Widget:
            @effect("count")
            def on_count_change(self, old, new):
                pass

        from textual_reactive.effects import get_effect_registration

        reg = get_effect_registration(Widget.on_count_change)
        assert reg is not None
        assert "count" in reg.targets

    def test_multiple_targets(self):
        class Widget:
            @effect("count", "name")
            def on_change(self, old, new):
                pass

        from textual_reactive.effects import get_effect_registration

        reg = get_effect_registration(Widget.on_change)
        assert "count" in reg.targets
        assert "name" in reg.targets

    def test_effect_with_store(self):
        store = create_store(counter_reducer, CounterState())

        class Widget:
            @effect(store)
            def on_store_change(self, old, new):
                pass

        from textual_reactive.effects import get_effect_registration

        reg = get_effect_registration(Widget.on_store_change)
        assert store in reg.targets

    def test_effect_requires_target(self):
        with pytest.raises(ValueError, match="requires at least one target"):

            @effect()
            def no_target(self, old, new):
                pass


class TestEffectConnection:
    """Tests for effect connection to state."""

    def test_connects_named_state(self):
        from textual_reactive import use_state

        changes = []

        class MockWidget(BaseMockWidget):
            @effect("count")
            def on_count_change(self, old: int, new: int):
                changes.append((old, new))

        widget = MockWidget()
        count = use_state(widget, 0, name="count")

        # Effect should be connected
        count.set(5)
        assert changes == [(0, 5)]

        count.set(10)
        assert changes == [(0, 5), (5, 10)]

    def test_effect_not_connected_without_name(self):
        from textual_reactive import use_state

        changes = []

        class MockWidget(BaseMockWidget):
            @effect("count")
            def on_count_change(self, old: int, new: int):
                changes.append((old, new))

        widget = MockWidget()
        # No name = no effect connection
        count = use_state(widget, 0)

        count.set(5)
        assert changes == []  # Effect not triggered


class TestUseDerived:
    """Tests for use_derived."""

    def test_computes_initial_value(self):
        from textual_reactive import use_state, use_derived

        widget = MagicMock()
        count = use_state(widget, 10, name="count")
        doubled = use_derived(widget, count, lambda x: x * 2, name="doubled")

        assert doubled.value == 20

    def test_updates_when_source_changes(self):
        from textual_reactive import use_state, use_derived

        widget = MagicMock()
        count = use_state(widget, 5, name="count")
        doubled = use_derived(widget, count, lambda x: x * 2, name="doubled")

        assert doubled.value == 10

        count.set(7)
        assert doubled.value == 14

    def test_multiple_sources(self):
        from textual_reactive import use_state, use_derived

        widget = MagicMock()
        a = use_state(widget, 3, name="a")
        b = use_state(widget, 4, name="b")

        sum_ab = use_derived(widget, [a, b], lambda x, y: x + y, name="sum")

        assert sum_ab.value == 7

        a.set(10)
        assert sum_ab.value == 14

        b.set(20)
        assert sum_ab.value == 30

    def test_derived_with_effect(self):
        from textual_reactive import use_state, use_derived

        changes = []

        class MockWidget(BaseMockWidget):
            @effect("doubled")
            def on_doubled_change(self, old: int, new: int):
                changes.append((old, new))

        widget = MockWidget()
        count = use_state(widget, 5, name="count")
        use_derived(widget, count, lambda x: x * 2, name="doubled")

        count.set(10)
        assert changes == [(10, 20)]

    def test_derived_only_triggers_on_different_value(self):
        from textual_reactive import use_state, use_derived

        changes = []

        class MockWidget(BaseMockWidget):
            @effect("is_positive")
            def on_change(self, old, new):
                changes.append((old, new))

        widget = MockWidget()
        count = use_state(widget, 5, name="count")
        use_derived(widget, count, lambda x: x > 0, name="is_positive")

        # Change count but is_positive stays True
        count.set(10)  # Still positive
        count.set(3)   # Still positive

        # Only when it actually changes
        count.set(-1)  # Now negative
        assert changes == [(True, False)]
