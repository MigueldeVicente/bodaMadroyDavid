# Boda Clau (Firestore + Firebase Storage)

Aplicación Flask pensada para móvil: QR → formulario (nombre + 2 apellidos) → 3 misiones aleatorias (si es nuevo) o misiones existentes (si ya participó) → subida de foto → galería privada para los novios.

## Requisitos
- Crear un proyecto en Firebase.
- **Firestore** habilitado.
- **Firebase Storage** habilitado (bucket).
- Obtener credenciales **Service Account**.

> Importante: el proyecto espera credenciales vía variable de entorno:
> - `FIREBASE_SERVICE_ACCOUNT_PATH` (recomendado) o
> - `FIREBASE_SERVICE_ACCOUNT_JSON` (texto JSON)

## 1) Configurar variables de entorno
Crea un `.env` (opcional) o define variables en tu hosting.

Ejemplo:
```env
BODA_SECRET_KEY=una_clave_larga_aleatoria
BODA_ADMIN_PASSWORD=tu_contraseña_novios
BODA_NOVIA=Madro
BODA_NOVIO=David
BODA_FECHA=18 de julio de 2026
BODA_LUGAR=

FIREBASE_PROJECT_ID=tu_project_id
FIREBASE_STORAGE_BUCKET=tu_project_id.appspot.com

# Opción A (recomendada): path en el servidor
FIREBASE_SERVICE_ACCOUNT_PATH=C:\ruta\serviceAccountKey.json

# Opción B: JSON completo en texto
# FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account", ...}
```

## 2) Instalar
```powershell
pip install -r requirements.txt
```

Después, copia `.env.example` como `.env` y completa las credenciales de tu proyecto Firebase. El archivo `.env` no se sube al repositorio.

## 3) Ejecutar local
```powershell
python app.py
```

Abre: http://127.0.0.1:5000

## Desarrollo local con Firebase

La aplicación usa el SDK de administración en Flask: los invitados nunca reciben credenciales de Firebase y las fotos se guardan desde el servidor. Para trabajar con datos locales instala Firebase CLI y ejecuta, en otra terminal:

```powershell
firebase emulators:start
```

Descomenta `FIRESTORE_EMULATOR_HOST` y `STORAGE_EMULATOR_HOST` en `.env`, y después inicia Flask con `F5` o `iniciar.bat`. La consola del emulador estará en `http://127.0.0.1:4000` y la boda en `http://127.0.0.1:5000`.

### Vista previa en VS Code
No uses Live Server para esta aplicación: solo sirve archivos estáticos y no puede ejecutar el registro ni Firebase. Usa **Ejecutar y depurar** (`F5`) y selecciona **“Boda: abrir vista previa”**. VS Code arrancará Flask y abrirá `http://127.0.0.1:5000` automáticamente. También puedes ejecutar `iniciar.bat`.

## Estructura de datos (Firestore)
- `guests/{guestId}`
  - nombre, apellido1, apellido2
  - nombre_norm, apellido1_norm, apellido2_norm (para detectar invitados existentes)
- `guest_missions/{missionRowId}`
  - guest_id, position (1..3)
  - mission_text
  - photo_url, completed_at

## Storage
Las fotos se guardan en:
- `{guest_id}/{mission_row_id}/{filename}`

El backend devuelve una URL (idealmente firmada por Firebase Admin). 

## Despliegue (GitHub/Render)
- Sube a GitHub.
- En Render (o similar), define las variables de entorno.
- Start command:
  - `gunicorn app:app --bind 0.0.0.0:$PORT`

## Endpoints
- GET `/` → landing + registro
- POST `/api/registro` → crea/recupera invitado
- GET `/misiones` → misiones y subida
- POST `/api/upload/<mission_row_id>` → sube foto
- GET `/novios` → galería privada

