# Plan de trabajo: Tablero de Control de Calidad en Tiempo Real

Actualizado el 2 de octubre de 2026. Las fases 1 y 2 están terminadas; este
documento refleja lo que de verdad se construyó y agrega a la Fase 3 el inicio
de sesión, el usuario administrador y la seguridad.

## 1. Herramientas

* **Frontend:** HTML, CSS y JavaScript sin frameworks, con el diseño del
  dashboard original (`docs/referencia/dashboard-original-grammer.html`).
  Las gráficas son SVG dibujado a mano, sin librerías externas.
* **Backend:** Python con **FastAPI**. También sirve el HTML (un solo servicio,
  sin CORS).
* **Datos:** Google Sheets API con `gspread.service_account()`; la hoja se
  abre por ID (`open_by_key`), así que no se usa la Google Drive API ni
  `oauth2client`. Solo lectura.
* **Seguridad:** contraseñas con hash **Argon2id** (`argon2-cffi`), sesión en
  cookie firmada (`itsdangerous`). Ambas se agregan a `requirements.txt`.
* **Control de versiones y despliegue:** Git Bash, GitHub y **Render**.

## 2. Flujo de datos

1. **Captura:** la app de terceros guarda cada inspección en la hoja de Google.
2. **Inicio de sesión:** el usuario entra en `/login`. El backend valida
   usuario y contraseña y entrega una cookie de sesión.
3. **Extracción:** con la sesión válida, el backend lee la hoja (caché de 5 min)
   y limpia los registros.
4. **Consumo:** el navegador pide `/api/datos`, recibe filas limpias y calcula
   KPIs, pareto, tendencia y filtros al instante.

## 3. Patrón de diseño

Variación de MVC:

* **Vista:** `frontend/` (HTML, CSS, JS).
* **Controlador:** `backend/app/routers/` (endpoints que responden JSON).
* **Modelo:** `backend/app/fuentes/` (lectura de Google) y
  `backend/app/servicios/` (limpieza y reglas de negocio).
* **Dependencias (`Depends`):** `backend/app/dependencias.py` decide quién es
  el usuario y qué cliente puede ver, antes de que corra cualquier ruta.

## 4. Estructura de carpetas

Lo marcado con ✚ se agrega en la Fase 3.

```
backend/
  app/
    main.py              crea la app, registra routers, cabeceras de seguridad, sirve /frontend
    config.py            configuración por variables de entorno / .env
    clientes.py          catálogo de clientes (hoy solo HBPO)
    dependencias.py      Depends: usuario actual, cliente permitido, fuente de datos
    esquemas.py        ✚ modelos Pydantic (login, usuario)
    seguridad/         ✚
      contrasenas.py     hash y verificación Argon2id
      sesiones.py        crear, leer y borrar la cookie de sesión
      intentos.py        límite de intentos fallidos de login
      cabeceras.py       middleware de cabeceras HTTP de seguridad
    usuarios.py        ✚ de dónde salen los usuarios (hoy: el admin desde variables de entorno)
    routers/
      datos.py           GET /api/salud, GET /api/datos (ahora protegido)
      auth.py          ✚ POST /api/login, POST /api/logout, GET /api/yo
    fuentes/gsheets.py   lectura de Google Sheets con caché
    servicios/           inspeccion.py, partes.py
  scripts/
    probar_conexion.py
    crear_hash.py      ✚ pide una contraseña y muestra su hash para la variable de entorno
  tests/               ✚ pruebas automáticas de login y protección de rutas
  credenciales.json      llave del robot (NO se sube)
frontend/              ✚
  login.html             pantalla de inicio de sesión
  index.html             dashboard (sin datos fijos)
  css/estilos.css
  js/login.js, js/dashboard.js
docs/
requirements.txt
.env.ejemplo
```

## 5. Seguridad

Objetivo: que solo usuarios autorizados vean los datos y que los ataques más
comunes (adivinar contraseñas, robar la sesión, inyectar código, incrustar la
página en otro sitio) no funcionen.

### 5.1 Dónde viven los usuarios

El disco de Render (plan gratuito) **se borra en cada despliegue o reinicio**,
así que no se puede guardar un archivo o SQLite con usuarios ahí.

* **Ahora (Fase 3): un solo usuario administrador definido en variables de
  entorno** (`ADMIN_USUARIO` y `ADMIN_HASH`). No hace falta base de datos.
  `usuarios.py` expone una función `buscar_usuario(nombre)`; el resto del
  código no sabe de dónde viene el usuario.
* **Después (fase multi‑cliente): base de datos PostgreSQL administrada**
  (Neon, Supabase o Render Postgres de pago). Solo se reescribe
  `usuarios.py`; login, sesiones y rutas no cambian. Ahí llegan los usuarios
  por cliente y la pantalla de administración para crearlos.

### 5.2 Cómo se crea el admin sin dejar contraseñas en el repo

1. En tu máquina: `python backend/scripts/crear_hash.py`. Pide la contraseña
   dos veces (sin mostrarla) y exige mínimo 12 caracteres.
2. Imprime un hash Argon2id (`$argon2id$v=19$...`). El hash no permite
   recuperar la contraseña.
3. Ese hash va en `.env` (local) y en el panel *Environment* de Render. La
   contraseña en texto plano nunca se escribe en ningún archivo.
4. Para cambiar la contraseña: generar otro hash y reemplazar la variable.

### 5.3 Contraseñas

* Hash **Argon2id** con los parámetros recomendados por `argon2-cffi`.
* Si el usuario no existe, se verifica igual contra un hash falso, para que el
  tiempo de respuesta no revele qué usuarios existen.
* Mensaje de error único: "Usuario o contraseña incorrectos".

### 5.4 Sesiones y cookies

* Al entrar, el backend crea una cookie firmada con `SECRET_KEY` (variable de
  entorno, 64 caracteres aleatorios). Si alguien la modifica, la firma no
  coincide y se rechaza.
* Atributos: `HttpOnly` (JavaScript no la puede leer, frena robo por XSS),
  `Secure` (solo viaja por HTTPS), `SameSite=Strict` (otro sitio no puede
  usarla), `Path=/`.
* Caducidad: 8 horas (configurable con `SESION_HORAS`). Al expirar, vuelve a
  pedir login.
* La sesión guarda una "huella" del hash de la contraseña: si cambias la
  contraseña del admin, todas las sesiones abiertas dejan de servir.
* Cerrar sesión borra la cookie. Cambiar `SECRET_KEY` cierra todas las
  sesiones de golpe (botón de emergencia).

### 5.5 Protección de rutas

* `/api/datos` exige sesión válida mediante `Depends(usuario_actual)`; sin
  sesión responde **401**.
* `obtener_cliente` valida que el usuario tenga permiso sobre el cliente. El
  admin ve todos; en el futuro, un usuario de cliente solo el suyo.
* `/` (dashboard) sin sesión redirige a `/login`. Los archivos CSS/JS no
  contienen datos, así que pueden ser públicos.
* `/api/salud` sigue pública (Render la usa para vigilar el servicio).
* `/docs` y `/openapi.json` se desactivan en producción (`ENTORNO=produccion`).

### 5.6 Límite de intentos (fuerza bruta)

* 5 intentos fallidos por IP o por usuario en 15 minutos bloquean el login por
  15 minutos (respuesta **429**). Valores configurables.
* El contador vive en memoria: suficiente para un solo servidor en Render. Si
  algún día hay varios servidores, se mueve a la base de datos o a Redis.
* La IP real se toma de la cabecera que pone el proxy de Render
  (`X-Forwarded-For`), solo cuando `ENTORNO=produccion`.
* Cada intento fallido se registra en el log (usuario e IP, nunca la
  contraseña).

### 5.7 Ataques desde otros sitios (CSRF)

* `SameSite=Strict` ya impide que otro sitio envíe la cookie.
* Además, login y logout solo aceptan `POST` con `Content-Type:
  application/json` y se revisa que la cabecera `Origin` sea la del propio
  sitio.

### 5.8 Inyección de código en la página (XSS)

* Los comentarios y defectos vienen de texto libre capturado en la app. En el
  dashboard **todo dato se inserta con `textContent`** o escapado, nunca con
  `innerHTML` crudo.
* Todo el JavaScript va en archivos `.js` (el original tiene un `<script>`
  dentro del HTML y un `onclick`); así se puede usar una política CSP estricta.

### 5.9 HTTPS y cabeceras HTTP

* Render da HTTPS automático y redirige HTTP a HTTPS.
* Middleware que agrega en cada respuesta:
  * `Strict-Transport-Security: max-age=31536000` (el navegador siempre usa HTTPS; solo en producción).
  * `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`.
  * `X-Content-Type-Options: nosniff`.
  * `X-Frame-Options: DENY` (nadie puede incrustar el dashboard en otra página).
  * `Referrer-Policy: same-origin`.
  * `Permissions-Policy: camera=(), microphone=(), geolocation=()`.
* `/api/datos` y `/api/yo` responden con `Cache-Control: no-store`, para que
  los datos no queden guardados en computadoras compartidas.

### 5.10 Secretos

| Variable | Qué es | Dónde |
|---|---|---|
| `SECRET_KEY` | firma de las cookies | `.env` / Render Environment |
| `ADMIN_USUARIO` | nombre del admin | `.env` / Render Environment |
| `ADMIN_HASH` | hash Argon2id de su contraseña | `.env` / Render Environment |
| `CREDENCIALES` | ruta de la llave del robot | Render Secret File |
| `ENTORNO` | `desarrollo` o `produccion` | `.env` / Render Environment |

* En producción, el servidor **no arranca** si falta `SECRET_KEY` o el admin,
  o si `SECRET_KEY` es corta. Así no se publica por error un sitio sin
  protección.
* `.env` y `credenciales.json` siguen en `.gitignore`. Nunca se usa el correo
  de la empresa en este proyecto.

### 5.11 Pruebas

Pruebas automáticas con `pytest` que confirman: sin sesión, `/api/datos` da
401; con contraseña mala, 401; tras 5 fallos, 429; con sesión válida, 200;
una cookie alterada o vencida se rechaza; las cabeceras de seguridad están
presentes.

## 6. Plan de acción

### Fase 1: Conexión a Google Sheets ✔

Cuenta de servicio con rol Lector sobre la hoja, llave en
`backend/credenciales.json` (fuera del repo). Solo se habilitó la Google
Sheets API. (PR #1)

### Fase 2: Backend FastAPI ✔

Backend modular, `/api/datos` con registros limpios de HBPO, caché de 5 min,
estandarización de números de parte. (PR #2)

### Fase 3: Inicio de sesión, seguridad y frontend

Se hace en pasos, cada uno en su PR y probado antes de seguir:

1. **Seguridad base:** nuevas variables en `config.py`, validación al
   arrancar, middleware de cabeceras, `/docs` apagado en producción,
   `scripts/crear_hash.py`.
2. **Login en el backend:** `seguridad/`, `usuarios.py`, `routers/auth.py`,
   límite de intentos, `/api/datos` protegido, pruebas.
3. **Pantalla de inicio de sesión:** `frontend/login.html` con el estilo del
   dashboard, mensajes de error y bloqueo.
4. **Dashboard conectado:** `frontend/index.html` a partir del original, sin
   el JSON fijo, con `fetch('/api/datos')`, reglas de negocio HBPO, inserción
   segura de texto, botón "Cerrar sesión" y redirección a `/login` si la
   sesión vence.

### Fase 4: Despliegue en Render

* Servicio web con `uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend`.
* Variables de la tabla 5.10 y la llave como Secret File.
* Revisar en el sitio publicado: HTTPS, cabeceras (securityheaders.com),
  login, bloqueo por intentos y que `/docs` no responda.

### Fase 5 (futuro): Varios clientes

* PostgreSQL administrada para usuarios, roles y permisos por cliente.
* Pantalla de administración para crear usuarios y cambiar contraseñas.
* Histórico de Grammer y más hojas en `clientes.py`.
