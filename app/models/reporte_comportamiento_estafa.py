"""
Modelo de Reportes de Comportamiento y Estafa
Permite a los usuarios denunciar fraudes, incumplimientos o abusos en una sala de chat,
congelando el estado para resolución, dictamen y sanción por parte del Administrador.
"""

from datetime import datetime
from app import db


class ReporteComportamientoEstafa(db.Model):
    """Mapeo de la tabla Reportes_Comportamiento_Estafa en SQL Server."""
    __tablename__ = 'Reportes_Comportamiento_Estafa'

    id_reporte = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_sala_chat = db.Column(db.Integer, db.ForeignKey('Salas_Chat_Intercambio.id_sala_chat'), nullable=False, index=True)
    id_usuario_denunciante = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False)
    id_usuario_denunciado = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False)

    categoria_reporte = db.Column(db.String(50), nullable=False)
    descripcion_hechos = db.Column(db.String(1500), nullable=False)
    ruta_evidencia_reporte = db.Column(db.String(300), nullable=True)

    estado_reporte = db.Column(db.String(30), default='PENDIENTE_REVISION', nullable=False, index=True)
    id_admin_revisor = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=True)
    dictamen_administrador = db.Column(db.String(1000), nullable=True)
    accion_aplicada = db.Column(db.String(100), nullable=True)

    fecha_reporte = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_resolucion = db.Column(db.DateTime, nullable=True)

    # Restricciones CHECK
    __table_args__ = (
        db.CheckConstraint(
            "categoria_reporte IN ('INTENTO_ESTAFA', 'ARTICULO_FALSIFICADO_O_DISTINTO', 'NO_ENVIO_O_INCUMPLIMIENTO', 'LENGUAJE_OFENSIVO_O_ACOSO', 'SOLICITUD_DINERO_EXTERNO')",
            name='CK_Reportes_Categoria'
        ),
        db.CheckConstraint(
            "estado_reporte IN ('PENDIENTE_REVISION', 'EN_INVESTIGACION', 'RESUELTO_CON_SANCION', 'DESESTIMADO')",
            name='CK_Reportes_Estado'
        ),
    )

    # Relaciones relacionales
    sala = db.relationship('SalaChatIntercambio', back_populates='reportes')
    denunciante = db.relationship('Usuario', foreign_keys=[id_usuario_denunciante], back_populates='reportes_interpuestos')
    denunciado = db.relationship('Usuario', foreign_keys=[id_usuario_denunciado], back_populates='reportes_denunciados')
    admin_revisor = db.relationship('Usuario', foreign_keys=[id_admin_revisor])

    def __repr__(self) -> str:
        return f"<ReporteComportamientoEstafa id={self.id_reporte} sala={self.id_sala_chat} categoria='{self.categoria_reporte}' estado='{self.estado_reporte}'>"
