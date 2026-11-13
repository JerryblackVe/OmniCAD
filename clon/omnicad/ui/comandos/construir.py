# -*- coding: utf-8 -*-
"""CONSTRUIR: el panel único «Geometría de construcción» (Tipo, Método y sus entradas, como Fusion) y el SCU.

Cada entrada del menú es un `Comando` propio (mismas claves de siempre) que abre el mismo panel con Tipo y Método puestos.
Las filas de selección son r0, r1 y r2 para todos los métodos: cambian etiqueta y filtros, así cambiar de método conserva lo
que sirve. Lo que depende de lo elegido aparece recién cuando está completo, como en las capturas de Fusion."""
import numpy as np

from ...timeline.operaciones import OpPlano
from ...timeline.ops_construir import TIPOS_EJE, TIPOS_PLANO, TIPOS_PUNTO, OpEje, OpPunto, OpSCU, calcular_plano, lugar_en
from ...timeline.parametros import ANGULO, ESCALAR, LONGITUD
from ..comando import (Botones, Casilla, Comando, ErrorComando, Expresion, Opciones, OpcionesVivas, Seleccion, acepta, hit_desde_ref,
                       hits, ref1, refs)
from . import registrar

PLANO = {"plano", "cara_plana"}
EJE = {"eje", "arista_lineal"}
PUNTO = {"vertice", "punto", "forzado"}
ARISTA = {"arista", "curva_boceto"}
DIRECCION = EJE | {"cara", "plano"}          # Eje Z y Eje X del SCU: una arista o una cara alinean ese eje

# método (la clave del menú) → (clase de op, tipo de la op, texto en el desplegable, [(fila, etiqueta, filtros, obligatoria)])
METODOS = {
    "plano_desfase": (OpPlano, "desfase", "Desfase", [("r0", "Plano", PLANO, True)]),
    "plano_angulo": (OpPlano, "angulo", "En el ángulo", [("r0", "Arista", EJE, True)]),
    "plano_tangente": (OpPlano, "tangente", "Tangente", [("r0", "Cara", {"cara"}, True), ("r1", "Objeto de referencia", PLANO, False)]),
    "plano_medio": (OpPlano, "medio", "Plano medio", [("r0", "Plano 1", PLANO, True), ("r1", "Plano 2", PLANO, True)]),
    "plano_perpendicular": (OpPlano, "perpendicular", "Plano perpendicular",
                            [("r0", "Cara", {"cara", "plano"}, True), ("r1", "Objeto de referencia", PUNTO | PLANO, False)]),
    "plano_dos_aristas": (OpPlano, "dos_aristas", "A través de dos aristas", [("r0", "Línea 1", EJE, True), ("r1", "Línea 2", EJE, True)]),
    "plano_tres_puntos": (OpPlano, "tres_puntos", "A través de tres puntos",
                          [("r0", "Punto 1", PUNTO, True), ("r1", "Punto 2", PUNTO, True), ("r2", "Punto 3", PUNTO, True)]),
    "plano_ruta": (OpPlano, "ruta", "A lo largo de la ruta", [("r0", "Ruta", ARISTA | {"eje"}, True)]),
    "eje_cilindro": (OpEje, "cilindro", "A través de cilindro/cono/toroide", [("r0", "Cara", {"cara"}, True)]),
    "eje_perpendicular": (OpEje, "perpendicular_cara", "Perpendicular a la cara",
                          [("r0", "Cara", {"cara", "plano"}, True), ("r1", "Punto", PUNTO, False)]),
    "eje_dos_planos": (OpEje, "dos_planos", "A través de dos planos", [("r0", "Plano 1", PLANO, True), ("r1", "Plano 2", PLANO, True)]),
    "eje_dos_puntos": (OpEje, "dos_puntos", "A través de dos puntos", [("r0", "Punto 1", PUNTO, True), ("r1", "Punto 2", PUNTO, True)]),
    "eje_arista": (OpEje, "arista", "A través de arista", [("r0", "Arista", EJE, True)]),
    "punto_vertice": (OpPunto, "vertice", "En vértice", [("r0", "Punto", PUNTO, True)]),
    "punto_dos_aristas": (OpPunto, "dos_aristas", "A través de dos aristas",
                          [("r0", "Arista 1", ARISTA | {"eje"}, True), ("r1", "Arista 2", ARISTA | {"eje"}, True)]),
    "punto_tres_planos": (OpPunto, "tres_planos", "A través de tres planos",
                          [("r0", "Plano 1", PLANO | {"perfil"}, True), ("r1", "Plano 2", PLANO | {"perfil"}, True),
                           ("r2", "Plano 3", PLANO | {"perfil"}, True)]),
    "punto_centro": (OpPunto, "centro", "En el centro de círculo/esfera/toroide",
                     [("r0", "Círculo/esfera/toroide", {"arista_circular", "cara", "curva_boceto", "perfil"}, True)]),
    "punto_arista_plano": (OpPunto, "arista_plano", "En arista y plano", [("r0", "Arista", EJE, True), ("r1", "Plano", PLANO, True)]),
    "punto_ruta": (OpPunto, "ruta", "A lo largo de la ruta", [("r0", "Ruta", ARISTA, True)]),
}
NOMBRES = {"plano": ("Plano", "plano_desfase"), "eje": ("Eje", "eje_cilindro"), "punto": ("Punto", "punto_vertice")}
TIPO_DE_CLASE = {OpPlano: "plano", OpEje: "eje", OpPunto: "punto"}
EXTENSION = {"distancia": ("Distancia", "ext_distancia"), "objeto": ("Al objeto", "ext_objeto")}
PERPENDICULARES = ("plano_perpendicular", "eje_perpendicular")
RUTAS = ("plano_ruta", "punto_ruta")
CON_DESFASE = ("plano_desfase", "plano_angulo", "plano_tangente", "plano_dos_aristas", "plano_tres_puntos")


def _es(*metodos):
    return lambda v: v.get("metodo") in metodos


def _filas(metodo):
    return METODOS[metodo][3]


def _completo(v):
    """Lo obligatorio del método ya está elegido: recién ahí aparece lo demás."""
    return all(v.get(k) for k, _e, _f, obligatoria in _filas(v["metodo"]) if obligatoria)


def _plana(v):
    """¿La cara o plano de un método perpendicular es plana? (hasta elegirla se muestra como en una cara plana)"""
    return not v.get("r0") or v["r0"][0].get("plano") is not None


def _ruta_eje(v):
    return v.get("metodo") == "plano_ruta" and any(h.get("tipo") == "eje" for h in v.get("r0") or [])


def _ve_fila(clave):
    """r1 del método perpendicular aparece después de elegir la cara, como en la captura; las demás, según el método."""
    def ver(v):
        if clave not in [f[0] for f in _filas(v["metodo"])]:
            return False
        return v["metodo"] not in PERPENDICULARES or clave == "r0" or bool(v.get("r0"))
    return ver


def _ve_direccion(v):
    return v.get("metodo") == "plano_perpendicular" and _plana(v)


def _ve_tipo_distancia(v):
    return v.get("metodo") in RUTAS and not _ruta_eje(v)


def _ve_objeto(v):
    return (v.get("metodo") == "plano_desfase" and v.get("extension") == "objeto"
            or v.get("metodo") == "plano_ruta" and (v.get("tipo_distancia") == "objeto" or _ruta_eje(v)))


def _ve_distancia(v):
    if v.get("metodo") == "plano_desfase":
        return v.get("extension") == "distancia" and _completo(v)
    return _ruta_eje(v) or _ve_tipo_distancia(v) and v.get("tipo_distancia") == "absoluto"


def _ve_posicion(v):
    return _ve_tipo_distancia(v) and v.get("tipo_distancia") == "proporcional"


def _ve_angulo(v):
    return v.get("metodo") in ("plano_angulo", "plano_tangente") and _completo(v)


def _ve_desfase(v):
    if v.get("metodo") in PERPENDICULARES[:1]:
        return bool(v.get("r0"))
    return _completo(v) and (v.get("metodo") in CON_DESFASE or v.get("metodo") == "plano_ruta" and v.get("tipo_distancia") == "objeto")


def _ve_tipo_extension(v):
    if v.get("metodo") == "plano_perpendicular":
        return True
    return _completo(v) and v.get("metodo") not in ("plano_desfase", "plano_ruta") and METODOS[v["metodo"]][0] is not OpPunto


def _ve_medida(v):
    return _ve_tipo_extension(v) and _completo(v) and v.get("tipo_extension") == "distancia"


def _ve_objeto_extension(v):
    return _ve_tipo_extension(v) and _completo(v) and v.get("tipo_extension") == "objeto"


def _ve_redimensionar(v):
    return _completo(v) and METODOS[v["metodo"]][0] is not OpPunto


def _metodos_de(v):
    return {k: (d[2], k) for k, d in METODOS.items() if TIPO_DE_CLASE[d[0]] == v.get("tipo")}


def _tipos_distancia(v):
    if v.get("metodo") == "punto_ruta":
        return {"proporcional": "Proporcional", "absoluto": "Físico"}
    return {"proporcional": "Proporcional", "absoluto": "Absoluto", "objeto": "Al objeto"}


def _etiqueta(clave):
    return lambda v: next((e for k, e, _f, _o in _filas(v["metodo"]) if k == clave), "")


# Valores con su fila: (clave, tipo de expresión o None, cuándo se ve). Lo que no se ve vuelve a su valor por defecto en el paso.
VALORES = (("distancia", LONGITUD, _ve_distancia), ("posicion", ESCALAR, _ve_posicion), ("angulo", ANGULO, _ve_angulo),
           ("desfase", LONGITUD, _ve_desfase), ("medida", LONGITUD, _ve_medida))
OPCIONES = (("extension", _es("plano_desfase")), ("direccion", _ve_direccion), ("tipo_distancia", _ve_tipo_distancia),
            ("tipo_extension", _ve_tipo_extension), ("redimensionar", _ve_redimensionar), ("cadena_tangente", _ve_tipo_distancia))


class GeometriaConstruccion(Comando):
    """El panel de los 19 métodos. Cada subclase solo dice con qué método abre (`CLAVE`)."""
    CLASE_OP, ANCHO_PANEL = None, "simple"
    TITULO_PANEL = "Geometría de construcción"

    def titulo_icono(self, valores):
        return self.TITULO_PANEL, valores.get("metodo") or self.ICONO

    def campos(self, ctx):
        def fila(clave):
            d = next((f for f in _filas(self.CLAVE) if f[0] == clave), None)
            return Seleccion(clave, d[1] if d else "", d[2] if d else set(), minimo=0, maximo=None if self.CLAVE in RUTAS and clave == "r0" else 1,
                             texto_boton="Seleccionar", visible_si=_ve_fila(clave), etiqueta_si=_etiqueta(clave))
        return [Botones("tipo", "Tipo", NOMBRES, TIPO_DE_CLASE[self.CLASE_OP]),
                OpcionesVivas("metodo", "Método", _metodos_de, self.CLAVE),
                fila("r0"),
                Botones("direccion", "Dirección", {"U": ("U", "direccion_u"), "V": ("V", "direccion_v")}, "U", visible_si=_ve_direccion),
                fila("r1"), fila("r2"),
                Opciones("extension", "Extensión", EXTENSION, visible_si=_es("plano_desfase")),
                OpcionesVivas("tipo_distancia", "Tipo de extensión", _tipos_distancia, "proporcional", visible_si=_ve_tipo_distancia),
                Seleccion("objeto", "Objeto", PUNTO, minimo=0, texto_boton="Seleccionar", visible_si=_ve_objeto,
                          etiqueta_si=lambda v: "Objeto" if v.get("metodo") == "plano_desfase" else "Objeto de referencia"),
                Expresion("distancia", "Distancia", "0 mm", visible_si=_ve_distancia),
                Expresion("posicion", "Distancia (0 a 1)", "0.5", ESCALAR, visible_si=_ve_posicion),
                Expresion("angulo", "Ángulo", "0 deg", ANGULO, visible_si=_ve_angulo),
                Expresion("desfase", "Desfase", "0 mm", visible_si=_ve_desfase,
                          etiqueta_si=lambda v: "Distancia" if v.get("metodo") == "plano_perpendicular" else "Desfase"),
                Casilla("cadena_tangente", "Cadena tangente", True, visible_si=_ve_tipo_distancia),
                Opciones("tipo_extension", "Tipo de extensión", EXTENSION, visible_si=_ve_tipo_extension,
                         etiqueta_si=lambda v: "Extensión" if v.get("metodo") == "plano_perpendicular" else "Tipo de extensión"),
                Expresion("medida", "Medida", "0 mm", visible_si=_ve_medida, ayuda="Lado del plano o largo del eje. 0 = el que sale de lo elegido."),
                Seleccion("objeto_extension", "Objeto de extensión", PUNTO | PLANO | EJE | {"perfil", "cuerpo"}, minimo=0,
                          texto_boton="Seleccionar", visible_si=_ve_objeto_extension),
                Opciones("redimensionar", "Redimensionar", {"predeterminado": "Predeterminado", "extendido": "Extendido"},
                         visible_si=_ve_redimensionar, ayuda="Solo cambia cómo se ve: ajustado a lo elegido o llenando la vista.")]

    def preparar_panel(self, panel):
        self.panel = panel
        if panel.ctx.op is not None:
            panel.widgets["tipo"].setEnabled(False)        # un plano editado sigue siendo un plano: los pasos que lo usan no se rompen
        elif panel.valores.get("metodo") != self.CLAVE:    # un preajuste guardado no cambia el método que se pidió en el menú
            panel.set_valor("tipo", TIPO_DE_CLASE[self.CLASE_OP])
            panel.set_valor("metodo", self.CLAVE)

    def al_cambiar(self, panel, clave):
        if clave not in ("tipo", "metodo", "r0"):
            return
        v, filas = panel.valores, {f[0]: f for f in _filas(panel.valores["metodo"])}
        for k in ("r0", "r1", "r2"):
            c = panel._por_clave[k]
            c.filtros = set(filas[k][2]) if k in filas else set()
            if k == "r1" and v["metodo"] == "plano_perpendicular" and not _plana(v):
                c.filtros = set(PUNTO)                     # en una cara curva el Objeto de referencia solo es un punto
            c.maximo = None if v["metodo"] in RUTAS and k == "r0" else 1
            if clave != "r0":
                v[k] = [h for h in v.get(k) or [] if acepta(c.filtros, h)]
        if clave != "r0":
            panel._activar(next((panel._por_clave[k] for k in filas if not v.get(k) and panel._visible(panel._por_clave[k])), None))
            panel._refrescar_seleccion()
            panel._actualizar_visibles()

    def ajustar_hit(self, campo, hit, ctx, visor):
        """Tocar otro lugar de la misma cara mueve el lugar: no la saca de la selección."""
        v = self.panel.valores
        if campo.clave == "r0" and v["metodo"] in PERPENDICULARES and v["r0"] and v["r0"][0]["ref"] == hit["ref"] and hit.get("punto") is not None:
            v["r0"] = []
        return None

    def construir(self, v, ctx):
        metodo = v["metodo"]
        clase, tipo = METODOS[metodo][:2]
        lista = []
        for k, et, _f, obligatoria in _filas(metodo):
            if not v.get(k) and obligatoria:
                raise ErrorComando(f"Seleccioná: {et.lower()}.")
            lista += refs(v, k)
        if _ruta_eje(v) and len(lista) > 1:
            raise ErrorComando("Un eje no se encadena: elegí solo el eje o solo aristas.")
        if metodo == "plano_desfase" and v.get("extension") == "distancia" and ctx.evaluar(v["distancia"]) == 0:
            raise ErrorComando("La distancia de desfase no puede ser cero: arrastrá la flecha o escribí una distancia.")
        params = {"tipo": tipo, "refs": lista}
        for k, t, ver in VALORES:
            if k in clase.PARAMS and ver(v):
                ctx.evaluar(v[k], t)
                params[k] = v[k]
        for k, ver in OPCIONES:
            if k in clase.PARAMS and ver(v):
                params[k] = v[k]
        for k, ver in (("objeto", _ve_objeto), ("objeto_extension", _ve_objeto_extension)):
            if k in clase.PARAMS and ver(v):
                params[k] = ref1(v, k)
                if params[k] is None and not _ruta_eje(v):
                    raise ErrorComando("Seleccioná el objeto.")
        if metodo in PERPENDICULARES and len(lista) == 1:
            hit = v["r0"][0]
            if hit["ref"]["tipo"] not in ("cara", "plano"):
                raise ErrorComando("Seleccioná el punto.")
            params["lugar"] = lugar_en(hit["ref"], hit.get("punto"), ctx.estado)
        if clase is OpPlano and tipo == "angulo":
            params["eje_0"] = v.get("eje_0") or _eje_cero_de(ctx, lista[0])
        self.nombre_base = NOMBRES[TIPO_DE_CLASE[clase]][0]
        return self.crear_op(clase, v, ctx, **params)

    def desde_op(self, op, ctx):
        v = dict(op.p, tipo=TIPO_DE_CLASE[self.CLASE_OP], metodo=self.CLAVE)
        lista = op.p.get("refs") or []
        if self.CLASE_OP is OpPlano and not lista and op.p.get("base") and op.p.get("base") != "cara":
            lista = [{"tipo": "plano", "id": op.p["base"]}]       # proyectos viejos (base/marco)
        if self.CLAVE in RUTAS:
            v["r0"] = hits(lista, ctx.estado)
        else:
            for (k, *_), ref in zip(_filas(self.CLAVE), lista, strict=False):
                v[k] = [hit_desde_ref(ref, ctx.estado)]
        for k in ("objeto", "objeto_extension"):
            v[k] = hits([op.p.get(k)], ctx.estado)
        if op.p.get("lugar") and v.get("r0"):
            lugar = _entidad(ctx, {"lugar": [{"ref": op.p["lugar"]}]}, "lugar")
            v["r0"][0]["punto"] = None if lugar is None else lugar.punto
        return v

    def nombre_nuevo(self, ctx):
        base = getattr(self, "nombre_base", NOMBRES[TIPO_DE_CLASE[self.CLASE_OP]][0])
        usados = {o.nombre for o in ctx.doc.operaciones}
        n = 1
        while f"{base}{n}" in usados:
            n += 1
        return f"{base}{n}"

    def manipuladores(self, ctx, v):
        asas = ASAS.get(v.get("metodo"))
        if asas is None:
            return []
        try:
            return asas(self, ctx, v)
        except Exception:  # noqa: BLE001 — con algo a medio elegir no hay asa; el diálogo sigue
            return []


def _entidad(ctx, v, clave="r0"):
    from .. import manipuladores as mp
    return mp.entidad(v[clave][0], ctx.estado) if v.get(clave) else None


def _asas_desfase(self, ctx, v):
    """Flecha de distancia desde el centro del plano o de la cara de referencia, por su normal."""
    from ...timeline import entidades as ent
    from .. import manipuladores as mp
    e = _entidad(ctx, v)
    if e is None or v.get("extension") != "distancia":
        return []
    plano = ent.como_plano(e)
    return [mp.Flecha("distancia", ent.como_punto(e) if e.tipo == "cara" else plano.origen, plano.normal)]


def _asas_ruta(self, ctx, v):
    """Asa que se desliza por la ruta. Escribe la posición de 0 a 1 o, con distancia absoluta, los milímetros; sobre un eje
    es una flecha. También se puede pasar de los extremos."""
    from ...nucleo import construccion as cs
    from ...timeline.ops_construir import _ruta
    from .. import manipuladores as mp
    e = _entidad(ctx, v)
    if e is None:
        return []
    if _ruta_eje(v):
        return [mp.Flecha("distancia", *e.eje)]
    if v.get("tipo_distancia") == "objeto":
        return []
    aristas = _ruta([mp.entidad(h, ctx.estado) for h in v["r0"]], v, ctx.estado)
    ts = np.linspace(-0.25, 1.25, 121)
    if v.get("tipo_distancia") == "absoluto":
        return [mp.AsaRuta("distancia", ts, cs.muestras_ruta(aristas, ts), cs.largo_ruta(aristas))]
    return [mp.AsaRuta("posicion", ts, cs.muestras_ruta(aristas, ts))]


def _asas_tangente(self, ctx, v):
    """Arco del ángulo alrededor del eje de la cara cilíndrica o cónica, a media altura."""
    from ...nucleo import construccion as cs
    from ...timeline import entidades as ent
    from .. import manipuladores as mp
    e, ref = _entidad(ctx, v), _entidad(ctx, v, "r1")
    if e is None or e.forma is None:
        return []
    centro, eje, cero, radio = cs.marco_tangente(e.forma, ent.como_plano(ref) if ref is not None else None)
    return [mp.Angulo("angulo", centro, eje, cero, radio)]


def _eje_cero_de(ctx, ref):
    """Eje del mundo del 0° del «Plano en el ángulo», fijado al crear (B-257); None si la referencia no es un eje."""
    from ...timeline import entidades as ent
    from ...timeline.ops_construir import eje_cero
    from .. import manipuladores as mp
    e = mp.entidad(ref, ctx.estado)
    try:
        return eje_cero(ent.como_eje(e)[1]) if e is not None else None
    except ent.ErrorReferencia:
        return None


def _asas_angulo(self, ctx, v):
    from ...timeline import entidades as ent
    from ...timeline.ops_construir import _plano_por_eje, eje_cero
    from .. import manipuladores as mp
    e = _entidad(ctx, v)
    if e is None:
        return []
    punto, d = ent.como_eje(e)
    a = mp.unitario(d)
    n0 = np.asarray(_plano_por_eje(e, v.get("eje_0") or eje_cero(d)).normal, float)
    n0 = n0 - a * float(n0 @ a)
    if np.linalg.norm(n0) < 1e-9:
        return []
    punto = np.asarray(punto, float)
    if e.tipo == "arista" and e.forma is not None:           # Fusion centra el anillo en el medio de la arista, no en un extremo
        from ...nucleo import geometria as geo
        pts = np.asarray(geo.polilinea_arista(e.forma), float)
        punto = punto + a * float(((pts[0] + pts[-1]) / 2 - punto) @ a)
    return [mp.AnilloAngulo("angulo", punto, a, np.cross(a, mp.unitario(n0)))]      # P-139: el anillo de Fusion, centrado en la arista


def _asas_perpendicular(self, ctx, v):
    """Flecha de la distancia sobre la normal del plano (sin correr)."""
    from .. import manipuladores as mp
    op = self.construir(v, ctx)
    plano = calcular_plano(dict(op.p, desfase="0 mm"), [mp.entidad(r, ctx.estado) for r in op.p["refs"]], ctx, ctx.estado)
    return [mp.Flecha("desfase", plano.origen, plano.normal)]


TITULOS = {OpPlano: TIPOS_PLANO, OpEje: TIPOS_EJE, OpPunto: TIPOS_PUNTO}
ASAS = {"plano_desfase": _asas_desfase, "plano_angulo": _asas_angulo, "plano_tangente": _asas_tangente,
        "plano_perpendicular": _asas_perpendicular, "plano_ruta": _asas_ruta, "punto_ruta": _asas_ruta}
COMANDOS = [type(f"Construir_{k}", (GeometriaConstruccion,),
                 {"CLAVE": k, "TITULO": TITULOS[d[0]][d[1]], "ICONO": k, "CLASE_OP": d[0], "TIPO_CONSTR": d[1],
                  "AYUDA": f"CONSTRUIR › {d[2]}."}) for k, d in METODOS.items()]
CATALOGO_LOCAL = {c.CLAVE: c for c in COMANDOS}
INFO_SCU = ("Seleccione el punto de referencia para el sistema de coordenadas.\n\n"
            "A continuación, ajuste el ángulo y el desfase desde la posición original.")
CONSEJOS_SCU = "Con el puntero sobre una cara, mantenga Ctrl para forzar a los puntos de esa cara."


def _hay_origen(v):
    return bool(v.get("origen"))


class SCU(Comando):
    CLAVE, TITULO, ICONO = "scu", "Sistema de coordenadas de usuario (SCU)", "scu"
    AYUDA = "Crea un sistema de coordenadas con su origen, ejes y planos."
    CLASE_OP, ANCHO_PANEL = OpSCU, "ancho"
    MODIFICADORES = {"Ctrl": "forzar a los puntos de la cara"}

    def campos(self, ctx):
        return [Seleccion("origen", "Forzar", PUNTO, texto_boton="Seleccionar"),
                *(Expresion(k, e, "0 deg", ANGULO, visible_si=_hay_origen) for k, e in (("rx", "Ángulo X"), ("ry", "Ángulo Y"), ("rz", "Ángulo Z"))),
                *(Expresion(k, e, "0 mm", visible_si=_hay_origen) for k, e in (("dx", "Desfase X"), ("dy", "Desfase Y"), ("dz", "Desfase Z"))),
                Seleccion("eje_z", "Eje Z", DIRECCION, minimo=0, texto_boton="Seleccionar", visible_si=_hay_origen, grupo="Alineación"),
                Seleccion("eje_x", "Eje X", DIRECCION, minimo=0, texto_boton="Seleccionar", visible_si=_hay_origen, grupo="Alineación")]

    def preparar_panel(self, panel):
        from ..panel_info import PanelInfo
        self.info = PanelInfo(panel.parent() or panel.visor, "Información del sistema de coordenadas", INFO_SCU, CONSEJOS_SCU)

    def al_cerrar(self, ctx):
        info = getattr(self, "info", None)
        if info is not None:
            info.deleteLater()
            self.info = None

    def construir(self, v, ctx):
        if not v.get("origen"):
            raise ErrorComando("Seleccioná el punto de forzado.")
        return self.crear_op(OpSCU, v, ctx, origen=ref1(v, "origen"), eje_z=ref1(v, "eje_z"), eje_x=ref1(v, "eje_x"),
                             eje_y=v.get("eje_y"), **{k: v[k] for k in ("dx", "dy", "dz", "rx", "ry", "rz")})

    def desde_op(self, op, ctx):
        v = dict(op.p)
        for k in ("origen", "eje_x", "eje_z"):
            v[k] = hits([op.p[k]], ctx.estado) if op.p.get(k) else []
        return v

    def nombre_nuevo(self, ctx):
        usados = {o.nombre for o in ctx.doc.operaciones}
        n = 1
        while f"SCU{n}" in usados:
            n += 1
        return f"SCU{n}"


registrar(*COMANDOS, SCU)
# Editar un plano/eje/punto abre el comando de SU tipo (no el primero registrado para la clase).
POR_TIPO_CONSTRUCCION = {(c.CLASE_OP.TIPO, c.TIPO_CONSTR): c for c in COMANDOS}
