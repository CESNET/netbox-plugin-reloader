# Changelog

## [4.5.4.1] - 2026-03-17

### Fixed
- Added defensive deduplication of `registry['views']` entries after model registration.
  This prevents duplicate Journal/Changelog tabs caused by dynamic model plugins
  (e.g. `netbox_custom_objects`) triggering multiple `register_model_view` calls
  during Plugin Reloader's `ready()` cycle.
- Changed deduplication strategy from "first wins" to "last wins" to ensure the most
  recent view registration is kept when dynamic model plugins re-register views.

### Added
- Unit tests for all core methods (deduplication, model registration, plugin iteration,
  form field refresh).

## [4.5.0.1] - 2026-01-22

### Added
- Initial release for NetBox 4.5.x compatibility.
- Dynamic registration of missed plugin models.
- Refresh of CustomFieldForm and TagForm `object_types` fields.

## [4.4.0.1] - 2025-09-01

### Changed
- Updated registry check for NetBox 4.4+ structure (`registry['models'][app_label][model_name]`).
- Removed `FEATURES_MAP` fallback in favor of direct registry lookup.

## [0.0.2] - 2025-02-26

### Added
- Initial release, NetBox 4.2.x support.
