from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Input, LoadingIndicator, OptionList, Static
from textual.widgets.option_list import Option

from macroterm.data.bls import get_by_category, get_categories
from macroterm.data.fred import CATEGORIES as FRED_CATEGORIES, get_category_series
from macroterm.data.search import search_all
from macroterm.screens.detail import SeriesDetailScreen


class ExplorerPane(Vertical):
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
    """

    def compose(self) -> ComposeResult:
        yield Static("Data Series Explorer", classes="section-title")
        yield Input(placeholder="Search series (e.g. GDP, CPI, unemployment)...", id="explorer-input")
        yield LoadingIndicator(id="explorer-loading")
        with Horizontal(id="explorer-body"):
            yield OptionList(id="category-list")
            with Vertical(id="explorer-right"):
                yield DataTable(id="series-table")

    def on_mount(self) -> None:
        table = self.query_one("#series-table", DataTable)
        table.add_columns("Source", "Series ID", "Title", "Frequency", "Units")
        table.cursor_type = "row"
        self.query_one("#explorer-loading").display = False

        cat_list = self.query_one("#category-list", OptionList)
        for name, cat_id in FRED_CATEGORIES.items():
            cat_list.add_option(Option(f"FRED: {name}", id=f"fred:{cat_id}"))
        for cat in get_categories():
            cat_list.add_option(Option(f"BLS: {cat}", id=f"bls:{cat}"))

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = str(event.option.id)
        source, _, category_key = option_id.partition(":")

        if source == "bls":
            self._show_bls_category(category_key)
        elif source == "fred":
            self.run_worker(
                self._show_fred_category(int(category_key)),
                name="fred_category",
                exclusive=True,
            )

    def _show_bls_category(self, category: str) -> None:
        table = self.query_one("#series-table", DataTable)
        table.clear()
        for e in get_by_category(category):
            row_key = f"BLS:{e.series_id}"
            table.add_row("BLS", e.series_id, e.title, e.frequency, e.units, key=row_key)

    async def _show_fred_category(self, category_id: int) -> None:
        loading = self.query_one("#explorer-loading")
        table = self.query_one("#series-table", DataTable)
        loading.display = True
        table.clear()

        try:
            series = await get_category_series(category_id)
        except Exception as e:
            loading.display = False
            table.add_row("—", "—", str(e), "—", "—")
            return

        loading.display = False
        if not series:
            table.add_row("—", "—", "No series found", "—", "—")
            return
        for s in series:
            row_key = f"FRED:{s.id}"
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

        try:
            results = await search_all(query, limit=25)
        except Exception as e:
            loading.display = False
            table.add_row("—", "—", str(e), "—", "—")
            return

        loading.display = False

        if not results:
            table.add_row("—", "—", "No results found", "—", "—")
            return

        for s in results:
            row_key = f"{s.source}:{s.series_id}"
            table.add_row(s.source, s.series_id, s.title, s.frequency, s.units, key=row_key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        table = self.query_one("#series-table", DataTable)
        row = table.get_row(event.row_key)
        source = row[0]
        series_id = row[1]
        series_title = row[2]
        if series_id and series_id != "—":
            self.app.push_screen(SeriesDetailScreen(series_id, series_title, source))
