# -*- coding: utf-8 -*-
"""Asas en la vista (flechas, arcos, aros de posición y tríada) para comandos que solo tenían campos de texto.

Mismo criterio que Fusion: lo que se escribe en un campo de medida se puede tirar con el ratón en la vista.
Cada función `_asas_*` es el `Comando.manipuladores` de un comando y se engancha al final (`_enganchar`).
"""
import numpy as np

from ...nucleo import geometria as geo
from ...timeline import entidades as ent
from . import CATALOGO
from .comunes import evaluar_o_cero


def _mp():
    from .. import manipuladores as mp
    return mp


def _cuerpos_ids(v, clave="cuerpos"):
    return [h["ref"]["cuerpo"] for h in v.get(clave) or [] if h["ref"].get("tipo") == "cuerpo"]


def _centro_cuerpos(ctx, v, clave="cuerpos"):
    """Centro de la caja envolvente de los cuerpos elegidos (None si no hay ninguno)."""
    centros = []
    for c in _cuerpos_ids(v, clave):
        if c not in ctx.estado.cuerpos:
            continue
        try:
            caja = geo.caja_envolvente(ctx.estado.cuerpos[c].forma)
        except Exception:  # noqa: BLE001 — cuerpos de malla: sin caja exacta
            caja = None
        if caja:
            centros.append((np.array(caja[0]) + np.array(caja[1])) / 2)
    return np.mean(centros, axis=0) if centros else None


def _punto_de(ctx, hit):
    """Punto 3D de una selección (vértice, punto de construcción…) o None."""
    mp = _mp()
    try:
        return np.asarray(ent.como_punto(mp.entidad(hit, ctx.estado)), float)
    except Exception:  # noqa: BLE001
        return None


def _direccion_de(ctx, hit):
    try:
        return _mp().unitario(ent.direccion(_mp().entidad(hit, ctx.estado)))
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- superficies
def _asas_desfase_superficie(self, ctx, v):
    from .modificar import _cara_y_normal
    base = _cara_y_normal(ctx, v.get("caras"))
    return [_mp().Flecha("distancia", base[0], base[1])] if base is not None else []


def _asas_engrosar(self, ctx, v):
    from .modificar import _cara_y_normal
    base = _cara_y_normal(ctx, v.get("caras"))
    if base is None:
        return []
    # «Simétrica»: el espesor es el total y se reparte a los dos lados
    return [_mp().Flecha("espesor", base[0], base[1], factor=0.5 if v.get("direccion") == "simetrica" else 1.0)]


def _asas_extruir_superficie(self, ctx, v):
    mp = _mp()
    if v.get("direccion"):                    # con una dirección elegida el origen no es la normal del boceto
        return []
    base = mp.base_perfiles(v.get("curvas"), ctx.estado)
    if base is None:
        return []
    centro, plano, _formas = base
    return [mp.Flecha("distancia", centro, mp.unitario(plano.normal), factor=0.5 if v.get("simetrica") else 1.0)]


# ---------------------------------------------------------------- patrones
def _asas_patron_rectangular(self, ctx, v):
    mp = _mp()
    centro = _centro_cuerpos(ctx, v)
    if centro is None:
        return []
    salida = []
    for dir_clave, dist_clave in (("dir1", "d1"), ("dir2", "d2")):
        if v.get(dir_clave):
            d = _direccion_de(ctx, v[dir_clave][0])
            if d is not None and np.linalg.norm(d) > 1e-9:
                salida.append(mp.Flecha(dist_clave, centro, d))
    return salida


def _asas_patron_circular(self, ctx, v):
    mp = _mp()
    centro = _centro_cuerpos(ctx, v)
    if centro is None or not v.get("eje"):
        return []
    try:
        punto, d = ent.como_eje(mp.entidad(v["eje"][0], ctx.estado))
    except Exception:  # noqa: BLE001
        return []
    d = mp.unitario(d)
    pie = np.asarray(punto, float) + d * float((centro - punto) @ d)
    radio = float(np.linalg.norm(centro - pie))
    return [mp.Angulo("angulo", pie, d, centro - pie, radio if radio > 1e-6 else None)]


# ---------------------------------------------------------------- dibujos sobre un plano
def _asas_desplazar_en_plano(self, ctx, v):
    """Aro de posición del dibujo sobre el plano (escribe Desplazamiento X / Y)."""
    mp = _mp()
    sel = v.get("plano") or []
    plano = sel[0].get("plano") if sel else None
    if plano is None:
        return []
    o, u, w = (np.asarray(x, float) for x in (plano.origen, plano.u, plano.v))
    dx, dy = evaluar_o_cero(ctx, v.get("dx")), evaluar_o_cero(ctx, v.get("dy"))

    def al_mover(q):
        d = np.asarray(q, float) - o
        return {"dx": float(d @ u), "dy": float(d @ w)}
    return [mp.Posicion("desplazamiento", o + u * dx + w * dy, plano.normal, al_mover)]


# ---------------------------------------------------------------- sistemas de coordenadas y uniones
def _asas_scu(self, ctx, v):
    """Tríada en el origen del SCU: flechas = Desfase X/Y/Z, arcos = Ángulo X/Y/Z."""
    mp = _mp()
    origen = _punto_de(ctx, v["origen"][0]) if v.get("origen") else np.zeros(3)
    if origen is None:
        return []
    L = lambda k: evaluar_o_cero(ctx, v.get(k))  # noqa: E731
    return [mp.Triada(origen + [L("dx"), L("dy"), L("dz")], claves=("dx", "dy", "dz"), giros=("rx", "ry", "rz"))]


def _asas_union(clave_origen):
    def asas(self, ctx, v):
        mp = _mp()
        if not v.get(clave_origen) or "dx" not in v:      # «Unión construida» no tiene desfases
            return []
        origen = _punto_de(ctx, v[clave_origen][0])
        if origen is None:
            return []
        L = lambda k: evaluar_o_cero(ctx, v.get(k))  # noqa: E731
        return [mp.Triada(origen + [L("dx"), L("dy"), L("dz")], claves=("dx", "dy", "dz"), giros=None)]
    return asas


# ---------------------------------------------------------------- bobina
def _asas_bobina(self, ctx, v):
    """Asa redonda en el borde de la hélice: el valor es el diámetro (como el agujero)."""
    mp = _mp()
    sel = v.get("plano") or []
    plano = sel[0].get("plano") if sel else None
    if plano is not None:
        origen, normal = np.asarray(plano.origen, float), np.asarray(plano.normal, float)
    else:
        origen, normal = np.zeros(3), np.array([0.0, 0.0, 1.0])
    centro = _punto_de(ctx, v["centro"][0]) if v.get("centro") else origen
    if centro is None:
        return []
    radial, _ = mp.perpendiculares(normal)
    return [mp.AsaRadial("diametro", centro, radial, factor=0.5, minimo=0.1)]


# ---------------------------------------------------------------- ayudas de curvas y aristas
def _curva_de(forma):
    """BRepAdaptor_Curve de la primera arista de una forma (arista o alambre); None si no hay."""
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopoDS import TopoDS
    for e in geo._explorar(forma, TopAbs_EDGE):
        return BRepAdaptor_Curve(TopoDS.Edge(e))
    return None


def _punto_y_tangente(forma, fraccion=0.5):
    """(punto, tangente unitaria) de la primera arista de `forma` a esa fracción de su recorrido."""
    from OCP.gp import gp_Pnt, gp_Vec
    c = _curva_de(forma)
    if c is None:
        return None
    a, b = c.FirstParameter(), c.LastParameter()
    p, d = gp_Pnt(), gp_Vec()
    c.D1(a + (b - a) * fraccion, p, d)
    t = np.array([d.X(), d.Y(), d.Z()], float)
    n = float(np.linalg.norm(t))
    return np.array([p.X(), p.Y(), p.Z()], float), (t / n if n > 1e-12 else t)


def _forma_de(ctx, hit):
    e = _mp().entidad(hit, ctx.estado)
    return e.forma if e is not None else None


def _saliente_de_arista(ctx, hit):
    """(punto medio de la arista, dirección que sale de su cara) para tirar de dobladillos y extensiones."""
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE

    from ...nucleo.solidos_modificar import _ancestros, _padres, _punto_normal
    e = _mp().entidad(hit, ctx.estado)
    if e is None or e.forma is None or getattr(e, "cuerpo", None) not in ctx.estado.cuerpos:
        return None
    punto_tang = _punto_y_tangente(e.forma)
    if punto_tang is None:
        return None
    medio, t = punto_tang
    cuerpo = ctx.estado.cuerpos[e.cuerpo].forma
    caras = _padres(_ancestros(cuerpo, TopAbs_EDGE, TopAbs_FACE), e.forma)
    if not caras:
        return None
    from OCP.TopoDS import TopoDS
    cara = TopoDS.Face(caras[0])
    _p, n = _punto_normal(cara)
    d = np.cross(np.asarray(n, float), t)
    if np.linalg.norm(d) < 1e-9:
        return None
    d = d / np.linalg.norm(d)
    if float(d @ (medio - np.array(geo.centro_masa(cara, True)))) < 0:
        d = -d
    return medio, d


# ---------------------------------------------------------------- nervio, red, repujado, rosca, tubería
def _asas_nervio(self, ctx, v):
    mp = _mp()
    base = mp.base_perfiles(v.get("curvas"), ctx.estado)
    if base is None:
        return []
    _centro, plano, formas = base
    n = mp.unitario(plano.normal) * (-1.0 if v.get("invertir") else 1.0)
    pt = _punto_y_tangente(formas[0]) if formas else None
    salida = []
    if pt is not None:
        lateral = np.cross(mp.unitario(plano.normal), pt[1])
        if np.linalg.norm(lateral) > 1e-9:
            salida.append(mp.Flecha("espesor", pt[0], lateral, factor=0.5 if v.get("direccion") == "simetrica" else 1.0,
                                    minimo=0.0))
        if v.get("extension") == "profundidad":
            salida.append(mp.Flecha("profundidad", pt[0], n, minimo=0.0))
    return salida


def _asas_repujado(self, ctx, v):
    mp = _mp()
    base = mp.base_perfiles(v.get("perfiles"), ctx.estado)
    cara = _forma_de(ctx, v["cara"][0]) if v.get("cara") else None
    if base is None or cara is None:
        return []
    punto, n = mp.punto_normal_cara(cara)
    centro = base[0] + n * float((punto - base[0]) @ n)         # el centro del perfil, sobre la cara
    return [mp.Flecha("profundidad", centro, n * (1.0 if v.get("tipo") != "grabado" else -1.0), minimo=0.0)]


def _asas_rosca(self, ctx, v):
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder
    mp = _mp()
    if v.get("largo_completo") or not v.get("caras"):
        return []
    forma = _forma_de(ctx, v["caras"][0])
    if forma is None:
        return []
    sup = BRepAdaptor_Surface(forma)
    if sup.GetType() != GeomAbs_Cylinder:
        return []
    eje = sup.Cylinder().Axis()
    loc = np.array([eje.Location().X(), eje.Location().Y(), eje.Location().Z()], float)
    d = np.array([eje.Direction().X(), eje.Direction().Y(), eje.Direction().Z()], float)
    if v.get("invertir"):
        inicio, d = loc + d * sup.LastVParameter(), -d
    else:
        inicio = loc + d * sup.FirstVParameter()
    return [mp.Flecha("desfase", inicio, d),
            mp.Flecha("longitud", inicio + d * evaluar_o_cero(ctx, v.get("desfase")), d, minimo=0.0)]


def _asas_tuberia(self, ctx, v):
    mp = _mp()
    forma = _forma_de(ctx, v["ruta"][0]) if v.get("ruta") else None
    pt = _punto_y_tangente(forma, 0.0) if forma is not None else None
    if pt is None:
        return []
    radial, _ = mp.perpendiculares(pt[1])
    return [mp.AsaRadial("tamano", pt[0], radial, factor=0.5, minimo=0.1)]


# ---------------------------------------------------------------- chapa y superficies con aristas
def _asas_dobladillo(self, ctx, v):
    if not v.get("aristas"):
        return []
    s = _saliente_de_arista(ctx, v["aristas"][0])
    return [_mp().Flecha("longitud", s[0], s[1], minimo=0.0)] if s is not None else []


def _asas_extender(self, ctx, v):
    if not v.get("aristas"):
        return []
    s = _saliente_de_arista(ctx, v["aristas"][0])
    return [_mp().Flecha("distancia", s[0], s[1])] if s is not None else []


def _asas_reglada(self, ctx, v):
    if not v.get("aristas") or not v.get("direccion"):
        return []
    forma = _forma_de(ctx, v["aristas"][0])
    pt = _punto_y_tangente(forma) if forma is not None else None
    d = _direccion_de(ctx, v["direccion"][0])
    if pt is None or d is None:
        return []
    return [_mp().Flecha("distancia", pt[0], d)]


def _asas_empalme_superficie(self, ctx, v):
    from .modificar import _flecha_arista
    try:
        return _flecha_arista(ctx, v.get("aristas"), "medida", chaflan=v.get("tipo") == "chaflan")
    except Exception:  # noqa: BLE001 — una arista suelta de superficie puede no tener ángulo definido
        return []


def _asas_plegar(self, ctx, v):
    mp = _mp()
    if not v.get("lineas") or not v.get("cara"):
        return []
    linea = _forma_de(ctx, v["lineas"][0])
    cara = _forma_de(ctx, v["cara"][0])
    if linea is None or cara is None:
        return []
    pt = _punto_y_tangente(linea)
    if pt is None:
        return []
    _p, n = mp.punto_normal_cara(cara)
    inicio = np.cross(pt[1], n)                   # dentro de la cara, perpendicular a la línea de plegado
    return [mp.Angulo("angulo", pt[0], pt[1], inicio, 25.0)]


def _asas_plano_angulo(self, ctx, v):
    from ...timeline.ops_construir import _plano_por_eje
    mp = _mp()
    e = mp.entidad(v["r0"][0], ctx.estado) if v.get("r0") else None
    if e is None:
        return []
    try:
        punto, d = ent.como_eje(e)
        base = _plano_por_eje(e)
    except Exception:  # noqa: BLE001
        return []
    a = mp.unitario(d)
    n0 = np.asarray(base.normal, float)
    n0 = n0 - a * float(n0 @ a)
    if np.linalg.norm(n0) < 1e-9:
        return []
    return [mp.Angulo("angulo", np.asarray(punto, float), a, np.cross(a, mp.unitario(n0)), 25.0)]


def _asas_desmoldeo(self, ctx, v):
    mp = _mp()
    if not v.get("plano") or not v.get("caras"):
        return []
    try:
        e = mp.entidad(v["plano"][0], ctx.estado)
        plano = ent.como_plano(e)
        cara = _forma_de(ctx, v["caras"][0])
        c_f = np.array(geo.centro_masa(cara, True), float)
        _p, n_f = mp.punto_normal_cara(cara)
    except Exception:  # noqa: BLE001
        return []
    n_p = mp.unitario(plano.normal)
    eje = np.cross(n_f, n_p)
    if np.linalg.norm(eje) < 1e-6:
        return []
    eje = eje / np.linalg.norm(eje)
    w = np.cross(eje, n_f)                         # en la cara, perpendicular a la línea neutra
    den = float(n_p @ w)
    if abs(den) < 1e-9:
        return []
    punto = c_f + w * (-float(n_p @ (c_f - np.asarray(plano.origen, float))) / den)
    salida = [mp.Angulo("angulo", punto, eje, w, 25.0)]
    if v.get("lados") == "dos":
        salida.append(mp.Angulo("angulo2", punto, -eje, w, 25.0))
    return salida


def _asas_patron_ruta(self, ctx, v):
    mp = _mp()
    forma = _forma_de(ctx, v["ruta"][0]) if v.get("ruta") else None
    pt = _punto_y_tangente(forma, 0.0) if forma is not None else None
    return [mp.Flecha("d1", pt[0], pt[1])] if pt is not None else []


def _enganchar():
    tabla = {
        "sup_desfase": _asas_desfase_superficie, "engrosar": _asas_engrosar, "sup_extruir": _asas_extruir_superficie,
        "patron_rectangular_3d": _asas_patron_rectangular, "patron_circular_3d": _asas_patron_circular,
        "lienzo": _asas_desplazar_en_plano, "calcomania": _asas_desplazar_en_plano,
        "scu": _asas_scu, "union": _asas_union("origen2"), "origen_union": _asas_union("origen"),
        "bobina": _asas_bobina,
        "nervio": _asas_nervio, "red": _asas_nervio, "repujado": _asas_repujado, "rosca": _asas_rosca,
        "tuberia": _asas_tuberia, "dobladillo": _asas_dobladillo, "extender_sup": _asas_extender,
        "reglada": _asas_reglada, "sup_empalme": _asas_empalme_superficie, "plegar": _asas_plegar,
        "plano_angulo": _asas_plano_angulo, "desmoldeo": _asas_desmoldeo, "patron_ruta": _asas_patron_ruta,
    }
    for clave, funcion in tabla.items():
        cls = CATALOGO.get(clave)
        if cls is not None:
            cls.manipuladores = funcion


_enganchar()
