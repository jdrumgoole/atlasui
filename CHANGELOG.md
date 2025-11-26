# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.3] - 2025-11-26

### Fixed
- Event loop conflicts between Playwright browser tests and async tests
- Browser test timeouts by changing wait strategy from "networkidle" to "load"
- All async test markers to work with pytest-asyncio strict mode

### Added
- Browser test marker (@pytest.mark.browser) for proper test separation
- Comprehensive test documentation in tests/README.md
- Auto-update cluster counts on projects pages when cluster operations complete

### Improved
- Test infrastructure now supports running browser and async tests separately
- Complete test suite: 68 tests (66 async + 2 browser), all passing
- Enhanced documentation for running different test types

## [0.2.1] - 2025-11-25

### Fixed
- Converted all test suites to async to support async-only AtlasClient
- Fixed integration test suite that was being skipped due to credential validation
- Fixed test_cluster_details to handle both M0 (free tier) and regular cluster structures
- Fixed Starlette TemplateResponse deprecation warnings (updated to new parameter order)
- Fixed async context manager support in all test fixtures

### Changed
- Development environment now defaults to port 8100 (inv start, inv restart, inv kill_port)
- Test environment explicitly uses port 8100 to avoid conflicts with production installs
- Production/end-user installations still default to port 8000

### Improved
- Playwright tests now automatically start and stop the AtlasUI server
- All 66 unit and integration tests now pass with zero warnings
- Better test organization with proper async/await patterns throughout

## [0.2.0] - 2025-11-24

### Added
- Operation queue system for managing long-running Atlas operations
- Auto-refresh for project and cluster lists on operation completion
- Lifecycle tests with resource deletion verification
- Status-based polling for cluster deletion
- Exit server modal with Bootstrap confirmation
- Database-themed favicon

### Fixed
- Cascading delete for already-deleting clusters
- Event listener property name bugs
- API tests to use AsyncMock for async context managers
- Cluster list superfluous reload on delete operations
- Project creation auto-update

### Improved
- Optimized cluster reload (no redundant reloads on delete)
- Added pytest markers for parallel test execution
- Added comprehensive test documentation
- Updated Sphinx docs with new capabilities

## [0.1.4] - 2025-11-20

### Added
- Setup wizard for initial configuration
- Exit button with confirmation dialog
- Port management for server operations
- MongoDB session persistence

### Improved
- Enhanced documentation
- Better error handling

## [0.1.3] - 2025-11-19

### Added
- Major improvements and new features

## [0.1.2] - 2025-11-18

### Added
- Initial release with basic functionality

[0.2.3]: https://github.com/jdrumgoole/atlasui/compare/v0.2.1...v0.2.3
[0.2.1]: https://github.com/jdrumgoole/atlasui/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/jdrumgoole/atlasui/compare/v0.1.4...v0.2.0
[0.1.4]: https://github.com/jdrumgoole/atlasui/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/jdrumgoole/atlasui/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/jdrumgoole/atlasui/releases/tag/v0.1.2
