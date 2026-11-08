"""
Servicio de Dominio: Calculadora Dinámica de Puntos
Implementa la fórmula matemática enriquecida sin datos quemados (CERO HARDCODING).
Toda regla de puntaje base, factores, bonos y requerimientos de aprobación
se consulta dinámicamente desde Microsoft SQL Server (DB_IntercambioRopa).
"""

from typing import Dict, Any
from app.models.categoria_prenda import CategoriaPrenda
from app.models.material import Material
from app.models.estado_aspecto import EstadoAspecto
from app.models.nivel_utilidad import NivelUtilidad


class CalculadoraPuntosService:
    """
    Motor dinámico de valoración y auditoría de puntos para prendas y accesorios.
    
    Fórmula de Dominio:
    Puntos = REDONDEAR(
        ((Categoria.puntaje_base * Material.factor_multiplicador) + Material.bono_puntos_material)
        * EstadoAspecto.factor_conservacion
        + NivelUtilidad.bono_puntos
    )
    """

    @classmethod
    def calcular_puntos(
        cls,
        id_categoria: int,
        id_material: int,
        id_estado_aspecto: int,
        id_nivel_utilidad: int
    ) -> Dict[str, Any]:
        """
        Ejecuta el cálculo dinámico de puntos consultando las tablas maestras en SQL Server.
        
        :param id_categoria: Identificador de la categoría del artículo.
        :param id_material: Identificador del material o tejido.
        :param id_estado_aspecto: Identificador del estado de conservación física.
        :param id_nivel_utilidad: Identificador del nivel de utilidad o versatilidad.
        :return: Diccionario con los puntos calculados, banderas de moderación y auditoría.
        :raises ValueError: Si algún parámetro no existe en la base de datos o está inactivo.
        """
        from app import db

        # 1. Consulta dinámica de Categoria (puntaje_base)
        categoria = db.session.get(CategoriaPrenda, id_categoria)
        if not categoria or not categoria.activo:
            raise ValueError(f"La categoría con ID {id_categoria} no existe o no se encuentra activa.")

        # 2. Consulta dinámica de Material (factor_multiplicador, bono, aprobación especial)
        material = db.session.get(Material, id_material)
        if not material or not material.activo:
            raise ValueError(f"El material con ID {id_material} no existe o no se encuentra activo.")

        # Validar compatibilidad de uso_principal con tipo_articulo de la categoría
        if material.uso_principal != 'AMBOS' and material.uso_principal != categoria.tipo_articulo:
            raise ValueError(
                f"El material '{material.nombre_material}' ({material.uso_principal}) "
                f"no es compatible con el tipo de artículo '{categoria.tipo_articulo}'."
            )

        # 3. Consulta dinámica de Estado de Aspecto (factor_conservacion)
        estado_aspecto = db.session.get(EstadoAspecto, id_estado_aspecto)
        if not estado_aspecto or not estado_aspecto.activo:
            raise ValueError(f"El estado de aspecto con ID {id_estado_aspecto} no existe o no se encuentra activo.")

        # 4. Consulta dinámica de Nivel de Utilidad (bono_puntos)
        nivel_utilidad = db.session.get(NivelUtilidad, id_nivel_utilidad)
        if not nivel_utilidad or not nivel_utilidad.activo:
            raise ValueError(f"El nivel de utilidad con ID {id_nivel_utilidad} no existe o no se encuentra activo.")

        # Extracción de valores numéricos de las entidades de SQL Server
        puntaje_base = float(categoria.puntaje_base)
        factor_multiplicador = float(material.factor_multiplicador)
        bono_material = int(material.bono_puntos_material)
        factor_conservacion = float(estado_aspecto.factor_conservacion)
        bono_utilidad = int(nivel_utilidad.bono_puntos)

        # Ejecución estricta de la fórmula de valoración
        subtotal_base_material = (puntaje_base * factor_multiplicador) + bono_material
        subtotal_conservacion = subtotal_base_material * factor_conservacion
        total_puntos_flotante = subtotal_conservacion + bono_utilidad
        
        # Redondeo matemático al entero más cercano
        puntos_finales = round(total_puntos_flotante)
        
        # Asegurar un mínimo de 1 punto para cualquier prenda activa
        if puntos_finales < 1:
            puntos_finales = 1

        # Generación de la cadena de trazabilidad contable para auditoría (máx 300 caracteres)
        descripcion_auditoria = (
            f"Fórmula: ((Base {puntaje_base:.1f} * Mult {factor_multiplicador:.2f}) + BonoMat {bono_material}) "
            f"* Cons {factor_conservacion:.2f} + BonoUtil {bono_utilidad} = {puntos_finales} pts | "
            f"Cat: {categoria.nombre_categoria[:25]} | Mat: {material.nombre_material[:25]}"
        )
        if len(descripcion_auditoria) > 295:
            descripcion_auditoria = descripcion_auditoria[:295] + "..."

        # Clasificación de acreditación según regla de aprobación especial de joyería
        tipo_acreditacion = 'RETENIDA' if material.requiere_aprobacion_especial else 'INMEDIATA'

        return {
            'puntos': puntos_finales,
            'requiere_aprobacion_especial': material.requiere_aprobacion_especial,
            'es_metal_o_joya_preciosa': material.es_metal_o_joya_preciosa,
            'tipo_acreditacion': tipo_acreditacion,
            'descripcion_auditoria': descripcion_auditoria,
            'desglose': {
                'categoria': {
                    'id': categoria.id_categoria,
                    'nombre': categoria.nombre_categoria,
                    'puntaje_base': puntaje_base
                },
                'material': {
                    'id': material.id_material,
                    'nombre': material.nombre_material,
                    'familia': material.familia_material,
                    'factor_multiplicador': factor_multiplicador,
                    'bono_puntos_material': bono_material
                },
                'estado_aspecto': {
                    'id': estado_aspecto.id_estado_aspecto,
                    'nombre': estado_aspecto.nombre_estado,
                    'factor_conservacion': factor_conservacion
                },
                'nivel_utilidad': {
                    'id': nivel_utilidad.id_nivel_utilidad,
                    'nombre': nivel_utilidad.nombre_utilidad,
                    'bono_puntos': bono_utilidad
                },
                'subtotal_base_material': round(subtotal_base_material, 2),
                'subtotal_conservacion': round(subtotal_conservacion, 2)
            }
        }
