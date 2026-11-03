# -*- coding: utf-8 -*-
"""«Remove Features» de Fusion (Simulation › Simplify › Modify › Remove Features): quita de un cuerpo
los empalmes, los chaflanes y los agujeros chicos de una vez, con un tamaño máximo.
Funciones puras del núcleo: reciben OCC y devuelven OCC (o dicts)."""
import numpy as np
from . import geometria as geo
from . import motor as _motor
from . import referencias as refs
from .solidos_modificar import _ancestros, _aristas_de_cara, _padres, _unicos, caras_de_empalme, quitar_caras

TIPOS = ("empalme", "chaflan", "agujero")


def _iniciar_opencascade():
    global BRepAdaptor_Surface, BRepClass3d_SolidClassifier, TopAbs_EDGE, TopAbs_FACE, TopAbs_IN
    global TopAbs_REVERSED, TopoDS, gp_Pnt
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_IN, TopAbs_REVERSED
    from OCP.TopoDS import TopoDS


if _motor.motor_activo() == "opencascade":
    _iniciar_opencascade()

_motor.registrar(globals(), _iniciar_opencascade)


def _es_plana(f):
    return (f or {}).get("geom") == "plano"


def _dentro(forma, punto):
    return BRepClass3d_SolidClassifier(forma, gp_Pnt(*punto), 1e-6).State() == TopAbs_IN


def _cilindro(cara):
    s = BRepAdaptor_Surface(cara)
    return (s.Cylinder().Radius(), s.Cylinder().Axis().Location(), s.Cylinder().Axis().Direction()) if s.GetType() == 1 else None


def _firmas(forma, caras):
    """La firma de cada cara, ubicada por su posición entre las del cuerpo: cada consulta a un mapa
    topológico devuelve un TopoDS_Shape nuevo para la misma cara, así que no sirven id() ni la cara."""
    mapa = refs.mapa_de_subformas(forma, "cara")
    firmas = {i: refs.firma_cara(c) for i, c in enumerate(caras)}
    return lambda cara: firmas.get(mapa.FindIndex(cara) - 1, {})


def _mitades(cara, firma, arista_caras):
    """La cara y sus mitades coplanares contiguas: cuando un chaflán corta un empalme, OCC parte la cara
    en dos por la diagonal y las dos mitades son UNA operación."""
    f = firma(cara)
    grupo, pendientes = [cara], [cara]
    while pendientes:
        actual = pendientes.pop()
        for e in _aristas_de_cara(actual):
            for v in _padres(arista_caras, e):
                g = firma(v)
                if (not any(v.IsSame(x) for x in grupo) and _es_plana(g) and np.allclose(g["normal"], f["normal"], atol=1e-6)
                        and np.isclose(np.dot(g["centro"], f["normal"]), np.dot(f["centro"], f["normal"]), atol=1e-6)):
                    grupo.append(v)
                    pendientes.append(v)
    return grupo


def _operaciones_chaflan(caras, firma, arista_caras, tamano):
    """Caras planas angostas, de ancho <= tamano, con un lado recto contra otra cara plana a 45° de su
    normal hacia adentro: un chaflán simétrico. Un escalón angosto o una cara que biseca dos planos no."""
    salida = []
    for cara in caras:
        f = firma(cara)
        rectas = [e for e in _aristas_de_cara(cara) if refs.firma_arista(e).get("geom") == "linea"]
        if not _es_plana(f) or not rectas or f["area"] / sum(refs.firma_arista(e)["largo"] for e in rectas) > tamano:
            continue
        interior = -np.asarray(f["normal"], float)
        vecinas = [firma(v) for e in rectas for v in _padres(arista_caras, e) if not v.IsSame(cara)]
        if any(_es_plana(n) and abs(abs(np.dot(n["normal"], interior)) - 1 / np.sqrt(2)) < 1e-3 for n in vecinas):
            salida.append(_mitades(cara, firma, arista_caras))
    return salida


def _es_pared_de_agujero(forma, cara):
    """Pared de agujero: cara cilíndrica cuya normal mira hacia el eje (el kernel la marca REVERSED) y
    cuyo eje no cae sobre el material (el de un empalme de esquina también mira adentro, pero es
    delgado y su eje pasa por el sólido)."""
    cil = _cilindro(cara)
    if cil is None or cara.Orientation() != TopAbs_REVERSED:
        return False
    _, loc, eje = cil
    for t in (0.0, cil[0], -cil[0], 2 * cil[0]):
        if _dentro(forma, [loc.X() + eje.X() * t, loc.Y() + eje.Y() * t, loc.Z() + eje.Z() * t]):
            return False
    return True


def _fondo_de_agujero(cara, firma, arista_caras):
    """Cara que cierra el agujero por el fondo (el cono de la punta o el piso plano, chico como para ser
    el fondo): defeaturing la necesita junto con la pared. Un agujero pasante no tiene."""
    radio = _cilindro(cara)[0]
    centro = np.asarray(firma(cara)["centro"], float)
    vecinas = []
    for e in _aristas_de_cara(cara):
        vecinas.extend(v for v in _padres(arista_caras, e)
                       if not v.IsSame(cara) and not any(v.IsSame(w) for w in vecinas))
    for v in vecinas:
        f = firma(v)
        if f.get("geom") == "cono" and np.abs(np.asarray(f["centro"], float) - centro).max() <= radio:
            return v
        if _es_plana(f) and f["area"] < np.pi * radio ** 2 * 1.5:
            return v
    return None


def detectar(forma, tamano, tipos=TIPOS):
    """Las operaciones chicas a quitar, como listas de caras: {"empalme": [[caras]...], "chaflan":
    [[caras]...], "agujero": [[pared y fondo]...]}, solo de los `tipos` pedidos y con medida <= `tamano`."""
    desconocidos = set(tipos) - set(TIPOS)
    if desconocidos:
        raise geo.ErrorGeometria(f"Tipo de operación desconocido: {', '.join(sorted(desconocidos))}. "
                                 f"Los válidos son: {', '.join(TIPOS)}.")
    if tamano <= 0:
        raise geo.ErrorGeometria("El tamaño máximo tiene que ser mayor que cero.")
    caras = [TopoDS.Face(f) for f in _unicos(forma, TopAbs_FACE)]
    firma = _firmas(forma, caras)
    arista_caras = _ancestros(forma, TopAbs_EDGE, TopAbs_FACE)
    encontrados = {"empalme": [], "chaflan": [], "agujero": []}
    if "empalme" in tipos:
        encontrados["empalme"] = [[c] for c, _r in caras_de_empalme(forma, tamano)]
    if "chaflan" in tipos:
        for grupo in _operaciones_chaflan(caras, firma, arista_caras, tamano):
            if not any(any(a.IsSame(b) for a in grupo for b in otro) for otro in encontrados["chaflan"]):
                encontrados["chaflan"].append(grupo)
    if "agujero" in tipos:
        for pared in [c for c in caras if _es_pared_de_agujero(forma, c) and _cilindro(c)[0] * 2 <= tamano]:
            fondo = _fondo_de_agujero(pared, firma, arista_caras)
            encontrados["agujero"].append([pared] + ([fondo] if fondo is not None else []))
    return encontrados


def quitar_operaciones(forma, tamano, tipos=TIPOS):
    """«Remove Features» de Fusion: quita del cuerpo los empalmes, chaflanes y agujeros con medida
    hasta `tamano` con defeaturing y une la topología que queda. Devuelve (forma, {"empalme": n,
    "chaflan": n, "agujero": n}); falla si no encontró nada de esos tipos."""
    encontrados = detectar(forma, tamano, tipos)
    if not any(encontrados.values()):
        raise geo.ErrorGeometria(f"No se encontraron {', '.join(tipos)} con tamaño <= {tamano:g} mm en el cuerpo.")
    # Un grupo por vez sobre el cuerpo ACTUAL: las caras ya quitadas dejan de existir, y unificar antes
    # de tiempo deja aristas finitas que el defeaturing no logra cerrar. Los recuentos son los detectados.
    while True:
        actuales = detectar(forma, tamano, tipos)
        grupos = [g for tipo in ("agujero", "empalme", "chaflan") for g in actuales[tipo]]
        if not grupos:
            break
        forma = geo.unificar_caras(quitar_caras(forma, grupos[0]))
    return forma, {t: len(g) for t, g in encontrados.items()}
