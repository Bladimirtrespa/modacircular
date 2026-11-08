"""
Controlador de Prendas y Accesorios (Blueprint de Prendas)
Gestiona la publicación con 7 atributos obligatorios, carga multimedia,
cálculo y acreditación/retención de puntos y visualización detallada.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.models.prenda_accesorio import PrendaAccesorio
from app.models.material import Material
from app.forms.prenda_forms import FormularioPublicacionPrenda
from app.services.publicacion_service import PublicacionService

blueprint_prendas = Blueprint('prendas', __name__, url_prefix='/prendas')


@blueprint_prendas.route('/publicar', methods=['GET', 'POST'])
@login_required
def publicar():
    """
    Ruta para la publicación de prendas y accesorios.
    Exige los 7 atributos obligatorios, evidencia multimedia
    y realiza la acreditación o retención de puntos atómica en SQL Server.
    """
    formulario = FormularioPublicacionPrenda()
    formulario.cargar_opciones_parametricas()

    materiales_activos = Material.query.filter_by(activo=True).order_by(Material.nombre_material.asc()).all()
    formulario.id_material.choices = [(m.id_material, m.nombre_material) for m in materiales_activos]

    if formulario.validate_on_submit():
        archivos = request.files.getlist('archivos_multimedia')
        try:
            prenda = PublicacionService.procesar_publicacion(
                usuario=current_user,
                formulario=formulario,
                archivos_subidos=archivos
            )

            if prenda.estado_publicacion == 'EN_INVENTARIO':
                flash(
                    f"¡Artículo agregado a tu Vitrina de Trueque Directo! "
                    f"Tiene una tasación referencial de {prenda.puntos_valoracion} puntos. "
                    f"No se agregaron puntos a tu saldo; está listo para intercambio o conversión posterior.",
                    "info"
                )
                return redirect(url_for('inventario.ver_vitrina', id_usuario=current_user.id_usuario))
            elif prenda.estado_publicacion == 'PUBLICADA':
                flash(
                    f"¡Publicación exitosa! Tu artículo fue publicado y se han acreditado {prenda.puntos_valoracion} "
                    f"puntos inmediatamente a tu saldo disponible.",
                    "success"
                )
            else:
                flash(
                    f"¡Artículo de joyería recibido! Por contener materiales preciosos ({prenda.material.nombre_material}), "
                    f"se han retenido {prenda.puntos_valoracion} puntos de forma preventiva. "
                    f"Un moderador revisará la evidencia de fotos/video para acreditarlos a tu saldo disponible.",
                    "warning"
                )

            return redirect(url_for('prendas.detalle', id_prenda=prenda.id_prenda))

        except ValueError as error_validacion:
            flash(str(error_validacion), 'danger')
        except Exception as error_inesperado:
            flash(f"Ocurrió un error inesperado al procesar la publicación: {str(error_inesperado)}", 'danger')

    return render_template('prendas/publicar.html', formulario=formulario)


@blueprint_prendas.route('/detalle/<int:id_prenda>')
def detalle(id_prenda: int):
    """
    Vista detallada de una prenda o accesorio.
    Muestra los 7 atributos de negocio, el desglose de valoración y reproductor multimedia.
    """
    prenda = PrendaAccesorio.query.get_or_404(id_prenda)

    # Si la prenda está en moderación o inactiva, solo el propietario o moderador pueden verla
    if prenda.estado_publicacion in ('PENDIENTE_APROBACION', 'RECHAZADA', 'INACTIVA'):
        if not current_user.is_authenticated or (
            current_user.id_usuario != prenda.id_usuario_propietario and not current_user.es_moderador
        ):
            abort(403)

    return render_template('prendas/detalle.html', prenda=prenda)
