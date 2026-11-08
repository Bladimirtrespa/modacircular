"""
Controlador de Vitrina e Inventario Dual de Usuario (Blueprint de Inventario)
Permite a los usuarios gestionar su vitrina personal de trueque directo,
visualizar inventarios públicos de otros miembros con su reputación,
y convertir de forma transaccional ítems de inventario a puntos con asiento contable.
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app import db
from app.models.usuario import Usuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos
from app.models.solicitud_aprobacion_material import SolicitudAprobacionMaterial

blueprint_inventario = Blueprint('inventario', __name__, url_prefix='/inventario')


@blueprint_inventario.route('/usuario/<int:id_usuario>')
def ver_vitrina(id_usuario: int):
    """
    Vitrina e inventario público o privado del usuario (Trueque Directo).
    Muestra los artículos disponibles para trueque, tasación referencial en puntos,
    reputación comunitaria y botones de acción contextual.
    """
    usuario = Usuario.query.get_or_404(id_usuario)
    es_dueno = current_user.is_authenticated and (current_user.id_usuario == usuario.id_usuario)

    filtro = request.args.get('filtro', 'todos').strip().lower()

    # Consulta base de artículos del usuario
    consulta = PrendaAccesorio.query.filter_by(id_usuario_propietario=id_usuario)

    if es_dueno:
        # El dueño puede ver sus ítems en inventario, publicados y reservados
        estados_permitidos = ['EN_INVENTARIO', 'PUBLICADA', 'RESERVADA_TRUEQUE', 'PENDIENTE_APROBACION']
    else:
        # Los visitantes solo pueden ver los ítems disponibles para negociar o en catálogo
        estados_permitidos = ['EN_INVENTARIO', 'PUBLICADA']

    consulta = consulta.filter(PrendaAccesorio.estado_publicacion.in_(estados_permitidos))

    if filtro == 'trueque':
        consulta = consulta.filter(PrendaAccesorio.estado_publicacion.in_(['EN_INVENTARIO', 'RESERVADA_TRUEQUE']))
    elif filtro == 'puntos':
        consulta = consulta.filter(PrendaAccesorio.estado_publicacion == 'PUBLICADA')

    prendas = consulta.order_by(PrendaAccesorio.fecha_publicacion.desc()).all()

    total_articulos = len(prendas)
    valor_total_puntos = sum(p.puntos_valoracion for p in prendas)

    return render_template(
        'inventario/vitrina_usuario.html',
        usuario=usuario,
        prendas=prendas,
        es_dueno=es_dueno,
        total_articulos=total_articulos,
        valor_total_puntos=valor_total_puntos,
        filtro=filtro
    )


@blueprint_inventario.route('/prenda/<int:id_prenda>/convertir-a-puntos', methods=['POST'])
@login_required
def convertir_a_puntos(id_prenda: int):
    """
    Convierte transaccionalmente un ítem de inventario a puntos disponibles en billetera.
    Cambia el estado de EN_INVENTARIO a PUBLICADA y genera un registro inmutable en el Kardex.
    """
    prenda = PrendaAccesorio.query.get_or_404(id_prenda)

    # Validar que el usuario sea el legítimo propietario
    if prenda.id_usuario_propietario != current_user.id_usuario:
        abort(403)

    # Validar que la prenda se encuentre actualmente en inventario de trueque
    if prenda.estado_publicacion != 'EN_INVENTARIO':
        flash("Solo los artículos que están en tu inventario de trueque pueden convertirse a puntos.", "warning")
        return redirect(url_for('inventario.ver_vitrina', id_usuario=current_user.id_usuario))

    try:
        # Si el material es metal o gema preciosa, requiere moderación preventiva
        if prenda.material.es_metal_o_joya_preciosa or prenda.material.requiere_aprobacion_especial:
            prenda.estado_publicacion = 'PENDIENTE_APROBACION'
            prenda.modalidad_publicacion = 'SOLO_PUNTOS'
            current_user.saldo_puntos_retenidos += prenda.puntos_valoracion

            solicitud = SolicitudAprobacionMaterial(
                id_prenda=prenda.id_prenda,
                estado_revision='PENDIENTE',
                fecha_solicitud=datetime.utcnow()
            )
            db.session.add(solicitud)
            db.session.commit()

            flash(
                f"Conversión iniciada: Por tratarse de una joya o metal precioso ({prenda.material.nombre_material}), "
                f"se han asignado {prenda.puntos_valoracion} puntos retenidos a la espera de validación de un moderador.",
                "warning"
            )
        else:
            # Material estándar: Acreditación inmediata y asiento contable
            saldo_anterior = current_user.saldo_puntos_disponibles
            current_user.saldo_puntos_disponibles += prenda.puntos_valoracion
            saldo_posterior = current_user.saldo_puntos_disponibles

            prenda.estado_publicacion = 'PUBLICADA'
            prenda.modalidad_publicacion = 'SOLO_PUNTOS'

            movimiento = HistorialMovimientosPuntos(
                id_usuario=current_user.id_usuario,
                id_prenda_referencia=prenda.id_prenda,
                tipo_movimiento='CREDITO_CONVERSION_INVENTARIO',
                cantidad_puntos=prenda.puntos_valoracion,
                saldo_anterior=saldo_anterior,
                saldo_posterior=saldo_posterior,
                descripcion_auditoria=f"Conversión desde vitrina de trueque para '{prenda.titulo_publicacion[:50]}'",
                fecha_movimiento=datetime.utcnow()
            )
            db.session.add(movimiento)
            db.session.commit()

            flash(
                f"¡Conversión exitosa! Se acreditaron {prenda.puntos_valoracion} puntos a tu billetera disponible "
                f"y tu prenda '{prenda.titulo_publicacion}' ahora está publicada en el catálogo general.",
                "success"
            )

    except Exception as err:
        db.session.rollback()
        flash(f"Error al convertir el artículo a puntos: {str(err)}", "danger")

    return redirect(url_for('inventario.ver_vitrina', id_usuario=current_user.id_usuario))
