"""
Pruebas Automatizadas: Publicación de Prendas, 7 Atributos y Flujo de Moderación
Valida la acreditación inmediata (Grupos A-E) vs la retención preventiva de joyas (Grupo F).
"""

import uuid
from app import db
from app.models.usuario import Usuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.solicitud_aprobacion_material import SolicitudAprobacionMaterial
from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos
from app.services.moderacion_service import ModeracionService


def test_publicacion_prenda_acreditacion_inmediata(cliente_http, aplicacion, imagen_prueba_bytes):
    """
    Verifica que la publicación de una prenda común acredite puntos inmediatamente
    y registre el asiento contable CREDITO_PUBLICACION en el Kardex.
    """
    cliente_http.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'carlos.restrepo@correo.com',
        'contrasena': 'Usuario1234*'
    })

    titulo_unico = f"Chaqueta Algodón Test {uuid.uuid4().hex[:6]}"
    datos_publicacion = {
        'titulo_publicacion': titulo_unico,
        'id_categoria': 1,
        'id_material': 10,
        'medida_largo_cm': '72.0',
        'talla': 'L',
        'procedencia': 'Zara Man España',
        'id_estado_aspecto': 2,
        'id_nivel_utilidad': 1,
        'motivo_cambio': 'Cambio por otra prenda exterior de temporada.',
        'archivos_multimedia': imagen_prueba_bytes
    }

    with aplicacion.app_context():
        u_antes = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        saldo_disp_antes = u_antes.saldo_puntos_disponibles

    res = cliente_http.post('/prendas/publicar', data=datos_publicacion, follow_redirects=True)
    assert res.status_code == 200

    with aplicacion.app_context():
        prenda = PrendaAccesorio.query.filter_by(titulo_publicacion=titulo_unico).first()
        assert prenda is not None
        assert prenda.estado_publicacion == 'PUBLICADA'
        assert prenda.archivos_multimedia.count() >= 1

        u_despues = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        assert u_despues.saldo_puntos_disponibles == saldo_disp_antes + prenda.puntos_valoracion

        # Verificar Kardex
        kardex = HistorialMovimientosPuntos.query.filter_by(
            id_prenda_referencia=prenda.id_prenda,
            tipo_movimiento='CREDITO_PUBLICACION'
        ).first()
        assert kardex is not None
        assert kardex.cantidad_puntos == prenda.puntos_valoracion

        # Teardown: Limpieza para no dejar artículos de prueba en BD
        db.session.delete(kardex)
        for media in prenda.archivos_multimedia:
            db.session.delete(media)
        db.session.delete(prenda)
        u_despues.saldo_puntos_disponibles = saldo_disp_antes
        db.session.commit()


def test_publicacion_joyeria_y_aprobacion_moderador(cliente_http, aplicacion, imagen_prueba_bytes):
    """
    Verifica que la publicación de una joya retenga los puntos preventivamente,
    genere una orden en Solicitudes_Aprobacion_Material y se apruebe atómicamente.
    """
    cliente_http.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'carlos.restrepo@correo.com',
        'contrasena': 'Usuario1234*'
    })

    titulo_joya_unico = f"Cadena Plata Ley 925 Test {uuid.uuid4().hex[:6]}"
    datos_joya = {
        'titulo_publicacion': titulo_joya_unico,
        'id_categoria': 7,
        'id_material': 46,
        'medida_largo_cm': '55.0',
        'talla': 'Única',
        'procedencia': 'Taller Joyero San Eloy',
        'id_estado_aspecto': 1,
        'id_nivel_utilidad': 2,
        'motivo_cambio': 'Prefiero intercambiarla por ropa de vestir casual.',
        'archivos_multimedia': imagen_prueba_bytes
    }

    with aplicacion.app_context():
        u_antes = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        saldo_disp_antes = u_antes.saldo_puntos_disponibles
        saldo_ret_antes = u_antes.saldo_puntos_retenidos

    res = cliente_http.post('/prendas/publicar', data=datos_joya, follow_redirects=True)
    assert res.status_code == 200

    with aplicacion.app_context():
        joya = PrendaAccesorio.query.filter_by(titulo_publicacion=titulo_joya_unico).first()
        assert joya is not None
        assert joya.estado_publicacion == 'PENDIENTE_APROBACION'

        # Puntos retenidos aumentaron, disponibles se mantuvieron intactos
        u_despues = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        assert u_despues.saldo_puntos_disponibles == saldo_disp_antes
        assert u_despues.saldo_puntos_retenidos == saldo_ret_antes + joya.puntos_valoracion

        # Verificar solicitud de aprobación
        solicitud = SolicitudAprobacionMaterial.query.filter_by(id_prenda=joya.id_prenda).first()
        assert solicitud is not None
        assert solicitud.estado_revision == 'PENDIENTE'

        # Ejecutar aprobación por el moderador
        admin = Usuario.query.filter_by(correo_electronico='admin@modacircular.com').first()
        sol_aprobada = ModeracionService.aprobar_solicitud(
            id_solicitud=solicitud.id_solicitud_aprobacion,
            id_usuario_revisor=admin.id_usuario,
            observaciones='Sello 925 verificado correctamente.'
        )

        assert sol_aprobada.estado_revision == 'APROBADA'
        assert joya.estado_publicacion == 'PUBLICADA'

        # Los puntos se transfirieron de retenidos a disponibles
        u_final = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        assert u_final.saldo_puntos_disponibles == saldo_disp_antes + joya.puntos_valoracion
        assert u_final.saldo_puntos_retenidos == saldo_ret_antes

        # Asiento contable CREDITO_APROBACION_JOYA
        kardex_joya = HistorialMovimientosPuntos.query.filter_by(
            id_prenda_referencia=joya.id_prenda,
            tipo_movimiento='CREDITO_APROBACION_JOYA'
        ).first()
        assert kardex_joya is not None
        assert kardex_joya.cantidad_puntos == joya.puntos_valoracion

        # Teardown: Limpieza para no dejar joyas de prueba en BD
        db.session.delete(kardex_joya)
        db.session.delete(sol_aprobada)
        for media in joya.archivos_multimedia:
            db.session.delete(media)
        db.session.delete(joya)
        u_final.saldo_puntos_disponibles = saldo_disp_antes
        u_final.saldo_puntos_retenidos = saldo_ret_antes
        db.session.commit()
