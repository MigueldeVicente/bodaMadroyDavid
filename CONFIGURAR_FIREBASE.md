# Configuración de Firebase

La aplicación ya está preparada para guardar invitados y misiones en **Cloud Firestore**, y fotografías en **Firebase Storage**.

## 1. Crear el proyecto

1. Entra en Firebase Console y crea un proyecto.
2. Abre **Firestore Database** y crea la base de datos.
3. Abre **Storage** y crea el bucket.
4. En **Configuración del proyecto → Cuentas de servicio**, genera una clave privada JSON.

No subas ese JSON a GitHub ni lo metas dentro del ZIP público.

## 2. Crear el archivo `.env`

Copia `.env.example` como `.env` y completa:

```env
BODA_SECRET_KEY=una-clave-larga-y-aleatoria
BODA_ADMIN_PASSWORD=una-contrasena-privada
BODA_NOVIA=Madro
BODA_NOVIO=David
BODA_FECHA=18 de julio de 2026
BODA_LUGAR=

FIREBASE_PROJECT_ID=identificador-de-tu-proyecto
FIREBASE_STORAGE_BUCKET=nombre-exacto-del-bucket
FIREBASE_SERVICE_ACCOUNT_PATH=C:\ruta\serviceAccountKey.json
```

El nombre exacto del bucket se encuentra en Firebase Console → Storage. Puede terminar en `.firebasestorage.app` o en `.appspot.com`, según el proyecto.

También puedes usar `GOOGLE_APPLICATION_CREDENTIALS` en lugar de `FIREBASE_SERVICE_ACCOUNT_PATH`:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\ruta\serviceAccountKey.json"
```

## 3. Ejecutar

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre `http://127.0.0.1:5000`.

## 4. Qué se guarda

- `guests/{guestId}`: nombre y apellidos del invitado.
- `guest_missions/{missionId}`: tres misiones asignadas y estado de la foto.
- Storage: imágenes en `{guestId}/{missionId}/archivo`.

La URL `/novios` abre la galería privada. La contraseña es `BODA_ADMIN_PASSWORD`.

## 5. Publicar online

En Render, Railway, Cloud Run u otro hosting Python:

- instala con `pip install -r requirements.txt`;
- inicia con `gunicorn app:app --bind 0.0.0.0:$PORT`;
- añade las variables del `.env` en el panel del hosting;
- para la cuenta de servicio, usa `FIREBASE_SERVICE_ACCOUNT_JSON` con el contenido JSON completo, o el sistema seguro de secretos del proveedor.

Las reglas incluidas bloquean el acceso directo desde navegadores. Esto es intencionado: el servidor Flask usa Firebase Admin SDK y es el único que escribe o lee los datos.
