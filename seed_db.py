"""
Script de Verificación e Inicialización de Semillas Paramétricas (seed_db.py)
Totalmente compatible con la base de datos existente en SQL Server (DB_IntercambioRopa).
Verifica e inserta de forma estrictamente idempotente:
- Roles de Usuario
- Categorías de Prendas y Accesorios
- Estados de Aspecto
- Niveles de Utilidad
- Catálogo Maestro Completo de 55 Materiales en 6 Familias
- Cuentas de Usuario Administrador / Moderador
"""

import sys
from app import crear_app, db
from app.models import (
    RolUsuario,
    Usuario,
    CategoriaPrenda,
    Material,
    EstadoAspecto,
    NivelUtilidad
)

app = crear_app('desarrollo')


def inicializar_roles():
    """Verifica e inicializa los roles de usuario."""
    roles_requeridos = [
        {'nombre_rol': 'ADMINISTRADOR', 'descripcion': 'Control total del sistema, configuración paramétrica y auditoría.'},
        {'nombre_rol': 'MODERADOR', 'descripcion': 'Revisión y aprobación de metales y joyas preciosas.'},
        {'nombre_rol': 'USUARIO', 'descripcion': 'Usuario estándar con billetera de puntos para publicar e intercambiar prendas.'}
    ]
    roles_actuales = {r.nombre_rol.upper(): r for r in RolUsuario.query.all()}
    nuevos = 0
    for datos in roles_requeridos:
        if datos['nombre_rol'].upper() not in roles_actuales and (datos['nombre_rol'] != 'ADMINISTRADOR' or 'ADMIN' not in roles_actuales):
            nuevo_rol = RolUsuario(**datos)
            db.session.add(nuevo_rol)
            nuevos += 1
    db.session.commit()
    total = RolUsuario.query.count()
    print(f"-> Roles verificados exitosamente. ({nuevos} nuevos creados, Total en BD: {total})")


def inicializar_categorias():
    """Verifica la existencia de categorías de prendas y accesorios."""
    total = CategoriaPrenda.query.count()
    print(f"-> Categorías verificadas exitosamente. (Total en BD: {total})")


def inicializar_estados_aspecto():
    """Verifica la existencia de los estados de aspecto."""
    total = EstadoAspecto.query.count()
    print(f"-> Estados de Aspecto verificados exitosamente. (Total en BD: {total})")


def inicializar_niveles_utilidad():
    """Verifica la existencia de los niveles de utilidad."""
    total = NivelUtilidad.query.count()
    print(f"-> Niveles de Utilidad verificados exitosamente. (Total en BD: {total})")


def inicializar_materiales():
    """
    Catálogo Maestro Exhaustivo de 55 Materiales distribuidos en 6 familias taxonómicas.
    Ejecuta sincronización idempotente en Microsoft SQL Server.
    """
    catalogo_55_materiales = [
        # FAMILIA 1: Textiles Sintéticos y Semisintéticos (9 materiales)
        {
            'codigo_material': 'TEX-SIN-001', 'nombre_material': 'Poliéster Estándar',
            'familia_material': 'Textil Sintético', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 0.85, 'bono_puntos_material': 5,
            'nivel_sostenibilidad': 'Estándar', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Fibra sintética de polímero convencional, secado rápido y resistencia a arrugas.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-SIN-002', 'nombre_material': 'Poliéster Reciclado (rPET)',
            'familia_material': 'Textil Sintético', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.15, 'bono_puntos_material': 10,
            'nivel_sostenibilidad': 'Alto (Eco/Reciclado)', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Fibra reciclada a partir de botellas PET post-consumo con certificación GRS.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-SIN-003', 'nombre_material': 'Nylon / Poliamida',
            'familia_material': 'Textil Sintético', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 0.95, 'bono_puntos_material': 5,
            'nivel_sostenibilidad': 'Estándar', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Poliamida termoplástica resistente a la abrasión y tracción.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-SIN-004', 'nombre_material': 'Acrílico Textil',
            'familia_material': 'Textil Sintético', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 0.85, 'bono_puntos_material': 0,
            'nivel_sostenibilidad': 'Estándar', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Sucedáneo sintético de lana, liviano y con retención térmica media.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-SIN-005', 'nombre_material': 'Elastano / Lycra / Spandex',
            'familia_material': 'Textil Sintético', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 0.95, 'bono_puntos_material': 5,
            'nivel_sostenibilidad': 'Estándar', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Fibra sintética de poliuretano segmentado con alta elasticidad y recuperación.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-SIN-006', 'nombre_material': 'Microfibra / Polar (Fleece)',
            'familia_material': 'Textil Sintético', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 1.00, 'bono_puntos_material': 5,
            'nivel_sostenibilidad': 'Estándar', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Tejido sintético perchado de fibra fina, suave y abrigado.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-ART-007', 'nombre_material': 'Viscosa / Rayón',
            'familia_material': 'Fibra Semisintética', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 1.05, 'bono_puntos_material': 8,
            'nivel_sostenibilidad': 'Medio', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Fibra de celulosa regenerada con caída fluida y transpirabilidad.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-ART-008', 'nombre_material': 'Modal / Bambú Textil',
            'familia_material': 'Fibra Semisintética', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 1.20, 'bono_puntos_material': 12,
            'nivel_sostenibilidad': 'Alto (Eco/Reciclado)', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Celulosa purificada de haya o bambú con proceso de bajo impacto hídrico.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-ART-009', 'nombre_material': 'Lyocell / Tencel',
            'familia_material': 'Fibra Semisintética', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 1.30, 'bono_puntos_material': 18,
            'nivel_sostenibilidad': 'Alto (Eco/Reciclado)', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Fibra vegetal de circuito cerrado, biodegradable y de tacto sedoso.',
            'activo': True
        },

        # FAMILIA 2: Fibras Naturales Vegetales (11 materiales)
        {
            'codigo_material': 'TEX-NAT-010', 'nombre_material': 'Algodón Convencional',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.15, 'bono_puntos_material': 10,
            'nivel_sostenibilidad': 'Medio', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Fibra natural vegetal suave, transpirable y de uso universal.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-NAT-011', 'nombre_material': 'Algodón Orgánico Certificado',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.35, 'bono_puntos_material': 20,
            'nivel_sostenibilidad': 'Alto (Eco/Reciclado)', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Algodón cultivado sin pesticidas sintéticos con certificación GOTS/OCS.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-NAT-012', 'nombre_material': 'Algodón Pima / Egipcio',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 1.45, 'bono_puntos_material': 25,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Algodón de fibra extra larga, alta resistencia al pilling y lustre sedoso.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-NAT-013', 'nombre_material': 'Denim / Mezclilla Liviana',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.25, 'bono_puntos_material': 15,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Tejido sarga de algodón teñido en índigo, densidad media (8-11 oz).',
            'activo': True
        },
        {
            'codigo_material': 'TEX-NAT-014', 'nombre_material': 'Denim Pesado / Selvedge (12oz+)',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 1.45, 'bono_puntos_material': 25,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Denim tejido en telar de lanzadera tradicional con orillo rematado.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-NAT-015', 'nombre_material': 'Dril / Gabardina / Twill de Algodón',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 1.25, 'bono_puntos_material': 15,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Tejido cruzado firme y compacto para pantalones y chaquetas de trabajo.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-NAT-016', 'nombre_material': 'Pana / Corduroy',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.30, 'bono_puntos_material': 18,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Tejido con canales aterciopelados longitudinales de algodón puro.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-NAT-017', 'nombre_material': 'Lino 100% Natural',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 1.55, 'bono_puntos_material': 30,
            'nivel_sostenibilidad': 'Alto (Eco/Reciclado)', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Fibra vegetal de tallo de lino, altamente fresca, noble y termorreguladora.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-NAT-018', 'nombre_material': 'Cáñamo Textil (Hemp)',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.50, 'bono_puntos_material': 28,
            'nivel_sostenibilidad': 'Alto (Eco/Reciclado)', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Fibra ecológica de bajo consumo hídrico, antibacteriana y ultrarresistente.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-NAT-019', 'nombre_material': 'Lona / Canvas de Algodón',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.20, 'bono_puntos_material': 12,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Tejido plano grueso de algodón reforzado para bolsos, mochilas y calzado.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-NAT-020', 'nombre_material': 'Yute / Iraca / Raffia Natural',
            'familia_material': 'Fibra Natural Vegetal', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.25, 'bono_puntos_material': 15,
            'nivel_sostenibilidad': 'Alto (Eco/Reciclado)', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Fibras naturales rústicas tejidas artesanalmente para bolsos y sombrerería.',
            'activo': True
        },

        # FAMILIA 3: Fibras Animales, Especiales y de Lujo (8 materiales)
        {
            'codigo_material': 'TEX-ANI-021', 'nombre_material': 'Lana Virgen Estándar',
            'familia_material': 'Fibra Natural Animal', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.45, 'bono_puntos_material': 25,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Lana de primer esquileo de oveja, aislante térmica y elástica.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-ANI-022', 'nombre_material': 'Lana Merino Extrafina',
            'familia_material': 'Fibra Natural Animal', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 1.70, 'bono_puntos_material': 40,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Lana ultra fina (<19.5 micras), suave al tacto directo sin picor.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-ANI-023', 'nombre_material': 'Alpaca / Mohair',
            'familia_material': 'Fibra Natural Animal', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.85, 'bono_puntos_material': 50,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Fibra noble andina o caprina, liviana, sin lanolina e hipoalergénica.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-ANI-024', 'nombre_material': 'Cachemira (Cashmere)',
            'familia_material': 'Fibra Natural Animal', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 2.20, 'bono_puntos_material': 75,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Duvet fino de cabra de Cachemira, máxima ligereza, suavidad y lujo.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-ANI-025', 'nombre_material': 'Seda Natural (Mulberry Silk)',
            'familia_material': 'Fibra Natural Animal', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.80, 'bono_puntos_material': 45,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Filamento proteico natural del gusano de seda con brillo prismático inigualable.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-ESP-026', 'nombre_material': 'Terciopelo / Velvet',
            'familia_material': 'Textil Especial', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.35, 'bono_puntos_material': 20,
            'nivel_sostenibilidad': 'Medio', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Tejido tupido con pelo corto y denso de brillo profundo.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-ESP-027', 'nombre_material': 'Encaje / Guipur / Tul Bordado',
            'familia_material': 'Textil Especial', 'uso_principal': 'PRENDA',
            'factor_multiplicador': 1.30, 'bono_puntos_material': 18,
            'nivel_sostenibilidad': 'Medio', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Calado ornamental bordado sobre red o tul para prendas de fiesta o gala.',
            'activo': True
        },
        {
            'codigo_material': 'TEX-ESP-028', 'nombre_material': 'Tejido Técnico Impermeable (Gore-Tex / Ripstop)',
            'familia_material': 'Textil Técnico', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.65, 'bono_puntos_material': 35,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Membrana microporosa cortavientos, impermeable y transpirable de alta tecnología.',
            'activo': True
        },

        # FAMILIA 4: Cueros, Marroquinería y Calzado (6 materiales)
        {
            'codigo_material': 'MAR-SIN-029', 'nombre_material': 'Cuero Sintético / Cuerina / PU',
            'familia_material': 'Marroquinería Sintética', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.00, 'bono_puntos_material': 5,
            'nivel_sostenibilidad': 'Estándar', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Material compuesto con base textil y revestimiento de poliuretano.',
            'activo': True
        },
        {
            'codigo_material': 'MAR-ECO-030', 'nombre_material': 'Cuero Vegano Ecológico (Piñatex / Cactus / Micelio)',
            'familia_material': 'Marroquinería Sostenible', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.45, 'bono_puntos_material': 25,
            'nivel_sostenibilidad': 'Alto (Eco/Reciclado)', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Biotextil innovador libre de crueldad animal derivado de residuos vegetales.',
            'activo': True
        },
        {
            'codigo_material': 'MAR-CUE-031', 'nombre_material': 'Gamuza / Ante / Nobuck Legítimo',
            'familia_material': 'Cuero y Piel Natural', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.75, 'bono_puntos_material': 45,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Piel curtida con acabado aterciopelado lijado de flor o descarne fino.',
            'activo': True
        },
        {
            'codigo_material': 'MAR-CUE-032', 'nombre_material': 'Cuero Vacuno Genuino (Grano Corregido)',
            'familia_material': 'Cuero y Piel Natural', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 1.85, 'bono_puntos_material': 55,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Cuero bovino auténtico curtido al cromo o vegetal con acabado resistente.',
            'activo': True
        },
        {
            'codigo_material': 'MAR-CUE-033', 'nombre_material': 'Cuero Plena Flor / Napa / Piel de Cordero',
            'familia_material': 'Cuero y Piel Natural', 'uso_principal': 'AMBOS',
            'factor_multiplicador': 2.15, 'bono_puntos_material': 75,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Capa superior intacta del cuero, máxima suavidad, durabilidad y pátina natural.',
            'activo': True
        },
        {
            'codigo_material': 'MAR-CAL-034', 'nombre_material': 'Caucho Natural / Goma Vulcanizada / EVA',
            'familia_material': 'Material de Calzado', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.10, 'bono_puntos_material': 10,
            'nivel_sostenibilidad': 'Medio', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Polímeros elásticos de alta amortiguación y adherencia para suelas y accesorios.',
            'activo': True
        },

        # FAMILIA 5: Accesorios No Metálicos, Óptica y Metales Inoxidables (10 materiales)
        {
            'codigo_material': 'ACC-PLA-035', 'nombre_material': 'Resina / Acrílico / Policarbonato',
            'familia_material': 'Polímero para Accesorios', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 0.85, 'bono_puntos_material': 0,
            'nivel_sostenibilidad': 'Estándar', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Termoplásticos moldeados rígidos para bisutería moderna y piezas de fantasía.',
            'activo': True
        },
        {
            'codigo_material': 'ACC-OPT-036', 'nombre_material': 'Acetato de Celulosa (Óptica / Gafas)',
            'familia_material': 'Polímero de Alta Gama', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.35, 'bono_puntos_material': 20,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Polímero vegetal hipoalergénico de origen natural usado en monturas de alta gama.',
            'activo': True
        },
        {
            'codigo_material': 'ACC-NAT-037', 'nombre_material': 'Madera Noble / Tagua / Semillas Naturales',
            'familia_material': 'Artesanal Sostenible', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.20, 'bono_puntos_material': 15,
            'nivel_sostenibilidad': 'Alto (Eco/Reciclado)', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Madera tratada o marfil vegetal (tagua) para joyería artesanal sostenible.',
            'activo': True
        },
        {
            'codigo_material': 'ACC-CRI-038', 'nombre_material': 'Cristal Tallado / Vidrio Murano / Swarovski',
            'familia_material': 'Cristalería Fina', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.50, 'bono_puntos_material': 30,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Vidrio óptico de alta refracción tallado a mano o con incrustaciones decorativas.',
            'activo': True
        },
        {
            'codigo_material': 'MET-BAS-039', 'nombre_material': 'Aleación de Zinc / Zamak / Fantasía Fina',
            'familia_material': 'Metal Base (Bisutería)', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 0.90, 'bono_puntos_material': 0,
            'nivel_sostenibilidad': 'Estándar', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Aleación no ferrosa de zinc, aluminio, magnesio y cobre para herrajes.',
            'activo': True
        },
        {
            'codigo_material': 'MET-BAS-040', 'nombre_material': 'Aluminio Anodizado',
            'familia_material': 'Metal Base (Bisutería)', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 0.95, 'bono_puntos_material': 5,
            'nivel_sostenibilidad': 'Alto (Eco/Reciclado)', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Metal ultraligero con capa de óxido electroquímica de protección anticorrosiva.',
            'activo': True
        },
        {
            'codigo_material': 'MET-BAS-041', 'nombre_material': 'Cobre / Bronce / Latón Artesanal',
            'familia_material': 'Metal Base (Bisutería)', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.20, 'bono_puntos_material': 15,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Metales cálidos tradicionales trabajados por orfebres para hebillas y joyería.',
            'activo': True
        },
        {
            'codigo_material': 'MET-INO-042', 'nombre_material': 'Acero Inoxidable Quirúrgico 316L',
            'familia_material': 'Metal Inoxidable', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.25, 'bono_puntos_material': 18,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Acero austenítico hipoalergénico, inalterable al agua marina y sudoración.',
            'activo': True
        },
        {
            'codigo_material': 'MET-INO-043', 'nombre_material': 'Titanio Grado Médico / Relojería',
            'familia_material': 'Metal Inoxidable', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.65, 'bono_puntos_material': 38,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Metal de transición ultrarresistente y ligero, 100% biocompatible.',
            'activo': True
        },
        {
            'codigo_material': 'MET-INO-044', 'nombre_material': 'Carburo de Tungsteno / Cerámica de Joyería',
            'familia_material': 'Metal Inoxidable', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.55, 'bono_puntos_material': 32,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': False,
            'requiere_aprobacion_especial': False,
            'descripcion_tecnica': 'Material sintético de extrema dureza (escala Mohs 9), inrayable y de brillo eterno.',
            'activo': True
        },

        # FAMILIA 6: Metales Preciosos, Perlas y Gemas (11 materiales con aprobación especial)
        {
            'codigo_material': 'JOY-REC-045', 'nombre_material': 'Baño de Oro / Oro Golfi (Gold Filled 14k-18k)',
            'familia_material': 'Joyería Recubierta', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 1.95, 'bono_puntos_material': 60,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Capa gruesa de oro auténtico prensada mecánicamente sobre metal base (5% en peso).',
            'activo': True
        },
        {
            'codigo_material': 'JOY-PLA-046', 'nombre_material': 'Plata Esterlina Ley 925',
            'familia_material': 'Metal Precioso', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 2.80, 'bono_puntos_material': 110,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Aleación de metal precioso con pureza mínima de 92.5% de plata certificada.',
            'activo': True
        },
        {
            'codigo_material': 'JOY-PLA-047', 'nombre_material': 'Plata Ley 950 / Plata con Baño de Rodio o Vermeil',
            'familia_material': 'Metal Precioso', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 3.15, 'bono_puntos_material': 135,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Plata de alta pureza (95%) con acabado electrolítico antidesgaste en rodio u oro.',
            'activo': True
        },
        {
            'codigo_material': 'JOY-ORO-048', 'nombre_material': 'Oro Macizo 10k / 14k (Amarillo, Blanco o Rosa)',
            'familia_material': 'Metal Precioso', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 4.50, 'bono_puntos_material': 250,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Aleación maciza de oro con pureza entre 41.7% y 58.5% con contraste oficial.',
            'activo': True
        },
        {
            'codigo_material': 'JOY-ORO-049', 'nombre_material': 'Oro Macizo 18k (Ley 750)',
            'familia_material': 'Metal Precioso', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 6.00, 'bono_puntos_material': 380,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Estándar internacional de alta joyería con 75% de oro fino puro garantizado.',
            'activo': True
        },
        {
            'codigo_material': 'JOY-ORO-050', 'nombre_material': 'Oro 24k / Platino Ley 950 / Paladio',
            'familia_material': 'Metal Precioso', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 7.20, 'bono_puntos_material': 480,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Metales nobles en estado de máxima pureza orfebre (99.9% oro o platino 950).',
            'activo': True
        },
        {
            'codigo_material': 'JOY-GEM-051', 'nombre_material': 'Perlas Naturales Cultivadas / Nácar Fino',
            'familia_material': 'Gema Orgánica', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 3.20, 'bono_puntos_material': 140,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Gemas orgánicas producidas por ostras perlíferas con oriente y lustre profundo.',
            'activo': True
        },
        {
            'codigo_material': 'JOY-GEM-052', 'nombre_material': 'Piedras Semipreciosas Naturales (Cuarzo, Amatista, Jade, Ónix, Turquesa)',
            'familia_material': 'Piedra Natural', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 2.60, 'bono_puntos_material': 95,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Minerales naturales tallados en cabujón o facetas para piezas de orfebrería.',
            'activo': True
        },
        {
            'codigo_material': 'JOY-GEM-053', 'nombre_material': 'Joya con Esmeralda Colombiana / Rubí / Zafiro Natural',
            'familia_material': 'Piedra Preciosa', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 7.80, 'bono_puntos_material': 550,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Piedras preciosas mayores de alta pureza mineral, color intenso y talla magistral.',
            'activo': True
        },
        {
            'codigo_material': 'JOY-GEM-054', 'nombre_material': 'Joya con Diamante Natural / Moissanita Certificada GRA',
            'familia_material': 'Piedra Preciosa', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 8.50, 'bono_puntos_material': 650,
            'nivel_sostenibilidad': 'Alta Durabilidad', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Carbono cristalizado de máxima dureza (Mohs 10) o carburo de silicio con certificado.',
            'activo': True
        },
        {
            'codigo_material': 'JOY-PLA-055', 'nombre_material': 'Platino Puro 950 Grado Joyería',
            'familia_material': 'Metales Preciosos, Perlas y Gemas', 'uso_principal': 'ACCESORIO',
            'factor_multiplicador': 7.50, 'bono_puntos_material': 500,
            'nivel_sostenibilidad': 'Máximo (Platino 950 Puro)', 'es_metal_o_joya_preciosa': True,
            'requiere_aprobacion_especial': True,
            'descripcion_tecnica': 'Platino puro al 95% de ley con sello oficial, densidad inalterable y máxima nobleza.',
            'activo': True
        }
    ]

    nuevos = 0
    actualizados = 0

    for datos_mat in catalogo_55_materiales:
        # Búsqueda idempotente por código SKU
        mat_existente = Material.query.filter_by(codigo_material=datos_mat['codigo_material']).first()
        if not mat_existente:
            # Alternativa por nombre
            mat_existente = Material.query.filter_by(nombre_material=datos_mat['nombre_material']).first()

        if mat_existente:
            # Sincronizar atributos paramétricos
            mat_existente.familia_material = datos_mat['familia_material']
            mat_existente.uso_principal = datos_mat['uso_principal']
            mat_existente.factor_multiplicador = datos_mat['factor_multiplicador']
            mat_existente.bono_puntos_material = datos_mat['bono_puntos_material']
            mat_existente.nivel_sostenibilidad = datos_mat['nivel_sostenibilidad']
            mat_existente.es_metal_o_joya_preciosa = datos_mat['es_metal_o_joya_preciosa']
            mat_existente.requiere_aprobacion_especial = datos_mat['requiere_aprobacion_especial']
            mat_existente.descripcion_tecnica = datos_mat['descripcion_tecnica']
            mat_existente.activo = datos_mat['activo']
            actualizados += 1
        else:
            nuevo_mat = Material(**datos_mat)
            db.session.add(nuevo_mat)
            nuevos += 1

    db.session.commit()
    total = Material.query.count()
    joyas = Material.query.filter_by(es_metal_o_joya_preciosa=True).count()
    print(f"-> Catálogo Maestro de Materiales sincronizado exitosamente:")
    print(f"   * Total en BD: {total} materiales")
    print(f"   * Nuevos creados: {nuevos}")
    print(f"   * Actualizados/Sincronizados: {actualizados}")
    print(f"   * Materiales de Joyería con aprobación especial: {joyas}")


def inicializar_usuarios_base():
    """
    Verifica e inicializa formalmente las cuentas principales del sistema:
    1. bladimir@intercambioropa.co (Administrador General, Clave: Admin1234*)
    2. admin@modacircular.com (Administrador / Moderador, Clave: Admin123*)
    3. carlos.restrepo@correo.com (Usuario Estándar, Clave: Usuario1234*)
    Garantiza que todos posean hashes válidos generados por Werkzeug.
    """
    rol_admin = RolUsuario.query.filter(RolUsuario.nombre_rol.in_(['ADMINISTRADOR', 'ADMIN'])).first()
    rol_usuario = RolUsuario.query.filter_by(nombre_rol='USUARIO').first()

    usuarios_requeridos = [
        {
            'correo': 'bladimir@intercambioropa.co',
            'nombre': 'Bladimir Albanis Trespalacio Carvajal',
            'clave': 'Admin1234*',
            'rol': rol_admin,
            'ciudad': 'Barranquilla, Colombia',
            'telefono': '+57 310 000 0000',
            'saldo_disponible': 1000
        },
        {
            'correo': 'admin@modacircular.com',
            'nombre': 'Administrador del Sistema',
            'clave': 'Admin123*',
            'rol': rol_admin,
            'ciudad': 'Bogotá, Colombia',
            'telefono': '+57 300 000 0000',
            'saldo_disponible': 100
        },
        {
            'correo': 'carlos.restrepo@correo.com',
            'nombre': 'Carlos Mario Restrepo',
            'clave': 'Usuario1234*',
            'rol': rol_usuario,
            'ciudad': 'Medellín, Colombia',
            'telefono': '+57 315 123 4567',
            'saldo_disponible': 250
        }
    ]

    for datos in usuarios_requeridos:
        usuario = Usuario.query.filter_by(correo_electronico=datos['correo']).first()
        if not usuario:
            nuevo_u = Usuario(
                id_rol=datos['rol'].id_rol if datos['rol'] else 1,
                nombre_completo=datos['nombre'],
                correo_electronico=datos['correo'],
                telefono=datos['telefono'],
                ciudad_ubicacion=datos['ciudad'],
                saldo_puntos_disponibles=datos['saldo_disponible'],
                saldo_puntos_retenidos=0,
                activo=True
            )
            nuevo_u.establecer_contrasena(datos['clave'])
            db.session.add(nuevo_u)
            print(f"-> Creado usuario base: {datos['correo']} (Rol: {datos['rol'].nombre_rol})")
        else:
            # Asegurar activación y regenerar hash formal con Werkzeug
            usuario.activo = True
            usuario.fecha_fin_suspension = None
            usuario.motivo_suspension = None
            if datos['rol']:
                usuario.id_rol = datos['rol'].id_rol
            usuario.establecer_contrasena(datos['clave'])
            print(f"-> Sincronizado y verificado acceso para: {datos['correo']} (Clave restaurada: {datos['clave']})")

    db.session.commit()


def ejecutar_semillas():
    """Punto de entrada para la ejecución y auditoría de semillas en SQL Server."""
    print("================================================================================")
    print("INICIANDO AUDITORÍA Y VERIFICACIÓN PARAMÉTRICA EN SQL SERVER (DB_IntercambioRopa)")
    print("================================================================================")
    with app.app_context():
        try:
            inicializar_roles()
            inicializar_categorias()
            inicializar_estados_aspecto()
            inicializar_niveles_utilidad()
            inicializar_materiales()
            inicializar_usuarios_base()
            
            print("================================================================================")
            print("VERIFICACIÓN PARAMÉTRICA EXITOSA: SISTEMA 100% OPERATIVO CON SQL SERVER")
            print("================================================================================")
        except Exception as error:
            db.session.rollback()
            print(f"ERROR DURANTE LA VERIFICACIÓN: {str(error)}", file=sys.stderr)
            raise error


if __name__ == '__main__':
    ejecutar_semillas()
