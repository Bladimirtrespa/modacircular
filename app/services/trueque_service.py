"""
Servicio de Dominio: Negociación y Transacciones de Trueque Directo
Gestiona la creación de ofertas N a M, reserva preventiva de inventario,
aceptación atómica ACID con transferencia de propietarios, rechazo, cancelación y apertura de sala de chat.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from app import db
from app.models.usuario import Usuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.oferta_trueque import OfertaTrueque
from app.models.detalle_articulo_oferta import DetalleArticuloOferta
from app.models.sala_chat_intercambio import SalaChatIntercambio
from app.models.mensaje_chat import MensajeChat


class TruequeService:
    """Motor transaccional para la mecánica de trueques directos bilaterales."""

    @classmethod
    def crear_oferta(
        cls,
        usuario_ofertante: Usuario,
        id_usuario_receptor: int,
        prendas_ofrecidas_ids: List[int],
        prendas_solicitadas_ids: List[int],
        mensaje_propuesta: Optional[str] = None,
        id_oferta_padre: Optional[int] = None
    ) -> OfertaTrueque:
        """
        Crea una propuesta de trueque N a M bloqueando preventivamente los artículos involucrados.
        """
        if usuario_ofertante.id_usuario == id_usuario_receptor:
            raise ValueError("No puedes proponer un trueque contigo mismo.")

        receptor = db.session.get(Usuario, id_usuario_receptor)
        if not receptor or not receptor.activo:
            raise ValueError("El usuario receptor no existe o se encuentra inactivo.")

        if not prendas_ofrecidas_ids:
            raise ValueError("Debes ofrecer al menos un artículo de tu inventario.")
        if not prendas_solicitadas_ids:
            raise ValueError("Debes solicitar al menos un artículo del inventario del receptor.")

        # 1. Validar y bloquear artículos ofrecidos por el emisor
        prendas_ofrecidas = []
        puntos_ofrecidos = 0
        for id_p in set(prendas_ofrecidas_ids):
            prenda = db.session.get(PrendaAccesorio, id_p)
            if not prenda or prenda.id_usuario_propietario != usuario_ofertante.id_usuario:
                raise ValueError(f"El artículo con ID {id_p} no te pertenece.")
            if prenda.estado_publicacion not in ('EN_INVENTARIO', 'PUBLICADA'):
                raise ValueError(f"El artículo '{prenda.titulo_publicacion}' no está disponible para trueque (estado: {prenda.estado_publicacion}).")
            prendas_ofrecidas.append(prenda)
            puntos_ofrecidos += prenda.puntos_valoracion

        # 2. Validar y bloquear artículos solicitados al receptor
        prendas_solicitadas = []
        puntos_solicitados = 0
        for id_p in set(prendas_solicitadas_ids):
            prenda = db.session.get(PrendaAccesorio, id_p)
            if not prenda or prenda.id_usuario_propietario != id_usuario_receptor:
                raise ValueError(f"El artículo con ID {id_p} no pertenece al receptor.")
            if prenda.estado_publicacion not in ('EN_INVENTARIO', 'PUBLICADA'):
                raise ValueError(f"El artículo '{prenda.titulo_publicacion}' no está disponible para intercambio.")
            prendas_solicitadas.append(prenda)
            puntos_solicitados += prenda.puntos_valoracion

        # 3. Transacción ACID: Reservar prendas y persistir oferta
        try:
            # Marcar todas las prendas en RESERVADA_TRUEQUE para prevenir colisiones concurrentes
            for p in prendas_ofrecidas + prendas_solicitadas:
                p.estado_publicacion = 'RESERVADA_TRUEQUE'

            nueva_oferta = OfertaTrueque(
                id_usuario_ofertante=usuario_ofertante.id_usuario,
                id_usuario_receptor=id_usuario_receptor,
                id_oferta_padre=id_oferta_padre,
                mensaje_propuesta=mensaje_propuesta.strip() if mensaje_propuesta else None,
                puntos_totales_ofrecidos=puntos_ofrecidos,
                puntos_totales_solicitados=puntos_solicitados,
                estado_oferta='PENDIENTE',
                fecha_creacion=datetime.utcnow()
            )
            db.session.add(nueva_oferta)
            db.session.flush()

            # Agregar detalles de artículos ofrecidos
            for p in prendas_ofrecidas:
                det = DetalleArticuloOferta(
                    id_oferta_trueque=nueva_oferta.id_oferta_trueque,
                    id_prenda=p.id_prenda,
                    rol_articulo='OFRECIDO',
                    puntos_referencia_momento=p.puntos_valoracion
                )
                db.session.add(det)

            # Agregar detalles de artículos solicitados
            for p in prendas_solicitadas:
                det = DetalleArticuloOferta(
                    id_oferta_trueque=nueva_oferta.id_oferta_trueque,
                    id_prenda=p.id_prenda,
                    rol_articulo='SOLICITADO',
                    puntos_referencia_momento=p.puntos_valoracion
                )
                db.session.add(det)

            # Si es una contraoferta, marcar la oferta padre como CONTRAOFERTA
            if id_oferta_padre:
                oferta_padre = db.session.get(OfertaTrueque, id_oferta_padre)
                if oferta_padre and oferta_padre.estado_oferta == 'PENDIENTE':
                    oferta_padre.estado_oferta = 'CONTRAOFERTA'
                    oferta_padre.fecha_resolucion = datetime.utcnow()

            db.session.commit()
            return nueva_oferta

        except Exception as err:
            db.session.rollback()
            raise err

    @classmethod
    def aceptar_oferta(cls, id_oferta: int, usuario_actual: Usuario) -> SalaChatIntercambio:
        """
        Acepta atómicamente la oferta de trueque en SQL Server:
        - Transfiere el propietario de todas las prendas ofrecidas al receptor.
        - Transfiere el propietario de todas las prendas solicitadas al ofertante.
        - Actualiza estado a INTERCAMBIADA.
        - Genera sala privada de chat para logística y entrega.
        """
        oferta = db.session.get(OfertaTrueque, id_oferta)
        if not oferta:
            raise ValueError("La oferta de trueque especificada no existe.")

        if oferta.id_usuario_receptor != usuario_actual.id_usuario:
            raise ValueError("Solo el usuario receptor de la propuesta puede aceptarla.")

        if oferta.estado_oferta != 'PENDIENTE':
            raise ValueError(f"La oferta ya no está pendiente (estado actual: {oferta.estado_oferta}).")

        try:
            # 1. Transferir artículos ofrecidos -> Al receptor
            for det in oferta.articulos_ofrecidos:
                prenda = det.prenda
                prenda.id_usuario_propietario = oferta.id_usuario_receptor
                prenda.estado_publicacion = 'INTERCAMBIADA'

            # 2. Transferir artículos solicitados -> Al ofertante
            for det in oferta.articulos_solicitados:
                prenda = det.prenda
                prenda.id_usuario_propietario = oferta.id_usuario_ofertante
                prenda.estado_publicacion = 'INTERCAMBIADA'

            # 3. Cerrar oferta como ACEPTADA
            oferta.estado_oferta = 'ACEPTADA'
            oferta.fecha_resolucion = datetime.utcnow()

            # 4. Bonificación de reputación comunitaria (+10 pts para ambos)
            ofertante = db.session.get(Usuario, oferta.id_usuario_ofertante)
            receptor = db.session.get(Usuario, oferta.id_usuario_receptor)
            if ofertante:
                ofertante.reputacion_trueques = (ofertante.reputacion_trueques or 100) + 10
            if receptor:
                receptor.reputacion_trueques = (receptor.reputacion_trueques or 100) + 10

            # 5. Apertura automática de Sala Privada de Chat
            codigo_sala = f"SALA-TRQ-{uuid.uuid4().hex[:8].upper()}"
            sala_chat = SalaChatIntercambio(
                codigo_sala=codigo_sala,
                tipo_operacion='TRUEQUE_INVENTARIO',
                id_oferta_trueque=oferta.id_oferta_trueque,
                id_transaccion_adquisicion=None,
                id_usuario_1=oferta.id_usuario_ofertante,
                id_usuario_2=oferta.id_usuario_receptor,
                metodo_entrega='POR_DEFINIR',
                estado_sala='ACTIVA',
                fecha_apertura=datetime.utcnow()
            )
            db.session.add(sala_chat)
            db.session.flush()

            # Mensaje inicial de sistema en la sala
            msg_sistema = MensajeChat(
                id_sala_chat=sala_chat.id_sala_chat,
                id_usuario_emisor=oferta.id_usuario_receptor,
                contenido_mensaje=(
                    f"¡Oferta de trueque #{oferta.id_oferta_trueque} ACEPTADA con éxito! "
                    f"La titularidad de los artículos ha sido transferida en SQL Server. "
                    f"Utilicen esta sala privada para acordar el método de entrega (presencial o envío a domicilio) "
                    f"y diligenciar la guía de transporte."
                ),
                es_mensaje_sistema=True,
                fecha_envio=datetime.utcnow()
            )
            db.session.add(msg_sistema)

            db.session.commit()
            return sala_chat

        except Exception as err:
            db.session.rollback()
            raise err

    @classmethod
    def rechazar_oferta(cls, id_oferta: int, usuario_actual: Usuario) -> None:
        """
        Rechaza la oferta y libera los artículos regresándolos a EN_INVENTARIO.
        """
        oferta = db.session.get(OfertaTrueque, id_oferta)
        if not oferta:
            raise ValueError("La oferta no existe.")

        if oferta.id_usuario_receptor != usuario_actual.id_usuario:
            raise ValueError("Solo el receptor puede rechazar la propuesta.")

        if oferta.estado_oferta != 'PENDIENTE':
            raise ValueError("La oferta no se encuentra pendiente.")

        try:
            # Liberar todas las prendas reservadas
            for det in oferta.articulos_detalle:
                if det.prenda.estado_publicacion == 'RESERVADA_TRUEQUE':
                    det.prenda.estado_publicacion = 'EN_INVENTARIO'

            oferta.estado_oferta = 'RECHAZADA'
            oferta.fecha_resolucion = datetime.utcnow()
            db.session.commit()

        except Exception as err:
            db.session.rollback()
            raise err

    @classmethod
    def cancelar_oferta(cls, id_oferta: int, usuario_actual: Usuario) -> None:
        """
        Permite al emisor cancelar su propuesta pendiente liberando las prendas.
        """
        oferta = db.session.get(OfertaTrueque, id_oferta)
        if not oferta:
            raise ValueError("La oferta no existe.")

        if oferta.id_usuario_ofertante != usuario_actual.id_usuario:
            raise ValueError("Solo el usuario que envió la propuesta puede cancelarla.")

        if oferta.estado_oferta != 'PENDIENTE':
            raise ValueError("Solo se pueden cancelar ofertas en estado PENDIENTE.")

        try:
            # Liberar prendas reservadas
            for det in oferta.articulos_detalle:
                if det.prenda.estado_publicacion == 'RESERVADA_TRUEQUE':
                    det.prenda.estado_publicacion = 'EN_INVENTARIO'

            oferta.estado_oferta = 'CANCELADA'
            oferta.fecha_resolucion = datetime.utcnow()
            db.session.commit()

        except Exception as err:
            db.session.rollback()
            raise err
