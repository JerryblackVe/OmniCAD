# -*- coding: utf-8 -*-
"""
Errores de la API con `error_kind` estable.

Toda falla que ve un agente es un `ErrorAPI(error_kind, mensaje, pistas)`:
  - `error_kind`: código fijo en inglés MAYÚSCULAS (no cambia entre versiones; el agente decide con él).
  - `mensaje`: qué pasó, en español (sale del núcleo cuando lo hay).
  - `pistas`: 1-3 acciones concretas para corregirlo.

`traducir(exc)` convierte las excepciones del núcleo y `desde_mensaje(texto)` los mensajes de un
`ResultadoPaso("error")`, que solo traen texto: por eso la tabla busca por patrón del mensaje.
"""
import re

from ..io_archivos.abrir_externo import ErrorAbrir
from ..io_archivos.exportar import ErrorExportacion
from ..io_archivos.puente_fusion import ErrorPuenteFusion
from ..io_archivos.proyecto import ErrorProyecto
from ..nucleo.geometria import ErrorGeometria
from ..restricciones import ErrorBoceto
from ..timeline.documento import ErrorDocumento
from ..timeline.operaciones import ErrorOperacion
from ..timeline.parametros import ErrorExpresion


class ErrorAPI(Exception):
    def __init__(self, error_kind, mensaje, pistas=()):
        super().__init__(mensaje)
        self.error_kind, self.mensaje, self.pistas = error_kind, mensaje, list(pistas)

    def a_dict(self):
        return {"ok": False, "error_kind": self.error_kind, "mensaje": self.mensaje, "pistas": self.pistas}


_VER_TIMELINE = "get_timeline lista los pasos con su id, nombre y estado."
_VER_PARAMETROS = "get_parameters lista los parámetros con su expresión y valor."

# Pistas por error_kind (las herramientas pueden sumar pistas propias, p. ej. la lista de nombres válidos).
PISTAS = {
    "INVALID_ARGUMENTS": ["Revisá nombres y tipos de los argumentos contra el esquema de la herramienta."],
    "UNKNOWN_TOOL": ["catalogo() o la lista de herramientas del MCP dice qué nombres existen."],
    "FEATURE_NOT_FOUND": ["Usá el id (p. ej. 'op3') o el nombre exacto del paso.", _VER_TIMELINE],
    "BODY_NOT_FOUND": ["get_scene_info lista los cuerpos con su id y nombre.",
                       "El cuerpo puede no existir en ese punto del timeline (borrado, suprimido o después del marcador)."],
    "PARAMETER_NOT_FOUND": [_VER_PARAMETROS, "Para uno nuevo usá create_parameter."],
    "AMBIGUOUS_REFERENCE": ["Hay más de uno con ese nombre: usá el id."],
    "PARAMETER_EXISTS": ["Para cambiarlo usá set_parameter.", _VER_PARAMETROS],
    "INVALID_PARAMETER_NAME": ["Un nombre válido empieza con letra o '_' y sigue con letras, números o '_' (p. ej. 'ancho_placa').",
                               "No uses unidades ni funciones como nombre (mm, deg, sin, pi…)."],
    "PARAMETER_IN_USE": ["Cambiá primero las expresiones de los pasos o parámetros que lo usan.", _VER_PARAMETROS],
    "CIRCULAR_REFERENCE": ["Un parámetro no puede depender de sí mismo, ni directa ni indirectamente."],
    "UNIT_MISMATCH": ["Las longitudes van en mm, cm, m, in o ft; los ángulos en deg, rad o °."],
    "INVALID_EXPRESSION": ["Ejemplos válidos: '10', '10 mm', 'ancho / 2', '2 * radio + 1 mm', '45 deg'.",
                           "Los nombres de la expresión tienen que ser parámetros existentes (get_parameters)."],
    "FEATURE_IN_USE": ["Borrá o editá primero los pasos que la usan.", _VER_TIMELINE],
    "OPERATION_FAILED": ["Revisá los valores del paso (medidas, perfiles, cuerpos objetivo) y probá de nuevo.",
                         "El documento quedó como estaba: no hace falta deshacer."],
    "NOTHING_TO_UNDO": ["No hay cambios para deshacer en este documento."],
    "NOTHING_TO_REDO": ["Solo se puede rehacer justo después de deshacer."],
    "NOTHING_TO_EXPORT": ["Creá al menos un cuerpo antes de exportar (get_scene_info lista los cuerpos)."],
    "FILE_NOT_FOUND": ["Revisá la ruta: el archivo o la carpeta no existen.", "Usá una ruta absoluta."],
    "FILE_EXISTS": ["Pasá overwrite=true (en la CLI: --overwrite) para reemplazarlo, o elegí otra ruta."],
    "PERMISSION_DENIED": ["Elegí una carpeta con permiso de escritura o cerrá el programa que tiene abierto el archivo."],
    "INVALID_FORMAT": ["Formatos de exportación: .stl, .obj, .3mf, .ply, .step/.stp, .iges/.igs, .brep y .dxf "
                       "(patrón plano de chapa).",
                       "Los cuerpos de malla solo se exportan a .stl, .obj, .3mf o .ply."],
    "INVALID_PROJECT": ["El archivo no es un proyecto .omnicad válido o está dañado.",
                        "Si hay un autoguardado (*.autoguardado.omnicad), probá abrir ese."],
    "UNSUPPORTED_FILE_TYPE": ["Se abren .omnicad/.fclone, .step/.stp, .iges/.igs, .stl, .obj, .3mf, .ply, .dxf, "
                              ".brep/.brp, .f3d y .f3z."],
    "IMPORT_FAILED": ["El archivo puede estar dañado o ser de un formato que OpenCascade no lee.",
                      "Probá exportarlo de nuevo desde el programa de origen (STEP AP214 o AP242)."],
    "FUSION_NOT_AVAILABLE": ["Abrí Fusion 360 y verificá que el complemento OmniCADPuente esté en ejecución "
                             "(Utilidades › Complementos, Mayús+S); se instala con «omnicad setup --cliente fusion --aplicar».",
                             "Sin Fusion: abrí el .f3d en Fusion, Archivo › Exportar… como STEP y abrí ese .step con open_document."],
    "FUSION_CONVERSION_FAILED": ["Revisá en Fusion si el archivo abre bien (referencias faltantes, versión más nueva).",
                                 "Alternativa: en Fusion, Archivo › Exportar… como STEP y abrí ese .step con open_document."],
    "FILE_ERROR": ["No se pudo leer o escribir el archivo: revisá la ruta y que haya espacio en el disco."],
    "NOT_FOUND": ["get_scene_info, get_timeline y get_parameters listan lo que existe."],
    "MISSING_PATH": ["El documento todavía no tiene archivo: pasá path."],
    "DOCUMENT_ERROR": [_VER_TIMELINE],
    # --- boceto y sólidos
    "SKETCH_NOT_FOUND": ["get_scene_info lista los bocetos con su id y nombre; create_sketch crea uno.",
                         "Usá el id (p. ej. 'op3') o el nombre exacto del boceto."],
    "PLANE_NOT_FOUND": ["Planos de origen: XY, XZ o YZ.",
                        "Un plano de construcción se pasa por su id o nombre (create_construction_plane lo crea)."],
    "ENTITY_NOT_FOUND": ["get_sketch lista las curvas y los puntos del boceto con sus ids."],
    "INVALID_GEOMETRY": ["Revisá que las medidas sean positivas y que los puntos no coincidan.",
                         "Las coordenadas van en mm sobre el plano del boceto (get_sketch dice cómo se orientan)."],
    "INVALID_CONSTRAINT": ["Tipos: coincident, horizontal, vertical, parallel, perpendicular, equal, tangent, "
                           "concentric, midpoint, fix, collinear, symmetry, curvature.",
                           "get_sketch dice el tipo de cada entidad; cada restricción exige ciertos tipos y orden."],
    "INVALID_DIMENSION": ["Tipos: distance, horizontal, vertical, radius, diameter, angle, offset.",
                          "distance: dos puntos, una línea, punto y línea o dos líneas; radius y diameter: un "
                          "círculo o arco; angle: dos líneas."],
    "SKETCH_OVERCONSTRAINED": ["La restricción o cota choca con las que ya hay: el boceto quedó como estaba.",
                               "get_sketch muestra restricciones, cotas y grados de libertad."],
    "INVALID_SPEC": ["Cada entidad lleva 'type' (line, rectangle, circle, arc, polygon, spline, point, ellipse, "
                     "slot) y sus "
                     "coordenadas; 'id' es opcional y sirve para citarla en constraints y dimensions.",
                     "Citas: 'id', 'id.start', 'id.end', 'id.center' o, en un rectángulo, 'id.bottom/right/top/left'."],
    "PROFILE_NOT_FOUND": ["get_sketch lista los perfiles con su índice, área y centroide.",
                          "profile acepta un índice, una lista de índices, 'all' o 'largest'."],
    "PROFILE_NOT_CLOSED": ["El boceto no tiene regiones cerradas: los extremos de las curvas tienen que coincidir.",
                           "Las líneas de construcción no forman perfiles."],
    "NO_TARGET_BODY": ["join, cut e intersect actúan sobre un cuerpo existente: creá uno antes o usá operation=new_body.",
                       "Con target elegís el cuerpo (id o nombre); sin target se usan los sólidos que toca la herramienta."],
    "INVALID_AXIS": ["axis: 'sketch_x', 'sketch_y', 'x', 'y', 'z' o el id de una línea del boceto (get_sketch)."],
    # --- selectores
    "INVALID_SELECTOR": ["Sintaxis: >Z <Z (más alto/bajo), |Z (paralelo), #Z (perpendicular), +Z -Z (normal), "
                         "|Z~3 (con 3° de tolerancia), %PLANE %CIRCLE (tipo), nearest:[x,y,z]. Se combinan con and, "
                         "or, not y paréntesis.",
                         "get_guide(topic='selectores') tiene ejemplos."],
    "NO_MATCH": ["find_faces / find_edges sin selector listan todo con su tipo y centro.",
                 "Revisá el eje y el tipo: '|Z' en caras es la tapa y la base, '#Z' son las laterales.",
                 "Si están apenas inclinadas (p. ej. tras un desmoldeo), sumá una tolerancia en grados: |Z~3, #Z~3."],
    "STALE_ID": ["Los ids de find_faces / find_edges valen solo hasta el próximo cambio del documento.",
                 "Volvé a llamar find_faces / find_edges, o usá un selector (p. ej. '>Z')."],
    "ELEMENT_NOT_FOUND": ["find_faces / find_edges listan los ids que existen (Cuerpo1/F3 = cara, Cuerpo1/E7 = arista)."],
    "UNSUPPORTED_ELEMENT": ["Hace falta una cara plana o una arista recta para esto.",
                            "find_faces(selector='%PLANE') y find_edges(selector='%LINE') las listan."],
    "REFERENCE_LOST": ["Una cara o arista elegida antes ya no existe: la geometría cambió demasiado.",
                       "Volvé a elegirla con find_faces / find_edges y editá el paso (edit_feature) o rehacelo.",
                       "El documento quedó como estaba."],
    # --- inspección y avanzado
    "NOTHING_TO_RENDER": ["Creá al menos un cuerpo antes de pedir la imagen (get_scene_info lista los cuerpos).",
                          "Si pasaste bodies, revisá que existan y tengan caras."],
    "NOTHING_TO_MEASURE": ["Creá al menos un cuerpo antes de medir (get_scene_info lista los cuerpos)."],
    "UNSUPPORTED_BODY_TYPE": ["Esta herramienta trabaja con sólidos o superficies, no con mallas.",
                              "get_scene_info dice el tipo de cada cuerpo."],
    "UNKNOWN_OPERATION_TYPE": ["list_operation_types lista los tipos válidos.",
                               "describe_operation explica los parámetros de un tipo."],
    "INVALID_RECIPE": ["Pasá una receta como la que devuelve get_recipe (objeto con la lista 'operaciones').",
                       "El documento quedó como estaba."],
    "CODE_ERROR": ["Corregí el código y volvé a llamar: el documento quedó como estaba.",
                   "Tenés definidos api, sesion, doc y llamar(nombre, args); print() sale en stdout."],
    "CODE_TIMEOUT": ["El documento quedó como estaba: no hace falta deshacer.",
                     "Subí timeout (en vivo, como mucho 100 s) o partí el trabajo en llamadas más cortas.",
                     "Si es un bucle sin salida, revisá la condición del while."],
    "TOPIC_NOT_FOUND": ["get_guide sin argumentos devuelve el índice con los temas."],
    "INTERNAL_ERROR": ["Es una falla interna de OmniCAD: el documento no cambió. Probá con otros valores o reportalo."],
    # --- puente en vivo (la app abierta; ver api/protocolo_puente.py)
    "UNAUTHORIZED": ["El token no coincide con el de puente.json: la app se reinició o el archivo es de otra instancia.",
                     "Volvé a leer puente.json (%LOCALAPPDATA%/OmniCAD) y reconectá."],
    "APP_BUSY": ["El usuario está usando un comando, editando un boceto o tiene un diálogo abierto: esperá unos "
                 "segundos o pedile que lo termine, y volvé a llamar.",
                 "Las herramientas que solo leen (get_scene_info, get_viewport_image…) funcionan igual.",
                 "No se aplicó nada: no hace falta deshacer."],
    "APP_NOT_RUNNING": ["Abrí OmniCAD y activá Preferencias › General › «Permitir que agentes IA controlen OmniCAD "
                        "(MCP en vivo)», o arrancalo con «OmniCAD.py --puente».",
                        "Para trabajar sin la ventana, arrancá el servidor MCP con --modo sin_ventana (o auto)."],
    "APP_NOT_RESPONDING": ["OmniCAD no contestó a tiempo: puede estar calculando algo pesado o trabado.",
                           "Revisá la ventana; get_scene_info dice si el último cambio se aplicó."],
    "UNSAVED_CHANGES": ["El documento tiene cambios sin guardar: guardalo antes con save_document, o pasá "
                        "discard=true para descartarlos (en vivo, mejor que decida el usuario).",
                        "No se descartó nada."],
    "LIVE_NOT_ALLOWED": ["En vivo, execute_code corre en la interfaz de OmniCAD: solo se permite si el usuario activa "
                         "Preferencias › General › «Permitir también execute_code en vivo».",
                         "Alternativa: run_operation, apply_recipe y las demás herramientas funcionan en vivo; o usá "
                         "el servidor MCP con --modo sin_ventana."],
    "INVALID_REQUEST": ["Cada línea es un objeto JSON {\"id\", \"token\", \"tool\", \"args\"} terminado en salto de línea."],
    "BRIDGE_ERROR": ["Falló la conexión con la app: se reintenta sola en la próxima llamada.",
                     "get_scene_info dice si el último cambio se aplicó."],
    "NESTED_CHECKS": ["run_checks ya está corriendo más arriba (este proceso lo lanzó él): no se anida, porque cada "
                      "nivel volvería a correr toda la suite y llenaría la memoria.",
                      "En un test, reemplazá los subprocesos (monkeypatch de herramientas_dev._correr)."],
    "DEV_ONLY": ["Esta herramienta trabaja sobre el código fuente (tests, prueba de humo, ventana en otro proceso) y la "
                 "app instalada no lo trae.",
                 "Cloná el repo y usala desde ahí: README › Instalación."],
}

# (clases, patrón del mensaje o None, error_kind). Gana la PRIMERA fila que coincide: lo específico va antes.
_PASO = (ErrorOperacion, ErrorGeometria, ErrorExpresion, ErrorBoceto)
_TABLA = [
    (ErrorDocumento, r"^No existe la operación", "FEATURE_NOT_FOUND"),
    (ErrorDocumento, r"^No se puede eliminar: la usan", "FEATURE_IN_USE"),
    (ErrorDocumento, r"parámetro en uso", "PARAMETER_IN_USE"),
    (ErrorExpresion, r"^Ya existe el parámetro", "PARAMETER_EXISTS"),
    (ErrorExpresion, r"^Nombre de parámetro inválido|palabra reservada", "INVALID_PARAMETER_NAME"),
    (ErrorExpresion, r"^No se puede borrar '.*': lo usan", "PARAMETER_IN_USE"),
    (ErrorExpresion, r"^Referencia circular", "CIRCULAR_REFERENCE"),
    (ErrorExpresion, r"^La unidad '.*' es de", "UNIT_MISMATCH"),
    (ErrorExpresion, None, "INVALID_EXPRESSION"),
    (ErrorOperacion, r"^Parámetro mal formado", "INVALID_ARGUMENTS"),
    (ErrorOperacion, r"^El cuerpo '.*' no existe", "BODY_NOT_FOUND"),
    (ErrorOperacion, r"^Se perdió la referencia", "REFERENCE_LOST"),
    (ErrorExportacion, r"^No hay cuerpos", "NOTHING_TO_EXPORT"),
    (ErrorExportacion, r"^Formato no soportado|malla no se pueden guardar|no parece un STEP", "INVALID_FORMAT"),
    (ErrorExportacion, None, "OPERATION_FAILED"),
    (ErrorProyecto, None, "INVALID_PROJECT"),
    (ErrorAbrir, r"^Formato no soportado", "UNSUPPORTED_FILE_TYPE"),
    (ErrorAbrir, r"^No existe el archivo", "FILE_NOT_FOUND"),
    (ErrorAbrir, None, "IMPORT_FAILED"),
    (ErrorDocumento, None, "DOCUMENT_ERROR"),
    (_PASO, None, "OPERATION_FAILED"),
    (FileNotFoundError, None, "FILE_NOT_FOUND"),
    (FileExistsError, None, "FILE_EXISTS"),
    (PermissionError, None, "PERMISSION_DENIED"),
    (OSError, None, "FILE_ERROR"),
    (KeyError, None, "NOT_FOUND"),
]
# Los mensajes de un paso del timeline solo traen texto: patrones propios además de los de la tabla.
_MENSAJES_PASO = [
    (r"^Nombre desconocido", "INVALID_EXPRESSION"),
    (r"^Sintaxis inválida|^Expresión vacía|^Expresión no permitida|^División por cero", "INVALID_EXPRESSION"),
    (r"^No hay cuerpos sobre los que", "NO_TARGET_BODY"),
]


def error(error_kind, mensaje, *pistas_extra):
    """ErrorAPI con las pistas de la tabla más las propias (máximo 3)."""
    return ErrorAPI(error_kind, mensaje, (list(pistas_extra) + PISTAS.get(error_kind, []))[:3])


def traducir(exc):
    """Excepción cualquiera → ErrorAPI (nunca lanza)."""
    if isinstance(exc, ErrorAPI):
        return exc
    mensaje = str(exc) or type(exc).__name__
    if isinstance(exc, ErrorPuenteFusion):
        return error("FUSION_NOT_AVAILABLE" if exc.motivo == "sin_puente" else "FUSION_CONVERSION_FAILED", mensaje)
    if isinstance(exc, KeyError):
        mensaje = f"No existe {exc.args[0]!r}." if exc.args else "Clave inexistente."
    for clases, patron, kind in _TABLA:
        if isinstance(exc, clases) and (patron is None or re.search(patron, mensaje)):
            return error(kind, mensaje)
    return error("INTERNAL_ERROR", f"{type(exc).__name__}: {mensaje}")


def desde_mensaje(mensaje, prefijo=""):
    """Mensaje de un `ResultadoPaso("error")` → ErrorAPI. `prefijo` dice qué paso falló."""
    kind = next((k for patron, k in _MENSAJES_PASO if re.search(patron, mensaje)), None)
    if kind is None:
        # Un paso solo falla con errores de operación o de expresión: los patrones de exportar o del proyecto no aplican.
        kind = next((k for c, patron, k in _TABLA if patron and c in (ErrorOperacion, ErrorExpresion)
                     and re.search(patron, mensaje)), "OPERATION_FAILED")
    return error(kind, prefijo + mensaje)
