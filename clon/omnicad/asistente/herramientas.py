"""Selección progresiva de herramientas del catálogo para el asistente."""
from pathlib import Path

from omnicad import api
from omnicad.api.doc_markdown import GRUPOS
from omnicad.api.errores import error
from omnicad.api.herramientas_ayuda import claves_de, puntaje


# Lo que va en cada paso. create_hole y chamfer (IA-11) y revolve, create_cylinder y measure_distance (IA-15) quedaron
# afuera: son esquemas pesados y el índice del prompt los deja a una búsqueda; con ellos el peor paso rozaba los 25 mil
# tokens.
NUCLEO = (
    "get_scene_info", "get_timeline", "get_parameters", "create_parameter", "set_parameter",
    "create_sketch", "draw_line", "draw_rectangle", "draw_circle", "add_dimension", "add_constraint",
    "extrude", "create_box", "fillet", "shell",
    "find_faces", "find_edges", "edit_feature", "get_viewport_image", "get_physical_properties",
    "describe_operation", "run_operation", "undo", "save_document", "search_help",
)
PROHIBIDAS = {"execute_code"}
TOPE_BUSQUEDA = 5        # herramientas por llamada a buscar_herramientas / find_tools
TOPE_RESULTADO = 8000    # caracteres del resultado de una herramienta que llegan al modelo
MODOS = ("explicar", "mostrar", "guiar", "hacer")
# Cuándo pregunta (IA-15); los modos dicen QUÉ puede hacer. Pisar un archivo que ya existe pregunta en los tres.
PERMISOS = ("cada_paso", "una_vez", "nunca")
# El catálogo dice que no modifican el documento, pero escriben en disco, tocan la biblioteca del usuario o la ventana.
CON_EFECTOS = {
    "save_document", "export", "export_mesh", "export_drawing", "export_flat_pattern_dxf", "export_animation_video",
    "export_hidden_line_svg", "export_sketch", "export_parameters", "get_bill_of_materials", "render_image",
    "run_graph", "discard_recoverable_document", "define_material", "delete_material", "create_sheet_metal_rule",
    "delete_sheet_metal_rule", "add_font_folder", "decal_view", "set_browser_visibility", "sketch_view",
    "create_plastic_rule", "delete_plastic_rule", "manage_command_presets",
}
# Mostrar suma mover la cámara y elegir en la ventana (set_view figura como modifica, pero solo guarda la cámara).
VISTA = {"set_view", "select_bodies", "select_entities", "find_in_window", "select_by_boundary"}


def en_modo(herramienta, modo):
    """Regla única: Explicar solo lee; Mostrar lee, mueve la cámara y selecciona; Guiar y Hacer, todo."""
    if modo in ("guiar", "hacer"):
        return True
    nombre = herramienta["nombre"]
    lectura = not herramienta["modifica"] and nombre not in CON_EFECTOS and nombre not in VISTA
    return lectura or (modo == "mostrar" and nombre in VISTA)


def recortar(texto):
    """El resultado de una herramienta cortado a TOPE_RESULTADO, con una nota: un documento grande no se come el
    contexto del modelo (lo que muestra el panel no se corta)."""
    if len(texto) <= TOPE_RESULTADO:
        return texto
    return (texto[:TOPE_RESULTADO] + f"… [resultado recortado: {TOPE_RESULTADO} de {len(texto)} caracteres; pedí "
            "menos, p. ej. summary=true, un filtro o un límite]")


def encontrar(catalogo, consulta=None, nombres=None, grupo=None):
    """(encontradas, sobrantes, desconocidas) en `catalogo` ({nombre: entrada}): por `nombres` exactos, por `grupo` o
    por `consulta` (palabras, con el puntaje de search_help). Hasta TOPE_BUSQUEDA encontradas; las demás que
    coinciden van en sobrantes. Lanza ErrorAPI INVALID_ARGUMENTS si el pedido no sirve."""
    if nombres is not None:
        if not isinstance(nombres, list) or not nombres or not all(isinstance(n, str) for n in nombres):
            raise error("INVALID_ARGUMENTS", "names/nombres tiene que ser una lista de nombres de herramientas.")
        pedidas = list(dict.fromkeys(nombres))
        coinciden, desconocidas = [n for n in pedidas if n in catalogo], [n for n in pedidas if n not in catalogo]
    elif grupo is not None:
        temas = sorted({h["grupo"] for h in catalogo.values()})
        if grupo not in temas:
            raise error("INVALID_ARGUMENTS", "Grupo de herramientas inválido.", "Grupos: " + ", ".join(temas) + ".")
        coinciden, desconocidas = [n for n, h in catalogo.items() if h["grupo"] == grupo], []
    elif isinstance(consulta, str) and claves_de(consulta):
        claves = claves_de(consulta)
        puntos = {n: puntaje(claves, n, f"{n}: {h['descripcion']}") for n, h in catalogo.items()}
        coinciden, desconocidas = sorted((n for n in puntos if puntos[n]), key=lambda n: -puntos[n]), []
    else:
        raise error("INVALID_ARGUMENTS", "Pedí las herramientas por consulta (palabras), por nombres (lista) o por "
                    "grupo.")
    return coinciden[:TOPE_BUSQUEDA], coinciden[TOPE_BUSQUEDA:], desconocidas


def resumen(descripcion):
    """La primera oración de una descripción: lo que alcanza para elegir."""
    return descripcion.split(". ")[0].rstrip(".")[:200]


def indice(catalogo):
    """Una línea por grupo con los NOMBRES de sus herramientas, sin esquemas (sin la descripción del grupo: IA-15)."""
    orden = list(GRUPOS)
    grupos = sorted({h["grupo"] for h in catalogo.values()}, key=lambda g: orden.index(g) if g in orden else 99)
    return "\n".join(f"- {g}: " + ", ".join(n for n, h in catalogo.items() if h["grupo"] == g) for g in grupos)


class Herramientas:
    """Lo que el asistente puede usar en un pedido (`modo`) y cuándo pregunta (`permisos`). `ruta_doc()` da la ruta
    del documento actual: guardar sin ruta la pisa. Es de UN pedido: guarda si el plan ya se aprobó."""

    def __init__(self, catalogo=None, modo="hacer", permisos="una_vez", ruta_doc=None):
        if modo not in MODOS:
            raise ValueError(f"Modo inválido: {modo!r}. Modos: {', '.join(MODOS)}.")
        if permisos not in PERMISOS:
            raise ValueError(f"Permisos inválidos: {permisos!r}. Opciones: {', '.join(PERMISOS)}.")
        self.modo, self.permisos, self.ruta_doc = modo, permisos, ruta_doc
        self.aprobado = False
        base = [h for h in (api.catalogo() if catalogo is None else catalogo)
                if h["grupo"] not in ("dev", "asistente") and h["nombre"] not in PROHIBIDAS]
        self.catalogo = {h["nombre"]: h for h in base if en_modo(h, modo)}
        self.fuera_de_modo = {h["nombre"] for h in base} - set(self.catalogo)
        self.habilitadas = []        # en el orden en que se pidieron: van al final y no rompen la caché del prompt
        self.temas = sorted({h["grupo"] for h in self.catalogo.values()})

    def definiciones(self):
        """Núcleo, buscar_herramientas y las habilitadas (en el orden en que se pidieron), con los esquemas originales."""
        definiciones = [{k: self.catalogo[n][k] for k in ("nombre", "descripcion", "esquema")}
                        for n in NUCLEO if n in self.catalogo]
        definiciones.append({
            "nombre": "buscar_herramientas",
            "descripcion": "Habilita herramientas del catálogo que no están cargadas (el índice del prompt de sistema "
                           f"dice cuáles hay), hasta {TOPE_BUSQUEDA} por llamada: pedilas por nombres exactos (lo "
                           "mejor), por consulta (palabras) o por grupo, y después usalas directamente.",
            "esquema": {
                "type": "object",
                "properties": {
                    "nombres": {"type": "array", "items": {"type": "string"},
                                "description": "Nombres exactos de herramientas del índice."},
                    "consulta": {"type": "string", "description": "Qué necesitás, en pocas palabras."},
                    "grupo": {"type": "string", "enum": self.temas, "description": "Un grupo del índice."},
                },
                "additionalProperties": False,
            },
        })
        return definiciones + [{k: self.catalogo[n][k] for k in ("nombre", "descripcion", "esquema")}
                               for n in self.habilitadas]

    def indice(self):
        return indice(self.catalogo)

    def necesita_aprobacion(self, nombre):
        """En Guiar y Hacer, lo que Mostrar no permitiría (cambia algo) se aprueba antes de correrlo."""
        return self.modo in ("guiar", "hacer") and nombre in self.catalogo and not en_modo(self.catalogo[nombre],
                                                                                            "mostrar")

    def pisa_archivo(self, nombre, args):
        """Guardar o exportar encima de un archivo que ya existe: escribe fuera del documento y no se deshace."""
        if nombre not in CON_EFECTOS or not isinstance(args, dict):
            return False
        ruta = args.get("path") or args.get("csv_path")
        if nombre == "save_document" and not ruta and self.ruta_doc is not None:
            ruta = self.ruta_doc()
        if not isinstance(ruta, str) or not ruta.strip():
            return False
        ruta = Path(ruta)
        return ruta.exists() or (nombre == "save_document" and ruta.with_suffix(".omnicad").exists())

    def a_aprobar(self, pedidos):
        """Regla única de permisos (bucle del modo API y filtro del puente de los CLI): de `pedidos` (con .nombre y
        .args), los que hay que aprobar ahora. Lo que cambia algo pregunta en cada tanda (cada_paso) o hasta que se
        apruebe el plan (una_vez); pisar un archivo existente pregunta siempre, también con «nunca»."""
        cambian = [p for p in pedidos if self.necesita_aprobacion(p.nombre)]
        if self.permisos == "nunca" or self.aprobado:
            return [p for p in cambian if self.pisa_archivo(p.nombre, p.args)]
        return cambian

    def aprobaron(self):
        """La persona aprobó una tanda: con «una_vez» el resto del pedido ya no pregunta."""
        self.aprobado = self.permisos == "una_vez"

    def para_cli(self):
        """Lo que reciben los CLI del modo suscripción: el núcleo, get_guide y las de vista que permita el modo. Las
        demás les llegan con find_tools y call_tool (`omnicad-mcp --meta-tools`)."""
        return sorted(n for n in {*NUCLEO, "get_guide", *VISTA} if n in self.catalogo)

    def permitida(self, nombre):
        """Indica si la herramienta del catálogo está ofrecida (buscar_herramientas la atiende el bucle)."""
        return nombre in self.catalogo and (nombre in NUCLEO or nombre in self.habilitadas)

    def buscar(self, nombres=None, consulta=None, grupo=None):
        """Habilita lo encontrado (con tope) y contesta nombre y descripción corta; error claro si no hay nada."""
        try:
            encontradas, sobrantes, desconocidas = encontrar(self.catalogo, consulta, nombres, grupo)
        except api.ErrorAPI as e:
            return e.a_dict()
        fuera = [n for n in desconocidas if n in self.fuera_de_modo]
        if not encontradas:
            pista = f"No se pueden usar en el modo {self.modo}: {', '.join(fuera)}." if fuera else \
                "Elegí nombres del índice del prompt de sistema."
            return error("TOOL_NOT_AVAILABLE", "No se encontró ninguna herramienta habilitable con ese pedido.",
                         pista).a_dict()
        self.habilitadas += [n for n in encontradas if n not in NUCLEO and n not in self.habilitadas]
        resultado = {"enabled": [{"name": n, "description": resumen(self.catalogo[n]["descripcion"])}
                                 for n in encontradas]}
        if sobrantes:
            resultado["more"] = sobrantes
        if set(desconocidas) - set(fuera):
            resultado["unknown"] = [n for n in desconocidas if n not in fuera]
        if fuera:
            resultado["not_in_mode"] = fuera
        return {"ok": True, "result": resultado, "avisos": []}
