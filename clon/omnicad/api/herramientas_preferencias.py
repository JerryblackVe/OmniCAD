"""Preferencias autorizadas, con QSettings cargado solo al usarse."""
import os

from .. import NOMBRE_APP
from .errores import error
from .registro import herramienta

# shortcut: catálogo de la UI replicado porque ui/preferencias importa QtWidgets; extraerlo a un módulo
# compartido cuando se autorice editar la UI. test_preferencias_coinciden_con_la_ventana detecta desvíos.
_OPCIONES = {
    "general/raton": ("fusion", ["omnicad", "fusion", "tinkercad"]),
    "general/invertir_zoom": (False, [False, True]),
    "general/camara": ("perspectiva", ["perspectiva", "ortografica", "persp_orto_caras"]),
    "general/tipo_orbita": ("libre", ["libre", "restringida"]),
    "general/auto_mirar_boceto": (True, [False, True]),
    "general/tamano_viewcube": ("automatico", ["pequeno", "automatico", "grande"]),
    "general/info_herramientas": (True, [False, True]),
    "general/autoguardado_min": (1, list(range(1, 61))),
    "material/aspecto": ("acero", ["acero", "paleta"]),
    "graficos/preset": ("personalizar", ["rendimiento", "equilibrado", "calidad", "personalizar"]),
    "graficos/detalle": ("automatico", ["automatico", "bajo", "medio", "alto"]),
    "graficos/dinamico": (True, [False, True]),
    "graficos/fps_minimo": (30, [15, 20, 30, 45, 60]),
    "graficos/limite_fps": (0, [0, 60, 30, 15]),
    "graficos/luces": ("una", ["una", "tres"]),
    "graficos/indicador_giro": (True, [False, True]),
    "unidades/precision": (3, list(range(6))),
    "unidades/precision_angular": (1, list(range(4))),
    "unidades/ocultar_ceros": (True, [False, True]),
    "vista/efecto_cupula": (True, [False, True]),
    "vista/efecto_suelo": (False, [False, True]),
    "vista/efecto_sombra_suelo": (False, [False, True]),
    "vista/efecto_reflejo": (False, [False, True]),
    "vista/efecto_aa": (True, [False, True]),
    "timeline/color_componente": (False, [False, True]),
}
_EFECTOS_BASE = {"vista/efecto_cupula": True, "vista/efecto_suelo": False,
                 "vista/efecto_sombra_suelo": False, "vista/efecto_reflejo": False}
_PRESETS = {
    "rendimiento": {**_EFECTOS_BASE, "vista/efecto_aa": False, "graficos/detalle": "bajo", "graficos/dinamico": True},
    "equilibrado": {**_EFECTOS_BASE, "vista/efecto_aa": True, "graficos/detalle": "automatico", "graficos/dinamico": True},
    "calidad": {**_EFECTOS_BASE, "vista/efecto_suelo": True, "vista/efecto_sombra_suelo": True,
                "vista/efecto_aa": True, "graficos/detalle": "alto", "graficos/dinamico": False},
}


def _ajustes():
    """Los ajustes de la aplicación. Las pruebas los redirigen a un .ini con OMNICAD_AJUSTES_INI; un agente no puede
    elegir el archivo (escribiría un .ini ajeno)."""
    from PySide6.QtCore import QSettings
    ruta = os.environ.get("OMNICAD_AJUSTES_INI")
    return QSettings(ruta, QSettings.IniFormat) if ruta else QSettings(NOMBRE_APP, NOMBRE_APP)


def _exigir_clave(clave):
    if clave not in _OPCIONES:
        raise error("INVALID_ARGUMENTS", f"La preferencia «{clave}» no está autorizada: no se permiten permisos "
                    "de agentes, motor geométrico, temas, rutas ni claves fuera de la lista blanca.")


def _valor(ajustes, clave):
    defecto = _OPCIONES[clave][0]
    valor = ajustes.value(clave, defecto)
    if isinstance(defecto, bool):
        return valor if isinstance(valor, bool) else str(valor).lower() in ("true", "1")
    if isinstance(defecto, int):
        try:
            return int(valor)
        except (TypeError, ValueError):
            return defecto
    return str(valor)


@herramienta("get_preferences", "documento", "Consulta las preferencias autorizadas, sus valores por defecto y opciones válidas.")
def get_preferences(sesion, keys: list[str] | None = None):
    """
    keys: claves a consultar; omitido devuelve toda la lista blanca de preferencias.
    """
    claves = list(_OPCIONES) if keys is None else keys
    for clave in claves:
        _exigir_clave(clave)
    ajustes = _ajustes()
    return {"preferences": [{"key": k, "value": _valor(ajustes, k), "default": _OPCIONES[k][0],
                             "options": list(_OPCIONES[k][1])} for k in claves]}


@herramienta("set_preference", "documento", "Valida y guarda una preferencia autorizada. No modifica el documento "
             "ni entra en deshacer; los ajustes se usan cuando la aplicación los relee.", modifica=True, transaccion=False)
def set_preference(sesion, key: str, value: str | int | bool):
    """
    key: clave autorizada devuelta por get_preferences; permisos, motor, temas y rutas están prohibidos.
    value: valor del tipo y de las opciones indicados por get_preferences.
    """
    _exigir_clave(key)
    defecto, opciones = _OPCIONES[key]
    if type(value) is not type(defecto) or value not in opciones:
        raise error("INVALID_ARGUMENTS", f"Valor inválido para «{key}»: opciones válidas {opciones}.")
    ajustes = _ajustes()
    cambios = {key: value}
    if key == "graficos/preset" and value in _PRESETS:
        cambios.update(_PRESETS[value])
    else:
        preset = _valor(ajustes, "graficos/preset")
        if preset in _PRESETS and key in _PRESETS[preset] and value != _PRESETS[preset][key]:
            cambios["graficos/preset"] = "personalizar"
    for clave, valor in cambios.items():
        ajustes.setValue(clave, valor)
    ajustes.sync()
    if ajustes.status() != ajustes.Status.NoError:
        raise error("FILE_ERROR", "No se pudieron guardar las preferencias.")
    return {"key": key, "value": _valor(ajustes, key), "updated": cambios}
