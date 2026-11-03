import sys, pathlib
# Ensure project root on sys.path
project_root = pathlib.Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
import app
print('app __path__:', list(app.__path__))
