"""
Modelo de Categorías de Prendas y Accesorios
Define el tipo de artículo (PRENDA o ACCESORIO) y el puntaje base de la fórmula.
Alineado con el esquema existente en SQL Server (puntaje_base: int).
"""

from app import db


class CategoriaPrenda(db.Model):
    """Mapeo de la tabla Categorias_Prenda en SQL Server."""
    __tablename__ = 'Categorias_Prenda'

    id_categoria = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_categoria = db.Column(db.String(80), unique=True, nullable=False, index=True)
    tipo_articulo = db.Column(db.String(30), nullable=False)  # 'PRENDA' o 'ACCESORIO'
    puntaje_base = db.Column(db.Integer, nullable=False, default=0)
    descripcion = db.Column(db.String(250), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Restricción CHECK de integridad a nivel de tabla
    __table_args__ = (
        db.CheckConstraint("tipo_articulo IN ('PRENDA', 'ACCESORIO')", name='CK_Categorias_tipo_articulo'),
    )

    # Relación con prendas y accesorios
    prendas = db.relationship('PrendaAccesorio', back_populates='categoria', lazy='dynamic')

    def __repr__(self) -> str:
        return f"<CategoriaPrenda id={self.id_categoria} nombre='{self.nombre_categoria}' tipo='{self.tipo_articulo}' base={self.puntaje_base}>"
