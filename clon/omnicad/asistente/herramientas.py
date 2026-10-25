"""Selección progresiva de herramientas del catálogo para el asistente."""
from omnicad import api
from omnicad.api.errores import error


NUCLEO = (
    "get_scene_info", "get_timeline", "get_parameters", "create_parameter", "set_parameter",
    "create_sketch", "draw_line", "draw_rectangle", "draw_circle", "add_dimension", "add_constraint",
    "extrude", "revolve", "create_box", "create_cylinder", "fillet", "chamfer", "shell", "create_hole",
    "find_faces", "find_edges", "edit_feature", "get_viewport_image", "get_physical_properties",
    "measure_distance", "describe_operation", "run_operation", "undo", "save_document",
)
PROHIBIDAS = {"execute_code"}


class Herramientas:
    def __init__(self, catalogo=None):
        self.catalogo = {h["nombre"]: h for h in (api.catalogo() if catalogo is None else catalogo)
                         if h["grupo"] != "dev" and h["nombre"] not in PROHIBIDAS}
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
