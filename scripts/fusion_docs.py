# -*- coding: utf-8 -*-
"""
Busca en la ayuda oficial de Fusion guardada en docs/fusion_docs/ (no está en git; ver LEEME.txt de esa carpeta).

  fusion_docs.py construir                       arma el índice de texto (_indice.db) y docs/fusion_docs/indice/<carpeta>.md
  fusion_docs.py buscar <palabras> [-s carpeta] [-n 12]
                                                 artículos que nombran TODAS las palabras (prefijos valen); el título pesa más
  fusion_docs.py ver <nombre o ruta> [-s carpeta] [--corto]   texto limpio del artículo y rutas absolutas de sus imágenes (para Read)
  fusion_docs.py mapa                            qué carpeta de la ayuda corresponde a cada parte de la app
  fusion_docs.py probar                          autocomprobación

Se corre con el Python del venv: clon/.venv/Scripts/python.exe scripts/fusion_docs.py ...
El árbol oficial (libro › capítulo › artículo) sale de analisis/fusion_doc/toctree.json; sin él, el índice sigue andando
pero sin "miga" de pan.
"""
import argparse
import csv
import json
import re
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs" / "fusion_docs"
TOC = RAIZ / "analisis" / "fusion_doc" / "toctree.json"
DB = DOCS / "_indice.db"
INDICE = DOCS / "indice"

# Carpeta de contenido/ → parte de Fusion y de OmniCAD. Es la tabla del CLAUDE.md: si cambia una, cambia la otra.
MAPA = {
    "fusion-sketch": "DISEÑO › Boceto (y paleta, restricciones, cotas, proyectar)",
    "fusion-model": "DISEÑO › SÓLIDO, y también Plástico (reglas), Construir, Inspeccionar, Insertar, Seleccionar, "
                    "Modificar (mover, parámetros, materiales), Fabricar",
    "fusion-patch": "DISEÑO › SUPERFICIE (se llama «Patch», no «Surface»)",
    "fusion-mesh": "DISEÑO › MALLA",
    "fusion-sculpt": "DISEÑO › FORMA (T-Splines)",
    "fusion-sheet-metal": "DISEÑO › CHAPA",
    "fusion-assemble": "Ensamblar: componentes, uniones, contactos, estudios de movimiento",
    "fusion-configurations": "Configuraciones (tablas, reglas, temas)",
    "fusion-designs": "Diseños: navegador, línea de tiempo y modo, versiones, lista de materiales, PMI",
    "fusion-drawing": "Espacio DIBUJO (planos 2D)",
    "fusion-render": "Espacio RENDERIZAR",
    "fusion-animate": "Espacio ANIMACIÓN",
    "fusion-simulate": "Espacio SIMULACIÓN",
    "fusion-cam": "Espacio FABRICACIÓN (CAM)",
    "fusion-ecad": "Espacio ELECTRÓNICA",
    "fusion-generativedesign": "Espacio DISEÑO GENERATIVO",
    "fusion-getstarted": "Interfaz, atajos, preferencias, primeros pasos",
    "fusion-manage": "No es del CAD: Fusion Manage (ciclo de vida del producto)",
    "fusion-import": "No es del CAD: hubs, proyectos, carpetas y miembros",
    "fusion-extensions": "No es del CAD: extensiones y planes",
    "fusion-cloudcredits": "No es del CAD: tokens de la nube",
    "fusion-autodesk-assistant": "No es del CAD: Autodesk Assistant",
    "fusion-mcp": "El MCP de Fusion",
    "fusion-releasenotes": "Novedades por año",
    "fusion-visor": "DUPLICADO: repite casi todo lo demás. Se ignora (el índice solo guarda sus pocos títulos propios)",
}


def _salida_utf8():
    sys.stdout.reconfigure(encoding="utf-8")


def _salir(mensaje):
    print(mensaje)      # por stdout: stderr de Windows rompe los acentos
    sys.exit(1)


def _clave(ruta_o_url):
    """'.../ENU/Fusion-Patch/files/SFC-EXTRUDE.htm' → 'fusion-patch/files/sfc-extrude.htm' (une toctree y fuentes.csv)."""
    return ruta_o_url.lower().split("/enu/")[-1]


def limpiar(md, base):
    """Quita la cabecera de «Share», deja los enlaces como texto y devuelve (texto, [rutas absolutas de imágenes])."""
    corte = md.find("* LinkedIn")
    if corte >= 0:
        md = md[corte + len("* LinkedIn"):]
    imagenes = []

    def imagen(m):
        if not m.group(2).startswith("http"):      # 24 artículos enlazan imágenes de la web: no hay archivo que abrir
            imagenes.append((base / m.group(2)).resolve())
        return f"[imagen: {m.group(1) or Path(m.group(2)).name}]"

    md = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", imagen, md)
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)
    return re.sub(r"\n{3,}", "\n\n", md).strip(), imagenes


def _arbol():
    """{clave: (libro, [capítulos], profundidad)} y, por carpeta, la lista ordenada de (profundidad, título, clave|None)."""
    if not TOC.is_file():
        return {}, {}
    libros = json.loads(TOC.read_text(encoding="utf-8"))["books"]
    miga, orden = {}, {}

    def rec(n, libro, camino):
        clave = _clave(n["ln"]) if n.get("ln") else None
        if clave:
            miga[clave] = (libro["ttl"], camino)
        orden.setdefault(libro["id"], []).append((len(camino), n["ttl"], clave))
        for h in n.get("children", []):
            rec(h, libro, camino + [n["ttl"]])

    for libro in libros:
        for cap in libro.get("children", []):
            rec(cap, {"ttl": libro["ttl"], "id": libro["id"]}, [])
    return miga, orden


def construir():
    filas = list(csv.reader((DOCS / "fuentes.csv").open(encoding="utf-8-sig")))[1:]
    total = len(filas)
    titulos_otros = {f[1] for f in filas if f[0] != "Fusion-Visor"}
    filas = [f for f in filas if f[0] != "Fusion-Visor" or f[1] not in titulos_otros]
    miga, orden = _arbol()
    nuevo = DB.with_suffix(".db.tmp")      # se arma aparte: un corte a mitad no deja un índice vacío que parezca bueno
    nuevo.unlink(missing_ok=True)
    con = sqlite3.connect(nuevo)
    con.execute("CREATE VIRTUAL TABLE a USING fts5(titulo, miga, cuerpo, carpeta UNINDEXED, md UNINDEXED, "
                "tokenize='unicode61 remove_diacritics 2')")
    por_clave = {}
    for seccion, titulo, url, _, md in filas:
        ruta = DOCS / md
        texto, _ = limpiar(ruta.read_text(encoding="utf-8", errors="replace"), ruta.parent)
        libro, camino = miga.get(_clave(url), ("", []))
        carpeta = md.split("/")[1]
        con.execute("INSERT INTO a VALUES (?,?,?,?,?)", (titulo, " › ".join([libro, *camino]) if libro else "", texto,
                                                         carpeta, md))
        por_clave[_clave(url)] = (carpeta, titulo, Path(md).name)
    con.commit()
    con.close()
    nuevo.replace(DB)
    INDICE.mkdir(exist_ok=True)
    colocados = set()
    for carpeta in sorted({v[0] for v in por_clave.values()}):
        lineas = []
        for libro_id, nodos in orden.items():
            if libro_id.lower().replace("_id", "") != carpeta:
                continue
            for prof, ttl, clave in nodos:
                if clave in por_clave and por_clave[clave][0] == carpeta:
                    lineas.append(f"{'  ' * prof}- {ttl} — {por_clave[clave][2]}")
                    colocados.add(clave)
                else:
                    lineas.append(f"{'  ' * prof}- {ttl}")
        sueltos = [f"- {v[1]} — {v[2]}" for k, v in por_clave.items() if v[0] == carpeta and k not in colocados]
        if sueltos:
            lineas += ["", "## Fuera del árbol oficial", *sueltos]
        cab = (f"# {carpeta} — {MAPA.get(carpeta, '')}\n\nArtículos en `{DOCS / 'contenido' / carpeta}`. "
               f"Leer con Read o con `scripts/fusion_docs.py ver <nombre>`.\n\n")
        (INDICE / f"{carpeta}.md").write_text(cab + "\n".join(lineas) + "\n", encoding="utf-8")
    print(f"{len(por_clave)} artículos indexados ({total - len(por_clave)} repetidos de Fusion-Visor omitidos); "
          f"índices por carpeta en {INDICE}")


def consultar(palabras, carpeta=None, n=12):
    palabras = [p.replace('"', "") for p in palabras if p.replace('"', "").strip()]
    if not palabras:
        return []
    consulta = " ".join(f'"{p}"*' for p in palabras)
    sql = ("SELECT titulo, miga, md, snippet(a, 2, '«', '»', '…', 14) FROM a WHERE a MATCH ?"
           + (" AND carpeta = ?" if carpeta else "") + " ORDER BY bm25(a, 10.0, 3.0, 1.0, 0, 0) LIMIT ?")
    args = (consulta, *([carpeta] if carpeta else []), n)
    return sqlite3.connect(DB).execute(sql, args).fetchall()


def buscar(palabras, carpeta, n):
    filas = consultar(palabras, carpeta, n)
    for i, (titulo, miga, md, trozo) in enumerate(filas, 1):
        print(f"{i}. {titulo}\n   {miga}\n   {md}\n   {' '.join(trozo.split())}")
    if not filas:
        print("Sin resultados: probá menos palabras o el singular (el índice solo entiende prefijos).")


def ver(nombre, corto, carpeta=None):
    ruta = DOCS / nombre
    if not ruta.is_file():
        like = f"%{nombre.lower()}%"
        filas = sqlite3.connect(DB).execute(
            "SELECT titulo, md FROM a WHERE (lower(titulo) = ? OR lower(md) LIKE ? OR lower(titulo) LIKE ?)"
            + (" AND carpeta = ?" if carpeta else "") + " ORDER BY lower(titulo) = ? DESC, length(titulo) LIMIT 8",
            (nombre.lower(), like, like, *([carpeta] if carpeta else []), nombre.lower())).fetchall()
        if not filas:
            _salir("No hay ningún artículo con ese nombre; usá buscar.")
        iguales = [f for f in filas if f[0].lower() == nombre.lower()]
        if len(filas) > 1 and len(iguales) != 1:    # sin título exacto único: que elija (usar -s carpeta)
            _salir("Varios artículos, elegí uno:\n" + "\n".join(f"  {t} → {m}" for t, m in filas))
        ruta = DOCS / filas[0][1]
    texto, imagenes = limpiar(ruta.read_text(encoding="utf-8", errors="replace"), ruta.parent)
    print(f"# {ruta}\n\n{texto}")
    if imagenes and not corto:
        print("\nImágenes (abrir con Read):\n" + "\n".join(f"  {i}" for i in dict.fromkeys(imagenes)))


def mapa():
    for carpeta, que in MAPA.items():
        print(f"{carpeta:26} {que}")


def probar():
    carpetas = {p.name for p in (DOCS / "contenido").iterdir() if p.is_dir()}
    assert carpetas <= set(MAPA), f"carpetas sin explicar en MAPA: {carpetas - set(MAPA)}"
    assert any("extrude-a-surface-body" in md for _, _, md, _ in consultar(["extrude", "surface"], n=3))
    assert consultar(["stitch"], "fusion-patch"), "stitch tiene que estar en fusion-patch"
    texto, _ = limpiar((DOCS / "contenido/fusion-patch/stitch-surface-bodies-cccd32b3eac.md").read_text(encoding="utf-8"),
                       DOCS / "contenido/fusion-patch")
    assert "Share" not in texto[:40] and texto.startswith("# Stitch surface bodies")
    print("fusion_docs: ok")


def main():
    _salida_utf8()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("construir")
    b = s.add_parser("buscar")
    b.add_argument("palabras", nargs="+")
    b.add_argument("-s", "--carpeta")
    b.add_argument("-n", type=int, default=12)
    v = s.add_parser("ver")
    v.add_argument("nombre")
    v.add_argument("-s", "--carpeta")
    v.add_argument("--corto", action="store_true", help="sin la lista de imágenes")
    s.add_parser("mapa")
    s.add_parser("probar")
    a = p.parse_args()
    if a.cmd != "construir" and a.cmd != "mapa" and not DB.is_file():
        _salir("Falta el índice: correr primero `fusion_docs.py construir`.")
    {"construir": construir, "mapa": mapa, "probar": probar,
     "buscar": lambda: buscar(a.palabras, a.carpeta, a.n), "ver": lambda: ver(a.nombre, a.corto, a.carpeta)}[a.cmd]()


if __name__ == "__main__":
    main()
