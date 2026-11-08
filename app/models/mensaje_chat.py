"""
Modelo de Mensajes de Chat de Intercambio
Contiene los mensajes de texto, avisos de sistema e imágenes adjuntas
intercambiadas en una sala privada, con trazabilidad inmutable para auditoría.
"""

from datetime import datetime
from app import db


class MensajeChat(db.Model):
    """Mapeo de la tabla Mensajes_Chat en SQL Server."""
    __tablename__ = 'Mensajes_Chat'

    id_mensaje = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_sala_chat = db.Column(db.Integer, db.ForeignKey('Salas_Chat_Intercambio.id_sala_chat', ondelete='CASCADE'), nullable=False, index=True)
    id_usuario_emisor = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False, index=True)

    contenido_mensaje = db.Column(db.String(1000), nullable=False)
    ruta_adjunto = db.Column(db.String(300), nullable=True)
    es_mensaje_sistema = db.Column(db.Boolean, default=False, nullable=False)
    leido = db.Column(db.Boolean, default=False, nullable=False)
    fecha_envio = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relaciones relacionales
    sala = db.relationship('SalaChatIntercambio', back_populates='mensajes')
    emisor = db.relationship('Usuario', back_populates='mensajes_enviados')

    def __repr__(self) -> str:
        return f"<MensajeChat id={self.id_mensaje} sala={self.id_sala_chat} emisor={self.id_usuario_emisor}>"
