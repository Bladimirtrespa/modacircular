"""
Modelo de Usuario del Sistema
Gestiona cuentas de usuario, autenticación (Flask-Login),
seguridad de contraseñas y doble billetera de puntos (disponibles y retenidos).
Alineado con el esquema existente en SQL Server.
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


class Usuario(UserMixin, db.Model):
    """Mapeo de la tabla Usuarios en SQL Server."""
    __tablename__ = 'Usuarios'

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_rol = db.Column(db.Integer, db.ForeignKey('Roles_Usuario.id_rol'), nullable=False)
    nombre_completo = db.Column(db.String(120), nullable=False)
    correo_electronico = db.Column(db.String(150), unique=True, nullable=False, index=True)
    hash_contrasena = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(30), nullable=True)
    ciudad_ubicacion = db.Column(db.String(100), nullable=False)
    
    # Nuevas columnas v3.0: logística y perfil público de trueque
    direccion_predeterminada = db.Column(db.String(250), nullable=True)
    biografia_vitrina = db.Column(db.String(300), nullable=True)
    reputacion_trueques = db.Column(db.Integer, default=100, nullable=False)

    # Billetera dual del usuario
    saldo_puntos_disponibles = db.Column(db.Integer, default=0, nullable=False)
    saldo_puntos_retenidos = db.Column(db.Integer, default=0, nullable=False)
    
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Gestión de suspensiones temporales y permanentes
    fecha_fin_suspension = db.Column(db.DateTime, nullable=True)
    motivo_suspension = db.Column(db.String(255), nullable=True)

    # Relaciones relacionales
    rol = db.relationship('RolUsuario', back_populates='usuarios')
    prendas = db.relationship('PrendaAccesorio', back_populates='propietario', lazy='dynamic', foreign_keys='PrendaAccesorio.id_usuario_propietario')
    movimientos_puntos = db.relationship('HistorialMovimientosPuntos', back_populates='usuario', lazy='dynamic')
    compras = db.relationship('TransaccionAdquisicion', back_populates='comprador', lazy='dynamic', foreign_keys='TransaccionAdquisicion.id_usuario_comprador')
    ventas = db.relationship('TransaccionAdquisicion', back_populates='oferente', lazy='dynamic', foreign_keys='TransaccionAdquisicion.id_usuario_oferente')
    solicitudes_revisadas = db.relationship('SolicitudAprobacionMaterial', back_populates='revisor', lazy='dynamic', foreign_keys='SolicitudAprobacionMaterial.id_usuario_revisor')

    # Relaciones de Trueque, Chat y Reportes (v3.0)
    ofertas_enviadas = db.relationship('OfertaTrueque', back_populates='usuario_ofertante', foreign_keys='OfertaTrueque.id_usuario_ofertante', lazy='dynamic')
    ofertas_recibidas = db.relationship('OfertaTrueque', back_populates='usuario_receptor', foreign_keys='OfertaTrueque.id_usuario_receptor', lazy='dynamic')
    salas_chat_1 = db.relationship('SalaChatIntercambio', back_populates='usuario_1', foreign_keys='SalaChatIntercambio.id_usuario_1', lazy='dynamic')
    salas_chat_2 = db.relationship('SalaChatIntercambio', back_populates='usuario_2', foreign_keys='SalaChatIntercambio.id_usuario_2', lazy='dynamic')
    mensajes_enviados = db.relationship('MensajeChat', back_populates='emisor', lazy='dynamic')
    reportes_denunciados = db.relationship('ReporteComportamientoEstafa', back_populates='denunciado', foreign_keys='ReporteComportamientoEstafa.id_usuario_denunciado', lazy='dynamic')
    reportes_interpuestos = db.relationship('ReporteComportamientoEstafa', back_populates='denunciante', foreign_keys='ReporteComportamientoEstafa.id_usuario_denunciante', lazy='dynamic')

    def get_id(self) -> str:
        """Identificador requerido por Flask-Login."""
        return str(self.id_usuario)

    def establecer_contrasena(self, contrasena_plana: str) -> None:
        """Genera y almacena el hash criptográfico seguro de la contraseña."""
        self.hash_contrasena = generate_password_hash(contrasena_plana)

    def verificar_contrasena(self, contrasena_plana: str) -> bool:
        """Verifica la contraseña ingresada contra el hash almacenado."""
        return check_password_hash(self.hash_contrasena, contrasena_plana)

    @property
    def es_administrador(self) -> bool:
        """Verifica si el usuario cuenta con el rol de Administrador."""
        return self.rol and self.rol.nombre_rol.upper() in ('ADMINISTRADOR', 'ADMIN')

    @property
    def es_moderador(self) -> bool:
        """Verifica si el usuario cuenta con el rol de Moderador o Administrador."""
        return self.rol and self.rol.nombre_rol.upper() in ('MODERADOR', 'ADMINISTRADOR', 'ADMIN')

    @property
    def esta_suspendido(self) -> bool:
        """Determina si la cuenta está bajo suspensión activa (temporal o permanente)."""
        if not self.activo:
            return True
        if self.fecha_fin_suspension and datetime.utcnow() < self.fecha_fin_suspension:
            return True
        return False

    @property
    def estado_suspension_legible(self) -> str:
        """Retorna una descripción humana del estado de la cuenta."""
        if not self.activo and not self.fecha_fin_suspension:
            return "Suspendido Permanente"
        if self.fecha_fin_suspension:
            if datetime.utcnow() < self.fecha_fin_suspension:
                return f"Suspendido hasta {self.fecha_fin_suspension.strftime('%d/%m/%Y %H:%M')}"
            return "Suspensión Expirada (Activo)"
        return "Activo"

    def reactivar_si_expirado(self) -> bool:
        """Si la suspensión temporal venció, reactiva automáticamente la cuenta."""
        if self.fecha_fin_suspension and datetime.utcnow() >= self.fecha_fin_suspension:
            self.activo = True
            self.fecha_fin_suspension = None
            self.motivo_suspension = None
            return True
        return False

    def __repr__(self) -> str:
        return f"<Usuario id={self.id_usuario} correo='{self.correo_electronico}' disponibles={self.saldo_puntos_disponibles} retenidos={self.saldo_puntos_retenidos}>"
