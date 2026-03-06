from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, LoadingIndicator, Static

from macroterm.data.fred import get_release_dates


class CalendarPane(Vertical):
    DEFAULT_CSS = """
    CalendarPane {
        height: 1fr;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Economic Calendar", classes="section-title")
        yield LoadingIndicator(id="calendar-loading")
        yield DataTable(id="release-table")

    def on_mount(self) -> None:
        table = self.query_one("#release-table", DataTable)
        table.add_columns("Date", "Release", "Release ID")
        table.cursor_type = "row"
        table.display = False
        self.load_data()

    def load_data(self) -> None:
        self.run_worker(self._fetch_data(), name="fetch_calendar")

    async def _fetch_data(self) -> None:
        loading = self.query_one("#calendar-loading")
        table = self.query_one("#release-table", DataTable)

        try:
            releases = await get_release_dates()
        except Exception as e:
            loading.display = False
            table.display = True
            table.add_row("—", str(e), "—")
            return

        loading.display = False
        table.display = True

        if not releases:
            table.add_row("—", "No upcoming releases found", "—")
            return

        for r in releases:
            table.add_row(r.date, r.release_name, str(r.release_id))
