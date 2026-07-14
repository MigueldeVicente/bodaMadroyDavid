import os
import secrets
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from database import (
    init_db,
    get_or_create_guest,
    get_guest_missions,
    save_mission_photo,
    upload_photo_file,
    get_all_photos_for_novios,
    get_stats_for_novios,
)
from config import (
    BODA_SECRET_KEY,
    BODA_ADMIN_PASSWORD,
    BODA_NOVIA,
    BODA_NOVIO,
    BODA_FECHA,
    BODA_LUGAR,
    USE_FIREBASE,
)

BASE_DIR = Path(__file__).resolve().parent


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
        static_url_path="/static",
    )

    app.secret_key = BODA_SECRET_KEY or os.environ.get("BODA_SECRET_KEY") or secrets.token_hex(32)

    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    init_db()

    @app.context_processor
    def inject_boda_config():
        return {
            "boda_novia": BODA_NOVIA,
            "boda_novio": BODA_NOVIO,
            "boda_fecha": BODA_FECHA,
            "boda_lugar": BODA_LUGAR,
            "is_cloud": USE_FIREBASE,
        }

    @app.get("/")
    def index():
        if session.get("guest"):
            return redirect(url_for("misiones"))
        return render_template("index.html")

    @app.post("/api/registro")
    def registro():
        payload = request.get_json(silent=True) or request.form
        nombre = (payload.get("nombre") or "").strip()
        apellido1 = (payload.get("apellido1") or "").strip()
        apellido2 = (payload.get("apellido2") or "").strip()

        if not nombre or not apellido1 or not apellido2:
            return jsonify({"error": "Completa nombre y ambos apellidos."}), 400

        try:
            guest, is_new = get_or_create_guest(nombre, apellido1, apellido2)
        except Exception as exc:
            return jsonify({"error": f"No se pudo registrar: {exc}"}), 503

        session["guest"] = {
            "id": guest["id"],
            "nombre": guest["nombre"],
            "apellido1": guest["apellido1"],
            "apellido2": guest["apellido2"],
        }

        missions = get_guest_missions(guest["id"])

        return jsonify(
            {
                "is_new": is_new,
                "guest": session["guest"],
                "missions": [
                    {
                        "id": m["id"],
                        "position": m["position"],
                        "text": m["mission_text"],
                        "photo_url": m.get("photo_url"),
                        "completed_at": m.get("completed_at"),
                    }
                    for m in missions
                ],
            }
        )

    @app.get("/misiones")
    def misiones():
        guest = session.get("guest")
        if not guest:
            return redirect(url_for("index"))

        missions = get_guest_missions(guest["id"])
        # Template espera: mission_text, position, display_url, is_complete, id
        missions_view = []
        for m in missions:
            photo_url = m.get("photo_url")
            missions_view.append(
                {
                    **m,
                    "text": m["mission_text"],
                    "display_url": photo_url,
                    "is_complete": bool(photo_url),
                }
            )

        return render_template("misiones.html", guest=guest, missions=missions_view)

    @app.post("/api/upload/<mission_row_id>")
    def upload_photo(mission_row_id: str):
        guest = session.get("guest")
        if not guest:
            return jsonify({"error": "Sesión no iniciada."}), 401

        if "photo" not in request.files:
            return jsonify({"error": "No se recibió ninguna foto."}), 400

        file = request.files["photo"]
        if not file or file.filename == "":
            return jsonify({"error": "Selecciona una imagen."}), 400

        if not (file.mimetype or "").startswith("image/"):
            return jsonify({"error": "El archivo debe ser una imagen."}), 400

        filename = secure_filename(file.filename) or "foto.jpg"
        file_bytes = file.read()

        try:
            photo_url = upload_photo_file(
                guest_id=guest["id"],
                mission_row_id=mission_row_id,
                filename=filename,
                file_bytes=file_bytes,
            )
            save_mission_photo(mission_row_id=mission_row_id, guest_id=guest["id"], photo_url=photo_url)
        except Exception as exc:
            return jsonify({"error": f"Error al subir la foto: {exc}"}), 500

        return jsonify({"success": True, "photo_url": photo_url})

    @app.route("/salir")
    def salir():
        session.pop("guest", None)
        return redirect(url_for("index"))

    @app.route("/novios", methods=["GET", "POST"])
    def novios():
        error = None

        if request.method == "POST":
            password = request.form.get("password", "")
            if password == BODA_ADMIN_PASSWORD:
                session["admin"] = True
                return redirect(url_for("novios"))
            error = "Contraseña incorrecta."

        if not session.get("admin"):
            return render_template("novios_login.html", error=error)

        photos = get_all_photos_for_novios()
        stats = get_stats_for_novios()
        return render_template("novios_gallery.html", photos=photos, stats=stats)

    @app.route("/novios/logout")
    def novios_logout():
        session.pop("admin", None)
        return redirect(url_for("novios"))

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")

