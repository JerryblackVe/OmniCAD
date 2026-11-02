# -*- coding: utf-8 -*-
"""
Unidades de Fusion 360: las 35 familias del artículo `Unit types` (No unit y Text, más 33 con unidades).

Una unidad es un factor a la unidad interna y una dimensión. Internas: mm, grados, g, s y SI para el resto, así que una
longitud y un ángulo valen lo mismo que en el resto del programa. La dimensión son los exponentes de BASES: alcanza para
saber que `w * h` no es una longitud, y que `N` y `kg * m / s^2` son lo mismo.
"""
import functools
import math
import re
from typing import NamedTuple

BASES = ("mm", "deg", "g", "s", "A", "K", "mol", "cd", "sr", "$", "pcs")


def _dim(**exponentes):
    return tuple(exponentes.get(b, 0) for b in ("L", "ANG", "M", "T", "I", "TEMP", "MOL", "CD", "SR", "DIN", "PZ"))


SIN_DIMENSION = _dim()
LONGITUD_DIM, ANGULO_DIM, MASA_DIM, TIEMPO_DIM = _dim(L=1), _dim(ANG=1), _dim(M=1), _dim(T=1)
_JOULE = _dim(M=1, L=2, T=-2)
_G_ESTANDAR = 9806.65          # mm/s²
_LIBRA_FUERZA = 453.59237 * _G_ESTANDAR
_GALON = 3785411.784           # mm³


class Unidad(NamedTuple):
    factor: float              # 1 de esta unidad en unidades internas
    dim: tuple
    desfase: float = 0.0       # solo Celsius y Fahrenheit

    def a_interno(self, valor):
        return valor * self.factor + self.desfase

    def desde_interno(self, valor):
        return (valor - self.desfase) / self.factor


# Familia → (dimensión, {abreviatura: factor}). El orden es el del artículo.
FAMILIAS = {
    "Ángulo": (ANGULO_DIM, {"rad": 180.0 / math.pi, "deg": 1.0, "grad": 0.9}),
    "Velocidad angular": (_dim(ANG=1, T=-1), {"rpm": 6.0}),
    "Área": (_dim(L=2), {"acre": 4046.8564224e6, "circular_mil": math.pi / 4 * 0.0254 ** 2}),
    "Capacitancia": (_dim(M=-1, L=-2, T=4, I=2), {"farad": 1e-9}),
    "Carga": (_dim(T=1, I=1), {"coulomb": 1.0}),
    "Conductancia": (_dim(M=-1, L=-2, T=3, I=2), {"S": 1e-9, "mho": 1e-9}),
    "Moneda": (_dim(DIN=1), {"dol": 1.0}),
    "Corriente": (_dim(I=1), {"A": 1.0}),
    "Energía": (_JOULE, {"J": 1e9, "erg": 100.0, "calorie": 4.184e9, "Btu": 1055.05585262e9}),
    "Fuerza electromotriz": (_dim(M=1, L=2, T=-3, I=-1), {"V": 1e9}),
    "Caudal": (_dim(L=3, T=-1), {"ccs": 1e3, "cis": 25.4 ** 3, "cfm": 304.8 ** 3 / 60, "cmh": 1e9 / 3600,
                                 "gpm": _GALON / 60, "lph": 1e6 / 3600}),
    "Fuerza": (_dim(M=1, L=1, T=-2), {"N": 1e6, "dyne": 10.0, "lbforce": _LIBRA_FUERZA, "ounceforce": _LIBRA_FUERZA / 16,
                                      "tonforce": _LIBRA_FUERZA * 2000}),
    "Frecuencia": (_dim(T=-1), {"Hz": 1.0}),
    "Iluminancia": (_dim(CD=1, SR=1, L=-2), {"lx": 1e-6}),
    "Inductancia": (_dim(M=1, L=2, T=-2, I=-2), {"H": 1e9}),
    "Longitud": (LONGITUD_DIM, {"mm": 1.0, "cm": 10.0, "dm": 100.0, "m": 1000.0, "hm": 1e5, "km": 1e6, "micron": 1e-3,
                                "in": 25.4, "ft": 304.8, "yd": 914.4, "mi": 1609344.0, "nauticalMile": 1852000.0,
                                "mil": 0.0254}),
    # shortcut: EV es logarítmica y comparte factor con cd: alcanza para escribirla, no para convertir entre las dos.
    "Luminosidad": (_dim(CD=1), {"cd": 1.0, "EV": 1.0}),
    "Flujo luminoso": (_dim(CD=1, SR=1), {"lm": 1.0}),
    "Flujo magnético": (_dim(M=1, L=2, T=-2, I=-1), {"Wb": 1e9, "maxwell": 10.0}),
    "Campo magnético": (_dim(M=1, T=-2, I=-1), {"T": 1e3, "gamma": 1e-6, "gauss": 0.1}),
    "Campo magnetizante": (_dim(I=1, L=-1), {"oersted": 1.0 / (4 * math.pi)}),
    "Masa": (MASA_DIM, {"g": 1.0, "kg": 1000.0, "slug": 14593.90294, "lbmass": 453.59237, "ouncemass": 28.349523125,
                        "tonmass": 907184.74}),
    "Piezas": (_dim(PZ=1), {"pcs": 1.0}),
    "Potencia": (_dim(M=1, L=2, T=-3), {"W": 1e9, "hp": 745.69987158227e9}),
    "Presión": (_dim(M=1, L=-1, T=-2), {"Pa": 1.0, "psi": 6894.757293168, "psf": 47.88025898, "ksi": 6894757.293168,
                                        "bar": 1e5, "atm": 101325.0, "inH2O": 249.08891, "ftH2O": 2989.067,
                                        "mH2O": 9806.65, "mmHg": 133.322387415, "inHg": 3386.38815}),
    "Resistencia": (_dim(M=1, L=2, T=-3, I=-2), {"ohm": 1e9}),
    "Ángulo sólido": (_dim(SR=1), {"sr": 1.0}),
    "Velocidad": (_dim(L=1, T=-1), {"mps": 1e3, "fps": 304.8, "mph": 1609344.0 / 3600, "knots": 1852000.0 / 3600,
                                    "mmpm": 1 / 60, "mpm": 1e3 / 60, "inpm": 25.4 / 60, "ftpm": 304.8 / 60}),
    "Sustancia": (_dim(MOL=1), {"mole": 1.0}),
    "Temperatura": (_dim(TEMP=1), {"K": 1.0, "C": 1.0, "F": 5 / 9, "R": 5 / 9}),
    "Tiempo": (TIEMPO_DIM, {"s": 1.0, "min": 60.0, "hr": 3600.0}),
    "Viscosidad": (_dim(M=1, L=-1, T=-1), {"poise": 0.1}),
    "Volumen": (_dim(L=3), {"l": 1e6, "gal": _GALON, "qt": _GALON / 4, "pt": _GALON / 8, "cup": _GALON / 16,
                            "fl_oz": _GALON / 128}),
}
_DESFASES = {"C": 273.15, "F": 459.67 * 5 / 9}
# Símbolos que Fusion admite en lugar de la abreviatura.
SIMBOLOS = {'"': "in", "'": "ft", "µ": "micron", "°": "deg", "˚": "deg", "$": "dol"}

TABLA = {u: Unidad(f, dim, _DESFASES.get(u, 0.0)) for dim, unidades in FAMILIAS.values() for u, f in unidades.items()}
TABLA.update({s: TABLA[u] for s, u in SIMBOLOS.items()})
SIN_UNIDAD = Unidad(1.0, SIN_DIMENSION)
_PIEZA_UNIDAD = re.compile(r"\s*([*/])?\s*([^\s*/^]+)(?:\s*\^\s*(-?\d+))?\s*")


def _potencia(u, exponente):
    return Unidad(u.factor ** exponente, tuple(d * exponente for d in u.dim))


def combinar(a, b, signo=1):
    """Producto (signo=1) o cociente (signo=-1) de dos dimensiones."""
    return tuple(x + signo * y for x, y in zip(a, b, strict=True))


@functools.lru_cache(maxsize=512)
def leer_unidad(texto):
    """La Unidad de «mm», «mm^2», «cm/s^2» o «N*m». «» es sin unidad; lo que no se entiende, ValueError."""
    texto = texto.strip()
    if not texto:
        return SIN_UNIDAD
    if texto in TABLA:
        return TABLA[texto]
    total, pos = SIN_UNIDAD, 0
    while pos < len(texto):
        m = _PIEZA_UNIDAD.match(texto, pos)
        if not m or m.group(2) not in TABLA or (pos == 0) == bool(m.group(1)):
            raise ValueError(f"Unidad desconocida: '{texto}'.")
        signo = -1 if m.group(1) == "/" else 1
        try:
            pieza = _potencia(TABLA[m.group(2)], int(m.group(3) or 1))
            total = Unidad(total.factor * pieza.factor ** signo, combinar(total.dim, pieza.dim, signo))
        except (OverflowError, ZeroDivisionError):
            raise ValueError(f"Unidad desconocida: '{texto}'.") from None
        pos = m.end()
    if not total.factor:
        raise ValueError(f"Unidad desconocida: '{texto}'.")
    return total


def familia(dim):
    """Nombre de la magnitud («longitud», «área»…); una dimensión sin familia, su unidad interna («mm^4»)."""
    if dim == SIN_DIMENSION:
        return "un número sin unidad"
    return next((n.lower() for n, (d, _) in FAMILIAS.items() if d == dim), texto_dimension(dim))


def texto_dimension(dim):
    """La dimensión escrita con las unidades internas: «mm^2», «mm/s^2»."""
    def pieza(b, e):
        return b if e == 1 else f"{b}^{e:g}"
    arriba = "*".join(pieza(b, e) for b, e in zip(BASES, dim, strict=True) if e > 0) or "1"
    abajo = [pieza(b, -e) for b, e in zip(BASES, dim, strict=True) if e < 0]
    return arriba + "".join(f"/{p}" for p in abajo)
