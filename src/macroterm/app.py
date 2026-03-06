from dotenv import load_dotenv

load_dotenv()

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from macroterm.screens.calendar import CalendarPane
from macroterm.screens.explorer import ExplorerPane
from macroterm.screens.alerts import AlertsPane


class MacroTermApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "MacroTerm"
    SUB_TITLE = "Economic Data Terminal"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "tab_calendar", "Calendar", show=False),
        Binding("2", "tab_explorer", "Explorer", show=False),
        Binding("3", "tab_alerts", "Alerts", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Calendar [1]", id="tab-calendar"):
                yield CalendarPane()
            with TabPane("Explorer [2]", id="tab-explorer"):
                yield ExplorerPane()
            with TabPane("Alerts [3]", id="tab-alerts"):
                yield AlertsPane()
        yield Footer()

    def action_tab_calendar(self) -> None:
        self.query_one(TabbedContent).active = "tab-calendar"

    def action_tab_explorer(self) -> None:
        self.query_one(TabbedContent).active = "tab-explorer"

    def action_tab_alerts(self) -> None:
        self.query_one(TabbedContent).active = "tab-alerts"


def main() -> None:
    app = MacroTermApp()
    app.run()
