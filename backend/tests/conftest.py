"""Configuración común de las pruebas.

Correr desde la raíz del proyecto:
    pip install -r requirements-dev.txt
    pytest backend/tests
"""

import sys
from pathlib import Path

# Para que `import app` funcione igual que con uvicorn --app-dir backend.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
