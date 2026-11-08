"""
Modelo de Estados de Aspecto
Define la escala de condición física del artículo y su factor de conservación.
"""

from app import db


class EstadoAspecto(db.Model):
    """Mapeo de la tabla Estados_Aspecto en SQL Server."""
    __tablename__ = 'Estados_Aspecto'

    id_estado_aspecto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_estado = db.Column(db.String(50), unique=True, nullable=False, index=True)
    factor_conservacion = db.Column(db.Numeric(5, 2), nullable=False, default=1.00)
    descripcion_criterio = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Relación con prendas y accesorios
    prendas = db.relationship('PrendaAccesorio', back_populates='estado_aspecto', lazy='dynamic')

    def __repr__(self) -> str:
        return f"<EstadoAspecto id={self.id_estado_aspecto} nombre='{self.nombre_estado}' factor={self.factor_conservacion}>"
