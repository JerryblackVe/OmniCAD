"""Sólidos › Crear: revolucion."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import (
    _aristas_de, _cadenas, _caras_de, _engrosar_lamina, _gdir, _perpendicular, _pnt, _tipado, _unir, _unit,
    _validar,
)
from .solidos_crear_extrusion import _bandas_cerradas
from .solidos_crear_nervios import _diagonal

if TYPE_CHECKING:
    from .solidos_crear_occ import BRepBuilderAPI_Transform, BRepPrimAPI_MakeRevol, TopAbs_WIRE, gp_Ax1, gp_Trsf


# ================================================================ 2. revolución
def _girar(forma, eje, grados):
    t = gp_Trsf()
    t.SetRotation(eje, math.radians(grados))
    return _tipado(BRepBuilderAPI_Transform(forma, t, True).Shape())


def revolver_avanzado(caras, punto_eje, dir_eje, *, direccion="un_lado", angulo1=360.0, angulo2=None,
                      delgado=None, aristas=None):
    """Revolución de Fusion [SLD-REVOLVE-SOLID]. Devuelve el sólido herramienta.

    "un_lado": angulo1 con signo; "dos_lados": angulo1 hacia un lado y angulo2 hacia el otro; "simetrica":
    angulo1 a cada lado (total 2·angulo1, como `setAngleExtent(isSymmetric=True)` de la API de Fusion).
    Revolución delgada: `delgado={"espesor", "ubicacion"}` con caras o con `aristas` abiertas (se revoluciona
    la curva como superficie y se le da espesor: lado1 = +espesor según la normal de esa superficie).
    """
    eje = gp_Ax1(_pnt(punto_eje), _gdir(_unit(dir_eje, "dirección del eje")))
    caras = _caras_de(caras)
    abiertas = _cadenas(aristas) if aristas is not None else []
    if not caras and not abiertas:
        raise geo.ErrorGeometria("Elegí al menos un perfil para revolucionar.")
    if delgado and caras:
        caras = _bandas_cerradas(caras, float(delgado["espesor"]), delgado.get("ubicacion", "lado1"))
    elif abiertas and not delgado:
        raise geo.ErrorGeometria("⚠ Perfil abierto: solo revolución delgada.")
    if direccion == "un_lado":
        tramos = [(0.0, float(angulo1))]
    elif direccion == "dos_lados":
        tramos = [(0.0, abs(angulo1)), (0.0, -abs(angulo2 or 0.0))]
    elif direccion == "simetrica":
        tramos = [(-abs(angulo1), 2 * abs(angulo1))]
    else:
        raise geo.ErrorGeometria(f"Dirección de revolución desconocida: {direccion}")
    if sum(abs(a) for _, a in tramos) >= 360.0 - 1e-9:
        tramos = [(0.0, 360.0)]
    solidos = []
    for inicio, ang in tramos:
        if abs(ang) < 1e-9:
            continue
        for perfil in caras + abiertas:
            base = _girar(perfil, eje, inicio) if inicio else perfil
            rev = BRepPrimAPI_MakeRevol(base, eje, math.radians(ang)).Shape()
            if perfil.ShapeType() == TopAbs_WIRE:
                t, ubic = float(delgado["espesor"]), delgado.get("ubicacion", "centro")
                partes = {"lado1": [t], "lado2": [-t], "centro": [t / 2, -t / 2]}.get(ubic)
                if partes is None:
                    raise geo.ErrorGeometria(f"Ubicación de pared desconocida: {ubic}")
                solidos += [_engrosar_lamina(rev, e) for e in partes]
            else:
                solidos.append(rev)
    if not solidos:
        raise geo.ErrorGeometria("El ángulo de revolución no puede ser cero.")
    return _validar(_unir(solidos), "Revolución (¿el perfil cruza el eje?)")


# ================================================================ 13b. revolución hasta un objeto
def _marco_giro(caras, punto, d):
    """(e1, e2, puntos): base del giro alrededor del eje (e1 hacia el perfil, e2 = d × e1) y puntos del contorno."""
    from . import curvas3d
    puntos = []
    for c in caras:
        for a in _aristas_de([c]):
            puntos.extend(curvas3d.muestrear(a, 16).astype(float))
    puntos = np.array(puntos)
    rel = puntos - punto
    radial = rel - np.outer(rel @ d, d)
    medio = radial.mean(axis=0)
    e1 = medio if np.linalg.norm(medio) > 1e-9 else _perpendicular(d)
    e1 = _unit(e1 - d * (e1 @ d))
    return e1, np.cross(d, e1), puntos


def _angulos_de_cruce(puntos, punto, d, e1, e2, n, q0):
    """Primer ángulo (rad, en (0, 2π]) en que cada punto girado alrededor del eje cruza el plano (n, q0)."""
    salida = []
    for p in puntos:
        rel = p - punto
        h = float(rel @ d)
        w = rel - d * h
        r = float(np.linalg.norm(w))
        if r < 1e-9:
            continue
        psi0 = math.atan2(float(w @ e2), float(w @ e1))
        a_, b_ = r * float(n @ e1), r * float(n @ e2)
        c_ = float(n @ (punto - q0)) + h * float(n @ d)
        modulo = math.hypot(a_, b_)
        if modulo < 1e-12 or abs(c_) > modulo + 1e-9:
            continue
        base = math.atan2(b_, a_)
        giro = math.acos(max(-1.0, min(1.0, -c_ / modulo)))
        posibles = [((base + signo * giro) - psi0) % (2 * math.pi) for signo in (1, -1)]
        posibles = [t if t > 1e-7 else t + 2 * math.pi for t in posibles]
        salida.append(min(posibles))
    return salida


def revolver_hasta(caras, punto_eje, dir_eje, objeto):
    """Revolución «A objeto» (Revolve › Extent Type To Object) [SLD-REVOLVE-SOLID]: gira el perfil hasta un
    vértice (`("punto", xyz)`), un plano o cara plana (`("plano", geo.Plano)`) o un cuerpo (`("forma", sólido)`).
    El sentido es el de la regla de la mano derecha sobre `dir_eje`. Con un plano que no contiene al eje (y que
    todo el perfil alcanza) el cuerpo se recorta contra él; con un cuerpo gira hasta el primer contacto (bisección sobre el volumen común)."""
    punto, d = np.asarray(punto_eje, float), _unit(dir_eje, "eje de revolución")
    e1, e2, puntos = _marco_giro(caras, punto, d)
    tipo, dato = objeto
    recorte = None
    if tipo == "punto":
        rel = np.asarray(dato, float) - punto
        if np.linalg.norm(rel - d * (rel @ d)) < 1e-9:
            raise geo.ErrorGeometria("⚠ El vértice está sobre el eje: sin ángulo.")
        angulo = math.atan2(float(rel @ e2), float(rel @ e1)) % (2 * math.pi)
    elif tipo == "plano":
        n = _unit(dato.normal)
        cruces = _angulos_de_cruce(puntos, punto, d, e1, e2, n, np.asarray(dato.origen, float))
        if not cruces:
            raise geo.ErrorGeometria("El perfil, al girar, no llega a ese plano.")
        fuera_del_eje = int((np.linalg.norm((puntos - punto) - np.outer((puntos - punto) @ d, d), axis=1) >= 1e-9).sum())
        if len(cruces) < fuera_del_eje:        # sin esto el ángulo dependería de qué puntos muestreados alcanzan el plano
            raise geo.ErrorGeometria("El perfil no llega a ese plano: elegí otro.")
        angulo = max(cruces)
        if max(cruces) - min(cruces) > 1e-6:            # el plano no contiene al eje: se recorta contra él
            lado = float((puntos.mean(axis=0) - np.asarray(dato.origen, float)) @ n)
            recorte = (dato, 1.0 if lado >= 0 else -1.0)
    elif tipo == "forma":
        def toca(a):
            sol = geo.revolver(caras, punto, d, math.degrees(a))
            comun = geo.booleano(sol, dato, "intersecar")
            return not geo.esta_vacia(comun) and geo.volumen(comun) > 1e-6 * max(1.0, geo.volumen(sol))
        if not toca(2 * math.pi):
            raise geo.ErrorGeometria("El perfil, al girar, no llega a ese cuerpo.")
        bajo, alto = 0.0, 2 * math.pi
        for _ in range(25):
            medio = (bajo + alto) / 2
            bajo, alto = (bajo, medio) if toca(medio) else (medio, alto)
        angulo = alto
    else:
        raise geo.ErrorGeometria(f"Objeto de revolución desconocido: {tipo}")
    if angulo < 1e-7:
        raise geo.ErrorGeometria("⚠ Elegí un objeto fuera del plano del perfil.")
    forma = geo.revolver(caras, punto, d, math.degrees(min(angulo, 2 * math.pi)))
    if recorte is not None:
        plano, lado = recorte
        tam = 4 * _diagonal(forma) + float(np.linalg.norm(np.asarray(plano.origen, float) - punto))
        mitad = geo.extruir([geo.cara_de_plano(plano, tam)], plano.normal, lado * tam)
        forma = _validar(geo.booleano(forma, mitad, "intersecar"), "Revolución hasta el plano")
    return forma


_registrar_tema(globals())
