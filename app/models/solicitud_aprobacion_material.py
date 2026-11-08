"""
Modelo de Solicitudes de Aprobación de Material
Gestiona la cola de moderación para metales y joyas preciosas (Grupo F)
que requieren revisión obligatoria de autenticidad antes de acreditar puntos.
"""

from datetime import datetime
from app import db


class SolicitudAprobacionMaterial(db.Model):
    """Mapeo de la tabla Solicitudes_Aprobacion_Material en SQL Server."""
    __tablename__ = 'Solicitudes_Aprobacion_Material'

    id_solicitud_aprobacion = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_prenda = db.Column(db.Integer, db.ForeignKey('Prendas_Accesorios.id_prenda'), nullable=False, index=True)
    id_usuario_revisor = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=True, index=True)
    
    estado_revision = db.Column(db.String(30), nullable=False, default='PENDIENTE', index=True)
    observaciones_revisor = db.Column(db.String(500), nullable=True)
    
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_resolucion = db.Column(db.DateTime, nullable=True)

    # Restricción CHECK de estados válidos de revisión
    __table_args__ = (
        db.CheckConstraint("estado_revision IN ('PENDIENTE', 'APROBADA', 'RECHAZADA')", name='CK_Solicitudes_estado_revision'),
    )

    # Relaciones relacionales
    prenda = db.relationship('PrendaAccesorio', back_populates='solicitudes_aprobacion')
    revisor = db.relationship('Usuario', back_populates='solicitudes_revisadas', foreign_keys=[id_usuario_revisor])

    def __repr__(self) -> str:
        return f"<SolicitudAprobacionMaterial id={self.id_solicitud_aprobacion} prenda={self.id_prenda} estado='{self.estado_revision}'>"
