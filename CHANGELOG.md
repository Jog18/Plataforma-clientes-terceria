# Historial de versiones

Cada versión se publica sola en Render al mezclarse a `main`. Las versiones
con número tienen etiqueta en GitHub (pestaña *Tags*).

## Sin versión todavía

- "LAZER" (como lo escribe la app de captura) ahora se muestra como "LÁSER" en
  defectos, filtros, gráficas, tablas, reporte y Excel. "LASER" sin acento
  también se unifica, para que cuenten como un solo defecto.
- Diálogo de Excel: si hay un día elegido en el tablero, lo propone en automático.
- Diálogo de Excel: con "Un solo día" solo aparece el campo Día; con "Rango
  de días" aparecen Desde y Hasta.
- La descarga ahora es un Excel (.xlsx) con el formato del equipo: encabezados
  de colores, una columna por defecto, %SCRAP, piezas OK y fila Total. FECHA DE
  PRODUCCION es la fecha de producción del lote. Reemplaza al CSV.
- El día del tablero cierra a las 6:00 en lugar de medianoche: el 3er turno
  cuenta completo para el día en que empieza. Filtros, KPIs, tendencias, CSV y
  reporte usan el día de producción; el CSV agrega la columna DIA PRODUCCION.

## v1.0.0 (2026-10-06): primera versión publicada

- Fase 4: dashboard en línea en https://plataforma-qsb.onrender.com (Render,
  plan gratis, HTTPS). Configuración en `render.yaml`; las pruebas corren en
  GitHub y Render solo publica si pasan (#10).
- Logo QSB en la pantalla de inicio de sesión (#11, #12).

## Fase 3 (2026-10-02): inicio de sesión y dashboard en vivo

- Plan de seguridad (#3) y base de seguridad: configuración por variables,
  cabeceras HTTP, `crear_hash.py` (#4).
- Login de administrador: cookie firmada de 8 h, bloqueo tras 5 intentos (#5).
- Pantalla de inicio de sesión (#6).
- Dashboard con datos reales de HBPO; la tarjeta "Retrabajo por tipo" se
  cambió por la tendencia diaria (#7).
- Corrección: las horas como 8:21 se ordenaban como texto (#8).
- Botón Actualizar que fuerza una lectura nueva de la hoja (#9).

## Fase 2 (2026-09-30): backend FastAPI

- `/api/datos` y `/api/salud`, limpieza de registros, reglas de negocio HBPO
  y estandarización de números de parte; reorganización del repositorio (#2).

## Fase 1 (2026-09-30): acceso a Google Sheets

- Cuenta de servicio de solo lectura y `probar_conexion.py` (#1).
