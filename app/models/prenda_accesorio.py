"""
Modelo de Prendas y Accesorios
Alberga las publicaciones de los usuarios con los 7 atributos obligatorios,
cálculo dinámico de puntos y estado de publicación en el ciclo de vida.
"""

from datetime import datetime
from app import db


class PrendaAccesorio(db.Model):
    """Mapeo de la tabla Prendas_Accesorios en SQL Server."""
    __tablename__ = 'Prendas_Accesorios'

    id_prenda = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Claves foráneas a tablas maestras
    id_usuario_propietario = db.Column(db.Integer, db.ForeignKey('Usuarios.id_usuario'), nullable=False, index=True)
    id_categoria = db.Column(db.Integer, db.ForeignKey('Categorias_Prenda.id_categoria'), nullable=False, index=True)
    id_material = db.Column(db.Integer, db.ForeignKey('Materiales.id_material'), nullable=False, index=True)
    id_estado_aspecto = db.Column(db.Integer, db.ForeignKey('Estados_Aspecto.id_estado_aspecto'), nullable=False)
    id_nivel_utilidad = db.Column(db.Integer, db.ForeignKey('Niveles_Utilidad.id_nivel_utilidad'), nullable=False)

    # Atributos descriptivos y obligatorios de la publicación (7 atributos de negocio)
    titulo_publicacion = db.Column(db.String(150), nullable=False)
    medida_largo_cm = db.Column(db.Numeric(6, 2), nullable=False)   # Atributo 2: Medida de largo en cm
    talla = db.Column(db.String(20), nullable=False)                 # Atributo 3: Talla
    procedencia = db.Column(db.String(100), nullable=False)          # Atributo 4: Procedencia (marca/origen)
    motivo_cambio = db.Column(db.String(1000), nullable=False)       # Atributo 7: Motivo de cambio

    # Valoración en puntos y ciclo de vida de la prenda
    puntos_valoracion = db.Column(db.Integer, nullable=False)
    modalidad_publicacion = db.Column(db.String(25), default='SOLO_PUNTOS', nullable=False)
    estado_publicacion = db.Column(db.String(30), nullable=False, default='PUBLICADA', index=True)
    fecha_publicacion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Restricciones CHECK de estados y modalidades válidas
    __table_args__ = (
        db.CheckConstraint(
            "estado_publicacion IN ('PUBLICADA', 'EN_INVENTARIO', 'PENDIENTE_APROBACION', 'RESERVADA_TRUEQUE', 'INTERCAMBIADA', 'RECHAZADA', 'INACTIVA')",
            name='CK_Prendas_estado_publicacion'
        ),
        db.CheckConstraint(
            "modalidad_publicacion IN ('SOLO_PUNTOS', 'INVENTARIO_TRUEQUE', 'AMBOS')",
            name='CK_Prendas_modalidad_publicacion'
        ),
    )

    # Relaciones relacionales
    propietario = db.relationship('Usuario', back_populates='prendas', foreign_keys=[id_usuario_propietario])
    categoria = db.relationship('CategoriaPrenda', back_populates='prendas')
    material = db.relationship('Material', back_populates='prendas')
    estado_aspecto = db.relationship('EstadoAspecto', back_populates='prendas')
    nivel_utilidad = db.relationship('NivelUtilidad', back_populates='prendas')

    # Relaciones hijas
    archivos_multimedia = db.relationship('MultimediaPrenda', back_populates='prenda', cascade='all, delete-orphan', lazy='dynamic')
    solicitudes_aprobacion = db.relationship('SolicitudAprobacionMaterial', back_populates='prenda', cascade='all, delete-orphan', lazy='dynamic')
    transacciones = db.relationship('TransaccionAdquisicion', back_populates='prenda', lazy='dynamic')
    movimientos_puntos = db.relationship('HistorialMovimientosPuntos', back_populates='prenda_referencia', lazy='dynamic')
    detalles_oferta = db.relationship('DetalleArticuloOferta', back_populates='prenda', lazy='dynamic')

    @property
    def archivo_portada(self):
        """Devuelve el archivo multimedia principal o el primero disponible."""
        portada = self.archivos_multimedia.filter_by(es_portada=True).first()
        if not portada:
            portada = self.archivos_multimedia.first()
        return portada

    def __repr__(self) -> str:
        return f"<PrendaAccesorio id={self.id_prenda} titulo='{self.titulo_publicacion}' puntos={self.puntos_valoracion} estado='{self.estado_publicacion}'>"
