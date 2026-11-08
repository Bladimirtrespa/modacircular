"""
Servicio de Dominio: Publicación Transaccional de Prendas y Accesorios
Orquesta de forma atómica (ACID):
1. Validación de los 7 atributos obligatorios y archivos multimedia.
2. Cálculo dinámico de puntos mediante CalculadoraPuntosService.
3. Decisión de bifurcación:
   - Grupos A-E: Acreditación inmediata a saldo_puntos_disponibles y asiento en Kardex.
   - Grupo F: Retención preventiva en saldo_puntos_retenidos y orden en Solicitudes_Aprobacion_Material.
4. Persistencia física de archivos multimedia y registro en Multimedia_Prenda.
"""

import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

from app import db
from app.models.usuario import Usuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.multimedia_prenda import MultimediaPrenda
from app.models.solicitud_aprobacion_material import SolicitudAprobacionMaterial
from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos
from app.services.calculadora_puntos_service import CalculadoraPuntosService


class PublicacionService:
    """Servicio que encapsula la transacción ACID de creación de publicaciones."""

    EXTENSIONES_IMAGENES = {'jpg', 'jpeg', 'png', 'webp'}
    EXTENSIONES_VIDEOS = {'mp4', 'mov', 'webm'}
    EXTENSIONES_PERMITIDAS = EXTENSIONES_IMAGENES.union(EXTENSIONES_VIDEOS)

    @classmethod
    def procesar_publicacion(cls, usuario: Usuario, formulario, archivos_subidos) -> PrendaAccesorio:
        """
        Ejecuta la publicación completa dentro de una transacción ACID en SQL Server.
        
        :param usuario: Entidad Usuario propietario autenticado.
        :param formulario: Instancia validada de FormularioPublicacionPrenda.
        :param archivos_subidos: Lista de objetos FileStorage subidos.
        :return: Entidad PrendaAccesorio persistida.
        :raises ValueError: Si falla alguna regla de validación de negocio o archivos.
        """
        # 1. Validar que se haya adjuntado al menos un archivo válido
        archivos_validos = [f for f in archivos_subidos if f and f.filename and f.filename.strip()]
        if not archivos_validos:
            raise ValueError("Debes subir al menos una fotografía o video corto de evidencia del artículo.")

        for archivo in archivos_validos:
            nombre = secure_filename(archivo.filename)
            extension = nombre.rsplit('.', 1)[-1].lower() if '.' in nombre else ''
            if extension not in cls.EXTENSIONES_PERMITIDAS:
                raise ValueError(f"El archivo '{archivo.filename}' tiene una extensión no permitida. Formatos válidos: {', '.join(cls.EXTENSIONES_PERMITIDAS)}")

        # 2. Calcular los puntos y evaluar requerimiento de moderación (CERO HARDCODING)
        calculo = CalculadoraPuntosService.calcular_puntos(
            id_categoria=formulario.id_categoria.data,
            id_material=formulario.id_material.data,
            id_estado_aspecto=formulario.id_estado_aspecto.data,
            id_nivel_utilidad=formulario.id_nivel_utilidad.data
        )

        puntos_asignados = calculo['puntos']
        requiere_aprobacion = calculo['requiere_aprobacion_especial']
        descripcion_auditoria = calculo['descripcion_auditoria']

        archivos_guardados_en_disco = []

        # Extraer modalidad de publicación (v3.0): SOLO_PUNTOS, INVENTARIO_TRUEQUE o AMBOS
        modalidad = 'SOLO_PUNTOS'
        if hasattr(formulario, 'modalidad_publicacion') and formulario.modalidad_publicacion.data:
            modalidad = formulario.modalidad_publicacion.data.strip().upper()
        if modalidad not in ('SOLO_PUNTOS', 'INVENTARIO_TRUEQUE', 'AMBOS'):
            modalidad = 'SOLO_PUNTOS'

        try:
            # 3. Transacción ACID: Definir estado inicial y manejo de billetera dual
            saldo_anterior = usuario.saldo_puntos_disponibles
            saldo_posterior = usuario.saldo_puntos_disponibles

            if modalidad == 'INVENTARIO_TRUEQUE':
                # Modalidad Inventario: No acredita puntos de inmediato a la billetera.
                # Queda en estado EN_INVENTARIO disponible para negociaciones de trueque directo.
                estado_publicacion = 'EN_INVENTARIO'
            elif requiere_aprobacion:
                # REGLA GRUPO F (Joyería / Metales Preciosos): Retención preventiva
                estado_publicacion = 'PENDIENTE_APROBACION'
                usuario.saldo_puntos_retenidos += puntos_asignados
            else:
                # REGLA GRUPOS A-E (Textiles, Fibras, Cueros, Accesorios estándar): Acreditación inmediata
                estado_publicacion = 'PUBLICADA'
                usuario.saldo_puntos_disponibles += puntos_asignados
                saldo_posterior = usuario.saldo_puntos_disponibles

            # Crear el registro de la prenda con los 7 atributos obligatorios
            nueva_prenda = PrendaAccesorio(
                id_usuario_propietario=usuario.id_usuario,
                id_categoria=formulario.id_categoria.data,
                id_material=formulario.id_material.data,
                id_estado_aspecto=formulario.id_estado_aspecto.data,
                id_nivel_utilidad=formulario.id_nivel_utilidad.data,
                titulo_publicacion=formulario.titulo_publicacion.data.strip(),
                medida_largo_cm=float(formulario.medida_largo_cm.data),
                talla=formulario.talla.data.strip(),
                procedencia=formulario.procedencia.data.strip(),
                motivo_cambio=formulario.motivo_cambio.data.strip(),
                puntos_valoracion=puntos_asignados,
                modalidad_publicacion=modalidad,
                estado_publicacion=estado_publicacion,
                fecha_publicacion=datetime.utcnow()
            )

            db.session.add(nueva_prenda)
            db.session.flush()  # Obtiene nueva_prenda.id_prenda para las relaciones hijas

            # 4. Bifurcación de Auditoría y Flujo de Moderación
            if modalidad == 'INVENTARIO_TRUEQUE':
                # En inventario no se emite crédito contable aún
                pass
            elif requiere_aprobacion:
                # Crear orden en Solicitudes_Aprobacion_Material
                solicitud_aprobacion = SolicitudAprobacionMaterial(
                    id_prenda=nueva_prenda.id_prenda,
                    estado_revision='PENDIENTE',
                    fecha_solicitud=datetime.utcnow(),
                    observaciones_revisor=None
                )
                db.session.add(solicitud_aprobacion)
            else:
                # Registrar asiento contable inmediato en Historial_Movimientos_Puntos (Kardex)
                movimiento = HistorialMovimientosPuntos(
                    id_usuario=usuario.id_usuario,
                    id_prenda_referencia=nueva_prenda.id_prenda,
                    tipo_movimiento='CREDITO_PUBLICACION',
                    cantidad_puntos=puntos_asignados,
                    saldo_anterior=saldo_anterior,
                    saldo_posterior=saldo_posterior,
                    descripcion_auditoria=descripcion_auditoria,
                    fecha_movimiento=datetime.utcnow()
                )
                db.session.add(movimiento)

            # 5. Guardado físico de archivos multimedia y registro relacional
            carpeta_base = current_app.config['CARPETA_SUBIDAS']
            es_primero = True

            for archivo in archivos_validos:
                nombre_seguro = secure_filename(archivo.filename)
                extension = nombre_seguro.rsplit('.', 1)[-1].lower()
                es_video = extension in cls.EXTENSIONES_VIDEOS
                tipo_archivo = 'VIDEO' if es_video else 'FOTO'
                
                subcarpeta = 'videos' if es_video else 'imagenes'
                nombre_unico = f"prenda_{nueva_prenda.id_prenda}_{uuid.uuid4().hex[:10]}.{extension}"
                ruta_fisica = os.path.join(carpeta_base, subcarpeta, nombre_unico)

                archivo.save(ruta_fisica)
                archivos_guardados_en_disco.append(ruta_fisica)

                # Ruta relativa para ser consumida desde Jinja2 / navegador
                ruta_relativa = f"uploads/{subcarpeta}/{nombre_unico}"

                multimedia = MultimediaPrenda(
                    id_prenda=nueva_prenda.id_prenda,
                    tipo_archivo=tipo_archivo,
                    ruta_archivo=ruta_relativa,
                    es_portada=es_primero and not es_video,
                    fecha_carga=datetime.utcnow()
                )
                db.session.add(multimedia)
                if not es_video:
                    es_primero = False

            # Confirmar toda la transacción ACID
            db.session.commit()
            return nueva_prenda

        except Exception as error_transaccion:
            db.session.rollback()
            # Limpieza preventiva de archivos guardados en caso de fallo en BD
            for ruta in archivos_guardados_en_disco:
                if os.path.exists(ruta):
                    try:
                        os.remove(ruta)
                    except OSError:
                        pass
            raise error_transaccion
