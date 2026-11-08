"""
Módulo de Configuración de la Aplicación Flask
Define los perfiles de configuración (desarrollo, pruebas, producción)
y la construcción dinámica de la cadena de conexión a Microsoft SQL Server (DB_IntercambioRopa).
"""

import os
import urllib.parse
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env si existe
load_dotenv()


class ConfiguracionBase:
    """Configuración base compartida entre todos los entornos."""

    # Clave de seguridad criptográfica para sesiones y tokens CSRF
    SECRET_KEY = os.getenv('CLAVE_SECRETA', 'clave_secreta_por_defecto_desarrollo_insegura_cambiar')

    # Desactivar seguimiento de modificaciones de SQLAlchemy para optimizar memoria
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Opciones avanzadas del pool de conexiones para SQL Server
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_size': 10,
        'max_overflow': 20
    }

    # Límite máximo para subida de archivos (fotografías y videos cortos)
    LIMITE_SUBIDA_MB = int(os.getenv('LIMITE_MAXIMO_SUBIDA_MB', 32))
    MAX_CONTENT_LENGTH = LIMITE_SUBIDA_MB * 1024 * 1024

    # Ruta absoluta al directorio de almacenamiento de archivos multimedia
    DIRECTORIO_RAIZ = os.path.abspath(os.path.dirname(__file__))
    CARPETA_SUBIDAS = os.path.join(DIRECTORIO_RAIZ, os.getenv('CARPETA_SUBIDAS', 'app/static/uploads'))

    # Extensiones de archivos permitidas para evidencias de prendas y accesorios
    EXTENSIONES_IMAGENES_PERMITIDAS = {'jpg', 'jpeg', 'png', 'webp'}
    EXTENSIONES_VIDEOS_PERMITIDAS = {'mp4', 'mov', 'webm'}
    EXTENSIONES_PERMITIDAS = EXTENSIONES_IMAGENES_PERMITIDAS.union(EXTENSIONES_VIDEOS_PERMITIDAS)

    @classmethod
    def construir_uri_base_datos(cls) -> str:
        """
        Construye dinámicamente la URI de conexión para SQLAlchemy y pyodbc hacia Microsoft SQL Server.
        Soporta tanto autenticación integrada de Windows como autenticación nativa de SQL Server.
        """
        servidor = os.getenv('DB_SERVIDOR', 'localhost')
        base_datos = os.getenv('DB_NOMBRE', 'DB_IntercambioRopa')
        controlador = os.getenv('DB_CONTROLADOR', 'ODBC Driver 17 for SQL Server')
        autenticacion_windows = os.getenv('DB_AUTENTICACION_WINDOWS', 'si').strip().lower() in ('si', 'yes', 'true', '1')

        if autenticacion_windows:
            cadena_odbc = (
                f"DRIVER={{{controlador}}};"
                f"SERVER={servidor};"
                f"DATABASE={base_datos};"
                f"Trusted_Connection=yes;"
                f"TrustServerCertificate=yes;"
            )
        else:
            usuario = os.getenv('DB_USUARIO', 'sa')
            contrasena = os.getenv('DB_CONTRASENA', '')
            cadena_odbc = (
                f"DRIVER={{{controlador}}};"
                f"SERVER={servidor};"
                f"DATABASE={base_datos};"
                f"UID={usuario};"
                f"PWD={contrasena};"
                f"TrustServerCertificate=yes;"
            )

        # Se codifican los parámetros ODBC para formar una URI de SQLAlchemy válida
        cadena_codificada = urllib.parse.quote_plus(cadena_odbc)
        return f"mssql+pyodbc:///?odbc_connect={cadena_codificada}"


class ConfiguracionDesarrollo(ConfiguracionBase):
    """Configuración para el entorno de desarrollo local."""
    DEBUG = True
    TESTING = False

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return self.construir_uri_base_datos()


class ConfiguracionPruebas(ConfiguracionBase):
    """Configuración para pruebas unitarias e integración (pytest)."""
    DEBUG = False
    TESTING = True
    WTF_CSRF_ENABLED = False  # Simplifica pruebas de envío de formularios

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        # Permite usar una base de datos de prueba dedicada o en memoria
        uri_prueba = os.getenv('DB_URI_PRUEBAS')
        if uri_prueba:
            return uri_prueba
        return self.construir_uri_base_datos()


class ConfiguracionProduccion(ConfiguracionBase):
    """Configuración para entorno de producción."""
    DEBUG = False
    TESTING = False

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return self.construir_uri_base_datos()


# Diccionario mapeador de configuraciones
configuraciones = {
    'desarrollo': ConfiguracionDesarrollo,
    'pruebas': ConfiguracionPruebas,
    'produccion': ConfiguracionProduccion,
    'default': ConfiguracionDesarrollo
}
