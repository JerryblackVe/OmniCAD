"""Selección progresiva de herramientas del catálogo para el asistente."""
from omnicad import api
from omnicad.api.errores import error


NUCLEO = (
    "get_scene_info", "get_timeline", "get_parameters", "create_parameter", "set_parameter",
    "create_sketch", "draw_line", "draw_rectangle", "draw_circle", "add_dimension", "add_constraint",
    "extrude", "revolve", "create_box", "create_cylinder", "fillet", "chamfer", "shell", "create_hole",
    "find_faces", "find_edges", "edit_feature", "get_viewport_image", "get_physical_properties",
    "measure_distance", "describe_operation", "run_operation", "undo", "save_document", "search_help",
)
PROHIBIDAS = {"execute_code"}
MODOS = ("explicar", "mostrar", "guiar", "hacer")
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


class Herramientas:
    def __init__(self, catalogo=None, modo="hacer"):
        if modo not in MODOS:
            raise ValueError(f"Modo inválido: {modo!r}. Modos: {', '.join(MODOS)}.")
        self.modo = modo
        base = [h for h in (api.catalogo() if catalogo is None else catalogo)
                if h["grupo"] not in ("dev", "asistente") and h["nombre"] not in PROHIBIDAS]
        self.catalogo = {h["nombre"]: h for h in base if en_modo(h, modo)}
        self.fuera_de_modo = {h["nombre"] for h in base} - set(self.catalogo)
        self.grupos = set()
        self.temas = sorted({h["grupo"] for h in self.catalogo.values()})

    def definiciones(self):
        """Núcleo, búsqueda y grupos habilitados, con los esquemas originales."""
        nombres = [n for n in NUCLEO if n in self.catalogo]
        posicion_busqueda = len(nombres)
        nombres += [n for n, h in self.catalogo.items() if h["grupo"] in self.grupos and n not in NUCLEO]
        definiciones = [{k: self.catalogo[n][k] for k in ("nombre", "descripcion", "esquema")} for n in nombres]
        definiciones.insert(posicion_busqueda, {
            "nombre": "buscar_herramientas",
            "descripcion": "Suma las herramientas de un grupo al asistente. Grupos: " + ", ".join(self.temas) + ".",
            "esquema": {
                "type": "object",
                "properties": {"tema": {"type": "string", "enum": self.temas,
                                         "description": "Grupo de herramientas que necesitás habilitar."}},
                "required": ["tema"],
                "additionalProperties": False,
            },
        })
        return definiciones

    def necesita_aprobacion(self, nombre):
        """En Guiar y Hacer, lo que Mostrar no permitiría (cambia algo) se aprueba antes de correrlo."""
        return self.modo in ("guiar", "hacer") and nombre in self.catalogo and not en_modo(self.catalogo[nombre],
                                                                                            "mostrar")

    def para_cli(self):
        """Lo que reciben los CLI del modo suscripción (no tienen buscar_herramientas): el núcleo, get_guide y las de
        vista que permita el modo. Las demás operaciones siguen al alcance con describe_operation y run_operation."""
        return sorted(n for n in {*NUCLEO, "get_guide", *VISTA} if n in self.catalogo)

    def permitida(self, nombre):
        """Indica si la herramienta del catálogo está ofrecida (buscar_herramientas la atiende el bucle)."""
        return nombre in self.catalogo and (nombre in NUCLEO or self.catalogo[nombre]["grupo"] in self.grupos)

    def buscar(self, tema):
        """Habilita un grupo válido o devuelve un error con los grupos disponibles."""
        if not isinstance(tema, str) or tema not in self.temas:
            return error("INVALID_ARGUMENTS", "Grupo de herramientas inválido.",
                         "Grupos: " + ", ".join(self.temas) + ".").a_dict()
        self.grupos.add(tema)
        return {"ok": True, "result": {"group": tema, "tools": [n for n, h in self.catalogo.items()
                                                               if h["grupo"] == tema]}, "avisos": []}
