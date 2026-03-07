from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, LoadingIndicator, Sparkline, Static

from macroterm.data import watchlist
from macroterm.data.bls import get_series_data
from macroterm.data.format import format_change, parse_floats
from macroterm.data.fred import get_observations


class SeriesDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("q", "pop_screen", "Back"),
        Binding("b", "toggle_bookmark", "Bookmark"),
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
            yield Sparkline([], id="detail-sparkline")
            yield DataTable(id="detail-table")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = self.series_id
        table = self.query_one("#detail-table", DataTable)
        table.add_columns("Date", "Value", "Change")
        table.cursor_type = "row"
        table.display = False
        self.query_one("#detail-sparkline").display = False
        self.run_worker(self._fetch_data(), name="fetch_detail")

    async def _fetch_data(self) -> None:
        loading = self.query_one("#detail-loading")
        table = self.query_one("#detail-table", DataTable)
        sparkline = self.query_one("#detail-sparkline", Sparkline)

        try:
            if self.source == "BLS":
                await self._fetch_bls(table, sparkline)
            else:
                await self._fetch_fred(table, sparkline)
        except Exception as e:
            table.add_row("—", str(e), "")
        finally:
            loading.display = False
            table.display = True

    async def _fetch_fred(self, table: DataTable, sparkline: Sparkline) -> None:
        observations = await get_observations(self.series_id, limit=50)
        if not observations:
            table.add_row("—", "No observations found", "")
            return
        values = parse_floats([o.value for o in reversed(observations)])
        if values:
            sparkline.data = values
            sparkline.display = True
        for i, o in enumerate(observations):
            if i + 1 < len(observations):
                change = format_change(o.value, observations[i + 1].value)
            else:
                change = "[dim]—[/dim]"
            table.add_row(o.date, o.value, change)

    async def _fetch_bls(self, table: DataTable, sparkline: Sparkline) -> None:
        data = await get_series_data([self.series_id])
        series = data.get(self.series_id, [])
        if not series:
            table.add_row("—", "No data found", "")
            return
        values = parse_floats([p.value for p in reversed(series)])
        if values:
            sparkline.data = values
            sparkline.display = True
        for i, point in enumerate(series):
            date_label = f"{point.period_name} {point.year}"
            if i + 1 < len(series):
                change = format_change(point.value, series[i + 1].value)
            else:
                change = "[dim]—[/dim]"
            table.add_row(date_label, point.value, change)

    def action_toggle_bookmark(self) -> None:
        if watchlist.is_bookmarked(self.series_id, self.source):
            watchlist.remove(self.series_id, self.source)
            self.notify(f"Removed {self.series_id} from watchlist")
        else:
            watchlist.add(self.series_id, self.source, self.series_title)
            self.notify(f"Bookmarked {self.series_id}")

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
