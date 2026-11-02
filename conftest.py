import sys
import pathlib

# Ensure the project root is on sys.path so that imports like `app` resolve correctly during pytest collection.
_project_root = pathlib.Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
