"""
Modelo de Ofertas de Trueque Directo
Gestiona propuestas de intercambio N a M entre usuarios con trazabilidad de contraofertas,
balance de puntos referenciales y ciclo de vida de la negociación.
"""

from datetime import datetime
from app import db


class OfertaTrueque(db.Model):
    """Mapeo de la tabla Ofertas_Trueque en SQL Server."""
    __tablename__ = 'Ofertas_Trueque'

    id_oferta_trueque = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario_ofertante = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False, index=True)
    id_usuario_receptor = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False, index=True)
    id_oferta_padre = db.Column(db.Integer, db.ForeignKey('Ofertas_Trueque.id_oferta_trueque'), nullable=True)

    mensaje_propuesta = db.Column(db.String(500), nullable=True)
    puntos_totales_ofrecidos = db.Column(db.Integer, default=0, nullable=False)
    puntos_totales_solicitados = db.Column(db.Integer, default=0, nullable=False)
    
    estado_oferta = db.Column(db.String(25), default='PENDIENTE', nullable=False, index=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_resolucion = db.Column(db.DateTime, nullable=True)

    # Restricción CHECK de estados válidos de la oferta
    __table_args__ = (
        db.CheckConstraint(
            "estado_oferta IN ('PENDIENTE', 'ACEPTADA', 'RECHAZADA', 'CANCELADA', 'CONTRAOFERTA')",
            name='CK_Ofertas_EstadoValido'
        ),
    )

    # Relaciones relacionales
    usuario_ofertante = db.relationship('Usuario', foreign_keys=[id_usuario_ofertante], back_populates='ofertas_enviadas')
    usuario_receptor = db.relationship('Usuario', foreign_keys=[id_usuario_receptor], back_populates='ofertas_recibidas')
    oferta_padre = db.relationship('OfertaTrueque', remote_side=[id_oferta_trueque], backref='contraofertas')
    
    articulos_detalle = db.relationship('DetalleArticuloOferta', back_populates='oferta', cascade='all, delete-orphan', lazy='dynamic')
    salas_chat = db.relationship('SalaChatIntercambio', back_populates='oferta_trueque', lazy='dynamic')

    @property
    def articulos_ofrecidos(self):
        """Retorna la lista de detalles de artículos que ofrece el usuario emisor."""
        return self.articulos_detalle.filter_by(rol_articulo='OFRECIDO').all()

    @property
    def articulos_solicitados(self):
        """Retorna la lista de detalles de artículos solicitados al receptor."""
        return self.articulos_detalle.filter_by(rol_articulo='SOLICITADO').all()

    @property
    def diferencia_puntos(self) -> int:
        """Diferencia neta de valor en puntos: ofrecidos menos solicitados."""
        return self.puntos_totales_ofrecidos - self.puntos_totales_solicitados

    def __repr__(self) -> str:
        return f"<OfertaTrueque id={self.id_oferta_trueque} de={self.id_usuario_ofertante} a={self.id_usuario_receptor} estado='{self.estado_oferta}'>"
