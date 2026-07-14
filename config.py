import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Secret/session
BODA_SECRET_KEY = os.environ.get("BODA_SECRET_KEY", "")
BODA_ADMIN_PASSWORD = os.environ.get("BODA_ADMIN_PASSWORD", "clau2026")

# Wedding config
BODA_NOVIA = os.environ.get("BODA_NOVIA", "Madro")
BODA_NOVIO = os.environ.get("BODA_NOVIO", "David")
BODA_FECHA = os.environ.get("BODA_FECHA", "18 de julio de 2026")
BODA_LUGAR = os.environ.get("BODA_LUGAR", "")

# Missions source (JSON file in repo)
MISSIONS_PATH = BASE_DIR / os.environ.get("MISSIONS_PATH", "missions.json")

# Firebase
# You will need to configure either:
#  - FIREBASE_SERVICE_ACCOUNT_PATH (recommended for deployment)
#  - or FIREBASE_SERVICE_ACCOUNT_JSON (JSON text)
FIREBASE_SERVICE_ACCOUNT_PATH = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH", "")
FIREBASE_SERVICE_ACCOUNT_JSON = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")

FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "")
FIREBASE_STORAGE_BUCKET = os.environ.get("FIREBASE_STORAGE_BUCKET", "")

USE_FIREBASE = bool(FIREBASE_PROJECT_ID and FIREBASE_STORAGE_BUCKET and (FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON))

