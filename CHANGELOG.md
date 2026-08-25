# Changelog

## [4.6.0.2] - 2026-08-25

### Fixed
- Avoid NetBox 4.6 FutureWarning on the deprecated `models` registry key by
  accessing the underlying dict directly (same pattern NetBox core uses
  internally). The 4.7 removal of the key is out of scope; version pins
  already exclude 4.7.

## [4.6.0.1] - 2026-05-11

### Changed
- Updated NetBox version pins to `4.6.0`–`4.6.99` and Django classifier to `6.0` for NetBox 4.6.x compatibility.
- No code logic changes: all referenced NetBox APIs (`registry['models']`, `register_models`, `CustomFieldForm`/`TagForm`, `ObjectType.objects.with_feature`) are unchanged in 4.6.

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
