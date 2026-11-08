"""
Pruebas Automatizadas: Adquisición de Prendas e Integridad del Kardex
Valida las transacciones ACID de canje, bloqueos de fondos y asientos contables.
"""

import pytest
from app import db
from app.models.usuario import Usuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.transaccion_adquisicion import TransaccionAdquisicion
from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos
from app.services.adquisicion_service import AdquisicionService


def test_adquisicion_exitosa_con_puntos(aplicacion, id_usuario_comprador):
    """
    Verifica que la compra con puntos descuente saldo, cambie estado a INTERCAMBIADA,
    registre la transacción y genere el asiento DEBITO_ADQUISICION.
    """
    with aplicacion.app_context():
        comprador = db.session.get(Usuario, id_usuario_comprador)
        assert comprador is not None

        # Buscar una prenda publicada que no pertenezca al comprador
        prenda = PrendaAccesorio.query.filter(
            PrendaAccesorio.estado_publicacion == 'PUBLICADA',
            PrendaAccesorio.id_usuario_propietario != comprador.id_usuario,
            PrendaAccesorio.puntos_valoracion <= comprador.saldo_puntos_disponibles
        ).first()

        assert prenda is not None, "Debe haber una prenda disponible para pruebas."
        id_prenda = prenda.id_prenda
        puntos = prenda.puntos_valoracion
        saldo_antes = comprador.saldo_puntos_disponibles

        # Ejecutar adquisición
        trx = AdquisicionService.procesar_adquisicion(
            id_prenda=id_prenda,
            id_usuario_comprador=comprador.id_usuario
        )

        assert trx is not None
        assert trx.puntos_canjeados == puntos
        assert trx.estado_entrega == 'COMPLETADA'

        # Verificar prenda actualizada
        prenda_actualizada = db.session.get(PrendaAccesorio, id_prenda)
        assert prenda_actualizada.estado_publicacion == 'INTERCAMBIADA'

        # Verificar saldo del comprador
        db.session.refresh(comprador)
        assert comprador.saldo_puntos_disponibles == saldo_antes - puntos

        # Verificar Kardex
        kardex = HistorialMovimientosPuntos.query.filter_by(
            id_usuario=comprador.id_usuario,
            id_prenda_referencia=id_prenda,
            tipo_movimiento='DEBITO_ADQUISICION'
        ).first()
        assert kardex is not None
        assert kardex.cantidad_puntos == puntos
        assert kardex.saldo_posterior == saldo_antes - puntos

        # Teardown: Revertir la adquisición para que la prenda siga disponible en el catálogo
        from app.models.sala_chat_intercambio import SalaChatIntercambio
        from app.models.mensaje_chat import MensajeChat
        salas = SalaChatIntercambio.query.filter_by(id_transaccion_adquisicion=trx.id_transaccion).all()
        for s in salas:
            MensajeChat.query.filter_by(id_sala_chat=s.id_sala_chat).delete()
            db.session.delete(s)
        db.session.delete(trx)
        db.session.delete(kardex)
        prenda_actualizada.estado_publicacion = 'PUBLICADA'
        comprador.saldo_puntos_disponibles = saldo_antes
        db.session.commit()


def test_bloqueo_adquisicion_prenda_propia(aplicacion, id_usuario_comprador):
    """Verifica que el sistema rechace si un usuario intenta adquirir su propio artículo."""
    with aplicacion.app_context():
        comprador = db.session.get(Usuario, id_usuario_comprador)

        # Buscar o crear prenda propia
        prenda_propia = PrendaAccesorio.query.filter_by(
            id_usuario_propietario=comprador.id_usuario,
            estado_publicacion='PUBLICADA'
        ).first()

        if not prenda_propia:
            prenda_publicada = PrendaAccesorio.query.filter_by(estado_publicacion='PUBLICADA').first()
            if prenda_publicada:
                prenda_publicada.id_usuario_propietario = comprador.id_usuario
                db.session.commit()
                prenda_propia = prenda_publicada

        if prenda_propia:
            with pytest.raises(ValueError) as err:
                AdquisicionService.procesar_adquisicion(
                    id_prenda=prenda_propia.id_prenda,
                    id_usuario_comprador=comprador.id_usuario
                )
            assert "te pertenece a ti mismo" in str(err.value)


def test_bloqueo_saldo_insuficiente(aplicacion):
    """Verifica que no se permita adquirir si el saldo de puntos disponibles es menor a los requeridos."""
    with aplicacion.app_context():
        correo_pobre = 'usuario.sin.puntos@correo.com'
        usuario_sin_puntos = Usuario.query.filter_by(correo_electronico=correo_pobre).first()
        if not usuario_sin_puntos:
            u_admin = Usuario.query.first()
            usuario_sin_puntos = Usuario(
                id_rol=u_admin.id_rol,
                nombre_completo='Usuario Sin Puntos',
                correo_electronico=correo_pobre,
                ciudad_ubicacion='Bogotá',
                saldo_puntos_disponibles=0,
                saldo_puntos_retenidos=0,
                activo=True
            )
            usuario_sin_puntos.establecer_contrasena('Clave123*')
            db.session.add(usuario_sin_puntos)
            db.session.commit()
        else:
            usuario_sin_puntos.saldo_puntos_disponibles = 0
            db.session.commit()

        prenda = PrendaAccesorio.query.filter_by(estado_publicacion='PUBLICADA').first()
        if prenda:
            with pytest.raises(ValueError) as err:
                AdquisicionService.procesar_adquisicion(
                    id_prenda=prenda.id_prenda,
                    id_usuario_comprador=usuario_sin_puntos.id_usuario
                )
            assert "insuficiente" in str(err.value).lower()
