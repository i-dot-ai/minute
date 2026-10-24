import importlib
import inspect
import pkgutil

from .adapter import TranscriptionAdapter

package_path = __path__
package_name = __name__

adapters = {}
# Walk through all modules in the package and subpackages
for _, modname, _ in pkgutil.walk_packages(package_path, package_name + "."):
    # Import the module
    module = importlib.import_module(modname)

    # Inspect all classes in the module
    for _, obj in inspect.getmembers(module, inspect.isclass):
        # Check if it's a subclass of TranscriptionAdapter
        if obj.__module__ == modname and obj != TranscriptionAdapter and (issubclass(obj, TranscriptionAdapter)):
            adapters[obj.name] = obj
