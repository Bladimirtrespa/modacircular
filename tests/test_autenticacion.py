"""
Pruebas Automatizadas: Módulo de Autenticación y Billetera Dual
Valida el registro de usuarios, unicidad de correo, seguridad de hash y control de sesiones.
"""

from app import db
from app.models.usuario import Usuario


def test_registro_usuario_exitoso(cliente_http, aplicacion):
    """Prueba el registro de una nueva cuenta individual con doble billetera en 0."""
    correo_nuevo = 'andres.lopez.test@correo.com'
    
    # Limpieza preventiva
    with aplicacion.app_context():
        u = Usuario.query.filter_by(correo_electronico=correo_nuevo).first()
        if u:
            db.session.delete(u)
            db.session.commit()

    datos = {
        'nombre_completo': 'Andrés López',
        'correo_electronico': correo_nuevo,
        'telefono': '+57 320 987 6543',
        'ciudad_ubicacion': 'Pereira',
        'contrasena': 'Segura123*',
        'confirmar_contrasena': 'Segura123*'
    }

    respuesta = cliente_http.post('/autenticacion/registro', data=datos, follow_redirects=True)
    assert respuesta.status_code == 200

    with aplicacion.app_context():
        usuario_creado = Usuario.query.filter_by(correo_electronico=correo_nuevo).first()
        assert usuario_creado is not None
        assert usuario_creado.verificar_contrasena('Segura123*') is True
        assert usuario_creado.verificar_contrasena('ClaveErronea') is False
        assert usuario_creado.saldo_puntos_disponibles == 0
        assert usuario_creado.saldo_puntos_retenidos == 0
        assert usuario_creado.rol.nombre_rol.upper() in ('USUARIO', 'ADMINISTRADOR', 'ADMIN')


def test_rechazo_registro_correo_duplicado(cliente_http, aplicacion):
    """Verifica que el sistema rechace el registro de un correo ya existente en SQL Server."""
    datos_duplicados = {
        'nombre_completo': 'Usuario Duplicado',
        'correo_electronico': 'admin@modacircular.com',  # Correo ya existente
        'telefono': '+57 300 000 0000',
        'ciudad_ubicacion': 'Bogotá',
        'contrasena': 'OtraClave123*',
        'confirmar_contrasena': 'OtraClave123*'
    }

    respuesta = cliente_http.post('/autenticacion/registro', data=datos_duplicados)
    assert respuesta.status_code == 200
    assert 'Este correo electrónico ya se encuentra registrado' in respuesta.get_data(as_text=True)


def test_inicio_sesion_y_cierre(cliente_http):
    """Prueba el ciclo de inicio de sesión seguro y cierre de sesión."""
    # Inicio con credenciales incorrectas
    res_error = cliente_http.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'admin@modacircular.com',
        'contrasena': 'ClaveIncorrecta'
    })
    assert 'Credenciales incorrectas' in res_error.get_data(as_text=True)

    # Inicio exitoso
    res_ok = cliente_http.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'admin@modacircular.com',
        'contrasena': 'Admin123*'
    }, follow_redirects=True)
    assert res_ok.status_code == 200
    assert 'Disponibles:' in res_ok.get_data(as_text=True)

    # Cierre de sesión
    res_logout = cliente_http.get('/autenticacion/cerrar-sesion', follow_redirects=True)
    assert res_logout.status_code == 200
    assert 'Has cerrado tu sesión de forma segura' in res_logout.get_data(as_text=True)
