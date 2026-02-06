"""
Todo App Example - Demonstrates all features of textual-reactive.

This example shows:
- use_state: For simple counter state
- use_model_reducer: For complex todo list state with Pydantic
- Context: For sharing theme across widgets
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, Static

from textual_reactive import (
    ContextProvider,
    ModelContextHandle,
    ReducerHandle,
    StateChanged,
    StateHandle,
    create_model_context,
    use_context,
    use_model_reducer,
    use_state,
)


# --- Pydantic Models ---


class TodoItem(BaseModel):
    """A single todo item."""

    id: int
    text: str
    completed: bool = False


class TodoState(BaseModel):
    """State for the todo list."""

    items: list[TodoItem] = []
    next_id: int = 1
    filter: Literal["all", "active", "completed"] = "all"


class ThemeConfig(BaseModel):
    """Theme configuration."""

    mode: Literal["light", "dark"] = "dark"
    primary_color: str = "#007bff"
    accent_color: str = "#28a745"


# --- Actions ---


@dataclass
class AddTodo:
    """Action to add a new todo."""

    text: str


@dataclass
class ToggleTodo:
    """Action to toggle a todo's completed state."""

    id: int


@dataclass
class DeleteTodo:
    """Action to delete a todo."""

    id: int


@dataclass
class SetFilter:
    """Action to change the filter."""

    filter: Literal["all", "active", "completed"]


@dataclass
class ClearCompleted:
    """Action to clear all completed todos."""

    pass


TodoAction = AddTodo | ToggleTodo | DeleteTodo | SetFilter | ClearCompleted


# --- Reducer ---


def todo_reducer(state: TodoState, action: TodoAction) -> TodoState:
    """Reducer for todo state."""
    match action:
        case AddTodo(text):
            if not text.strip():
                return state
            new_item = TodoItem(id=state.next_id, text=text.strip())
            return state.model_copy(
                update={
                    "items": [*state.items, new_item],
                    "next_id": state.next_id + 1,
                }
            )

        case ToggleTodo(id):
            items = [
                (
                    item.model_copy(update={"completed": not item.completed})
                    if item.id == id
                    else item
                )
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


# --- Context ---

ThemeContext = create_model_context(ThemeConfig(), name="theme")


# --- Widgets ---


class TodoInput(Static):
    """Input widget for adding new todos."""

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

    def __init__(self, todos: ReducerHandle[TodoState, TodoAction]) -> None:
        super().__init__()
        self._todos = todos

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Input(placeholder="What needs to be done?", id="todo-input")
            yield Button("Add", id="add-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-btn":
            self._add_todo()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._add_todo()

    def _add_todo(self) -> None:
        input_widget = self.query_one("#todo-input", Input)
        text = input_widget.value
        if text.strip():
            self._todos.dispatch(AddTodo(text))
            input_widget.value = ""


class TodoItemWidget(Static):
    """Widget representing a single todo item."""

    DEFAULT_CSS = """
    TodoItemWidget {
        height: 3;
        padding: 0 1;
    }
    TodoItemWidget Horizontal {
        width: 100%;
        height: 100%;
    }
    TodoItemWidget .completed {
        text-style: strike;
        color: $text-muted;
    }
    TodoItemWidget Label {
        width: 1fr;
        height: 100%;
        content-align: left middle;
    }
    TodoItemWidget Button {
        width: 8;
    }
    """

    def __init__(
        self, item: TodoItem, todos: ReducerHandle[TodoState, TodoAction]
    ) -> None:
        super().__init__()
        self._item = item
        self._todos = todos

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Checkbox(value=self._item.completed, id=f"check-{self._item.id}")
            label = Label(self._item.text, id=f"label-{self._item.id}")
            if self._item.completed:
                label.add_class("completed")
            yield label
            yield Button("×", id=f"delete-{self._item.id}", variant="error")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        self._todos.dispatch(ToggleTodo(self._item.id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if str(event.button.id).startswith("delete-"):
            self._todos.dispatch(DeleteTodo(self._item.id))


class TodoList(Static):
    """Widget displaying the list of todos."""

    DEFAULT_CSS = """
    TodoList {
        height: auto;
        max-height: 20;
        margin: 1;
        border: solid $primary;
    }
    """

    def __init__(self, todos: ReducerHandle[TodoState, TodoAction]) -> None:
        super().__init__()
        self._todos = todos

    def compose(self) -> ComposeResult:
        state = self._todos.value
        filtered_items = self._get_filtered_items(state)

        if not filtered_items:
            yield Label("No items to show", id="empty-msg")
        else:
            for item in filtered_items:
                yield TodoItemWidget(item, self._todos)

    def _get_filtered_items(self, state: TodoState) -> list[TodoItem]:
        match state.filter:
            case "all":
                return state.items
            case "active":
                return [item for item in state.items if not item.completed]
            case "completed":
                return [item for item in state.items if item.completed]
        return state.items


class FilterBar(Static):
    """Widget for filtering todos."""

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
    FilterBar .active-filter {
        background: $primary;
    }
    """

    def __init__(self, todos: ReducerHandle[TodoState, TodoAction]) -> None:
        super().__init__()
        self._todos = todos

    def compose(self) -> ComposeResult:
        state = self._todos.value
        with Horizontal():
            all_btn = Button("All", id="filter-all")
            active_btn = Button("Active", id="filter-active")
            completed_btn = Button("Completed", id="filter-completed")
            clear_btn = Button("Clear Completed", id="clear-completed", variant="warning")

            # Highlight active filter
            match state.filter:
                case "all":
                    all_btn.add_class("active-filter")
                case "active":
                    active_btn.add_class("active-filter")
                case "completed":
                    completed_btn.add_class("active-filter")

            yield all_btn
            yield active_btn
            yield completed_btn
            yield clear_btn

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "filter-all":
                self._todos.dispatch(SetFilter("all"))
            case "filter-active":
                self._todos.dispatch(SetFilter("active"))
            case "filter-completed":
                self._todos.dispatch(SetFilter("completed"))
            case "clear-completed":
                self._todos.dispatch(ClearCompleted())


class StatsDisplay(Static):
    """Widget showing todo statistics."""

    DEFAULT_CSS = """
    StatsDisplay {
        height: 3;
        margin: 1;
        padding: 0 1;
        background: $surface;
        border: solid $secondary;
    }
    StatsDisplay Horizontal {
        width: 100%;
        height: 100%;
        align: center middle;
    }
    StatsDisplay Label {
        margin: 0 2;
    }
    """

    def __init__(
        self,
        todos: ReducerHandle[TodoState, TodoAction],
        counter: StateHandle[int],
    ) -> None:
        super().__init__()
        self._todos = todos
        self._counter = counter

    def compose(self) -> ComposeResult:
        state = self._todos.value
        total = len(state.items)
        completed = sum(1 for item in state.items if item.completed)
        active = total - completed

        with Horizontal():
            yield Label(f"Total: {total}")
            yield Label(f"Active: {active}")
            yield Label(f"Completed: {completed}")
            yield Label(f"Interactions: {self._counter.value}")


class ThemeToggle(Static):
    """Widget for toggling theme (demonstrates context)."""

    DEFAULT_CSS = """
    ThemeToggle {
        height: 3;
        margin: 1;
        dock: right;
        width: auto;
    }
    """

    theme: ModelContextHandle[ThemeConfig]

    def on_mount(self) -> None:
        self.theme = use_context(self, ThemeContext)

    def compose(self) -> ComposeResult:
        yield Button("Toggle Theme", id="theme-toggle")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "theme-toggle":
            current_mode = self.theme.value.mode
            new_mode: Literal["light", "dark"] = (
                "light" if current_mode == "dark" else "dark"
            )
            self.theme.update(mode=new_mode)

    def on_state_changed(self, event: StateChanged[ThemeConfig]) -> None:
        # Could update widget appearance based on theme
        pass


class TodoApp(App):
    """Main todo application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: $primary;
        height: 3;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("t", "toggle_theme", "Toggle Theme"),
    ]

    todos: ReducerHandle[TodoState, TodoAction]
    interaction_count: StateHandle[int]

    def compose(self) -> ComposeResult:
        yield Header()
        yield ContextProvider(
            ThemeContext,
            ThemeConfig(mode="dark"),
            Container(
                Static("Todo App", id="title"),
                ThemeToggle(),
                TodoInput(self.todos),
                TodoList(self.todos),
                FilterBar(self.todos),
                StatsDisplay(self.todos, self.interaction_count),
                id="main-container",
            ),
        )
        yield Footer()

    def on_mount(self) -> None:
        # Initialize state using hooks
        self.todos = use_model_reducer(self, todo_reducer, TodoState())
        self.interaction_count = use_state(self, 0, name="interactions")

        # Add some initial todos
        self.todos.dispatch(AddTodo("Learn Textual"))
        self.todos.dispatch(AddTodo("Build awesome TUI apps"))
        self.todos.dispatch(AddTodo("Master textual-reactive"))

    def on_state_changed(self, event: StateChanged) -> None:
        # Track all state changes as interactions
        self.interaction_count.set(lambda x: x + 1)
        # Refresh the app to reflect state changes
        self.refresh()
        # Re-compose affected widgets
        self._refresh_widgets()

    def _refresh_widgets(self) -> None:
        """Refresh widgets that depend on state."""
        # Remove and re-add dynamic widgets
        try:
            container = self.query_one("#main-container", Container)
            # Find and refresh TodoList
            for widget in container.query(TodoList):
                widget.remove()
            for widget in container.query(FilterBar):
                widget.remove()
            for widget in container.query(StatsDisplay):
                widget.remove()

            # Re-mount updated widgets
            container.mount(TodoList(self.todos))
            container.mount(FilterBar(self.todos))
            container.mount(StatsDisplay(self.todos, self.interaction_count))
        except Exception:
            pass  # Widget not found during initial compose

    def action_toggle_theme(self) -> None:
        """Toggle theme action for keybinding."""
        try:
            toggle = self.query_one(ThemeToggle)
            toggle.theme.update(
                mode="light" if toggle.theme.value.mode == "dark" else "dark"
            )
        except Exception:
            pass


if __name__ == "__main__":
    app = TodoApp()
    app.run()
