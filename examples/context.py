"""
Context Example - Demonstrates createContext and useContext.

Shows how to share state across the widget tree without prop drilling.
"""

from typing import Literal

from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Label, Static

from textual_reactive import (
    ContextProvider,
    ModelContextHandle,
    StateChanged,
    create_model_context,
    use_context,
)


# --- Theme Model ---


class Theme(BaseModel):
    """Theme configuration shared across components."""

    mode: Literal["light", "dark"] = "dark"
    primary: str = "#007bff"
    secondary: str = "#6c757d"
    success: str = "#28a745"
    danger: str = "#dc3545"


# --- Create Context ---

ThemeContext = create_model_context(Theme(), name="theme")


# --- Deeply Nested Widget ---


class DeepChild(Static):
    """A deeply nested widget that consumes the theme context."""

    DEFAULT_CSS = """
    DeepChild {
        height: 5;
        padding: 1;
        margin: 1;
        border: solid $primary;
    }
    """

    theme: ModelContextHandle[Theme]

    def on_mount(self) -> None:
        # Consume context - no need to pass it through every parent!
        self.theme = use_context(self, ThemeContext)
        self._update_display()

    def compose(self) -> ComposeResult:
        yield Label("Deep Child Widget", id="deep-label")
        yield Label("", id="theme-info")

    def on_state_changed(self, event: StateChanged[Theme]) -> None:
        self._update_display()

    def _update_display(self) -> None:
        info = f"Theme: {self.theme.value.mode} | Primary: {self.theme.value.primary}"
        try:
            self.query_one("#theme-info", Label).update(info)
        except Exception:
            pass


class MiddleWidget(Static):
    """A middle widget - doesn't need to know about the theme."""

    DEFAULT_CSS = """
    MiddleWidget {
        height: auto;
        padding: 1;
        margin: 1;
        border: dashed $secondary;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("Middle Widget (doesn't consume context)")
        # DeepChild will get the context from the provider above
        yield DeepChild()


class AnotherBranch(Static):
    """Another branch that also consumes the same context."""

    DEFAULT_CSS = """
    AnotherBranch {
        height: 5;
        padding: 1;
        margin: 1;
        background: $surface;
    }
    """

    theme: ModelContextHandle[Theme]

    def on_mount(self) -> None:
        self.theme = use_context(self, ThemeContext)
        self._update_display()

    def compose(self) -> ComposeResult:
        yield Label("", id="branch-label")

    def on_state_changed(self, event: StateChanged[Theme]) -> None:
        self._update_display()

    def _update_display(self) -> None:
        mode = self.theme.value.mode
        emoji = "🌙" if mode == "dark" else "☀️"
        try:
            self.query_one("#branch-label", Label).update(
                f"{emoji} Another branch sees: {mode} mode"
            )
        except Exception:
            pass


class ThemeControls(Static):
    """Widget to control the theme (modifies context)."""

    DEFAULT_CSS = """
    ThemeControls {
        height: 5;
        padding: 1;
        margin: 1;
        background: $primary-darken-2;
    }
    """

    theme: ModelContextHandle[Theme]

    def on_mount(self) -> None:
        self.theme = use_context(self, ThemeContext)

    def compose(self) -> ComposeResult:
        yield Label("Theme Controls:")
        yield Button("Toggle Mode", id="toggle-mode")
        yield Button("Blue Primary", id="blue")
        yield Button("Green Primary", id="green")
        yield Button("Red Primary", id="red")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        match event.button.id:
            case "toggle-mode":
                current = self.theme.value.mode
                new_mode: Literal["light", "dark"] = (
                    "light" if current == "dark" else "dark"
                )
                self.theme.update(mode=new_mode)
            case "blue":
                self.theme.update(primary="#007bff")
            case "green":
                self.theme.update(primary="#28a745")
            case "red":
                self.theme.update(primary="#dc3545")


class ContextApp(App):
    """Demonstrates context for sharing state."""

    CSS = """
    Screen {
        layout: vertical;
        padding: 1;
    }

    #title {
        text-align: center;
        text-style: bold;
        height: 3;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Context Example - Shared Theme State", id="title")

        # The ContextProvider wraps the tree and provides the theme
        yield ContextProvider(
            ThemeContext,
            Theme(mode="dark", primary="#007bff"),
            Container(
                ThemeControls(),  # Can modify the context
                MiddleWidget(),  # Doesn't use context, but contains DeepChild
                AnotherBranch(),  # Also consumes context
            ),
        )


if __name__ == "__main__":
    ContextApp().run()
