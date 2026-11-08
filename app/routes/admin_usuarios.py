"""
Controlador de Administración de Usuarios, Roles y Prendas (Blueprint de Administración de Usuarios)
Permite al Administrador gestionar usuarios, asignar roles, restablecer contraseñas,
auditar y ajustar saldos con trazabilidad contable, y supervisar prendas.
Coexiste fluidamente con el auto-registro público en /registro.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

from app import db
from app.models.usuario import Usuario
from app.models.rol_usuario import RolUsuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos

blueprint_admin_usuarios = Blueprint('admin_usuarios', __name__, url_prefix='/admin/usuarios')


@blueprint_admin_usuarios.before_request
@login_required
def verificar_permisos_administrador():
    """Garantiza acceso exclusivo para administradores."""
    if not current_user.es_administrador:
        abort(403)


# ==============================================================================
# VISTA PRINCIPAL: LISTADO Y BÚSQUEDA DE USUARIOS
# ==============================================================================

@blueprint_admin_usuarios.route('/')
def listar_usuarios():
    """Listado dinámico de usuarios con búsqueda y filtros por rol y estado."""
    termino_busqueda = request.args.get('q', '').strip()
    filtro_rol = request.args.get('rol', '').strip()
    filtro_estado = request.args.get('estado', '').strip()

    consulta = Usuario.query

    if termino_busqueda:
        patron = f"%{termino_busqueda}%"
        consulta = consulta.filter(
            db.or_(
                Usuario.nombre_completo.ilike(patron),
                Usuario.correo_electronico.ilike(patron),
                Usuario.ciudad_ubicacion.ilike(patron)
            )
        )

    if filtro_rol and filtro_rol.isdigit():
        consulta = consulta.filter(Usuario.id_rol == int(filtro_rol))

    if filtro_estado in ('1', '0'):
        consulta = consulta.filter(Usuario.activo == (filtro_estado == '1'))

    usuarios = consulta.order_by(Usuario.fecha_registro.desc()).all()
    roles = RolUsuario.query.filter_by(activo=True).all()

    return render_template(
        'admin/usuarios.html',
        usuarios=usuarios,
        roles=roles,
        termino_busqueda=termino_busqueda,
        filtro_rol=filtro_rol,
        filtro_estado=filtro_estado
    )


# ==============================================================================
# CREACIÓN DE USUARIO ADMINISTRATIVA
# ==============================================================================

@blueprint_admin_usuarios.route('/crear', methods=['POST'])
def crear_usuario():
    """Permite al administrador crear una cuenta y asignarle un rol específico."""
    try:
        nombre = request.form.get('nombre_completo', '').strip()
        correo = request.form.get('correo_electronico', '').strip().lower()
        telefono = request.form.get('telefono', '').strip()
        ciudad = request.form.get('ciudad_ubicacion', '').strip()
        direccion = request.form.get('direccion_predeterminada', '').strip()
        biografia = request.form.get('biografia_vitrina', '').strip()
        reputacion = int(request.form.get('reputacion_trueques', 100))
        id_rol = int(request.form.get('id_rol', 0))
        contrasena = request.form.get('contrasena', '').strip()
        saldo_inicial = int(request.form.get('saldo_puntos_disponibles', 0))
        activo = 'activo' in request.form

        if not nombre or not correo or not contrasena or not ciudad:
            raise ValueError("Nombre, correo, ciudad y contraseña inicial son obligatorios.")

        if len(contrasena) < 6:
            raise ValueError("La contraseña debe contener al menos 6 caracteres.")

        rol = db.session.get(RolUsuario, id_rol)
        if not rol:
            raise ValueError("El rol seleccionado no es válido.")

        existente = Usuario.query.filter_by(correo_electronico=correo).first()
        if existente:
            raise ValueError(f"Ya existe un usuario registrado con el correo '{correo}'.")

        nuevo_usuario = Usuario(
            nombre_completo=nombre,
            correo_electronico=correo,
            telefono=telefono or '+57 300 000 0000',
            ciudad_ubicacion=ciudad,
            direccion_predeterminada=direccion or None,
            biografia_vitrina=biografia or None,
            reputacion_trueques=max(0, reputacion),
            id_rol=id_rol,
            saldo_puntos_disponibles=max(0, saldo_inicial),
            saldo_puntos_retenidos=0,
            activo=activo,
            fecha_registro=datetime.utcnow()
        )
        nuevo_usuario.establecer_contrasena(contrasena)

        db.session.add(nuevo_usuario)
        db.session.flush()

        # Si se asignó saldo inicial, registrar movimiento contable
        if nuevo_usuario.saldo_puntos_disponibles > 0:
            movimiento = HistorialMovimientosPuntos(
                id_usuario=nuevo_usuario.id_usuario,
                id_prenda_referencia=None,
                tipo_movimiento='CREDITO_PUBLICACION',
                cantidad_puntos=nuevo_usuario.saldo_puntos_disponibles,
                saldo_anterior=0,
                saldo_posterior=nuevo_usuario.saldo_puntos_disponibles,
                descripcion_auditoria=f"Bono inicial administrativo de bienvenida asignado por {current_user.nombre_completo[:40]}"
            )
            db.session.add(movimiento)

        db.session.commit()
        flash(f"Usuario '{nuevo_usuario.nombre_completo}' registrado exitosamente con rol {rol.nombre_rol}.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al crear usuario: {str(err)}", "danger")

    return redirect(url_for('admin_usuarios.listar_usuarios'))


# ==============================================================================
# EDICIÓN DE USUARIO
# ==============================================================================

@blueprint_admin_usuarios.route('/editar/<int:id_usuario>', methods=['POST'])
def editar_usuario(id_usuario: int):
    """Actualiza datos personales, logísticos y rol del usuario."""
    usuario = Usuario.query.get_or_404(id_usuario)
    try:
        nombre = request.form.get('nombre_completo', '').strip()
        correo = request.form.get('correo_electronico', '').strip().lower()
        telefono = request.form.get('telefono', '').strip()
        ciudad = request.form.get('ciudad_ubicacion', '').strip()
        direccion = request.form.get('direccion_predeterminada', '').strip()
        biografia = request.form.get('biografia_vitrina', '').strip()
        reputacion = int(request.form.get('reputacion_trueques', usuario.reputacion_trueques or 100))
        id_rol = int(request.form.get('id_rol', usuario.id_rol))
        activo = 'activo' in request.form

        if not nombre or not correo or not ciudad:
            raise ValueError("Nombre, correo y ciudad son obligatorios.")

        # Verificar unicidad de correo
        duplicado = Usuario.query.filter(
            Usuario.correo_electronico == correo,
            Usuario.id_usuario != id_usuario
        ).first()
        if duplicado:
            raise ValueError(f"El correo '{correo}' ya se encuentra en uso por otra cuenta.")

        rol = db.session.get(RolUsuario, id_rol)
        if not rol:
            raise ValueError("Rol no válido.")

        # Evitar que el administrador se desactive a sí mismo
        if usuario.id_usuario == current_user.id_usuario and not activo:
            raise ValueError("No puedes desactivar tu propia cuenta de administrador en sesión.")

        usuario.nombre_completo = nombre
        usuario.correo_electronico = correo
        usuario.telefono = telefono
        usuario.ciudad_ubicacion = ciudad
        usuario.direccion_predeterminada = direccion or None
        usuario.biografia_vitrina = biografia or None
        usuario.reputacion_trueques = max(0, reputacion)
        usuario.id_rol = id_rol
        usuario.activo = activo

        db.session.commit()
        flash(f"Usuario '{usuario.nombre_completo}' actualizado correctamente en SQL Server.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al actualizar usuario: {str(err)}", "danger")

    return redirect(url_for('admin_usuarios.listar_usuarios'))


# ==============================================================================
# GESTIÓN DE SUSPENSIONES (TEMPORALES POR TIEMPO O PERMANENTES)
# ==============================================================================

@blueprint_admin_usuarios.route('/suspender/<int:id_usuario>', methods=['POST'])
def suspender_usuario(id_usuario: int):
    """
    Aplica una suspensión temporal (por horas o días) o permanente a un usuario.
    El Administrador define el tipo, la duración exacta y el motivo auditable.
    """
    usuario = Usuario.query.get_or_404(id_usuario)
    try:
        if usuario.id_usuario == current_user.id_usuario:
            raise ValueError("No puedes suspender tu propia cuenta de administrador en sesión.")

        tipo_suspension = request.form.get('tipo_suspension', 'TEMPORAL').strip().upper()
        motivo = request.form.get('motivo_suspension', '').strip()

        if not motivo:
            raise ValueError("Debes ingresar un motivo claro para la suspensión de la cuenta.")

        if tipo_suspension == 'PERMANENTE':
            usuario.activo = False
            usuario.fecha_fin_suspension = None
            usuario.motivo_suspension = f"[PERMANENTE] {motivo} | Sancionado por: {current_user.nombre_completo[:30]}"
            mensaje = f"La cuenta de '{usuario.nombre_completo}' ha sido suspendida de forma PERMANENTE."
        elif tipo_suspension == 'TEMPORAL':
            duracion_valor = int(request.form.get('duracion_valor', 1))
            duracion_unidad = request.form.get('duracion_unidad', 'DIAS').strip().upper()

            if duracion_valor <= 0:
                raise ValueError("La duración de la suspensión debe ser mayor a 0.")

            ahora = datetime.utcnow()
            if duracion_unidad == 'HORAS':
                fecha_fin = ahora + timedelta(hours=duracion_valor)
                texto_duracion = f"{duracion_valor} hora(s)"
            elif duracion_unidad == 'DIAS':
                fecha_fin = ahora + timedelta(days=duracion_valor)
                texto_duracion = f"{duracion_valor} día(s)"
            else:
                raise ValueError("Unidad de tiempo no válida (debe ser HORAS o DIAS).")

            usuario.activo = True
            usuario.fecha_fin_suspension = fecha_fin
            usuario.motivo_suspension = f"[TEMPORAL: {texto_duracion} hasta {fecha_fin.strftime('%d/%m/%Y %H:%M')}] {motivo} | Sancionado por: {current_user.nombre_completo[:30]}"
            mensaje = f"La cuenta de '{usuario.nombre_completo}' ha sido suspendida por {texto_duracion} (hasta el {fecha_fin.strftime('%d/%m/%Y %H:%M')})."
        else:
            raise ValueError("Tipo de suspensión no válido.")

        db.session.commit()
        flash(mensaje, "warning")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al suspender usuario: {str(err)}", "danger")

    return redirect(url_for('admin_usuarios.listar_usuarios'))


@blueprint_admin_usuarios.route('/reactivar/<int:id_usuario>', methods=['POST'])
def reactivar_usuario(id_usuario: int):
    """Levanta cualquier suspensión activa y restablece el acceso total de la cuenta."""
    usuario = Usuario.query.get_or_404(id_usuario)
    try:
        usuario.activo = True
        usuario.fecha_fin_suspension = None
        usuario.motivo_suspension = None

        db.session.commit()
        flash(f"La cuenta de '{usuario.nombre_completo}' ha sido reactivada exitosamente. Acceso restaurado.", "success")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al reactivar usuario: {str(err)}", "danger")

    return redirect(url_for('admin_usuarios.listar_usuarios'))


# ==============================================================================
# RESTABLECER CONTRASEÑA ADMINISTRATIVA
# ==============================================================================

@blueprint_admin_usuarios.route('/restablecer-clave/<int:id_usuario>', methods=['POST'])
def restablecer_contrasena(id_usuario: int):
    """Genera una nueva contraseña para el usuario."""
    usuario = Usuario.query.get_or_404(id_usuario)
    try:
        nueva_clave = request.form.get('nueva_contrasena', '').strip()
        if len(nueva_clave) < 6:
            raise ValueError("La nueva contraseña debe tener al menos 6 caracteres.")

        usuario.establecer_contrasena(nueva_clave)
        db.session.commit()
        flash(f"Contraseña de '{usuario.nombre_completo}' restablecida con éxito.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al restablecer contraseña: {str(err)}", "danger")

    return redirect(url_for('admin_usuarios.listar_usuarios'))


# ==============================================================================
# AJUSTE Y AUDITORÍA DE SALDO DE PUNTOS
# ==============================================================================

@blueprint_admin_usuarios.route('/ajustar-saldo/<int:id_usuario>', methods=['POST'])
def ajustar_saldo(id_usuario: int):
    """
    Ajusta manualmente los puntos del usuario dejando registro contable inmutable
    en Historial_Movimientos_Puntos cumpliendo estrictamente con la restricción CK_Historial_Tipo.
    """
    usuario = Usuario.query.get_or_404(id_usuario)
    try:
        tipo_saldo = request.form.get('tipo_saldo', 'disponibles').strip()
        operacion = request.form.get('operacion', 'sumar').strip()
        cantidad = int(request.form.get('cantidad_puntos', 0))
        motivo = request.form.get('motivo_ajuste', '').strip()

        if cantidad <= 0:
            raise ValueError("La cantidad de puntos debe ser un número entero mayor a cero.")
        if not motivo:
            raise ValueError("Debes ingresar un motivo detallado para el ajuste de saldo (auditoría obligatoria).")

        saldo_anterior = usuario.saldo_puntos_disponibles if tipo_saldo == 'disponibles' else usuario.saldo_puntos_retenidos

        if operacion == 'sumar':
            nuevo_saldo = saldo_anterior + cantidad
            tipo_movimiento = 'CREDITO_PUBLICACION'
            glosa = f"Ajuste Administrativo Crédito (+{cantidad} pts) a saldo {tipo_saldo}. Motivo: {motivo} | Por: {current_user.nombre_completo[:30]}"
        elif operacion == 'restar':
            if cantidad > saldo_anterior:
                raise ValueError(f"No es posible restar {cantidad} puntos. El saldo actual es de {saldo_anterior} pts.")
            nuevo_saldo = saldo_anterior - cantidad
            tipo_movimiento = 'DEBITO_ADQUISICION'
            glosa = f"Ajuste Administrativo Débito (-{cantidad} pts) a saldo {tipo_saldo}. Motivo: {motivo} | Por: {current_user.nombre_completo[:30]}"
        else:
            raise ValueError("Operación no válida.")

        if tipo_saldo == 'disponibles':
            usuario.saldo_puntos_disponibles = nuevo_saldo
        else:
            usuario.saldo_puntos_retenidos = nuevo_saldo

        # Inserción contable con transacción ACID
        movimiento = HistorialMovimientosPuntos(
            id_usuario=usuario.id_usuario,
            id_prenda_referencia=None,
            tipo_movimiento=tipo_movimiento,
            cantidad_puntos=cantidad,
            saldo_anterior=saldo_anterior,
            saldo_posterior=nuevo_saldo,
            descripcion_auditoria=glosa[:295],
            fecha_movimiento=datetime.utcnow()
        )
        db.session.add(movimiento)
        db.session.commit()

        flash(f"Saldo de '{usuario.nombre_completo}' ajustado a {nuevo_saldo} pts. Asiento contable registrado con éxito.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al ajustar saldo: {str(err)}", "danger")

    return redirect(url_for('admin_usuarios.listar_usuarios'))


# ==============================================================================
# ENDPOINT JSON PARA MODALES DINÁMICOS
# ==============================================================================

@blueprint_admin_usuarios.route('/detalle-json/<int:id_usuario>', methods=['GET'])
def detalle_usuario_json(id_usuario: int):
    """Devuelve datos del usuario para poblar modales de edición sin recarga."""
    usuario = Usuario.query.get_or_404(id_usuario)
    return jsonify({
        'id_usuario': usuario.id_usuario,
        'nombre_completo': usuario.nombre_completo,
        'correo_electronico': usuario.correo_electronico,
        'telefono': usuario.telefono,
        'ciudad_ubicacion': usuario.ciudad_ubicacion,
        'id_rol': usuario.id_rol,
        'nombre_rol': usuario.rol.nombre_rol if usuario.rol else 'USUARIO',
        'saldo_puntos_disponibles': usuario.saldo_puntos_disponibles,
        'saldo_puntos_retenidos': usuario.saldo_puntos_retenidos,
        'activo': usuario.activo,
        'esta_suspendido': usuario.esta_suspendido,
        'estado_suspension': usuario.estado_suspension_legible,
        'motivo_suspension': usuario.motivo_suspension or '',
        'fecha_fin_suspension': usuario.fecha_fin_suspension.strftime('%Y-%m-%d %H:%M') if usuario.fecha_fin_suspension else '',
        'fecha_registro': usuario.fecha_registro.strftime('%Y-%m-%d %H:%M') if usuario.fecha_registro else ''
    })
