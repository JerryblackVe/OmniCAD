# -*- coding: utf-8 -*-
"""
CONSTRUIR de Fusion [SLD-CONSTRUCT-TOOLS]: planos, ejes, puntos y sistemas de coordenadas de usuario.

Los planos son `OpPlano` (en `operaciones.py`, con `tipo`); acá están el cálculo de cada tipo de plano
y las operaciones de ejes, puntos y SCU. Cada uno guarda referencias a lo elegido, así un plano medio
entre dos caras sigue a las caras cuando cambia una cota.
"""
import numpy as np

from ..nucleo import geometria as geo
from ..nucleo import referencias as refs
from ..nucleo.perfiles import aristas_boceto
from . import entidades as ent
from .operaciones import ANGULO, ErrorOperacion, Operacion, OpPlano, _resolver, registrar_operacion
from .parametros import LONGITUD_MAXIMA

TIPOS_PLANO = {"desfase": "Plano de desfase", "angulo": "Plano en el ángulo", "tangente": "Plano tangente",
               "medio": "Plano medio", "dos_aristas": "Plano a través de dos aristas",
               "tres_puntos": "Plano a través de tres puntos", "perpendicular": "Plano perpendicular",
               "ruta": "Plano en ruta"}
EXTENSIONES = ("distancia", "objeto")
DISTANCIAS_RUTA = ("proporcional", "absoluto", "objeto")
REDIMENSIONAR = ("predeterminado", "extendido")
# OpPlano vive en operaciones.py; sus listas de opciones, acá
OpPlano.OPCIONES = {"tipo": TIPOS_PLANO, "extension": EXTENSIONES, "direccion": ("U", "V"), "tipo_distancia": DISTANCIAS_RUTA,
                    "redimensionar": REDIMENSIONAR, "tipo_extension": EXTENSIONES}
TIPOS_EJE = {"cilindro": "Eje a través de cilindro/cono/toroide", "perpendicular_cara": "Eje perpendicular a la cara",
             "dos_planos": "Eje a través de dos planos", "dos_puntos": "Eje a través de dos puntos",
             "arista": "Eje a través de arista"}
TIPOS_PUNTO = {"vertice": "Punto en vértice", "dos_aristas": "Punto a través de dos aristas",
               "tres_planos": "Punto a través de tres planos", "centro": "Punto en el centro de círculo/esfera/toroide",
               "arista_plano": "Punto en arista y plano", "ruta": "Punto a lo largo de la ruta"}


def _a_tiro(punto):
    """P-93: lo construido queda a menos de 1 km del origen, como las cotas: más lejos el núcleo ya no calcula bien
    (una posición proporcional enorme o un lugar fuera de la cara llegaban a cualquier distancia)."""
    if np.abs(punto).max() > LONGITUD_MAXIMA:
        raise ErrorOperacion("Queda a más de 1.000.000 mm (1 km) del origen: acercalo (posición, distancia o lugar).")
    return punto


def _cs():
    from ..nucleo import construccion
    return construccion


def _eje(e):
    p, d = ent.como_eje(e)
    return _cs().Eje(np.asarray(p, float), np.asarray(d, float))


def _forma_o_plano(e):
    return e.forma if e.forma is not None else ent.como_plano(e)


_EJES_MUNDO = {"Z": (0.0, 0.0, 1.0), "Y": (0.0, 1.0, 0.0), "X": (1.0, 0.0, 0.0)}    # orden = preferencia en empate


def eje_cero(direccion):
    """Eje del mundo más perpendicular a `direccion` (empate: Z, luego Y, luego X): con él se arma el 0° del «Plano
    en el ángulo». Medido en Fusion (P-92 y B-257, 2026-11-08): arista a lo largo de X → horizontal; vertical →
    frontal; inclinada en XZ → normal Y; inclinada en YZ → normal X."""
    d = np.abs(np.asarray(direccion, float)) / (np.linalg.norm(direccion) or 1.0)
    return min(_EJES_MUNDO, key=lambda k: round(float(d["XYZ".index(k)]), 9))


def _plano_por_eje(e, eje_0=""):
    """Plano de referencia que contiene un eje (el ángulo 0 del «Plano en el ángulo»): el plano del boceto si es una
    línea de boceto; si no, el que contiene al eje y al eje del mundo `eje_0`, elegido al crear (`eje_cero`) para que
    un parámetro no lo haga saltar (B-257, como Fusion); nunca la cara vecina. Sin `eje_0` (pasos anteriores a B-257),
    la regla vieja: el plano más horizontal, o el frontal si el eje está a menos de ~26° de la vertical."""
    if e.tipo == "curva_boceto" and e.plano is not None:
        return e.plano
    p, d = ent.como_eje(e)
    d = np.asarray(d, float) / (np.linalg.norm(d) or 1.0)
    if not eje_0:
        ref = np.array([0.0, 0.0, 1.0]) if abs(d[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    else:
        ref = np.array(_EJES_MUNDO[eje_0 if isinstance(eje_0, str) and eje_0 in _EJES_MUNDO else eje_cero(d)])
        if np.linalg.norm(np.cross(d, ref)) < 1e-9:       # el eje quedó paralelo al elegido: se elige otro
            ref = np.array(_EJES_MUNDO[eje_cero(d)])
    n = ref - d * float(ref @ d)
    return geo.Plano.desde_marco(p, n, d)


def lugar_en(ref, punto, estado):
    """Referencia «forzado» al lugar `punto` de la cara o plano `ref` (el clic en la vista); sin punto, su centro."""
    e = _resolver(ref, estado)
    if ref["tipo"] == "plano":
        return {"tipo": "forzado", "modo": "lugar_plano", "base": ref, "uv": list(e.plano.a_uv(e.plano.origen if punto is None else punto))}
    if punto is None:
        return {"tipo": "forzado", "modo": "centro_cara", "base": ref}
    return {"tipo": "forzado", "modo": "lugar_cara", "base": ref, "uv": _cs().lugar_en_cara(e.forma, punto)}


def _objeto(p, clave, estado):
    """Punto de la referencia de un campo «Al objeto»."""
    if not p.get(clave):
        raise ErrorOperacion("Elegí el objeto.")
    return ent.como_punto(_resolver(p[clave], estado))


def _vecinas(e, estado):
    """Aristas del cuerpo o curvas del boceto donde está la arista `e`: donde se busca su cadena tangente."""
    if e.cuerpo is not None:
        return refs.subformas(estado.cuerpos[e.cuerpo].forma, "arista")
    if e.boceto is not None:
        return [a for _c, a in aristas_boceto(e.boceto.boceto.geometria(incluir_construccion=True), e.boceto.plano)]
    return []


def _ruta(E, p, estado):
    """Aristas de la ruta. Con Cadena tangente, una sola arista elegida arrastra a las que siguen por tangencia."""
    if any(e.forma is None for e in E):
        raise ErrorOperacion("La ruta tiene que ser una arista, una curva de boceto o una cadena de ellas.")
    if p.get("cadena_tangente") and len(E) == 1:
        return _cs().cadena_tangente(E[0].forma, _vecinas(E[0], estado))
    return [e.forma for e in E]


def _distancia_ruta(p, aristas, ctx, estado):
    """(distancia, absoluta) según el tipo de distancia: fracción del largo, milímetros o hasta el objeto."""
    modo = p.get("tipo_distancia", "proporcional")
    if modo == "absoluto":
        return ctx.evaluar(p.get("distancia", "0")), True
    if modo == "objeto":
        return _cs().distancia_en_ruta(aristas, _objeto(p, "objeto", estado)), True
    return ctx.evaluar(p.get("posicion", "0.5"), "escalar"), False


def _plano_perpendicular(p, E, ctx, estado):
    cs, base, d = _cs(), _forma_o_plano(E[0]), ctx.evaluar(p.get("desfase", "0"))
    plana = E[0].plano is not None
    if len(E) > 1 and E[1].tipo in ("plano", "cara"):
        if not plana:
            raise ErrorOperacion("En una cara curva, el Objeto de referencia tiene que ser un punto.")
        return cs.plano_perpendicular_en_plano(base, ent.como_plano(E[1]), distancia=d)
    punto = ent.como_punto(E[1]) if len(E) > 1 else _objeto(p, "lugar", estado)
    return cs.plano_perpendicular(base, punto, direccion=p.get("direccion", "U") if plana else "U", distancia=d)


def calcular_plano(p, entidades, ctx, estado):
    plano = _plano_de_tipo(p, entidades, ctx, estado)
    _a_tiro(plano.origen)
    return plano


def _plano_de_tipo(p, entidades, ctx, estado):
    cs, t, E = _cs(), p.get("tipo", "desfase"), entidades
    faltan = {"desfase": 1, "angulo": 1, "tangente": 1, "medio": 2, "dos_aristas": 2, "tres_puntos": 3,
              "perpendicular": 1 if p.get("lugar") else 2, "ruta": 1}[t]
    if len(E) < faltan:
        raise ErrorOperacion("Faltan referencias para el plano.")
    extra = ctx.evaluar(p.get("desfase", "0"))
    if t == "desfase":
        base = ent.como_plano(E[0])
        d = (float((_objeto(p, "objeto", estado) - base.origen) @ base.normal) if p.get("extension") == "objeto"
             else ctx.evaluar(p.get("distancia", "0")))
        return cs.plano_desfase(base, d + extra)
    if t == "angulo":
        if E[0].tipo not in ("eje", "arista", "curva_boceto"):     # B-261: el mismo filtro que la herramienta de creación
            raise ErrorOperacion("El plano en el ángulo necesita un eje, una arista o una línea de boceto.")
        if E[0].tipo != "eje" and E[0].forma is not None:     # P-93: recta, como Fusion (una circular daba su eje)
            cs.eje_arista(E[0].forma)
        punto, direccion = ent.como_eje(E[0])
        return cs.plano_en_angulo(_plano_por_eje(E[0], p.get("eje_0")), punto, direccion, ctx.evaluar(p.get("angulo", "0"), ANGULO), desfase=extra)
    if t == "tangente":
        ref = ent.como_plano(E[1]) if len(E) > 1 else None
        return cs.plano_tangente(E[0].forma, ctx.evaluar(p.get("angulo", "0"), ANGULO), ref, desfase=extra)
    if t == "medio":
        return cs.plano_medio(ent.como_plano(E[0]), ent.como_plano(E[1]))
    if t == "dos_aristas":
        return cs.plano_dos_aristas(_eje(E[0]), _eje(E[1]), desfase=extra)
    if t == "tres_puntos":
        return cs.plano_tres_puntos(*(ent.como_punto(e) for e in E[:3]), desfase=extra)
    if t == "perpendicular":
        return _plano_perpendicular(p, E, ctx, estado)
    if t == "ruta":
        if E[0].tipo == "eje":      # el eje no tiene largo: la distancia se mide desde su punto o desde el Objeto de referencia
            q, d = (np.asarray(x, float) for x in E[0].eje)
            if p.get("objeto"):
                q = q + d * float((_objeto(p, "objeto", estado) - q) @ d)
            return geo.Plano.desde_marco(q + d * ctx.evaluar(p.get("distancia", "0")), d, np.zeros(3), "Plano en ruta").desplazado(extra)
        aristas = _ruta(E, p, estado)
        distancia, absoluta = _distancia_ruta(p, aristas, ctx, estado)
        return cs.plano_en_ruta(aristas, distancia, absoluta=absoluta).desplazado(extra)
    raise ErrorOperacion(f"Tipo de plano desconocido: {t}")


def _puntos_de(e):
    """Puntos que representan lo elegido, para ajustar a ellos el dibujo de un plano o de un eje."""
    if e.forma is not None:
        a, b = geo.caja_envolvente(e.forma)
        return [np.array((x, y, z), float) for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])]
    if e.punto is not None:
        return [np.asarray(e.punto, float)]
    return [np.asarray(e.eje[0], float)] if e.eje is not None else []


def _lado(p, ctx):
    """Medida pedida con Tipo de extensión «Distancia»; 0 = la que sale de lo elegido."""
    if p.get("tipo_extension") != "distancia":
        return 0.0
    lado = ctx.evaluar(p.get("medida", "0"))
    if lado < 0:
        raise ErrorOperacion("La medida del plano o del eje no puede ser negativa.")
    return lado


def _puntos_objeto(p, estado):
    """Puntos del objeto hasta donde llega el plano o eje, con Tipo de extensión «Al objeto»."""
    objeto = p.get("objeto_extension") if p.get("tipo_extension") == "objeto" else None
    return _puntos_de(_resolver(objeto, estado)) if objeto else []


def medida_plano(p, plano, E, ctx, estado):
    """Cómo se dibuja el plano: Predeterminado ajusta a lo elegido; Tipo de extensión fija el lado o llega al objeto."""
    limites, lado = None, _lado(p, ctx)
    uv = np.array([plano.a_uv(q) for e in E for q in _puntos_de(e)], float)
    a, b = (uv.min(axis=0), uv.max(axis=0)) if len(uv) else (np.zeros(2), np.zeros(2))
    if lado > 0:
        c = (a + b) / 2
        a, b = c - lado / 2, c + lado / 2
    elif len(uv):
        m = max(float((b - a).max()) * 0.1, 2.0) + np.maximum((b - a).max() / 2 - (b - a), 0.0) / 2     # nunca una tira finita
        a, b = a - m, b + m
    objeto = np.array([plano.a_uv(q) for q in _puntos_objeto(p, estado)], float).reshape(-1, 2)
    if lado > 0 or len(uv) or len(objeto):
        limites = (*np.minimum(a, objeto.min(axis=0, initial=np.inf)).tolist(), *np.maximum(b, objeto.max(axis=0, initial=-np.inf)).tolist())
    return {"redimensionar": p.get("redimensionar", "predeterminado"), "limites": limites}


def medida_eje(p, punto, direccion, E, ctx, estado):
    """Lo mismo para un eje: `limites` son (t0, t1) a lo largo de su dirección, medidos desde `punto`."""
    limites, lado = None, _lado(p, ctx)
    ts = [float((q - punto) @ direccion) for e in E for q in _puntos_de(e)]
    a, b = (min(ts), max(ts)) if ts else (0.0, 0.0)
    if lado > 0:
        a, b = (a + b - lado) / 2, (a + b + lado) / 2
    elif ts:
        m = max((b - a) * 0.1, 2.0)
        a, b = a - m, b + m
    objeto = [float((q - punto) @ direccion) for q in _puntos_objeto(p, estado)]
    if lado > 0 or ts or objeto:
        limites = (min([a, *objeto]), max([b, *objeto]))
    return {"redimensionar": p.get("redimensionar", "predeterminado"), "limites": limites}


class OpEje(Operacion):
    """Ejes de construcción de Fusion [SLD-CONSTRUCT-AXIS-*]."""
    TIPO, ETIQUETA, ICONO = "eje", "Eje", "╱"
    PARAMS = {"tipo": "arista", "refs": [], "lugar": None, "redimensionar": "predeterminado", "tipo_extension": "distancia",
              "medida": "0 mm", "objeto_extension": None}
    EXPRESIONES = ("medida",)
    OPCIONES = {"tipo": TIPOS_EJE, "redimensionar": REDIMENSIONAR, "tipo_extension": EXTENSIONES}

    def dependencias(self):
        return ent.dependencias_de(self.p["refs"], self.p["lugar"], self.p["objeto_extension"]) - {self.id}

    def ejecutar(self, estado, ctx):
        cs, t = _cs(), self.p["tipo"]
        E = [_resolver(r, estado) for r in self.p["refs"]]
        faltan = {"cilindro": 1, "perpendicular_cara": 1 if self.p["lugar"] else 2, "dos_planos": 2, "dos_puntos": 2, "arista": 1}[t]
        if len(E) < faltan:
            raise ErrorOperacion("Faltan referencias para el eje.")
        if t == "cilindro":
            eje = cs.eje_cilindro(E[0].forma, esfera=False)
        elif t == "perpendicular_cara":
            eje = cs.eje_perpendicular_cara(_forma_o_plano(E[0]), ent.como_punto(E[1]) if len(E) > 1 else _objeto(self.p, "lugar", estado))
        elif t == "dos_planos":
            eje = cs.eje_dos_planos(ent.como_plano(E[0]), ent.como_plano(E[1]))
        elif t == "dos_puntos":
            eje = cs.eje_dos_puntos(ent.como_punto(E[0]), ent.como_punto(E[1]))
        else:
            eje = _eje(E[0])
        punto, direccion = _a_tiro(np.asarray(eje.punto, float)), np.asarray(eje.direccion, float)
        estado.ejes[self.id] = (punto, direccion, self.nombre)
        estado.medidas[self.id] = medida_eje(self.p, punto, direccion, E, ctx, estado)


class OpPunto(Operacion):
    """Puntos de construcción de Fusion [SLD-CONSTRUCT-POINT-*]."""
    TIPO, ETIQUETA, ICONO = "punto", "Punto", "•"
    PARAMS = {"tipo": "vertice", "refs": [], "posicion": "0.5", "tipo_distancia": "proporcional", "distancia": "0 mm",
              "cadena_tangente": False}
    EXPRESIONES = ("posicion", "distancia")
    OPCIONES = {"tipo": TIPOS_PUNTO, "tipo_distancia": ("proporcional", "absoluto")}

    def dependencias(self):
        return ent.dependencias_de(self.p["refs"]) - {self.id}

    def ejecutar(self, estado, ctx):
        cs, t = _cs(), self.p["tipo"]
        E = [_resolver(r, estado) for r in self.p["refs"]]
        faltan = {"vertice": 1, "dos_aristas": 2, "tres_planos": 3, "centro": 1, "arista_plano": 2, "ruta": 1}[t]
        if len(E) < faltan:
            raise ErrorOperacion("Faltan referencias para el punto.")
        if t == "vertice":
            p = ent.como_punto(E[0])
        elif t == "dos_aristas":
            p = cs.punto_dos_aristas(*(e.forma if e.forma is not None and e.eje is None else _eje(e) for e in E[:2]))
        elif t == "tres_planos":
            p = cs.punto_tres_planos(*(ent.como_plano(e) for e in E[:3]))
        elif t == "centro":
            p = cs.punto_centro(E[0].forma)
        elif t == "arista_plano":
            p = cs.punto_arista_plano(_eje(E[0]), ent.como_plano(E[1]))
        else:
            aristas = _ruta(E, self.p, estado)
            distancia, absoluta = _distancia_ruta(self.p, aristas, ctx, estado)
            p = cs.punto_en_ruta(aristas, distancia, absoluta=absoluta)
        estado.puntos[self.id] = (_a_tiro(np.asarray(p, float)), self.nombre)


class OpSCU(Operacion):
    """Sistema de coordenadas de usuario de Fusion [SLD-DEFINE-UCS]: origen, alineación de Z y X (arista o cara; los
    pasos viejos traen X e Y), giros y desfases. Agrega su punto de origen, sus tres ejes y sus tres planos a la construcción."""
    TIPO, ETIQUETA, ICONO = "scu", "SCU", "⊹"
    PARAMS = {"origen": None, "eje_x": None, "eje_y": None, "eje_z": None, "rx": "0 deg", "ry": "0 deg", "rz": "0 deg",
              "dx": "0 mm", "dy": "0 mm", "dz": "0 mm"}
    EXPRESIONES = ("rx", "ry", "rz", "dx", "dy", "dz")

    def dependencias(self):
        return ent.dependencias_de(self.p["origen"], self.p["eje_x"], self.p["eje_y"], self.p["eje_z"]) - {self.id}

    def ejecutar(self, estado, ctx):
        p = self.p
        origen = ent.como_punto(_resolver(p["origen"], estado)) if p["origen"] else np.zeros(3)
        x = _eje(_resolver(p["eje_x"], estado)).direccion if p["eje_x"] else np.array([1.0, 0, 0])
        y = _eje(_resolver(p["eje_y"], estado)).direccion if p["eje_y"] else None
        z = _eje(_resolver(p["eje_z"], estado)).direccion if p["eje_z"] else None
        if p["eje_x"] and z is not None and np.linalg.norm(np.cross(x, z)) < 1e-9:     # B-259: sin X elegido, uno solo
            raise ErrorOperacion("Los ejes X y Z del SCU son paralelos.")
        A = lambda k: ctx.evaluar(p[k], ANGULO)  # noqa: E731
        L = lambda k: ctx.evaluar(p[k])  # noqa: E731
        m = _cs().scu(origen, x, y, eje_z=z, angulos=(A("rx"), A("ry"), A("rz")), desfase=(L("dx"), L("dy"), L("dz")))
        o, ex, ey, ez = (np.asarray(m[k], float) for k in ("origen", "x", "y", "z"))
        _a_tiro(o)
        n = self.nombre
        estado.puntos[f"{self.id}_o"] = (o, f"{n} origen")
        for k, d in (("x", ex), ("y", ey), ("z", ez)):
            estado.ejes[f"{self.id}_{k}"] = (o, d, f"{n} {k.upper()}")
        for k, normal, u in (("xy", ez, ex), ("xz", -ey, ex), ("yz", ex, ey)):
            estado.planos[f"{self.id}_{k}"] = geo.Plano.desde_marco(o, normal, u, f"{n} {k.upper()}")


registrar_operacion(OpEje, OpPunto, OpSCU)
