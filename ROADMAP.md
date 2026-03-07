# Roadmap

## Data & Content

- [ ] Add more RSS feeds (ECB, IMF, World Bank, OECD)
- [ ] Show release times in Calendar tab (FRED provides time-of-day data)
- [ ] Series comparison view — side-by-side table or overlaid sparklines for two series

## UX & Navigation

- [ ] Search/filter within the Feeds tab by keyword
- [ ] Table keyboard shortcuts (`r` to refresh, `/` to filter rows in-place)
- [ ] Export series observations or calendar to CSV
- [ ] Color-coded calendar (highlight today, weekends, high-impact releases)
- [ ] Desktop notifications when a watched series publishes new data

## Technical

- [ ] Persistent cache (SQLite or JSON on disk) to survive restarts
- [ ] User config file for RSS feed selection, refresh intervals, default tab
- [ ] Toast notifications for errors instead of inline error rows
- [ ] Test suite for the data layer (parsing, catalog search, cache TTL)
