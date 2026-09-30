# Plan Preliminar: Tablero de Control de Calidad en Tiempo Real

## 1\. Herramientas Recomendadas

* **Frontend (Interfaz del cliente):** HTML, CSS y JavaScript (Basado en el diseño estético actual).  
* **Backend (Servidor y Lógica):** Python, ideal para el procesamiento de datos. Usaremos Flask o FastAPI como framework.  
* **Base de Datos / Conector:** API oficial de Google Sheets (lectura directa en la nube).  
* **Control de Versiones y Despliegue:** Git Bash para control de cambios, GitHub para repositorio, y Render, Heroku o PythonAnywhere para alojar la web.

## 2\. Flujo de Datos

1. **Captura:** La aplicación de terceros registra las piezas, defectos y retrabajos; los datos se guardan en el documento de Google Sheets.  
2. **Extracción (Backend):** El servidor en Python se autentica de forma segura y consulta las filas de la hoja en tiempo real.  
3. **Transformación:** Python estructura la información (calcula pareto de defectos, tendencia mensual, scrap vs retrabajo).  
4. **Consumo (Frontend):** El navegador del cliente hace una petición al servidor Python, descarga el paquete de datos y actualiza las tarjetas y gráficas instantáneamente.

## 3\. Patrones de Diseño Recomendados

Utilizaremos una variación de **MVC (Modelo-Vista-Controlador)**:

* **Vista (View):** Tu archivo HTML actual y CSS, encargado de los componentes visuales.  
* **Controlador (Controller):** Los *endpoints* en tu código Python (ej. `/api/obtener_registros`) que reciben la petición y devuelven la respuesta en JSON.  
* **Modelo (Model):** La lógica en Python para conectarse a Google Workspace, limpiar datos y realizar cálculos.

## 4\. Estructura de Carpetas Recomendada

/tablero-calidad-hbpo

│

├── /frontend                  \# La interfaz que consumirá el cliente

│   ├── index.html             \# Tu archivo Dashboard modificado

│   ├── /css                   \# Estilos separados

│   └── /js                    \# Lógica de las gráficas

│

├── /backend                   \# El motor de datos

│   ├── app.py                 \# Archivo principal de tu servidor Python (Flask/FastAPI)

│   ├── gsheets\_service.py     \# Script para conectarse a Google Sheets

│   └── credenciales.json      \# Llave privada de Google (¡No se sube a GitHub\!)

│

├── requirements.txt           \# Lista de dependencias de Python

└── .gitignore                 \# Archivos a ignorar en el control de versiones

## 5\. Plan de Acción (Hoja de Ruta)

### Fase 1: Preparar la Conexión a la Nube (Guía Detallada)

Esta fase permite que el servidor de Python lea tu Google Sheets de manera automatizada.

**Paso 1: Crear el proyecto en Google Cloud**

1. Ingresa a [Google Cloud Console](https://console.cloud.google.com/).  
2. Inicia sesión y haz clic en el selector de proyectos (esquina superior izquierda). Selecciona "Nuevo proyecto".  
3. Asígnale un nombre (ej. `DashboardCalidadHBPO`) y haz clic en "Crear".

**Paso 2: Habilitar las APIs necesarias**

1. En el menú de navegación (hamburguesa), ve a **API y servicios \> Biblioteca**.  
2. Busca "Google Sheets API" y haz clic en **Habilitar**.  
3. Regresa a la Biblioteca, busca "Google Drive API" y haz clic en **Habilitar** (necesaria para ubicar el archivo).

**Paso 3: Crear la Cuenta de Servicio (Service Account)**

1. Ve a **API y servicios \> Credenciales**.  
2. Haz clic en **\+ CREAR CREDENCIALES** y selecciona **Cuenta de servicio**.  
3. Ponle un nombre (ej. `bot-sheets`) y haz clic en **Crear y continuar** y luego en **Listo**.  
4. Verás la cuenta creada en la lista con un correo electrónico parecido a `bot-sheets@...iam.gserviceaccount.com`. **Copia este correo**.

**Paso 4: Generar el archivo JSON de credenciales**

1. Haz clic sobre el correo de la cuenta de servicio en la lista.  
2. Ve a la pestaña **Claves** (Keys).  
3. Haz clic en **Agregar clave \> Crear clave nueva**.  
4. Selecciona el formato **JSON** y haz clic en **Crear**.  
5. Se descargará el archivo a tu computadora. Este es tu `credenciales.json`. Guárdalo en la carpeta `/backend` de tu proyecto y **asegúrate de incluirlo en el .gitignore** para no subirlo a internet.

**Paso 5: Dar permisos en Google Sheets**

1. Abre tu documento original de Google Sheets.  
2. Haz clic en el botón verde **Compartir** (arriba a la derecha).  
3. Pega el correo de la cuenta de servicio que copiaste en el Paso 3\.  
4. Asígnale el rol de **Lector** y haz clic en "Enviar". Ahora tu programa en Python está autorizado para leer los datos.

### Fase 2: Construir el Backend en Python

* Instalar dependencias mediante terminal: `pip install gspread oauth2client flask`.  
* Desarrollar `gsheets_service.py` para leer y extraer la matriz de datos de la hoja.  
* Configurar `app.py` para establecer las rutas que proveerán el JSON estructurado al frontend.

### Fase 3: Refactorizar el Frontend

* Eliminar el arreglo de datos estático (JSON quemado) del archivo HTML.  
* Implementar `fetch()` en JavaScript para conectarse al backend, descargar la información y dibujar dinámicamente las gráficas y los KPIs.

### Fase 4: Pruebas y Despliegue

* Utilizar Git Bash para registrar los cambios y subirlos al repositorio de GitHub.  
* Desplegar el backend en un servicio gratuito en la nube (como Render).  
* Conectar el frontend para que consuma la URL pública del servidor, entregando la plataforma final al cliente.