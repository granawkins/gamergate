import sys
from pathlib import Path

# Make sure the backend directory is in the path
backend_dir = Path(__file__).parent.absolute()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
