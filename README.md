# Plataforma Clientes Tercería

Dashboard de calidad en tiempo real para clientes de inspección de tercería.
Hoy muestra **HBPO**, leyendo en vivo (solo lectura) la hoja de Google Sheets
que llena la app de captura.

## Estado

| Fase | Qué | Estado |
|---|---|---|
| 1 | Acceso a Google Sheets con cuenta de servicio | Listo |
| 2 | Backend FastAPI (`/api/datos`) | Listo |
| 3 | Inicio de sesión (admin), seguridad y dashboard que consume `/api/datos` | En curso |
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
    dependencias.py    Depends: cliente y fuente (aquí entrarán login y permisos)
    routers/datos.py   GET /api/salud, GET /api/datos
    fuentes/gsheets.py lectura de Google Sheets con caché
    servicios/
      inspeccion.py    limpieza de registros y reglas de negocio HBPO
      partes.py        estandarización de números de parte
  scripts/
    probar_conexion.py prueba rápida de acceso a la hoja
  credenciales.json    llave del robot (NO se sube, está en .gitignore)
docs/
  plan-preliminar.md
  referencia/dashboard-original-grammer.html   dashboard original con datos fijos
requirements.txt
.env.ejemplo
```

## Correr en local (Git Bash)

```bash
python -m venv venv            # solo la primera vez
source venv/Scripts/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

- http://127.0.0.1:8000/api/salud: el servidor está vivo.
- http://127.0.0.1:8000/api/datos: registros limpios de la hoja.
- http://127.0.0.1:8000/docs: documentación interactiva.

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

## Configuración

Todo tiene valor por defecto. Para cambiar algo, copia `.env.ejemplo` como `.env`.
En Render, la llave será un *Secret File* y su ruta va en `CREDENCIALES`.
