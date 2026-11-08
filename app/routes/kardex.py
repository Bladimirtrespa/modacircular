"""
Controlador del Kardex y Movimientos Contables (Blueprint de Kardex)
Muestra el libro mayor inmutable de débitos y créditos con desglose de fórmulas.
"""

from flask import Blueprint, render_template
from flask_login import login_required, current_user

from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos

blueprint_kardex = Blueprint('kardex', __name__, url_prefix='/kardex')


@blueprint_kardex.route('/movimientos')
@login_required
def movimientos():
    """
    Libro mayor de auditoría y trazabilidad inmutable de puntos.
    Muestra cada asiento contable, tipo de movimiento y desglose de cálculo.
    """
    movimientos_usuario = HistorialMovimientosPuntos.query.filter_by(
        id_usuario=current_user.id_usuario
    ).order_by(HistorialMovimientosPuntos.fecha_movimiento.desc()).all()

    total_acreditado = sum(
        m.cantidad_puntos for m in movimientos_usuario if m.tipo_movimiento in ('CREDITO_PUBLICACION', 'CREDITO_APROBACION_JOYA')
    )
    total_debitado = sum(
        m.cantidad_puntos for m in movimientos_usuario if m.tipo_movimiento == 'DEBITO_ADQUISICION'
    )

    return render_template(
        'kardex/movimientos.html',
        movimientos=movimientos_usuario,
        total_acreditado=total_acreditado,
        total_debitado=total_debitado
    )
