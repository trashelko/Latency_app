from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.absolute()
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
MAPS_DIR = BASE_DIR / "maps"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
MAPS_DIR.mkdir(parents=True, exist_ok=True)

# Default settings
DEFAULT_CUSTOMER = "Zim"
LATENCY_THRESHOLD_HOURS = 24