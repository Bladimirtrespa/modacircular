"""
Modelo de Historial de Movimientos de Puntos (Kardex de Auditoría)
Garantiza trazabilidad inmutable y auditoría exhaustiva de cada débito o crédito
en las billeteras de los usuarios con desglose de la fórmula de valoración.
"""

from datetime import datetime
from app import db


class HistorialMovimientosPuntos(db.Model):
    """Mapeo de la tabla Historial_Movimientos_Puntos en SQL Server."""
    __tablename__ = 'Historial_Movimientos_Puntos'

    id_movimiento = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False, index=True)
    id_prenda_referencia = db.Column(db.Integer, db.ForeignKey('Prendas_Accesorios.id_prenda'), nullable=True, index=True)
    
    tipo_movimiento = db.Column(db.String(40), nullable=False)
    cantidad_puntos = db.Column(db.Integer, nullable=False)
    saldo_anterior = db.Column(db.Integer, nullable=False)
    saldo_posterior = db.Column(db.Integer, nullable=False)
    
    descripcion_auditoria = db.Column(db.String(500), nullable=True)
    fecha_movimiento = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Restricción CHECK de tipos de movimiento contable
    __table_args__ = (
        db.CheckConstraint(
            "tipo_movimiento IN ('CREDITO_PUBLICACION', 'CREDITO_APROBACION_JOYA', 'CREDITO_CONVERSION_INVENTARIO', 'DEBITO_ADQUISICION', 'AJUSTE_ADMIN', 'AJUSTE_ADMINISTRATIVO', 'REVERSION_POR_DISPUTA')",
            name='CK_Movimientos_tipo_movimiento'
        ),
    )

    # Relaciones relacionales
    usuario = db.relationship('Usuario', back_populates='movimientos_puntos')
    prenda_referencia = db.relationship('PrendaAccesorio', back_populates='movimientos_puntos')

    def __repr__(self) -> str:
        return f"<HistorialMovimientosPuntos id={self.id_movimiento} usuario={self.id_usuario} tipo='{self.tipo_movimiento}' puntos={self.cantidad_puntos}>"
