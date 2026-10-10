# -*- coding: utf-8 -*-
"""
Fuentes tipográficas del texto de boceto, con fontTools (sin Qt).

Antes el texto dependía del administrador de fuentes de OpenCascade, que no ve las fuentes instaladas «solo
para el usuario» ni las variables. Acá se escanean todas (carpetas del sistema, del usuario, el registro de
Windows y las que se sumen), se guarda un catálogo en caché y los contornos salen directo de los glifos
(TrueType, OpenType/CFF, colecciones .ttc y variables), con espaciado entre letras, interlineado, caja con
ajuste de línea, alineación horizontal, anclaje vertical y volteo.

Limitación: no hay ligaduras ni formas contextuales (árabe, devanagari…): cada carácter es un glifo.
Equivale al texto de boceto de Fusion (SKT-CREATE-TEXT), con más opciones.
"""
import json
import os
import sys
from functools import lru_cache
from pathlib import Path

EXTENSIONES = (".ttf", ".otf", ".ttc", ".otc")
CARPETAS_EXTRA = []              # carpetas sumadas en tiempo de ejecución (agregar_carpeta)
ALINEACIONES = ("izq", "centro", "der")
ANCLAJES = ("base", "arriba", "medio", "abajo")
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
    _CATALOGO = salida
    return salida


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
    return {"f": f, "upem": upem, "cmap": f.getBestCmap() or {}, "hmtx": f["hmtx"], "gs": f.getGlyphSet(),
            "asc": asc, "desc": desc, "gap": gap, "kern": _tabla_kern(f)}


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


def _lapiz(gs, dx, dy, s, salida):
    from fontTools.pens.basePen import BasePen

    class Lapiz(BasePen):
        def __init__(self):
            super().__init__(gs)
            self.ini = self.act = None

        @staticmethod
        def _t(p):
            return (dx + p[0] * s, dy + p[1] * s)

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


def _ajustar_lineas(lineas, ancho_max, ancho_de):
    """Parte las líneas en palabras para que ninguna pase de `ancho_max` (una palabra más larga queda sola)."""
    if ancho_max <= 0:
        return lineas
    salida = []
    for linea in lineas:
        actual = ""
        for palabra in linea.split(" "):
            prueba = palabra if not actual else actual + " " + palabra
            if actual and ancho_de(prueba) > ancho_max:
                salida.append(actual)
                actual = palabra
            else:
                actual = prueba
        salida.append(actual)
    return salida


def contornos_texto(texto, fuente="Arial", altura=5.0, negrita=False, cursiva=False, *, espaciado=0.0,
                    interlineado=1.0, alineacion="izq", ancla_v="base", ancho_caja=0.0, voltear_h=False,
                    voltear_v=False):
    """Contornos de un texto como primitivas 2D ('linea' y 'spline' de Bézier, id None) con el origen en el
    ancla: la esquina izquierda de la caja y, en vertical, la línea base de la primera línea ("base"), su
    borde superior ("arriba"), el centro del bloque ("medio") o el borde inferior de la última ("abajo").
    `altura` es el tamaño de la fuente en mm; `espaciado`, mm extra entre letras; `interlineado`, factor sobre
    el salto de línea de la fuente; `ancho_caja` > 0 parte las líneas en palabras; `alineacion` izq/centro/der
    dentro de la caja. Levanta ErrorFuente si la fuente no existe."""
    reg = buscar_fuente(fuente, negrita, cursiva)
    if reg is None:
        raise ErrorFuente(f"No se encontró la fuente «{fuente}».")
    if alineacion not in ALINEACIONES:
        raise ErrorFuente(f"Alineación desconocida: {alineacion} (izq, centro, der).")
    if ancla_v not in ANCLAJES:
        raise ErrorFuente(f"Anclaje vertical desconocido: {ancla_v} (base, arriba, medio, abajo).")
    peso = (700 if negrita else 400) if "wght" in reg["ejes"] else 0
    d = _datos(reg["ruta"], reg["indice"], peso)
    s = float(altura) / d["upem"]
    cmap, hmtx, kern = d["cmap"], d["hmtx"], d["kern"]
    notdef = d["f"].getGlyphOrder()[0]

    def glifo(ch):
        return cmap.get(ord(ch), notdef)

    def avance(g):
        try:
            return hmtx[g][0]
        except KeyError:
            return 0

    def ancho_de(linea):
        w, previo = 0.0, None
        for ch in linea:
            g = glifo(ch)
            if previo is not None:
                w += (kern(previo, g) * s)
            w += avance(g) * s + espaciado
            previo = g
        return w - (espaciado if linea else 0.0)

    lineas = str(texto).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lineas = _ajustar_lineas(lineas, float(ancho_caja or 0.0), ancho_de)
    anchos = [ancho_de(ln) for ln in lineas]
    ancho_bloque = float(ancho_caja) if ancho_caja and ancho_caja > 0 else max(anchos + [0.0])
    paso = (d["asc"] - d["desc"] + d["gap"]) * s * float(interlineado)
    asc, desc = d["asc"] * s, d["desc"] * s
    # y de la línea base de la primera línea, según el anclaje
    n = len(lineas)
    alto = (n - 1) * paso + (asc - desc)
    y0 = {"base": 0.0, "arriba": -asc, "medio": -asc + alto / 2, "abajo": -asc + alto}[ancla_v]
    y_sup, y_inf = y0 + asc, y0 - (n - 1) * paso + desc          # bordes del bloque (para el volteo)
    salida = []
    for i, ln in enumerate(lineas):
        x = {"izq": 0.0, "centro": (ancho_bloque - anchos[i]) / 2, "der": ancho_bloque - anchos[i]}[alineacion]
        y = y0 - i * paso
        previo = None
        for ch in ln:
            g = glifo(ch)
            if previo is not None:
                x += kern(previo, g) * s
            if not ch.isspace():
                try:
                    d["gs"][g].draw(_lapiz(d["gs"], x, y, s, salida))
                except KeyError:
                    pass
            x += avance(g) * s + espaciado
            previo = g
    if voltear_h or voltear_v:
        def v(q):
            return ((ancho_bloque - q[0]) if voltear_h else q[0], (y_sup + y_inf - q[1]) if voltear_v else q[1])
        salida = [("linea", None, v(p[2]), v(p[3])) if p[0] == "linea"
                  else ("spline", None, tuple(v(q) for q in p[2]), p[3], p[4], p[5]) for p in salida]
    return salida


# ---------------------------------------------------------------- texto sobre un camino
LADOS = ("izq", "der")


def glifos_de_linea(texto, fuente="Arial", altura=5.0, negrita=False, cursiva=False, espaciado=0.0):
    """([(x, avance, prims)], ancho) de una línea: un elemento por carácter visible, con sus contornos en
    coordenadas propias (origen en la línea base, a la izquierda del glifo) y `x` su posición en la línea."""
    reg = buscar_fuente(fuente, negrita, cursiva)
    if reg is None:
        raise ErrorFuente(f"No se encontró la fuente «{fuente}».")
    peso = (700 if negrita else 400) if "wght" in reg["ejes"] else 0
    d = _datos(reg["ruta"], reg["indice"], peso)
    s = float(altura) / d["upem"]
    notdef = d["f"].getGlyphOrder()[0]
    x, previo, salida = 0.0, None, []
    for ch in str(texto):
        g = d["cmap"].get(ord(ch), notdef)
        if previo is not None:
            x += d["kern"](previo, g) * s
        try:
            avance = d["hmtx"][g][0] * s
        except KeyError:
            avance = 0.0
        if not ch.isspace():
            prims = []
            try:
                d["gs"][g].draw(_lapiz(d["gs"], 0.0, 0.0, s, prims))
            except KeyError:
                pass
            if prims:
                salida.append((x, avance, prims))
        x += avance + espaciado
        previo = g
    return salida, (x - espaciado if texto else 0.0)


def contornos_en_camino(texto, camino, fuente="Arial", altura=5.0, negrita=False, cursiva=False, *, espaciado=0.0,
                        alineacion="centro", posicion=0.5, lado="izq", desfase=0.0, ajustar=False):
    """Texto sobre un camino (Fusion: Texto en trayectoria), con las letras rígidas y perpendiculares a la curva.

    camino: polilínea densa [(x, y)…] que sigue la curva (cerrada si el último punto es el primero). Las letras
    quedan del lado izquierdo del sentido de recorrido; lado "der" recorre al revés (las letras pasan al otro lado
    y se siguen leyendo derechas). posicion: fracción 0-1 del largo, medida en el sentido ORIGINAL del camino,
    donde va el ancla del texto; alineacion: qué parte del texto cae ahí (izq, centro, der). desfase: mm entre la
    curva y la línea base (positivo = hacia el lado de las letras). ajustar: reparte el texto en todo el largo
    (ignora posición y alineación). En un camino cerrado el texto da la vuelta; en uno abierto sigue recto más
    allá de las puntas. Varias líneas se juntan en una."""
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
    linea = " ".join(ln for ln in str(texto).replace("\r", "").split("\n"))
    glifos, ancho = glifos_de_linea(linea, fuente, altura, negrita, cursiva, espaciado)
    if not glifos:
        return []
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
    salida = []
    for i, (x, avance, prims) in enumerate(glifos):
        sc = inicio + x + avance / 2 + i * extra
        p = punto(sc)
        t = punto(sc + h) - punto(sc - h)
        nt = float(np.hypot(*t))
        c, s = (t / nt) if nt > 1e-12 else (1.0, 0.0)
        bx, by = p[0] - s * desfase, p[1] + c * desfase          # la normal izquierda es (-s, c)
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
