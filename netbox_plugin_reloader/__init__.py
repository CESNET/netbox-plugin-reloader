"""
NetBox Plugin Reloader - Dynamically reload NetBox plugins without server restart.
"""

import logging

from netbox.plugins import PluginConfig

from netbox_plugin_reloader.version import __version__

logger = logging.getLogger(__name__)


class NetboxPluginReloaderConfig(PluginConfig):
    """
    Configuration for the Plugin Reloader NetBox plugin.

    This plugin allows NetBox to dynamically reload plugin models and form fields
    that might have been missed during the initial application startup.
    """

    name = "netbox_plugin_reloader"
    verbose_name = "Plugin Reloader"
    description = "Dynamically reload NetBox plugins without server restart"
    version = __version__
    base_url = "netbox-plugin-reloader"
    min_version = "4.7.0"
    max_version = "4.7.99"

    def ready(self):
        """
        Initializes the plugin when the Django application loads.

        Registers any plugin models missed during startup and refreshes form fields to include newly registered models for custom fields and tags.
        """
        super().ready()

        from core.models.object_types import ObjectType
        from django.apps.registry import apps
        from django.utils.translation import gettext_lazy as _
        from extras.forms.model_forms import CustomFieldForm, TagForm
        from netbox.models.features import (
            ChangeLoggingMixin,
            ContactsMixin,
            ImageAttachmentsMixin,
            JobsMixin,
            JournalingMixin,
            SyncedDataMixin,
            register_models,
        )
        from netbox.registry import registry
        from utilities.forms.fields import ContentTypeMultipleChoiceField

        # Only plugins NetBox actually loaded (those failing min/max_version are skipped by NetBox 4.7).
        # Materialized because plugin_configs is iterated by both registration and deduplication
        plugin_configs = list(self._iter_plugin_configs(registry["plugins"]["installed"], apps))

        # Mirrors the feature views register_models() adds (netbox/models/features.py)
        feature_views = (
            (ContactsMixin, "contacts"),
            (JournalingMixin, "journal"),
            (ChangeLoggingMixin, "changelog"),
            (JobsMixin, "jobs"),
            (ImageAttachmentsMixin, "image-attachments"),
            (SyncedDataMixin, "sync"),
        )

        # Register missing plugin models
        models_registered = self._register_missing_plugin_models(
            plugin_configs, registry, register_models, feature_views
        )

        # Deduplicate view registrations that may have accumulated during dynamic model registration
        self._deduplicate_view_registrations(plugin_configs, registry)

        # Refresh form fields only if new models were registered
        if models_registered:
            self._refresh_form_field(CustomFieldForm, "custom_fields", ObjectType, ContentTypeMultipleChoiceField, _)
            self._refresh_form_field(TagForm, "tags", ObjectType, ContentTypeMultipleChoiceField, _)

    def _iter_plugin_configs(self, plugin_list, app_registry):
        """
        Yields (plugin_name, app_config, app_label) tuples for each plugin,
        logging and skipping any that fail to resolve.
        """
        for plugin_name in plugin_list:
            try:
                app_config = app_registry.get_app_config(plugin_name)
                yield plugin_name, app_config, app_config.label
            except LookupError:
                logger.exception("Error resolving plugin %s", plugin_name)

    def _register_missing_plugin_models(self, plugin_configs, netbox_registry, model_register_function, feature_views):
        """
        Registers plugin models that were not registered during initial application startup.

        Returns True if any models were registered, False otherwise.
        """
        unregistered_models = []

        for plugin_name, app_config, app_label in plugin_configs:
            try:
                for model_class in app_config.get_models():
                    model_name = model_class._meta.model_name
                    if not self._is_model_registered(model_class, app_label, model_name, netbox_registry, feature_views):
                        unregistered_models.append(model_class)
            except Exception:
                logger.exception("Error processing models for plugin %s", plugin_name)

        if unregistered_models:
            model_register_function(*unregistered_models)
            logger.info("Registered %d previously missed models", len(unregistered_models))
            return True
        return False

    def _deduplicate_view_registrations(self, plugin_configs, netbox_registry):
        """
        Removes duplicate view registrations for plugin models from the NetBox registry.

        When dynamic models are registered, register_model_view may be called multiple
        times for the same model/view combination, resulting in duplicate tabs (e.g.
        Journal, Changelog appearing more than once). This method deduplicates entries
        in registry['views'] for all plugin app labels, keeping only the last occurrence
        of each view name per model (last wins ensures the most recent registration is kept).
        """
        views_registry = netbox_registry.get("views", {})

        for plugin_name, app_config, app_label in plugin_configs:
            if app_label not in views_registry:
                continue

            for model_name, view_list in list(views_registry[app_label].items()):
                seen = set()
                reversed_deduped = []
                for entry in reversed(view_list):
                    key = entry.get("name")
                    if key is None:
                        reversed_deduped.append(entry)
                        continue
                    if key not in seen:
                        seen.add(key)
                        reversed_deduped.append(entry)
                deduped = list(reversed(reversed_deduped))
                removed = len(view_list) - len(deduped)
                if removed:
                    logger.debug("Removed %d duplicate view entries for %s.%s", removed, app_label, model_name)
                views_registry[app_label][model_name] = deduped

    def _is_model_registered(self, model_class, app_label, model_name, netbox_registry, feature_views):
        """
        Determines whether register_models() has already run for a model.

        NetBox 4.7 removed registry['models'], so registration is inferred from registry['views']:
        a model is registered if every feature view register_models() would add for it (based on
        the feature mixins it subclasses) is already present by name. Models with no applicable
        feature mixin have nothing to register and count as registered.
        """
        views = netbox_registry.get("views", {}).get(app_label, {}).get(model_name, [])
        present = {view.get("name") for view in views}
        return all(name in present for mixin, name in feature_views if issubclass(model_class, mixin))

    def _refresh_form_field(self, form_class, feature_name, object_type_class, field_class, translation_function):
        """
        Updates a form class's object_types field to reflect models supporting a specific NetBox feature.
        """
        field_labels = {
            "custom_fields": ("Object types", "The type(s) of object that have this custom field"),
            "tags": ("Object types", "The type(s) of object that can have this tag"),
        }

        label, help_text = field_labels[feature_name]

        object_types_field = field_class(
            label=translation_function(label),
            queryset=object_type_class.objects.with_feature(feature_name),
            help_text=translation_function(help_text),
        )

        form_class.base_fields["object_types"] = object_types_field


# Plugin configuration object
config = NetboxPluginReloaderConfig
