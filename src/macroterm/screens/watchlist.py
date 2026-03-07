from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, LoadingIndicator, Sparkline, Static

from macroterm.data import watchlist
from macroterm.data.bls import get_series_data
from macroterm.data.fred import get_observations
from macroterm.screens.detail import SeriesDetailScreen


def _is_float(v: str) -> bool:
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def _format_change(current_val: str, prev_val: str) -> str:
    try:
        curr = float(current_val)
        prev = float(prev_val)
    except (ValueError, TypeError):
        return "[dim]—[/dim]"
    diff = curr - prev
    if diff > 0:
        return f"[green]▲ +{diff:.2f}[/green]"
    elif diff < 0:
        return f"[red]▼ {diff:.2f}[/red]"
    else:
        return "[dim]— 0.00[/dim]"


class WatchlistPane(Vertical):
    DEFAULT_CSS = """
    WatchlistPane {
        height: 1fr;
        padding: 1 2;
    }
    """

    BINDINGS = [
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
                        change = _format_change(obs[0].value, obs[1].value) if len(obs) > 1 else "[dim]—[/dim]"
                    else:
                        value, date, change = "N/A", "—", "[dim]—[/dim]"
                elif entry.source == "BLS":
                    data = await get_series_data([entry.series_id])
                    series = data.get(entry.series_id, [])
                    if series:
                        value = series[0].value
                        date = f"{series[0].period_name} {series[0].year}"
                        change = _format_change(series[0].value, series[1].value) if len(series) > 1 else "[dim]—[/dim]"
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
            values = [float(v) for v in raw if _is_float(v)]
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

    def action_refresh(self) -> None:
        self._refresh_watchlist()
