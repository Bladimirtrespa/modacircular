"""
Controlador de Administración de Tablas Paramétricas (Blueprint de Administración)
Permite al Administrador gestionar dinámicamente las reglas de negocio de SQL Server:
CRUD completo de Categorías, Catálogo Maestro de 55 Materiales, Estados de Aspecto y Niveles de Utilidad.
Cero hardcoding: toda modificación se persiste directamente en DB_IntercambioRopa.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.categoria_prenda import CategoriaPrenda
from app.models.material import Material
from app.models.estado_aspecto import EstadoAspecto
from app.models.nivel_utilidad import NivelUtilidad

blueprint_admin = Blueprint('admin', __name__, url_prefix='/admin')


@blueprint_admin.before_request
@login_required
def verificar_permisos_administrador():
    """Garantiza acceso exclusivo para el rol ADMINISTRADOR."""
    if not current_user.es_administrador:
        abort(403)


# ==============================================================================
# VISTA PRINCIPAL: PANEL DE TABLAS PARAMÉTRICAS
# ==============================================================================

@blueprint_admin.route('/tablas')
def tablas():
    """Panel de control visual de las 4 tablas maestras de valoración en SQL Server."""
    filtro_familia = request.args.get('familia', '').strip()
    filtro_uso = request.args.get('uso', '').strip()

    consulta_materiales = Material.query
    if filtro_familia:
        consulta_materiales = consulta_materiales.filter(Material.familia_material == filtro_familia)
    if filtro_uso:
        consulta_materiales = consulta_materiales.filter(Material.uso_principal == filtro_uso)

    materiales = consulta_materiales.order_by(
        Material.familia_material.asc(),
        Material.nombre_material.asc()
    ).all()

    categorias = CategoriaPrenda.query.order_by(
        CategoriaPrenda.tipo_articulo.desc(),
        CategoriaPrenda.nombre_categoria.asc()
    ).all()

    estados_aspecto = EstadoAspecto.query.order_by(
        EstadoAspecto.factor_conservacion.desc()
    ).all()

    niveles_utilidad = NivelUtilidad.query.order_by(
        NivelUtilidad.bono_puntos.asc()
    ).all()

    # Familias únicas para el filtro dinámico
    familias_disponibles = sorted(list({m.familia_material for m in Material.query.all()}))

    return render_template(
        'admin/tablas.html',
        categorias=categorias,
        materiales=materiales,
        estados_aspecto=estados_aspecto,
        niveles_utilidad=niveles_utilidad,
        familias_disponibles=familias_disponibles,
        filtro_familia=filtro_familia,
        filtro_uso=filtro_uso
    )


# ==============================================================================
# CRUD: CATEGORÍAS DE PRENDA Y ACCESORIO
# ==============================================================================

@blueprint_admin.route('/categorias/crear', methods=['POST'])
def crear_categoria():
    """Crea una nueva categoría taxonómica en SQL Server."""
    try:
        nombre = request.form.get('nombre_categoria', '').strip()
        tipo = request.form.get('tipo_articulo', '').strip().upper()
        puntaje_base = int(request.form.get('puntaje_base', 0))
        descripcion = request.form.get('descripcion', '').strip()

        if not nombre:
            raise ValueError("El nombre de la categoría es obligatorio.")
        if tipo not in ('PRENDA', 'ACCESORIO'):
            raise ValueError("El tipo de artículo debe ser 'PRENDA' o 'ACCESORIO'.")
        if puntaje_base <= 0:
            raise ValueError("El puntaje base debe ser mayor a 0.")

        existente = CategoriaPrenda.query.filter_by(nombre_categoria=nombre).first()
        if existente:
            raise ValueError(f"Ya existe una categoría registrada con el nombre '{nombre}'.")

        nueva_cat = CategoriaPrenda(
            nombre_categoria=nombre,
            tipo_articulo=tipo,
            puntaje_base=puntaje_base,
            descripcion=descripcion or f"Categoría de {tipo.lower()} para prendas e indumentaria.",
            activo='activo' in request.form
        )
        db.session.add(nueva_cat)
        db.session.commit()
        flash(f"Categoría '{nueva_cat.nombre_categoria}' creada exitosamente en SQL Server.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al registrar la categoría: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-categorias'))


@blueprint_admin.route('/categorias/editar/<int:id_categoria>', methods=['POST'])
def editar_categoria(id_categoria: int):
    """Actualiza los atributos de una categoría existente."""
    categoria = CategoriaPrenda.query.get_or_404(id_categoria)
    try:
        nombre = request.form.get('nombre_categoria', '').strip()
        tipo = request.form.get('tipo_articulo', '').strip().upper()
        puntaje_base = int(request.form.get('puntaje_base', 0))
        descripcion = request.form.get('descripcion', '').strip()

        if not nombre:
            raise ValueError("El nombre de la categoría es obligatorio.")
        if tipo not in ('PRENDA', 'ACCESORIO'):
            raise ValueError("El tipo de artículo debe ser 'PRENDA' o 'ACCESORIO'.")
        if puntaje_base <= 0:
            raise ValueError("El puntaje base debe ser mayor a 0.")

        # Verificar duplicidad de nombre excluyendo el actual
        existente = CategoriaPrenda.query.filter(
            CategoriaPrenda.nombre_categoria == nombre,
            CategoriaPrenda.id_categoria != id_categoria
        ).first()
        if existente:
            raise ValueError(f"Otra categoría ya utiliza el nombre '{nombre}'.")

        categoria.nombre_categoria = nombre
        categoria.tipo_articulo = tipo
        categoria.puntaje_base = puntaje_base
        categoria.descripcion = descripcion
        categoria.activo = 'activo' in request.form

        db.session.commit()
        flash(f"Categoría '{categoria.nombre_categoria}' actualizada exitosamente.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al actualizar la categoría: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-categorias'))


@blueprint_admin.route('/categorias/alternar/<int:id_categoria>', methods=['POST'])
def alternar_categoria(id_categoria: int):
    """Activa o desactiva lógicamente una categoría sin romper integridad referencial."""
    categoria = CategoriaPrenda.query.get_or_404(id_categoria)
    try:
        categoria.activo = not categoria.activo
        db.session.commit()
        estado = "activada" if categoria.activo else "desactivada"
        flash(f"Categoría '{categoria.nombre_categoria}' {estado} con éxito.", "info")
    except Exception as err:
        db.session.rollback()
        flash(f"No fue posible alternar el estado de la categoría: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-categorias'))


# ==============================================================================
# CRUD: CATÁLOGO DE MATERIALES (12 ATRIBUTOS COMPLETOS)
# ==============================================================================

@blueprint_admin.route('/materiales/crear', methods=['POST'])
def crear_material():
    """Registra un nuevo material en el catálogo maestro de SQL Server."""
    try:
        codigo = request.form.get('codigo_material', '').strip().upper()
        nombre = request.form.get('nombre_material', '').strip()
        familia = request.form.get('familia_material', '').strip()
        uso = request.form.get('uso_principal', '').strip().upper()
        factor = float(request.form.get('factor_multiplicador', 1.0))
        bono = int(request.form.get('bono_puntos_material', 0))
        sostenibilidad = request.form.get('nivel_sostenibilidad', '').strip()
        descripcion = request.form.get('descripcion_tecnica', '').strip()

        es_joya = 'es_metal_o_joya_preciosa' in request.form
        req_aprobacion = 'requiere_aprobacion_especial' in request.form or es_joya
        activo = 'activo' in request.form

        if not codigo or not nombre or not familia:
            raise ValueError("El código SKU, el nombre y la familia del material son obligatorios.")
        if uso not in ('PRENDA', 'ACCESORIO', 'AMBOS'):
            raise ValueError("El uso principal debe ser 'PRENDA', 'ACCESORIO' o 'AMBOS'.")
        if factor <= 0:
            raise ValueError("El factor multiplicador debe ser mayor a 0.")
        if bono < 0:
            raise ValueError("El bono de puntos no puede ser negativo.")
        if len(sostenibilidad) > 30:
            raise ValueError("El nivel de sostenibilidad no debe exceder los 30 caracteres (límite SQL Server).")

        # Verificar unicidad
        if Material.query.filter_by(codigo_material=codigo).first():
            raise ValueError(f"Ya existe un material registrado con el código SKU '{codigo}'.")
        if Material.query.filter_by(nombre_material=nombre).first():
            raise ValueError(f"Ya existe un material con el nombre '{nombre}'.")

        nuevo_mat = Material(
            codigo_material=codigo,
            nombre_material=nombre,
            familia_material=familia,
            uso_principal=uso,
            factor_multiplicador=factor,
            bono_puntos_material=bono,
            nivel_sostenibilidad=sostenibilidad or 'Estándar',
            es_metal_o_joya_preciosa=es_joya,
            requiere_aprobacion_especial=req_aprobacion,
            descripcion_tecnica=descripcion or f"Material {nombre} de la familia {familia}.",
            activo=activo
        )
        db.session.add(nuevo_mat)
        db.session.commit()
        flash(f"Material '{nuevo_mat.nombre_material}' ({nuevo_mat.codigo_material}) creado con éxito en SQL Server.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except IntegrityError as err_int:
        db.session.rollback()
        flash(f"Conflicto de unicidad o restricción en SQL Server: {str(err_int.orig)}", "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al registrar el material: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-materiales'))


@blueprint_admin.route('/materiales/editar/<int:id_material>', methods=['POST'])
def editar_material(id_material: int):
    """Actualiza todos los atributos de un material en SQL Server."""
    material = Material.query.get_or_404(id_material)
    try:
        codigo = request.form.get('codigo_material', '').strip().upper()
        nombre = request.form.get('nombre_material', '').strip()
        familia = request.form.get('familia_material', '').strip()
        uso = request.form.get('uso_principal', '').strip().upper()
        factor = float(request.form.get('factor_multiplicador', 1.0))
        bono = int(request.form.get('bono_puntos_material', 0))
        sostenibilidad = request.form.get('nivel_sostenibilidad', '').strip()
        descripcion = request.form.get('descripcion_tecnica', '').strip()

        es_joya = 'es_metal_o_joya_preciosa' in request.form
        req_aprobacion = 'requiere_aprobacion_especial' in request.form or es_joya
        activo = 'activo' in request.form

        if not codigo or not nombre or not familia:
            raise ValueError("El código SKU, el nombre y la familia son campos requeridos.")
        if uso not in ('PRENDA', 'ACCESORIO', 'AMBOS'):
            raise ValueError("Uso principal no válido.")
        if factor <= 0:
            raise ValueError("El factor multiplicador debe ser mayor a 0.")
        if bono < 0:
            raise ValueError("El bono de puntos no puede ser negativo.")
        if len(sostenibilidad) > 30:
            raise ValueError("El nivel de sostenibilidad no debe exceder 30 caracteres.")

        # Verificar duplicidad de SKU o Nombre
        duplicado_sku = Material.query.filter(
            Material.codigo_material == codigo,
            Material.id_material != id_material
        ).first()
        if duplicado_sku:
            raise ValueError(f"El código SKU '{codigo}' ya está asignado a otro material.")

        duplicado_nom = Material.query.filter(
            Material.nombre_material == nombre,
            Material.id_material != id_material
        ).first()
        if duplicado_nom:
            raise ValueError(f"El nombre '{nombre}' ya está en uso.")

        material.codigo_material = codigo
        material.nombre_material = nombre
        material.familia_material = familia
        material.uso_principal = uso
        material.factor_multiplicador = factor
        material.bono_puntos_material = bono
        material.nivel_sostenibilidad = sostenibilidad
        material.es_metal_o_joya_preciosa = es_joya
        material.requiere_aprobacion_especial = req_aprobacion
        material.descripcion_tecnica = descripcion
        material.activo = activo

        db.session.commit()
        flash(f"Material '{material.nombre_material}' ({material.codigo_material}) actualizado con éxito.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al actualizar el material: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-materiales'))


@blueprint_admin.route('/materiales/alternar/<int:id_material>', methods=['POST'])
def alternar_material(id_material: int):
    """Activa o desactiva un material para el catálogo."""
    material = Material.query.get_or_404(id_material)
    try:
        material.activo = not material.activo
        db.session.commit()
        estado = "activado" if material.activo else "desactivado"
        flash(f"Material '{material.nombre_material}' {estado} correctamente.", "info")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al alternar el estado del material: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-materiales'))


@blueprint_admin.route('/materiales/detalle-json/<int:id_material>', methods=['GET'])
def detalle_material_json(id_material: int):
    """Retorna los datos de un material en JSON para poblar modales de edición dinámica."""
    material = Material.query.get_or_404(id_material)
    return jsonify(material.a_diccionario())


# ==============================================================================
# CRUD: NIVELES DE UTILIDAD
# ==============================================================================

@blueprint_admin.route('/niveles-utilidad/crear', methods=['POST'])
def crear_nivel_utilidad():
    """Registra un nuevo nivel de utilidad en SQL Server."""
    try:
        nombre = request.form.get('nombre_utilidad', '').strip()
        bono = int(request.form.get('bono_puntos', 0))

        if not nombre:
            raise ValueError("El nombre del nivel de utilidad es obligatorio.")
        if bono < 0:
            raise ValueError("El bono de puntos no puede ser negativo.")

        existente = NivelUtilidad.query.filter_by(nombre_utilidad=nombre).first()
        if existente:
            raise ValueError(f"Ya existe un nivel de utilidad con el nombre '{nombre}'.")

        nuevo_nivel = NivelUtilidad(
            nombre_utilidad=nombre,
            bono_puntos=bono,
            activo='activo' in request.form
        )
        db.session.add(nuevo_nivel)
        db.session.commit()
        flash(f"Nivel de utilidad '{nuevo_nivel.nombre_utilidad}' registrado exitosamente.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al crear el nivel de utilidad: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-utilidad'))


@blueprint_admin.route('/niveles-utilidad/editar/<int:id_nivel>', methods=['POST'])
def editar_nivel_utilidad(id_nivel: int):
    """Actualiza un nivel de utilidad existente."""
    nivel = NivelUtilidad.query.get_or_404(id_nivel)
    try:
        nombre = request.form.get('nombre_utilidad', '').strip()
        bono = int(request.form.get('bono_puntos', 0))

        if not nombre:
            raise ValueError("El nombre no puede estar vacío.")
        if bono < 0:
            raise ValueError("El bono de puntos no puede ser negativo.")

        duplicado = NivelUtilidad.query.filter(
            NivelUtilidad.nombre_utilidad == nombre,
            NivelUtilidad.id_nivel_utilidad != id_nivel
        ).first()
        if duplicado:
            raise ValueError(f"Ya existe otro nivel con el nombre '{nombre}'.")

        nivel.nombre_utilidad = nombre
        nivel.bono_puntos = bono
        nivel.activo = 'activo' in request.form

        db.session.commit()
        flash(f"Nivel de utilidad '{nivel.nombre_utilidad}' actualizado correctamente.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al actualizar el nivel de utilidad: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-utilidad'))


@blueprint_admin.route('/niveles-utilidad/alternar/<int:id_nivel>', methods=['POST'])
def alternar_nivel_utilidad(id_nivel: int):
    """Alterna el estado activo de un nivel de utilidad."""
    nivel = NivelUtilidad.query.get_or_404(id_nivel)
    try:
        nivel.activo = not nivel.activo
        db.session.commit()
        estado = "activado" if nivel.activo else "desactivado"
        flash(f"Nivel de utilidad '{nivel.nombre_utilidad}' {estado}.", "info")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al alternar estado: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-utilidad'))


# ==============================================================================
# CRUD: ESTADOS DE ASPECTO
# ==============================================================================

@blueprint_admin.route('/estados-aspecto/crear', methods=['POST'])
def crear_estado_aspecto():
    """Registra un nuevo estado físico de conservación en SQL Server."""
    try:
        nombre = request.form.get('nombre_estado', '').strip()
        factor = float(request.form.get('factor_conservacion', 1.0))
        descripcion = request.form.get('descripcion_criterio', '').strip()

        if not nombre:
            raise ValueError("El nombre del estado de aspecto es obligatorio.")
        if factor <= 0 or factor > 2.0:
            raise ValueError("El factor de conservación debe ser mayor a 0 y menor o igual a 2.0.")

        existente = EstadoAspecto.query.filter_by(nombre_estado=nombre).first()
        if existente:
            raise ValueError(f"Ya existe un estado de aspecto con el nombre '{nombre}'.")

        nuevo_estado = EstadoAspecto(
            nombre_estado=nombre,
            factor_conservacion=factor,
            descripcion_criterio=descripcion or f"Criterio físico para prendas en estado {nombre}.",
            activo='activo' in request.form
        )
        db.session.add(nuevo_estado)
        db.session.commit()
        flash(f"Estado de aspecto '{nuevo_estado.nombre_estado}' creado con éxito.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al registrar el estado de aspecto: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-estados'))


@blueprint_admin.route('/estados-aspecto/editar/<int:id_estado>', methods=['POST'])
def editar_estado_aspecto(id_estado: int):
    """Actualiza el factor de conservación y descripción de un estado de aspecto."""
    estado = EstadoAspecto.query.get_or_404(id_estado)
    try:
        nombre = request.form.get('nombre_estado', '').strip()
        factor = float(request.form.get('factor_conservacion', 1.0))
        descripcion = request.form.get('descripcion_criterio', '').strip()

        if not nombre:
            raise ValueError("El nombre es requerido.")
        if factor <= 0 or factor > 2.0:
            raise ValueError("El factor de conservación debe ser mayor a 0 y hasta 2.0.")

        duplicado = EstadoAspecto.query.filter(
            EstadoAspecto.nombre_estado == nombre,
            EstadoAspecto.id_estado_aspecto != id_estado
        ).first()
        if duplicado:
            raise ValueError(f"Ya existe otro estado con el nombre '{nombre}'.")

        estado.nombre_estado = nombre
        estado.factor_conservacion = factor
        estado.descripcion_criterio = descripcion
        estado.activo = 'activo' in request.form

        db.session.commit()
        flash(f"Estado de aspecto '{estado.nombre_estado}' actualizado correctamente.", "success")
    except ValueError as err_val:
        flash(str(err_val), "danger")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al actualizar el estado de aspecto: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-estados'))


@blueprint_admin.route('/estados-aspecto/alternar/<int:id_estado>', methods=['POST'])
def alternar_estado_aspecto(id_estado: int):
    """Alterna el estado activo de un estado de aspecto."""
    estado = EstadoAspecto.query.get_or_404(id_estado)
    try:
        estado.activo = not estado.activo
        db.session.commit()
        est = "activado" if estado.activo else "desactivado"
        flash(f"Estado de aspecto '{estado.nombre_estado}' {est}.", "info")
    except Exception as err:
        db.session.rollback()
        flash(f"Error al alternar estado: {str(err)}", "danger")

    return redirect(url_for('admin.tablas', _anchor='tab-estados'))
