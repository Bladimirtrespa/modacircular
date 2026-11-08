"""
Pruebas Automatizadas de Administración, CRUDs y Sistema de Suspensiones
Verifica creación de materiales con 12 atributos, suspensión temporal y permanente,
reactivación automática y ajuste de saldo con trazabilidad contable.
"""

import uuid
from datetime import datetime
import pytest
from app import db
from app.models import Usuario, RolUsuario, Material, HistorialMovimientosPuntos


def autenticar_admin(cliente):
    """Inicia sesión formalmente como Administrador."""
    cliente.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'admin@modacircular.com',
        'contrasena': 'Admin123*'
    }, follow_redirects=True)


def cerrar_sesion(cliente):
    """Cierra la sesión del cliente."""
    cliente.get('/autenticacion/cerrar-sesion', follow_redirects=True)


def test_creacion_material_admin_12_columnas(aplicacion):
    """Verifica que el Administrador puede registrar un nuevo material con los 12 atributos en SQL Server."""
    cliente = aplicacion.test_client()
    autenticar_admin(cliente)

    sku_unico = f"TST-{uuid.uuid4().hex[:6].upper()}"
    nombre_mat = f"Material Test {uuid.uuid4().hex[:6]}"

    respuesta = cliente.post('/admin/materiales/crear', data={
        'codigo_material': sku_unico,
        'nombre_material': nombre_mat,
        'familia_material': 'Fibras Naturales Vegetales',
        'uso_principal': 'AMBOS',
        'factor_multiplicador': '1.75',
        'bono_puntos_material': '35',
        'nivel_sostenibilidad': 'Alto (Eco/Reciclado)',
        'descripcion_tecnica': 'Fibra ecológica de prueba para auditoría integral.',
        'activo': 'on'
    }, follow_redirects=True)

    assert respuesta.status_code == 200
    cerrar_sesion(cliente)

    with aplicacion.app_context():
        db.session.expire_all()
        material_creado = Material.query.filter_by(codigo_material=sku_unico).first()
        assert material_creado is not None
        assert material_creado.nombre_material == nombre_mat
        assert float(material_creado.factor_multiplicador) == 1.75
        assert material_creado.bono_puntos_material == 35
        assert material_creado.es_metal_o_joya_preciosa is False
        assert material_creado.requiere_aprobacion_especial is False
        assert material_creado.activo is True

        # Limpieza (Teardown) para no dejar materiales de prueba en SQL Server
        db.session.delete(material_creado)
        db.session.commit()


def test_suspension_temporal_usuario_y_bloqueo(aplicacion):
    """Verifica la aplicación de una suspensión temporal por horas y el bloqueo en inicio de sesión."""
    correo_test = f"usuario.sancion.{uuid.uuid4().hex[:6]}@correo.com"
    clave_plana = "ClaveSancion123*"

    with aplicacion.app_context():
        rol_usuario = RolUsuario.query.filter_by(nombre_rol='USUARIO').first()
        usuario_sancionado = Usuario(
            id_rol=rol_usuario.id_rol,
            nombre_completo='Usuario Para Sancionar',
            correo_electronico=correo_test,
            ciudad_ubicacion='Cali, Colombia',
            saldo_puntos_disponibles=50,
            saldo_puntos_retenidos=0,
            activo=True
        )
        usuario_sancionado.establecer_contrasena(clave_plana)
        db.session.add(usuario_sancionado)
        db.session.commit()
        id_usuario = usuario_sancionado.id_usuario

    # 1. Administrador aplica suspensión temporal de 48 horas
    cliente_admin = aplicacion.test_client()
    autenticar_admin(cliente_admin)

    respuesta_susp = cliente_admin.post(f'/admin/usuarios/suspender/{id_usuario}', data={
        'tipo_suspension': 'TEMPORAL',
        'duracion_valor': '48',
        'duracion_unidad': 'HORAS',
        'motivo_suspension': 'Infracción leve en descripción de prenda.'
    }, follow_redirects=True)
    assert respuesta_susp.status_code == 200
    assert "suspendida por 48 hora(s)" in respuesta_susp.get_data(as_text=True)

    with aplicacion.app_context():
        db.session.expire_all()
        usuario_verificado = db.session.get(Usuario, id_usuario)
        assert usuario_verificado.esta_suspendido is True
        assert usuario_verificado.fecha_fin_suspension > datetime.utcnow()

    # Cerrar sesión de admin para aislar el siguiente intento
    cerrar_sesion(cliente_admin)

    # 2. Intentar inicio de sesión con el usuario suspendido
    cliente_usuario = aplicacion.test_client()
    resp_login = cliente_usuario.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': correo_test,
        'contrasena': clave_plana
    }, follow_redirects=True)

    assert "suspendida temporalmente" in resp_login.get_data(as_text=True)

    # 3. Administrador vuelve a iniciar sesión y reactiva la cuenta
    autenticar_admin(cliente_admin)
    resp_reactivar = cliente_admin.post(f'/admin/usuarios/reactivar/{id_usuario}', follow_redirects=True)
    assert resp_reactivar.status_code == 200
    assert "reactivada exitosamente" in resp_reactivar.get_data(as_text=True)
    cerrar_sesion(cliente_admin)

    with aplicacion.app_context():
        db.session.expire_all()
        usuario_reactivado = db.session.get(Usuario, id_usuario)
        assert usuario_reactivado.esta_suspendido is False
        assert usuario_reactivado.fecha_fin_suspension is None


def test_suspension_permanente_usuario(aplicacion):
    """Verifica la suspensión permanente de un usuario."""
    correo_test = f"usuario.permanente.{uuid.uuid4().hex[:6]}@correo.com"
    clave_plana = "ClavePerm123*"

    with aplicacion.app_context():
        rol_usuario = RolUsuario.query.filter_by(nombre_rol='USUARIO').first()
        usuario_perm = Usuario(
            id_rol=rol_usuario.id_rol,
            nombre_completo='Usuario Infractor Grave',
            correo_electronico=correo_test,
            ciudad_ubicacion='Barranquilla, Colombia',
            saldo_puntos_disponibles=0,
            saldo_puntos_retenidos=0,
            activo=True
        )
        usuario_perm.establecer_contrasena(clave_plana)
        db.session.add(usuario_perm)
        db.session.commit()
        id_usuario = usuario_perm.id_usuario

    # Administrador suspende permanentemente
    cliente_admin = aplicacion.test_client()
    autenticar_admin(cliente_admin)

    resp_susp = cliente_admin.post(f'/admin/usuarios/suspender/{id_usuario}', data={
        'tipo_suspension': 'PERMANENTE',
        'motivo_suspension': 'Fraude reiterado en autenticidad de joyería.'
    }, follow_redirects=True)
    assert resp_susp.status_code == 200
    assert "PERMANENTE" in resp_susp.get_data(as_text=True)

    with aplicacion.app_context():
        db.session.expire_all()
        usuario_verificado = db.session.get(Usuario, id_usuario)
        assert usuario_verificado.esta_suspendido is True
        assert usuario_verificado.activo is False
        assert usuario_verificado.fecha_fin_suspension is None

    # Cerrar sesión de admin para aislar
    cerrar_sesion(cliente_admin)

    # Intentar inicio de sesión
    cliente_usuario = aplicacion.test_client()
    resp_login = cliente_usuario.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': correo_test,
        'contrasena': clave_plana
    }, follow_redirects=True)

    assert "suspendida permanentemente" in resp_login.get_data(as_text=True)


def test_ajuste_saldo_con_asiento_contable_historial(aplicacion):
    """Verifica que el ajuste de saldo crea el movimiento contable respetando la restricción CK_Historial_Tipo."""
    with aplicacion.app_context():
        usuario = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        id_usuario = usuario.id_usuario
        saldo_inicial = usuario.saldo_puntos_disponibles

    cliente_admin = aplicacion.test_client()
    autenticar_admin(cliente_admin)

    # Administrador suma 150 puntos por compensación
    resp = cliente_admin.post(f'/admin/usuarios/ajustar-saldo/{id_usuario}', data={
        'tipo_saldo': 'disponibles',
        'operacion': 'sumar',
        'cantidad_puntos': '150',
        'motivo_ajuste': 'Bono especial otorgado por fidelidad y economía circular.'
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert "ajustado a" in resp.get_data(as_text=True)
    cerrar_sesion(cliente_admin)

    with aplicacion.app_context():
        db.session.expire_all()
        usuario_actualizado = db.session.get(Usuario, id_usuario)
        assert usuario_actualizado.saldo_puntos_disponibles == saldo_inicial + 150

        # Verificar que se insertó el asiento contable en Historial_Movimientos_Puntos
        asiento = HistorialMovimientosPuntos.query.filter_by(
            id_usuario=id_usuario,
            cantidad_puntos=150
        ).order_by(HistorialMovimientosPuntos.id_movimiento.desc()).first()

        assert asiento is not None
        assert asiento.tipo_movimiento == 'CREDITO_PUBLICACION'
        assert "Ajuste Administrativo" in asiento.descripcion_auditoria
