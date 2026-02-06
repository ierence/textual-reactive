# Textual Reactive

React-like state management for the [Textual](https://textual.textualize.io/) TUI framework, with Pydantic support.

## Features

- **`use_state`** - Simple reactive state (like React's `useState`)
- **`use_reducer`** - Complex state with actions and reducers (like React's `useReducer`)
- **`use_derived`** - Computed values that update automatically (like Svelte's derived stores)
- **`@effect`** - Decorator to watch specific state changes (like React's `useEffect` with dependencies)
- **Context system** - Share state across widget trees without prop drilling
- **Pydantic support** - Full integration with Pydantic models for validated state

## Installation

```bash
pip install textual-reactive
```

Or with uv:

```bash
uv add textual-reactive
```

## Quick Start

```python
from dataclasses import dataclass
from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.widgets import Button, Static

from textual_reactive import (
    create_reducer_context,
    use_reducer,
    use_reducer_context,
    ReducerProvider,
    effect,
)


# 1. Define your state with Pydantic
class CounterState(BaseModel):
    count: int = 0


# 2. Define actions as dataclasses
@dataclass
class Increment:
    pass

@dataclass
class Decrement:
    pass


# 3. Create a reducer function
def counter_reducer(state: CounterState, action) -> CounterState:
    match action:
        case Increment():
            return state.model_copy(update={"count": state.count + 1})
        case Decrement():
            return state.model_copy(update={"count": state.count - 1})
    return state


# 4. Create a context to share the reducer
CounterContext = create_reducer_context("counter")


# 5. Build your widgets
class CounterDisplay(Static):
    def on_mount(self) -> None:
        self.counter = use_reducer_context(self, CounterContext)

    @effect("counter")
    def on_counter_change(self, old: CounterState, new: CounterState) -> None:
        self.update(f"Count: {new.count}")


class CounterApp(App):
    def compose(self) -> ComposeResult:
        # Create reducer at the top level
        self.counter = use_reducer(self, counter_reducer, CounterState(), name="counter")

        # Provide to children
        yield ReducerProvider(CounterContext, self.counter,
            CounterDisplay(),
            Button("+ Increment", id="inc"),
            Button("- Decrement", id="dec"),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "inc":
                self.counter.dispatch(Increment())
            case "dec":
                self.counter.dispatch(Decrement())


if __name__ == "__main__":
    CounterApp().run()
```

## API Reference

### State Hooks

#### `use_state(widget, initial_value, *, name=None)`

Create simple reactive state bound to a widget.

```python
class MyWidget(Widget):
    def on_mount(self):
        self.count = use_state(self, 0, name="count")

    def increment(self):
        self.count.set(lambda x: x + 1)
        # or: self.count.set(5)
```

#### `use_reducer(widget, reducer, initial_value, *, name=None)`

Create reducer-based state for complex state logic.

```python
def reducer(state, action):
    match action:
        case Increment():
            return state + 1
    return state

class MyWidget(Widget):
    def on_mount(self):
        self.counter = use_reducer(self, reducer, 0, name="counter")

    def increment(self):
        self.counter.dispatch(Increment())
```

#### `use_derived(widget, source, selector, *, name=None)`

Create computed values that update when the source changes.

```python
class TodoList(Widget):
    def on_mount(self):
        self.todos = use_reducer_context(self, TodoContext)

        # Derived values
        self.total = use_derived(self, self.todos, lambda t: len(t.items), name="total")
        self.completed = use_derived(
            self,
            self.todos,
            lambda t: len([i for i in t.items if i.done]),
            name="completed"
        )

    @effect("total")
    def on_total_change(self, old: int, new: int):
        self.query_one("#total").update(f"Total: {new}")
```

### Context System

#### `create_reducer_context(name=None)`

Create a context for sharing a reducer across the widget tree.

```python
# In a shared module (e.g., contexts.py)
TodoContext = create_reducer_context("todos")
```

#### `ReducerProvider`

Provide a reducer to descendant widgets.

```python
class App(App):
    def compose(self):
        self.todos = use_reducer(self, todo_reducer, TodoState(), name="todos")

        yield ReducerProvider(TodoContext, self.todos,
            Header(),
            TodoList(),
            Footer(),
        )
```

#### `use_reducer_context(widget, context, *, subscribe=True)`

Consume a reducer from context in a child widget.

```python
class TodoList(Widget):
    def on_mount(self):
        self.todos = use_reducer_context(self, TodoContext)
        # self.todos.value -> current state
        # self.todos.dispatch(action) -> dispatch action
```

### Effects

#### `@effect(*targets)`

Decorator to run a method when specific state changes.

```python
class MyWidget(Widget):
    def on_mount(self):
        self.count = use_state(self, 0, name="count")
        self.name = use_state(self, "", name="name")

    @effect("count")
    def on_count_change(self, old: int, new: int):
        self.refresh()

    @effect("count", "name")  # multiple targets
    def on_any_change(self, old, new):
        self.save()
```

### Store Pattern (Alternative)

For simpler cases, use `create_store` which combines reducer and context:

```python
from textual_reactive import create_store, effect

# Create store
TodoStore = create_store(todo_reducer, TodoState(), name="todos")

class App(App):
    def compose(self):
        yield TodoStore.provider(
            TodoList(),
        )

class TodoList(Widget):
    def on_mount(self):
        self.todos = TodoStore.use(self)

    @effect(TodoStore)  # Can use store as effect target
    def on_change(self, old, new):
        self.refresh()
```

### Pydantic Models

All hooks work seamlessly with Pydantic models:

```python
class UserState(BaseModel):
    name: str = ""
    email: str = ""
    preferences: dict = {}

class MyWidget(Widget):
    def on_mount(self):
        self.user = use_model_state(self, UserState(), name="user")

    def update_name(self, name: str):
        # Update single field
        self.user.update(name=name)

    def update_all(self, user: UserState):
        # Replace entire model
        self.user.set(user)
```

## Comparison with React

| React | Textual Reactive |
|-------|------------------|
| `useState` | `use_state` |
| `useReducer` | `use_reducer` |
| `useContext` | `use_reducer_context` / `use_context` |
| `useEffect` with deps | `@effect("dep1", "dep2")` |
| `useMemo` | `use_derived` |
| `createContext` | `create_reducer_context` / `create_context` |
| `<Context.Provider>` | `ReducerProvider` / `ContextProvider` |

## Examples

See the `examples/` directory for complete working examples:

- `examples/new_counter.py` - Simple counter with reducer
- `examples/new_todo_app.py` - Todo app with derived state
- `examples/context.py` - Context sharing example

## License

MIT
