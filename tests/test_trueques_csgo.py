"""
Pruebas Automatizadas: Negociación y Transacciones de Trueque Directo (Micro-paso 4)
Verifica la creación N a M, bloqueo temporal (RESERVADA_TRUEQUE),
aceptación atómica ACID con transferencia de titularidad y apertura de sala de chat,
y cancelación/rechazo con liberación de inventario.
"""

from datetime import datetime
from app import db
from app.models.usuario import Usuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.oferta_trueque import OfertaTrueque
from app.models.detalle_articulo_oferta import DetalleArticuloOferta
from app.models.sala_chat_intercambio import SalaChatIntercambio
from app.models.mensaje_chat import MensajeChat
from app.services.trueque_service import TruequeService


def test_flujo_completo_trueque_csgo(aplicacion):
    """
    Prueba el ciclo de vida completo de un trueque directo bilateral:
    1. Preparar 2 usuarios y prendas en EN_INVENTARIO.
    2. Crear oferta N a M -> Valida estado RESERVADA_TRUEQUE.
    3. Aceptar oferta -> Valida cambio de propietario, estado INTERCAMBIADA,
       bono de reputación y generación de SalaChatIntercambio.
    """
    with aplicacion.app_context():
        # Obtener 2 usuarios distintos
        usuario1 = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        usuario2 = Usuario.query.filter_by(correo_electronico='maria.gomez@correo.com').first()
        assert usuario1 is not None and usuario2 is not None

        rep_u1_antes = usuario1.reputacion_trueques or 100
        rep_u2_antes = usuario2.reputacion_trueques or 100

        # Crear 1 prenda de prueba para usuario1
        prenda_u1 = PrendaAccesorio(
            id_usuario_propietario=usuario1.id_usuario,
            id_categoria=1,
            id_material=1,
            id_estado_aspecto=1,
            id_nivel_utilidad=1,
            titulo_publicacion="Gorra Vintage Test U1",
            medida_largo_cm=20.0,
            talla="Única",
            procedencia="Vintage Store",
            motivo_cambio="Trueque de prueba",
            puntos_valoracion=80,
            modalidad_publicacion="INVENTARIO_TRUEQUE",
            estado_publicacion="EN_INVENTARIO",
            fecha_publicacion=datetime.utcnow()
        )
        db.session.add(prenda_u1)

        # Crear 1 prenda de prueba para usuario2
        prenda_u2 = PrendaAccesorio(
            id_usuario_propietario=usuario2.id_usuario,
            id_categoria=2,
            id_material=2,
            id_estado_aspecto=1,
            id_nivel_utilidad=1,
            titulo_publicacion="Bufanda Lana Test U2",
            medida_largo_cm=120.0,
            talla="M",
            procedencia="Artesanías",
            motivo_cambio="Trueque de prueba",
            puntos_valoracion=85,
            modalidad_publicacion="INVENTARIO_TRUEQUE",
            estado_publicacion="EN_INVENTARIO",
            fecha_publicacion=datetime.utcnow()
        )
        db.session.add(prenda_u2)
        db.session.commit()

        id_p1 = prenda_u1.id_prenda
        id_p2 = prenda_u2.id_prenda

        # 1. Crear la propuesta de trueque
        oferta = TruequeService.crear_oferta(
            usuario_ofertante=usuario1,
            id_usuario_receptor=usuario2.id_usuario,
            prendas_ofrecidas_ids=[id_p1],
            prendas_solicitadas_ids=[id_p2],
            mensaje_propuesta="¿Te interesa cambiar tu bufanda por mi gorra?"
        )

        assert oferta is not None
        assert oferta.estado_oferta == 'PENDIENTE'
        assert oferta.puntos_totales_ofrecidos == 80
        assert oferta.puntos_totales_solicitados == 85

        # Validar que los artículos quedaron bloqueados en RESERVADA_TRUEQUE
        assert prenda_u1.estado_publicacion == 'RESERVADA_TRUEQUE'
        assert prenda_u2.estado_publicacion == 'RESERVADA_TRUEQUE'

        # 2. El receptor (usuario2) acepta la oferta
        sala = TruequeService.aceptar_oferta(oferta.id_oferta_trueque, usuario2)

        assert sala is not None
        assert sala.codigo_sala.startswith("SALA-TRQ-")
        assert sala.tipo_operacion == 'TRUEQUE_INVENTARIO'
        assert sala.estado_sala == 'ACTIVA'

        # 3. Validar transferencia de titularidad atómica en SQL Server
        # Ahora prenda_u1 pertenece a usuario2 y prenda_u2 a usuario1
        db.session.refresh(prenda_u1)
        db.session.refresh(prenda_u2)
        assert prenda_u1.id_usuario_propietario == usuario2.id_usuario
        assert prenda_u1.estado_publicacion == 'INTERCAMBIADA'

        assert prenda_u2.id_usuario_propietario == usuario1.id_usuario
        assert prenda_u2.estado_publicacion == 'INTERCAMBIADA'

        # Validar incremento de reputación
        db.session.refresh(usuario1)
        db.session.refresh(usuario2)
        assert usuario1.reputacion_trueques == rep_u1_antes + 10
        assert usuario2.reputacion_trueques == rep_u2_antes + 10

        # TEARDOWN: Limpieza de registros de prueba
        MensajeChat.query.filter_by(id_sala_chat=sala.id_sala_chat).delete()
        db.session.delete(sala)
        DetalleArticuloOferta.query.filter_by(id_oferta_trueque=oferta.id_oferta_trueque).delete()
        db.session.delete(oferta)
        db.session.delete(prenda_u1)
        db.session.delete(prenda_u2)
        usuario1.reputacion_trueques = rep_u1_antes
        usuario2.reputacion_trueques = rep_u2_antes
        db.session.commit()


def test_rechazo_y_liberacion_trueque(aplicacion):
    """
    Verifica que al rechazar una oferta los artículos regresen a EN_INVENTARIO.
    """
    with aplicacion.app_context():
        usuario1 = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        usuario2 = Usuario.query.filter_by(correo_electronico='maria.gomez@correo.com').first()

        p1 = PrendaAccesorio(
            id_usuario_propietario=usuario1.id_usuario,
            id_categoria=1,
            id_material=1,
            id_estado_aspecto=1,
            id_nivel_utilidad=1,
            titulo_publicacion="Gorra Rechazo Test",
            medida_largo_cm=20.0,
            talla="Única",
            procedencia="Test",
            motivo_cambio="Test",
            puntos_valoracion=50,
            modalidad_publicacion="INVENTARIO_TRUEQUE",
            estado_publicacion="EN_INVENTARIO",
            fecha_publicacion=datetime.utcnow()
        )
        p2 = PrendaAccesorio(
            id_usuario_propietario=usuario2.id_usuario,
            id_categoria=1,
            id_material=1,
            id_estado_aspecto=1,
            id_nivel_utilidad=1,
            titulo_publicacion="Bufanda Rechazo Test",
            medida_largo_cm=20.0,
            talla="Única",
            procedencia="Test",
            motivo_cambio="Test",
            puntos_valoracion=50,
            modalidad_publicacion="INVENTARIO_TRUEQUE",
            estado_publicacion="EN_INVENTARIO",
            fecha_publicacion=datetime.utcnow()
        )
        db.session.add(p1)
        db.session.add(p2)
        db.session.commit()

        # Crear oferta
        oferta = TruequeService.crear_oferta(
            usuario_ofertante=usuario1,
            id_usuario_receptor=usuario2.id_usuario,
            prendas_ofrecidas_ids=[p1.id_prenda],
            prendas_solicitadas_ids=[p2.id_prenda]
        )

        assert p1.estado_publicacion == 'RESERVADA_TRUEQUE'
        assert p2.estado_publicacion == 'RESERVADA_TRUEQUE'

        # Rechazar
        TruequeService.rechazar_oferta(oferta.id_oferta_trueque, usuario2)

        db.session.refresh(p1)
        db.session.refresh(p2)
        assert p1.estado_publicacion == 'EN_INVENTARIO'
        assert p2.estado_publicacion == 'EN_INVENTARIO'
        assert oferta.estado_oferta == 'RECHAZADA'

        # Teardown
        DetalleArticuloOferta.query.filter_by(id_oferta_trueque=oferta.id_oferta_trueque).delete()
        db.session.delete(oferta)
        db.session.delete(p1)
        db.session.delete(p2)
        db.session.commit()
