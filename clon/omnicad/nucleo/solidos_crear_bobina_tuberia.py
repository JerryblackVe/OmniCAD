"""Sólidos › Crear: bobina y tuberia."""
from typing import TYPE_CHECKING
import numpy as np
from . import geometria as geo
import math
from .solidos_crear_occ import _registrar_tema
from .solidos_crear_comun import (
    _alambre, _gdir, _perpendicular, _pnt, _poligono, _punto_en, _recortar_alambre, _unit, _validar,
)
from .solidos_crear_revolucion import _girar
from .solidos_crear_barrido import _barrido_alambre
from .solidos_crear_roscas import _barrido_helicoidal, _helice

if TYPE_CHECKING:
    from .solidos_crear_occ import (
        BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, GeomAPI_Interpolate, HArray1_gp_Pnt, gp_Ax1, gp_Ax2,
        gp_Circ,
    )


# ================================================================ 9. bobina
def _seccion_bobina(seccion, tamano):
    """Puntos (radial, axial) de la sección inscrita en un círculo de diámetro `tamano` (None = círculo)."""
    r = tamano / 2
    if seccion == "circular":
        return None
    if seccion == "cuadrada":
        a = r / math.sqrt(2)
        return [(-a, -a), (a, -a), (a, a), (-a, a)]
    if seccion == "triangular_externa":
        return [(r, 0.0), (-r / 2, r * math.sqrt(3) / 2), (-r / 2, -r * math.sqrt(3) / 2)]
    if seccion == "triangular_interna":
        return [(-r, 0.0), (r / 2, -r * math.sqrt(3) / 2), (r / 2, r * math.sqrt(3) / 2)]
    raise geo.ErrorGeometria(f"Sección de bobina desconocida: {seccion}")


def _espiral(origen, eje, x, radio, paso, revoluciones, horario):
    """Espiral de Arquímedes plana: el radio aumenta un paso por vuelta."""
    y = np.cross(eje, x)
    # shortcut: interpolación a 64 muestras/vuelta; usar aproximación adaptativa si se exige tolerancia radial.
    cantidad = max(8, math.ceil(revoluciones * 64) + 1)
    puntos = HArray1_gp_Pnt(1, cantidad)
    for i in range(cantidad):
        vueltas = revoluciones * i / (cantidad - 1)
        angulo = vueltas * 2 * math.pi * (-1 if horario else 1)
        puntos.SetValue(i + 1, _pnt(origen + (radio + paso * vueltas) *
                                   (math.cos(angulo) * x + math.sin(angulo) * y)))
    curva = GeomAPI_Interpolate(puntos, False, 1e-7)
    curva.Perform()
    if not curva.IsDone():
        raise geo.ErrorGeometria("No se pudo construir la espiral de la bobina.")
    return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(curva.Curve()).Edge()).Wire()


def bobina(base_punto, eje, *, diametro, revoluciones=None, altura=None, paso=None, angulo=0.0,
           seccion="circular", tamano_seccion, posicion_seccion="sobre", horario=False, eje_x=None,
           tipo="rev_altura", girar=False):
    """Bobina (Coil) de Fusion [SLD-COIL-SOLID, SLD-REF-COIL]: hélice de `diametro` con base en `base_punto`.
    Se dan dos de `revoluciones`, `altura` y `paso` (la altura va del centro de la sección inicial al de la
    final). `angulo` = inclinación (positivo = el radio crece con la altura). Sección "circular", "cuadrada",
    "triangular_externa" o "triangular_interna" de tamaño = diámetro del círculo circunscrito, ubicada
    "dentro", "sobre" o "fuera" del diámetro. `horario` invierte el sentido. `tipo="espiral"` usa
    revoluciones y paso radial, sin altura ni ángulo. `girar` rota 90° alrededor de Y local en la base."""
    if tipo not in ("rev_altura", "rev_paso", "altura_paso", "espiral"):
        raise geo.ErrorGeometria(f"Tipo de bobina desconocido: {tipo}")
    espiral = tipo == "espiral"
    if espiral and (revoluciones is None or paso is None or altura is not None):
        raise geo.ErrorGeometria("⚠ La espiral necesita revoluciones y paso.")
    if sum(v is not None for v in (revoluciones, altura, paso)) != 2:
        raise geo.ErrorGeometria("⚠ Dá dos de: revoluciones, altura y paso.")
    if revoluciones is not None and revoluciones <= 0:     # antes de dividir por ellas
        raise geo.ErrorGeometria(f"⚠ Revoluciones {revoluciones:g}: debe ser mayor que 0.")
    if paso is not None and paso <= 0:
        raise geo.ErrorGeometria(f"⚠ Paso {paso:g}: debe ser mayor que 0.")
    if revoluciones is None:
        revoluciones = altura / paso
    elif altura is None:
        altura = revoluciones * paso
    else:
        paso = altura / revoluciones
    if diametro <= 0 or tamano_seccion <= 0 or revoluciones <= 0 or altura <= 0:
        raise geo.ErrorGeometria("⚠ Todos los valores de la bobina: positivos.")
    z = _unit(eje, "eje de la bobina")
    x = _perpendicular(z) if eje_x is None else _unit(np.asarray(eje_x, float) - z * float(np.asarray(eje_x) @ z))
    o = np.asarray(base_punto, float)
    pts = _seccion_bobina(seccion, tamano_seccion)
    radiales = [-tamano_seccion / 2, tamano_seccion / 2] if pts is None else [q[0] for q in pts]
    axiales = [-tamano_seccion / 2, tamano_seccion / 2] if pts is None else [q[1] for q in pts]
    r_c = {"dentro": diametro / 2 - max(radiales), "sobre": diametro / 2,
           "fuera": diametro / 2 - min(radiales)}.get(posicion_seccion)
    if r_c is None:
        raise geo.ErrorGeometria(f"Posición de sección desconocida: {posicion_seccion}")
    if r_c + min(radiales) <= 0:
        raise geo.ErrorGeometria("⚠ La sección cruza el eje de la bobina.")
    if not espiral and r_c + altura * math.tan(math.radians(angulo)) + min(radiales) <= 0:   # el cono angosta el radio
        raise geo.ErrorGeometria("⚠ Bajá el ángulo: la bobina llega al eje.")
    ancho = max(radiales) - min(radiales) if espiral else max(axiales) - min(axiales)
    if paso <= ancho + 1e-6:
        raise geo.ErrorGeometria("⚠ El paso es menor que la sección: se pisan.")
    centro = o + x * r_c
    if pts is None:
        perfil = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(
            gp_Circ(gp_Ax2(_pnt(centro), _gdir(np.cross(z, x))), tamano_seccion / 2)).Edge()).Wire()
    else:
        perfil = _poligono([centro + x * a + z * b for a, b in pts])
    helice = (_espiral(o, z, x, r_c, paso, revoluciones, horario) if espiral else
              _helice(o, z, x, r_c, paso, altura, "izquierda" if horario else "derecha", angulo))
    forma = _barrido_helicoidal(perfil, helice)
    if girar:
        forma = _girar(forma, gp_Ax1(_pnt(o), _gdir(np.cross(z, x))), 90)
    forma = _validar(forma, "Bobina")
    if geo.volumen(forma) <= 0:          # B-391: medidas extremas (altura 1e6 con 30°) dan el sólido dado vuelta
        raise geo.ErrorGeometria("Bobina inválida: menos altura o ángulo.")
    return forma


# ================================================================ 10. tubería
def _seccion_tuberia(seccion, centro, u, v, radio):
    if seccion == "circular":
        return BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(
            gp_Circ(gp_Ax2(_pnt(centro), _gdir(np.cross(u, v)), _gdir(u)), radio)).Edge()).Wire()
    lados = {"cuadrada": 4, "triangular": 3}.get(seccion)
    if lados is None:
        raise geo.ErrorGeometria(f"Sección de tubería desconocida: {seccion}")
    giro = math.pi / 4 if lados == 4 else math.pi / 2
    return _poligono([centro + radio * (math.cos(giro + 2 * math.pi * k / lados) * u
                                        + math.sin(giro + 2 * math.pi * k / lados) * v) for k in range(lados)])


def tuberia(ruta, *, seccion="circular", tamano, hueca=False, espesor=0.0, distancia=1.0, distancia2=0.0):
    """Tubería (Pipe) de Fusion [SLD-PIPE-SOLID]: sección "circular", "cuadrada" o "triangular" de tamaño =
    diámetro del círculo circunscrito, barrida entre las fracciones `distancia2` y `distancia` de la ruta.
    `distancia2=0` conserva el inicio original. `hueca` con `espesor` de
    pared (paredes paralelas a las exteriores)."""
    distancia, distancia2 = float(distancia), float(distancia2)
    if not math.isfinite(distancia) or not math.isfinite(distancia2) or not 0 <= distancia2 < min(distancia, 1.0):
        raise geo.ErrorGeometria("⚠ Distancia finita: inicio entre 0 y el fin.")
    w = _recortar_alambre(_alambre(ruta), distancia, distancia2)
    if tamano <= 0:
        raise geo.ErrorGeometria("El tamaño de la sección debe ser positivo.")
    p0, t0 = _punto_en(w, 0.0)
    u = _perpendicular(t0)
    v = np.cross(t0, u)
    radio = tamano / 2
    args = (w, None, "perpendicular", 0.0, 0.0, "escalar", True, 1.0)
    forma = _barrido_alambre(_seccion_tuberia(seccion, p0, u, v, radio), *args)
    if hueca:
        lados = {"circular": None, "cuadrada": 4, "triangular": 3}[seccion]
        interior = radio - espesor / (1.0 if lados is None else math.cos(math.pi / lados))
        if espesor <= 0 or interior <= 1e-6:
            raise geo.ErrorGeometria("⚠ Espesor del tubo: mayor que 0 y menor.")
        forma = geo.booleano(forma, _barrido_alambre(_seccion_tuberia(seccion, p0, u, v, interior), *args), "cortar")
    return _validar(forma, "Tubería")


_registrar_tema(globals())
