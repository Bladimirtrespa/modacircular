"""
Controlador de Auditoría Antifraude, Reportes de Estafa y Resolución de Disputas (Blueprint de Auditoría)
Permite a los usuarios radicar denuncias formales con evidencia en salas de chat, congelando el espacio
e impidiendo manipulación de registros mientras el Administrador audita, emite dictamen, aplica sanciones
o revierte contablemente transacciones fraudulentas.
"""

import os
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models.sala_chat_intercambio import SalaChatIntercambio
from app.models.mensaje_chat import MensajeChat
from app.models.reporte_comportamiento_estafa import ReporteComportamientoEstafa
from app.models.usuario import Usuario
from app.models.transaccion_adquisicion import TransaccionAdquisicion
from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos
from app.models.prenda_accesorio import PrendaAccesorio

blueprint_auditoria = Blueprint('auditoria', __name__)

EXTENSIONES_PERMITIDAS_EVIDENCIA = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
CATEGORIAS_VALIDAS = {
    'INTENTO_ESTAFA',
    'ARTICULO_FALSIFICADO_O_DISTINTO',
    'NO_ENVIO_O_INCUMPLIMIENTO',
    'LENGUAJE_OFENSIVO_O_ACOSO',
    'SOLICITUD_DINERO_EXTERNO'
}


# ==============================================================================
# RADICACIÓN DE REPORTES POR USUARIOS (CONGELAMIENTO PERICIAL)
# ==============================================================================

@blueprint_auditoria.route('/chat/sala/<string:codigo_sala>/reportar', methods=['POST'], endpoint='crear_reporte')
@blueprint_auditoria.route('/auditoria/sala/<string:codigo_sala>/reportar', methods=['POST'])
@login_required
def reportar_sala(codigo_sala: str):
    """
    Radica una denuncia formal sobre una sala de intercambio o adquisición.
    Congela inmediatamente la sala en estado 'EN_DISPUTA_AUDITORIA', impidiendo
    que cualquiera de las partes envíe más mensajes o altere información.
    """
    sala = SalaChatIntercambio.query.filter_by(codigo_sala=codigo_sala).first_or_404()

    # Validar que el denunciante pertenezca a la sala o sea Administrador
    if current_user.id_usuario not in (sala.id_usuario_1, sala.id_usuario_2) and not current_user.es_administrador:
        abort(403)

    if sala.estado_sala in ('CERRADA_EXITOSA', 'CANCELADA_POR_FRAUDE'):
        flash(f"La sala ya se encuentra en estado '{sala.estado_sala}' y no admite nuevos reportes.", "warning")
        return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))

    categoria = request.form.get('categoria_reporte', '').strip().upper()
    if categoria not in CATEGORIAS_VALIDAS:
        flash("La categoría del reporte seleccionada no es válida.", "danger")
        return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))

    descripcion = request.form.get('descripcion_hechos', '').strip()
    if len(descripcion) < 10:
        flash("La descripción de los hechos debe contener al menos 10 caracteres explicativos.", "warning")
        return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))

    # Determinar el usuario denunciado (la contraparte en la sala)
    id_denunciado = sala.id_usuario_2 if current_user.id_usuario == sala.id_usuario_1 else sala.id_usuario_1

    # Procesar evidencia adjunta si se suministró
    archivo_evidencia = request.files.get('evidencia')
    ruta_evidencia = None

    if archivo_evidencia and archivo_evidencia.filename and archivo_evidencia.filename.strip():
        nombre_original = secure_filename(archivo_evidencia.filename)
        ext = nombre_original.rsplit('.', 1)[-1].lower() if '.' in nombre_original else ''
        if ext in EXTENSIONES_PERMITIDAS_EVIDENCIA:
            carpeta_reportes = os.path.join(current_app.config['CARPETA_SUBIDAS'], 'reportes')
            os.makedirs(carpeta_reportes, exist_ok=True)
            nombre_archivo = f"evidencia_sala_{sala.id_sala_chat}_{uuid.uuid4().hex[:10]}.{ext}"
            archivo_evidencia.save(os.path.join(carpeta_reportes, nombre_archivo))
            ruta_evidencia = f"uploads/reportes/{nombre_archivo}"
        else:
            flash("Formato de evidencia no permitido. Formatos admitidos: PNG, JPG, JPEG, WEBP, PDF.", "warning")

    try:
        # 1. Crear el expediente pericial en Reportes_Comportamiento_Estafa
        reporte = ReporteComportamientoEstafa(
            id_sala_chat=sala.id_sala_chat,
            id_usuario_denunciante=current_user.id_usuario,
            id_usuario_denunciado=id_denunciado,
            categoria_reporte=categoria,
            descripcion_hechos=descripcion,
            ruta_evidencia_reporte=ruta_evidencia,
            estado_reporte='PENDIENTE_REVISION',
            fecha_reporte=datetime.utcnow()
        )
        db.session.add(reporte)

        # 2. Congelar atómicamente la sala
        sala.estado_sala = 'EN_DISPUTA_AUDITORIA'

        # 3. Registrar mensaje inmutable del sistema informando a las partes
        categoria_formateada = categoria.replace('_', ' ')
        mensaje_sistema = MensajeChat(
            id_sala_chat=sala.id_sala_chat,
            id_usuario_emisor=current_user.id_usuario,
            contenido_mensaje=(
                f"ALERTA PERICIAL: El usuario '{current_user.nombre_completo}' ha radicado un reporte formal "
                f"bajo la causal '{categoria_formateada}'. La sala ha sido CONGELADA preventivamente y los registros "
                f"remitidos a la Bandeja de Auditoría Antifraude del Administrador. No se permiten nuevos mensajes."
            ),
            ruta_adjunto=None,
            es_mensaje_sistema=True,
            leido=False,
            fecha_envio=datetime.utcnow()
        )
        db.session.add(mensaje_sistema)
        db.session.commit()

        flash(
            "Reporte radicado con éxito. La sala fue congelada preventivamente y el caso remitido a la Bandeja de Auditoría del Administrador.",
            "warning"
        )
    except Exception as err:
        db.session.rollback()
        flash(f"Error al radicar el reporte de disputa: {str(err)}", "danger")

    return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))


# ==============================================================================
# BANDEJA DE AUDITORÍA Y DISPUTAS DEL ADMINISTRADOR
# ==============================================================================

@blueprint_auditoria.route('/admin/disputas', methods=['GET'])
@login_required
def listar_disputas():
    """
    Bandeja exclusiva del Administrador para supervisar y auditar controversias,
    intentos de fraude, falsificaciones o incumplimientos reportados.
    """
    if not current_user.es_administrador:
        abort(403)

    filtro_estado = request.args.get('estado', '').strip().upper()
    filtro_categoria = request.args.get('categoria', '').strip().upper()

    consulta = ReporteComportamientoEstafa.query

    if filtro_estado and filtro_estado in ('PENDIENTE_REVISION', 'EN_INVESTIGACION', 'RESUELTO_CON_SANCION', 'DESESTIMADO'):
        consulta = consulta.filter_by(estado_reporte=filtro_estado)

    if filtro_categoria and filtro_categoria in CATEGORIAS_VALIDAS:
        consulta = consulta.filter_by(categoria_reporte=filtro_categoria)

    reportes = consulta.order_by(ReporteComportamientoEstafa.fecha_reporte.desc()).all()

    # Métricas para indicadores superiores
    metricas = {
        'total': ReporteComportamientoEstafa.query.count(),
        'pendientes': ReporteComportamientoEstafa.query.filter_by(estado_reporte='PENDIENTE_REVISION').count(),
        'en_investigacion': ReporteComportamientoEstafa.query.filter_by(estado_reporte='EN_INVESTIGACION').count(),
        'resueltos': ReporteComportamientoEstafa.query.filter_by(estado_reporte='RESUELTO_CON_SANCION').count(),
        'desestimados': ReporteComportamientoEstafa.query.filter_by(estado_reporte='DESESTIMADO').count(),
    }

    return render_template(
        'admin/disputas.html',
        reportes=reportes,
        metricas=metricas,
        filtro_estado=filtro_estado,
        filtro_categoria=filtro_categoria
    )


@blueprint_auditoria.route('/admin/disputas/<int:id_reporte>', methods=['GET'])
@login_required
def ver_disputa(id_reporte: str):
    """
    Visor pericial de auditoría: despliega el expediente de la controversia,
    los participantes, la evidencia adjunta, el historial íntegro de la sala de chat
    y la consola de resolución / sanciones para el Administrador.
    """
    if not current_user.es_administrador:
        abort(403)

    reporte = ReporteComportamientoEstafa.query.get_or_404(id_reporte)

    # Si está pendiente, transicionar a EN_INVESTIGACION para trazabilidad
    if reporte.estado_reporte == 'PENDIENTE_REVISION':
        reporte.estado_reporte = 'EN_INVESTIGACION'
        reporte.id_admin_revisor = current_user.id_usuario
        db.session.commit()

    sala = reporte.sala
    mensajes = sala.mensajes.order_by(MensajeChat.fecha_envio.asc()).all()

    # Obtener detalles de la transacción o trueque asociado
    transaccion = sala.transaccion_adquisicion
    oferta_trueque = sala.oferta_trueque

    return render_template(
        'admin/detalle_disputa.html',
        reporte=reporte,
        sala=sala,
        mensajes=mensajes,
        transaccion=transaccion,
        oferta_trueque=oferta_trueque
    )


@blueprint_auditoria.route('/admin/disputas/<int:id_reporte>/resolver', methods=['POST'])
@login_required
def resolver_disputa(id_reporte: int):
    """
    Ejecuta el dictamen pericial del Administrador sobre un reporte de fraude o disputa.
    Permite:
    1. Desestimar el reporte (reactivando la sala).
    2. Sanción con advertencia y penalización de reputación (-20 pts).
    3. Sanción con suspensión temporal (N días), penalización de reputación (-40 pts) y cierre fraudulento.
    4. Sanción con expulsión permanente del usuario denunciado y cierre definitivo.
    5. Reversión contable opcional de puntos ('REVERSION_POR_DISPUTA') en compras por puntos.
    """
    if not current_user.es_administrador:
        abort(403)

    reporte = ReporteComportamientoEstafa.query.get_or_404(id_reporte)
    accion = request.form.get('accion_resolucion', '').strip().upper()
    dictamen = request.form.get('dictamen_administrador', '').strip()
    revertir_puntos = request.form.get('revertir_puntos') in ('1', 'on', 'true', 'True')

    if len(dictamen) < 10:
        flash("El dictamen del Administrador debe incluir una justificación pericial de al menos 10 caracteres.", "warning")
        return redirect(url_for('auditoria.ver_disputa', id_reporte=id_reporte))

    sala = reporte.sala
    denunciado = reporte.denunciado
    denunciante = reporte.denunciante

    try:
        reporte.dictamen_administrador = dictamen
        reporte.id_admin_revisor = current_user.id_usuario
        reporte.fecha_resolucion = datetime.utcnow()

        if accion == 'DESESTIMAR':
            reporte.estado_reporte = 'DESESTIMADO'
            reporte.accion_aplicada = 'DENUNCIA_DESESTIMADA_SIN_SANCION'
            sala.estado_sala = 'ACTIVA'

            # Mensaje en la sala
            msg = MensajeChat(
                id_sala_chat=sala.id_sala_chat,
                id_usuario_emisor=current_user.id_usuario,
                contenido_mensaje=f"RESOLUCIÓN DE AUDITORÍA: La denuncia ha sido DESESTIMADA por el Administrador. Justificación: '{dictamen}'. La sala se encuentra nuevamente ACTIVA.",
                es_mensaje_sistema=True,
                fecha_envio=datetime.utcnow()
            )
            db.session.add(msg)
            flash("El reporte ha sido desestimado y la sala reactivada.", "info")

        elif accion == 'SANCION_ADVERTENCIA':
            reporte.estado_reporte = 'RESUELTO_CON_SANCION'
            reporte.accion_aplicada = 'ADVERTENCIA_FORMAL_PENALIZACION_REPUTACION'
            denunciado.reputacion_trueques = max(0, (denunciado.reputacion_trueques or 100) - 20)
            sala.estado_sala = 'ACTIVA'

            msg = MensajeChat(
                id_sala_chat=sala.id_sala_chat,
                id_usuario_emisor=current_user.id_usuario,
                contenido_mensaje=f"DICTAMEN DISCIPLINARIO: Se emite ADVERTENCIA FORMAL al usuario '{denunciado.nombre_completo}' con reducción de 20 pts de reputación. Dictamen: '{dictamen}'.",
                es_mensaje_sistema=True,
                fecha_envio=datetime.utcnow()
            )
            db.session.add(msg)
            flash(f"Advertencia aplicada a '{denunciado.nombre_completo}' (-20 pts de reputación).", "warning")

        elif accion == 'SANCION_SUSPENSION_TEMPORAL':
            dias = int(request.form.get('dias_suspension', 7))
            reporte.estado_reporte = 'RESUELTO_CON_SANCION'
            reporte.accion_aplicada = f"SUSPENSION_TEMPORAL_{dias}_DIAS"
            
            denunciado.activo = True
            denunciado.fecha_fin_suspension = datetime.utcnow() + timedelta(days=dias)
            denunciado.motivo_suspension = f"Suspensión por arbitraje en disputa #{reporte.id_reporte}: {dictamen[:200]}"
            denunciado.reputacion_trueques = max(0, (denunciado.reputacion_trueques or 100) - 40)

            sala.estado_sala = 'CANCELADA_POR_FRAUDE'
            sala.fecha_cierre = datetime.utcnow()

            msg = MensajeChat(
                id_sala_chat=sala.id_sala_chat,
                id_usuario_emisor=current_user.id_usuario,
                contenido_mensaje=f"DICTAMEN DISCIPLINARIO: El usuario '{denunciado.nombre_completo}' fue SUSPENDIDO por {dias} días por infracción grave. Operación cancelada por fraude. Dictamen: '{dictamen}'.",
                es_mensaje_sistema=True,
                fecha_envio=datetime.utcnow()
            )
            db.session.add(msg)
            flash(f"Usuario '{denunciado.nombre_completo}' suspendido por {dias} días y sala cancelada por fraude.", "danger")

        elif accion == 'SANCION_EXPULSION_PERMANENTE':
            reporte.estado_reporte = 'RESUELTO_CON_SANCION'
            reporte.accion_aplicada = 'EXPULSION_PERMANENTE_BLOQUEO_CUENTA'

            denunciado.activo = False
            denunciado.fecha_fin_suspension = None
            denunciado.motivo_suspension = f"Expulsión permanente por fraude comprobado en disputa #{reporte.id_reporte}: {dictamen[:200]}"
            denunciado.reputacion_trueques = 0

            sala.estado_sala = 'CANCELADA_POR_FRAUDE'
            sala.fecha_cierre = datetime.utcnow()

            msg = MensajeChat(
                id_sala_chat=sala.id_sala_chat,
                id_usuario_emisor=current_user.id_usuario,
                contenido_mensaje=f"DICTAMEN DISCIPLINARIO: El usuario '{denunciado.nombre_completo}' ha sido EXPULSADO DEFINITIVAMENTE de la plataforma por estafa comprobada. Operación cancelada. Dictamen: '{dictamen}'.",
                es_mensaje_sistema=True,
                fecha_envio=datetime.utcnow()
            )
            db.session.add(msg)
            flash(f"Usuario '{denunciado.nombre_completo}' expulsado definitivamente de la plataforma.", "danger")

        else:
            flash("Acción de resolución no reconocida.", "danger")
            return redirect(url_for('auditoria.ver_disputa', id_reporte=id_reporte))

        # Reversión contable de puntos si fue solicitada y aplica para compra
        if revertir_puntos and sala.transaccion_adquisicion:
            transaccion = sala.transaccion_adquisicion
            puntos_rev = transaccion.puntos_canjeados
            comprador = transaccion.comprador
            vendedor = transaccion.oferente

            # 1. Acreditar reembolso al comprador
            saldo_ant_c = comprador.saldo_puntos_disponibles
            comprador.saldo_puntos_disponibles += puntos_rev
            mov_comprador = HistorialMovimientosPuntos(
                id_usuario=comprador.id_usuario,
                id_prenda_referencia=transaccion.id_prenda,
                tipo_movimiento='REVERSION_POR_DISPUTA',
                cantidad_puntos=puntos_rev,
                saldo_anterior=saldo_ant_c,
                saldo_posterior=comprador.saldo_puntos_disponibles,
                descripcion_auditoria=f"Reembolso por dictamen de auditoría en disputa #{reporte.id_reporte}. Dictamen: {dictamen[:200]}",
                fecha_movimiento=datetime.utcnow()
            )
            db.session.add(mov_comprador)

            # 2. Debitar al vendedor/estafador
            saldo_ant_v = vendedor.saldo_puntos_disponibles
            vendedor.saldo_puntos_disponibles = max(0, vendedor.saldo_puntos_disponibles - puntos_rev)
            mov_vendedor = HistorialMovimientosPuntos(
                id_usuario=vendedor.id_usuario,
                id_prenda_referencia=transaccion.id_prenda,
                tipo_movimiento='REVERSION_POR_DISPUTA',
                cantidad_puntos=-puntos_rev,
                saldo_anterior=saldo_ant_v,
                saldo_posterior=vendedor.saldo_puntos_disponibles,
                descripcion_auditoria=f"Débito de reversión por fraude comprobado en disputa #{reporte.id_reporte}",
                fecha_movimiento=datetime.utcnow()
            )
            db.session.add(mov_vendedor)

            # 3. Anular estado de la transacción
            transaccion.estado_entrega = 'CANCELADA'

            # 4. Retornar prenda a estado RECHAZADA
            prenda = transaccion.prenda
            if prenda:
                prenda.estado = 'RECHAZADA'

            flash(f"Reversión contable ejecutada con éxito: +{puntos_rev} pts devueltos al comprador y debitados al infractor.", "info")

        db.session.commit()
    except Exception as err:
        db.session.rollback()
        flash(f"Error al procesar el dictamen pericial: {str(err)}", "danger")

    return redirect(url_for('auditoria.ver_disputa', id_reporte=id_reporte))
