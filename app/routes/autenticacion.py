"""
Controlador de Autenticación de Usuarios (Blueprint de Autenticación)
Maneja el registro de cuentas individuales, inicio de sesión (Flask-Login),
cierre de sesión seguro y consulta de perfil con billetera de puntos.
"""

from datetime import datetime
from urllib.parse import urlsplit
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.usuario import Usuario
from app.models.rol_usuario import RolUsuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.forms.autenticacion_forms import FormularioRegistro, FormularioInicioSesion

blueprint_autenticacion = Blueprint('autenticacion', __name__, url_prefix='/autenticacion')


@blueprint_autenticacion.route('/registro', methods=['GET', 'POST'])
def registro():
    """Ruta para la creación de una cuenta individual de usuario."""
    if current_user.is_authenticated:
        return redirect(url_for('autenticacion.mi_perfil'))

    formulario = FormularioRegistro()
    if formulario.validate_on_submit():
        try:
            # Obtener el rol USUARIO por defecto desde la base de datos (CERO HARDCODING)
            rol_usuario = RolUsuario.query.filter_by(nombre_rol='USUARIO').first()
            if not rol_usuario:
                flash('Error de configuración en el sistema: rol de usuario no encontrado.', 'danger')
                return render_template('autenticacion/registro.html', formulario=formulario)

            # Instanciar el nuevo usuario con billetera dual en 0
            nuevo_usuario = Usuario(
                id_rol=rol_usuario.id_rol,
                nombre_completo=formulario.nombre_completo.data.strip(),
                correo_electronico=formulario.correo_electronico.data.strip().lower(),
                telefono=formulario.telefono.data.strip() if formulario.telefono.data else None,
                ciudad_ubicacion=formulario.ciudad_ubicacion.data.strip(),
                saldo_puntos_disponibles=0,
                saldo_puntos_retenidos=0,
                activo=True
            )
            # Hashear la contraseña con algoritmo criptográfico seguro (scrypt)
            nuevo_usuario.establecer_contrasena(formulario.contrasena.data)

            db.session.add(nuevo_usuario)
            db.session.commit()

            flash('¡Tu cuenta ha sido creada exitosamente! Ya puedes iniciar sesión y comenzar a intercambiar.', 'success')
            return redirect(url_for('autenticacion.iniciar_sesion'))

        except Exception as error:
            db.session.rollback()
            flash(f'Ocurrió un error al registrar la cuenta: {str(error)}', 'danger')

    return render_template('autenticacion/registro.html', formulario=formulario)


@blueprint_autenticacion.route('/iniciar-sesion', methods=['GET', 'POST'])
def iniciar_sesion():
    """Ruta para autenticación de credenciales de usuario."""
    if current_user.is_authenticated:
        return redirect(url_for('autenticacion.mi_perfil'))

    formulario = FormularioInicioSesion()
    if formulario.validate_on_submit():
        correo_ingresado = formulario.correo_electronico.data.strip().lower()
        usuario = Usuario.query.filter_by(correo_electronico=correo_ingresado).first()

        if usuario and usuario.verificar_contrasena(formulario.contrasena.data):
            # Si el usuario tenía una suspensión temporal y ya expiró, reactivarlo automáticamente
            if usuario.reactivar_si_expirado():
                db.session.commit()

            # Verificar si la cuenta está bajo suspensión
            if usuario.esta_suspendido:
                if usuario.fecha_fin_suspension and datetime.utcnow() < usuario.fecha_fin_suspension:
                    fecha_str = usuario.fecha_fin_suspension.strftime('%d/%m/%Y a las %H:%M')
                    motivo = f" Motivo: {usuario.motivo_suspension}" if usuario.motivo_suspension else ""
                    flash(f'Tu cuenta se encuentra suspendida temporalmente hasta el {fecha_str}.{motivo}', 'danger')
                else:
                    motivo = f" Motivo: {usuario.motivo_suspension}" if usuario.motivo_suspension else ""
                    flash(f'Tu cuenta ha sido suspendida permanentemente por la administración.{motivo}', 'danger')
                return render_template('autenticacion/iniciar_sesion.html', formulario=formulario)

            login_user(usuario, remember=formulario.recordarme.data)
            flash(f'¡Bienvenido de nuevo, {usuario.nombre_completo}!', 'success')

            # Redirección segura verificando que no sea enlace externo
            proxima_pagina = request.args.get('next')
            if not proxima_pagina or urlsplit(proxima_pagina).netloc != '':
                proxima_pagina = url_for('autenticacion.mi_perfil')

            return redirect(proxima_pagina)
        else:
            flash('Credenciales incorrectas. Verifica tu correo electrónico y contraseña.', 'danger')

    return render_template('autenticacion/iniciar_sesion.html', formulario=formulario)


@blueprint_autenticacion.route('/cerrar-sesion')
@login_required
def cerrar_sesion():
    """Finaliza de forma segura la sesión del usuario actual."""
    logout_user()
    flash('Has cerrado tu sesión de forma segura. ¡Te esperamos pronto!', 'info')
    return redirect(url_for('autenticacion.iniciar_sesion'))


@blueprint_autenticacion.route('/mi-perfil')
@login_required
def mi_perfil():
    """Panel de información personal del usuario y desglose de su billetera."""
    # Estadísticas de publicaciones del usuario
    total_publicadas = PrendaAccesorio.query.filter_by(
        id_usuario_propietario=current_user.id_usuario,
        estado_publicacion='PUBLICADA'
    ).count()

    total_pendientes = PrendaAccesorio.query.filter_by(
        id_usuario_propietario=current_user.id_usuario,
        estado_publicacion='PENDIENTE_APROBACION'
    ).count()

    total_intercambiadas = PrendaAccesorio.query.filter_by(
        id_usuario_propietario=current_user.id_usuario,
        estado_publicacion='INTERCAMBIADA'
    ).count()

    return render_template(
        'autenticacion/perfil.html',
        usuario=current_user,
        total_publicadas=total_publicadas,
        total_pendientes=total_pendientes,
        total_intercambiadas=total_intercambiadas
    )
