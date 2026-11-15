# -*- coding: utf-8 -*-
"""Campos y conversiones que comparten varios comandos (operación booleana, perfiles, objetivos)."""
from ...nucleo import geometria as geo
from ...nucleo.malla import Malla
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
def direcciones_revolucion(v):
    """B-384: con «A objeto» Fusion ofrece Un lado y Dos lados (cada lado gira hasta su objeto); Simétrica, solo con ángulo."""
    return {k: t for k, t in DIRECCIONES_UI.items() if k != "simetrica" or v.get("extension") != "objeto"}


POSICIONES_SECCION = {"interior": ("Interior", "pos_interior"), "centro": ("En el centro", "pos_centro"),
                      "exterior": ("Exterior", "pos_exterior")}


SIEMPRE = lambda v: True  # noqa: E731
# Escala de los peines: es relativa al tamaño de lo analizado (10 = púa más larga del 20 % de su diagonal), así que 20 = 40 %.
# Más arriba las púas pasan de la pieza y tapan la vista (P-148).
ESCALA_PEINE_MAX = 20.0


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
            Deslizador(f"{pre}escala_peine", "Escala", 10.0, 0.0, ESCALA_PEINE_MAX, decimales=3, visible_si=peines, **kw)]


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
        propiedades = ctx.ventana.propiedades_analisis(estado) if ctx.ventana is not None else ctx.doc.propiedades
        aplicar_analisis(visor, av.calcular(tipo, params, estado, propiedades))
        self._analizado = True

    def cerrar(self, ctx):
        al_cerrar(self, ctx)
        if getattr(self, "_analizado", False) and ctx.ventana is not None:
            ctx.ventana.aplicar_analisis()

    clase.campos, clase.analizar_previa, clase.al_cerrar = campos_con, analizar_previa, cerrar
    return clase


def campo_operacion(defecto="nuevo"):
    return Opciones("operacion", "Operación", OPCIONES_OPERACION, defecto)


def solidos_visibles(ctx):
    ocultos = getattr(ctx.ventana, "_ocultos_efectivos", lambda _estado: ())(ctx.estado)
    return [c for c in ctx.estado.cuerpos.values() if c.tipo == "solido" and c.id not in ocultos]


def caja_cuerpo(cuerpo, cajas):
    if cuerpo.id not in cajas:
        cajas[cuerpo.id] = geo.caja_envolvente(cuerpo.forma)
    return cajas[cuerpo.id]


def caja_nueva(estado, cid, forma):
    """Caja de un cuerpo de la previa para descartar lo lejano: la de su malla si vino del proceso aparte (sin kernel; la
    exacta de un barrido con guía tardaba 0,15 s), con 1 mm de holgura; si no, la exacta. El solape lo decide `solapan`."""
    malla = getattr(estado, "_mallas_previa", {}).get(cid)
    if malla is None or not len(malla[0]):
        return geo.caja_envolvente(forma)
    return tuple((malla[0].min(0) - 1.0).tolist()), tuple((malla[0].max(0) + 1.0).tolist())


def _cajas_tocan(a, b):
    """¿Dos cajas se tocan o solapan? Apoyarse en una cara sí cuenta."""
    return all(min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]) >= -1e-6 for i in range(3))


def _area_comun(cara, solido):
    comun = geo.booleano(cara, solido, "intersecar")
    return 0.0 if geo.esta_vacia(comun) else geo.area(comun)


def perfil_apoyado(ctx, v, apoyos, cajas):
    """B-344: perfil, cara o superficie sobre un sólido visible, con área (una arista sola no cuenta). Se mide una vez por selección,
    no en cada cuadro del arrastre (P-99)."""
    if v.get("inicio", "plano") != "plano":
        return False
    clave = repr([h["ref"] for h in v.get("perfiles") or []])
    if clave not in apoyos:
        from .. import manipuladores as mp
        entidades = [mp.entidad(h, ctx.estado) for h in v.get("perfiles") or []]
        formas = [e.forma for e in entidades if e is not None and e.forma is not None]
        apoyos[clave] = any(
            _area_comun(f, c.forma) > 1e-6 for f in formas for c in solidos_visibles(ctx)
            if _cajas_tocan(geo.caja_envolvente(f), caja_cuerpo(c, cajas)))
    return apoyos[clave]


def ajustar_operacion(comando, panel, auto):
    """Cortar/Unir automáticos; None restaura la operación anterior sin fijarla como elección manual."""
    actual = panel.valores.get("operacion")
    if auto is not None and actual != auto:
        if comando._antes_auto is None:
            comando._antes_auto = actual
        nueva = auto
    elif auto is None and comando._antes_auto is not None:
        nueva, comando._antes_auto = comando._antes_auto, None
    else:
        return
    comando._ajustando = True
    try:
        panel.set_valor("operacion", nueva)
    finally:
        comando._ajustando = False


def con_operacion_automatica(clase):
    """Revolución, Barrido, Solevación y Engrosar: Unir desde una selección apoyada; Cortar si entra en un sólido visible.
    La operación elegida a mano o reabierta para editar queda fija, como en Extruir."""
    preparar, cambiar, previa = clase.preparar_panel, clase.al_cambiar, clase.previa_lista

    def apoyo(self, panel):
        v = panel.valores
        seleccion = [] if v.get("tipo") == "cuerpo" else v.get("caras", v.get("perfiles", (v.get("secciones") or [])[:1]))
        return perfil_apoyado(panel.ctx, {"perfiles": seleccion}, self._apoyos, self._cajas)

    def preparar_auto(self, panel):
        self._fija = panel.ctx.op is not None
        self._antes_auto, self._ajustando = None, True
        self._apoyos, self._cajas = {}, {}
        self._herramienta_previa = None
        if not self._fija:
            panel.set_valor("operacion", "nuevo")  # B-431: el objetivo de un preajuste no viaja con él.
        self._ajustando = False
        preparar(self, panel)
        if not self._fija:     # B-471b: el perfil que ya trae el panel (único a la vista o preseleccionado) también apoya
            ajustar_auto(self, panel)

    def ajustar_auto(self, panel):
        try:
            ajustar_operacion(self, panel, "unir" if apoyo(self, panel) else None)
        except Exception as e:  # noqa: BLE001 — un apoyo que no se puede medir se informa sin romper la selección
            panel._mostrar(f"⚠ {e}", tipo="aviso")

    def cambiar_auto(self, panel, clave):
        if clave == "operacion" and not self._ajustando:
            self._fija = True
        cambiar(self, panel, clave)
        if not self._fija and clave in ("perfiles", "secciones", "caras", "tipo"):
            ajustar_auto(self, panel)

    def previa_auto(self, panel, estado):
        previa(self, panel, estado)
        op, ctx = panel.ultima_op, panel.ctx
        if self._fija or op is None:
            return
        solidos = solidos_visibles(ctx)
        auto = "unir" if apoyo(self, panel) else None
        if solidos:
            params = dict(op.p, operacion="nuevo", objetivos=[])
            clave = repr(params)
            if self._herramienta_previa is None or self._herramienta_previa[0] != clave:
                # FL-1b: la previa aparte trae el B-Rep; sin esto el barrido se volvía a calcular en la ventana (0,3 s)
                if op.p.get("operacion") == "nuevo" and not any(
                        isinstance(c.forma, Malla) for k, c in estado.cuerpos.items() if k not in ctx.estado.cuerpos):
                    herramienta = estado
                else:
                    with geo.en_serie():
                        herramienta, _avisos = ctx.doc.previsualizar(type(op)(op.id, op.nombre, **params), ctx.indice,
                                                                   en_vivo=True)
                self._herramienta_previa = clave, [(c.forma, caja_nueva(herramienta, k, c.forma))
                                                   for k, c in herramienta.cuerpos.items() if k not in ctx.estado.cuerpos]
            if any(geo.solapan(f, c.forma) for f, caja in self._herramienta_previa[1] for c in solidos
                   if geo.cajas_solapan(caja, caja_cuerpo(c, self._cajas))):
                auto = "cortar"
        ajustar_operacion(self, panel, auto)

    clase.preparar_panel, clase.al_cambiar, clase.previa_lista = preparar_auto, cambiar_auto, previa_auto
    return clase


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
