from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, LoadingIndicator, Sparkline, Static

from macroterm.data.bls import get_series_data
from macroterm.data.format import format_change, is_float, parse_floats
from macroterm.data.fred import get_observations
from macroterm.logger import get_logger

logger = get_logger("screens.compare")


async def _fetch_series(series_id: str, source: str) -> list[tuple[str, str]]:
    """Return [(date, value), ...] newest-first for a series."""
    if source == "BLS":
        data = await get_series_data([series_id])
        series = data.get(series_id, [])
        return [(f"{p.period_name} {p.year}", p.value) for p in series]
    else:
        obs = await get_observations(series_id, limit=50)
        return [(o.date, o.value) for o in obs] if obs else []


def _align_by_date(
    a_data: list[tuple[str, str]],
    b_data: list[tuple[str, str]],
) -> list[tuple[str, str | None, str | None]]:
    """Merge two date-keyed lists into aligned rows, preserving newest-first order."""
    a_map = {date: val for date, val in a_data}
    b_map = {date: val for date, val in b_data}

    seen: set[str] = set()
    ordered_dates: list[str] = []
    for date, _ in a_data:
        if date not in seen:
            ordered_dates.append(date)
            seen.add(date)
    for date, _ in b_data:
        if date not in seen:
            ordered_dates.append(date)
            seen.add(date)

    return [(d, a_map.get(d), b_map.get(d)) for d in ordered_dates]


class CompareScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("q", "pop_screen", "Back"),
        Binding("n", "toggle_normalize", "Normalize"),
    ]

    def __init__(
        self,
        series_a: tuple[str, str, str],
        series_b: tuple[str, str, str],
    ) -> None:
        """Each series arg is (series_id, title, source)."""
        super().__init__()
        self.a_id, self.a_title, self.a_source = series_a
        self.b_id, self.b_title, self.b_source = series_b
        self._a_raw_values: list[float] = []
        self._b_raw_values: list[float] = []
        self._normalized = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="compare-container"):
            yield Static(
                f"[{self.a_source}] {self.a_id} vs [{self.b_source}] {self.b_id}",
                classes="section-title",
            )
            yield LoadingIndicator(id="compare-loading")
            yield Static(f"[dim]{self.a_title}[/dim]", id="compare-label-a")
            yield Sparkline([], id="compare-sparkline-a")
            yield Static(f"[dim]{self.b_title}[/dim]", id="compare-label-b")
            yield Sparkline([], id="compare-sparkline-b")
            yield DataTable(id="compare-table")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = f"{self.a_id} vs {self.b_id}"
        table = self.query_one("#compare-table", DataTable)
        table.add_columns("Date", self.a_id, "Change", self.b_id, "Change")
        table.cursor_type = "row"
        table.display = False
        self.query_one("#compare-sparkline-a").display = False
        self.query_one("#compare-sparkline-b").display = False
        self.query_one("#compare-label-a").display = False
        self.query_one("#compare-label-b").display = False
        self.run_worker(self._fetch_data(), name="fetch_compare")

    async def _fetch_data(self) -> None:
        loading = self.query_one("#compare-loading")
        table = self.query_one("#compare-table", DataTable)

        try:
            a_data = await _fetch_series(self.a_id, self.a_source)
            b_data = await _fetch_series(self.b_id, self.b_source)
        except Exception as e:
            logger.error("failed to fetch comparison data", extra={"extra_fields": {
                "series_a": self.a_id, "series_b": self.b_id,
            }}, exc_info=True)
            loading.display = False
            table.display = True
            table.add_row("—", str(e), "", "", "")
            return

        loading.display = False

        if not a_data and not b_data:
            table.display = True
            table.add_row("—", "No data", "", "No data", "")
            return

        # Sparklines (oldest-first)
        self._a_raw_values = parse_floats([v for _, v in reversed(a_data)])
        self._b_raw_values = parse_floats([v for _, v in reversed(b_data)])
        self._update_sparklines()

        # Table rows (newest-first)
        aligned = _align_by_date(a_data, b_data)
        a_vals = [v for _, v, _ in aligned]
        b_vals = [v for _, _, v in aligned]
        table.display = True
        for i, (date, a_val, b_val) in enumerate(aligned):
            a_str = a_val if a_val is not None else "—"
            b_str = b_val if b_val is not None else "—"
            a_prev = a_vals[i + 1] if i + 1 < len(a_vals) else None
            b_prev = b_vals[i + 1] if i + 1 < len(b_vals) else None
            a_change = format_change(a_val, a_prev) if a_val and a_prev else "[dim]—[/dim]"
            b_change = format_change(b_val, b_prev) if b_val and b_prev else "[dim]—[/dim]"
            table.add_row(date, a_str, a_change, b_str, b_change)

    def _update_sparklines(self) -> None:
        spark_a = self.query_one("#compare-sparkline-a", Sparkline)
        spark_b = self.query_one("#compare-sparkline-b", Sparkline)
        label_a = self.query_one("#compare-label-a")
        label_b = self.query_one("#compare-label-b")

        if self._normalized and self._a_raw_values and self._b_raw_values:
            spark_a.data = _normalize(self._a_raw_values)
            spark_b.data = _normalize(self._b_raw_values)
        else:
            if self._a_raw_values:
                spark_a.data = self._a_raw_values
            if self._b_raw_values:
                spark_b.data = self._b_raw_values

        spark_a.display = bool(self._a_raw_values)
        spark_b.display = bool(self._b_raw_values)
        label_a.display = bool(self._a_raw_values)
        label_b.display = bool(self._b_raw_values)

    def action_toggle_normalize(self) -> None:
        self._normalized = not self._normalized
        self._update_sparklines()
        state = "on" if self._normalized else "off"
        self.notify(f"Normalize: {state}")

    def action_pop_screen(self) -> None:
        self.app.pop_screen()


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [50.0] * len(values)
    return [(v - lo) / (hi - lo) * 100 for v in values]
