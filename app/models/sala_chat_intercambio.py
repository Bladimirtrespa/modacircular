"""
Modelo de Salas de Chat de Intercambio
Espacio de mensajería privada generado tras acordar un trueque o compra con puntos,
donde se gestiona la ficha logística de envío y confirmación mutua de entrega.
"""

from datetime import datetime
from app import db


class SalaChatIntercambio(db.Model):
    """Mapeo de la tabla Salas_Chat_Intercambio en SQL Server."""
    __tablename__ = 'Salas_Chat_Intercambio'

    id_sala_chat = db.Column(db.Integer, primary_key=True, autoincrement=True)
    codigo_sala = db.Column(db.String(50), unique=True, nullable=False)
    tipo_operacion = db.Column(db.String(30), nullable=False)  # 'TRUEQUE_INVENTARIO' o 'ADQUISICION_PUNTOS'

    id_oferta_trueque = db.Column(db.Integer, db.ForeignKey('Ofertas_Trueque.id_oferta_trueque'), nullable=True)
    id_transaccion_adquisicion = db.Column(db.Integer, db.ForeignKey('Transacciones_Adquisicion.id_transaccion'), nullable=True)

    id_usuario_1 = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False, index=True)
    id_usuario_2 = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False, index=True)

    # Logística de entrega o envío a domicilio
    metodo_entrega = db.Column(db.String(30), default='POR_DEFINIR', nullable=False)  # 'POR_DEFINIR', 'ENTREGA_PRESENCIAL', 'ENVIO_DOMICILIO'
    direccion_envio = db.Column(db.String(250), nullable=True)
    ciudad_destino = db.Column(db.String(100), nullable=True)
    nombre_receptor_envio = db.Column(db.String(150), nullable=True)
    telefono_contacto_envio = db.Column(db.String(30), nullable=True)
    empresa_transportadora = db.Column(db.String(100), nullable=True)
    numero_guia_rastreo = db.Column(db.String(100), nullable=True)

    # Confirmación dual de recepción
    confirmado_usuario_1 = db.Column(db.Boolean, default=False, nullable=False)
    confirmado_usuario_2 = db.Column(db.Boolean, default=False, nullable=False)

    estado_sala = db.Column(db.String(30), default='ACTIVA', nullable=False, index=True)  # 'ACTIVA', 'EN_DISPUTA_AUDITORIA', 'CERRADA_EXITOSA', 'CANCELADA_POR_FRAUDE'
    fecha_apertura = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    fecha_cierre = db.Column(db.DateTime, nullable=True)

    # Restricciones CHECK
    __table_args__ = (
        db.CheckConstraint("tipo_operacion IN ('TRUEQUE_INVENTARIO', 'ADQUISICION_PUNTOS')", name='CK_SalasChat_TipoOperacion'),
        db.CheckConstraint("metodo_entrega IN ('POR_DEFINIR', 'ENTREGA_PRESENCIAL', 'ENVIO_DOMICILIO')", name='CK_SalasChat_MetodoEntrega'),
        db.CheckConstraint("estado_sala IN ('ACTIVA', 'EN_DISPUTA_AUDITORIA', 'CERRADA_EXITOSA', 'CANCELADA_POR_FRAUDE')", name='CK_SalasChat_Estado'),
    )

    # Relaciones relacionales
    oferta_trueque = db.relationship('OfertaTrueque', back_populates='salas_chat')
    transaccion_adquisicion = db.relationship('TransaccionAdquisicion')
    usuario_1 = db.relationship('Usuario', foreign_keys=[id_usuario_1], back_populates='salas_chat_1')
    usuario_2 = db.relationship('Usuario', foreign_keys=[id_usuario_2], back_populates='salas_chat_2')

    mensajes = db.relationship('MensajeChat', back_populates='sala', cascade='all, delete-orphan', lazy='dynamic')
    reportes = db.relationship('ReporteComportamientoEstafa', back_populates='sala', lazy='dynamic')

    @property
    def ambas_partes_confirmaron(self) -> bool:
        """Determina si ambos usuarios marcaron como recibido el artículo."""
        return self.confirmado_usuario_1 and self.confirmado_usuario_2

    def __repr__(self) -> str:
        return f"<SalaChatIntercambio id={self.id_sala_chat} codigo='{self.codigo_sala}' estado='{self.estado_sala}'>"
