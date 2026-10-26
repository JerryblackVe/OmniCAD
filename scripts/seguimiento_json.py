"""Datos de la página «Seguimiento OmniCAD» (Artifact de claude.ai).

Lee docs/seguimiento/{bugs,faltantes,mejoras}.md y la sección «Registro» de PROJECT_LOG.md y escribe, en la
carpeta que se pase (por defecto, la actual), `seguimiento.json` (una fila por pendiente) y `resueltos.json` (las
últimas 25 entradas del Registro). Cómo subirlos a la página: sección «Página de seguimiento» de CLAUDE.md.

Uso: python scripts/seguimiento_json.py [carpeta_de_salida]
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TIPOS = {"bugs.md": "Bug", "faltantes.md": "Faltante", "mejoras.md": "Mejora"}
RENOMBRES = {"Abiertos y parciales": "Bugs generales", "Pendientes generales": "Generales",
             "Hallazgos de pruebas de uso": "Pruebas de uso"}
MAX_RESUELTOS = 25


def limpiar(texto):
    return re.sub(r"\s+", " ", re.sub(r"\*\*|`", "", texto)).strip()


def tema(seccion):
    """Nombre de la sección sin el paréntesis con la fecha de la auditoría."""
    nombre = re.sub(r"\s*\(.*$", "", seccion).strip()
    return RENOMBRES.get(nombre, nombre or "Generales")


def pendientes():
    filas = []
    for archivo, tipo in TIPOS.items():
        seccion = ""
        for linea in (RAIZ / "docs" / "seguimiento" / archivo).read_text(encoding="utf-8").splitlines():
            if linea.startswith("#"):
                seccion = limpiar(linea.lstrip("# "))
            if not linea.startswith("|"):
                continue
            c = [x.strip() for x in linea.strip().strip("|").split("|")]
            if len(c) < 7 or c[0] == "ID" or set(c[0]) <= set("-: "):
                continue
            filas.append({"id": c[0], "tipo": tipo, "area": tema(seccion), "seccion": seccion, "que": limpiar(c[1]),
                          "estado": c[2], "dificultad": c[3], "queda": limpiar(c[4])[:400], "verificado": c[6]})
    return filas


def resueltos():
    salida, en_registro = [], False
    for linea in (RAIZ / "PROJECT_LOG.md").read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            en_registro = linea.strip() == "## Registro"
            continue
        m = re.match(r"- \*\*(\d{4}-\d{2}-\d{2}) · (.+?)\.?\*\*", linea) if en_registro else None
        if m and len(salida) < MAX_RESUELTOS:
            salida.append({"fecha": m.group(1), "titulo": limpiar(m.group(2))[:140]})
    return salida


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    filas, hechos = pendientes(), resueltos()
    (carpeta / "seguimiento.json").write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
    (carpeta / "resueltos.json").write_text(json.dumps(hechos, ensure_ascii=False), encoding="utf-8")
    print(f"{len(filas)} pendientes ({dict(Counter(f['tipo'] for f in filas))}), {len(hechos)} resueltos")
