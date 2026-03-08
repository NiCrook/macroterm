# MacroTerm

A terminal UI for browsing economic data, releases, and central bank feeds. Built with [Textual](https://textual.textualize.io/).

## Features

- **Calendar** — Upcoming economic release dates from FRED
- **Explorer** — Search and browse FRED and BLS data series with geographic filtering, category sidebar, and sparkline previews
- **Feeds** — RSS feeds from the Federal Reserve, BEA, Census Bureau, ECB, and BIS with full article reading
- **Alerts** — Recent economic data releases
- **Watchlist** — Save series, track latest values and changes, compare two series side-by-side with normalized sparklines

Data is cached locally (in-memory + SQLite at `~/.local/share/macroterm/cache.db`) to minimize API calls.

## Installation

Requires Python 3.11+.

```bash
git clone https://github.com/yourusername/macroterm.git
cd macroterm
python -m venv .venv
.venv/bin/pip install -e .
```

## Setup

Get a free [FRED API key](https://fred.stlouisfed.org/docs/api/api_key.html) and create a `.env` file:

```
FRED_API_KEY=your_key_here
BLS_API_KEY=your_key_here  # optional — BLS public API works without it
```

## Usage

```bash
.venv/bin/macroterm
```

### Keyboard Shortcuts

| Key          | Action                            |
| ------------ | --------------------------------- |
| `1`–`5`      | Switch tabs                       |
| `/` or click | Search in Explorer                |
| `Enter`      | Open series detail / feed article |
| `b`          | Bookmark series to watchlist      |
| `d`          | Delete bookmark (in Watchlist)    |
| `c`          | Compare two series (in Watchlist) |
| `n`          | Toggle normalization (in Compare) |
| `r`          | Refresh (in Watchlist)            |
| `Escape`     | Back                              |
| `q`          | Quit                              |

## Configuration

| Variable              | Purpose                                                        |
| --------------------- | -------------------------------------------------------------- |
| `FRED_API_KEY`        | Required. FRED API access                                      |
| `BLS_API_KEY`         | Optional. Higher BLS rate limits                               |
| `MACROTERM_LOG_LEVEL` | Optional. Set to `DEBUG`, `INFO`, `WARNING` (default), `ERROR` |

Logs are JSON-formatted and written to stderr.

## License

MIT
