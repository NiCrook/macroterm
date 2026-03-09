# Changelog

## [1.0.0] - 2026-03-09

### Features

- add multi-source search: BLS catalog alongside FRED API
- add BLS category browsing sidebar in Explorer
- (explorer) expand FRED categories and BLS catalog
- (explorer) add geographic filtering to search and category browsing
- add persistent watchlist/bookmarks feature
- add sparkline previews to explorer, watchlist, and detail screens
- add RSS feeds tab with Fed, BEA, and Census Bureau sources
- (rss) add ECB, ECB Blog, and BIS Speeches feeds
- (cache) add persistent disk cache with SQLite backend
- (compare) add series comparison view from watchlist
- (logging) add structured JSON logger and instrument data clients
- (logging) add structured logging to RSS feed client
- (logging) add structured logging to unified search client
- (logging) add structured logging to cache and watchlist modules
- (logging) add structured logging to all screen modules
- (fred) add structured logging to FRED API client

### Bug Fixes

- fix FRED category IDs to use leaf categories with actual series
- (explorer) handle Select.NULL sentinel and improve category browsing

### Performance

- (watchlist) fetch all entries concurrently with asyncio.gather

### Documentation

- add CLAUDE.md with project conventions and architecture
- add project roadmap
- mark RSS feeds roadmap item as complete
- mark series comparison roadmap item as complete
- add README and update CLAUDE.md architecture docs
- add screenshot to README

### Other

- remove finnhub integration
