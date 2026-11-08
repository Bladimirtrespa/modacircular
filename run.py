"""
Punto de Entrada Principal (Entry Point)
Ejecuta el servidor de desarrollo de la plataforma de intercambio sostenible.
"""

import os
from app import crear_app

# Obtener el entorno de ejecución (por defecto: desarrollo)
entorno = os.getenv('FLASK_ENV', 'desarrollo')
app = crear_app(entorno)

if __name__ == '__main__':
    # Ejecución en modo local
    puerto = int(os.getenv('PUERTO', 5000))
    app.run(host='0.0.0.0', port=puerto, debug=app.config.get('DEBUG', True))
