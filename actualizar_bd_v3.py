"""
Script de Actualización y Migración Automática de Base de Datos - Versión 3.0
Plataforma Sostenible de Intercambio de Ropa y Accesorios Basada en Puntos Dinámicos.

Aplica de forma idempotente las modificaciones sobre las tablas existentes,
crea las 5 nuevas tablas (totalizando 16 tablas en DB_IntercambioRopa),
actualiza la función escalar SQL dbo.fn_CalcularPuntosPrenda y valida la integridad de los 55 materiales.
"""

import sys
from sqlalchemy import text
from app import crear_app, db

def registrar_log(mensaje: str, exito: bool = True):
    prefijo = "[OK]" if exito else "[INFO]"
    print(f"{prefijo} {mensaje}")

def ejecutar_ddl_seguro(session, sentencia_sql: str, descripcion: str):
    try:
        session.execute(text(sentencia_sql))
        session.commit()
        registrar_log(descripcion, exito=True)
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Error al {descripcion.lower()}: {e}")
        raise e

def actualizar_base_datos():
    app = crear_app()

    with app.app_context():
        print("=" * 80)
        print(" INICIANDO ACTUALIZACIÓN INTEGRAL DE BASE DE DATOS SQL SERVER (v3.0)")
        print(" Servidor: Microsoft SQL Server 2022 | BD: DB_IntercambioRopa")
        print("=" * 80)

        # 1. Modificaciones en dbo.Usuarios
        print("\n--- PASO 1: Actualizar dbo.Usuarios ---")
        ddl_usr_dir = """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('dbo.Usuarios') AND name = 'direccion_predeterminada')
        BEGIN
            ALTER TABLE dbo.Usuarios ADD direccion_predeterminada NVARCHAR(250) NULL;
        END
        """
        ejecutar_ddl_seguro(db.session, ddl_usr_dir, "Columna direccion_predeterminada en dbo.Usuarios")

        ddl_usr_bio = """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('dbo.Usuarios') AND name = 'biografia_vitrina')
        BEGIN
            ALTER TABLE dbo.Usuarios ADD biografia_vitrina NVARCHAR(300) NULL;
        END
        """
        ejecutar_ddl_seguro(db.session, ddl_usr_bio, "Columna biografia_vitrina en dbo.Usuarios")

        ddl_usr_rep = """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('dbo.Usuarios') AND name = 'reputacion_trueques')
        BEGIN
            ALTER TABLE dbo.Usuarios ADD reputacion_trueques INT NOT NULL CONSTRAINT DF_Usuarios_Reputacion DEFAULT 100;
        END
        """
        ejecutar_ddl_seguro(db.session, ddl_usr_rep, "Columna reputacion_trueques en dbo.Usuarios")

        # 2. Modificaciones en dbo.Prendas_Accesorios
        print("\n--- PASO 2: Actualizar dbo.Prendas_Accesorios ---")
        ddl_prenda_mod = """
        IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('dbo.Prendas_Accesorios') AND name = 'modalidad_publicacion')
        BEGIN
            ALTER TABLE dbo.Prendas_Accesorios ADD modalidad_publicacion NVARCHAR(25) NOT NULL CONSTRAINT DF_Prendas_Modalidad DEFAULT 'SOLO_PUNTOS';
        END
        """
        ejecutar_ddl_seguro(db.session, ddl_prenda_mod, "Columna modalidad_publicacion en dbo.Prendas_Accesorios")

        ddl_prenda_ck_mod = """
        IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_Prendas_ModalidadValida')
        BEGIN
            ALTER TABLE dbo.Prendas_Accesorios ADD CONSTRAINT CK_Prendas_ModalidadValida 
            CHECK (modalidad_publicacion IN ('SOLO_PUNTOS', 'INVENTARIO_TRUEQUE', 'AMBOS'));
        END
        """
        ejecutar_ddl_seguro(db.session, ddl_prenda_ck_mod, "Restricción CK_Prendas_ModalidadValida en dbo.Prendas_Accesorios")

        ddl_prenda_ck_estado = """
        DECLARE @chk_nombre NVARCHAR(200);
        SELECT @chk_nombre = cc.name 
        FROM sys.check_constraints cc 
        JOIN sys.columns c ON cc.parent_object_id = c.object_id AND cc.parent_column_id = c.column_id
        WHERE cc.parent_object_id = OBJECT_ID('dbo.Prendas_Accesorios') AND c.name = 'estado_publicacion';

        IF @chk_nombre IS NOT NULL
        BEGIN
            EXEC('ALTER TABLE dbo.Prendas_Accesorios DROP CONSTRAINT ' + @chk_nombre);
        END

        ALTER TABLE dbo.Prendas_Accesorios ADD CONSTRAINT CK_Prendas_EstadoValido 
        CHECK (estado_publicacion IN ('PUBLICADA', 'EN_INVENTARIO', 'PENDIENTE_APROBACION', 'RESERVADA_TRUEQUE', 'INTERCAMBIADA', 'RECHAZADA', 'INACTIVA'));
        """
        ejecutar_ddl_seguro(db.session, ddl_prenda_ck_estado, "Restricción CK_Prendas_EstadoValido ampliada en dbo.Prendas_Accesorios")

        # 3. Modificaciones en dbo.Historial_Movimientos_Puntos
        print("\n--- PASO 3: Actualizar dbo.Historial_Movimientos_Puntos ---")
        ddl_historial = """
        DECLARE @chk_hist NVARCHAR(200);
        SELECT @chk_hist = cc.name 
        FROM sys.check_constraints cc 
        JOIN sys.columns c ON cc.parent_object_id = c.object_id AND cc.parent_column_id = c.column_id
        WHERE cc.parent_object_id = OBJECT_ID('dbo.Historial_Movimientos_Puntos') AND c.name = 'tipo_movimiento';

        IF @chk_hist IS NOT NULL
        BEGIN
            EXEC('ALTER TABLE dbo.Historial_Movimientos_Puntos DROP CONSTRAINT ' + @chk_hist);
        END

        ALTER TABLE dbo.Historial_Movimientos_Puntos ADD CONSTRAINT CK_Historial_Tipo 
        CHECK (tipo_movimiento IN (
            'CREDITO_PUBLICACION', 
            'CREDITO_APROBACION_JOYA', 
            'CREDITO_CONVERSION_INVENTARIO', 
            'DEBITO_ADQUISICION', 
            'AJUSTE_ADMIN', 
            'AJUSTE_ADMINISTRATIVO',
            'REVERSION_POR_DISPUTA'
        ));
        """
        ejecutar_ddl_seguro(db.session, ddl_historial, "Actualizar restricción CK_Historial_Tipo en dbo.Historial_Movimientos_Puntos")

        # 4. Crear Tabla 12: dbo.Ofertas_Trueque
        print("\n--- PASO 4: Crear Tabla 12 dbo.Ofertas_Trueque ---")
        ddl_ofertas = """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Ofertas_Trueque')
        BEGIN
            CREATE TABLE dbo.Ofertas_Trueque (
                id_oferta_trueque INT IDENTITY(1,1) PRIMARY KEY,
                id_usuario_ofertante INT NOT NULL CONSTRAINT FK_Ofertas_UsuarioOfertante FOREIGN KEY REFERENCES dbo.Usuarios(id_usuario),
                id_usuario_receptor INT NOT NULL CONSTRAINT FK_Ofertas_UsuarioReceptor FOREIGN KEY REFERENCES dbo.Usuarios(id_usuario),
                id_oferta_padre INT NULL CONSTRAINT FK_Ofertas_OfertaPadre FOREIGN KEY REFERENCES dbo.Ofertas_Trueque(id_oferta_trueque),
                mensaje_propuesta NVARCHAR(500) NULL,
                puntos_totales_ofrecidos INT NOT NULL DEFAULT 0,
                puntos_totales_solicitados INT NOT NULL DEFAULT 0,
                estado_oferta NVARCHAR(25) NOT NULL DEFAULT 'PENDIENTE' CONSTRAINT CK_Ofertas_EstadoValido CHECK (estado_oferta IN ('PENDIENTE', 'ACEPTADA', 'RECHAZADA', 'CANCELADA', 'CONTRAOFERTA')),
                fecha_creacion DATETIME NOT NULL DEFAULT GETDATE(),
                fecha_resolucion DATETIME NULL
            );
            CREATE INDEX IX_Ofertas_Ofertante ON dbo.Ofertas_Trueque(id_usuario_ofertante);
            CREATE INDEX IX_Ofertas_Receptor ON dbo.Ofertas_Trueque(id_usuario_receptor);
            CREATE INDEX IX_Ofertas_Estado ON dbo.Ofertas_Trueque(estado_oferta);
        END
        """
        ejecutar_ddl_seguro(db.session, ddl_ofertas, "Crear Tabla 12 dbo.Ofertas_Trueque con índices y claves foráneas")

        # 5. Crear Tabla 13: dbo.Detalle_Articulos_Oferta
        print("\n--- PASO 5: Crear Tabla 13 dbo.Detalle_Articulos_Oferta ---")
        ddl_detalle = """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Detalle_Articulos_Oferta')
        BEGIN
            CREATE TABLE dbo.Detalle_Articulos_Oferta (
                id_detalle_oferta INT IDENTITY(1,1) PRIMARY KEY,
                id_oferta_trueque INT NOT NULL CONSTRAINT FK_DetalleOferta_Oferta FOREIGN KEY REFERENCES dbo.Ofertas_Trueque(id_oferta_trueque) ON DELETE CASCADE,
                id_prenda INT NOT NULL CONSTRAINT FK_DetalleOferta_Prenda FOREIGN KEY REFERENCES dbo.Prendas_Accesorios(id_prenda),
                rol_articulo NVARCHAR(20) NOT NULL CONSTRAINT CK_DetalleOferta_Rol CHECK (rol_articulo IN ('OFRECIDO', 'SOLICITADO')),
                puntos_referencia_momento INT NOT NULL DEFAULT 0
            );
            CREATE INDEX IX_DetalleOferta_Oferta ON dbo.Detalle_Articulos_Oferta(id_oferta_trueque);
            CREATE INDEX IX_DetalleOferta_Prenda ON dbo.Detalle_Articulos_Oferta(id_prenda);
        END
        """
        ejecutar_ddl_seguro(db.session, ddl_detalle, "Crear Tabla 13 dbo.Detalle_Articulos_Oferta con índices y cascada")

        # 6. Crear Tabla 14: dbo.Salas_Chat_Intercambio
        print("\n--- PASO 6: Crear Tabla 14 dbo.Salas_Chat_Intercambio ---")
        ddl_salas = """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Salas_Chat_Intercambio')
        BEGIN
            CREATE TABLE dbo.Salas_Chat_Intercambio (
                id_sala_chat INT IDENTITY(1,1) PRIMARY KEY,
                codigo_sala NVARCHAR(50) NOT NULL CONSTRAINT UQ_SalasChat_Codigo UNIQUE,
                tipo_operacion NVARCHAR(30) NOT NULL CONSTRAINT CK_SalasChat_TipoOperacion CHECK (tipo_operacion IN ('TRUEQUE_INVENTARIO', 'ADQUISICION_PUNTOS')),
                id_oferta_trueque INT NULL CONSTRAINT FK_SalasChat_Oferta FOREIGN KEY REFERENCES dbo.Ofertas_Trueque(id_oferta_trueque),
                id_transaccion_adquisicion INT NULL CONSTRAINT FK_SalasChat_Transaccion FOREIGN KEY REFERENCES dbo.Transacciones_Adquisicion(id_transaccion),
                id_usuario_1 INT NOT NULL CONSTRAINT FK_SalasChat_Usuario1 FOREIGN KEY REFERENCES dbo.Usuarios(id_usuario),
                id_usuario_2 INT NOT NULL CONSTRAINT FK_SalasChat_Usuario2 FOREIGN KEY REFERENCES dbo.Usuarios(id_usuario),
                metodo_entrega NVARCHAR(30) NOT NULL DEFAULT 'POR_DEFINIR' CONSTRAINT CK_SalasChat_MetodoEntrega CHECK (metodo_entrega IN ('POR_DEFINIR', 'ENTREGA_PRESENCIAL', 'ENVIO_DOMICILIO')),
                direccion_envio NVARCHAR(250) NULL,
                ciudad_destino NVARCHAR(100) NULL,
                nombre_receptor_envio NVARCHAR(150) NULL,
                telefono_contacto_envio NVARCHAR(30) NULL,
                empresa_transportadora NVARCHAR(100) NULL,
                numero_guia_rastreo NVARCHAR(100) NULL,
                confirmado_usuario_1 BIT NOT NULL DEFAULT 0,
                confirmado_usuario_2 BIT NOT NULL DEFAULT 0,
                estado_sala NVARCHAR(30) NOT NULL DEFAULT 'ACTIVA' CONSTRAINT CK_SalasChat_Estado CHECK (estado_sala IN ('ACTIVA', 'EN_DISPUTA_AUDITORIA', 'CERRADA_EXITOSA', 'CANCELADA_POR_FRAUDE')),
                fecha_apertura DATETIME NOT NULL DEFAULT GETDATE(),
                fecha_cierre DATETIME NULL
            );
            CREATE INDEX IX_SalasChat_Usuario1 ON dbo.Salas_Chat_Intercambio(id_usuario_1);
            CREATE INDEX IX_SalasChat_Usuario2 ON dbo.Salas_Chat_Intercambio(id_usuario_2);
            CREATE INDEX IX_SalasChat_Estado ON dbo.Salas_Chat_Intercambio(estado_sala);
        END
        """
        ejecutar_ddl_seguro(db.session, ddl_salas, "Crear Tabla 14 dbo.Salas_Chat_Intercambio para logística y chat")

        # 7. Crear Tabla 15: dbo.Mensajes_Chat
        print("\n--- PASO 7: Crear Tabla 15 dbo.Mensajes_Chat ---")
        ddl_mensajes = """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Mensajes_Chat')
        BEGIN
            CREATE TABLE dbo.Mensajes_Chat (
                id_mensaje INT IDENTITY(1,1) PRIMARY KEY,
                id_sala_chat INT NOT NULL CONSTRAINT FK_Mensajes_Sala FOREIGN KEY REFERENCES dbo.Salas_Chat_Intercambio(id_sala_chat) ON DELETE CASCADE,
                id_usuario_emisor INT NOT NULL CONSTRAINT FK_Mensajes_Emisor FOREIGN KEY REFERENCES dbo.Usuarios(id_usuario),
                contenido_mensaje NVARCHAR(1000) NOT NULL,
                ruta_adjunto NVARCHAR(300) NULL,
                es_mensaje_sistema BIT NOT NULL DEFAULT 0,
                leido BIT NOT NULL DEFAULT 0,
                fecha_envio DATETIME NOT NULL DEFAULT GETDATE()
            );
            CREATE INDEX IX_Mensajes_Sala ON dbo.Mensajes_Chat(id_sala_chat);
            CREATE INDEX IX_Mensajes_Emisor ON dbo.Mensajes_Chat(id_usuario_emisor);
            CREATE INDEX IX_Mensajes_Fecha ON dbo.Mensajes_Chat(fecha_envio);
        END
        """
        ejecutar_ddl_seguro(db.session, ddl_mensajes, "Crear Tabla 15 dbo.Mensajes_Chat con soporte de evidencias y sistema")

        # 8. Crear Tabla 16: dbo.Reportes_Comportamiento_Estafa
        print("\n--- PASO 8: Crear Tabla 16 dbo.Reportes_Comportamiento_Estafa ---")
        ddl_reportes = """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Reportes_Comportamiento_Estafa')
        BEGIN
            CREATE TABLE dbo.Reportes_Comportamiento_Estafa (
                id_reporte INT IDENTITY(1,1) PRIMARY KEY,
                id_sala_chat INT NOT NULL CONSTRAINT FK_Reportes_Sala FOREIGN KEY REFERENCES dbo.Salas_Chat_Intercambio(id_sala_chat),
                id_usuario_denunciante INT NOT NULL CONSTRAINT FK_Reportes_Denunciante FOREIGN KEY REFERENCES dbo.Usuarios(id_usuario),
                id_usuario_denunciado INT NOT NULL CONSTRAINT FK_Reportes_Denunciado FOREIGN KEY REFERENCES dbo.Usuarios(id_usuario),
                categoria_reporte NVARCHAR(50) NOT NULL CONSTRAINT CK_Reportes_Categoria CHECK (categoria_reporte IN ('INTENTO_ESTAFA', 'ARTICULO_FALSIFICADO_O_DISTINTO', 'NO_ENVIO_O_INCUMPLIMIENTO', 'LENGUAJE_OFENSIVO_O_ACOSO', 'SOLICITUD_DINERO_EXTERNO')),
                descripcion_hechos NVARCHAR(1500) NOT NULL,
                ruta_evidencia_reporte NVARCHAR(300) NULL,
                estado_reporte NVARCHAR(30) NOT NULL DEFAULT 'PENDIENTE_REVISION' CONSTRAINT CK_Reportes_Estado CHECK (estado_reporte IN ('PENDIENTE_REVISION', 'EN_INVESTIGACION', 'RESUELTO_CON_SANCION', 'DESESTIMADO')),
                id_admin_revisor INT NULL CONSTRAINT FK_Reportes_AdminRevisor FOREIGN KEY REFERENCES dbo.Usuarios(id_usuario),
                dictamen_administrador NVARCHAR(1000) NULL,
                accion_aplicada NVARCHAR(100) NULL,
                fecha_reporte DATETIME NOT NULL DEFAULT GETDATE(),
                fecha_resolucion DATETIME NULL
            );
            CREATE INDEX IX_Reportes_Sala ON dbo.Reportes_Comportamiento_Estafa(id_sala_chat);
            CREATE INDEX IX_Reportes_Estado ON dbo.Reportes_Comportamiento_Estafa(estado_reporte);
        END
        """
        ejecutar_ddl_seguro(db.session, ddl_reportes, "Crear Tabla 16 dbo.Reportes_Comportamiento_Estafa para auditoría y sanciones")

        # 9. Actualizar Función SQL dbo.fn_CalcularPuntosPrenda
        print("\n--- PASO 9: Actualizar Función SQL dbo.fn_CalcularPuntosPrenda ---")
        ddl_funcion = """
        CREATE OR ALTER FUNCTION dbo.fn_CalcularPuntosPrenda(
            @id_categoria INT,
            @id_material INT,
            @id_estado_aspecto INT,
            @id_nivel_utilidad INT
        )
        RETURNS INT
        AS
        BEGIN
            DECLARE @puntaje_base INT = 0;
            DECLARE @factor_mat DECIMAL(5,2) = 1.0;
            DECLARE @bono_mat INT = 0;
            DECLARE @factor_asp DECIMAL(4,2) = 1.0;
            DECLARE @bono_uti INT = 0;
            DECLARE @resultado INT = 0;

            SELECT @puntaje_base = ISNULL(puntaje_base, 0) FROM dbo.Categorias_Prenda WHERE id_categoria = @id_categoria;
            SELECT @factor_mat = ISNULL(factor_multiplicador, 1.0), @bono_mat = ISNULL(bono_puntos_material, 0) FROM dbo.Materiales WHERE id_material = @id_material;
            SELECT @factor_asp = ISNULL(factor_conservacion, 1.0) FROM dbo.Estados_Aspecto WHERE id_estado_aspecto = @id_estado_aspecto;
            SELECT @bono_uti = ISNULL(bono_puntos, 0) FROM dbo.Niveles_Utilidad WHERE id_nivel_utilidad = @id_nivel_utilidad;

            SET @resultado = ROUND(((@puntaje_base * @factor_mat) + @bono_mat) * @factor_asp + @bono_uti, 0);
            IF @resultado < 1 SET @resultado = 1;
            RETURN @resultado;
        END;
        """
        ejecutar_ddl_seguro(db.session, ddl_funcion, "Actualizar función escalar SQL dbo.fn_CalcularPuntosPrenda con fórmula de redondeo")

        # 10. Verificación y Auditoría Final de las 16 Tablas y Materiales
        print("\n--- PASO 10: Auditoría y Verificación de Integridad ---")
        consulta_tablas = text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_CATALOG = 'DB_IntercambioRopa'
            ORDER BY TABLE_NAME;
        """)
        tablas_actuales = [fila[0] for fila in db.session.execute(consulta_tablas).fetchall()]
        
        tablas_requeridas = [
            'Roles_Usuario',
            'Usuarios',
            'Categorias_Prenda',
            'Materiales',
            'Estados_Aspecto',
            'Niveles_Utilidad',
            'Prendas_Accesorios',
            'Multimedia_Prenda',
            'Solicitudes_Aprobacion_Material',
            'Transacciones_Adquisicion',
            'Historial_Movimientos_Puntos',
            'Ofertas_Trueque',
            'Detalle_Articulos_Oferta',
            'Salas_Chat_Intercambio',
            'Mensajes_Chat',
            'Reportes_Comportamiento_Estafa'
        ]

        print(f"\n[INFO] Total de tablas encontradas en DB_IntercambioRopa: {len(tablas_actuales)}")
        todas_presentes = True
        for t in tablas_requeridas:
            if t in tablas_actuales:
                print(f"  [+] Tabla activa: dbo.{t}")
            else:
                print(f"  [-] FALTA TABLA: dbo.{t}")
                todas_presentes = False

        # Conteo de materiales auténticos
        conteo_materiales = db.session.execute(text("SELECT COUNT(*) FROM dbo.Materiales WHERE activo = 1")).scalar()
        print(f"\n[INFO] Materiales activos en catálogo: {conteo_materiales} (Esperados: 55)")

        # Prueba de la función fn_CalcularPuntosPrenda
        puntos_calc = db.session.execute(text("SELECT dbo.fn_CalcularPuntosPrenda(1, 1, 1, 1)")).scalar()
        print(f"[INFO] Prueba de fn_CalcularPuntosPrenda(1, 1, 1, 1) -> {puntos_calc} puntos calculados por SQL Server")

        if todas_presentes and conteo_materiales == 55 and puntos_calc is not None:
            print("\n" + "=" * 80)
            print(" ¡ÉXITO TOTAL! BASE DE DATOS ACTUALIZADA A v3.0 (16 TABLAS OPERATIVAS)")
            print("=" * 80)
            return True
        else:
            print("\n[ADVERTENCIA] La verificación detectó discrepancias. Revisa los mensajes anteriores.")
            return False

if __name__ == '__main__':
    exito = actualizar_base_datos()
    sys.exit(0 if exito else 1)
