from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, LoadingIndicator, Static

from macroterm.data.rss import _strip_html, fetch_fed_article
from macroterm.logger import get_logger

logger = get_logger("screens.feed_detail")


class FeedDetailScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
        Binding("q", "pop_screen", "Back"),
    ]

    def __init__(self, title: str, source: str, date: str, description: str, link: str) -> None:
        super().__init__()
        self.feed_title = title
        self.source = source
        self.feed_date = date
        self.description = description
        self.link = link

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="feed-detail-container"):
            yield Static(f"[b]{self.feed_title}[/b]", id="feed-detail-title")
            yield Static(f"[dim]{self.source}  ·  {self.feed_date}[/dim]", id="feed-detail-meta")
            yield LoadingIndicator(id="feed-detail-loading")
            yield Static("", id="feed-detail-body")
            if self.link:
                yield Static(f"\n[dim]Link:[/dim] {self.link}", id="feed-detail-link")
        yield Footer()

    def on_mount(self) -> None:
        self.run_worker(self._load_content(), name="load_feed_content")

    async def _load_content(self) -> None:
        loading = self.query_one("#feed-detail-loading")
        body_widget = self.query_one("#feed-detail-body", Static)

        body = ""

        # For Federal Reserve items, fetch the full article from the linked page
        if self.source == "Federal Reserve" and self.link:
            try:
                body = await fetch_fed_article(self.link)
            except Exception:
                logger.warning("failed to fetch fed article", extra={"extra_fields": {
                    "link": self.link,
                }}, exc_info=True)

        # Fall back to RSS description
        if not body:
            body = _strip_html(self.description) if self.description else "[dim]No description available.[/dim]"

        loading.display = False
        body_widget.update(body)

    def action_pop_screen(self) -> None:
        self.app.pop_screen()
