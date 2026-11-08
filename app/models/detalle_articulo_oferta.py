"""
Modelo de Detalle de Artículos en Oferta de Trueque
Especifica individualmente cada prenda o accesorio involucrado en la oferta,
distinguiendo entre los ofrecidos y los solicitados con su valor referencial.
"""

from app import db


class DetalleArticuloOferta(db.Model):
    """Mapeo de la tabla Detalle_Articulos_Oferta en SQL Server."""
    __tablename__ = 'Detalle_Articulos_Oferta'

    id_detalle_oferta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_oferta_trueque = db.Column(db.Integer, db.ForeignKey('Ofertas_Trueque.id_oferta_trueque', ondelete='CASCADE'), nullable=False, index=True)
    id_prenda = db.Column(db.Integer, db.ForeignKey('Prendas_Accesorios.id_prenda'), nullable=False, index=True)
    
    rol_articulo = db.Column(db.String(20), nullable=False)  # 'OFRECIDO' o 'SOLICITADO'
    puntos_referencia_momento = db.Column(db.Integer, default=0, nullable=False)

    # Restricción CHECK de roles válidos
    __table_args__ = (
        db.CheckConstraint("rol_articulo IN ('OFRECIDO', 'SOLICITADO')", name='CK_DetalleOferta_Rol'),
    )

    # Relaciones relacionales
    oferta = db.relationship('OfertaTrueque', back_populates='articulos_detalle')
    prenda = db.relationship('PrendaAccesorio', back_populates='detalles_oferta')

    def __repr__(self) -> str:
        return f"<DetalleArticuloOferta id={self.id_detalle_oferta} oferta={self.id_oferta_trueque} prenda={self.id_prenda} rol='{self.rol_articulo}'>"
