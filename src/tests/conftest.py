import os
import sys
from pathlib import Path

# Make `import pharos` work even without `pip install -e .`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Tests must never hit the network.
os.environ.setdefault("PHAROS_OFFLINE", "1")
