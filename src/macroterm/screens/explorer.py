import httpx
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Input, LoadingIndicator, OptionList, Select, Sparkline, Static
from textual.widgets.option_list import Option

from macroterm.data.bls import get_by_category, get_categories
from macroterm.data.fred import (
    CATEGORIES as FRED_CATEGORIES,
    GEO_COUNTRIES,
    GEO_TYPES,
    GEO_US_COUNTIES,
    GEO_US_METROS,
    GEO_US_STATES,
    get_category_series,
    get_observations,
    search_series,
)
from macroterm.data.bls import get_series_data
from macroterm.data.search import search_all
from macroterm.data import watchlist
from macroterm.screens.detail import SeriesDetailScreen

def _is_float(v: str) -> bool:
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


BLANK = Select.BLANK
_SENTINEL = getattr(Select, "NULL", BLANK)  # Textual >=1.x uses NULL, older uses BLANK

# Location options keyed by geo type value
_LOCATION_OPTIONS: dict[str, list[tuple[str, str]]] = {
    "nation": [(name, tag) for name, tag in GEO_COUNTRIES.items()],
    "state": [(name, tag) for name, tag in GEO_US_STATES.items()],
    "msa": [(name, tag) for name, tag in GEO_US_METROS.items()],
    "county": [(name, tag) for name, tag in GEO_US_COUNTIES.items()],
}


class ExplorerPane(Vertical):
    BINDINGS = [
        Binding("b", "bookmark_series", "Bookmark"),
    ]

    DEFAULT_CSS = """
    ExplorerPane {
        height: 1fr;
        padding: 1 2;
    }

    #explorer-body {
        height: 1fr;
    }

    #category-list {
        width: 36;
        height: 1fr;
        margin-right: 1;
    }

    #explorer-right {
        height: 1fr;
    }

    #geo-filter-bar {
        height: auto;
        margin: 0 1;
    }

    #geo-type-select {
        width: 24;
        margin-right: 1;
    }

    #geo-location-select {
        width: 36;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Data Series Explorer", classes="section-title")
        yield Input(placeholder="Search series (e.g. GDP, CPI, unemployment)...", id="explorer-input")
        with Horizontal(id="geo-filter-bar"):
            yield Select(
                [(name, val) for name, val in GEO_TYPES.items()],
                prompt="Geo Type",
                id="geo-type-select",
                allow_blank=True,
            )
            yield Select(
                [],
                prompt="Location",
                id="geo-location-select",
                allow_blank=True,
                disabled=True,
            )
        yield LoadingIndicator(id="explorer-loading")
        with Horizontal(id="explorer-body"):
            yield OptionList(id="category-list")
            with Vertical(id="explorer-right"):
                yield DataTable(id="series-table")
                with Vertical(id="sparkline-preview"):
                    yield Static("", id="sparkline-preview-label")
                    yield Sparkline([], id="explorer-sparkline")

    def on_mount(self) -> None:
        table = self.query_one("#series-table", DataTable)
        table.add_columns("Source", "Series ID", "Title", "Frequency", "Units")
        table.cursor_type = "row"
        self.query_one("#explorer-loading").display = False
        self.query_one("#sparkline-preview").display = False

        cat_list = self.query_one("#category-list", OptionList)
        for name, cat_id in FRED_CATEGORIES.items():
            cat_list.add_option(Option(f"FRED: {name}", id=f"fred:{cat_id}:{name}"))
        for cat in get_categories():
            cat_list.add_option(Option(f"BLS: {cat}", id=f"bls:{cat}"))

    def _geo_search_params(self) -> tuple[str | None, str | None]:
        """Return (tag_names, extra_query_text) based on current geo filter.

        For US sub-national (state/msa/county), uses FRED tag_names filtering.
        For national/country, appends country name to the search query instead,
        since FRED's geo tags are sparse for international series.
        """
        geo_type_sel = self.query_one("#geo-type-select", Select)
        geo_loc_sel = self.query_one("#geo-location-select", Select)
        geo_type = geo_type_sel.value
        geo_loc = geo_loc_sel.value

        if geo_type is BLANK or geo_type is _SENTINEL or not geo_type:
            return None, None

        geo_type_str = str(geo_type)

        if geo_type_str == "nation":
            # Append country name to search text instead of using tags
            if geo_loc is not BLANK and geo_loc is not _SENTINEL and geo_loc:
                # Find the display name for this tag value
                for name, tag in GEO_COUNTRIES.items():
                    if tag == str(geo_loc):
                        return None, name
            return None, None

        # US sub-national: use tag_names
        parts: list[str] = [geo_type_str]
        if geo_loc is not BLANK and geo_loc is not _SENTINEL and geo_loc:
            parts.append(str(geo_loc))
        return ";".join(parts), None

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "geo-type-select":
            self._on_geo_type_changed(event)
        elif event.select.id == "geo-location-select":
            self._rerun_current()

    def _on_geo_type_changed(self, event: Select.Changed) -> None:
        loc_select = self.query_one("#geo-location-select", Select)
        geo_type = event.value

        if geo_type is BLANK or geo_type is _SENTINEL or not geo_type:
            loc_select.set_options([])
            loc_select.disabled = True
            # Cleared geo filter — re-run to show unfiltered results
            self._rerun_current()
        else:
            options = _LOCATION_OPTIONS.get(str(geo_type), [])
            loc_select.set_options(options)
            loc_select.disabled = False
            # Don't re-run yet — wait for user to pick a location

    def _rerun_current(self) -> None:
        search_input = self.query_one("#explorer-input", Input)
        query = search_input.value.strip()
        if query:
            self.run_worker(self._do_search(query), name="search_series", exclusive=True)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = str(event.option.id)
        source, _, rest = option_id.partition(":")

        if source == "bls":
            self._show_bls_category(rest)
        elif source == "fred":
            cat_id_str, _, cat_name = rest.partition(":")
            self.run_worker(
                self._show_fred_category(int(cat_id_str), cat_name),
                name="fred_category",
                exclusive=True,
            )

    def _show_bls_category(self, category: str) -> None:
        table = self.query_one("#series-table", DataTable)
        table.clear()
        for e in get_by_category(category):
            row_key = f"BLS:{e.series_id}"
            table.add_row("BLS", e.series_id, e.title, e.frequency, e.units, key=row_key)

    async def _show_fred_category(self, category_id: int, category_name: str) -> None:
        loading = self.query_one("#explorer-loading")
        table = self.query_one("#series-table", DataTable)
        loading.display = True
        table.clear()

        tag_names, extra_text = self._geo_search_params()

        try:
            if tag_names or extra_text:
                # Geo filter active — search by category name + geo text
                query = category_name
                if extra_text:
                    query = f"{category_name} {extra_text}"
                series = await search_series(query, limit=100, tag_names=tag_names)
            else:
                try:
                    series = await get_category_series(category_id)
                except httpx.HTTPStatusError:
                    series = []
                if not series:
                    series = await search_series(category_name, limit=100)
        except Exception as e:
            loading.display = False
            table.add_row("—", "—", str(e), "—", "—")
            return

        loading.display = False
        if not series:
            table.add_row("—", "—", "No series found", "—", "—")
            return
        seen: set[str] = set()
        for s in series:
            row_key = f"FRED:{s.id}"
            if row_key in seen:
                continue
            seen.add(row_key)
            table.add_row("FRED", s.id, s.title, s.frequency, s.units, key=row_key)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if query:
            self.run_worker(self._do_search(query), name="search_series", exclusive=True)

    async def _do_search(self, query: str) -> None:
        loading = self.query_one("#explorer-loading")
        table = self.query_one("#series-table", DataTable)

        loading.display = True
        table.clear()

        tag_names, extra_text = self._geo_search_params()
        search_query = f"{query} {extra_text}" if extra_text else query

        try:
            results = await search_all(search_query, limit=100, tag_names=tag_names)
        except Exception as e:
            loading.display = False
            table.add_row("—", "—", str(e), "—", "—")
            return

        loading.display = False

        if not results:
            table.add_row("—", "—", "No results found", "—", "—")
            return

        seen: set[str] = set()
        for s in results:
            row_key = f"{s.source}:{s.series_id}"
            if row_key in seen:
                continue
            seen.add(row_key)
            table.add_row(s.source, s.series_id, s.title, s.frequency, s.units, key=row_key)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.row_key is None:
            return
        table = self.query_one("#series-table", DataTable)
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
        sparkline = self.query_one("#explorer-sparkline", Sparkline)
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
        table = self.query_one("#series-table", DataTable)
        row = table.get_row(event.row_key)
        source = row[0]
        series_id = row[1]
        series_title = row[2]
        if series_id and series_id != "—":
            self.app.push_screen(SeriesDetailScreen(series_id, series_title, source))

    def action_bookmark_series(self) -> None:
        table = self.query_one("#series-table", DataTable)
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            row = table.get_row(row_key)
        except Exception:
            return
        source = row[0]
        series_id = row[1]
        title = row[2]
        if series_id and series_id != "—":
            watchlist.add(series_id, source, title)
            self.notify(f"Bookmarked {series_id}")
