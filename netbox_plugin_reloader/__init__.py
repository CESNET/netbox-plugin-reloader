"""
NetBox Plugin Reloader - Dynamically reload NetBox plugins without server restart.
"""

from netbox.plugins import PluginConfig

from netbox_plugin_reloader.version import __version__


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
    min_version = "4.5.0"
    max_version = "4.5.99"

    def ready(self):
        """
        Initializes the plugin when the Django application loads.

        Registers any plugin models missed during startup and refreshes form fields to include newly registered models for custom fields and tags.
        """
        super().ready()

        from core.models.object_types import ObjectType
        from django.apps.registry import apps
        from django.conf import settings
        from django.utils.translation import gettext_lazy as _
        from extras.forms.model_forms import CustomFieldForm, TagForm
        from netbox.models.features import register_models
        from netbox.registry import registry
        from utilities.forms.fields import ContentTypeMultipleChoiceField

        # Register missing plugin models
        self._register_missing_plugin_models(settings.PLUGINS, apps, registry, register_models)

        # Refresh form fields
        self._refresh_form_field(CustomFieldForm, "custom_fields", ObjectType, ContentTypeMultipleChoiceField, _)
        self._refresh_form_field(TagForm, "tags", ObjectType, ContentTypeMultipleChoiceField, _)

    def _register_missing_plugin_models(self, plugin_list, app_registry, netbox_registry, model_register_function):
        """
        Registers plugin models that were not registered during initial application startup.

        Iterates through the provided list of plugin names, identifies models that are missing from the NetBox feature registry, and registers them using the supplied registration function. Prints errors encountered during processing and reports the number of models registered if any were missed.
        """
        unregistered_models = []

        for plugin_name in plugin_list:
            try:
                plugin_app_config = app_registry.get_app_config(plugin_name)
                app_label = plugin_app_config.label

                for model_class in plugin_app_config.get_models():
                    model_name = model_class._meta.model_name
                    if not self._is_model_registered(app_label, model_name, netbox_registry):
                        unregistered_models.append(model_class)

            except Exception as e:
                print(f"Error processing plugin {plugin_name}: {e}")

        if unregistered_models:
            model_register_function(*unregistered_models)
            print(f"Plugin Reloader: Registered {len(unregistered_models)} previously missed models")

    def _is_model_registered(self, app_label, model_name, registry):
        """
        Determines whether a model is registered in the NetBox registry.

        In NetBox 4.4+, we check if the model is in the registry['models'] structure.

        Returns:
            True if the specified model is present in the registry; otherwise, False.
        """
        return app_label in registry["models"] and model_name in registry["models"][app_label]

    def _refresh_form_field(self, form_class, feature_name, object_type_class, field_class, translation_function):
        """
        Updates a form class's object_types field to reflect models supporting a specific NetBox feature.

        Args:
            form_class: The form class to update.
            feature_name: The NetBox feature name (e.g., "custom_fields", "tags").
            object_type_class: The ContentType-like class used to query object types.
            field_class: The form field class to instantiate.
            translation_function: Function used to translate field labels and help texts.
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
