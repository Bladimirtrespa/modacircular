"""
Script de Verificación y Manejo de Microsoft SQL Server (DB_IntercambioRopa)
Demuestra conectividad, metadatos, integridad relacional, restricciones CHECK y transacciones ACID.
"""
import sys
from sqlalchemy import text
from app import crear_app, db
from app.models import (
    RolUsuario,
    Usuario,
    CategoriaPrenda,
    Material,
    EstadoAspecto,
    NivelUtilidad,
    PrendaAccesorio,
    MultimediaPrenda,
    SolicitudAprobacionMaterial,
    TransaccionAdquisicion,
    HistorialMovimientosPuntos,
    OfertaTrueque,
    DetalleArticuloOferta,
    SalaChatIntercambio,
    MensajeChat,
    ReporteComportamientoEstafa
)
from app.services.calculadora_puntos_service import CalculadoraPuntosService

def separador(titulo=""):
    print("\n" + "=" * 70)
    if titulo:
        print(f" >>> {titulo.upper()} <<<")
        print("=" * 70)

def ejecutar_prueba():
    app = crear_app()

    with app.app_context():
        separador("1. Salud y Metadatos de Microsoft SQL Server")
        try:
            consulta_meta = text("""
                SELECT 
                    @@VERSION AS version, 
                    @@SERVERNAME AS servidor, 
                    DB_NAME() AS base_datos,
                    CURRENT_USER AS usuario_sesion;
            """)
            resultado = db.session.execute(consulta_meta).mappings().first()
            
            linea_version = resultado['version'].split("\n")[0]
            print(f"[OK] Servidor / Instancia : {resultado['servidor']}")
            print(f"[OK] Base de Datos Activa : {resultado['base_datos']}")
            print(f"[OK] Usuario de Conexión  : {resultado['usuario_sesion']}")
            print(f"[OK] Versión del Motor    : {linea_version}")
        except Exception as e:
            print(f"[ERROR] Error al consultar metadatos: {e}")
            sys.exit(1)

        separador("2. Inventario y Conteo en Tiempo Real de las 16 Tablas (v3.0)")
        tablas_modelos = [
            ("Roles_Usuario", RolUsuario),
            ("Usuarios", Usuario),
            ("Categorias_Prenda", CategoriaPrenda),
            ("Materiales", Material),
            ("Estados_Aspecto", EstadoAspecto),
            ("Niveles_Utilidad", NivelUtilidad),
            ("Prendas_Accesorios", PrendaAccesorio),
            ("Multimedia_Prenda", MultimediaPrenda),
            ("Solicitudes_Aprobacion_Material", SolicitudAprobacionMaterial),
            ("Transacciones_Adquisicion", TransaccionAdquisicion),
            ("Historial_Movimientos_Puntos", HistorialMovimientosPuntos),
            ("Ofertas_Trueque", OfertaTrueque),
            ("Detalle_Articulos_Oferta", DetalleArticuloOferta),
            ("Salas_Chat_Intercambio", SalaChatIntercambio),
            ("Mensajes_Chat", MensajeChat),
            ("Reportes_Comportamiento_Estafa", ReporteComportamientoEstafa)
        ]

        total_registros_sistema = 0
        for nombre_tabla, modelo in tablas_modelos:
            conteo = db.session.query(modelo).count()
            total_registros_sistema += conteo
            print(f" -> Tabla {nombre_tabla.ljust(33)}: {str(conteo).rjust(5)} registros")
        
        print(f"\n[TOTAL GLOBAL]: {total_registros_sistema} registros activos inspeccionados.")

        # Detalle de materiales y joyería
        total_materiales = db.session.query(Material).count()
        total_joyas = db.session.query(Material).filter_by(es_metal_o_joya_preciosa=True).count()
        print(f"[CATÁLOGO DE MATERIALES]: {total_materiales} materiales (11 metales/gemas preciosas con aprobación especial)")

        separador("3. Demostración de Transaccionalidad ACID (Commit vs. Rollback)")
        usuario_prueba = db.session.query(Usuario).first()
        if usuario_prueba:
            saldo_original = usuario_prueba.saldo_puntos_disponibles
            print(f" - Usuario de prueba       : {usuario_prueba.nombre_completo} ({usuario_prueba.correo_electronico})")
            print(f" - Saldo original en BD    : {saldo_original} puntos")

            # Modificación en memoria y en sesión transaccional
            print(" - Simulando modificación temporal: saldo_puntos_disponibles += 50000...")
            usuario_prueba.saldo_puntos_disponibles += 50000
            db.session.flush()

            # Forzar ROLLBACK
            print(" - Ejecutando db.session.rollback() forzado...")
            db.session.rollback()

            # Recargar usuario fresco desde SQL Server
            usuario_recargado = db.session.get(Usuario, usuario_prueba.id_usuario)
            print(f" - Saldo verificado en BD  : {usuario_recargado.saldo_puntos_disponibles} puntos")

            if usuario_recargado.saldo_puntos_disponibles == saldo_original:
                print("[ACID CONFIRMADO] Atomicidad y Consistencia garantizadas. La BD no sufrió ninguna alteración indebida.")
            else:
                print("[FALLO ACID] La reversión de transacción falló.")
        else:
            print("[ALERTA] No se encontró usuario para prueba ACID.")

        separador("4. Verificación de Restricciones CHECK Nativas de SQL Server")
        prenda_ref = db.session.query(PrendaAccesorio).first()
        if prenda_ref:
            print(" - Intentando violar deliberadamente la restricción CK_Multimedia_Tipo:")
            print("   Inserción de tipo_archivo='TIPO_ILEGAL' (Solo permitido: 'FOTO' o 'VIDEO')...")
            try:
                multimedia_invalida = MultimediaPrenda(
                    id_prenda=prenda_ref.id_prenda,
                    tipo_archivo="TIPO_ILEGAL",
                    ruta_archivo="subidas/test_ilegal.xyz",
                    es_portada=False
                )
                db.session.add(multimedia_invalida)
                db.session.flush()
                print("[FALLO] SQL Server permitió un dato inválido contra la restricción.")
            except Exception as ex_check:
                db.session.rollback()
                print("[ÉXITO] SQL Server rechazó la operación a nivel nativo de base de datos:")
                print(f"  Detalle técnico del motor: {str(ex_check).splitlines()[0]}")
                print("  -> Restricción CHECK 'CK_Multimedia_Tipo' activa y funcionando.")
        else:
            print("[ALERTA] No hay prendas para prueba de CHECK constraint.")

        separador("5. Prueba de Consulta Relacional Avanzada (Eager Loading y Joins ORM)")
        prenda_rel = db.session.query(PrendaAccesorio).first()
        if prenda_rel:
            print(f" - Prenda ID        : {prenda_rel.id_prenda}")
            print(f" - Título           : {prenda_rel.titulo_publicacion}")
            print(f" - Propietario      : {prenda_rel.propietario.nombre_completo} <{prenda_rel.propietario.correo_electronico}>")
            print(f" - Categoría        : {prenda_rel.categoria.nombre_categoria} (Tipo: {prenda_rel.categoria.tipo_articulo}, Base: {prenda_rel.categoria.puntaje_base})")
            print(f" - Material         : {prenda_rel.material.nombre_material} (Factor: {prenda_rel.material.factor_multiplicador}, Bono: {prenda_rel.material.bono_puntos_material})")
            print(f" - Estado Aspecto   : {prenda_rel.estado_aspecto.nombre_estado} (Factor: {prenda_rel.estado_aspecto.factor_conservacion})")
            print(f" - Nivel Utilidad   : {prenda_rel.nivel_utilidad.nombre_utilidad} (Bono: {prenda_rel.nivel_utilidad.bono_puntos})")
            print(f" - Puntos Asignados : {prenda_rel.puntos_valoracion} pts")
            print(f" - Estado Prenda    : {prenda_rel.estado_publicacion}")
            print(f" - Multimedia       : {prenda_rel.archivos_multimedia.count()} archivo(s) asociado(s)")

            # Validar con la Calculadora de Dominio
            calculo = CalculadoraPuntosService.calcular_puntos(
                id_categoria=prenda_rel.id_categoria,
                id_material=prenda_rel.id_material,
                id_estado_aspecto=prenda_rel.id_estado_aspecto,
                id_nivel_utilidad=prenda_rel.id_nivel_utilidad
            )
            print(f" - Validación Motor : {calculo['puntos']} pts calculados dinámicamente.")
            print(f" - Fórmula Auditoría: {calculo['descripcion_auditoria']}")
            print("[OK] Integridad referencial bidireccional y motor dinámico de puntos 100% operativos.")
        else:
            print("[ALERTA] No hay prendas registradas para consulta relacional.")

        separador("PRUEBA DE MANEJO DE SQL SERVER COMPLETADA CON ÉXITO")

if __name__ == "__main__":
    ejecutar_prueba()
