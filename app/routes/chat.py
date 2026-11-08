"""
Controlador de Salas de Chat y Logística de Envíos (Blueprint de Chat)
Gestiona la mensajería privada post-intercambio / post-compra con puntos,
administración de la Ficha Logística de Despacho (empresa, guía, dirección)
y confirmación dual de entrega que culmina en cierre exitoso y reputación.
"""

import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models.sala_chat_intercambio import SalaChatIntercambio
from app.models.mensaje_chat import MensajeChat
from app.models.usuario import Usuario

blueprint_chat = Blueprint('chat', __name__, url_prefix='/chat')

EXTENSIONES_PERMITIDAS_CHAT = {'jpg', 'jpeg', 'png', 'webp'}


@blueprint_chat.route('/sala/<string:codigo_sala>')
@login_required
def ver_sala(codigo_sala: str):
    """
    Vista de la sala privada de chat y logística de entrega.
    Acceso exclusivo para los 2 participantes o el Administrador.
    """
    sala = SalaChatIntercambio.query.filter_by(codigo_sala=codigo_sala).first_or_404()

    if current_user.id_usuario not in (sala.id_usuario_1, sala.id_usuario_2) and not current_user.es_administrador:
        abort(403)

    # Marcar como leídos los mensajes que envió la otra parte
    MensajeChat.query.filter_by(id_sala_chat=sala.id_sala_chat, leido=False).filter(
        MensajeChat.id_usuario_emisor != current_user.id_usuario
    ).update({'leido': True})
    db.session.commit()

    mensajes = sala.mensajes.order_by(MensajeChat.fecha_envio.asc()).all()
    contraparte = sala.usuario_2 if current_user.id_usuario == sala.id_usuario_1 else sala.usuario_1

    mi_confirmacion = sala.confirmado_usuario_1 if current_user.id_usuario == sala.id_usuario_1 else sala.confirmado_usuario_2
    confirmacion_contraparte = sala.confirmado_usuario_2 if current_user.id_usuario == sala.id_usuario_1 else sala.confirmado_usuario_1

    return render_template(
        'chat/sala_chat.html',
        sala=sala,
        mensajes=mensajes,
        contraparte=contraparte,
        mi_confirmacion=mi_confirmacion,
        confirmacion_contraparte=confirmacion_contraparte
    )


@blueprint_chat.route('/sala/<string:codigo_sala>/enviar-mensaje', methods=['POST'])
@login_required
def enviar_mensaje(codigo_sala: str):
    """Envía un mensaje de texto o soporte fotográfico a la sala."""
    sala = SalaChatIntercambio.query.filter_by(codigo_sala=codigo_sala).first_or_404()

    if current_user.id_usuario not in (sala.id_usuario_1, sala.id_usuario_2) and not current_user.es_administrador:
        abort(403)

    if sala.estado_sala != 'ACTIVA':
        flash(
            f"No es posible enviar nuevos mensajes. La sala se encuentra en estado '{sala.estado_sala}'. "
            f"Los registros permanecen inmutables para fines de auditoría.",
            "warning"
        )
        return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))

    contenido = request.form.get('contenido_mensaje', '').strip()
    archivo_adjunto = request.files.get('adjunto')
    ruta_adjunto = None

    if archivo_adjunto and archivo_adjunto.filename and archivo_adjunto.filename.strip():
        nombre = secure_filename(archivo_adjunto.filename)
        ext = nombre.rsplit('.', 1)[-1].lower() if '.' in nombre else ''
        if ext in EXTENSIONES_PERMITIDAS_CHAT:
            carpeta_chat = os.path.join(current_app.config['CARPETA_SUBIDAS'], 'chat')
            os.makedirs(carpeta_chat, exist_ok=True)
            nombre_guardado = f"chat_{sala.id_sala_chat}_{uuid.uuid4().hex[:10]}.{ext}"
            archivo_adjunto.save(os.path.join(carpeta_chat, nombre_guardado))
            ruta_adjunto = f"uploads/chat/{nombre_guardado}"
        else:
            flash("Solo se permiten imágenes (JPG, PNG, WEBP) como adjunto de soporte.", "warning")

    if not contenido and not ruta_adjunto:
        flash("El mensaje no puede estar vacío.", "danger")
        return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))

    try:
        nuevo_msg = MensajeChat(
            id_sala_chat=sala.id_sala_chat,
            id_usuario_emisor=current_user.id_usuario,
            contenido_mensaje=contenido or "Foto de soporte adjuntada",
            ruta_adjunto=ruta_adjunto,
            es_mensaje_sistema=False,
            leido=False,
            fecha_envio=datetime.utcnow()
        )
        db.session.add(nuevo_msg)
        db.session.commit()
    except Exception as err:
        db.session.rollback()
        flash(f"Error al enviar mensaje: {str(err)}", "danger")

    return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))


@blueprint_chat.route('/sala/<string:codigo_sala>/actualizar-envio', methods=['POST'])
@login_required
def actualizar_envio(codigo_sala: str):
    """Actualiza la Ficha Logística de Envío y Emite Mensaje de Sistema."""
    sala = SalaChatIntercambio.query.filter_by(codigo_sala=codigo_sala).first_or_404()

    if current_user.id_usuario not in (sala.id_usuario_1, sala.id_usuario_2) and not current_user.es_administrador:
        abort(403)

    if sala.estado_sala != 'ACTIVA':
        flash("No se pueden modificar datos logísticos en este estado de sala.", "warning")
        return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))

    try:
        metodo = request.form.get('metodo_entrega', 'POR_DEFINIR').strip().upper()
        if metodo not in ('POR_DEFINIR', 'ENTREGA_PRESENCIAL', 'ENVIO_DOMICILIO'):
            metodo = 'POR_DEFINIR'

        sala.metodo_entrega = metodo
        sala.direccion_envio = request.form.get('direccion_envio', '').strip() or None
        sala.ciudad_destino = request.form.get('ciudad_destino', '').strip() or None
        sala.nombre_receptor_envio = request.form.get('nombre_receptor_envio', '').strip() or None
        sala.telefono_contacto_envio = request.form.get('telefono_contacto_envio', '').strip() or None
        sala.empresa_transportadora = request.form.get('empresa_transportadora', '').strip() or None
        sala.numero_guia_rastreo = request.form.get('numero_guia_rastreo', '').strip() or None

        # Mensaje de sistema notificando el cambio
        guia_txt = f"Guía: {sala.numero_guia_rastreo}" if sala.numero_guia_rastreo else "Guía pendiente"
        transp_txt = f"Transportadora: {sala.empresa_transportadora}" if sala.empresa_transportadora else ""
        msg_sistema = MensajeChat(
            id_sala_chat=sala.id_sala_chat,
            id_usuario_emisor=current_user.id_usuario,
            contenido_mensaje=(
                f"Datos logísticos actualizados por {current_user.nombre_completo}: "
                f"Modalidad '{sala.metodo_entrega}'. {transp_txt} {guia_txt}."
            ),
            es_mensaje_sistema=True,
            fecha_envio=datetime.utcnow()
        )
        db.session.add(msg_sistema)
        db.session.commit()

        flash("Ficha de entrega y despacho actualizada con éxito.", "success")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al actualizar logística: {str(err)}", "danger")

    return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))


@blueprint_chat.route('/sala/<string:codigo_sala>/confirmar-entrega', methods=['POST'])
@login_required
def confirmar_entrega(codigo_sala: str):
    """
    Registra la confirmación de recepción del artículo por parte del usuario.
    Si ambas partes confirman, se cierra la sala y se bonifica la reputación.
    """
    sala = SalaChatIntercambio.query.filter_by(codigo_sala=codigo_sala).first_or_404()

    if current_user.id_usuario not in (sala.id_usuario_1, sala.id_usuario_2) and not current_user.es_administrador:
        abort(403)

    if sala.estado_sala != 'ACTIVA':
        flash("Esta sala ya no se encuentra en estado activo.", "warning")
        return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))

    try:
        if current_user.id_usuario == sala.id_usuario_1:
            sala.confirmado_usuario_1 = True
        else:
            sala.confirmado_usuario_2 = True

        msg_conf = MensajeChat(
            id_sala_chat=sala.id_sala_chat,
            id_usuario_emisor=current_user.id_usuario,
            contenido_mensaje=f"{current_user.nombre_completo} ha confirmado la recepción a satisfacción del artículo.",
            es_mensaje_sistema=True,
            fecha_envio=datetime.utcnow()
        )
        db.session.add(msg_conf)

        # Si ambas partes han confirmado
        if sala.confirmado_usuario_1 and sala.confirmado_usuario_2:
            sala.estado_sala = 'CERRADA_EXITOSA'
            sala.fecha_cierre = datetime.utcnow()

            # Bonificar reputación (+5 pts)
            u1 = db.session.get(Usuario, sala.id_usuario_1)
            u2 = db.session.get(Usuario, sala.id_usuario_2)
            if u1:
                u1.reputacion_trueques = (u1.reputacion_trueques or 100) + 5
            if u2:
                u2.reputacion_trueques = (u2.reputacion_trueques or 100) + 5

            msg_cierre = MensajeChat(
                id_sala_chat=sala.id_sala_chat,
                id_usuario_emisor=current_user.id_usuario,
                contenido_mensaje=(
                    "¡INTERCAMBIO / ADQUISICIÓN CULMINADO CON ÉXITO! "
                    "Ambas partes confirmaron la entrega a conformidad. "
                    "Ambos usuarios han recibido +5 puntos de reputación comunitaria."
                ),
                es_mensaje_sistema=True,
                fecha_envio=datetime.utcnow()
            )
            db.session.add(msg_cierre)
            flash("¡Felicidades! Ambas partes confirmaron la entrega y la operación cerró exitosamente.", "success")
        else:
            flash("Confirmación registrada. A la espera de que la contraparte confirme también la recepción.", "info")

        db.session.commit()

    except Exception as err:
        db.session.rollback()
        flash(f"Error al registrar confirmación: {str(err)}", "danger")

    return redirect(url_for('chat.ver_sala', codigo_sala=codigo_sala))


@blueprint_chat.route('/mis-chats')
@login_required
def mis_chats():
    """Listado de todas las salas de chat activas y pasadas del usuario."""
    salas = SalaChatIntercambio.query.filter(
        db.or_(
            SalaChatIntercambio.id_usuario_1 == current_user.id_usuario,
            SalaChatIntercambio.id_usuario_2 == current_user.id_usuario
        )
    ).order_by(SalaChatIntercambio.fecha_apertura.desc()).all()

    return render_template('chat/mis_chats.html', salas=salas)
