from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, LoadingIndicator, Static

from macroterm.data.fred import get_observations


class SeriesDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("q", "pop_screen", "Back"),
    ]

    def __init__(self, series_id: str, series_title: str) -> None:
        super().__init__()
        self.series_id = series_id
        self.series_title = series_title

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="detail-container"):
            yield Static(f"{self.series_id} — {self.series_title}", classes="section-title")
            yield LoadingIndicator(id="detail-loading")
            yield DataTable(id="detail-table")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.series_id
        table = self.query_one("#detail-table", DataTable)
        table.add_columns("Date", "Value")
        table.cursor_type = "row"
        table.display = False
        self.run_worker(self._fetch_data(), name="fetch_detail")

    async def _fetch_data(self) -> None:
        loading = self.query_one("#detail-loading")
        table = self.query_one("#detail-table", DataTable)

        try:
            observations = await get_observations(self.series_id, limit=50)
        except Exception as e:
            loading.display = False
            table.display = True
            table.add_row("—", str(e))
            return

        loading.display = False
        table.display = True

        if not observations:
            table.add_row("—", "No observations found")
            return

        for o in observations:
            table.add_row(o.date, o.value)

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
