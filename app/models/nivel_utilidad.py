"""
Modelo de Niveles de Utilidad
Define la versatilidad de uso y el bono directo de puntos sumado a la valoración.
"""

from app import db


class NivelUtilidad(db.Model):
    """Mapeo de la tabla Niveles_Utilidad en SQL Server."""
    __tablename__ = 'Niveles_Utilidad'

    id_nivel_utilidad = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_utilidad = db.Column(db.String(50), unique=True, nullable=False, index=True)
    bono_puntos = db.Column(db.Integer, nullable=False, default=0)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Relación con prendas y accesorios
    prendas = db.relationship('PrendaAccesorio', back_populates='nivel_utilidad', lazy='dynamic')

    def __repr__(self) -> str:
        return f"<NivelUtilidad id={self.id_nivel_utilidad} nombre='{self.nombre_utilidad}' bono={self.bono_puntos}>"
