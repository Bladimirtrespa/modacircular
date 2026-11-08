"""
Formularios de Publicación de Prendas y Accesorios
Valida de forma estricta los 7 atributos de negocio obligatorios
y la carga de evidencia multimedia (fotos y videos).
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, SelectField, DecimalField, MultipleFileField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, ValidationError

from app.models.categoria_prenda import CategoriaPrenda
from app.models.estado_aspecto import EstadoAspecto
from app.models.nivel_utilidad import NivelUtilidad


class FormularioPublicacionPrenda(FlaskForm):
    """
    Formulario web con validación estricta de los 7 atributos obligatorios
    y carga segura de evidencia multimedia.
    """

    titulo_publicacion = StringField(
        'Título de la Publicación',
        validators=[
            DataRequired(message='El título de la publicación es obligatorio.'),
            Length(min=5, max=150, message='El título debe tener entre 5 y 150 caracteres.')
        ]
    )

    id_categoria = SelectField(
        'Categoría del Artículo',
        coerce=int,
        validators=[DataRequired(message='Debes seleccionar una categoría.')]
    )

    # Atributo Obligatorio 1: Material (se filtra dinámicamente vía AJAX)
    id_material = SelectField(
        'Material o Composición Textil / Joyera',
        coerce=int,
        validators=[DataRequired(message='Debes seleccionar el material del artículo.')]
    )

    # Atributo Obligatorio 2: Medida de largo en centímetros
    medida_largo_cm = DecimalField(
        'Medida de Largo (en centímetros)',
        places=2,
        validators=[
            DataRequired(message='Ingresa la medida de largo en centímetros.'),
            NumberRange(min=0.5, max=500.0, message='La medida debe ser un valor positivo entre 0.5 cm y 500 cm.')
        ]
    )

    # Atributo Obligatorio 3: Talla o Dimensión
    talla = StringField(
        'Talla / Dimensión',
        validators=[
            DataRequired(message='La talla es obligatoria (ej. S, M, L, XL, 38, 40, Talla Única, 18mm).'),
            Length(min=1, max=30, message='La talla debe tener hasta 30 caracteres.')
        ]
    )

    # Atributo Obligatorio 4: Procedencia (marca, origen o tienda)
    procedencia = StringField(
        'Procedencia (Marca, Origen o Tienda)',
        validators=[
            DataRequired(message='La procedencia o marca del artículo es obligatoria.'),
            Length(min=2, max=150, message='La procedencia debe tener entre 2 y 150 caracteres.')
        ]
    )

    # Atributo Obligatorio 5: Estado de Aspecto Físico
    id_estado_aspecto = SelectField(
        'Estado de Conservación y Aspecto',
        coerce=int,
        validators=[DataRequired(message='Debes indicar el estado de conservación.')]
    )

    # Atributo Obligatorio 6: Nivel de Utilidad / Versatilidad
    id_nivel_utilidad = SelectField(
        'Nivel de Utilidad y Versatilidad',
        coerce=int,
        validators=[DataRequired(message='Debes seleccionar el nivel de utilidad.')]
    )

    # Atributo Obligatorio 7: Motivo de Cambio
    motivo_cambio = TextAreaField(
        'Motivo de Cambio',
        validators=[
            DataRequired(message='El motivo de cambio es obligatorio.'),
            Length(min=15, max=600, message='Describe el motivo de cambio con claridad (entre 15 y 600 caracteres).')
        ]
    )

    # Modalidad de Publicación (v3.0): Solo Puntos, Inventario Trueque o Ambos
    modalidad_publicacion = SelectField(
        'Modalidad de Publicación',
        choices=[
            ('SOLO_PUNTOS', 'Solo Puntos (Acreditar puntos inmediatamente a tu billetera)'),
            ('INVENTARIO_TRUEQUE', 'Inventario de Trueque (Guardar en vitrina para trueque directo sin acreditar puntos)'),
            ('AMBOS', 'Ambos (Publicar en catálogo para canje con puntos y visible en vitrina para trueques)')
        ],
        default='SOLO_PUNTOS',
        validators=[DataRequired(message='Debes seleccionar la modalidad de publicación.')]
    )

    # Evidencia Multimedia (al menos 1 archivo requerido: Foto o Video corto)
    archivos_multimedia = MultipleFileField(
        'Fotografías y Video de Evidencia (Máx. 32 MB)'
    )

    boton_publicar = SubmitField('Publicar y Calcular Mis Puntos')

    def validate_archivos_multimedia(self, campo):
        """Valida que se haya adjuntado al menos un archivo con nombre válido."""
        from flask import request
        archivos = request.files.getlist(campo.name)
        archivos_validos = [f for f in archivos if f and f.filename and f.filename.strip()]
        if not archivos_validos:
            raise ValidationError('Debes adjuntar al menos una fotografía o video corto como evidencia del estado real.')

    def cargar_opciones_parametricas(self):
        """
        Puebla dinámicamente las listas desplegables consultando SQL Server (CERO HARDCODING).
        """
        self.id_categoria.choices = [
            (c.id_categoria, f"{c.nombre_categoria} ({c.tipo_articulo})")
            for c in CategoriaPrenda.query.filter_by(activo=True).order_by(CategoriaPrenda.tipo_articulo.desc(), CategoriaPrenda.nombre_categoria.asc()).all()
        ]

        self.id_estado_aspecto.choices = [
            (e.id_estado_aspecto, f"{e.nombre_estado} (Factor: {e.factor_conservacion})")
            for e in EstadoAspecto.query.filter_by(activo=True).order_by(EstadoAspecto.factor_conservacion.desc()).all()
        ]

        self.id_nivel_utilidad.choices = [
            (u.id_nivel_utilidad, f"{u.nombre_utilidad} (+{u.bono_puntos} pts bono)")
            for u in NivelUtilidad.query.filter_by(activo=True).order_by(NivelUtilidad.bono_puntos.asc()).all()
        ]
