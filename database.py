import json
import os
import random
import hashlib
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import MISSIONS_PATH


def _load_missions() -> list[dict]:
    if not MISSIONS_PATH.exists():
        raise FileNotFoundError(f"No existe missions.json en: {MISSIONS_PATH}")
    missions = json.loads(MISSIONS_PATH.read_text(encoding="utf-8"))
    if not isinstance(missions, list) or not missions:
        raise ValueError("missions.json debe ser una lista con misiones")
    if len(missions) < 3:
        raise ValueError("Se necesitan al menos 3 misiones en missions.json")
    return missions


@dataclass
class GuestRow:
    id: str
    nombre: str
    apellido1: str
    apellido2: str


class Database:
    def init_db(self) -> None:
        raise NotImplementedError

    def get_or_create_guest(self, nombre: str, apellido1: str, apellido2: str) -> tuple[dict, bool]:
        raise NotImplementedError

    def get_guest_missions(self, guest_id: str) -> list[dict]:
        raise NotImplementedError

    def upload_photo_file(self, guest_id: str, mission_row_id: str, filename: str, file_bytes: bytes) -> str:
        """Devuelve photo_url (usaremos URL firmada o bien string de Storage)."""
        raise NotImplementedError

    def save_mission_photo(self, mission_row_id: str, guest_id: str, photo_url: str) -> None:
        raise NotImplementedError

    def get_all_photos_for_novios(self) -> list[dict]:
        raise NotImplementedError

    def get_stats_for_novios(self) -> dict:
        raise NotImplementedError


class SQLiteBackend(Database):
    # No se implementa: el objetivo es operar con Firebase/Firestore.
    def __init__(self) -> None:
        raise RuntimeError("Este proyecto está configurado para Firebase. No hay backend local.")


class FirestoreFirebaseBackend(Database):
    def __init__(self, *, project_id: str, bucket: str, credentials: Any) -> None:
        # Late imports para no romper si no está instalado.
        import firebase_admin
        from firebase_admin import credentials as fb_credentials
        from firebase_admin import firestore, storage

        if not firebase_admin._apps:
            if isinstance(credentials, dict):
                cred = fb_credentials.Certificate(credentials)
            else:
                # string JSON text
                cred = fb_credentials.Certificate(json.loads(credentials))
            firebase_admin.initialize_app(cred, {"storageBucket": bucket})

        self.db = firestore.client()
        self.storage = storage.bucket(bucket)
        self.bucket = bucket

    @staticmethod
    def _normalize(value: str) -> str:
        return unicodedata.normalize("NFKC", value).strip().casefold()

    def init_db(self) -> None:
        # Firestore no requiere migraciones en este flujo.
        return

    def get_or_create_guest(self, nombre: str, apellido1: str, apellido2: str) -> tuple[dict, bool]:
        nombre_norm = self._normalize(nombre)
        a1_norm = self._normalize(apellido1)
        a2_norm = self._normalize(apellido2)

        guests_ref = self.db.collection("guests")
        identity = "|".join((nombre_norm, a1_norm, a2_norm))
        guest_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
        guest_ref = guests_ref.document(guest_id)
        existing = guest_ref.get()
        if existing.exists:
            data = existing.to_dict() or {}
            data["id"] = guest_id
            return data, False

        # Create new guest
        missions = _load_missions()
        selected = random.sample(missions, 3)

        guest_payload = {
            "id": guest_id,
            "nombre": nombre.strip(),
            "apellido1": apellido1.strip(),
            "apellido2": apellido2.strip(),
            "nombre_norm": nombre_norm,
            "apellido1_norm": a1_norm,
            "apellido2_norm": a2_norm,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        guest_ref.set(guest_payload)

        # Write 3 mission rows
        missions_col = self.db.collection("guest_missions")
        created_mission_ids = []
        for position, mission in enumerate(selected, start=1):
            mission_text = mission.get("text") or mission.get("mission_text") or mission.get("mission")
            if not mission_text:
                raise ValueError("Cada misión en missions.json debe tener {text: ...}")
            mission_doc = missions_col.document()
            created_mission_ids.append(mission_doc.id)
            mission_doc.set(
                {
                    "id": mission_doc.id,
                    "guest_id": guest_id,
                    "position": position,
                    "mission_text": mission_text,
                    "photo_url": None,
                    "photo_path": None,
                    "completed_at": None,
                    "created_at": firestore.SERVER_TIMESTAMP,
                }
            )

        data = dict(guest_payload)
        data["id"] = guest_id
        return data, True

    def get_guest_missions(self, guest_id: str) -> list[dict]:
        missions_col = self.db.collection("guest_missions")
        query = missions_col.where("guest_id", "==", guest_id).order_by("position")

        results: list[dict] = []
        for doc in query.stream():
            d = doc.to_dict() or {}
            d["id"] = doc.id
            results.append(
                {
                    "id": d["id"],
                    "position": d.get("position"),
                    "mission_text": d.get("mission_text"),
                    "photo_url": d.get("photo_url"),
                    "completed_at": d.get("completed_at"),
                }
            )
        return results

    def upload_photo_file(self, guest_id: str, mission_row_id: str, filename: str, file_bytes: bytes) -> str:
        # Storage path
        # Use extension from filename; if none, default to .jpg
        ext = os.path.splitext(filename)[1].lower() if os.path.splitext(filename)[1] else ".jpg"
        safe_name = f"{guest_id}_{mission_row_id}_{int(datetime.now(tz=timezone.utc).timestamp())}{ext}"
        path = f"{guest_id}/{mission_row_id}/{safe_name}"

        blob = self.storage.blob(path)
        content_type = "image/jpeg" if ext in {".jpg", ".jpeg"} else f"image/{ext.lstrip('.')}"
        blob.upload_from_string(file_bytes, content_type=content_type)

        # Generate signed URL (long-lived)
        # firebase_admin.storage.Blob ofrece generate_signed_url
        try:
            url = blob.generate_signed_url(expiration=3600 * 24 * 365)  # 1 año aprox
        except Exception:
            # Fallback: make it public URL-ish (requires bucket public). Better to still return something.
            url = blob.public_url
        return url

    def save_mission_photo(self, mission_row_id: str, guest_id: str, photo_url: str) -> None:
        doc_ref = self.db.collection("guest_missions").document(mission_row_id)
        snapshot = doc_ref.get()
        if not snapshot.exists or (snapshot.to_dict() or {}).get("guest_id") != guest_id:
            raise PermissionError("Esta misión no pertenece al invitado.")
        doc_ref.update(
            {
                "guest_id": guest_id,
                "photo_url": photo_url,
                "completed_at": firestore.SERVER_TIMESTAMP,
            }
        )

    def get_all_photos_for_novios(self) -> list[dict]:
        # Get missions with photo_url not null and join with guest
        missions_col = self.db.collection("guest_missions")
        # Firestore query for != null can be tricky; we do: photo_url > ''
        query = missions_col.where("photo_url", "!=", None).order_by("completed_at", direction="DESC")

        photos = []
        for doc in query.stream():
            d = doc.to_dict() or {}
            guest_id = d.get("guest_id")
            guest_snap = self.db.collection("guests").document(guest_id).get()
            guest_data = guest_snap.to_dict() or {}

            photos.append(
                {
                    "id": doc.id,
                    "mission_text": d.get("mission_text"),
                    "photo_url": d.get("photo_url"),
                    "completed_at": d.get("completed_at"),
                    "nombre": guest_data.get("nombre", ""),
                    "apellido1": guest_data.get("apellido1", ""),
                    "apellido2": guest_data.get("apellido2", ""),
                    "display_url": d.get("photo_url"),
                }
            )

        return photos

    def get_stats_for_novios(self) -> dict:
        guests = self.db.collection("guests").get()
        missions = self.db.collection("guest_missions").where("photo_url", "!=", None).get()
        return {"guests": len(list(guests)), "photos": len(list(missions))}


# ---- Public API used by app.py ----
from config import USE_FIREBASE, FIREBASE_PROJECT_ID, FIREBASE_STORAGE_BUCKET, FIREBASE_SERVICE_ACCOUNT_PATH, FIREBASE_SERVICE_ACCOUNT_JSON


_backend: Database | None = None


def _load_credentials() -> Any:
    if FIREBASE_SERVICE_ACCOUNT_JSON.strip():
        return FIREBASE_SERVICE_ACCOUNT_JSON
    if FIREBASE_SERVICE_ACCOUNT_PATH.strip():
        # Load JSON file contents
        content = Path(FIREBASE_SERVICE_ACCOUNT_PATH).read_text(encoding="utf-8")
        return content
    return ""


def get_backend() -> Database:
    global _backend
    if _backend is not None:
        return _backend

    if USE_FIREBASE:
        creds = _load_credentials()
        if not creds:
            raise RuntimeError(
                "USE_FIREBASE=True pero faltan credenciales. Define FIREBASE_SERVICE_ACCOUNT_PATH o FIREBASE_SERVICE_ACCOUNT_JSON."
            )

        _backend = FirestoreFirebaseBackend(
            project_id=FIREBASE_PROJECT_ID,
            bucket=FIREBASE_STORAGE_BUCKET,
            credentials=creds,
        )
        return _backend

    # Local mode disabled by default; make it explicit.
    raise RuntimeError(
        "Falta configuración de Firebase (USE_FIREBASE=False). Define variables de entorno para ejecutar en la nube."
    )


def init_db() -> None:
    get_backend().init_db()


def get_or_create_guest(nombre: str, apellido1: str, apellido2: str):
    return get_backend().get_or_create_guest(nombre, apellido1, apellido2)


def get_guest_missions(guest_id: str):
    return get_backend().get_guest_missions(guest_id)


def upload_photo_file(guest_id: str, mission_row_id: str, filename: str, file_bytes: bytes) -> str:
    return get_backend().upload_photo_file(guest_id=guest_id, mission_row_id=mission_row_id, filename=filename, file_bytes=file_bytes)


def save_mission_photo(mission_row_id: str, guest_id: str, photo_url: str) -> None:
    return get_backend().save_mission_photo(mission_row_id=mission_row_id, guest_id=guest_id, photo_url=photo_url)


def get_all_photos_for_novios() -> list[dict]:
    return get_backend().get_all_photos_for_novios()


def get_stats_for_novios() -> dict:
    return get_backend().get_stats_for_novios()

