"""
Modelo de Roles de Usuario
Define los perfiles de acceso (Usuario, Moderador, Administrador) en la plataforma.
"""

from app import db


class RolUsuario(db.Model):
    """Mapeo de la tabla Roles_Usuario en SQL Server."""
    __tablename__ = 'Roles_Usuario'

    id_rol = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_rol = db.Column(db.String(50), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.String(255), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Relación con Usuarios
    usuarios = db.relationship('Usuario', back_populates='rol', lazy='dynamic')

    def __repr__(self) -> str:
        return f"<RolUsuario id={self.id_rol} nombre='{self.nombre_rol}'>"
