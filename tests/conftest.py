"""
Configuración de Fixtures y Entorno de Pruebas Automatizadas con pytest
Inicializa el cliente de pruebas, la base de datos de pruebas y fixtures desacoplados de sesión.
"""

import io
import pytest
from app import crear_app, db
from app.models.usuario import Usuario
from app.models.rol_usuario import RolUsuario


@pytest.fixture(scope='session')
def aplicacion():
    """Crea una instancia de la aplicación Flask en perfil de pruebas."""
    app = crear_app('pruebas')
    with app.app_context():
        yield app


@pytest.fixture(scope='function')
def cliente_http(aplicacion):
    """Cliente de pruebas HTTP para simular peticiones web."""
    c = aplicacion.test_client()
    yield c
    c.get('/autenticacion/cerrar-sesion')


@pytest.fixture(scope='function')
def id_usuario_comprador(aplicacion):
    """Fixture que asegura y provee el ID de un usuario comprador con saldo disponible."""
    with aplicacion.app_context():
        correo = 'test.comprador@correo.com'
        usuario = Usuario.query.filter_by(correo_electronico=correo).first()
        if not usuario:
            rol = RolUsuario.query.filter(RolUsuario.nombre_rol.in_(['USUARIO', 'ADMIN'])).first()
            usuario = Usuario(
                id_rol=rol.id_rol,
                nombre_completo='Usuario Comprador Test',
                correo_electronico=correo,
                telefono='+57 300 111 2233',
                ciudad_ubicacion='Cali',
                saldo_puntos_disponibles=500,
                saldo_puntos_retenidos=0,
                activo=True
            )
            usuario.establecer_contrasena('Test1234*')
            db.session.add(usuario)
            db.session.commit()
        else:
            usuario.saldo_puntos_disponibles = 500
            db.session.commit()
        return usuario.id_usuario


@pytest.fixture
def imagen_prueba_bytes():
    """Genera un archivo JPEG binario real y válido con Pillow para pruebas de subida."""
    from PIL import Image
    img = Image.new('RGB', (100, 100), color=(16, 185, 129))
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    return (buffer, 'evidencia_test.jpg')
