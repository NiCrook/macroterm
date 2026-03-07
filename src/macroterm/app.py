from dotenv import load_dotenv

load_dotenv()

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from macroterm.screens.alerts import AlertsPane
from macroterm.screens.calendar import CalendarPane
from macroterm.screens.explorer import ExplorerPane
from macroterm.screens.feeds import FeedsPane
from macroterm.screens.watchlist import WatchlistPane


class MacroTermApp(App):
    CSS_PATH = "app.tcss"
    TITLE = "MacroTerm"
    SUB_TITLE = "Economic Data Terminal"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "tab_calendar", "Calendar", show=False),
        Binding("2", "tab_explorer", "Explorer", show=False),
        Binding("3", "tab_feeds", "Feeds", show=False),
        Binding("4", "tab_alerts", "Alerts", show=False),
        Binding("5", "tab_watchlist", "Watchlist", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Calendar [1]", id="tab-calendar"):
                yield CalendarPane()
            with TabPane("Explorer [2]", id="tab-explorer"):
                yield ExplorerPane()
            with TabPane("Feeds [3]", id="tab-feeds"):
                yield FeedsPane()
            with TabPane("Alerts [4]", id="tab-alerts"):
                yield AlertsPane()
            with TabPane("Watchlist [5]", id="tab-watchlist"):
                yield WatchlistPane()
        yield Footer()

    def action_tab_calendar(self) -> None:
        self.query_one(TabbedContent).active = "tab-calendar"

    def action_tab_explorer(self) -> None:
        self.query_one(TabbedContent).active = "tab-explorer"

    def action_tab_feeds(self) -> None:
        self.query_one(TabbedContent).active = "tab-feeds"

    def action_tab_alerts(self) -> None:
        self.query_one(TabbedContent).active = "tab-alerts"

    def action_tab_watchlist(self) -> None:
        self.query_one(TabbedContent).active = "tab-watchlist"


def main() -> None:
    app = MacroTermApp()
    app.run()
