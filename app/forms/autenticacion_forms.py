"""
Formularios de Autenticación de Usuarios
Valida los datos de registro e inicio de sesión con Flask-WTF.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

from app.models.usuario import Usuario


class FormularioRegistro(FlaskForm):
    """Formulario para la creación de cuentas individuales."""
    
    nombre_completo = StringField(
        'Nombre Completo',
        validators=[
            DataRequired(message='El nombre completo es obligatorio.'),
            Length(min=3, max=120, message='El nombre debe tener entre 3 y 120 caracteres.')
        ]
    )
    
    correo_electronico = StringField(
        'Correo Electrónico',
        validators=[
            DataRequired(message='El correo electrónico es obligatorio.'),
            Email(message='Ingresa una dirección de correo válida.'),
            Length(max=150, message='El correo no debe superar los 150 caracteres.')
        ]
    )
    
    telefono = StringField(
        'Teléfono / Celular de Contacto',
        validators=[
            Length(max=30, message='El teléfono no debe superar los 30 caracteres.')
        ]
    )
    
    ciudad_ubicacion = StringField(
        'Ciudad de Ubicación',
        validators=[
            DataRequired(message='La ciudad de ubicación es obligatoria para los intercambios.'),
            Length(min=2, max=100, message='La ciudad debe tener entre 2 y 100 caracteres.')
        ]
    )
    
    contrasena = PasswordField(
        'Contraseña',
        validators=[
            DataRequired(message='La contraseña es obligatoria.'),
            Length(min=6, message='La contraseña debe tener al menos 6 caracteres.')
        ]
    )
    
    confirmar_contrasena = PasswordField(
        'Confirmar Contraseña',
        validators=[
            DataRequired(message='Por favor confirma tu contraseña.'),
            EqualTo('contrasena', message='Las contraseñas no coinciden.')
        ]
    )
    
    boton_registro = SubmitField('Crear Cuenta e Iniciar en ModaCircular')

    def validate_correo_electronico(self, campo):
        """Valida dinámicamente que el correo no se encuentre registrado en SQL Server."""
        correo_normalizado = campo.data.strip().lower()
        usuario_existente = Usuario.query.filter_by(correo_electronico=correo_normalizado).first()
        if usuario_existente:
            raise ValidationError('Este correo electrónico ya se encuentra registrado. Inicia sesión o utiliza otro.')


class FormularioInicioSesion(FlaskForm):
    """Formulario para inicio de sesión en la plataforma."""
    
    correo_electronico = StringField(
        'Correo Electrónico',
        validators=[
            DataRequired(message='Ingresa tu correo electrónico.'),
            Email(message='Ingresa un correo electrónico válido.')
        ]
    )
    
    contrasena = PasswordField(
        'Contraseña',
        validators=[
            DataRequired(message='Ingresa tu contraseña.')
        ]
    )
    
    recordarme = BooleanField('Mantener mi sesión iniciada')
    
    boton_iniciar_sesion = SubmitField('Iniciar Sesión')
