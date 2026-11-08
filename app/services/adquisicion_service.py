"""
Servicio de Dominio: Adquisición e Intercambio de Prendas y Accesorios
Orquesta de forma atómica (ACID) en SQL Server:
1. Validación de disponibilidad del artículo (estado 'PUBLICADA').
2. Validación de regla de negocio: el comprador no puede ser el propietario.
3. Validación de solvencia de puntos disponibles.
4. Débito de puntos en la billetera del comprador.
5. Transición de estado de la prenda a 'INTERCAMBIADA'.
6. Registro de la operación en Transacciones_Adquisicion.
7. Registro del asiento contable DEBITO_ADQUISICION en Historial_Movimientos_Puntos.
"""

import uuid
from datetime import datetime
from app import db
from app.models.usuario import Usuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.transaccion_adquisicion import TransaccionAdquisicion
from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos
from app.models.sala_chat_intercambio import SalaChatIntercambio
from app.models.mensaje_chat import MensajeChat


class AdquisicionService:
    """Servicio que ejecuta la transacción ACID de canje de prendas por puntos."""

    @classmethod
    def procesar_adquisicion(cls, id_prenda: int, id_usuario_comprador: int) -> TransaccionAdquisicion:
        """
        Ejecuta la adquisición completa de un artículo a cambio de puntos.
        
        :param id_prenda: Identificador de la prenda o accesorio a adquirir.
        :param id_usuario_comprador: Identificador del usuario que realiza la compra.
        :return: Entidad TransaccionAdquisicion registrada.
        :raises ValueError: Si no cumple alguna regla de negocio de canje o fondos insuficientes.
        """
        comprador = db.session.get(Usuario, id_usuario_comprador)
        if not comprador or not comprador.activo:
            raise ValueError("El usuario comprador no existe o se encuentra inactivo.")

        prenda = db.session.get(PrendaAccesorio, id_prenda)
        if not prenda:
            raise ValueError(f"La prenda con ID {id_prenda} no existe.")

        # 1. Validar que la prenda se encuentre publicada
        if prenda.estado_publicacion != 'PUBLICADA':
            raise ValueError(
                f"El artículo '{prenda.titulo_publicacion}' no está disponible para adquisición "
                f"(estado actual: {prenda.estado_publicacion})."
            )

        # 2. Validar que el comprador no sea el mismo propietario
        if prenda.id_usuario_propietario == comprador.id_usuario:
            raise ValueError("No puedes adquirir un artículo que te pertenece a ti mismo.")

        # 3. Validar solvencia de puntos disponibles
        puntos_requeridos = prenda.puntos_valoracion
        if comprador.saldo_puntos_disponibles < puntos_requeridos:
            raise ValueError(
                f"Saldo de puntos insuficiente. Tienes {comprador.saldo_puntos_disponibles} puntos disponibles "
                f"y el artículo requiere {puntos_requeridos} puntos."
            )

        propietario = prenda.propietario

        try:
            # 4. Transacción ACID: Débito de puntos al comprador
            saldo_anterior_comp = comprador.saldo_puntos_disponibles
            comprador.saldo_puntos_disponibles -= puntos_requeridos
            saldo_posterior_comp = comprador.saldo_puntos_disponibles

            # 5. Cambiar estado de la prenda a INTERCAMBIADA
            prenda.estado_publicacion = 'INTERCAMBIADA'

            # 6. Registrar en Transacciones_Adquisicion (estado COMPLETADA en SQL Server)
            transaccion = TransaccionAdquisicion(
                id_prenda=prenda.id_prenda,
                id_usuario_comprador=comprador.id_usuario,
                id_usuario_oferente=propietario.id_usuario,
                puntos_canjeados=puntos_requeridos,
                estado_entrega='COMPLETADA',
                fecha_transaccion=datetime.utcnow()
            )
            db.session.add(transaccion)
            db.session.flush()

            # 7. Asiento contable en Historial_Movimientos_Puntos (Kardex)
            descripcion_auditoria = (
                f"Débito de Canje: -{puntos_requeridos} pts por adquisición de '{prenda.titulo_publicacion[:30]}' | "
                f"Prenda ID {prenda.id_prenda} cedida por {propietario.nombre_completo[:25]} ({propietario.ciudad_ubicacion})"
            )
            if len(descripcion_auditoria) > 295:
                descripcion_auditoria = descripcion_auditoria[:295] + "..."

            movimiento = HistorialMovimientosPuntos(
                id_usuario=comprador.id_usuario,
                id_prenda_referencia=prenda.id_prenda,
                tipo_movimiento='DEBITO_ADQUISICION',
                cantidad_puntos=puntos_requeridos,
                saldo_anterior=saldo_anterior_comp,
                saldo_posterior=saldo_posterior_comp,
                descripcion_auditoria=descripcion_auditoria,
                fecha_movimiento=datetime.utcnow()
            )
            db.session.add(movimiento)

            # 8. Apertura de Sala Privada de Chat y Logística para la compra
            codigo_sala = f"SALA-PTS-{uuid.uuid4().hex[:8].upper()}"
            sala_chat = SalaChatIntercambio(
                codigo_sala=codigo_sala,
                tipo_operacion='ADQUISICION_PUNTOS',
                id_oferta_trueque=None,
                id_transaccion_adquisicion=transaccion.id_transaccion,
                id_usuario_1=comprador.id_usuario,
                id_usuario_2=propietario.id_usuario,
                metodo_entrega='POR_DEFINIR',
                direccion_envio=comprador.direccion_predeterminada,
                ciudad_destino=comprador.ciudad_ubicacion,
                nombre_receptor_envio=comprador.nombre_completo,
                telefono_contacto_envio=comprador.telefono,
                estado_sala='ACTIVA',
                fecha_apertura=datetime.utcnow()
            )
            db.session.add(sala_chat)
            db.session.flush()

            msg_inicial = MensajeChat(
                id_sala_chat=sala_chat.id_sala_chat,
                id_usuario_emisor=comprador.id_usuario,
                contenido_mensaje=(
                    f"¡Adquisición con puntos #{transaccion.id_transaccion} confirmada! "
                    f"Se han debitado {puntos_requeridos} pts del comprador. "
                    f"En esta sala pueden coordinar los detalles de despacho y entrega de '{prenda.titulo_publicacion}'."
                ),
                es_mensaje_sistema=True,
                fecha_envio=datetime.utcnow()
            )
            db.session.add(msg_inicial)

            db.session.commit()
            return transaccion

        except Exception as error_canje:
            db.session.rollback()
            raise error_canje
