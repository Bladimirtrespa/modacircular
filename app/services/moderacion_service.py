"""
Servicio de Dominio: Moderación de Joyas y Metales Preciosos
Orquesta de forma atómica (ACID) la aprobación o rechazo de piezas del Grupo F:
- Aprobación: Transfiere puntos de retenidos a disponibles y registra CREDITO_APROBACION_JOYA.
- Rechazo: Libera los puntos retenidos y marca la prenda como RECHAZADA.
"""

from datetime import datetime
from app import db
from app.models.solicitud_aprobacion_material import SolicitudAprobacionMaterial
from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos


class ModeracionService:
    """Servicio que ejecuta la resolución de solicitudes de joyería."""

    @classmethod
    def aprobar_solicitud(cls, id_solicitud: int, id_usuario_revisor: int, observaciones: str = None) -> SolicitudAprobacionMaterial:
        """
        Aprueba una solicitud de joyería y ejecuta la transferencia atómica de puntos.
        
        :param id_solicitud: Identificador de la solicitud en Solicitudes_Aprobacion_Material.
        :param id_usuario_revisor: Identificador del moderador o administrador que autoriza.
        :param observaciones: Justificación o dictamen técnico del moderador.
        :return: Entidad SolicitudAprobacionMaterial actualizada.
        :raises ValueError: Si la solicitud no existe o no se encuentra en estado PENDIENTE.
        """
        solicitud = db.session.get(SolicitudAprobacionMaterial, id_solicitud)
        if not solicitud:
            raise ValueError(f"La solicitud de aprobación con ID {id_solicitud} no existe.")

        if solicitud.estado_revision != 'PENDIENTE':
            raise ValueError(f"La solicitud ya se encuentra resuelta con estado '{solicitud.estado_revision}'.")

        prenda = solicitud.prenda
        propietario = prenda.propietario
        puntos = prenda.puntos_valoracion

        try:
            # 1. Actualizar el estado de la solicitud
            solicitud.estado_revision = 'APROBADA'
            solicitud.id_usuario_revisor = id_usuario_revisor
            solicitud.observaciones_revisor = observaciones or "Autenticidad y sellos de contraste verificados conforme."
            solicitud.fecha_resolucion = datetime.utcnow()

            # 2. Publicar la prenda en el catálogo
            prenda.estado_publicacion = 'PUBLICADA'

            # 3. Transferir puntos retenidos a disponibles en la billetera del propietario
            saldo_anterior_disp = propietario.saldo_puntos_disponibles
            propietario.saldo_puntos_retenidos = max(0, propietario.saldo_puntos_retenidos - puntos)
            propietario.saldo_puntos_disponibles += puntos
            saldo_posterior_disp = propietario.saldo_puntos_disponibles

            # 4. Insertar asiento contable inmutable en Historial_Movimientos_Puntos
            descripcion_auditoria = (
                f"Aprobación de Joya: Transferidos {puntos} pts de retenidos a disponibles | "
                f"Prenda ID {prenda.id_prenda} ({prenda.material.nombre_material}) | "
                f"Dictamen: {solicitud.observaciones_revisor[:100]}"
            )
            if len(descripcion_auditoria) > 295:
                descripcion_auditoria = descripcion_auditoria[:295] + "..."

            movimiento = HistorialMovimientosPuntos(
                id_usuario=propietario.id_usuario,
                id_prenda_referencia=prenda.id_prenda,
                tipo_movimiento='CREDITO_APROBACION_JOYA',
                cantidad_puntos=puntos,
                saldo_anterior=saldo_anterior_disp,
                saldo_posterior=saldo_posterior_disp,
                descripcion_auditoria=descripcion_auditoria,
                fecha_movimiento=datetime.utcnow()
            )
            db.session.add(movimiento)

            db.session.commit()
            return solicitud

        except Exception as error_aprobacion:
            db.session.rollback()
            raise error_aprobacion

    @classmethod
    def rechazar_solicitud(cls, id_solicitud: int, id_usuario_revisor: int, motivo_rechazo: str) -> SolicitudAprobacionMaterial:
        """
        Rechaza una solicitud de joyería, desestima los puntos retenidos y marca la prenda rechazada.
        
        :param id_solicitud: Identificador de la solicitud.
        :param id_usuario_revisor: Identificador del moderador que dictamina el rechazo.
        :param motivo_rechazo: Razón justificada del rechazo.
        :return: Entidad SolicitudAprobacionMaterial rechazada.
        :raises ValueError: Si el motivo está vacío o la solicitud no está pendiente.
        """
        if not motivo_rechazo or not motivo_rechazo.strip():
            raise ValueError("Debes ingresar un motivo o justificación clara para el rechazo de la solicitud.")

        solicitud = db.session.get(SolicitudAprobacionMaterial, id_solicitud)
        if not solicitud:
            raise ValueError(f"La solicitud con ID {id_solicitud} no existe.")

        if solicitud.estado_revision != 'PENDIENTE':
            raise ValueError(f"La solicitud ya se encuentra resuelta con estado '{solicitud.estado_revision}'.")

        prenda = solicitud.prenda
        propietario = prenda.propietario
        puntos = prenda.puntos_valoracion

        try:
            # 1. Actualizar solicitud
            solicitud.estado_revision = 'RECHAZADA'
            solicitud.id_usuario_revisor = id_usuario_revisor
            solicitud.observaciones_revisor = motivo_rechazo.strip()
            solicitud.fecha_resolucion = datetime.utcnow()

            # 2. Marcar prenda como rechazada
            prenda.estado_publicacion = 'RECHAZADA'

            # 3. Descontar los puntos retenidos que no llegaron a ser aprobados
            propietario.saldo_puntos_retenidos = max(0, propietario.saldo_puntos_retenidos - puntos)

            db.session.commit()
            return solicitud

        except Exception as error_rechazo:
            db.session.rollback()
            raise error_rechazo
