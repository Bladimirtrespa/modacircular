"""
Controlador de Trueques Directos (Blueprint de Trueques)
Gestiona la creación interactiva con doble inventario, cálculo de equilibrio en tiempo real,
bandeja de ofertas recibidas/enviadas y resolución transaccional de propuestas.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.models.usuario import Usuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.oferta_trueque import OfertaTrueque
from app.services.trueque_service import TruequeService

blueprint_trueques = Blueprint('trueques', __name__, url_prefix='/trueques')


@blueprint_trueques.route('/proponer/<int:id_receptor>')
@login_required
def proponer_trueque(id_receptor: int):
    """
    Constructor interactivo de trueques directos (Doble Inventario N a M).
    Panel Izquierdo: Artículos del usuario actual.
    Panel Derecho: Artículos del receptor elegido.
    """
    if current_user.id_usuario == id_receptor:
        flash("No puedes crear una oferta de trueque contigo mismo.", "warning")
        return redirect(url_for('catalogo.explorar'))

    receptor = Usuario.query.get_or_404(id_receptor)
    if not receptor.activo:
        flash("El usuario receptor se encuentra inactivo.", "danger")
        return redirect(url_for('catalogo.explorar'))

    # Prendas disponibles del ofertante (usuario en sesión)
    prendas_ofertante = PrendaAccesorio.query.filter_by(
        id_usuario_propietario=current_user.id_usuario
    ).filter(
        PrendaAccesorio.estado_publicacion.in_(['EN_INVENTARIO', 'PUBLICADA'])
    ).all()

    # Prendas disponibles del receptor
    prendas_receptor = PrendaAccesorio.query.filter_by(
        id_usuario_propietario=id_receptor
    ).filter(
        PrendaAccesorio.estado_publicacion.in_(['EN_INVENTARIO', 'PUBLICADA'])
    ).all()

    # Soporte para contraoferta precargada
    id_oferta_padre = request.args.get('contraoferta_de', type=int)
    items_ofrecidos_preseleccionados = []
    items_solicitados_preseleccionados = []

    if id_oferta_padre:
        oferta_padre = OfertaTrueque.query.get(id_oferta_padre)
        if oferta_padre:
            # En la contraoferta, lo que el receptor pedía ahora lo ofrece, y viceversa
            items_ofrecidos_preseleccionados = [d.id_prenda for d in oferta_padre.articulos_solicitados]
            items_solicitados_preseleccionados = [d.id_prenda for d in oferta_padre.articulos_ofrecidos]

    return render_template(
        'trueques/constructor_trueque.html',
        receptor=receptor,
        prendas_ofertante=prendas_ofertante,
        prendas_receptor=prendas_receptor,
        id_oferta_padre=id_oferta_padre,
        items_ofrecidos_preseleccionados=items_ofrecidos_preseleccionados,
        items_solicitados_preseleccionados=items_solicitados_preseleccionados
    )


@blueprint_trueques.route('/enviar', methods=['POST'])
@login_required
def enviar_propuesta():
    """
    Procesa el formulario del constructor de trueques y persiste la oferta con reserva de ítems.
    """
    try:
        id_receptor = int(request.form.get('id_receptor', 0))
        mensaje = request.form.get('mensaje_propuesta', '').strip()
        id_oferta_padre = request.form.get('id_oferta_padre', type=int)

        prendas_ofrecidas = [int(x) for x in request.form.getlist('prendas_ofrecidas') if x.isdigit()]
        prendas_solicitadas = [int(x) for x in request.form.getlist('prendas_solicitadas') if x.isdigit()]

        nueva_oferta = TruequeService.crear_oferta(
            usuario_ofertante=current_user,
            id_usuario_receptor=id_receptor,
            prendas_ofrecidas_ids=prendas_ofrecidas,
            prendas_solicitadas_ids=prendas_solicitadas,
            mensaje_propuesta=mensaje,
            id_oferta_padre=id_oferta_padre
        )

        flash(
            f"¡Oferta de trueque #{nueva_oferta.id_oferta_trueque} enviada con éxito! "
            f"Los artículos quedaron reservados en el sistema a la espera de respuesta.",
            "success"
        )
        return redirect(url_for('trueques.detalle_oferta', id_oferta=nueva_oferta.id_oferta_trueque))

    except ValueError as err_val:
        flash(str(err_val), "danger")
        return redirect(request.referrer or url_for('catalogo.explorar'))
    except Exception as err:
        flash(f"Error al enviar la oferta: {str(err)}", "danger")
        return redirect(request.referrer or url_for('catalogo.explorar'))


@blueprint_trueques.route('/mis-ofertas')
@login_required
def mis_ofertas():
    """Bandeja unificada de ofertas de trueque recibidas y enviadas."""
    ofertas_recibidas = OfertaTrueque.query.filter_by(
        id_usuario_receptor=current_user.id_usuario
    ).order_by(OfertaTrueque.fecha_creacion.desc()).all()

    ofertas_enviadas = OfertaTrueque.query.filter_by(
        id_usuario_ofertante=current_user.id_usuario
    ).order_by(OfertaTrueque.fecha_creacion.desc()).all()

    return render_template(
        'trueques/mis_ofertas.html',
        ofertas_recibidas=ofertas_recibidas,
        ofertas_enviadas=ofertas_enviadas
    )


@blueprint_trueques.route('/detalle/<int:id_oferta>')
@login_required
def detalle_oferta(id_oferta: int):
    """
    Inspección detallada de una oferta de trueque con doble panel y botones contextuales.
    """
    oferta = OfertaTrueque.query.get_or_404(id_oferta)

    if current_user.id_usuario not in (oferta.id_usuario_ofertante, oferta.id_usuario_receptor) and not current_user.es_administrador:
        abort(403)

    es_receptor = (current_user.id_usuario == oferta.id_usuario_receptor)
    es_ofertante = (current_user.id_usuario == oferta.id_usuario_ofertante)

    # Buscar si ya tiene sala de chat asociada
    sala_chat = oferta.salas_chat.first()

    return render_template(
        'trueques/detalle_oferta.html',
        oferta=oferta,
        es_receptor=es_receptor,
        es_ofertante=es_ofertante,
        sala_chat=sala_chat
    )


@blueprint_trueques.route('/<int:id_oferta>/aceptar', methods=['POST'])
@login_required
def aceptar_oferta(id_oferta: int):
    """Acepta la oferta de trueque atómicamente."""
    try:
        sala = TruequeService.aceptar_oferta(id_oferta, current_user)
        flash(
            f"¡Has aceptado el trueque! La titularidad de los artículos se ha intercambiado en SQL Server. "
            f"Se ha abierto la sala privada para coordinar la entrega.",
            "success"
        )
        return redirect(url_for('trueques.detalle_oferta', id_oferta=id_oferta))
    except Exception as err:
        flash(str(err), "danger")
        return redirect(url_for('trueques.detalle_oferta', id_oferta=id_oferta))


@blueprint_trueques.route('/<int:id_oferta>/rechazar', methods=['POST'])
@login_required
def rechazar_oferta(id_oferta: int):
    """Rechaza la propuesta de trueque liberando los artículos."""
    try:
        TruequeService.rechazar_oferta(id_oferta, current_user)
        flash("Has rechazado la oferta de trueque. Los artículos han sido liberados a sus dueños.", "info")
    except Exception as err:
        flash(str(err), "danger")

    return redirect(url_for('trueques.mis_ofertas'))


@blueprint_trueques.route('/<int:id_oferta>/cancelar', methods=['POST'])
@login_required
def cancelar_oferta(id_oferta: int):
    """Cancela la propuesta de trueque liberando los artículos."""
    try:
        TruequeService.cancelar_oferta(id_oferta, current_user)
        flash("Propuesta cancelada con éxito. Tus artículos han sido devueltos a tu inventario.", "info")
    except Exception as err:
        flash(str(err), "danger")

    return redirect(url_for('trueques.mis_ofertas'))
