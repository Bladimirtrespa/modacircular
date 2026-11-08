"""
Pruebas Automatizadas: Auditoría Antifraude, Reportes de Estafa y Resolución de Disputas (Micro-paso 6)
Verifica la radicación de denuncias formales, congelamiento preventivo inmutable de la sala de chat,
bloqueo de nuevos mensajes durante la disputa, e intervención pericial del Administrador con dictamen y sanciones.
"""

import uuid
from datetime import datetime
from app import db
from app.models.usuario import Usuario
from app.models.sala_chat_intercambio import SalaChatIntercambio
from app.models.mensaje_chat import MensajeChat
from app.models.reporte_comportamiento_estafa import ReporteComportamientoEstafa


def test_reporte_estafa_congela_sala_y_bloquea_mensajes(cliente_http, aplicacion):
    """
    1. Crea una sala activa entre Carlos Restrepo y María Gómez.
    2. Carlos radica una denuncia por INTENTO_ESTAFA.
    3. Valida que se cree el expediente pericial en Reportes_Comportamiento_Estafa.
    4. Valida que la sala pase al estado 'EN_DISPUTA_AUDITORIA' y se inserte mensaje de sistema.
    5. Intenta enviar un mensaje ordinario y verifica que el sistema lo rechaza por congelamiento.
    """
    with aplicacion.app_context():
        u1 = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        u2 = Usuario.query.filter_by(correo_electronico='maria.gomez@correo.com').first()
        id_u1 = u1.id_usuario
        id_u2 = u2.id_usuario

        codigo_test = f"SALA-DISP-{uuid.uuid4().hex[:6].upper()}"
        sala = SalaChatIntercambio(
            codigo_sala=codigo_test,
            tipo_operacion='TRUEQUE_INVENTARIO',
            id_usuario_1=id_u1,
            id_usuario_2=id_u2,
            metodo_entrega='ENVIO_DOMICILIO',
            estado_sala='ACTIVA',
            fecha_apertura=datetime.utcnow()
        )
        db.session.add(sala)
        db.session.commit()
        id_sala = sala.id_sala_chat

    # Iniciar sesión como usuario1 (Carlos)
    cliente_http.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'carlos.restrepo@correo.com',
        'contrasena': 'Usuario1234*'
    })

    # 1. Carlos radica el reporte formal
    res_rep = cliente_http.post(f'/chat/sala/{codigo_test}/reportar', data={
        'categoria_reporte': 'INTENTO_ESTAFA',
        'descripcion_hechos': 'El usuario afirma haber despachado pero el número de guía suministrado no existe en el sistema de la transportadora.'
    }, follow_redirects=True)
    assert res_rep.status_code == 200

    # 2. Verificar estado pericial en Base de Datos
    with aplicacion.app_context():
        sala_db = db.session.get(SalaChatIntercambio, id_sala)
        assert sala_db.estado_sala == 'EN_DISPUTA_AUDITORIA'

        reporte = ReporteComportamientoEstafa.query.filter_by(id_sala_chat=id_sala).first()
        assert reporte is not None
        assert reporte.categoria_reporte == 'INTENTO_ESTAFA'
        assert reporte.estado_reporte == 'PENDIENTE_REVISION'
        assert reporte.id_usuario_denunciante == id_u1
        assert reporte.id_usuario_denunciado == id_u2
        id_reporte = reporte.id_reporte

        # Validar existencia de mensaje de sistema alertando del congelamiento
        msg_sistema = MensajeChat.query.filter_by(id_sala_chat=id_sala, es_mensaje_sistema=True).first()
        assert msg_sistema is not None
        assert 'CONGELADA' in msg_sistema.contenido_mensaje

    # 3. Intentar enviar mensaje en la sala congelada -> Debe ser rechazado
    res_intento = cliente_http.post(f'/chat/sala/{codigo_test}/enviar-mensaje', data={
        'contenido_mensaje': 'Este mensaje no debería permitirse porque la sala está en auditoría.'
    }, follow_redirects=True)
    assert res_intento.status_code == 200

    with aplicacion.app_context():
        # Los mensajes ordinarios deben ser exactamente 0
        mensajes_usuario = MensajeChat.query.filter_by(id_sala_chat=id_sala, es_mensaje_sistema=False).count()
        assert mensajes_usuario == 0

    # TEARDOWN
    with aplicacion.app_context():
        MensajeChat.query.filter_by(id_sala_chat=id_sala).delete()
        ReporteComportamientoEstafa.query.filter_by(id_sala_chat=id_sala).delete()
        sala_del = db.session.get(SalaChatIntercambio, id_sala)
        db.session.delete(sala_del)
        db.session.commit()


def test_resolucion_disputa_admin_con_sancion(cliente_http, aplicacion):
    """
    1. Prepara una disputa formal en estado PENDIENTE_REVISION.
    2. El Administrador inicia sesión e inspecciona la bandeja de disputas.
    3. El Administrador abre el expediente pericial (cambia a EN_INVESTIGACION).
    4. El Administrador emite dictamen con sanción de suspensión temporal (7 días).
    5. Valida que el denunciado quede suspendido, reputación reducida y la sala CANCELADA_POR_FRAUDE.
    """
    with aplicacion.app_context():
        u1 = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        u2 = Usuario.query.filter_by(correo_electronico='maria.gomez@correo.com').first()
        id_u1 = u1.id_usuario
        id_u2 = u2.id_usuario
        rep_u2_inicial = u2.reputacion_trueques or 100

        codigo_test = f"SALA-DISP-{uuid.uuid4().hex[:6].upper()}"
        sala = SalaChatIntercambio(
            codigo_sala=codigo_test,
            tipo_operacion='TRUEQUE_INVENTARIO',
            id_usuario_1=id_u1,
            id_usuario_2=id_u2,
            metodo_entrega='ENVIO_DOMICILIO',
            estado_sala='EN_DISPUTA_AUDITORIA',
            fecha_apertura=datetime.utcnow()
        )
        db.session.add(sala)
        db.session.commit()
        id_sala = sala.id_sala_chat

        reporte = ReporteComportamientoEstafa(
            id_sala_chat=id_sala,
            id_usuario_denunciante=id_u1,
            id_usuario_denunciado=id_u2,
            categoria_reporte='NO_ENVIO_O_INCUMPLIMIENTO',
            descripcion_hechos='Pasaron más de 10 días y el usuario no responde ni envía el artículo.',
            estado_reporte='PENDIENTE_REVISION',
            fecha_reporte=datetime.utcnow()
        )
        db.session.add(reporte)
        db.session.commit()
        id_reporte = reporte.id_reporte

    # Iniciar sesión como Administrador
    cliente_http.get('/autenticacion/cerrar-sesion')
    cliente_http.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'bladimir@intercambioropa.co',
        'contrasena': 'Admin1234*'
    })

    # 1. Visitar la bandeja de disputas
    res_bandeja = cliente_http.get('/admin/disputas')
    assert res_bandeja.status_code == 200

    # 2. Visitar el detalle de la disputa (transiciona a EN_INVESTIGACION)
    res_detalle = cliente_http.get(f'/admin/disputas/{id_reporte}')
    assert res_detalle.status_code == 200

    with aplicacion.app_context():
        rep_db = db.session.get(ReporteComportamientoEstafa, id_reporte)
        assert rep_db.estado_reporte == 'EN_INVESTIGACION'

    # 3. Emitir Dictamen Sancionatorio
    res_resolver = cliente_http.post(f'/admin/disputas/{id_reporte}/resolver', data={
        'accion_resolucion': 'SANCION_SUSPENSION_TEMPORAL',
        'dias_suspension': '7',
        'dictamen_administrador': 'Se evidencia incumplimiento formal del envío pactado. Se aplica suspensión temporal de 7 días y penalización de reputación.'
    }, follow_redirects=True)
    assert res_resolver.status_code == 200

    with aplicacion.app_context():
        rep_resuelto = db.session.get(ReporteComportamientoEstafa, id_reporte)
        assert rep_resuelto.estado_reporte == 'RESUELTO_CON_SANCION'
        assert rep_resuelto.accion_aplicada == 'SUSPENSION_TEMPORAL_7_DIAS'

        sala_res = db.session.get(SalaChatIntercambio, id_sala)
        assert sala_res.estado_sala == 'CANCELADA_POR_FRAUDE'
        assert sala_res.fecha_cierre is not None

        u2_sancionado = db.session.get(Usuario, id_u2)
        assert u2_sancionado.esta_suspendido is True
        assert u2_sancionado.fecha_fin_suspension is not None
        assert u2_sancionado.reputacion_trueques == max(0, rep_u2_inicial - 40)

    # TEARDOWN
    with aplicacion.app_context():
        MensajeChat.query.filter_by(id_sala_chat=id_sala).delete()
        ReporteComportamientoEstafa.query.filter_by(id_sala_chat=id_sala).delete()
        sala_del = db.session.get(SalaChatIntercambio, id_sala)
        db.session.delete(sala_del)

        u2_rst = db.session.get(Usuario, id_u2)
        u2_rst.activo = True
        u2_rst.fecha_fin_suspension = None
        u2_rst.motivo_suspension = None
        u2_rst.reputacion_trueques = rep_u2_inicial
        db.session.commit()
