"""
Modelo de Multimedia de Prendas y Accesorios
Almacena las referencias a las fotos y videos de evidencia subidos por el usuario.
"""

from datetime import datetime
from app import db


class MultimediaPrenda(db.Model):
    """Mapeo de la tabla Multimedia_Prenda en SQL Server."""
    __tablename__ = 'Multimedia_Prenda'

    id_multimedia = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_prenda = db.Column(db.Integer, db.ForeignKey('Prendas_Accesorios.id_prenda'), nullable=False, index=True)
    tipo_archivo = db.Column(db.String(15), nullable=False)  # 'FOTO' o 'VIDEO'
    ruta_archivo = db.Column(db.String(400), nullable=False)
    es_portada = db.Column(db.Boolean, default=False, nullable=False)
    fecha_carga = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Restricción CHECK de tipos permitidos en SQL Server (CK_Multimedia_Tipo)
    __table_args__ = (
        db.CheckConstraint("tipo_archivo IN ('FOTO', 'VIDEO')", name='CK_Multimedia_tipo_archivo'),
    )

    # Relación con la prenda
    prenda = db.relationship('PrendaAccesorio', back_populates='archivos_multimedia')

    def __repr__(self) -> str:
        return f"<MultimediaPrenda id={self.id_multimedia} prenda={self.id_prenda} tipo='{self.tipo_archivo}' portada={self.es_portada}>"
