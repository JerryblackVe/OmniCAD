# -*- coding: utf-8 -*-
"""
Lector de fuentes de una línea `.shx` de AutoCAD (las SHX de Fusion), en Python puro, sin Qt ni kernel.

Formatos: «unifont 1.0» (el de las SHX actuales, códigos Unicode) y «shapes 1.0 / 1.1» (los viejos, 1 byte por
código). «bigfont» (fuentes CJK) no se lee. Cada forma es una lista de bytes de comandos: pluma arriba / abajo,
vectores de 16 direcciones, desplazamientos, arcos (octante, fraccionario y de panza), escala (÷ / ×), pila de
posiciones y subformas. La SHX no trae anchos: el avance de una letra es donde queda la pluma al terminar.

`leer(ruta)` / `leer_bytes(datos)` devuelven una `FuenteSHX`; `FuenteSHX.glifo(codigo)` da
([trazo: [(x, y)…]…], avance) en unidades de la fuente (la altura de mayúscula es `above`) o None si no hay forma.
Se arma con los datos de OTRO (un archivo): topes de tamaño, de pasos y de recursión, y nada se ejecuta.
shortcut: la subforma «7, 0, …» de unifont (con origen y ventana) se mueve al origen pero no se escala a la
ventana; el arco fraccionario en sentido horario usa el mismo ángulo de partida que el antihorario.
"""
import math
import struct
from pathlib import Path

TOPE_ARCHIVO = 16 * 1024 * 1024
TOPE_PASOS = 100_000            # comandos por letra (corta ciclos y archivos hechos para colgar)
TOPE_PUNTOS = 200_000           # puntos por letra (un arco o una subforma repetida multiplica los puntos por comando)
TOPE_ESCALA = 1e6               # la escala (÷ / ×) no puede irse a infinito
PROFUNDIDAD = 8                 # subformas anidadas
_UNI = b"AutoCAD-86 unifont 1.0\r\n\x1a"
_SHAPES = (b"AutoCAD-86 shapes 1.0\r\n\x1a", b"AutoCAD-86 shapes 1.1\r\n\x1a")
_BIG = b"AutoCAD-86 bigfont 1.0\r\n\x1a"
_DIR = ((1, 0), (1, .5), (1, 1), (.5, 1), (0, 1), (-.5, 1), (-1, 1), (-1, .5),
        (-1, 0), (-1, -.5), (-1, -1), (-.5, -1), (0, -1), (.5, -1), (1, -1), (1, -.5))
_PASO_ARCO = math.radians(6)


class ErrorSHX(ValueError):
    """El archivo no es una SHX que se pueda leer."""


def _s8(b):
    return b - 256 if b > 127 else b


class _Estado:
    def __init__(self):
        self.x = self.y = 0.0
        self.abajo = False
        self.actual = None
        self.trazos = []
        self.mul = 1.0
        self.pila = []
        self.pasos = 0
        self.puntos = 0
        self.mudo = False       # el comando que se está leyendo se lee pero no se dibuja
        self.proximo_mudo = False   # «0E» (solo texto vertical): el comando que le sigue no cuenta en horizontal

    def ir(self, x, y):
        if self.abajo and not self.mudo:
            self.puntos += 1
            if self.puntos > TOPE_PUNTOS:
                self.pasos = TOPE_PASOS + 1         # corta la forma: todos los bucles miran `pasos`
                return
            if self.actual is None:
                self.puntos += 1                    # el punto de partida del trazo también cuenta
                self.actual = [(self.x, self.y)]
                self.trazos.append(self.actual)
            self.actual.append((x, y))
        if not self.mudo:
            self.x, self.y = x, y

    def arco(self, centro, v0, giro):
        """Arco desde el punto actual (centro + v0) girando `giro` radianes alrededor de `centro`."""
        n = max(2, int(abs(giro) / _PASO_ARCO) + 1)
        for k in range(1, n + 1):
            a = giro * k / n
            c, s = math.cos(a), math.sin(a)
            self.ir(centro[0] + v0[0] * c - v0[1] * s, centro[1] + v0[0] * s + v0[1] * c)


class FuenteSHX:
    def __init__(self, above, below, formas, ancho_sub):
        self.above, self.below = above, below
        self._formas = formas            # {código: bytes de comandos}
        self._ancho_sub = ancho_sub      # bytes del número de subforma (unifont 2, shapes 1)
        self._cache = {}

    def codigos(self):
        return [c for c in self._formas if c != 0]

    def glifo(self, codigo):
        if codigo not in self._formas or codigo == 0:
            return None
        if codigo not in self._cache:
            est = _Estado()
            try:
                self._ejecutar(codigo, est, 0)
                self._cache[codigo] = ([t for t in est.trazos if len(t) > 1], est.x)
            except (IndexError, ValueError, RecursionError):
                self._cache[codigo] = ([], 0.0)
        return self._cache[codigo]

    def _ejecutar(self, codigo, est, prof):
        cmds, i = self._formas[codigo], 0
        while i < len(cmds):
            i, fin = self._paso(cmds, i, est, prof)
            if fin or est.pasos > TOPE_PASOS:
                return

    def _paso(self, cmds, i, est, prof):
        """Un comando desde `i`. Devuelve (índice siguiente, ¿terminó la forma?). Un operando que falta corta la
        forma sin error."""
        est.pasos += 1
        c = cmds[i]
        i += 1
        if c == 0xE:
            est.proximo_mudo = True
            return i, False
        est.mudo, est.proximo_mudo = est.proximo_mudo, False
        try:
            return self._comando(c, cmds, i, est, prof)
        finally:
            est.mudo = False

    def _comando(self, c, cmds, i, est, prof):
        try:
            if c == 0:
                return i, True
            if c == 1 or c == 2:
                est.abajo, est.actual = c == 1, None
            elif c == 3 or c == 4:
                n = cmds[i]
                i += 1
                if n:
                    est.mul = min(max(est.mul / n if c == 3 else est.mul * n, 1 / TOPE_ESCALA), TOPE_ESCALA)
            elif c == 5:
                est.pila.append((est.x, est.y))
                if len(est.pila) > 16:
                    return i, True
            elif c == 6:
                if est.pila and not est.mudo:
                    est.x, est.y = est.pila.pop()
                    est.actual = None
            elif c == 7:
                i = self._subforma(cmds, i, est, prof)
            elif c == 8:
                est.ir(est.x + _s8(cmds[i]) * est.mul, est.y + _s8(cmds[i + 1]) * est.mul)
                i += 2
            elif c == 9:
                while _s8(cmds[i]) or _s8(cmds[i + 1]):
                    est.ir(est.x + _s8(cmds[i]) * est.mul, est.y + _s8(cmds[i + 1]) * est.mul)
                    i += 2
                i += 2
            elif c == 0xA:
                i = self._octante(cmds, i, est)
            elif c == 0xB:
                i = self._fraccionario(cmds, i, est)
            elif c == 0xC:
                self._panza(est, _s8(cmds[i]) * est.mul, _s8(cmds[i + 1]) * est.mul, _s8(cmds[i + 2]) / 127)
                i += 3
            elif c == 0xD:
                while _s8(cmds[i]) or _s8(cmds[i + 1]):
                    self._panza(est, _s8(cmds[i]) * est.mul, _s8(cmds[i + 1]) * est.mul, _s8(cmds[i + 2]) / 127)
                    i += 3
                i += 2
            elif c >> 4:
                v = _DIR[c & 0xF]
                largo = (c >> 4) * est.mul
                est.ir(est.x + v[0] * largo, est.y + v[1] * largo)
        except IndexError:
            return len(cmds), True
        return i, False

    def _subforma(self, cmds, i, est, prof):
        if self._ancho_sub == 2:
            n = cmds[i] << 8 | cmds[i + 1]       # el byte alto va primero (comprobado en las SHX de AutoCAD)
            i += 2
            ox = oy = 0.0
            if n == 0:                          # «7, 0, 0, forma(2), origen x, y, ancho, alto»
                n = cmds[i] << 8 | cmds[i + 1]
                ox, oy = _s8(cmds[i + 2]) * est.mul, _s8(cmds[i + 3]) * est.mul
                i += 6
        else:
            n, ox, oy = cmds[i], 0.0, 0.0
            i += 1
        if n in self._formas and n != 0 and prof < PROFUNDIDAD and not est.mudo:
            mul = est.mul
            if ox or oy:
                est.ir(est.x + ox, est.y + oy)
            self._ejecutar(n, est, prof + 1)
            est.mul = mul
        return i

    def _octante(self, cmds, i, est):
        radio, sc = cmds[i] * est.mul, cmds[i + 1]
        inicio, cuenta = sc >> 4 & 7, sc & 0xF or 8      # «(±)0SC»: bit 7 = sentido horario, S octante, C cuántos
        a0 = math.radians(45 * inicio)
        giro = math.radians(45 * cuenta) * (-1 if sc & 0x80 else 1)
        v0 = (radio * math.cos(a0), radio * math.sin(a0))
        est.arco((est.x - v0[0], est.y - v0[1]), v0, giro)
        return i + 2

    def _fraccionario(self, cmds, i, est):
        if i + 5 > len(cmds):                   # operandos que faltan: se corta la forma
            return len(cmds)
        ini, fin, alto, bajo, sc = cmds[i:i + 5]
        radio = (alto * 256 + bajo) * est.mul
        octante = math.radians(45)
        a0 = (sc >> 4 & 7) * octante + ini * octante / 256
        giro = (sc & 0xF) * octante + (fin - ini) * octante / 256
        if sc & 0x80:
            giro = -giro
        v0 = (radio * math.cos(a0), radio * math.sin(a0))
        est.arco((est.x - v0[0], est.y - v0[1]), v0, giro)
        return i + 5

    @staticmethod
    def _panza(est, dx, dy, panza):
        cuerda = math.hypot(dx, dy)
        if cuerda < 1e-12 or abs(panza) < 1e-9:
            est.ir(est.x + dx, est.y + dy)
            return
        # el centro queda a la izquierda de la cuerda si la panza es positiva (antihorario)
        d = cuerda / 2 * (1 - panza * panza) / (2 * panza)
        centro = (est.x + dx / 2 - dy / cuerda * d, est.y + dy / 2 + dx / cuerda * d)
        est.arco(centro, (est.x - centro[0], est.y - centro[1]), 4 * math.atan(panza))


def _nombre_y_cuerpo(cuerpo):
    """(nombre, comandos): la forma empieza con su nombre terminado en 0."""
    fin = cuerpo.find(b"\0")
    return (cuerpo[:fin], cuerpo[fin + 1:]) if fin >= 0 else (b"", None)


def leer_bytes(datos):
    """FuenteSHX desde el contenido de un archivo .shx. Levanta ErrorSHX si no se puede leer."""
    try:
        if datos.startswith(_UNI):
            i = len(_UNI)
            cuantas, largo0 = struct.unpack_from("<IH", datos, i)
            i += 6
            cuerpos = {0: datos[i:i + largo0]}
            if len(cuerpos[0]) < largo0:
                raise ErrorSHX("El archivo SHX está cortado.")
            i += largo0
            while i + 4 <= len(datos) and len(cuerpos) < cuantas:
                codigo, largo = struct.unpack_from("<HH", datos, i)
                i += 4
                if i + largo > len(datos):
                    break
                cuerpos[codigo] = datos[i:i + largo]
                i += largo
            ancho = 2
        elif any(datos.startswith(h) for h in _SHAPES):
            i = len(_SHAPES[0])
            _primera, _ultima, cuantas = struct.unpack_from("<HHH", datos, i)
            i += 6
            if cuantas * 4 > len(datos) - i:
                raise ErrorSHX("El archivo SHX está cortado.")
            tabla = [struct.unpack_from("<HH", datos, i + 4 * k) for k in range(cuantas)]
            i += 4 * cuantas
            cuerpos = {}
            for codigo, largo in tabla:
                cuerpos[codigo] = datos[i:i + largo]
                i += largo
            ancho = 1
        elif datos.startswith(_BIG):
            raise ErrorSHX("Las SHX «bigfont» (caracteres CJK) no están soportadas.")
        else:
            raise ErrorSHX("No es un archivo SHX (falta la cabecera «AutoCAD-86 …»).")
    except struct.error as e:
        raise ErrorSHX("El archivo SHX está cortado.") from e
    above = below = 0
    if 0 in cuerpos:
        _nombre, resto = _nombre_y_cuerpo(cuerpos.pop(0))
        if resto and len(resto) >= 2:
            above, below = resto[0], resto[1]
    formas = {}
    for codigo, cuerpo in cuerpos.items():
        _nombre, cmds = _nombre_y_cuerpo(cuerpo)
        if cmds is not None:
            formas[codigo] = cmds
    if not formas:
        raise ErrorSHX("El archivo SHX no trae ninguna forma.")
    f = FuenteSHX(above, below, formas, ancho)
    if not above:                       # sin cabecera de fuente (shapes 1.0): la mayor altura de las mayúsculas
        alturas = [max(p[1] for t in g[0] for p in t) for g in (f.glifo(ord(c)) for c in "HEIT") if g and g[0]]
        f.above = int(round(max(alturas))) if alturas else 1
    return f


def leer(ruta):
    """FuenteSHX desde un archivo .shx (tope de tamaño `TOPE_ARCHIVO`)."""
    p = Path(ruta)
    if p.stat().st_size > TOPE_ARCHIVO:
        raise ErrorSHX(f"El archivo SHX pesa más de {TOPE_ARCHIVO // 2**20} MB.")
    return leer_bytes(p.read_bytes())
