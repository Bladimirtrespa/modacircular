"""
Controlador de Endpoints AJAX / API REST (Blueprint de API)
Expone servicios para:
1. Filtrado dinámico de materiales según el tipo de artículo de la categoría.
2. Simulación y cálculo en tiempo real de los puntos que obtendrá el usuario.
"""

from flask import Blueprint, jsonify, request
from app.models.categoria_prenda import CategoriaPrenda
from app.models.material import Material
from app.services.calculadora_puntos_service import CalculadoraPuntosService

blueprint_api = Blueprint('api', __name__, url_prefix='/api')


@blueprint_api.route('/materiales-por-categoria/<int:id_categoria>', methods=['GET'])
def obtener_materiales_por_categoria(id_categoria: int):
    """
    Retorna la lista de materiales compatibles con la categoría seleccionada.
    Filtra dinámicamente según el tipo de artículo ('PRENDA' o 'ACCESORIO') o 'AMBOS'.
    """
    categoria = CategoriaPrenda.query.get(id_categoria)
    if not categoria or not categoria.activo:
        return jsonify({
            'exito': False,
            'mensaje': 'Categoría no encontrada o inactiva en el sistema.'
        }), 404

    # Consulta filtrada a SQL Server respetando la regla de negocio
    materiales = Material.query.filter(
        Material.activo == True,
        Material.uso_principal.in_([categoria.tipo_articulo, 'AMBOS'])
    ).order_by(Material.familia_material.asc(), Material.nombre_material.asc()).all()

    resultado = [
        {
            'id_material': m.id_material,
            'codigo_material': m.codigo_material,
            'nombre_material': m.nombre_material,
            'familia_material': m.familia_material,
            'uso_principal': m.uso_principal,
            'factor_multiplicador': float(m.factor_multiplicador),
            'bono_puntos_material': m.bono_puntos_material,
            'nivel_sostenibilidad': m.nivel_sostenibilidad,
            'es_metal_o_joya_preciosa': m.es_metal_o_joya_preciosa,
            'requiere_aprobacion_especial': m.requiere_aprobacion_especial,
            'descripcion_tecnica': m.descripcion_tecnica
        }
        for m in materiales
    ]

    return jsonify({
        'exito': True,
        'categoria': {
            'id_categoria': categoria.id_categoria,
            'nombre_categoria': categoria.nombre_categoria,
            'tipo_articulo': categoria.tipo_articulo,
            'puntaje_base': float(categoria.puntaje_base)
        },
        'total_materiales': len(resultado),
        'materiales': resultado
    })


@blueprint_api.route('/calcular-puntos', methods=['POST'])
def simular_calculo_puntos():
    """
    Calcula y simula en tiempo real los puntos de una publicación a partir de los 4 factores paramétricos.
    """
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({
            'exito': False,
            'mensaje': 'La petición debe incluir un cuerpo JSON válido.'
        }), 400

    id_categoria = datos.get('id_categoria')
    id_material = datos.get('id_material')
    id_estado_aspecto = datos.get('id_estado_aspecto')
    id_nivel_utilidad = datos.get('id_nivel_utilidad')

    # Validación de parámetros requeridos
    if not all([id_categoria, id_material, id_estado_aspecto, id_nivel_utilidad]):
        return jsonify({
            'exito': False,
            'mensaje': 'Se requieren los 4 parámetros: id_categoria, id_material, id_estado_aspecto, id_nivel_utilidad.'
        }), 400

    try:
        resultado = CalculadoraPuntosService.calcular_puntos(
            id_categoria=int(id_categoria),
            id_material=int(id_material),
            id_estado_aspecto=int(id_estado_aspecto),
            id_nivel_utilidad=int(id_nivel_utilidad)
        )
        return jsonify({
            'exito': True,
            'calculo': resultado
        })
    except ValueError as error_validacion:
        return jsonify({
            'exito': False,
            'mensaje': str(error_validacion)
        }), 400
    except Exception as error_servidor:
        return jsonify({
            'exito': False,
            'mensaje': f'Error interno al calcular puntos: {str(error_servidor)}'
        }), 500
