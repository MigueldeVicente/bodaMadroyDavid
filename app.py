import hashlib
import json
import os
import random
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from firebase_admin import credentials, firestore, initialize_app, storage
from google.cloud.firestore_v1 import transactional
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

MISSIONS = [
    "Hazle una foto bonita a los novios.",
    "Haz una foto en el bus.",
    "Sube una foto con tu pintxo favorito.",
    "Hazte una foto con una persona que hayas conocido en esta experiencia.",
    "Sube una foto del brindis.",
    "Haz una foto con un grupo de 5 personas.",
    "Haz una foto en la puerta de la finca Valdespinos con tus amigos o familiares.",
    "Sube una foto bailando.",
    "Sube una foto haciendo el tonto.",
    "Pilla a los novios bailando.",
    "Haz una foto de la ceremonia.",
    "Hazte una foto con tu persona especial.",
    "Pilla desprevenidos a los novios.",
    "Hazles a los novios una foto caminando.",
    "Hazte una foto con los novios.",
    "Sube una foto del atardecer.",
    "Haz una foto cantando tu canción favorita.",
    "Saca a bailar a un desconocido y sube una foto del momento.",
    "Sube una foto con tus amigos tomando esa copa especial.",
    "Hazte una foto con el mayor número de personas que puedas.",
    "Hazte una foto graciosa con los novios.",
    "Luce tu vestido con tus amigos o familiares y sube la foto.",
    "Encuentra a David de las Heras y sácate una foto con él.",
    "Encuentra a María del Madroñal Sánchez y hazte una foto con ella.",
    "Hazte una foto con la persona que lleve el mejor vestido de la ceremonia.",
    "Sube una foto de los novios en el altar.",
    "Sube un selfie con tus seres queridos.",
    "Hazte una foto con un grupo de 3 personas.",
    "Sube tu foto favorita de la noche.",
    "Sube una foto saltando de forma aesthetic con tus amigos o familiares.",
]

ALLOWED_MIME_TYPES = {
    "image/jpeg",
}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MISSIONS_PER_GUEST = 5


def normalize(value: str) -> str:
    value = " ".join((value or "").strip().lower().split())
    value = "".join(
        char for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )
    return value


def guest_id_for(nombre: str, apellido1: str, apellido2: str) -> str:
    normalized = "|".join(map(normalize, (nombre, apellido1, apellido2)))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def initialize_firebase():
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET")
    service_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    service_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

    if service_json:
        credential = credentials.Certificate(json.loads(service_json))
    elif service_path:
        credential = credentials.Certificate(service_path)
    else:
        credential = credentials.ApplicationDefault()

    options = {}
    if project_id:
        options["projectId"] = project_id
    if bucket_name:
        options["storageBucket"] = bucket_name

    initialize_app(credential, options)
    return firestore.client()


db = initialize_firebase()
app = Flask(__name__)
app.secret_key = os.getenv("BODA_SECRET_KEY", "cambia-esta-clave-en-produccion")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


@transactional
def get_or_create_guest(transaction, guest_ref, usage_ref, guest_data):
    guest_snapshot = guest_ref.get(transaction=transaction)
    usage_snapshot = usage_ref.get(transaction=transaction)
    usage_data = usage_snapshot.to_dict() if usage_snapshot.exists else {}
    counts = usage_data.get("counts", [0] * len(MISSIONS))

    if not isinstance(counts, list) or len(counts) != len(MISSIONS):
        counts = [0] * len(MISSIONS)

    if guest_snapshot.exists:
        document = guest_snapshot.to_dict()
        selected = [
            mission_id for mission_id in document.get("mission_ids", [])
            if isinstance(mission_id, int) and 0 <= mission_id < len(MISSIONS)
        ]
        selected = list(dict.fromkeys(selected))[:MISSIONS_PER_GUEST]
        created = False
    else:
        document = {
            **guest_data,
            "mission_ids": [],
            "completed_mission_ids": [],
            "uploads": {},
            "created_at": datetime.now(timezone.utc),
        }
        selected = []
        created = True

    available = set(range(len(MISSIONS))) - set(selected)

    while len(selected) < MISSIONS_PER_GUEST and available:
        minimum = min(counts[index] for index in available)
        candidates = [index for index in available if counts[index] == minimum]
        chosen = random.choice(candidates)
        selected.append(chosen)
        counts[chosen] += 1
        available.remove(chosen)

    now = datetime.now(timezone.utc)
    document.update({"mission_ids": selected, "updated_at": now})

    transaction.set(guest_ref, document, merge=True)
    transaction.set(
        usage_ref,
        {"counts": counts, "updated_at": now},
        merge=True,
    )
    return document, created


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/misiones")
def missions_page():
    return render_template("misiones.html")


@app.post("/api/invitado")
def identify_guest():
    payload = request.get_json(silent=True) or {}
    nombre = (payload.get("nombre") or "").strip()
    apellido1 = (payload.get("apellido1") or "").strip()
    apellido2 = (payload.get("apellido2") or "").strip()

    if not nombre or not apellido1 or not apellido2:
        return jsonify(ok=False, error="Completa el nombre y los dos apellidos."), 400

    guest_id = guest_id_for(nombre, apellido1, apellido2)
    guest_ref = db.collection("guests").document(guest_id)
    usage_ref = db.collection("system").document("mission_usage")

    guest_data = {
        "nombre": nombre,
        "apellido1": apellido1,
        "apellido2": apellido2,
        "normalized_identity": {
            "nombre": normalize(nombre),
            "apellido1": normalize(apellido1),
            "apellido2": normalize(apellido2),
        },
    }

    transaction = db.transaction()
    guest, created = get_or_create_guest(
        transaction, guest_ref, usage_ref, guest_data
    )

    session["guest_id"] = guest_id
    return jsonify(ok=True, created=created, redirect="/misiones")


@app.get("/api/misiones")
def get_missions():
    guest_id = session.get("guest_id")
    if not guest_id:
        return jsonify(ok=False, error="Identifícate primero."), 401

    snapshot = db.collection("guests").document(guest_id).get()
    if not snapshot.exists:
        session.clear()
        return jsonify(ok=False, error="No encontramos tu registro."), 404

    guest = snapshot.to_dict()
    mission_ids = guest.get("mission_ids", [])
    completed = set(guest.get("completed_mission_ids", []))
    uploads = guest.get("uploads", {})

    missions = [
        {
            "id": mission_id,
            "text": MISSIONS[mission_id],
            "completed": mission_id in completed,
            "media_url": (uploads.get(str(mission_id)) or {}).get("url"),
            "media_type": (uploads.get(str(mission_id)) or {}).get("content_type"),
        }
        for mission_id in mission_ids
        if isinstance(mission_id, int) and 0 <= mission_id < len(MISSIONS)
    ]

    return jsonify(
        ok=True,
        guest={"nombre": guest.get("nombre", "")},
        missions=missions,
    )


@app.post("/api/misiones/subir")
def upload_mission():
    guest_id = session.get("guest_id")
    if not guest_id:
        return jsonify(ok=False, error="Tu sesión ha caducado. Vuelve al inicio."), 401

    file = request.files.get("archivo")
    mission_raw = request.form.get("mission_id", "")

    try:
        mission_id = int(mission_raw)
    except ValueError:
        return jsonify(ok=False, error="La misión no es válida."), 400

    if not file or not file.filename:
        return jsonify(ok=False, error="Selecciona una fotografía."), 400

    if file.mimetype not in ALLOWED_MIME_TYPES:
        return jsonify(ok=False, error="El formato del archivo no está permitido."), 400

    guest_ref = db.collection("guests").document(guest_id)
    guest_snapshot = guest_ref.get()
    if not guest_snapshot.exists:
        return jsonify(ok=False, error="No encontramos tu registro."), 404

    guest = guest_snapshot.to_dict()
    if mission_id not in guest.get("mission_ids", []):
        return jsonify(ok=False, error="Esta misión no pertenece a tu registro."), 403

    date_prefix = "20260718"
    unique_token = uuid.uuid4().hex[:8]
    object_name = f"wedding_uploads/{date_prefix}_{unique_token}_mision-{mission_id:02d}.jpg"
    token = str(uuid.uuid4())
    blob = storage.bucket().blob(object_name)
    blob.metadata = {"firebaseStorageDownloadTokens": token}
    blob.upload_from_file(file.stream, content_type="image/jpeg")

    bucket_name = storage.bucket().name
    encoded_path = object_name.replace("/", "%2F")
    public_url = (
        f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/"
        f"{encoded_path}?alt=media&token={token}"
    )

    now = datetime.now(timezone.utc)
    guest_ref.update(
        {
            "completed_mission_ids": firestore.ArrayUnion([mission_id]),
            f"uploads.{mission_id}": {
                "url": public_url,
                "storage_path": object_name,
                "content_type": "image/jpeg",
                "filename": secure_filename(file.filename),
                "uploaded_at": now,
            },
            "updated_at": now,
        }
    )

    return jsonify(ok=True, url=public_url, content_type="image/jpeg")


@app.errorhandler(413)
def too_large(_error):
    return jsonify(ok=False, error="El archivo no puede superar los 50 MB."), 413


@app.errorhandler(Exception)
def unhandled_error(error):
    if isinstance(error, HTTPException):
        return error

    app.logger.exception("Error no controlado", exc_info=error)
    if request.path.startswith("/api/"):
        return jsonify(
            ok=False,
            error="El servidor no pudo completar la operación. Revisa su configuración de Firebase.",
        ), 500
    return "Error interno del servidor", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
