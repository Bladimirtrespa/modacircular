"""
Pruebas Automatizadas: Vitrina de Trueque e Inventario Dual (Micro-paso 3)
Valida la publicación de ítems en modalidad INVENTARIO_TRUEQUE (sin puntos inmediatos),
la visualización de la vitrina de trueque directo y la conversión transaccional a puntos con Kardex.
"""

import uuid
from app import db
from app.models.usuario import Usuario
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos


def test_publicacion_inventario_y_conversion_a_puntos(cliente_http, aplicacion, imagen_prueba_bytes):
    """
    1. Publica un artículo con modalidad INVENTARIO_TRUEQUE.
    2. Comprueba que el estado sea EN_INVENTARIO y que el saldo no aumente.
    3. Inspecciona la vitrina del usuario vía HTTP GET.
    4. Ejecuta la conversión a puntos vía POST y valida el asiento CREDITO_CONVERSION_INVENTARIO.
    """
    # Iniciar sesión con Carlos Mario Restrepo
    cliente_http.post('/autenticacion/iniciar-sesion', data={
        'correo_electronico': 'carlos.restrepo@correo.com',
        'contrasena': 'Usuario1234*'
    })

    with aplicacion.app_context():
        u_inicial = Usuario.query.filter_by(correo_electronico='carlos.restrepo@correo.com').first()
        saldo_inicial = u_inicial.saldo_puntos_disponibles
        id_carlos = u_inicial.id_usuario

    titulo_item = f"Campera Denim Trueque Test {uuid.uuid4().hex[:6]}"
    datos_publicacion = {
        'titulo_publicacion': titulo_item,
        'id_categoria': 1,
        'id_material': 10,
        'medida_largo_cm': '70.0',
        'talla': 'M',
        'procedencia': 'Levi Strauss & Co',
        'id_estado_aspecto': 1,
        'id_nivel_utilidad': 1,
        'motivo_cambio': 'Disponible exclusivamente para trueque por otra prenda vintage.',
        'modalidad_publicacion': 'INVENTARIO_TRUEQUE',
        'archivos_multimedia': imagen_prueba_bytes
    }

    # 1. Publicar en inventario
    res_pub = cliente_http.post('/prendas/publicar', data=datos_publicacion, follow_redirects=True)
    assert res_pub.status_code == 200

    with aplicacion.app_context():
        prenda = PrendaAccesorio.query.filter_by(titulo_publicacion=titulo_item).first()
        assert prenda is not None
        assert prenda.estado_publicacion == 'EN_INVENTARIO'
        assert prenda.modalidad_publicacion == 'INVENTARIO_TRUEQUE'
        id_prenda = prenda.id_prenda
        puntos_prenda = prenda.puntos_valoracion

        # Saldo NO debe haber cambiado
        u_actual = Usuario.query.get(id_carlos)
        assert u_actual.saldo_puntos_disponibles == saldo_inicial

    # 2. Consultar la vitrina pública/privada de Carlos
    res_vitrina = cliente_http.get(f'/inventario/usuario/{id_carlos}')
    assert res_vitrina.status_code == 200
    assert titulo_item.encode('utf-8') in res_vitrina.data

    # 3. Convertir el ítem de inventario a puntos
    res_conv = cliente_http.post(f'/inventario/prenda/{id_prenda}/convertir-a-puntos', follow_redirects=True)
    assert res_conv.status_code == 200

    with aplicacion.app_context():
        prenda_conv = PrendaAccesorio.query.get(id_prenda)
        assert prenda_conv.estado_publicacion == 'PUBLICADA'

        u_final = Usuario.query.get(id_carlos)
        assert u_final.saldo_puntos_disponibles == saldo_inicial + puntos_prenda

        # Verificar asiento contable de auditoría
        kardex = HistorialMovimientosPuntos.query.filter_by(
            id_prenda_referencia=id_prenda,
            tipo_movimiento='CREDITO_CONVERSION_INVENTARIO'
        ).first()
        assert kardex is not None
        assert kardex.cantidad_puntos == puntos_prenda

        # Teardown
        db.session.delete(kardex)
        for media in prenda_conv.archivos_multimedia:
            db.session.delete(media)
        db.session.delete(prenda_conv)
        u_final.saldo_puntos_disponibles = saldo_inicial
        db.session.commit()
