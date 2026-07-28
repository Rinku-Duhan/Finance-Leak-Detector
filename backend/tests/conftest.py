"""
Shared pytest fixtures. Runs the synthetic data generator once per test
session so every test file works against real, consistent data -- the
same ground_truth.json used throughout development.
"""

import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(BACKEND_ROOT / "app" / "data_gen"))

OUTPUT_DIR = BACKEND_ROOT / "app" / "data_gen" / "output"


@pytest.fixture(scope="session", autouse=True)
def generate_synthetic_data():
    """Runs once before the whole test session. Regenerates the synthetic
    CSVs + ground_truth.json fresh (they're gitignored, so CI won't have
    them checked out -- this recreates them deterministically thanks to
    the fixed random seed)."""
    import generate_data
    generate_data.main()
    yield


@pytest.fixture(scope="session")
def ground_truth():
    with open(OUTPUT_DIR / "ground_truth.json") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def synthetic_csv_paths():
    return {i: OUTPUT_DIR / f"user_{i}_transactions.csv" for i in range(1, 9)}