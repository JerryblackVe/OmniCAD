"""Datos de la página «Seguimiento OmniCAD» (Artifact de claude.ai).

Lee docs/seguimiento/{bugs,faltantes,mejoras}.md y la sección «Registro» de PROJECT_LOG.md y escribe, en la
carpeta que se pase (por defecto, la actual), `seguimiento.json` (una fila por pendiente), `resueltos.json` (las
últimas 25 entradas del Registro) `prompts.json` (los prompts de la tabla «Prompts guardados» del README de
seguimiento) y `agenda.json` (las tareas programadas de docs/seguimiento/agenda.md). Cómo subirlos a la página: sección «Página de seguimiento» de CLAUDE.md.

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


def prompts():
    salida = []
    indice = (RAIZ / "docs" / "seguimiento" / "README.md").read_text(encoding="utf-8")
    for tema_doc, archivo in re.findall(r"^\| (.+?) \| \[(.+?)\]\(\.\./.+?\) \|$", indice, re.M):
        cuerpo = (RAIZ / "docs" / archivo).read_text(encoding="utf-8").partition("## Prompt para el agente")[2]
        texto = re.search(r"^```text\n(.*?)^```$", cuerpo, re.M | re.S)
        modelo = re.search(r"Modelo sugerido[^:]*: ([^.\n]+)", cuerpo)
        if not texto or not modelo:
            raise SystemExit(f"{archivo}: falta el prompt o su modelo sugerido")
        salida.append({"tema": tema_doc, "archivo": archivo, "modelo": modelo.group(1), "texto": texto.group(1).strip()})
    return salida


def agenda():
    """Filas de docs/seguimiento/agenda.md: tareas que Gerardo programa para una fecha."""
    filas = []
    for linea in (RAIZ / "docs" / "seguimiento" / "agenda.md").read_text(encoding="utf-8").splitlines():
        c = [x.strip() for x in linea.strip().strip("|").split("|")] if linea.startswith("|") else []
        if len(c) == 5 and c[0] != "ID" and not set(c[0]) <= set("-: "):
            filas.append({"id": c[0], "tarea": limpiar(c[1]), "cuando": c[2], "pedido": c[3], "estado": c[4]})
    # primero las que tienen fecha, de la más cercana a la más lejana; «A definir» al final
    return sorted(filas, key=lambda f: (not re.fullmatch(r"\d{4}-\d{2}-\d{2}", f["cuando"]), f["cuando"]))


if __name__ == "__main__":
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    filas, hechos, guardados, programadas = pendientes(), resueltos(), prompts(), agenda()
    (carpeta / "seguimiento.json").write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
    (carpeta / "resueltos.json").write_text(json.dumps(hechos, ensure_ascii=False), encoding="utf-8")
    (carpeta / "prompts.json").write_text(json.dumps(guardados, ensure_ascii=False), encoding="utf-8")
    (carpeta / "agenda.json").write_text(json.dumps(programadas, ensure_ascii=False), encoding="utf-8")
    print(f"{len(filas)} pendientes ({dict(Counter(f['tipo'] for f in filas))}), {len(hechos)} resueltos, "
          f"{len(guardados)} prompts, {len(programadas)} en agenda")
