# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Run the app (loads .env automatically via python-dotenv)
.venv/bin/macroterm

# Quick import check (no API keys needed)
.venv/bin/python -c "from macroterm.app import MacroTermApp; print('OK')"

# Test API calls (requires .env to be sourced since dotenv only loads at app startup)
set -a && source .env && set +a && .venv/bin/python -c "..."

# Install in dev mode
.venv/bin/pip install -e .
```

No test framework or linter is configured yet.

## Architecture

**Textual TUI app** with five tabs: Calendar, Explorer, Feeds, Alerts, Watchlist. Each tab is a pane widget in `screens/`. The app entry point is `app.py:main()` which loads `.env` then runs `MacroTermApp`. Tabs are switchable with number keys 1–5.

### Data Layer (`data/`)

- **`fred.py`** — FRED API client (search, observations, releases, category series). Has a `CATEGORIES` dict mapping display names to FRED category IDs. Category IDs must be leaf-level (not parent containers) or `get_category_series` returns nothing.
- **`bls.py`** — BLS API client + local catalog. BLS has no search API, so we maintain a `CATALOG` list of `BLSCatalogEntry` with keyword-based fuzzy matching via `search_catalog()`. Each entry has a `category` field for browse-by-category.
- **`search.py`** — Unified `search_all()` that fans out to FRED API + BLS local catalog. Returns `SearchResult` with a `source` field ("FRED" or "BLS").
- **`cache.py`** — Two-tier caching: in-memory TTL dict + persistent SQLite disk cache (`~/.local/share/macroterm/cache.db`). `async_ttl_cache(ttl_seconds)` decorator for async functions. Exceptions are not cached.
- **`watchlist.py`** — JSON-file persistence for user's saved series (`~/.config/macroterm/watchlist.json`). Synchronous `load()`/`save()` API.
- **`rss.py`** — RSS feed fetcher for central bank and economic agency feeds (Fed, BEA, Census, ECB, BIS). Returns `RSSEvent` dataclasses.
- **`format.py`** — Numeric formatting helpers (`parse_floats`, `is_float`, `format_change`).

### Screen Layer (`screens/`)

- **`explorer.py`** — Search bar + category sidebar (OptionList) + results table (DataTable). Category sidebar shows both FRED and BLS categories with prefixed labels. BLS categories populate instantly (local); FRED categories fetch via API.
- **`detail.py`** — `SeriesDetailScreen` accepts `source` param and dispatches to `_fetch_fred()` or `_fetch_bls()`.
- **`calendar.py`** — Upcoming economic release dates from FRED.
- **`alerts.py`** — Recent release dates from FRED.
- **`feeds.py`** — RSS feed viewer showing recent items from central bank and economic agency feeds.
- **`feed_detail.py`** — Detail view for a single RSS feed item.
- **`watchlist.py`** — Watchlist management with sparklines, change indicators, and series comparison launcher.
- **`compare.py`** — Side-by-side comparison view for two series (from watchlist).

### Adding a New Data Source

1. Create `data/{source}.py` with API client and (if no search API) a local catalog with `search_catalog()` and `get_categories()`/`get_by_category()`
2. Add the source to `search.py:search_all()` for unified search
3. Add prefixed categories to `explorer.py:on_mount()` category list
4. Add a fetch branch in `detail.py:_fetch_data()` for the new source

### Key Patterns

- `.env` is only loaded by `dotenv` in `app.py`. Scripts run outside the app need `set -a && source .env && set +a` first.
- All async data functions use `httpx.AsyncClient` in context managers.
- Screen widgets use `self.run_worker()` for async operations with `exclusive=True` to cancel prior requests.
- User data paths follow XDG conventions: config in `~/.config/macroterm/`, data in `~/.local/share/macroterm/`.

## Environment Variables

Defined in `.env` (gitignored): `FRED_API_KEY`, `BLS_API_KEY`. FRED key is required; BLS key is optional (public API works without, registered key gets higher rate limits).

## Git Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:** `feat`, `fix`, `refactor`, `perf`, `docs`, `style`, `test`, `build`, `ci`, `chore`

**Scope** (optional): area of the codebase, e.g. `explorer`, `fred`, `cache`, `bls`

The description should complete the sentence "This commit will..." (but don't include that prefix). Use imperative mood, lowercase.

**Examples:**
- `feat(explorer): add category browsing sidebar for BLS and FRED`
- `fix(fred): use leaf category IDs that return actual series`
- `refactor(detail): dispatch fetch by source instead of hardcoding FRED`

**Breaking changes:** append `!` after type/scope (e.g. `feat(search)!: change SearchResult fields`) or add a `BREAKING CHANGE:` footer.

Always include `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` as a footer when Claude contributes.
