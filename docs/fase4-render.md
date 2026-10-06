# Fase 4: publicar el dashboard en Render

Propuesta aprobada el 2026-10-06 y ya ejecutada: el sitio está en
https://plataforma-qsb.onrender.com (PR #10). Se conserva como registro de
por qué se eligió Render y cómo se configuró.

## 1. Qué se va a hacer

Hoy el dashboard solo funciona en tu computadora (`uvicorn ... --reload`). En
esta fase lo publicamos en internet, con una dirección fija tipo
`https://plataforma-qsb.onrender.com`, con HTTPS y con el mismo login que ya
tienes. Desde ahí lo abres en el celular o lo compartes con quien deba verlo.

Nada cambia en la lógica del dashboard ni en la hoja de Google: Render solo
corre el mismo programa que corres tú, pero en un servidor suyo, y lo vuelve a
publicar solo cada vez que se mezcla algo a `main`.

## 2. Por qué Render (y no otra opción)

| Opción | Costo | Qué tan fácil | Comentario |
|---|---|---|---|
| **Render (recomendado)** | Gratis, o 7 USD/mes sin "dormir" | Muy fácil: conectas GitHub y listo | Ya está en el plan; HTTPS gratis; "Secret Files" para la llave de Google; se redepliega solo desde `main`. |
| Google Cloud Run | Capa gratuita amplia | Media/alta: Docker, consola de Google Cloud, facturación | Más potente, pero mucho más que aprender para un solo dashboard. |
| Railway / Fly.io | Ya no tienen plan gratis real; piden tarjeta | Media | Sin ventaja clara sobre Render para este caso. |
| PythonAnywhere | Gratis limitado | Media | Soporte de FastAPI todavía limitado; no conviene. |

Render es la mejor opción para este proyecto porque el backend ya se preparó
pensando en él (variables de entorno, `/api/salud`, IP real por
`X-Forwarded-For`, HSTS en producción) y porque todo se configura desde una
página web, sin servidores que administrar.

### Lo que hay que saber del plan gratuito

* **Se duerme** después de 15 minutos sin visitas. La siguiente visita tarda
  unos 30 a 60 segundos en despertar; después va normal. Para un dashboard
  interno suele estar bien. Si a los clientes les molesta, se cambia al plan
  *Starter* (7 USD/mes) con un clic, sin tocar código.
* **El disco se borra** en cada reinicio. No nos afecta: no guardamos nada en
  disco (usuarios en variables de entorno, datos en Google Sheets).
* **La memoria también se borra** al dormir: el caché de 5 minutos y el
  contador de intentos fallidos de login empiezan de cero. Aceptable hoy.
* 750 horas gratis al mes por cuenta: alcanza para un servicio todo el mes.

## 3. Cómo se va a hacer (paso a paso)

### Paso 4.1: preparar el repositorio (lo hago yo, un PR)

1. **Arreglar el error conocido:** falta `itsdangerous` en `requirements.txt`
   (lo usa `backend/app/seguridad/sesiones.py`). Sin esto Render no arranca.
   Sigue faltando en `main` hoy, así que va en este PR.
2. **`.python-version` con `3.13`**, la misma versión de tu máquina, para que
   Render no use otra y aparezcan diferencias.
3. **`render.yaml`** (un "Blueprint"): un archivo que describe el servicio
   para que Render lo cree solo. Así la configuración queda guardada en GitHub
   y no depende de recordar qué se puso en qué casilla. Contendrá:
   * Tipo: servicio web Python, plan gratuito, región Ohio (EE. UU., la más
     cercana a México).
   * Instalación: `pip install -r requirements.txt`
   * Arranque: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend`
     (un solo proceso, porque el caché y el contador de intentos viven en
     memoria).
   * Chequeo de salud: `/api/salud` (Render lo consulta para saber si el
     servidor vive; si una versión nueva no responde, no reemplaza a la buena).
   * Variables sin secreto ya llenas: `ENTORNO=produccion`,
     `CREDENCIALES=/etc/secrets/credenciales.json`.
   * Variables secretas marcadas como "pedir al crear" (`SECRET_KEY`,
     `ADMIN_USUARIO`, `ADMIN_HASH`): Render te pide el valor en su página; nunca
     se escriben en el repositorio.
4. **Pruebas automáticas en GitHub (GitHub Actions)** que corren todos los tests (pytest)
   en cada PR, y Render configurado para **publicar solo si los tests pasan**.
   Esto es una mejora sobre el plan original: evita que un error llegue al
   sitio público. Si prefieres no agregarlo ahora, se quita sin problema.
5. **Sección "Publicar en Render"** en el README.

Tú lo revisas y lo mezclas a `main` como en las fases anteriores.

### Paso 4.2: preparar los secretos nuevos (tú, en tu máquina)

Con Git Bash en `~/Desktop/PlataformaQSB`:

* Una **SECRET_KEY nueva**: `python backend/scripts/crear_hash.py --secret-key`.
  No reutilizar la de tu `.env` (una se pegó en el chat, así que ya no es
  secreta).
* El **hash de la contraseña** del admin: `python backend/scripts/crear_hash.py`.
  Puedes usar la misma contraseña o una nueva más larga.

Estos valores los pegas **solo en la página de Render**, nunca en el chat.

### Paso 4.3: crear el servicio en Render (tú, con mi guía)

1. Crear cuenta en render.com **con tu cuenta personal de GitHub o Google**
   (nunca la de mgtransportes.mx).
2. Darle a Render acceso solo al repositorio `Plataforma-clientes-terceria`.
3. *New → Blueprint*, elegir el repositorio: Render lee `render.yaml` y te
   pide `SECRET_KEY`, `ADMIN_USUARIO` y `ADMIN_HASH` (el hash sin comillas,
   a diferencia del `.env`).
4. En *Environment → Secret Files* subir `credenciales.json` con ese nombre.
   Render lo guarda cifrado y lo pone en `/etc/secrets/credenciales.json`.
5. Esperar el primer despliegue (unos minutos). Si falta un secreto, el
   servidor se niega a arrancar a propósito y el log dice cuál falta.

### Paso 4.4: verificar (juntos)

* `https://<tu-servicio>.onrender.com/api/salud` responde `{"estado":"ok"}`.
* `/` manda al login; el login funciona; el dashboard muestra los datos reales.
* `/docs` da 404 (apagado en producción).
* Abrirlo desde el celular con datos móviles (esto resuelve lo de la red local).
* Revisar en el log que el intento fallido de login registre tu IP real. Si
  Render la entrega distinto a como espera el código, ajusto
  `ip_del_visitante` en un PR pequeño (es lo que hace que el bloqueo de 5
  intentos sea por persona y no se pueda burlar).

### Después

Cada PR mezclado a `main` se publica solo. La hoja de Google sigue siendo de
solo lectura para el robot; Render nunca escribe en ella.

## 4. Decisiones (las tres se aprobaron con "sí")

1. ¿Apruebas Render plan gratuito (con la opción de pasar a 7 USD/mes si el
   "dormir" estorba)? **Recomendado: sí.**
2. ¿Agrego las pruebas automáticas en GitHub + "publicar solo si pasan"?
   **Recomendado: sí.**
3. ¿Usamos `render.yaml` (configuración guardada en el repo) en lugar de
   llenar todo a mano en la página de Render? **Recomendado: sí.**
