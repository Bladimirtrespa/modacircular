"""
Modelo de Transacciones de Adquisición
Registra el intercambio de prendas o accesorios entre usuarios a cambio de puntos.
"""

from datetime import datetime
from app import db


class TransaccionAdquisicion(db.Model):
    """Mapeo de la tabla Transacciones_Adquisicion en SQL Server."""
    __tablename__ = 'Transacciones_Adquisicion'

    id_transaccion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_prenda = db.Column(db.Integer, db.ForeignKey('Prendas_Accesorios.id_prenda'), nullable=False, index=True)
    id_usuario_comprador = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False, index=True)
    id_usuario_oferente = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False, index=True)
    
    puntos_canjeados = db.Column(db.Integer, nullable=False)
    estado_entrega = db.Column(db.String(30), nullable=False, default='COMPLETADA', index=True)
    fecha_transaccion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Restricción CHECK de estados válidos de entrega en SQL Server
    __table_args__ = (
        db.CheckConstraint("estado_entrega IN ('COMPLETADA', 'CANCELADA')", name='CK_Transacciones_estado_entrega'),
    )

    # Relaciones relacionales
    prenda = db.relationship('PrendaAccesorio', back_populates='transacciones')
    comprador = db.relationship('Usuario', back_populates='compras', foreign_keys=[id_usuario_comprador])
    oferente = db.relationship('Usuario', back_populates='ventas', foreign_keys=[id_usuario_oferente])

    def __repr__(self) -> str:
        return f"<TransaccionAdquisicion id={self.id_transaccion} prenda={self.id_prenda} puntos={self.puntos_canjeados} estado='{self.estado_entrega}'>"
