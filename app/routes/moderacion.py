"""
Controlador de Moderación de Joyas y Metales Preciosos (Blueprint de Moderación)
Permite a usuarios con rol MODERADOR o ADMINISTRADOR inspeccionar evidencias
y dictaminar la autenticidad para acreditar o rechazar puntos de joyería.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.models.solicitud_aprobacion_material import SolicitudAprobacionMaterial
from app.services.moderacion_service import ModeracionService

blueprint_moderacion = Blueprint('moderacion', __name__, url_prefix='/moderacion')


@blueprint_moderacion.before_request
@login_required
def verificar_permisos_moderador():
    """Restringe el acceso exclusivo a Moderadores y Administradores."""
    if not current_user.es_moderador:
        abort(403)


@blueprint_moderacion.route('/bandeja')
def bandeja():
    """Listado de órdenes de moderación pendientes e histórico de resoluciones."""
    solicitudes_pendientes = SolicitudAprobacionMaterial.query.filter_by(
        estado_revision='PENDIENTE'
    ).order_by(SolicitudAprobacionMaterial.fecha_solicitud.asc()).all()

    solicitudes_resueltas = SolicitudAprobacionMaterial.query.filter(
        SolicitudAprobacionMaterial.estado_revision != 'PENDIENTE'
    ).order_by(SolicitudAprobacionMaterial.fecha_resolucion.desc()).limit(30).all()

    return render_template(
        'moderacion/bandeja.html',
        pendientes=solicitudes_pendientes,
        resueltas=solicitudes_resueltas
    )


@blueprint_moderacion.route('/revisar/<int:id_solicitud>')
def revisar(id_solicitud: int):
    """
    Vista de peritaje gemológico para inspeccionar fotos en alta resolución,
    video de sellos de contraste y emitir dictamen de aprobación o rechazo.
    """
    solicitud = SolicitudAprobacionMaterial.query.get_or_404(id_solicitud)
    prenda = solicitud.prenda

    return render_template(
        'moderacion/revisar.html',
        solicitud=solicitud,
        prenda=prenda
    )


@blueprint_moderacion.route('/aprobar/<int:id_solicitud>', methods=['POST'])
def aprobar(id_solicitud: int):
    """Ejecuta la aprobación de la joya y transferencia inmediata de puntos."""
    observaciones = request.form.get('observaciones', '').strip()
    try:
        solicitud = ModeracionService.aprobar_solicitud(
            id_solicitud=id_solicitud,
            id_usuario_revisor=current_user.id_usuario,
            observaciones=observaciones
        )
        flash(
            f"¡Solicitud #{solicitud.id_solicitud_aprobacion} aprobada con éxito! La prenda '{solicitud.prenda.titulo_publicacion}' "
            f"ha sido publicada y se transfirieron {solicitud.prenda.puntos_valoracion} puntos al saldo disponible del usuario.",
            "success"
        )
    except ValueError as error_val:
        flash(str(error_val), 'danger')
    except Exception as error_servidor:
        flash(f"Error al aprobar la solicitud: {str(error_servidor)}", 'danger')

    return redirect(url_for('moderacion.bandeja'))


@blueprint_moderacion.route('/rechazar/<int:id_solicitud>', methods=['POST'])
def rechazar(id_solicitud: int):
    """Ejecuta el rechazo motivado de la joya y remoción de puntos retenidos."""
    motivo_rechazo = request.form.get('motivo_rechazo', '').strip()
    try:
        solicitud = ModeracionService.rechazar_solicitud(
            id_solicitud=id_solicitud,
            id_usuario_revisor=current_user.id_usuario,
            motivo_rechazo=motivo_rechazo
        )
        flash(
            f"Solicitud #{solicitud.id_solicitud_aprobacion} rechazada. Se han descontado los "
            f"{solicitud.prenda.puntos_valoracion} puntos retenidos al usuario.",
            "warning"
        )
    except ValueError as error_val:
        flash(str(error_val), 'danger')
    except Exception as error_servidor:
        flash(f"Error al procesar el rechazo: {str(error_servidor)}", 'danger')

    return redirect(url_for('moderacion.bandeja'))
