# -*- coding: utf-8 -*-
"""Genera clon/omnicad/nucleo/tablas_rosca.py: las tablas de rosca de OmniCAD en formato propio.

Lee las medidas de los XML de la instalación de Fusion (solo lectura; los XML no se copian al repo) y
escribe una fila por designación: (tamaño, designación, paso, Ø mayor, Ø flancos, Ø menor, broca) en mm. Las familias que
OmniCAD ya tenía (solidos_crear.py) conservan sus filas: de esas solo se agregan los tamaños y pasos que faltan.

Uso, desde la raíz del repo: clon/.venv/Scripts/python.exe scripts/generar_tablas_rosca.py
OMNICAD_FUSION_CONFIG permite indicar la carpeta Configuration que contiene ThreadData/ y TaperThreadData/;
sin esa variable se usa la instalación de D:\\Autodesk. Ejemplo en Linux:
OMNICAD_FUSION_CONFIG=/ruta/Configuration clon/.venv/bin/python scripts/generar_tablas_rosca.py
"""
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = Path(os.environ.get("OMNICAD_FUSION_CONFIG",
                            r"D:\Autodesk\webdeploy\production\9c5312dfff2e4569cd1d269973ddf11cb999f782\Fusion\Server\Fusion\Configuration"))
SALIDA = RAIZ / "clon" / "omnicad" / "nucleo" / "tablas_rosca.py"
H60 = math.sqrt(3) / 2

# clave de familia: (carpeta, archivo, nombre en Fusion, prefijo de la designación, norma)
NUEVAS = {
    "ansi_metrica": ("ThreadData", "ANSIMetricMProfile", "Perfil en M métrico ANSI", "ANSI ", "ASME B1.13M"),
    "gb_metrica": ("ThreadData", "GBMetricprofile", "Perfil métrico GB", "GB ", "GB/T 193"),
    "gost_autorroscante": ("ThreadData", "GOSTSelf-tappingScrewThread", "Rosca de tornillo autorroscante GOST", "GOST ", "GOST"),
    "din_madera": ("ThreadData", "DINWoodScrewThread", "Rosca de tornillo para madera DIN", "DIN ", "DIN 7998"),
    "pulgadas_autorroscante": ("ThreadData", "InchTappingThreads", "Roscas autorroscantes en pulgadas", "AB ", "ASME B18.6.4"),
    "pulgadas_plasticos": ("ThreadData", "InchTappingThreadsForPlastics", "Roscas autorroscantes en pulgadas para plásticos",
                           "Plástico ", "ASME B18.6.4 (plásticos)"),
    "metrica_plasticos": ("ThreadData", "MetricTappingThreadsForPlastics", "Roscas autorroscantes métricas para plásticos",
                          "Plástico ", "DIN 7500 (plásticos)"),
    "din_tuberia": ("ThreadData", "DINPipeThreads", "Roscas de tubería DIN", "DIN ", "DIN EN ISO 228"),
    "gb_tuberia": ("ThreadData", "GBPipeThreadswithoutseal", "Roscas de tubería GB", "GB ", "GB/T 7307"),
    "iso_tuberia": ("ThreadData", "ISOPipeThreads", "Roscas de tubería ISO", "ISO ", "ISO 228-1"),
    "jis_tuberia": ("ThreadData", "JISPipeThreads", "Roscas de tubería JIS", "JIS ", "JIS B 0202"),
    "metrica_formado": ("ThreadData", "MetricFormingScrewThreads", "Roscas métricas de tornillo", "Formado ", "DIN 7500"),
    "afbma": ("ThreadData", "AFBMAStandardLocknuts", "Tuercas de bloqueo estándar AFBMA", "AFBMA ", "AFBMA Standard 8.2"),
}
CONICAS = {
    "din_conica": ("DIN_Pipe_Taper_Internal", "Rosca cónica de tubería DIN", "DIN ", "DIN EN 10226"),
    "iso_conica": ("ISO_Taper_Internal", "Rosca cónica de tubería ISO", "ISO ", "ISO 7-1"),
    "jis_conica": ("JIS_Taper_Internal", "Rosca cónica de tubería JIS", "JIS ", "JIS B 0203"),
    "npt_pvc": ("NPTforPVCPipeAndFitting", "NPT para PVC", "PVC ", "ASTM D2466"),
}


def _n(texto):
    return float(texto) if texto not in (None, "") else None


def _hilo(t):
    return {k: _n(t.findtext(c)) for k, c in (("mayor", "MajorDia"), ("flancos", "PitchDia"), ("menor", "MinorDia"), ("broca", "TapDrill"))}


def _medidas(d):
    """Hilo exterior e interior de una designación ({}, si no tiene)."""
    ext, inte = {}, {}
    for t in d.findall("Thread"):
        if t.findtext("Gender") == "external" and not ext:
            ext = _hilo(t)
        elif t.findtext("Gender") == "internal" and not inte:
            inte = _hilo(t)
    return ext, inte


def _paso_mm(d, unidad):
    if d.findtext("Pitch"):
        p = float(d.findtext("Pitch"))
        return p * 25.4 if unidad == "in" else p
    return 25.4 / float(d.findtext("TPI"))


def _fila_medida(tam, nombre, d, unidad):
    """Fila con las medidas del XML: el Ø mayor del hilo exterior; flancos y menor del interior, si lo hay."""
    k = 25.4 if unidad == "in" else 1.0
    ext, inte = _medidas(d)
    mayor = ext.get("mayor") or inte.get("mayor")
    flancos = inte.get("flancos") or ext.get("flancos")
    menor = inte.get("menor") or ext.get("menor")
    if not all((mayor, flancos, menor)) or not menor < flancos < mayor:
        return None
    broca = inte.get("broca")
    return (tam, nombre, round(_paso_mm(d, unidad), 5), round(mayor * k, 4), round(flancos * k, 4), round(menor * k, 4),
            round(broca * k, 4) if broca else None)


def _tamano_texto(s, unidad):
    s = (s or "").strip()
    try:
        return f"{float(s):g} mm" if unidad == "mm" else f"{float(s):g} in"
    except ValueError:
        return f"{s} in" if unidad == "in" and "(" in s else s


def _raiz(carpeta, nombre):
    return ET.parse(CONFIG / carpeta / f"{nombre}.xml").getroot()


def _familia_nueva(carpeta, archivo, prefijo):
    r = _raiz(carpeta, archivo)
    unidad, filas, saltadas = r.findtext("Unit"), [], 0
    metrica_basica = archivo in ("ANSIMetricMProfile", "GBMetricprofile")
    for s in r.findall("ThreadSize"):
        tam = _tamano_texto(s.findtext("Size"), unidad)
        for d in s.findall("Designation"):
            nombre = prefijo + d.findtext("ThreadDesignation").strip().replace(" - ", "-")
            if metrica_basica:                  # perfil básico igual que la métrica ISO: las tablas traen la clase 6g/6H
                D, p = float(s.findtext("Size")), _paso_mm(d, unidad)
                _, inte = _medidas(d)
                filas.append((tam, nombre, round(p, 5), D, round(D - 2 * (3 / 8) * H60 * p, 4),
                              round(D - 2 * (5 / 8) * H60 * p, 4), inte.get("broca")))
                continue
            f = _fila_medida(tam, nombre, d, unidad)
            if f is None:
                saltadas += 1
                continue
            filas.append(f)
    return r, filas, saltadas


def _extras_iso():
    filas = []
    for s in _raiz("ThreadData", "ISOMetricprofile").findall("ThreadSize"):
        D = float(s.findtext("Size"))
        for d in s.findall("Designation"):
            p = _paso_mm(d, "mm")
            _, inte = _medidas(d)
            filas.append((f"M{D:g}", f"M{D:g}x{p:g}", p, D, round(D - 2 * (3 / 8) * H60 * p, 4),
                          round(D - 2 * (5 / 8) * H60 * p, 4), inte.get("broca")))
    return filas


def _extras_trapezoidal():
    filas = []
    for s in _raiz("ThreadData", "ISOMetricTrapezoidalThreads").findall("ThreadSize"):
        D = float(s.findtext("Size"))
        for d in s.findall("Designation"):
            p = _paso_mm(d, "mm")
            filas.append((f"Tr{D:g}", f"Tr{D:g}x{p:g}", p, D, D - p / 2, D - p, D - p))
    return filas


def _extras_unificada():
    filas = []
    for s in _raiz("ThreadData", "ANSIUnifiedScrewThreads").findall("ThreadSize"):
        texto = s.findtext("Size").strip()
        D = round(float(texto.split("(")[0]) * 25.4, 4)
        for d in s.findall("Designation"):
            nombre = d.findtext("ThreadDesignation").strip()
            m = re.fullmatch(r"(.+)-(\d+(?:\.\d+)?) (\S+)", nombre)
            if m is None:
                continue
            tam = m.group(1).replace(" ", "-")
            if "(#" in texto:
                tam = f"#{tam}"
            p = _paso_mm(d, "in")
            _, inte = _medidas(d)
            broca = round(inte["broca"] * 25.4, 3) if inte.get("broca") else None
            filas.append((tam, f"{tam}-{float(m.group(2)):g} {m.group(3)}", round(p, 5), D, round(D - 2 * (3 / 8) * H60 * p, 4),
                          round(D - 2 * (5 / 8) * H60 * p, 4), broca))
    return filas


def _extras_acme():
    filas = []
    for s in _raiz("ThreadData", "ACMEScrewThreads").findall("ThreadSize"):
        tam = s.findtext("Size").strip().replace(" ", "-")
        for d in s.findall("Designation"):
            f = _fila_medida(tam, f"{tam}-{float(d.findtext('TPI')):g} ACME", d, "in")
            if f is not None:
                filas.append(f)
    return filas


def _extras_bsp():
    filas = []
    for s in _raiz("ThreadData", "BSPPipeThreads").findall("ThreadSize"):
        tam = s.findtext("Size").strip().replace(" ", "-")
        for d in s.findall("Designation"):
            f = _fila_medida(tam, f"G{tam}", d, "mm")
            if f is not None:
                filas.append(f)
    return filas


def _conica(archivo, prefijo):
    """Filas de una cónica interior: Ø medidos en el plano de calibre (WMInternalDia y alto del filete)."""
    r = _raiz("TaperThreadData", archivo)
    unidad, filas = r.findtext("Unit"), []
    k = 25.4 if unidad == "in" else 1.0
    for s in r.findall("ThreadSize"):
        for d in s.findall("Designation"):
            t = d.find("Thread")
            menor, h = float(t.findtext("WMInternalDia")) * k, float(t.findtext("HeightOfThread")) * k
            nombre = d.findtext("ThreadDesignation").strip().replace(" - ", "-")
            tam = s.findtext("Size").strip().replace("Rc ", "").replace(" ", "-")
            nombre = re.sub(r"^(\d+) (\d+/\d+)", r"\1-\2", nombre) if "NPT" in nombre else re.sub(r"^Rc ", "Rc", nombre).replace(" ", "-")
            filas.append((tam, prefijo + nombre, round(_paso_mm(d, unidad), 5), round(menor + 2 * h, 4), round(menor + h, 4),
                          round(menor, 4), round(float(t.findtext("TapDrill")) * k, 4)))
    return filas


def _extras_cono(archivo, formato):
    """Tamaños de BSP y NPT que OmniCAD no tenía."""
    salida = []
    for tam, nombre, *resto in _conica(archivo, ""):
        salida.append((tam, formato(tam, nombre), *resto))
    return salida


# Clases de tolerancia (CAP-14): familias cuyos XML traen clases; las métricas M respaldan los tamaños y clases
# sin intervalos ISO 965-1 verificados. La unificada sigue con las fórmulas de ASME B1.1 (tolerancias.py).
CON_CLASES = {**{k: (v[0], v[1], v[3]) for k, v in NUEVAS.items()},
              "iso_metrica": ("ThreadData", "ISOMetricprofile", ""),
              "trapezoidal": ("ThreadData", "ISOMetricTrapezoidalThreads", ""),
              "acme": ("ThreadData", "ACMEScrewThreads", ""), "bsp_paralela": ("ThreadData", "BSPPipeThreads", "")}


def _nombre_clases(familia, prefijo, s, d):
    """La designación de la tabla (la misma que arman las funciones de arriba) para una designación del XML."""
    if familia == "trapezoidal":
        return f"Tr{float(s.findtext('Size')):g}x{_paso_mm(d, 'mm'):g}"
    if familia == "acme":
        return f"{s.findtext('Size').strip().replace(' ', '-')}-{float(d.findtext('TPI')):g} ACME"
    if familia == "bsp_paralela":
        return f"G{s.findtext('Size').strip().replace(' ', '-')}"
    return prefijo + d.findtext("ThreadDesignation").strip().replace(" - ", "-")


def _clases(familia, carpeta, archivo, prefijo):
    """({designación: {clase: (hilo interior, hilo exterior)}}, {clase: True si es solo interior, False si es solo
    exterior, None si vale para los dos}, (clase interior, clase exterior) por defecto de Fusion). Cada hilo es
    (Ø mayor, Ø flancos, Ø menor) en mm o None."""
    r = _raiz(carpeta, archivo)
    k = 25.4 if r.findtext("Unit") == "in" else 1.0
    tabla, genero, auto = {}, {}, {"internal": None, "external": None}
    for s in r.findall("ThreadSize"):
        for d in s.findall("Designation"):
            por_clase = {}
            for t in d.findall("Thread"):
                clase, lado = t.findtext("Class"), t.findtext("Gender")
                medidas = tuple(None if t.findtext(c) in (None, "") else round(float(t.findtext(c)) * k, 4)
                                for c in ("MajorDia", "PitchDia", "MinorDia"))
                if not clase or not all(medidas[:2]):
                    continue
                dos = por_clase.setdefault(clase, [None, None])
                dos[0 if lado == "internal" else 1] = medidas
                genero.setdefault(clase, set()).add(lado)
                auto[lado] = auto[lado] or clase
            if por_clase:
                tabla[_nombre_clases(familia, prefijo, s, d)] = {c: tuple(v) for c, v in por_clase.items()}
    disponibles = {c: (None if len(g) == 2 else g == {"internal"}) for c, g in genero.items()}
    return tabla, disponibles, (auto["internal"], auto["external"])


def main():
    familias, filas, saltadas = {}, {}, {}
    for clave, (carpeta, archivo, nombre, prefijo, norma) in NUEVAS.items():
        r, f, n = _familia_nueva(carpeta, archivo, prefijo)
        familias[clave] = {"nombre": nombre, "norma": norma, "angulo": float(r.findtext("Angle")), "conica": False,
                           "solo_exterior": r.findtext("ExternalOnly") == "yes"}
        filas[clave], saltadas[clave] = f, n
    for clave, (archivo, nombre, prefijo, norma) in CONICAS.items():
        familias[clave] = {"nombre": nombre, "norma": norma, "angulo": 60.0 if "PVC" in nombre else 55.0, "conica": True,
                           "solo_exterior": False}
        filas[clave] = _conica(archivo, prefijo)
    filas["iso_metrica"] = _extras_iso()
    filas["trapezoidal"] = _extras_trapezoidal()
    filas["unificada"] = _extras_unificada()
    filas["acme"] = _extras_acme()
    filas["bsp_paralela"] = _extras_bsp()
    filas["bsp_conica"] = _extras_cono("BSP_Taper_Internal", lambda t, _n: f"R{t}")
    filas["npt"] = _extras_cono("NPT", lambda _t, n: n)
    texto = ['# -*- coding: utf-8 -*-',
             '"""Tablas de rosca en formato propio. Generado por scripts/generar_tablas_rosca.py: no editar a mano.',
             'FILAS: familia → [(tamaño, designación, paso, Ø mayor, Ø flancos, Ø menor, broca)] en mm."""', '',
             f'FAMILIAS = {familias!r}', '', 'FILAS = {']
    for clave, lista in filas.items():
        texto.append(f'    {clave!r}: [')
        texto += [f'        {f!r},' for f in lista]
        texto.append('    ],')
    texto.append('}')
    clases, disponibles, auto = {}, {}, {}
    for clave, (carpeta, archivo, prefijo) in CON_CLASES.items():
        clases[clave], disponibles[clave], auto[clave] = _clases(clave, carpeta, archivo, prefijo)
    texto += ['', "# CLASES (CAP-14): familia → designación → clase → (hilo interior, hilo exterior), cada hilo (Ø mayor, Ø flancos,",
              "# Ø menor) en mm o None. CLASES_FAMILIA: familia → clase → True (solo interior), False (solo exterior) o None",
              "# (las dos). CLASE_FUSION: familia → (clase interior, clase exterior) que Fusion propone.",
              f'CLASES_FAMILIA = {disponibles!r}', f'CLASE_FUSION = {auto!r}', '', 'CLASES = {']
    for clave, tabla in clases.items():
        texto.append(f'    {clave!r}: {{')
        texto += [f'        {nombre!r}: {por_clase!r},' for nombre, por_clase in tabla.items()]
        texto.append('    },')
    texto.append('}')
    SALIDA.write_text("\n".join(texto) + "\n", encoding="utf-8")
    print(f"{SALIDA.name}: {sum(map(len, filas.values()))} filas, {len(familias)} familias nuevas, "
          f"{sum(map(len, clases.values()))} designaciones con clases")
    if any(saltadas.values()):
        print("Saltadas por datos incompletos:", {k: v for k, v in saltadas.items() if v})


if __name__ == "__main__":
    sys.exit(main())
