from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, LoadingIndicator, Static

from macroterm.data.rss import RSSEvent, get_rss_events
from macroterm.logger import get_logger
from macroterm.screens.feed_detail import FeedDetailScreen

logger = get_logger("screens.feeds")


class FeedsPane(Vertical):
    DEFAULT_CSS = """
    FeedsPane {
        height: 1fr;
        padding: 1 2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._events: list[RSSEvent] = []

    def compose(self) -> ComposeResult:
        yield Static("RSS Feeds", classes="section-title")
        yield LoadingIndicator(id="feeds-loading")
        yield DataTable(id="feeds-table")

    def on_mount(self) -> None:
        table = self.query_one("#feeds-table", DataTable)
        table.add_columns("Date", "Title", "Source")
        table.cursor_type = "row"
        table.display = False
        self.load_data()

    def load_data(self) -> None:
        self.run_worker(self._fetch_data(), name="fetch_feeds")

    async def _fetch_data(self) -> None:
        loading = self.query_one("#feeds-loading")
        table = self.query_one("#feeds-table", DataTable)

        try:
            self._events = await get_rss_events()
        except Exception as e:
            logger.error("failed to fetch feeds", exc_info=True)
            loading.display = False
            table.display = True
            table.add_row("—", str(e), "—")
            return

        loading.display = False
        table.display = True

        if not self._events:
            table.add_row("—", "No feed items found", "—")
            return

        for e in self._events:
            table.add_row(e.date, e.title, e.source)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_idx = event.cursor_row
        if row_idx < 0 or row_idx >= len(self._events):
            return
        e = self._events[row_idx]
        self.app.push_screen(FeedDetailScreen(
            title=e.title,
            source=e.source,
            date=e.date,
            description=e.description,
            link=e.link,
        ))
