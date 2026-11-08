"""
Pruebas Automatizadas: Chat Interno y Logística de Envíos (Micro-paso 5)
Verifica la mensajería privada, actualización de ficha de despacho (transportadora y guía),
doble confirmación de entrega con cierre exitoso (+5 pts reputación) y control de acceso 403.
"""

import uuid
from datetime import datetime
from app import db
from app.models.usuario import Usuario
from app.models.sala_chat_intercambio import SalaChatIntercambio
from app.models.mensaje_chat import MensajeChat


def test_ciclo_completo_chat_y_logistica(cliente_http, aplicacion):
    """
    1. Crea una sala de chat entre dos usuarios válidos.
    2. Envía un mensaje desde usuario1.
    3. Actualiza la ficha logística (transportadora, guía, dirección).
    4. Confirma entrega por ambas partes y valida el estado CERRADA_EXITOSA y reputación.
    5. Intenta acceder con un tercer usuario y valida el bloqueo HTTP 403.
    """
    with aplicacion.app_context():
        u1 = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        u2 = Usuario.query.filter_by(correo_electronico='maria.gomez@correo.com').first()
        u3 = Usuario.query.filter_by(correo_electronico='test.comprador@correo.com').first()

        rep_u1_inicial = u1.reputacion_trueques or 100
        rep_u2_inicial = u2.reputacion_trueques or 100
        id_u1 = u1.id_usuario
        id_u2 = u2.id_usuario

        codigo_test = f"SALA-TEST-{uuid.uuid4().hex[:6].upper()}"
        sala = SalaChatIntercambio(
            codigo_sala=codigo_test,
            tipo_operacion='TRUEQUE_INVENTARIO',
            id_usuario_1=id_u1,
            id_usuario_2=id_u2,
            metodo_entrega='POR_DEFINIR',
            estado_sala='ACTIVA',
            fecha_apertura=datetime.utcnow()
        )
        db.session.add(sala)
        db.session.commit()
        id_sala = sala.id_sala_chat

    # Iniciar sesión como usuario1
    cliente_http.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'carlos.restrepo@correo.com',
        'contrasena': 'Usuario1234*'
    })

    # 1. Enviar mensaje en la sala
    res_msg = cliente_http.post(f'/chat/sala/{codigo_test}/enviar-mensaje', data={
        'contenido_mensaje': 'Hola María, acabo de empacar el paquete. Mañana lo despacho.'
    }, follow_redirects=True)
    assert res_msg.status_code == 200

    with aplicacion.app_context():
        msg = MensajeChat.query.filter_by(id_sala_chat=id_sala, es_mensaje_sistema=False).first()
        assert msg is not None
        assert "acabo de empacar" in msg.contenido_mensaje

    # 2. Actualizar ficha logística de despacho
    res_envio = cliente_http.post(f'/chat/sala/{codigo_test}/actualizar-envio', data={
        'metodo_entrega': 'ENVIO_DOMICILIO',
        'empresa_transportadora': 'Servientrega',
        'numero_guia_rastreo': 'SERVI-123456789',
        'direccion_envio': 'Calle 50 # 40-20 Apto 301',
        'ciudad_destino': 'Medellín',
        'nombre_receptor_envio': 'María Gómez',
        'telefono_contacto_envio': '+57 311 987 6543'
    }, follow_redirects=True)
    assert res_envio.status_code == 200

    with aplicacion.app_context():
        sala_db = db.session.get(SalaChatIntercambio, id_sala)
        assert sala_db.metodo_entrega == 'ENVIO_DOMICILIO'
        assert sala_db.empresa_transportadora == 'Servientrega'
        assert sala_db.numero_guia_rastreo == 'SERVI-123456789'

    # 3. Confirmar entrega por usuario1
    res_conf1 = cliente_http.post(f'/chat/sala/{codigo_test}/confirmar-entrega', follow_redirects=True)
    assert res_conf1.status_code == 200

    with aplicacion.app_context():
        sala_db = db.session.get(SalaChatIntercambio, id_sala)
        assert sala_db.confirmado_usuario_1 is True
        assert sala_db.confirmado_usuario_2 is False
        assert sala_db.estado_sala == 'ACTIVA'

    # Cambiar de sesión a usuario2 (María Gómez)
    cliente_http.get('/autenticacion/cerrar-sesion')
    cliente_http.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'maria.gomez@correo.com',
        'contrasena': 'Maria123*'
    })

    # 4. Confirmar entrega por usuario2 -> Debe cerrar la sala y sumar reputación
    res_conf2 = cliente_http.post(f'/chat/sala/{codigo_test}/confirmar-entrega', follow_redirects=True)
    assert res_conf2.status_code == 200

    with aplicacion.app_context():
        sala_db = db.session.get(SalaChatIntercambio, id_sala)
        assert sala_db.confirmado_usuario_1 is True
        assert sala_db.confirmado_usuario_2 is True
        assert sala_db.estado_sala == 'CERRADA_EXITOSA'
        assert sala_db.fecha_cierre is not None

        # Validar bono de reputación (+5 pts a ambos)
        u1_fin = db.session.get(Usuario, id_u1)
        u2_fin = db.session.get(Usuario, id_u2)
        assert u1_fin.reputacion_trueques == rep_u1_inicial + 5
        assert u2_fin.reputacion_trueques == rep_u2_inicial + 5

    # 5. Iniciar sesión con usuario3 (ajeno) y verificar bloqueo 403
    cliente_http.get('/autenticacion/cerrar-sesion')
    cliente_http.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'test.comprador@correo.com',
        'contrasena': 'Test1234*'
    })
    res_bloqueo = cliente_http.get(f'/chat/sala/{codigo_test}')
    assert res_bloqueo.status_code == 403

    # TEARDOWN
    with aplicacion.app_context():
        MensajeChat.query.filter_by(id_sala_chat=id_sala).delete()
        sala_del = db.session.get(SalaChatIntercambio, id_sala)
        db.session.delete(sala_del)
        u1_rst = db.session.get(Usuario, id_u1)
        u2_rst = db.session.get(Usuario, id_u2)
        u1_rst.reputacion_trueques = rep_u1_inicial
        u2_rst.reputacion_trueques = rep_u2_inicial
        db.session.commit()
