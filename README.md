# Plataforma Clientes Tercería

Dashboard de calidad en tiempo real para clientes de inspección de tercería.
Hoy muestra **HBPO**, leyendo en vivo (solo lectura) la hoja de Google Sheets
que llena la app de captura.

## Estado

| Fase | Qué | Estado |
|---|---|---|
| 1 | Acceso a Google Sheets con cuenta de servicio | Listo |
| 2 | Backend FastAPI (`/api/datos`) | Listo |
| 3 | Inicio de sesión (admin), seguridad y dashboard que consume `/api/datos` | Listo |
| 4 | Despliegue en Render | Pendiente |

El detalle de cada fase y de la seguridad está en `docs/plan-preliminar.md`.

Futuro: usuarios por cliente, varios clientes (histórico Grammer),
base de datos relacional y permisos. La estructura del backend ya deja el
lugar para cada uno.

## Estructura

```
backend/
  app/
    main.py            crea la app, registra routers, sirve /frontend
    config.py          configuración por variables de entorno / .env
    clientes.py        catálogo de clientes (hoy solo HBPO)
    dependencias.py    Depends: usuario con sesión, cliente permitido, fuente
    usuarios.py        de dónde salen los usuarios (hoy: el admin del .env)
    esquemas.py        modelos Pydantic (login, usuario)
    seguridad/
      contrasenas.py   hash y verificación Argon2id
      sesiones.py      cookie de sesión firmada
      intentos.py      límite de intentos fallidos de login
      cabeceras.py     cabeceras HTTP de seguridad (CSP, HSTS, no-store...)
    routers/
      auth.py          POST /api/login, POST /api/logout, GET /api/yo
      datos.py         GET /api/salud (pública), GET /api/datos (con sesión)
    fuentes/gsheets.py lectura de Google Sheets con caché
    servicios/
      inspeccion.py    limpieza de registros y reglas de negocio HBPO
      partes.py        estandarización de números de parte
  scripts/
    probar_conexion.py prueba rápida de acceso a la hoja
    servidor_demo.py   dashboard con datos inventados, sin llave de Google
    crear_hash.py      genera el hash del admin y la SECRET_KEY
  tests/               pruebas automáticas (pytest backend/tests)
  credenciales.json    llave del robot (NO se sube, está en .gitignore)
frontend/
  index.html           dashboard (KPIs, pareto, tendencias, turnos, partes, detalle)
  login.html           pantalla de inicio de sesión
  css/base.css         colores y componentes compartidos (del dashboard original)
  css/dashboard.css, css/login.css
  js/dashboard.js      pide /api/datos y calcula todo en el navegador (sin innerHTML)
  js/login.js          envía el login a /api/login y pasa al dashboard
docs/
  plan-preliminar.md
  referencia/dashboard-original-grammer.html   dashboard original con datos fijos
requirements.txt
requirements-dev.txt   lo de arriba más pytest, para correr las pruebas
.env.ejemplo
```

## Correr en local (Git Bash)

```bash
python -m venv venv            # solo la primera vez
source venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

- http://127.0.0.1:8000/: pantalla de inicio de sesión (usuario y contraseña
  del `.env`); después, el dashboard.
- http://127.0.0.1:8000/api/salud: el servidor está vivo.
- http://127.0.0.1:8000/docs: documentación interactiva.
- http://127.0.0.1:8000/api/datos: registros limpios de la hoja (necesita sesión).

Requiere la llave en `backend/credenciales.json` y que la hoja esté compartida
como Lector con el correo de la cuenta de servicio.

## Reglas de negocio HBPO

- Scrap = PIEZAS NOK
- Retrabajo = PIEZAS INSP. (todo lo inspeccionado es pieza retrabajada)
- OK = PIEZAS INSP. − PIEZAS NOK
- El ID de inspección es texto hexadecimal (`e21c0dc4`); nunca se convierte a número.
- Números de parte: mayúsculas sin espacios, sin `P` inicial, `8` al inicio si
  empieza con `MB`/`MC`, y se corta después de `BCS`. Excepciones en
  `CORRECCIONES` de `servicios/partes.py`.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest backend/tests
```

## Configuración

Todo tiene valor por defecto. Para cambiar algo, copia `.env.ejemplo` como `.env`.
En Render, la llave será un *Secret File* y su ruta va en `CREDENCIALES`.

### Seguridad

- `ENTORNO=produccion` (en Render) apaga `/docs`, activa HSTS y exige
  `SECRET_KEY`, `ADMIN_USUARIO` y `ADMIN_HASH`; si falta alguno, el servidor
  no arranca. En desarrollo todo es opcional.
- `python backend/scripts/crear_hash.py` genera el hash Argon2id del admin;
  `--secret-key` genera la llave de las cookies. La contraseña nunca se escribe
  en un archivo.
- Todas las respuestas llevan cabeceras de seguridad y `/api/*` no se guarda
  en caché del navegador.
- Login: sesión en cookie firmada (HttpOnly, SameSite=Strict, Secure en
  producción) que dura `SESION_HORAS`. Tras `INTENTOS_MAXIMOS` fallos por IP
  o por usuario, el login se bloquea `BLOQUEO_MINUTOS`. Cambiar la contraseña
  del admin o la `SECRET_KEY` cierra todas las sesiones.
- Detalle en `docs/plan-preliminar.md`, sección 5.
