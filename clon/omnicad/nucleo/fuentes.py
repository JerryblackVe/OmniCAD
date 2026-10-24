# -*- coding: utf-8 -*-
"""
Fuentes tipográficas del texto de boceto, con fontTools (sin Qt).

Antes el texto dependía del administrador de fuentes de OpenCascade, que no ve las fuentes instaladas «solo
para el usuario» ni las variables. Acá se escanean todas (carpetas del sistema, del usuario, el registro de
Windows y las que se sumen), se guarda un catálogo en caché y los contornos salen directo de los glifos
(TrueType, OpenType/CFF, colecciones .ttc y variables), con espaciado entre letras, interlineado, caja con
ajuste de línea, alineación horizontal, anclaje vertical y volteo. Además, las opciones del panel «Carácter» de
los editores de diseño: kerning de la fuente (sí / no), inclinación (sesgo), escala horizontal y vertical,
desplazamiento de línea base, capitalización (mayúsculas, minúsculas, título, versalitas), subrayado y
tachado (simple o doble, con grosor propio) y «sin división» (la caja no parte las líneas).

`mapa_texto` devuelve dónde cae cada posición del cursor (para escribir y mover el cursor dentro del texto).

Limitación: no hay ligaduras ni formas contextuales (árabe, devanagari…): cada carácter es un glifo.
Equivale al texto de boceto de Fusion (SKT-CREATE-TEXT), con más opciones.
"""
import json
import math
import os
import sys
from functools import lru_cache
from pathlib import Path

EXTENSIONES = (".ttf", ".otf", ".ttc", ".otc")
CARPETAS_EXTRA = []              # carpetas sumadas en tiempo de ejecución (agregar_carpeta)
ALINEACIONES = ("izq", "centro", "der")
ANCLAJES = ("base", "arriba", "medio", "abajo")
CAPITALIZACIONES = ("ninguno", "mayusculas", "minusculas", "titulo", "versalitas")
DECORACIONES = ("ninguno", "simple", "doble")
FACTOR_VERSALITAS = 0.8          # tamaño de las minúsculas pasadas a versalitas
MAX_INCLINACION = 80.0           # grados de sesgo (más allá la tangente se dispara)
_CATALOGO = []


class ErrorFuente(ValueError):
    """No se encontró o no se pudo leer la fuente pedida."""


# ---------------------------------------------------------------- dónde están las fuentes
def carpetas_de_fuentes():
    """Carpetas donde buscar fuentes: sistema, usuario, variable OMNICAD_FUENTES y las sumadas a mano."""
    c = []
    if sys.platform.startswith("win"):
        c.append(Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            c.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    elif sys.platform == "darwin":
        c += [Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library" / "Fonts"]
    else:
        c += [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts",
              Path.home() / ".local" / "share" / "fonts"]
    c += [Path(p) for p in os.environ.get("OMNICAD_FUENTES", "").split(os.pathsep) if p.strip()]
    c += [Path(p) for p in CARPETAS_EXTRA]
    return c


def _archivos_del_registro():
    """Archivos de fuentes registrados en Windows (incluye los instalados fuera de las carpetas de fuentes)."""
    if not sys.platform.startswith("win"):
        return []
    try:
        import winreg
    except ImportError:
        return []
    salida = []
    base = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for raiz in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(raiz, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as k:
                i = 0
                while True:
                    try:
                        _, valor, _ = winreg.EnumValue(k, i)
                    except OSError:
                        break
                    i += 1
                    p = Path(str(valor))
                    salida.append(p if p.is_absolute() else base / p)
        except OSError:
            continue
    return salida


def _archivos():
    vistos, salida = set(), []
    candidatos = list(_archivos_del_registro())
    for carpeta in carpetas_de_fuentes():
        if carpeta.is_dir():
            for raiz, _dirs, nombres in os.walk(carpeta):
                candidatos += [Path(raiz) / n for n in nombres]
    for p in candidatos:
        if p.suffix.lower() in EXTENSIONES:
            clave = str(p).casefold()
            if clave not in vistos and p.is_file():
                vistos.add(clave)
                salida.append(p)
    return salida


# ---------------------------------------------------------------- catálogo
def _ruta_cache():
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return base / "OmniCAD" / "fuentes_v1.json"


def _registros_de(ruta):
    """Un registro por cada fuente que trae el archivo (las .ttc traen varias)."""
    from fontTools.ttLib import TTCollection, TTFont
    try:
        if ruta.suffix.lower() in (".ttc", ".otc"):
            fuentes = list(TTCollection(str(ruta), lazy=True).fonts)
        else:
            fuentes = [TTFont(str(ruta), lazy=True)]
    except Exception:  # noqa: BLE001 — un archivo roto no tiene que frenar el escaneo
        return []
    salida = []
    for i, f in enumerate(fuentes):
        try:
            nombres = f["name"]
            familia = nombres.getDebugName(16) or nombres.getDebugName(1)
            if not familia:
                continue
            os2 = f["OS/2"] if "OS/2" in f else None
            peso = int(getattr(os2, "usWeightClass", 400) or 400)
            mac = f["head"].macStyle if "head" in f else 0
            cursiva = bool(mac & 2) or bool(os2 is not None and os2.fsSelection & 1)
            ejes = {}
            if "fvar" in f:
                ejes = {a.axisTag: [a.minValue, a.defaultValue, a.maxValue] for a in f["fvar"].axes}
            salida.append({"familia": familia, "estilo": nombres.getDebugName(17) or nombres.getDebugName(2) or "",
                           "completo": nombres.getDebugName(4) or familia, "ruta": str(ruta), "indice": i,
                           "peso": peso, "cursiva": cursiva, "ejes": ejes})
        except Exception:  # noqa: BLE001
            continue
    return salida


def catalogo(forzar=False):
    """Lista de registros de todas las fuentes instaladas (con caché en disco por archivo, fecha y tamaño)."""
    global _CATALOGO
    if _CATALOGO and not forzar:
        return _CATALOGO
    cache_ruta, cache = _ruta_cache(), {}
    try:
        cache = json.loads(cache_ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    nuevo, salida = {}, []
    for p in _archivos():
        try:
            st = p.stat()
        except OSError:
            continue
        clave = str(p)
        previo = cache.get(clave)
        if previo and previo.get("mtime") == st.st_mtime and previo.get("size") == st.st_size:
            entrada = previo
        else:
            entrada = {"mtime": st.st_mtime, "size": st.st_size, "registros": _registros_de(p)}
        nuevo[clave] = entrada
        salida += entrada["registros"]
    if nuevo != cache:
        try:
            cache_ruta.parent.mkdir(parents=True, exist_ok=True)
            cache_ruta.write_text(json.dumps(nuevo), encoding="utf-8")
        except OSError:
            pass
    _CATALOGO = salida + [dict(_TRAZO)]
    return _CATALOGO


# ---------------------------------------------------------------- fuente de un trazo (SHX de Fusion), propia
# Trazos en una grilla de 100 unidades de fuente: mayúscula de 7 de alto, ancho 4 salvo los que dicen otro.
# shortcut: solo mayúsculas, números y signos comunes (las minúsculas salen en mayúscula); sumar minúsculas si
# hace falta grabar texto mixto.
_TRAZOS = {
    "A": "0,0 2,7 4,0;0.7,2.5 3.3,2.5", "B": "0,0 0,7 3,7 4,6 4,4.5 3,3.5 0,3.5;3,3.5 4,2.5 4,1 3,0 0,0",
    "C": "4,6 3,7 1,7 0,6 0,1 1,0 3,0 4,1", "D": "0,0 0,7 2.5,7 4,5.5 4,1.5 2.5,0 0,0",
    "E": "4,7 0,7 0,0 4,0;0,3.5 3,3.5", "F": "4,7 0,7 0,0;0,3.5 3,3.5",
    "G": "4,6 3,7 1,7 0,6 0,1 1,0 3,0 4,1 4,3 2.5,3", "H": "0,0 0,7;4,0 4,7;0,3.5 4,3.5",
    "I": "0,7 2,7;1,7 1,0;0,0 2,0", "J": "1,7 4,7;3,7 3,1 2,0 1,0 0,1 0,2", "K": "0,0 0,7;4,7 0,2.5;1.3,3.8 4,0",
    "L": "0,7 0,0 4,0", "M": "0,0 0,7 2,3.5 4,7 4,0", "N": "0,0 0,7 4,0 4,7",
    "O": "1,0 0,1 0,6 1,7 3,7 4,6 4,1 3,0 1,0", "P": "0,0 0,7 3,7 4,6 4,4.5 3,3.5 0,3.5",
    "Q": "1,0 0,1 0,6 1,7 3,7 4,6 4,1 3,0 1,0;2.5,1.5 4.3,-0.3",
    "R": "0,0 0,7 3,7 4,6 4,4.5 3,3.5 0,3.5;2,3.5 4,0",
    "S": "4,6 3,7 1,7 0,6 0,4.5 1,3.5 3,3.5 4,2.5 4,1 3,0 1,0 0,1", "T": "0,7 4,7;2,7 2,0",
    "U": "0,7 0,1 1,0 3,0 4,1 4,7", "V": "0,7 2,0 4,7", "W": "0,7 1.25,0 2.5,5 3.75,0 5,7", "X": "0,0 4,7;0,7 4,0",
    "Y": "0,7 2,3.5 4,7;2,3.5 2,0", "Z": "0,7 4,7 0,0 4,0",
    "0": "1,0 0,1 0,6 1,7 3,7 4,6 4,1 3,0 1,0;0.3,0.7 3.7,6.3", "1": "0,5.5 1.5,7 1.5,0;0,0 3,0",
    "2": "0,6 1,7 3,7 4,6 4,4.5 0,0 4,0", "3": "0,6 1,7 3,7 4,6 4,4.5 3,3.5 1.5,3.5;3,3.5 4,2.5 4,1 3,0 1,0 0,1",
    "4": "3,0 3,7 0,2 4,2", "5": "4,7 0,7 0,4 3,4 4,3 4,1 3,0 1,0 0,1",
    "6": "4,6 3,7 1,7 0,6 0,1 1,0 3,0 4,1 4,3 3,4 0,4", "7": "0,7 4,7 1.5,0",
    "8": "1,3.5 0,4.5 0,6 1,7 3,7 4,6 4,4.5 3,3.5 1,3.5 0,2.5 0,1 1,0 3,0 4,1 4,2.5 3,3.5",
    "9": "4,3 1,3 0,4 0,6 1,7 3,7 4,6 4,1 3,0 1,0 0,1",
    ".": "0,0 0,0.5", ",": "0.3,0.5 0.3,0 0,-1", "-": "0,3.5 3,3.5", "+": "0,3.5 4,3.5;2,1.5 2,5.5", "/": "0,0 4,7",
    ":": "0,1.5 0,2;0,5 0,5.5", "(": "1.5,7.5 0.5,6 0,3.5 0.5,1 1.5,-0.5", ")": "0,7.5 1,6 1.5,3.5 1,1 0,-0.5",
    "=": "0,2.5 4,2.5;0,4.5 4,4.5", "_": "0,-1 4,-1", "!": "0,7 0,2;0,0 0,0.5",
    "?": "0,6 1,7 3,7 4,6 4,4.5 2,3 2,2;2,0 2,0.5", "'": "0,7 0,5.5", '"': "0,7 0,5.5;1.2,7 1.2,5.5",
    "#": "1,0 1.5,7;2.5,0 3,7;0,2.5 4,2.5;0,4.5 4,4.5", "*": "2,6 2,2;0.3,5 3.7,3;0.3,3 3.7,5",
    "<": "4,6 0,3.5 4,1", ">": "0,6 4,3.5 0,1", "%": "0,0 4,7;0.5,6.5 0.5,5.5;3.5,1.5 3.5,0.5",
    "°": "0.5,7 1,6.5 0.5,6 0,6.5 0.5,7", ".notdef": "0,0 4,0 4,7 0,7 0,0",
}
_MARCAS = {"́": "1.5,7.8 2.5,8.8", "̀": "1.5,8.8 2.5,7.8", "̃": "0.8,8 1.5,8.5 2.5,8 3.2,8.5",
           "̈": "1,8 1,8.4;3,8 3,8.4"}
_TRAZO = {"familia": "OmniCAD Trazo SHX", "estilo": "Regular", "completo": "OmniCAD Trazo SHX", "ruta": "omnicad:trazo",
          "indice": 0, "peso": 400, "cursiva": False, "ejes": {}, "una_linea": True}


class _GlifoTrazo:
    def __init__(self, trazos):
        self.trazos = [[tuple(100 * float(v) for v in q.split(",")) for q in t.split()]
                       for t in trazos.split(";") if t.strip()]

    def draw(self, lapiz):
        for t in self.trazos:
            lapiz.moveTo(t[0])
            for q in t[1:]:
                lapiz.lineTo(q)
            lapiz.endPath()


class _OrdenTrazo:
    @staticmethod
    def getGlyphOrder():
        return [".notdef"]


@lru_cache(maxsize=1)
def _datos_trazo():
    """Los datos de `_datos` para la fuente de un trazo (las letras son líneas abiertas: no forman perfiles,
    como las SHX de Fusion; sirven para grabar o marcar con una herramienta que sigue la línea)."""
    import unicodedata
    gs = {n: _GlifoTrazo(t) for n, t in _TRAZOS.items()}
    cmap = {ord(n): n for n in _TRAZOS if len(n) == 1}
    cmap |= {ord(n.lower()): n for n in _TRAZOS if len(n) == 1 and n.lower() != n}
    for cod in range(0xC0, 0x180):                     # acentos del latín: la letra base más su marca
        base, *marcas = unicodedata.normalize("NFD", chr(cod))
        if base.upper() in gs and marcas and all(m in _MARCAS for m in marcas):
            nombre = chr(cod).upper()
            gs[nombre] = _GlifoTrazo(";".join([_TRAZOS[base.upper()]] + [_MARCAS[m] for m in marcas]))
            cmap[cod] = nombre
    hmtx = {n: (max(q[0] for t in g.trazos for q in t) + 150.0, 0) for n, g in gs.items()}
    gs[" "], hmtx[" "], cmap[32] = _GlifoTrazo(""), (300.0, 0), " "
    return {"f": _OrdenTrazo(), "upem": 1000.0, "cmap": cmap, "hmtx": hmtx, "gs": gs, "asc": 800.0, "desc": -200.0,
            "gap": 0.0, "kern": lambda _a, _b: 0, "sub_gro": 50.0, "sub_pos": -100.0, "tac_gro": 50.0,
            "tac_pos": 350.0}


def glifos_faltantes(texto, fuente="Arial", negrita=False, cursiva=False):
    """Caracteres del texto que la fuente no tiene (se dibujarían con el cuadrito `.notdef`), sin repetir."""
    cmap = _fuente_datos(fuente, negrita, cursiva)["cmap"]
    return list(dict.fromkeys(ch for ch in str(texto) if not ch.isspace() and ord(ch) not in cmap))


def agregar_carpeta(ruta):
    """Suma una carpeta de fuentes y vuelve a armar el catálogo. Devuelve cuántas fuentes se sumaron."""
    p = Path(ruta)
    if not p.is_dir():
        raise ErrorFuente(f"No existe la carpeta de fuentes: {ruta}")
    antes = len(catalogo())
    if str(p) not in map(str, CARPETAS_EXTRA):
        CARPETAS_EXTRA.append(str(p))
    return len(catalogo(forzar=True)) - antes


def familias():
    """Nombres de familia, ordenados y sin repetir."""
    return sorted({r["familia"] for r in catalogo()}, key=str.casefold)


def estilos(familia):
    """Registros de una familia (para listar sus estilos)."""
    return [r for r in catalogo() if r["familia"].casefold() == str(familia).casefold()]


def buscar_fuente(nombre, negrita=False, cursiva=False):
    """Registro de la fuente que mejor corresponde a `nombre` (familia, nombre completo, nombre de archivo o
    ruta a un .ttf/.otf) con el peso y la cursiva pedidos; None si no está."""
    nombre = str(nombre or "").strip()
    if not nombre:
        return None
    p = Path(nombre)
    if p.suffix.lower() in EXTENSIONES and p.is_file():
        regs = _registros_de(p)
        return regs[0] if regs else None
    clave = nombre.casefold()
    todas = catalogo()
    cand = [r for r in todas if r["familia"].casefold() == clave]
    cand = cand or [r for r in todas if r["completo"].casefold() == clave]
    cand = cand or [r for r in todas if Path(r["ruta"]).stem.casefold() == clave]
    if not cand:
        return None
    peso = 700 if negrita else 400

    def costo(r):
        if "wght" in r["ejes"]:                  # una fuente variable cubre cualquier peso
            return (r["cursiva"] != bool(cursiva), 0)
        return (r["cursiva"] != bool(cursiva), abs(r["peso"] - peso))
    return min(cand, key=costo)


# ---------------------------------------------------------------- contornos
@lru_cache(maxsize=24)
def _abrir(ruta, indice, peso_variable):
    from fontTools.ttLib import TTCollection, TTFont
    if str(ruta).lower().endswith((".ttc", ".otc")):
        f = TTCollection(ruta).fonts[indice]
    else:
        f = TTFont(ruta)
    if peso_variable and "fvar" in f:
        try:
            from fontTools.varLib.instancer import instantiateVariableFont
            ejes = {a.axisTag: a for a in f["fvar"].axes}
            w = ejes["wght"]
            f = instantiateVariableFont(f, {"wght": min(max(peso_variable, w.minValue), w.maxValue)})
        except Exception:  # noqa: BLE001 — si no se puede fijar el peso, queda el de la instancia por defecto
            pass
    return f


@lru_cache(maxsize=24)
def _datos(ruta, indice, peso_variable):
    f = _abrir(ruta, indice, peso_variable)
    upem = float(f["head"].unitsPerEm)
    hhea = f["hhea"]
    os2 = f["OS/2"] if "OS/2" in f else None
    asc = float(getattr(os2, "sTypoAscender", 0) or hhea.ascent or 0.8 * upem)
    desc = float(getattr(os2, "sTypoDescender", 0) or hhea.descent or -0.2 * upem)
    gap = float(getattr(os2, "sTypoLineGap", 0) or hhea.lineGap or 0.0)
    if asc - desc < 0.5 * upem:                     # métricas vacías o absurdas
        asc, desc = float(hhea.ascent), float(hhea.descent)
    post = f["post"] if "post" in f else None
    sub_gro = float(getattr(post, "underlineThickness", 0) or 0.05 * upem)
    sub_pos = float(getattr(post, "underlinePosition", 0) or -0.1 * upem)       # centro de la barra, bajo la base
    tac_gro = float(getattr(os2, "yStrikeoutSize", 0) or sub_gro)
    tac_pos = float(getattr(os2, "yStrikeoutPosition", 0) or 0.28 * upem)
    return {"f": f, "upem": upem, "cmap": f.getBestCmap() or {}, "hmtx": f["hmtx"], "gs": f.getGlyphSet(),
            "asc": asc, "desc": desc, "gap": gap, "kern": _tabla_kern(f),
            "sub_gro": sub_gro, "sub_pos": sub_pos, "tac_gro": tac_gro, "tac_pos": tac_pos}


def _tabla_kern(f):
    """Función (izq, der) → ajuste en unidades de fuente, con la tabla `kern` o los pares GPOS de 'kern'."""
    pares = {}
    try:
        if "kern" in f:
            for t in f["kern"].kernTables:
                pares.update(t.kernTable)
    except Exception:  # noqa: BLE001
        pass
    sub = []
    try:
        if "GPOS" in f:
            gpos = f["GPOS"].table
            idx = set()
            for fr in gpos.FeatureList.FeatureRecord:
                if fr.FeatureTag == "kern":
                    idx.update(fr.Feature.LookupListIndex)
            for i in sorted(idx):
                lk = gpos.LookupList.Lookup[i]
                for st in lk.SubTable:
                    st = getattr(st, "ExtSubTable", st)
                    if getattr(st, "LookupType", lk.LookupType) == 2 or hasattr(st, "PairSet") or hasattr(st, "Class1Record"):
                        sub.append(st)
    except Exception:  # noqa: BLE001
        sub = []

    @lru_cache(maxsize=4096)
    def kern(a, b):
        if (a, b) in pares:
            return pares[(a, b)]
        for st in sub:
            try:
                cov = st.Coverage.glyphs
                if a not in cov:
                    continue
                if st.Format == 1:
                    for rec in st.PairSet[cov.index(a)].PairValueRecord:
                        if rec.SecondGlyph == b:
                            return getattr(rec.Value1, "XAdvance", 0) or 0
                elif st.Format == 2:
                    c1 = st.ClassDef1.classDefs.get(a, 0)
                    c2 = st.ClassDef2.classDefs.get(b, 0)
                    v = st.Class1Record[c1].Class2Record[c2].Value1
                    x = getattr(v, "XAdvance", 0) or 0
                    if x:
                        return x
            except Exception:  # noqa: BLE001
                continue
        return 0
    return kern


def _lapiz(gs, dx, dy, sx, sy, sesgo, salida):
    """Lápiz que vuelca un glifo como primitivas ('linea' y 'spline') con el origen en (dx, dy), escala sx × sy y
    `sesgo` (tangente del ángulo de inclinación: cada punto corre y·sesgo en x)."""
    from fontTools.pens.basePen import BasePen

    class Lapiz(BasePen):
        def __init__(self):
            super().__init__(gs)
            self.ini = self.act = None

        @staticmethod
        def _t(p):
            return (dx + p[0] * sx + p[1] * sy * sesgo, dy + p[1] * sy)

        def _moveTo(self, p):
            self.ini = self.act = self._t(p)

        def _lineTo(self, p):
            q = self._t(p)
            if self.act is not None and abs(q[0] - self.act[0]) + abs(q[1] - self.act[1]) > 1e-9:
                salida.append(("linea", None, self.act, q))
            self.act = q

        def _curveToOne(self, p1, p2, p3):
            polos = (self.act, self._t(p1), self._t(p2), self._t(p3))
            self._spline(polos, 3, (0.0,) * 4 + (1.0,) * 4)

        def _qCurveToOne(self, p1, p2):
            polos = (self.act, self._t(p1), self._t(p2))
            self._spline(polos, 2, (0.0,) * 3 + (1.0,) * 3)

        def _spline(self, polos, grado, nudos):
            if max(abs(q[0] - polos[0][0]) + abs(q[1] - polos[0][1]) for q in polos[1:]) > 1e-9:
                salida.append(("spline", None, polos, nudos, grado, None))
            self.act = polos[-1]

        def _closePath(self):
            if self.act is not None and self.ini is not None:
                self._lineTo_abs(self.ini)
            self.act = self.ini

        def _lineTo_abs(self, q):
            if abs(q[0] - self.act[0]) + abs(q[1] - self.act[1]) > 1e-9:
                salida.append(("linea", None, self.act, q))
            self.act = q

    return Lapiz()


# ---------------------------------------------------------------- composición (una sola para contornos y cursor)
_PREDETERMINADAS = {"espaciado": 0.0, "interlineado": 1.0, "alineacion": "izq", "ancla_v": "base", "ancho_caja": 0.0,
                    "voltear_h": False, "voltear_v": False, "kerning": True, "inclinacion": 0.0, "escala_h": 100.0,
                    "escala_v": 100.0, "desfase_base": 0.0, "capitalizacion": "ninguno", "subrayado": "ninguno",
                    "tachado": "ninguno", "grosor_decoracion": 0.0, "sin_division": False, "ajustes_kerning": ()}
_DE_COMPOSICION = ("espaciado", "interlineado", "alineacion", "ancla_v", "ancho_caja", "kerning", "inclinacion",
                   "escala_h", "escala_v", "capitalizacion", "sin_division", "ajustes_kerning")


def _opciones(dadas):
    """Opciones del texto con sus valores por defecto, validadas. Levanta ErrorFuente si algo no sirve."""
    desconocidas = set(dadas) - set(_PREDETERMINADAS)
    if desconocidas:
        raise ErrorFuente(f"Opciones de texto desconocidas: {', '.join(sorted(desconocidas))}.")
    o = _PREDETERMINADAS | dict(dadas)
    if o["alineacion"] not in ALINEACIONES:
        raise ErrorFuente(f"Alineación desconocida: {o['alineacion']} (izq, centro, der).")
    if o["ancla_v"] not in ANCLAJES:
        raise ErrorFuente(f"Anclaje vertical desconocido: {o['ancla_v']} (base, arriba, medio, abajo).")
    if o["capitalizacion"] not in CAPITALIZACIONES:
        raise ErrorFuente(f"Capitalización desconocida: {o['capitalizacion']} ({', '.join(CAPITALIZACIONES)}).")
    for k in ("subrayado", "tachado"):
        if o[k] not in DECORACIONES:
            raise ErrorFuente(f"«{k}» desconocido: {o[k]} ({', '.join(DECORACIONES)}).")
    for k in ("escala_h", "escala_v"):
        if not (math.isfinite(o[k]) and 1.0 <= o[k] <= 1000.0):
            raise ErrorFuente(f"«{k}» va de 1 a 1000 (%).")
    if not (math.isfinite(o["inclinacion"]) and abs(o["inclinacion"]) <= MAX_INCLINACION):
        raise ErrorFuente(f"La inclinación va de -{MAX_INCLINACION:g} a {MAX_INCLINACION:g} grados.")
    if not (math.isfinite(o["grosor_decoracion"]) and o["grosor_decoracion"] >= 0):
        raise ErrorFuente("El grosor de la decoración tiene que ser un número mayor o igual que cero.")
    if not math.isfinite(o["desfase_base"]):
        raise ErrorFuente("El desplazamiento de la línea base tiene que ser un número finito.")
    try:
        o["ajustes_kerning"] = tuple((int(i), float(x)) for i, x in o["ajustes_kerning"])
    except (TypeError, ValueError):
        raise ErrorFuente("Los ajustes de kerning son pares [posición, mm].") from None
    if not all(i >= 0 and math.isfinite(x) for i, x in o["ajustes_kerning"]):
        raise ErrorFuente("Los ajustes de kerning necesitan posiciones desde 0 y valores finitos (mm).")
    return o


def _fuente_datos(fuente, negrita, cursiva):
    reg = buscar_fuente(fuente, negrita, cursiva)
    if reg is None:
        raise ErrorFuente(f"No se encontró la fuente «{fuente}».")
    if reg["ruta"] == _TRAZO["ruta"]:
        return _datos_trazo()
    peso =(700 if negrita else 400) if "wght" in reg["ejes"] else 0
    return _datos(reg["ruta"], reg["indice"], peso)


def _capitalizar(texto, modo):
    """(texto, factores): el texto con la capitalización pedida, carácter por carácter (el largo no cambia, así los
    índices del cursor siguen valiendo) y el tamaño relativo de cada uno (solo las versalitas lo cambian; None si
    todos valen 1)."""
    if modo == "ninguno":
        return texto, None
    salida, factores, tras_letra = [], [], False
    for ch in texto:
        f = 1.0
        if modo == "mayusculas":
            nuevo = ch.upper()
        elif modo == "minusculas":
            nuevo = ch.lower()
        elif modo == "titulo":
            nuevo = ch.lower() if tras_letra else ch.upper()
        else:                                            # versalitas: las minúsculas pasan a mayúscula más chica
            nuevo = ch.upper()
            if nuevo != ch:
                f = FACTOR_VERSALITAS
        if len(nuevo) != 1:                              # «ß».upper() = «SS»: cambiaría el largo
            nuevo, f = ch, 1.0
        salida.append(nuevo)
        factores.append(f)
        tras_letra = ch.isalnum()
    return "".join(salida), (factores if any(f != 1.0 for f in factores) else None)


def _lineas_visuales(texto, ancho_max, ancho_de):
    """Líneas de composición [(inicio, fin)] como índices de `texto`: una por salto de línea y, si `ancho_max` > 0,
    partidas en palabras para que ninguna pase de ese ancho (una palabra más larga queda sola). `ancho_de(i, j)`
    mide el tramo texto[i:j]. El espacio donde se corta (y el salto de línea) quedan fuera de las dos líneas."""
    salida, pos = [], 0
    for linea in texto.split("\n"):
        fin_linea = pos + len(linea)
        if ancho_max <= 0:
            salida.append((pos, fin_linea))
        else:
            ini = actual_fin = cursor = pos
            for k, palabra in enumerate(linea.split(" ")):
                fin_palabra = cursor + len(palabra)
                if k > 0 and actual_fin > ini and ancho_de(ini, fin_palabra) > ancho_max:
                    salida.append((ini, actual_fin))
                    ini = cursor
                actual_fin = fin_palabra
                cursor = fin_palabra + 1
            salida.append((ini, actual_fin))
        pos = fin_linea + 1
    return salida


def _maquetar(texto, d, altura, *, espaciado=0.0, interlineado=1.0, alineacion="izq", ancla_v="base",
              ancho_caja=0.0, kerning=True, inclinacion=0.0, escala_h=100.0, escala_v=100.0,
              capitalizacion="ninguno", sin_division=False, ajustes_kerning=()):
    """Compone el texto sin dibujarlo: dónde cae cada carácter. Devuelve un dict con `texto` (ya capitalizado, con
    saltos «\\n»), `gl` (glifo de cada carácter), `f_(i)` (tamaño relativo del carácter i), `avance(i)`, `lineas`
    (por línea de composición: `ini`, `fin`, `x`, `y` de la línea base, `xs` (x de cada carácter relativa a `x`) y
    `ancho`), `ancho_bloque`, `y_sup` / `y_inf` (bordes del bloque), `asc` / `desc` (ya con la escala vertical),
    `sx` / `sy` (escala de los glifos) y `sesgo`."""
    texto = str(texto).replace("\r\n", "\n").replace("\r", "\n")
    texto, fc = _capitalizar(texto, capitalizacion)
    s = float(altura) / d["upem"]
    sh, sv = float(escala_h) / 100.0, float(escala_v) / 100.0
    cmap, hmtx, kern = d["cmap"], d["hmtx"], d["kern"]
    notdef = d["f"].getGlyphOrder()[0]
    gl = [cmap.get(ord(ch), notdef) for ch in texto]

    def f_(i):
        return 1.0 if fc is None else fc[i]

    def avance(i):
        try:
            return hmtx[gl[i]][0] * s * sh * f_(i)
        except KeyError:
            return 0.0

    manual = dict(ajustes_kerning)           # {posición: mm}: ajuste a mano entre la letra i - 1 y la i

    def posiciones(ini, fin):
        """x de cada carácter del tramo (con kerning y espaciado) y el ancho del tramo."""
        xs, x = [], 0.0
        for i in range(ini, fin):
            if i > ini:
                x += manual.get(i, 0.0)
                if kerning:
                    x += kern(gl[i - 1], gl[i]) * s * sh * f_(i)
            xs.append(x)
            x += avance(i) + espaciado
        return xs, x - (espaciado if fin > ini else 0.0)

    tramos = _lineas_visuales(texto, 0.0 if sin_division else float(ancho_caja or 0.0),
                              lambda i, j: posiciones(i, j)[1])
    medidas = [posiciones(i, j) for i, j in tramos]
    ancho_bloque = float(ancho_caja) if ancho_caja and ancho_caja > 0 else max([w for _xs, w in medidas] + [0.0])
    paso = (d["asc"] - d["desc"] + d["gap"]) * s * float(interlineado)
    asc, desc = d["asc"] * s * sv, d["desc"] * s * sv
    n = len(tramos)
    alto = (n - 1) * paso + (asc - desc)
    y0 = {"base": 0.0, "arriba": -asc, "medio": -asc + alto / 2, "abajo": -asc + alto}[ancla_v]
    lineas = []
    for k, ((i, j), (xs, w)) in enumerate(zip(tramos, medidas, strict=True)):
        x = {"izq": 0.0, "centro": (ancho_bloque - w) / 2, "der": ancho_bloque - w}[alineacion]
        lineas.append({"ini": i, "fin": j, "x": x, "y": y0 - k * paso, "xs": xs, "ancho": w})
    return {"texto": texto, "gl": gl, "f_": f_, "avance": avance, "lineas": lineas, "ancho_bloque": ancho_bloque,
            "y_sup": y0 + asc, "y_inf": y0 - (n - 1) * paso + desc, "asc": asc, "desc": desc, "s": s,
            "sx": s * sh, "sy": s * sv, "sesgo": math.tan(math.radians(float(inclinacion)))}


def _de_composicion(o):
    return {k: o[k] for k in _DE_COMPOSICION}


def _barras_decoracion(d, m, o):
    """Barras de subrayado y tachado como [(centro, grosor)] relativas a la línea base (mm). Doble = dos barras
    separadas un grosor. Con `grosor_decoracion` > 0 ese grosor manda; si no, el de la fuente."""
    barras = []
    for modo, pos, gro, abajo in ((o["subrayado"], d["sub_pos"], d["sub_gro"], True),
                                  (o["tachado"], d["tac_pos"], d["tac_gro"], False)):
        if modo == "ninguno":
            continue
        t = o["grosor_decoracion"] if o["grosor_decoracion"] > 0 else gro * m["s"]
        c = pos * m["sy"]
        if modo == "simple":
            barras.append((c, t))
        elif abajo:
            barras += [(c, t), (c - 2 * t, t)]
        else:
            barras += [(c + t, t), (c - t, t)]
    return barras


# ---------------------------------------------------------------- contornos
def contornos_texto(texto, fuente="Arial", altura=5.0, negrita=False, cursiva=False, **opciones):
    """Contornos de un texto como primitivas 2D ('linea' y 'spline' de Bézier, id None) con el origen en el
    ancla: la esquina izquierda de la caja y, en vertical, la línea base de la primera línea ("base"), su
    borde superior ("arriba"), el centro del bloque ("medio") o el borde inferior de la última ("abajo").
    `altura` es el tamaño de la fuente en mm.

    Opciones: `espaciado` (mm extra entre letras), `interlineado` (factor sobre el salto de línea de la fuente),
    `alineacion` (izq / centro / der dentro de la caja), `ancla_v`, `ancho_caja` (> 0 parte las líneas en
    palabras), `voltear_h` / `voltear_v` (espejo del bloque), `kerning` (False ignora los pares de la fuente),
    `ajustes_kerning` ([(posición, mm)]: kerning a mano entre la letra anterior y la de esa posición),
    `inclinacion` (grados de sesgo; no es la cursiva de la fuente), `escala_h` / `escala_v` (% del ancho y del alto
    de las letras, de 1 a 1000), `desfase_base` (mm que sube todo el texto), `capitalizacion` (ninguno, mayusculas,
    minusculas, titulo, versalitas), `subrayado` y `tachado` (ninguno, simple, doble: barras cerradas que forman
    perfiles), `grosor_decoracion` (mm; 0 = el de la fuente) y `sin_division` (True: `ancho_caja` no parte las
    líneas). Levanta ErrorFuente si la fuente no existe o una opción no sirve."""
    d = _fuente_datos(fuente, negrita, cursiva)
    o = _opciones(opciones)
    m = _maquetar(texto, d, altura, **_de_composicion(o))
    salida = []
    for ln in m["lineas"]:
        for j in range(ln["fin"] - ln["ini"]):
            i = ln["ini"] + j
            if m["texto"][i].isspace():
                continue
            f = m["f_"](i)
            try:
                d["gs"][m["gl"][i]].draw(_lapiz(d["gs"], ln["x"] + ln["xs"][j], ln["y"], m["sx"] * f, m["sy"] * f,
                                                m["sesgo"], salida))
            except KeyError:
                pass
    barras = _barras_decoracion(d, m, o)
    if barras:
        for ln in m["lineas"]:
            if ln["ancho"] <= 1e-9:
                continue
            x1, x2 = ln["x"], ln["x"] + ln["ancho"]
            for centro, grosor in barras:
                y1, y2 = ln["y"] + centro - grosor / 2, ln["y"] + centro + grosor / 2
                esquinas = ((x1, y1), (x2, y1), (x2, y2), (x1, y2))
                salida += [("linea", None, a, b) for a, b in zip(esquinas, esquinas[1:] + esquinas[:1], strict=True)]
    if o["voltear_h"] or o["voltear_v"] or o["desfase_base"]:
        w, y_sum, dy = m["ancho_bloque"], m["y_sup"] + m["y_inf"], o["desfase_base"]

        def v(q):
            return ((w - q[0]) if o["voltear_h"] else q[0],
                    ((y_sum - q[1]) if o["voltear_v"] else q[1]) + dy)
        salida = [("linea", None, v(p[2]), v(p[3])) if p[0] == "linea"
                  else ("spline", None, tuple(v(q) for q in p[2]), p[3], p[4], p[5]) for p in salida]
    return salida


def mapa_texto(texto, fuente="Arial", altura=5.0, negrita=False, cursiva=False, **opciones):
    """Dónde cae cada posición del cursor de un texto recto, en las mismas coordenadas que `contornos_texto`
    (mismas opciones): {"paradas": [(x, y)] con n + 1 posiciones (y = línea base), "linea_de": [nº de línea de
    composición de cada posición], "lineas": [(ini, fin)] (índices de cada línea), "abajo" / "arriba": hasta
    dónde baja y sube el cursor desde la línea base, "sesgo": cuánto corre en x por cada mm de y}. La posición i
    es el borde izquierdo del carácter i; la n, el final del texto. Con la caja que parte líneas, el espacio donde
    se corta queda al final de la línea de arriba."""
    d = _fuente_datos(fuente, negrita, cursiva)
    o = _opciones(opciones)
    m = _maquetar(texto, d, altura, **_de_composicion(o))
    n = len(m["texto"])
    paradas, linea_de = [(0.0, 0.0)] * (n + 1), [0] * (n + 1)
    w, y_sum, dy = m["ancho_bloque"], m["y_sup"] + m["y_inf"], o["desfase_base"]
    for k, ln in enumerate(m["lineas"]):
        for j, x in enumerate(ln["xs"] + [ln["ancho"]]):
            x, y = ln["x"] + x, ln["y"]
            paradas[ln["ini"] + j] = ((w - x) if o["voltear_h"] else x, ((y_sum - y) if o["voltear_v"] else y) + dy)
            linea_de[ln["ini"] + j] = k
    abajo, arriba, sesgo = m["desc"], m["asc"], m["sesgo"]
    if o["voltear_v"]:
        abajo, arriba, sesgo = -arriba, -abajo, -sesgo
    if o["voltear_h"]:
        sesgo = -sesgo
    return {"paradas": paradas, "linea_de": linea_de, "lineas": [(ln["ini"], ln["fin"]) for ln in m["lineas"]],
            "abajo": abajo, "arriba": arriba, "sesgo": sesgo}


# ---------------------------------------------------------------- texto sobre un camino
LADOS = ("izq", "der")


def _glifos_linea(texto, d, altura, espaciado, o):
    """([(x, avance, prims, índice)], ancho, xs, avances, maqueta) de una sola línea (los saltos pasan a espacios)."""
    linea = str(texto).replace("\r", "").replace("\n", " ")
    base = {k: v for k, v in _de_composicion(o).items() if k not in ("espaciado", "ancho_caja", "sin_division",
                                                                    "interlineado", "alineacion", "ancla_v")}
    m = _maquetar(linea, d, altura, espaciado=espaciado, **base)
    ln = m["lineas"][0]
    salida, avances = [], []
    for j in range(ln["fin"] - ln["ini"]):
        i = ln["ini"] + j
        avances.append(m["avance"](i))
        if m["texto"][i].isspace():
            continue
        prims, f = [], m["f_"](i)
        try:
            d["gs"][m["gl"][i]].draw(_lapiz(d["gs"], 0.0, 0.0, m["sx"] * f, m["sy"] * f, m["sesgo"], prims))
        except KeyError:
            pass
        if prims:
            salida.append((ln["xs"][j], avances[-1], prims, j))
    return salida, ln["ancho"], ln["xs"], avances, m


def glifos_de_linea(texto, fuente="Arial", altura=5.0, negrita=False, cursiva=False, espaciado=0.0, **opciones):
    """([(x, avance, prims)], ancho) de una línea: un elemento por carácter visible, con sus contornos en
    coordenadas propias (origen en la línea base, a la izquierda del glifo) y `x` su posición en la línea.
    Acepta las opciones de tipografía de `contornos_texto` (kerning, inclinacion, escala_h, escala_v,
    capitalizacion)."""
    d = _fuente_datos(fuente, negrita, cursiva)
    glifos, ancho, _xs, _av, _m = _glifos_linea(texto, d, altura, espaciado, _opciones(opciones))
    return [(x, avance, prims) for x, avance, prims, _j in glifos], ancho


def _texto_en_camino(texto, camino, fuente, altura, negrita, cursiva, espaciado, alineacion, posicion, lado,
                     desfase, ajustar, opciones):
    """Lo que comparten los contornos y el cursor de un texto en curva: (glifos, ancho, xs, avances, maqueta,
    inicio, extra, colocar) con `colocar(s)` = (bx, by, cos, sen) del punto a la distancia `s` del camino."""
    import numpy as np
    if lado not in LADOS:
        raise ErrorFuente(f"Lado desconocido: {lado} (izq, der).")
    if alineacion not in ALINEACIONES:
        raise ErrorFuente(f"Alineación desconocida: {alineacion} (izq, centro, der).")
    pts = np.asarray(camino, dtype=float)
    if pts.ndim != 2 or len(pts) < 2:
        raise ErrorFuente("El camino del texto necesita al menos dos puntos.")
    cerrado = len(pts) > 2 and bool(np.allclose(pts[0], pts[-1]))
    posicion = float(posicion)
    if lado == "der":
        pts, posicion = pts[::-1], 1.0 - posicion
    tramos = np.hypot(*np.diff(pts, axis=0).T)
    acum = np.concatenate([[0.0], np.cumsum(tramos)])
    largo = float(acum[-1])
    if largo < 1e-9:
        raise ErrorFuente("El camino del texto no tiene largo.")
    d = _fuente_datos(fuente, negrita, cursiva)
    glifos, ancho, xs, avances, m = _glifos_linea(texto, d, altura, espaciado, _opciones(opciones))
    validos = tramos > 1e-12
    d_ini = np.diff(pts, axis=0)[validos][0] / tramos[validos][0]
    d_fin = np.diff(pts, axis=0)[validos][-1] / tramos[validos][-1]

    def punto(sv):
        if cerrado:
            sv %= largo
        elif sv < 0:
            return pts[0] + d_ini * sv
        elif sv > largo:
            return pts[-1] + d_fin * (sv - largo)
        return np.array([np.interp(sv, acum, pts[:, 0]), np.interp(sv, acum, pts[:, 1])])

    h = max(largo * 1e-3, float(altura) * 0.05)
    extra = 0.0
    if ajustar:                    # la primera letra arranca en la punta, la última termina en la otra
        inicio = 0.0
        if len(glifos) > 1:
            extra = (largo - ancho) / (len(glifos) - 1)
        else:
            inicio = (largo - ancho) / 2
    else:
        inicio = posicion * largo - {"izq": 0.0, "centro": ancho / 2, "der": ancho}[alineacion]

    def colocar(sc):
        p = punto(sc)
        t = punto(sc + h) - punto(sc - h)
        nt = float(np.hypot(*t))
        c, s = (t / nt) if nt > 1e-12 else (1.0, 0.0)
        return p[0] - s * desfase, p[1] + c * desfase, c, s         # la normal izquierda es (-s, c)
    return glifos, ancho, xs, avances, m, inicio, extra, colocar


def contornos_en_camino(texto, camino, fuente="Arial", altura=5.0, negrita=False, cursiva=False, *, espaciado=0.0,
                        alineacion="centro", posicion=0.5, lado="izq", desfase=0.0, ajustar=False, **opciones):
    """Texto sobre un camino (Fusion: Texto en trayectoria), con las letras rígidas y perpendiculares a la curva.

    camino: polilínea densa [(x, y)…] que sigue la curva (cerrada si el último punto es el primero). Las letras
    quedan del lado izquierdo del sentido de recorrido; lado "der" recorre al revés (las letras pasan al otro lado
    y se siguen leyendo derechas). posicion: fracción 0-1 del largo, medida en el sentido ORIGINAL del camino,
    donde va el ancla del texto; alineacion: qué parte del texto cae ahí (izq, centro, der). desfase: mm entre la
    curva y la línea base (positivo = hacia el lado de las letras). ajustar: reparte el texto en todo el largo
    (ignora posición y alineación). En un camino cerrado el texto da la vuelta; en uno abierto sigue recto más
    allá de las puntas. Varias líneas se juntan en una. `opciones`: kerning, inclinacion, escala_h, escala_v y
    capitalizacion (como en `contornos_texto`); el subrayado y el tachado no se aplican en curva."""
    glifos, ancho, _xs, _av, _m, inicio, extra, colocar = _texto_en_camino(
        texto, camino, fuente, altura, negrita, cursiva, espaciado, alineacion, posicion, lado, desfase, ajustar,
        opciones)
    if not glifos:
        return []
    salida = []
    for i, (x, avance, prims, _j) in enumerate(glifos):
        bx, by, c, s = colocar(inicio + x + avance / 2 + i * extra)
        medio = avance / 2

        def T(q, bx=bx, by=by, c=c, s=s, medio=medio):
            lx, ly = q[0] - medio, q[1]
            return (float(bx + c * lx - s * ly), float(by + s * lx + c * ly))
        for pr in prims:
            if pr[0] == "linea":
                salida.append(("linea", None, T(pr[2]), T(pr[3])))
            else:
                salida.append(("spline", None, tuple(T(q) for q in pr[2]), pr[3], pr[4], pr[5]))
    return salida


def paradas_en_camino(texto, camino, fuente="Arial", altura=5.0, negrita=False, cursiva=False, *, espaciado=0.0,
                      alineacion="centro", posicion=0.5, lado="izq", desfase=0.0, ajustar=False, **opciones):
    """Cursor de un texto en curva: n + 1 segmentos ((x, y) de abajo, (x, y) de arriba), uno por posición del
    texto (la i es el borde izquierdo del carácter i; la n, el final). Mismas opciones que `contornos_en_camino`."""
    glifos, ancho, xs, avances, m, inicio, extra, colocar = _texto_en_camino(
        texto, camino, fuente, altura, negrita, cursiva, espaciado, alineacion, posicion, lado, desfase, ajustar,
        opciones)
    visibles = [g[3] for g in glifos]
    n, salida = len(xs), []
    for c in range(n + 1):
        x, av = (xs[c], avances[c]) if c < n else (ancho, 0.0)
        antes = sum(1 for j in visibles if j < c)
        bx, by, co, sn = colocar(inicio + x + av / 2 + min(antes, max(len(glifos) - 1, 0)) * extra)
        punta = []
        for ly in (m["desc"], m["asc"]):
            lx = -av / 2 + m["sesgo"] * ly
            punta.append((float(bx + co * lx - sn * ly), float(by + sn * lx + co * ly)))
        salida.append(tuple(punta))
    return salida
