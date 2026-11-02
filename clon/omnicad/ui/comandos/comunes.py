# -*- coding: utf-8 -*-
"""Campos y conversiones que comparten varios comandos (operación booleana, perfiles, objetivos)."""
from ...timeline.operaciones import OPERACIONES_CUERPO
from ...timeline import analisis_vista as av
from ...timeline.parametros import ESCALAR, LONGITUD
from ..analisis_vista import aplicar as aplicar_analisis
from ..comando import Botones, Casilla, Deslizador, ErrorComando, Expresion, Opciones, Seleccion, hits

OPCIONES_OPERACION = {"unir": ("Unir", "op_unir"), "cortar": ("Cortar", "op_cortar"),
                      "intersecar": ("Intersección", "op_intersecar"), "nuevo": ("Cuerpo nuevo", "op_nuevo")}
assert set(OPCIONES_OPERACION) == set(OPERACIONES_CUERPO)
DIRECCIONES_UI = {"un_lado": ("Un lado", "dir_un_lado"), "dos_lados": ("Dos lados", "dir_dos_lados"),
                  "simetrica": ("Simétrico", "dir_simetrica")}
POSICIONES_SECCION = {"interior": ("Interior", "pos_interior"), "centro": ("En el centro", "pos_centro"),
                      "exterior": ("Exterior", "pos_exterior")}


SIEMPRE = lambda v: True  # noqa: E731


def campos_cebra(pre="", visible=SIEMPRE, **kw):
    """Opciones de Cebra (Zebra Analysis reference): las del comando suelto y las de la pestaña Análisis (`pre` = "ana_")."""
    kw["visible_si"] = visible
    return [Botones(f"{pre}orientacion", "Dirección", {"vertical": ("Vertical", "rayas_v"), "horizontal": ("Horizontal", "rayas_h")}, **kw),
            Deslizador(f"{pre}frecuencia", "Repetición", 20, 1, 100, **kw), Deslizador(f"{pre}opacidad", "Opacidad", 100, 0, 100, **kw),
            Casilla(f"{pre}bloquear", "Bloquear rayas", **kw), Casilla(f"{pre}alta_calidad", "Calidad alta", **kw)]


def params_cebra(v, ctx, pre=""):
    p = {"orientacion": v[f"{pre}orientacion"], "frecuencia": int(v[f"{pre}frecuencia"]), "opacidad": int(v[f"{pre}opacidad"]),
         "alta_calidad": bool(v[f"{pre}alta_calidad"])}
    if v[f"{pre}bloquear"]:
        p["vista_fija"] = [float(x) for x in ctx.ventana.visor.R[2]] if ctx.ventana is not None else [0.0, -1.0, 0.0]
    return p


def campos_mapa(pre="", visible=SIEMPRE, **kw):
    """Opciones de Mapa de curvatura (Curvature Map Analysis reference)."""
    tipo = lambda v: v.get(f"{pre}tipo_curvatura")  # noqa: E731
    gauss = lambda v: visible(v) and tipo(v) == "gaussiana"  # noqa: E731
    principal = lambda v: visible(v) and tipo(v) != "gaussiana"  # noqa: E731
    return [Botones(f"{pre}tipo_curvatura", "Tipo", {"gaussiana": ("Gaussiana", "ana_mapa"), "minima": ("Principal mínima", "cur_minima"),
                                                     "maxima": ("Principal máxima", "cur_maxima")}, visible_si=visible, **kw),
            Botones(f"{pre}visualizar", "Visualizar", {"suave": ("Suave", "cur_gradiente"), "bandas": ("Bandas", "cur_bandas")},
                    visible_si=gauss, **kw),
            Deslizador(f"{pre}escala", "Escala", 1.0, 0.0, 10.0, decimales=3, visible_si=gauss, **kw),
            Expresion(f"{pre}limite", "Límite", "0.1", ESCALAR, visible_si=principal,
                      etiqueta_si=lambda v: "Límite máximo" if tipo(v) == "minima" else "Límite mínimo",
                      ayuda="Curvatura (1/mm) desde la que la zona se pinta de rojo.", **kw),
            Deslizador(f"{pre}opacidad_mapa", "Opacidad", 100, 0, 100, visible_si=visible, **kw),
            Casilla(f"{pre}alta_calidad_mapa", "Calidad alta", visible_si=visible, **kw)]


def params_mapa(v, ctx, pre=""):
    t = v[f"{pre}tipo_curvatura"]
    p = {"tipo_curvatura": t, "opacidad": int(v[f"{pre}opacidad_mapa"]), "alta_calidad": bool(v[f"{pre}alta_calidad_mapa"])}
    if t == "gaussiana":
        return p | {"bandas": v[f"{pre}visualizar"] == "bandas", "escala": max(float(v[f"{pre}escala"]), 1e-3)}
    return p | {"limite": ctx.evaluar(v[f"{pre}limite"], ESCALAR)}


def campos_iso(pre="", visible=SIEMPRE, **kw):
    """Opciones de Isocurva (Isocurve Analysis reference)."""
    peines = lambda v: visible(v) and bool(v.get(f"{pre}peines"))  # noqa: E731
    return [Botones(f"{pre}tipo_iso", "Tipo", {"uv": ("U y V", "ana_iso"), "u": ("U", "ana_iso_u"), "v": ("V", "ana_iso_v")},
                    visible_si=visible, **kw),
            Deslizador(f"{pre}densidad", "Isocurvas", 5, 1, 50, visible_si=visible, **kw),
            Casilla(f"{pre}peines", "Curvatura en peines", visible_si=visible, **kw),
            Deslizador(f"{pre}densidad_peine", "Densidad", 50, 3, 200, visible_si=peines, **kw),
            Deslizador(f"{pre}escala_peine", "Escala", 10.0, 0.0, 100.0, decimales=3, visible_si=peines, **kw)]


def params_iso(v, ctx, pre=""):
    return {"tipo_iso": v[f"{pre}tipo_iso"], "densidad": int(v[f"{pre}densidad"]), "peines": bool(v[f"{pre}peines"]),
            "densidad_peine": int(v[f"{pre}densidad_peine"]), "escala_peine": max(float(v[f"{pre}escala_peine"]), 1e-3)}


TIPOS_ANALISIS = {"ninguno": ("Ninguno", "ana_ninguno"), "cebra": ("Cebra", "ana_cebra"), "curvatura": ("Mapa de curvatura", "ana_mapa"),
                  "isocurva": ("Isocurva", "ana_iso")}
_PARAMS_ANALISIS = {"cebra": params_cebra, "curvatura": params_mapa, "isocurva": params_iso}


def campos_analisis():
    es = lambda t: (lambda v: v.get("ana_tipo") == t)  # noqa: E731
    kw = {"pestana": "Análisis"}
    return [Botones("ana_tipo", "Tipo de análisis", TIPOS_ANALISIS, **kw),
            Seleccion("ana_cuerpos", "Cuerpos", {"cuerpo"}, minimo=0, maximo=None, ayuda="Sin selección: todos.", **kw),
            *campos_cebra("ana_", es("cebra"), **kw), *campos_mapa("ana_", es("curvatura"), **kw), *campos_iso("ana_", es("isocurva"), **kw)]


def con_analisis(clase):
    """Decorador: suma a un comando la pestaña Análisis (Barrido, Solevación y los diálogos de superficie). Pinta la vista
    previa y no queda nada al cerrar."""
    campos, al_cerrar = clase.campos, clase.al_cerrar

    def campos_con(self, ctx):
        return [*campos(self, ctx), *campos_analisis()]

    def analizar_previa(self, v, ctx, estado, visor):
        tipo = v.get("ana_tipo", "ninguno")
        if tipo == "ninguno":
            if getattr(self, "_analizado", False):
                self._analizado = False
                aplicar_analisis(visor, {"mallas": {}, "colores": None, "capas": [], "cortes": []})
            return
        params = _PARAMS_ANALISIS[tipo](v, ctx, "ana_") | {"cuerpos": [h["ref"]["cuerpo"] for h in v.get("ana_cuerpos") or []]}
        aplicar_analisis(visor, av.calcular(tipo, params, estado, ctx.doc.propiedades))
        self._analizado = True

    def cerrar(self, ctx):
        al_cerrar(self, ctx)
        if getattr(self, "_analizado", False) and ctx.ventana is not None:
            ctx.ventana.aplicar_analisis()

    clase.campos, clase.analizar_previa, clase.al_cerrar = campos_con, analizar_previa, cerrar
    return clase


def campo_operacion(defecto="nuevo"):
    return Opciones("operacion", "Operación", OPCIONES_OPERACION, defecto)


def campo_objetivos():
    """«Objetos para cortar» de Fusion: vacío = automático (los cuerpos que toca)."""
    return Seleccion("objetivos", "Objetos", {"cuerpo"}, minimo=0, maximo=None,
                     visible_si=lambda v: v.get("operacion") != "nuevo",
                     ayuda="Cuerpos afectados. Sin selección: los que toca la herramienta.")


def objetivos(v):
    return [h["ref"]["cuerpo"] for h in v.get("objetivos") or [] if h["ref"].get("tipo") == "cuerpo"]


def perfiles_a_params(seleccion):
    """Selección de perfiles y caras planas → (boceto, perfiles, caras) como los guarda la operación."""
    boceto, perfiles, caras = "", [], []
    for h in seleccion or []:
        ref = h["ref"]
        if ref["tipo"] == "perfil":
            if boceto and ref["boceto"] != boceto:
                raise ErrorComando("Los perfiles tienen que ser de un mismo boceto.")
            boceto = ref["boceto"]
            perfiles.append({"firma": ref["firma"], "centroide": ref["centroide"]})
        elif ref["tipo"] == "cara":
            caras.append(ref)
    if not perfiles and not caras:
        raise ErrorComando("Seleccioná uno o más perfiles o caras planas.")
    return boceto, perfiles, caras


def perfiles_desde_op(op, estado):
    refs_lista = [{"tipo": "perfil", "boceto": op.p["boceto"], **r} for r in op.p.get("perfiles", [])]
    return hits(refs_lista + list(op.p.get("caras") or []), estado)


def objetivos_desde_op(op, estado):
    lista = op.p.get("objetivos") or ([op.p["objetivo"]] if op.p.get("objetivo") else [])
    return hits([{"tipo": "cuerpo", "cuerpo": c} for c in lista], estado)


def simetria_total(ctx):
    """¿La cantidad simétrica del patrón es el total con el original (PAT-1)? Un paso viejo editado conserva su reparto."""
    return ctx.op is None or ctx.op.p.get("version_simetria", 1) == 2


def evaluar_o_cero(ctx, expr, tipo=LONGITUD):
    """Valor de una expresión del panel para ubicar manipuladores (0 si todavía no se puede evaluar)."""
    try:
        return float(ctx.evaluar(str(expr if expr not in (None, "") else "0"), tipo))
    except Exception:  # noqa: BLE001 — una expresión inválida deja el manipulador en 0
        return 0.0
