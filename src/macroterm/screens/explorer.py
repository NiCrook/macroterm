from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Input, LoadingIndicator, Static

from macroterm.data.fred import search_series
from macroterm.screens.detail import SeriesDetailScreen


class ExplorerPane(Vertical):
    DEFAULT_CSS = """
    ExplorerPane {
        height: 1fr;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Data Series Explorer", classes="section-title")
        yield Input(placeholder="Search series (e.g. GDP, CPI, unemployment)...", id="explorer-input")
        yield LoadingIndicator(id="explorer-loading")
        yield DataTable(id="series-table")

    def on_mount(self) -> None:
        table = self.query_one("#series-table", DataTable)
        table.add_columns("Series ID", "Title", "Frequency", "Units", "Last Updated")
        table.cursor_type = "row"
        self.query_one("#explorer-loading").display = False

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.run_worker(self._do_search(query), name="search_series", exclusive=True)

    async def _do_search(self, query: str) -> None:
        loading = self.query_one("#explorer-loading")
        table = self.query_one("#series-table", DataTable)

        loading.display = True
        table.clear()

        try:
            results = await search_series(query, limit=25)
        except Exception as e:
            loading.display = False
            table.add_row("—", str(e), "—", "—", "—")
            return

        loading.display = False

        if not results:
            table.add_row("—", "No results found", "—", "—", "—")
            return

        for s in results:
            table.add_row(s.id, s.title, s.frequency, s.units, s.last_updated, key=s.id)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#series-table", DataTable)
        row = table.get_row(event.row_key)
        series_id = row[0]
        series_title = row[1]
        if series_id and series_id != "—":
            self.app.push_screen(SeriesDetailScreen(series_id, series_title))
