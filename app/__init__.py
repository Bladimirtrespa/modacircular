"""
Fábrica de Aplicaciones (Application Factory) de Flask
Inicializa las extensiones, configura el entorno de ejecución
y establece la arquitectura modular para la plataforma de intercambio de ropa.
"""

import os
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

from config import configuraciones

# Inicialización de extensiones desacopladas del contexto de aplicación
db = SQLAlchemy()
gestor_sesiones = LoginManager()
csrf = CSRFProtect()


def crear_app(nombre_configuracion='desarrollo'):
    """
    Función de fábrica para instanciar y configurar la aplicación Flask.
    
    :param nombre_configuracion: Clave del perfil de configuración ('desarrollo', 'pruebas', 'produccion').
    :return: Instancia configurada de Flask.
    """
    app = Flask(__name__)

    # Cargar la configuración seleccionada
    clase_configuracion = configuraciones.get(nombre_configuracion, configuraciones['default'])()
    app.config.from_object(clase_configuracion)
    
    # Asignar explícitamente la propiedad calculada de base de datos
    app.config['SQLALCHEMY_DATABASE_URI'] = clase_configuracion.SQLALCHEMY_DATABASE_URI

    # Inicializar extensiones con la instancia de aplicación
    db.init_app(app)
    gestor_sesiones.init_app(app)
    csrf.init_app(app)

    # Configuración de políticas de sesión y redirección de autenticación
    gestor_sesiones.login_view = 'autenticacion.iniciar_sesion'
    gestor_sesiones.login_message = 'Por favor inicia sesión con tu cuenta para acceder a este recurso.'
    gestor_sesiones.login_message_category = 'warning'

    # Asegurar la existencia de directorios para almacenamiento de archivos multimedia
    ruta_subidas = app.config.get('CARPETA_SUBIDAS')
    if ruta_subidas:
        os.makedirs(os.path.join(ruta_subidas, 'imagenes'), exist_ok=True)
        os.makedirs(os.path.join(ruta_subidas, 'videos'), exist_ok=True)
        os.makedirs(os.path.join(ruta_subidas, 'chat'), exist_ok=True)

    # Cargador de usuario para Flask-Login
    @gestor_sesiones.user_loader
    def cargar_usuario(id_usuario):
        from app.models.usuario import Usuario
        return Usuario.query.get(int(id_usuario))

    # Inyección de variables globales en plantillas Jinja2
    @app.context_processor
    def inyectar_variables_globales():
        return {
            'nombre_plataforma': 'ModaCircular - Intercambio Sostenible',
            'version_app': '1.0.0'
        }

    # Registro de Blueprints Modulares
    from app.routes.autenticacion import blueprint_autenticacion
    from app.routes.api_puntos import blueprint_api
    from app.routes.prendas import blueprint_prendas
    from app.routes.moderacion import blueprint_moderacion
    from app.routes.admin_tablas import blueprint_admin
    from app.routes.admin_usuarios import blueprint_admin_usuarios
    from app.routes.catalogo import blueprint_catalogo
    from app.routes.kardex import blueprint_kardex
    from app.routes.inventario import blueprint_inventario
    from app.routes.trueques import blueprint_trueques
    from app.routes.chat import blueprint_chat
    from app.routes.auditoria import blueprint_auditoria

    app.register_blueprint(blueprint_autenticacion)
    app.register_blueprint(blueprint_api)
    app.register_blueprint(blueprint_prendas)
    app.register_blueprint(blueprint_moderacion)
    app.register_blueprint(blueprint_admin)
    app.register_blueprint(blueprint_admin_usuarios)
    app.register_blueprint(blueprint_catalogo)
    app.register_blueprint(blueprint_kardex)
    app.register_blueprint(blueprint_inventario)
    app.register_blueprint(blueprint_trueques)
    app.register_blueprint(blueprint_chat)
    app.register_blueprint(blueprint_auditoria)

    # Eximir endpoints de API pública de validación CSRF para consumo AJAX fluido
    csrf.exempt(blueprint_api)

    # Ruta Raíz / Inicio del Sistema: Redirección directa al Catálogo Público de Exploración
    @app.route('/')
    def inicio():
        return redirect(url_for('catalogo.explorar'))

    return app
