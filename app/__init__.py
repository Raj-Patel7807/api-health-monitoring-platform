import sys
import pathlib

# Resolve project root and the backend/app directory.
_project_root = pathlib.Path(__file__).resolve().parent.parent
_backend_app_path = _project_root / "backend" / "app"

if not _backend_app_path.is_dir():
    raise ImportError("backend/app package not found; cannot set up app package alias.")

# Ensure the project root is on sys.path for absolute imports.
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Direct this package's submodule search to the backend/app directory.
__path__ = [str(_backend_app_path)]
