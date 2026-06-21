import importlib
import inspect
import pkgutil

from app.plugins.base import EnvForagePlugin


def load_plugins(package_name: str) -> list[type[EnvForagePlugin]]:
    """Dynamically discover and load plugin classes from a package."""
    plugins = []
    package = importlib.import_module(package_name)
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        full_module_name = f"{package_name}.{module_name}"
        module = importlib.import_module(full_module_name)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, EnvForagePlugin) and obj is not EnvForagePlugin:
                plugins.append(obj)
    return plugins
