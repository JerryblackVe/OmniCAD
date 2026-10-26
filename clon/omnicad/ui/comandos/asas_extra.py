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


# ---------------------------------------------------------------- escala
def _asas_escala(self, ctx, v):
    """Flecha del factor (o una por eje en «No uniforme») que sale del punto base; con factor 1 la punta queda a la
    mitad de la diagonal de los cuerpos, así que la escala se lee como «cuántas veces el tamaño»."""
    mp = _mp()
    base = _punto_de(ctx, v["punto"][0]) if v.get("punto") else np.zeros(3)
    if base is None:
        return []
    radios = []
    for c in _cuerpos_ids(v):
        try:
            caja = geo.caja_envolvente(ctx.estado.cuerpos[c].forma)
        except Exception:  # noqa: BLE001 — cuerpos de malla o ya borrados: sin caja exacta
            continue
        if caja:
            radios.append(float(np.linalg.norm(np.array(caja[1]) - np.array(caja[0]))) / 2)
    radio = max(radios, default=20.0)
    if v.get("tipo") == "no_uniforme":
        return [mp.Flecha(k, base, eje, factor=radio, minimo=0.001) for k, eje in
                (("fx", (1, 0, 0)), ("fy", (0, 1, 0)), ("fz", (0, 0, 1)))]
    return [mp.Flecha("factor", base, (1, 1, 1), factor=radio, minimo=0.001)]


# ---------------------------------------------------------------- planos de corte
def _asas_corte(clave_valor):
    """Flecha de la distancia del plano de corte (Análisis de sección y Sección de malla), sobre su normal,
    desde el centro de la cara o del plano elegidos."""
    def asas(self, ctx, v):
        mp = _mp()
        e = mp.entidad(v["plano"][0], ctx.estado) if v.get("plano") else None
        if e is None:
            return []
        try:
            plano = ent.como_plano(e)
            centro = ent.como_punto(e) if e.tipo == "cara" else plano.origen
        except Exception:  # noqa: BLE001
            return []
        return [mp.Flecha(clave_valor, centro, plano.normal)]
    return asas


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
    """Flecha de distancia y asa de conicidad; la dirección es la que usa la operación: la elegida, la normal
    del boceto o, con aristas de un cuerpo (sin plano), el eje Z."""
    mp = _mp()
    ents = [e for e in (mp.entidad(h, ctx.estado) for h in v.get("curvas") or []) if e is not None and e.forma is not None]
    if not ents:
        return []
    centro = np.mean([mp.centroide(e.forma) for e in ents], axis=0)
    if v.get("direccion"):
        n = _direccion_de(ctx, v["direccion"][0])
    else:
        plano = next((e.plano for e in ents if e.plano is not None), None)
        n = mp.unitario(plano.normal) if plano is not None else np.array([0.0, 0.0, 1.0])
    if n is None:
        return []
    salida = [mp.Flecha("distancia", centro, n, factor=0.5 if v.get("simetrica") else 1.0)]
    lateral = mp.perpendiculares(n)[0]
    borde = mp.punto_borde([e.forma for e in ents], centro, lateral)
    t = n * (-1.0 if evaluar_o_cero(ctx, v.get("distancia")) < 0 else 1.0)
    salida.append(mp.Angulo("conicidad", borde, np.cross(t, lateral), t, minimo=-89.0, maximo=89.0, caja="arrastre"))
    return salida


# ---------------------------------------------------------------- patrones
def _paso(v, n_clave, dist_clave, ctx):
    """Distancia (con signo) entre copias vecinas: la distancia dada (Espaciado) o repartida entre las copias (Extensión)."""
    d, n = evaluar_o_cero(ctx, v.get(dist_clave)), max(1, int(evaluar_o_cero(ctx, v.get(n_clave)) or 1))
    return d / (n - 1) if v.get("distribucion") == "extension" and n > 1 else d


def _asa_cantidad(clave, origen, direccion, paso):
    """Asa de cantidad de las copias alineadas: la última queda en `origen + direccion·paso·(n-1)` (paso con signo)."""
    signo = -1.0 if paso < 0 else 1.0
    return _mp().AsaCantidad(clave, lambda n: (origen + direccion * paso * (n - 1), direccion * signo), abs(paso) or 10.0)


def _asas_patron_rectangular(self, ctx, v):
    mp = _mp()
    centro = _centro_cuerpos(ctx, v)
    if centro is None:
        return []
    salida = []
    for dir_clave, dist_clave, n_clave in (("dir1", "d1", "n1"), ("dir2", "d2", "n2")):
        if v.get(dir_clave):
            d = _direccion_de(ctx, v[dir_clave][0])
            if d is not None and np.linalg.norm(d) > 1e-9:
                salida.append(mp.Flecha(dist_clave, centro, d))
                salida.append(_asa_cantidad(n_clave, centro, d, _paso(v, n_clave, dist_clave, ctx)))
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
    salida = [mp.Angulo("angulo", pie, d, centro - pie, radio if radio > 1e-6 else None)]
    if radio > 1e-6:
        total, n0 = evaluar_o_cero(ctx, v.get("angulo")), max(1, int(evaluar_o_cero(ctx, v.get("n")) or 1))
        paso_grados = total / n0 if v.get("distribucion") == "extension" else total
        u, signo = (centro - pie) / radio, (-1.0 if paso_grados < 0 else 1.0)

        def posicion(n):
            a = np.radians(paso_grados * (n - 1))
            p = pie + radio * (u * np.cos(a) + np.cross(d, u) * np.sin(a))
            return p, np.cross(d, (p - pie) / radio) * signo
        salida.append(mp.AsaCantidad("n", posicion, radio * abs(np.radians(paso_grados)) or 10.0))
    return salida


# ---------------------------------------------------------------- sistemas de coordenadas y uniones
def _asas_scu(self, ctx, v):
    """Tríada en el origen del SCU: flechas = Desfase X/Y/Z, arcos = Ángulo X/Y/Z."""
    mp = _mp()
    origen = _punto_de(ctx, v["origen"][0]) if v.get("origen") else np.zeros(3)
    if origen is None:
        return []
    L = lambda k: evaluar_o_cero(ctx, v.get(k))  # noqa: E731
    return [mp.Triada(origen + [L("dx"), L("dy"), L("dz")], claves=("dx", "dy", "dz"), giros=("rx", "ry", "rz"))]


def _asas_union(clave_origen, clave_punto):
    """Tres flechas de desfase sobre los ejes del marco del origen (X, Y y Z de la unión, no los del mundo: así los
    calcula la operación) y el arco del ángulo alrededor de su Z, como los manipuladores de Fusion al crear una unión."""
    def asas(self, ctx, v):
        from ...timeline.ops_ensamblar import _marco
        mp = _mp()
        if not v.get(clave_origen) or "dx" not in v:      # «Unión construida» no tiene desfases
            return []
        e = mp.entidad(v[clave_origen][0], ctx.estado)
        if e is None:
            return []
        try:
            F, _eje = _marco(e, v.get(clave_punto) or "centro", ctx.op.p.get("version_marco", 1) if ctx.op else 2)
        except Exception:  # noqa: BLE001 — una selección sin marco no rompe el diálogo
            return []
        ejes, d = F[:3, :3], np.array([evaluar_o_cero(ctx, v.get(k)) for k in ("dx", "dy", "dz")])
        centro = F[:3, 3] + ejes @ d
        flechas = [mp.Flecha(k, F[:3, 3] + ejes @ np.where(np.arange(3) == i, 0.0, d), ejes[:, i], caja="arrastre")
                   for i, k in enumerate(("dx", "dy", "dz"))]
        return flechas + [mp.Angulo("angulo", centro, ejes[:, 2], ejes[:, 0])]
    return asas


# ---------------------------------------------------------------- bobina
def _asas_bobina(self, ctx, v):
    """Asa de diámetro sobre X del plano y flecha de altura sobre su normal, si el tipo usa altura."""
    mp = _mp()
    sel = v.get("plano") or []
    plano = ent.como_plano(mp.entidad(sel[0], ctx.estado)) if sel else geo.Plano("XY")
    centro = _punto_de(ctx, v["centro"][0]) if v.get("centro") else plano.origen
    if centro is None:
        return []
    asas = [mp.AsaRadial("diametro", centro, plano.u, factor=0.5, minimo=0.1)]
    if v.get("tipo") in ("rev_altura", "altura_paso"):
        asas.append(mp.Flecha("altura", centro, plano.normal, minimo=0.0))
    return asas


# ---------------------------------------------------------------- ayudas de curvas y aristas
def _punto_y_tangente(forma, fraccion=0.5):
    """(punto, tangente unitaria) de la primera arista de `forma` a esa fracción de su recorrido."""
    from ...nucleo.consultas import punto_y_tangente
    return punto_y_tangente(forma, fraccion)


def _forma_de(ctx, hit):
    e = _mp().entidad(hit, ctx.estado)
    return e.forma if e is not None else None


def _saliente_de_arista(ctx, hit):
    """(punto medio de la arista, dirección que sale de su cara) para tirar de dobladillos y extensiones."""
    from ...nucleo.consultas import saliente_de_arista
    e = _mp().entidad(hit, ctx.estado)
    if e is None or e.forma is None or getattr(e, "cuerpo", None) not in ctx.estado.cuerpos:
        return None
    cuerpo = ctx.estado.cuerpos[e.cuerpo].forma
    return saliente_de_arista(e.forma, cuerpo)


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
    caras = v.get("caras") or v.get("cara")
    cara = _forma_de(ctx, caras[0]) if caras else None
    if base is None or cara is None:
        return []
    punto, n = mp.punto_normal_cara(cara)
    centro = base[0] + n * float((punto - base[0]) @ n)         # el centro del perfil, sobre la cara
    return [mp.Flecha("profundidad", centro, n * (1.0 if v.get("tipo") != "grabado" else -1.0), minimo=0.0)]


def _asas_rosca(self, ctx, v):
    from ...nucleo.consultas import inicio_rosca
    mp = _mp()
    if v.get("largo_completo") or not v.get("caras"):
        return []
    forma = _forma_de(ctx, v["caras"][0])
    if forma is None:
        return []
    datos = inicio_rosca(forma, bool(v.get("invertir")))
    if datos is None:
        return []
    inicio, d = datos
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
    """Flecha de distancia y asa de cantidad donde empieza el patrón (`inicio`), y un asa que desliza ese inicio por la ruta."""
    from ...nucleo.construccion import muestras_ruta
    mp = _mp()
    forma = _forma_de(ctx, v["ruta"][0]) if v.get("ruta") else None
    inicio = min(1.0, max(0.0, evaluar_o_cero(ctx, v.get("inicio"))))
    pt = _punto_y_tangente(forma, inicio) if forma is not None else None
    if pt is None:
        return []
    salida = [mp.Flecha("d1", pt[0], pt[1]), _asa_cantidad("n1", pt[0], pt[1], _paso(v, "n1", "d1", ctx))]
    try:
        ts = np.linspace(0.0, 1.0, 81)
        salida.append(mp.AsaRuta("inicio", ts, muestras_ruta(forma, ts)))
    except Exception:  # noqa: BLE001 — una ruta que no se puede muestrear no rompe el diálogo
        pass
    return salida


def _enganchar():
    tabla = {
        "sup_desfase": _asas_desfase_superficie, "engrosar": _asas_engrosar, "sup_extruir": _asas_extruir_superficie,
        "escala_3d": _asas_escala, "seccion": _asas_corte("desfase"),
        "seccion_malla": _asas_corte("distancia"),
        "patron_rectangular_3d": _asas_patron_rectangular, "patron_circular_3d": _asas_patron_circular,
        "scu": _asas_scu, "union": _asas_union("origen2", "clave2"), "origen_union": _asas_union("origen", "clave"),
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
