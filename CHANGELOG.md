# Changelog

## [4.5.0.2] - 2026-03-16

### Fixed
- Added defensive deduplication of `registry['views']` entries after model registration.
  This prevents duplicate Journal/Changelog tabs caused by dynamic model plugins
  (e.g. `netbox_custom_objects`) triggering multiple `register_model_view` calls
  during Plugin Reloader's `ready()` cycle.

## [4.5.0.1] - 2026-01-22

### Added
- Initial release for NetBox 4.5.x compatibility.
- Dynamic registration of missed plugin models.
- Refresh of CustomFieldForm and TagForm `object_types` fields.

## [4.4.0.1] - 2025-09-01

### Changed
- Updated registry check for NetBox 4.4+ structure (`registry['models'][app_label][model_name]`).

## [0.0.2]

### Added
- Initial release, NetBox 4.2.x support.
