"""
Todo App - Clean example of the new Store API.

Demonstrates:
- create_store: Shared state with reducer
- Store.provider() / Store.use(): Provider/consumer pattern
- @effect: React to state changes
- use_derived: Computed values
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, Static

from textual_reactive import create_store, effect, use_derived


# --- Models ---


class TodoItem(BaseModel):
    id: int
    text: str
    completed: bool = False


class TodoState(BaseModel):
    items: list[TodoItem] = []
    next_id: int = 1
    filter: Literal["all", "active", "completed"] = "all"


# --- Actions ---


@dataclass
class AddTodo:
    text: str


@dataclass
class ToggleTodo:
    id: int


@dataclass
class DeleteTodo:
    id: int


@dataclass
class SetFilter:
    filter: Literal["all", "active", "completed"]


@dataclass
class ClearCompleted:
    pass


# --- Reducer ---


def todo_reducer(state: TodoState, action) -> TodoState:
    match action:
        case AddTodo(text) if text.strip():
            new_item = TodoItem(id=state.next_id, text=text.strip())
            return state.model_copy(update={
                "items": [*state.items, new_item],
                "next_id": state.next_id + 1,
            })

        case ToggleTodo(id):
            items = [
                item.model_copy(update={"completed": not item.completed})
                if item.id == id else item
                for item in state.items
            ]
            return state.model_copy(update={"items": items})

        case DeleteTodo(id):
            items = [item for item in state.items if item.id != id]
            return state.model_copy(update={"items": items})

        case SetFilter(filter):
            return state.model_copy(update={"filter": filter})

        case ClearCompleted():
            items = [item for item in state.items if not item.completed]
            return state.model_copy(update={"items": items})

    return state


# --- Store (defined once, imported where needed) ---

TodoStore = create_store(todo_reducer, TodoState(), name="todos")


# --- Components ---


class TodoInput(Static):
    """Input for adding new todos."""

    DEFAULT_CSS = """
    TodoInput {
        height: 3;
        margin: 1;
    }
    TodoInput Horizontal {
        width: 100%;
    }
    TodoInput Input {
        width: 1fr;
    }
    TodoInput Button {
        width: 12;
    }
    """

    def on_mount(self) -> None:
        self.todos = TodoStore.use(self)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Input(placeholder="What needs to be done?", id="new-todo")
            yield Button("Add", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self._add_todo()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._add_todo()

    def _add_todo(self) -> None:
        input_widget = self.query_one("#new-todo", Input)
        if input_widget.value.strip():
            self.todos.dispatch(AddTodo(input_widget.value))
            input_widget.value = ""


class TodoItemView(Static):
    """Single todo item view."""

    DEFAULT_CSS = """
    TodoItemView {
        height: 3;
        padding: 0 1;
    }
    TodoItemView Horizontal {
        width: 100%;
    }
    TodoItemView .completed {
        text-style: strike;
        color: $text-muted;
    }
    TodoItemView Label {
        width: 1fr;
    }
    TodoItemView Button {
        width: 3;
        min-width: 3;
    }
    """

    def __init__(self, item: TodoItem) -> None:
        super().__init__()
        self.item = item

    def on_mount(self) -> None:
        self.todos = TodoStore.use(self)

    def compose(self) -> ComposeResult:
        with Horizontal():
            check = "✓" if self.item.completed else "○"
            yield Button(check, id="toggle")
            label = Label(self.item.text)
            if self.item.completed:
                label.add_class("completed")
            yield label
            yield Button("×", id="delete", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "toggle":
            self.todos.dispatch(ToggleTodo(self.item.id))
        elif event.button.id == "delete":
            self.todos.dispatch(DeleteTodo(self.item.id))


class TodoList(Static):
    """List of todos with filtering."""

    DEFAULT_CSS = """
    TodoList {
        height: auto;
        max-height: 15;
        margin: 1;
        border: solid $primary;
        padding: 1;
    }
    """

    def on_mount(self) -> None:
        self.todos = TodoStore.use(self)

        # Derived: filtered items based on current filter
        self.filtered = use_derived(
            self,
            self.todos,
            self._filter_items,
            name="filtered"
        )

    def _filter_items(self, state: TodoState) -> list[TodoItem]:
        match state.filter:
            case "all":
                return state.items
            case "active":
                return [i for i in state.items if not i.completed]
            case "completed":
                return [i for i in state.items if i.completed]
        return state.items

    def compose(self) -> ComposeResult:
        yield Label("Loading...", id="empty")

    @effect(TodoStore)
    def on_todos_change(self, old: TodoState, new: TodoState) -> None:
        self._rebuild_list()

    def _rebuild_list(self) -> None:
        # Clear existing items
        for child in list(self.children):
            child.remove()

        # Add filtered items
        items = self.filtered.value
        if not items:
            self.mount(Label("No items to show"))
        else:
            for item in items:
                self.mount(TodoItemView(item))


class FilterBar(Static):
    """Filter buttons and stats."""

    DEFAULT_CSS = """
    FilterBar {
        height: 3;
        margin: 1;
    }
    FilterBar Horizontal {
        width: 100%;
        align: center middle;
    }
    FilterBar Button {
        margin: 0 1;
    }
    FilterBar #stats {
        width: 1fr;
    }
    """

    def on_mount(self) -> None:
        self.todos = TodoStore.use(self)

        # Derived values
        self.active_count = use_derived(
            self,
            self.todos,
            lambda s: sum(1 for i in s.items if not i.completed),
            name="active_count"
        )

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("", id="stats")
            yield Button("All", id="all")
            yield Button("Active", id="active")
            yield Button("Completed", id="completed")
            yield Button("Clear Done", id="clear", variant="warning")

    @effect("active_count")
    def on_count_change(self, old: int, new: int) -> None:
        total = len(self.todos.value.items)
        self.query_one("#stats", Label).update(f"{new} active / {total} total")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "all":
                self.todos.dispatch(SetFilter("all"))
            case "active":
                self.todos.dispatch(SetFilter("active"))
            case "completed":
                self.todos.dispatch(SetFilter("completed"))
            case "clear":
                self.todos.dispatch(ClearCompleted())


class TodoInitializer(Static):
    """Invisible widget that adds initial todos on mount."""

    def on_mount(self) -> None:
        todos = TodoStore.use(self)
        todos.dispatch(AddTodo("Learn Textual"))
        todos.dispatch(AddTodo("Build awesome TUI apps"))
        todos.dispatch(AddTodo("Master textual-reactive"))
        # Remove self after initialization
        self.remove()


class TodoApp(App):
    """Main todo application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        height: 3;
        margin: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        # Provider wraps all children that need access to the store
        yield TodoStore.provider(
            TodoInitializer(),  # Adds initial todos
            Static("Todo App", id="title"),
            TodoInput(),
            TodoList(),
            FilterBar(),
        )
        yield Footer()


if __name__ == "__main__":
    TodoApp().run()
