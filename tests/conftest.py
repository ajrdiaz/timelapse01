import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def example_dict():
    return json.loads((ROOT / "examples" / "bunker_gamer.json").read_text(encoding="utf-8"))
