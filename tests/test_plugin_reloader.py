"""
Unit tests for NetBox Plugin Reloader.

All tests use mocks to avoid requiring Django/NetBox runtime dependencies.
The methods under test accept their dependencies as parameters, making them
testable in isolation.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# We can't import the real class (requires Django), so we test methods directly
# by constructing a minimal instance that bypasses Django's AppConfig machinery.
import importlib
import sys


def _make_instance():
    """Create a NetboxPluginReloaderConfig-like instance with only the methods we need."""

    # Avoid importing the real module (it triggers Django imports at module level).
    # Instead, read the source and extract the class methods we want to test.
    # We'll mock the base class and re-import.
    mock_plugin_config = type("PluginConfig", (), {"name": "", "ready": lambda self: None})
    fake_netbox_plugins = type(sys)("netbox.plugins")
    fake_netbox_plugins.PluginConfig = mock_plugin_config

    fake_version = type(sys)("netbox_plugin_reloader.version")
    fake_version.__version__ = "0.0.0-test"

    with patch.dict(
        sys.modules,
        {
            "netbox.plugins": fake_netbox_plugins,
            "netbox": type(sys)("netbox"),
            "netbox_plugin_reloader.version": fake_version,
        },
    ):
        # Force re-import so the module picks up our fakes
        if "netbox_plugin_reloader" in sys.modules:
            del sys.modules["netbox_plugin_reloader"]
        mod = importlib.import_module("netbox_plugin_reloader")

    return mod.NetboxPluginReloaderConfig()


INSTANCE = _make_instance()


# ---------------------------------------------------------------------------
# _deduplicate_view_registrations
# ---------------------------------------------------------------------------
class TestDeduplicateViewRegistrations(unittest.TestCase):
    def _call(self, plugin_configs, registry_dict):
        INSTANCE._deduplicate_view_registrations(plugin_configs, registry_dict)

    def _make_configs(self, app_label):
        return [("test_plugin", None, app_label)]

    def test_keeps_last_occurrence(self):
        """When a view name appears twice, the last occurrence wins."""
        views = {
            "myplugin": {
                "mymodel": [
                    {"name": "journal", "path": "old"},
                    {"name": "changelog", "path": "cl"},
                    {"name": "journal", "path": "new"},
                ]
            }
        }
        registry = {"views": views}
        self._call(self._make_configs("myplugin"), registry)

        result = views["myplugin"]["mymodel"]
        names = [e["name"] for e in result]
        self.assertEqual(names, ["changelog", "journal"])
        # The kept "journal" should be the LAST one (path="new")
        journal_entry = [e for e in result if e["name"] == "journal"][0]
        self.assertEqual(journal_entry["path"], "new")

    def test_nameless_views_always_preserved(self):
        """Views without a 'name' key are never deduplicated."""
        views = {
            "myplugin": {
                "mymodel": [
                    {"name": "journal"},
                    {"path": "/a"},
                    {"path": "/b"},
                    {"name": "journal"},
                ]
            }
        }
        registry = {"views": views}
        self._call(self._make_configs("myplugin"), registry)

        result = views["myplugin"]["mymodel"]
        nameless = [e for e in result if "name" not in e]
        self.assertEqual(len(nameless), 2)

    def test_no_duplicates_no_changes(self):
        """If there are no duplicates, the list is unchanged."""
        original = [{"name": "journal"}, {"name": "changelog"}]
        views = {"myplugin": {"mymodel": list(original)}}
        registry = {"views": views}
        self._call(self._make_configs("myplugin"), registry)

        self.assertEqual(views["myplugin"]["mymodel"], original)

    def test_empty_view_list(self):
        """Empty view list doesn't crash."""
        views = {"myplugin": {"mymodel": []}}
        registry = {"views": views}
        self._call(self._make_configs("myplugin"), registry)
        self.assertEqual(views["myplugin"]["mymodel"], [])

    def test_app_label_not_in_views(self):
        """Plugin whose app_label isn't in views registry is skipped."""
        views = {}
        registry = {"views": views}
        # Should not raise
        self._call(self._make_configs("nonexistent"), registry)

    def test_mixed_duplicates_unique_nameless(self):
        """Mixed scenario: duplicates, unique views, and nameless entries."""
        views = {
            "myplugin": {
                "mymodel": [
                    {"name": "journal", "v": 1},
                    {"name": "changelog", "v": 1},
                    {"path": "/nameless"},
                    {"name": "journal", "v": 2},
                    {"name": "contacts", "v": 1},
                    {"name": "changelog", "v": 2},
                ]
            }
        }
        registry = {"views": views}
        self._call(self._make_configs("myplugin"), registry)

        result = views["myplugin"]["mymodel"]
        named = [e for e in result if "name" in e]
        nameless = [e for e in result if "name" not in e]

        # All unique names kept, nameless preserved
        self.assertEqual(len(nameless), 1)
        names = [e["name"] for e in named]
        self.assertEqual(sorted(names), ["changelog", "contacts", "journal"])

        # Last wins: journal v=2, changelog v=2, contacts v=1
        by_name = {e["name"]: e for e in named}
        self.assertEqual(by_name["journal"]["v"], 2)
        self.assertEqual(by_name["changelog"]["v"], 2)
        self.assertEqual(by_name["contacts"]["v"], 1)


# ---------------------------------------------------------------------------
# _register_missing_plugin_models
# ---------------------------------------------------------------------------
class TestRegisterMissingPluginModels(unittest.TestCase):
    def _make_model(self, app_label, model_name):
        meta = SimpleNamespace(model_name=model_name)
        return SimpleNamespace(_meta=meta, _app_label=app_label)

    def _make_app_config(self, models):
        config = MagicMock()
        config.get_models.return_value = models
        config.label = "test_app"
        return config

    def test_registers_unregistered_models(self):
        model = self._make_model("test_app", "mymodel")
        config = self._make_app_config([model])
        plugin_configs = [("test_plugin", config, "test_app")]
        registry = {"models": {}}
        register_fn = MagicMock()

        result = INSTANCE._register_missing_plugin_models(plugin_configs, registry, register_fn)

        self.assertTrue(result)
        register_fn.assert_called_once_with(model)

    def test_skips_registered_models(self):
        model = self._make_model("test_app", "mymodel")
        config = self._make_app_config([model])
        plugin_configs = [("test_plugin", config, "test_app")]
        registry = {"models": {"test_app": {"mymodel": True}}}
        register_fn = MagicMock()

        result = INSTANCE._register_missing_plugin_models(plugin_configs, registry, register_fn)

        self.assertFalse(result)
        register_fn.assert_not_called()

    def test_broken_plugin_skipped_others_continue(self):
        good_model = self._make_model("good_app", "goodmodel")

        broken_config = MagicMock()
        broken_config.get_models.side_effect = RuntimeError("broken")
        broken_config.label = "broken_app"

        good_config = self._make_app_config([good_model])
        good_config.label = "good_app"

        plugin_configs = [
            ("broken_plugin", broken_config, "broken_app"),
            ("good_plugin", good_config, "good_app"),
        ]
        registry = {"models": {}}
        register_fn = MagicMock()

        result = INSTANCE._register_missing_plugin_models(plugin_configs, registry, register_fn)

        self.assertTrue(result)
        register_fn.assert_called_once_with(good_model)

    def test_returns_false_when_nothing_to_register(self):
        config = self._make_app_config([])
        plugin_configs = [("test_plugin", config, "test_app")]
        registry = {"models": {}}
        register_fn = MagicMock()

        result = INSTANCE._register_missing_plugin_models(plugin_configs, registry, register_fn)

        self.assertFalse(result)
        register_fn.assert_not_called()


# ---------------------------------------------------------------------------
# _is_model_registered
# ---------------------------------------------------------------------------
class TestIsModelRegistered(unittest.TestCase):
    def test_model_present(self):
        registry = {"models": {"myapp": {"mymodel": True}}}
        self.assertTrue(INSTANCE._is_model_registered("myapp", "mymodel", registry))

    def test_model_absent(self):
        registry = {"models": {"myapp": {"othermodel": True}}}
        self.assertFalse(INSTANCE._is_model_registered("myapp", "mymodel", registry))

    def test_app_label_absent(self):
        registry = {"models": {}}
        self.assertFalse(INSTANCE._is_model_registered("myapp", "mymodel", registry))


# ---------------------------------------------------------------------------
# _iter_plugin_configs
# ---------------------------------------------------------------------------
class TestIterPluginConfigs(unittest.TestCase):
    def test_valid_plugins(self):
        app_config = MagicMock()
        app_config.label = "myplugin"
        app_registry = MagicMock()
        app_registry.get_app_config.return_value = app_config

        result = list(INSTANCE._iter_plugin_configs(["myplugin"], app_registry))

        self.assertEqual(result, [("myplugin", app_config, "myplugin")])

    def test_missing_plugin_skipped(self):
        app_registry = MagicMock()
        app_registry.get_app_config.side_effect = LookupError("not found")

        result = list(INSTANCE._iter_plugin_configs(["missing"], app_registry))

        self.assertEqual(result, [])

    def test_mix_valid_and_invalid(self):
        good_config = MagicMock()
        good_config.label = "good"

        def side_effect(name):
            if name == "good":
                return good_config
            raise LookupError(f"{name} not found")

        app_registry = MagicMock()
        app_registry.get_app_config.side_effect = side_effect

        result = list(INSTANCE._iter_plugin_configs(["bad", "good", "also_bad"], app_registry))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], ("good", good_config, "good"))


# ---------------------------------------------------------------------------
# _refresh_form_field
# ---------------------------------------------------------------------------
class TestRefreshFormField(unittest.TestCase):
    def test_replaces_object_types_field(self):
        form_class = type("FakeForm", (), {"base_fields": {"object_types": "old"}})
        object_type_class = MagicMock()
        object_type_class.objects.with_feature.return_value = ["ct1", "ct2"]

        captured = {}

        def fake_field_class(**kwargs):
            captured.update(kwargs)
            return "new_field"

        INSTANCE._refresh_form_field(form_class, "custom_fields", object_type_class, fake_field_class, str)

        self.assertEqual(form_class.base_fields["object_types"], "new_field")
        self.assertEqual(captured["queryset"], ["ct1", "ct2"])


if __name__ == "__main__":
    unittest.main()
