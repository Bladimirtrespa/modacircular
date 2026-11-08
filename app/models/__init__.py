"""
Paquete de Modelos ORM de SQLAlchemy
Exporta las 16 entidades del modelo relacional integral de DB_IntercambioRopa (v3.0).
"""

from app.models.rol_usuario import RolUsuario
from app.models.usuario import Usuario
from app.models.categoria_prenda import CategoriaPrenda
from app.models.material import Material
from app.models.estado_aspecto import EstadoAspecto
from app.models.nivel_utilidad import NivelUtilidad
from app.models.prenda_accesorio import PrendaAccesorio
from app.models.multimedia_prenda import MultimediaPrenda
from app.models.solicitud_aprobacion_material import SolicitudAprobacionMaterial
from app.models.transaccion_adquisicion import TransaccionAdquisicion
from app.models.historial_movimientos_puntos import HistorialMovimientosPuntos
from app.models.oferta_trueque import OfertaTrueque
from app.models.detalle_articulo_oferta import DetalleArticuloOferta
from app.models.sala_chat_intercambio import SalaChatIntercambio
from app.models.mensaje_chat import MensajeChat
from app.models.reporte_comportamiento_estafa import ReporteComportamientoEstafa

__all__ = [
    'RolUsuario',
    'Usuario',
    'CategoriaPrenda',
    'Material',
    'EstadoAspecto',
    'NivelUtilidad',
    'PrendaAccesorio',
    'MultimediaPrenda',
    'SolicitudAprobacionMaterial',
    'TransaccionAdquisicion',
    'HistorialMovimientosPuntos',
    'OfertaTrueque',
    'DetalleArticuloOferta',
    'SalaChatIntercambio',
    'MensajeChat',
    'ReporteComportamientoEstafa'
]
