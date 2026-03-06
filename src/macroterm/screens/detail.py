from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, LoadingIndicator, Static

from macroterm.data.bls import get_series_data
from macroterm.data.fred import get_observations


class SeriesDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("q", "pop_screen", "Back"),
    ]

    def __init__(self, series_id: str, series_title: str, source: str = "FRED") -> None:
        super().__init__()
        self.series_id = series_id
        self.series_title = series_title
        self.source = source

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="detail-container"):
            yield Static(f"[{self.source}] {self.series_id} — {self.series_title}", classes="section-title")
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
            if self.source == "BLS":
                await self._fetch_bls(table)
            else:
                await self._fetch_fred(table)
        except Exception as e:
            table.add_row("—", str(e))
        finally:
            loading.display = False
            table.display = True

    async def _fetch_fred(self, table: DataTable) -> None:
        observations = await get_observations(self.series_id, limit=50)
        if not observations:
            table.add_row("—", "No observations found")
            return
        for o in observations:
            table.add_row(o.date, o.value)

    async def _fetch_bls(self, table: DataTable) -> None:
        data = await get_series_data([self.series_id])
        series = data.get(self.series_id, [])
        if not series:
            table.add_row("—", "No data found")
            return
        for point in series:
            date_label = f"{point.period_name} {point.year}"
            table.add_row(date_label, point.value)

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
