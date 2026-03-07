from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import DataTable, LoadingIndicator, OptionList, Sparkline, Static
from textual.widgets.option_list import Option

from macroterm.data import watchlist
from macroterm.data.bls import get_series_data
from macroterm.data.format import format_change, is_float
from macroterm.data.fred import get_observations
from macroterm.screens.compare import CompareScreen
from macroterm.screens.detail import SeriesDetailScreen


class _ComparePickerModal(ModalScreen[tuple[str, str, str] | None]):
    """Pick a second series from the watchlist to compare against."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    _ComparePickerModal {
        align: center middle;
    }

    #compare-picker {
        width: 60;
        height: 20;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }

    #compare-picker-title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, exclude_key: str, entries: list[watchlist.WatchlistEntry]) -> None:
        super().__init__()
        self._entries = [e for e in entries if f"{e.source}:{e.series_id}" != exclude_key]

    def compose(self) -> ComposeResult:
        with Vertical(id="compare-picker"):
            yield Static("Compare with...", id="compare-picker-title")
            yield OptionList(id="compare-picker-list")

    def on_mount(self) -> None:
        ol = self.query_one("#compare-picker-list", OptionList)
        for e in self._entries:
            ol.add_option(Option(
                f"[{e.source}] {e.series_id} — {e.display_name}",
                id=f"{e.source}:{e.series_id}",
            ))
        if not self._entries:
            ol.add_option(Option("No other series in watchlist", id="__none__"))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        opt_id = str(event.option.id)
        if opt_id == "__none__":
            self.dismiss(None)
            return
        for e in self._entries:
            if f"{e.source}:{e.series_id}" == opt_id:
                self.dismiss((e.series_id, e.display_name, e.source))
                return
        self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class WatchlistPane(Vertical):
    DEFAULT_CSS = """
    WatchlistPane {
        height: 1fr;
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("c", "compare_series", "Compare", priority=True),
        Binding("d", "delete_bookmark", "Delete", priority=True),
        Binding("r", "refresh", "Refresh", priority=True),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Watchlist", classes="section-title")
        yield LoadingIndicator(id="watchlist-loading")
        yield DataTable(id="watchlist-table")
        with Vertical(id="sparkline-preview"):
            yield Static("", id="sparkline-preview-label")
            yield Sparkline([], id="watchlist-sparkline")

    def on_mount(self) -> None:
        table = self.query_one("#watchlist-table", DataTable)
        table.add_columns("Source", "Series ID", "Title", "Latest Value", "Date", "Change")
        table.cursor_type = "row"
        table.display = False
        self.query_one("#sparkline-preview").display = False
        self._refresh_watchlist()

    def on_show(self) -> None:
        self._refresh_watchlist()

    def _refresh_watchlist(self) -> None:
        self.run_worker(self._fetch_data(), name="fetch_watchlist", exclusive=True)

    async def _fetch_data(self) -> None:
        loading = self.query_one("#watchlist-loading")
        table = self.query_one("#watchlist-table", DataTable)
        loading.display = True
        table.clear()

        entries = watchlist.load()
        if not entries:
            loading.display = False
            table.display = True
            table.add_row("—", "—", "No bookmarked series", "—", "—", "—")
            return

        for entry in entries:
            try:
                if entry.source == "FRED":
                    obs = await get_observations(entry.series_id, limit=2)
                    if obs:
                        value = obs[0].value
                        date = obs[0].date
                        change = format_change(obs[0].value, obs[1].value) if len(obs) > 1 else "[dim]—[/dim]"
                    else:
                        value, date, change = "N/A", "—", "[dim]—[/dim]"
                elif entry.source == "BLS":
                    data = await get_series_data([entry.series_id])
                    series = data.get(entry.series_id, [])
                    if series:
                        value = series[0].value
                        date = f"{series[0].period_name} {series[0].year}"
                        change = format_change(series[0].value, series[1].value) if len(series) > 1 else "[dim]—[/dim]"
                    else:
                        value, date, change = "N/A", "—", "[dim]—[/dim]"
                else:
                    value, date, change = "N/A", "—", "[dim]—[/dim]"
            except Exception:
                value, date, change = "Error", "—", "[dim]—[/dim]"

            row_key = f"{entry.source}:{entry.series_id}"
            table.add_row(entry.source, entry.series_id, entry.display_name, value, date, change, key=row_key)

        loading.display = False
        table.display = True

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        table = self.query_one("#watchlist-table", DataTable)
        try:
            row = table.get_row(event.row_key)
        except Exception:
            return
        source = row[0]
        series_id = row[1]
        if series_id and series_id != "—":
            self.run_worker(
                self._fetch_sparkline_preview(series_id, source, row[2]),
                name="sparkline_preview",
                exclusive=True,
            )

    async def _fetch_sparkline_preview(self, series_id: str, source: str, title: str) -> None:
        sparkline = self.query_one("#watchlist-sparkline", Sparkline)
        label = self.query_one("#sparkline-preview-label", Static)
        try:
            if source == "BLS":
                data = await get_series_data([series_id])
                series = data.get(series_id, [])
                raw = [p.value for p in reversed(series)]
            else:
                obs = await get_observations(series_id, limit=20)
                raw = [o.value for o in reversed(obs)] if obs else []
            values = [float(v) for v in raw if is_float(v)]
            if values:
                sparkline.data = values
                label.update(f"[dim]{title}[/dim]")
                self.query_one("#sparkline-preview").display = True
            else:
                self.query_one("#sparkline-preview").display = False
        except Exception:
            self.query_one("#sparkline-preview").display = False

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#watchlist-table", DataTable)
        row = table.get_row(event.row_key)
        source = row[0]
        series_id = row[1]
        series_title = row[2]
        if series_id and series_id != "—":
            self.app.push_screen(SeriesDetailScreen(series_id, series_title, source))

    def action_delete_bookmark(self) -> None:
        table = self.query_one("#watchlist-table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            row = table.get_row(row_key)
        except Exception:
            return
        source = row[0]
        series_id = row[1]
        if series_id and series_id != "—":
            watchlist.remove(series_id, source)
            self.notify(f"Removed {series_id} from watchlist")
            self._refresh_watchlist()

    def action_compare_series(self) -> None:
        table = self.query_one("#watchlist-table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            row = table.get_row(row_key)
        except Exception:
            return
        source = row[0]
        series_id = row[1]
        title = row[2]
        if not series_id or series_id == "—":
            return

        entries = watchlist.load()
        if len(entries) < 2:
            self.notify("Need at least 2 watchlist items to compare")
            return

        current_key = f"{source}:{series_id}"
        series_a = (series_id, title, source)

        def on_pick(result: tuple[str, str, str] | None) -> None:
            if result is not None:
                self.app.push_screen(CompareScreen(series_a, result))

        self.app.push_screen(_ComparePickerModal(current_key, entries), on_pick)

    def action_refresh(self) -> None:
        self._refresh_watchlist()
