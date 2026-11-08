"""
Pruebas Automatizadas: Motor Dinámico de Puntos y Cero Hardcoding
Valida la fórmula matemática enriquecida consultando dinámicamente desde SQL Server.
"""

import pytest
from app.models.categoria_prenda import CategoriaPrenda
from app.models.material import Material
from app.models.estado_aspecto import EstadoAspecto
from app.models.nivel_utilidad import NivelUtilidad
from app.services.calculadora_puntos_service import CalculadoraPuntosService


def test_calculo_formula_enriquecida_prenda_estandar(aplicacion):
    """
    Verifica que la fórmula:
    Puntos = REDONDEAR( ((Base * FactorMat) + BonoMat) * Conservacion + BonoUtil )
    se calcule con total precisión matemática sin datos quemados.
    """
    with aplicacion.app_context():
        # Consultar entidades activas en SQL Server
        categoria = CategoriaPrenda.query.filter_by(tipo_articulo='PRENDA', activo=True).first()
        material = Material.query.filter_by(es_metal_o_joya_preciosa=False, activo=True).first()
        estado = EstadoAspecto.query.filter_by(activo=True).first()
        utilidad = NivelUtilidad.query.filter_by(activo=True).first()

        resultado = CalculadoraPuntosService.calcular_puntos(
            id_categoria=categoria.id_categoria,
            id_material=material.id_material,
            id_estado_aspecto=estado.id_estado_aspecto,
            id_nivel_utilidad=utilidad.id_nivel_utilidad
        )

        base = float(categoria.puntaje_base)
        factor = float(material.factor_multiplicador)
        bono_mat = int(material.bono_puntos_material)
        conservacion = float(estado.factor_conservacion)
        bono_uti = int(utilidad.bono_puntos)

        esperado = round(((base * factor) + bono_mat) * conservacion + bono_uti)

        assert resultado['puntos'] == esperado
        assert resultado['requiere_aprobacion_especial'] == material.requiere_aprobacion_especial
        assert resultado['tipo_acreditacion'] == 'INMEDIATA'
        assert 'Fórmula:' in resultado['descripcion_auditoria']


def test_bloqueo_retencion_joyeria_preciosa(aplicacion):
    """
    Verifica que para materiales del Grupo F (joyería y metales preciosos),
    el servicio identifique obligatoriamente la regla de retención preventiva.
    """
    with aplicacion.app_context():
        categoria_joya = CategoriaPrenda.query.filter_by(tipo_articulo='ACCESORIO', activo=True).first()
        material_joya = Material.query.filter_by(es_metal_o_joya_preciosa=True, requiere_aprobacion_especial=True, activo=True).first()
        estado = EstadoAspecto.query.filter_by(activo=True).first()
        utilidad = NivelUtilidad.query.filter_by(activo=True).first()

        assert material_joya is not None, "Debe existir al menos un material de joyería en la base de datos."

        resultado = CalculadoraPuntosService.calcular_puntos(
            id_categoria=categoria_joya.id_categoria,
            id_material=material_joya.id_material,
            id_estado_aspecto=estado.id_estado_aspecto,
            id_nivel_utilidad=utilidad.id_nivel_utilidad
        )

        assert resultado['requiere_aprobacion_especial'] is True
        assert resultado['es_metal_o_joya_preciosa'] is True
        assert resultado['tipo_acreditacion'] == 'RETENIDA'


def test_incompatibilidad_material_con_tipo_articulo(aplicacion):
    """
    Verifica que no se permita calcular puntos si el uso_principal del material
    no es compatible con el tipo_articulo de la categoría.
    """
    with aplicacion.app_context():
        cat_prenda = CategoriaPrenda.query.filter_by(tipo_articulo='PRENDA', activo=True).first()
        mat_accesorio = Material.query.filter_by(uso_principal='ACCESORIO', activo=True).first()
        estado = EstadoAspecto.query.filter_by(activo=True).first()
        utilidad = NivelUtilidad.query.filter_by(activo=True).first()

        if mat_accesorio:
            with pytest.raises(ValueError) as err:
                CalculadoraPuntosService.calcular_puntos(
                    id_categoria=cat_prenda.id_categoria,
                    id_material=mat_accesorio.id_material,
                    id_estado_aspecto=estado.id_estado_aspecto,
                    id_nivel_utilidad=utilidad.id_nivel_utilidad
                )
            assert "no es compatible" in str(err.value)
