"""
Modelo de Materiales (Catálogo Maestro de 55 Materiales)
Contiene exactamente las 12 columnas maestras con factores, bonos,
clasificación de joyería y requerimientos de aprobación especial.
Alineado con el esquema existente en SQL Server.
"""

from app import db


class Material(db.Model):
    """Mapeo de la tabla Materiales en SQL Server con exactamente 12 columnas."""
    __tablename__ = 'Materiales'

    # 1. Identificador único primario
    id_material = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # 2. Código SKU único (ej. MAT-SIN-001)
    codigo_material = db.Column(db.String(25), unique=True, nullable=False, index=True)
    
    # 3. Nombre del material
    nombre_material = db.Column(db.String(100), unique=True, nullable=False)
    
    # 4. Familia taxonómica (ej. Fibras Naturales, Metales Preciosos, etc.)
    familia_material = db.Column(db.String(60), nullable=False, index=True)
    
    # 5. Uso aplicable ('PRENDA', 'ACCESORIO' o 'AMBOS')
    uso_principal = db.Column(db.String(30), nullable=False)
    
    # 6. Factor multiplicador para el cálculo de puntos
    factor_multiplicador = db.Column(db.Numeric(5, 2), nullable=False, default=1.00)
    
    # 7. Bono de puntos adicional por material
    bono_puntos_material = db.Column(db.Integer, nullable=False, default=0)
    
    # 8. Nivel de sostenibilidad ambiental (máx 30 caracteres en SQL Server)
    nivel_sostenibilidad = db.Column(db.String(30), nullable=False)
    
    # 9. Bandera indicadora si es metal o joya preciosa
    es_metal_o_joya_preciosa = db.Column(db.Boolean, nullable=False, default=False)
    
    # 10. Bandera que exige flujo de moderación previa antes de acreditar puntos
    requiere_aprobacion_especial = db.Column(db.Boolean, nullable=False, default=False)
    
    # 11. Descripción técnica de la composición y atributos del material
    descripcion_tecnica = db.Column(db.String(300), nullable=False)
    
    # 12. Estado activo/inactivo para el catálogo
    activo = db.Column(db.Boolean, nullable=False, default=True)

    # Restricción CHECK de integridad
    __table_args__ = (
        db.CheckConstraint("uso_principal IN ('PRENDA', 'ACCESORIO', 'AMBOS')", name='CK_Materiales_uso_principal'),
    )

    # Relación con prendas y accesorios
    prendas = db.relationship('PrendaAccesorio', back_populates='material', lazy='dynamic')

    def a_diccionario(self) -> dict:
        """Serializa el modelo a un diccionario para consumo en APIs, AJAX y CRUD."""
        return {
            'id_material': self.id_material,
            'codigo_material': self.codigo_material,
            'nombre_material': self.nombre_material,
            'familia_material': self.familia_material,
            'uso_principal': self.uso_principal,
            'factor_multiplicador': float(self.factor_multiplicador),
            'bono_puntos_material': self.bono_puntos_material,
            'nivel_sostenibilidad': self.nivel_sostenibilidad,
            'es_metal_o_joya_preciosa': self.es_metal_o_joya_preciosa,
            'requiere_aprobacion_especial': self.requiere_aprobacion_especial,
            'descripcion_tecnica': self.descripcion_tecnica,
            'activo': self.activo
        }

    def obtener_clase_familia(self) -> str:
        """Retorna una clase CSS temática según la familia taxonómica para badges vibrantes."""
        familia_lower = self.familia_material.lower()
        if 'sintético' in familia_lower or 'semisintético' in familia_lower:
            return 'badge-familia-sintetico'
        elif 'vegetal' in familia_lower or 'fibras naturales' in familia_lower:
            return 'badge-familia-vegetal'
        elif 'animal' in familia_lower or 'lujo' in familia_lower:
            return 'badge-familia-animal'
        elif 'cuero' in familia_lower or 'calzado' in familia_lower:
            return 'badge-familia-cuero'
        elif 'joya' in familia_lower or 'metal precioso' in familia_lower or 'gema' in familia_lower:
            return 'badge-familia-joya'
        return 'badge-familia-accesorio'

    def obtener_clase_sostenibilidad(self) -> str:
        """Retorna la clase CSS adecuada según el nivel de sostenibilidad ambiental."""
        nivel = (self.nivel_sostenibilidad or '').lower()
        if 'alto' in nivel or 'eco' in nivel or 'orgánico' in nivel:
            return 'badge-sostenible-alto'
        elif 'medio' in nivel or 'durabilidad' in nivel:
            return 'badge-sostenible-medio'
        elif 'máximo' in nivel or 'platino' in nivel or 'oro' in nivel:
            return 'badge-sostenible-lujo'
        return 'badge-sostenible-estandar'

    def __repr__(self) -> str:
        return f"<Material id={self.id_material} codigo='{self.codigo_material}' nombre='{self.nombre_material}' factor={self.factor_multiplicador} joya={self.es_metal_o_joya_preciosa}>"
