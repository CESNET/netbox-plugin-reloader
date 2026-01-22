# NetBox Plugin Reloader

A NetBox plugin that dynamically reloads plugins without requiring a server restart. This plugin ensures that NetBox properly registers all plugin models and form fields that might have been missed during the initial application startup.

## Features

- Dynamically registers plugin models that were missed during server startup
- Refreshes custom field form definitions to include newly registered models
- Refreshes tag form definitions to include newly registered models
- Helps solve integration issues between NetBox and other plugins
- No configuration required - works out of the box

## Compatibility Matrix

| NetBox Version | Plugin Version |
|----------------|---------------|
| 4.2.x          | 0.0.2         |
| 4.3.x          | 4.3.x         |
| 4.4.x          | 4.4.x         |
| 4.5.x          | 4.5.x         |


**Version Format**: X.X.Y where X.X = NetBox version (e.g., 4.3) and Y = plugin version increment

## Installation

The plugin is available as a Python package on PyPI and can be installed with pip:

```bash
pip install netbox-plugin-reloader
```

To enable the plugin, add it to the `PLUGINS` list in your `configuration.py`:

```python
PLUGINS = [
    'other_plugin',
    'another_plugin',
    'netbox_plugin_reloader',  # Always add netbox_plugin_reloader last!
]
```

After installing the plugin:

1. Restart NetBox:
   ```bash
   sudo systemctl restart netbox
   ```

2. Ensure that `netbox-plugin-reloader` is included in your `local_requirements.txt` if you're using the official NetBox installation method.

For more details, see the [NetBox Documentation](https://docs.netbox.dev/en/stable/plugins/).

## Important Note

**netbox_plugin_reloader must be the last item in your PLUGINS list!** This ensures that it can properly detect and register all models from other plugins that may have been missed during the initial startup process.

## How It Works

When NetBox starts, Plugin Reloader:

1. Scans all enabled plugins for models that aren't properly registered in NetBox's feature registry
2. Registers any missed models with NetBox's registration system
3. Refreshes custom field form definitions to ensure they include all registered models
4. Refreshes tag form definitions to ensure they include all registered models

This helps resolve issues where plugins might not fully integrate with NetBox due to load order problems without requiring a server restart. The reloader specifically updates custom field choices and tag choices to include newly registered plugin models.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Jan Krupa <jan.krupa@cesnet.cz>

## Links
- Based on https://github.com/netbox-community/netbox/discussions/17836