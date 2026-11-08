"""
Controlador del Catálogo Público e Intercambios (Blueprint de Catálogo)
Provee búsqueda y filtros multicriterio, adquisición atómica por puntos
y panel de seguimiento de compras y entregas.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.models.prenda_accesorio import PrendaAccesorio
from app.models.categoria_prenda import CategoriaPrenda
from app.models.material import Material
from app.models.transaccion_adquisicion import TransaccionAdquisicion
from app.services.adquisicion_service import AdquisicionService

blueprint_catalogo = Blueprint('catalogo', __name__, url_prefix='/catalogo')


@blueprint_catalogo.route('/explorar')
def explorar():
    """
    Catálogo interactivo con filtros multicriterio en SQL Server:
    - Búsqueda textual libre (título o procedencia)
    - Categoría o Tipo de Artículo (PRENDA / ACCESORIO)
    - Familia de Material (Textiles, Cueros, Fibras, Joyas, etc.)
    - Talla
    - Rango de Puntos (mínimo y máximo)
    """
    consulta = PrendaAccesorio.query.filter_by(estado_publicacion='PUBLICADA')

    # 1. Filtro por término de búsqueda (título o marca/procedencia)
    termino_busqueda = request.args.get('q', '').strip()
    if termino_busqueda:
        consulta = consulta.filter(
            or_(
                PrendaAccesorio.titulo_publicacion.ilike(f"%{termino_busqueda}%"),
                PrendaAccesorio.procedencia.ilike(f"%{termino_busqueda}%")
            )
        )

    # 2. Filtro por Categoría
    id_categoria = request.args.get('id_categoria', type=int)
    if id_categoria:
        consulta = consulta.filter(PrendaAccesorio.id_categoria == id_categoria)

    # 3. Filtro por Tipo de Artículo (PRENDA o ACCESORIO)
    tipo_articulo = request.args.get('tipo_articulo', '').strip()
    if tipo_articulo in ('PRENDA', 'ACCESORIO'):
        consulta = consulta.join(CategoriaPrenda).filter(CategoriaPrenda.tipo_articulo == tipo_articulo)

    # 4. Filtro por Familia de Material
    familia_material = request.args.get('familia_material', '').strip()
    if familia_material:
        consulta = consulta.join(Material).filter(Material.familia_material == familia_material)

    # 5. Filtro por Talla
    talla = request.args.get('talla', '').strip()
    if talla:
        consulta = consulta.filter(PrendaAccesorio.talla.ilike(f"%{talla}%"))

    # 6. Filtro por Rango de Puntos
    puntos_min = request.args.get('puntos_min', type=int)
    if puntos_min is not None and puntos_min >= 0:
        consulta = consulta.filter(PrendaAccesorio.puntos_valoracion >= puntos_min)

    puntos_max = request.args.get('puntos_max', type=int)
    if puntos_max is not None and puntos_max > 0:
        consulta = consulta.filter(PrendaAccesorio.puntos_valoracion <= puntos_max)

    # Orden cronológico descendente (los más recientes primero)
    prendas_disponibles = consulta.order_by(PrendaAccesorio.fecha_publicacion.desc()).all()

    # Opciones dinámicas para los menús de filtrado
    categorias = CategoriaPrenda.query.filter_by(activo=True).order_by(CategoriaPrenda.nombre_categoria.asc()).all()
    familias = [
        f[0] for f in Material.query.with_entities(Material.familia_material).distinct().order_by(Material.familia_material.asc()).all()
    ]

    return render_template(
        'catalogo/explorar.html',
        prendas=prendas_disponibles,
        categorias=categorias,
        familias=familias,
        filtros={
            'q': termino_busqueda,
            'id_categoria': id_categoria,
            'tipo_articulo': tipo_articulo,
            'familia_material': familia_material,
            'talla': talla,
            'puntos_min': puntos_min,
            'puntos_max': puntos_max
        }
    )


@blueprint_catalogo.route('/adquirir/<int:id_prenda>', methods=['GET', 'POST'])
@login_required
def adquirir(id_prenda: int):
    """Ejecuta la adquisición transaccional de un artículo con puntos disponibles."""
    try:
        transaccion = AdquisicionService.procesar_adquisicion(
            id_prenda=id_prenda,
            id_usuario_comprador=current_user.id_usuario
        )
        flash(
            f"¡Felicitaciones! Has adquirido exitosamente el artículo '{transaccion.prenda.titulo_publicacion}' "
            f"por {transaccion.puntos_canjeados} puntos. El oferente ha sido notificado para coordinar la entrega.",
            "success"
        )
        return redirect(url_for('catalogo.mis_intercambios'))

    except ValueError as error_negocio:
        flash(str(error_negocio), 'danger')
        return redirect(url_for('prendas.detalle', id_prenda=id_prenda))
    except Exception as error_servidor:
        flash(f"Error inesperado al procesar la adquisición: {str(error_servidor)}", 'danger')
        return redirect(url_for('prendas.detalle', id_prenda=id_prenda))


@blueprint_catalogo.route('/mis-intercambios')
@login_required
def mis_intercambios():
    """Panel de seguimiento de transacciones realizadas y artículos entregados."""
    compras = TransaccionAdquisicion.query.filter_by(
        id_usuario_comprador=current_user.id_usuario
    ).order_by(TransaccionAdquisicion.fecha_transaccion.desc()).all()

    ventas = TransaccionAdquisicion.query.filter_by(
        id_usuario_oferente=current_user.id_usuario
    ).order_by(TransaccionAdquisicion.fecha_transaccion.desc()).all()

    return render_template(
        'catalogo/mis_intercambios.html',
        compras=compras,
        ventas=ventas
    )
