from datetime import date, timedelta

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, LoadingIndicator, Static

from macroterm.data.fred import get_release_dates


class AlertsPane(Vertical):
    DEFAULT_CSS = """
    AlertsPane {
        height: 1fr;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Recent Releases", classes="section-title")
        yield LoadingIndicator(id="alerts-loading")
        yield DataTable(id="alerts-table")

    def on_mount(self) -> None:
        table = self.query_one("#alerts-table", DataTable)
        table.add_columns("Date", "Release", "Release ID")
        table.cursor_type = "row"
        table.display = False
        self.load_data()

    def load_data(self) -> None:
        self.run_worker(self._fetch_data(), name="fetch_alerts")

    async def _fetch_data(self) -> None:
        loading = self.query_one("#alerts-loading")
        table = self.query_one("#alerts-table", DataTable)

        try:
            today = date.today()
            releases = await get_release_dates(
                start=today - timedelta(days=7),
                end=today,
            )
        except Exception as e:
            loading.display = False
            table.display = True
            table.add_row("—", str(e), "—")
            return

        loading.display = False
        table.display = True

        if not releases:
            table.add_row("—", "No recent releases found", "—")
            return

        for r in reversed(releases):
            table.add_row(r.date, r.release_name, str(r.release_id))
