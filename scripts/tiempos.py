"""Ranking de tests y archivos lentos a partir de los JUnit XML que deja el cierre.

Lee todos los `*.xml` de la carpeta (los que escribe pytest con `--junitxml`, sueltos o envueltos en
`testsuites`) y escribe en `--salida` un JSON con los segundos de cada test («archivo::nombre»), la suma por
archivo, el total y los XML leídos; además imprime los 30 tests y los 20 archivos más lentos. Paquete A de
docs/plan_velocidad.md; lo llama scripts/cierre_completo.sh. Los segundos son el `time` de JUnit (preparación,
llamada y cierre del test): sin colección ni arranque del intérprete, así que el total queda por debajo del `pytest -q`.

Uso: python scripts/tiempos.py <carpeta_con_xml> [--salida evidencias/tiempos.json]
"""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent      # la raíz del repo: scripts/ es su hija
TOPE_TESTS, TOPE_ARCHIVOS = 30, 20


def leer(carpeta):
    """(segundos por test, segundos por archivo, nombres de los XML) de los JUnit de la carpeta."""
    fuentes = sorted(carpeta.glob("*.xml"))
    if not fuentes:
        raise SystemExit(f"{carpeta}: no hay ningún *.xml; pytest tiene que haber corrido con --junitxml ahí")
    tests, archivos = {}, {}
    for xml in fuentes:
        for caso in ET.parse(xml).getroot().iter("testcase"):
            # classname «tests.test_x» o «tests.test_x.TestClase» → tests/test_x.py (y la clase va en el id)
            partes = caso.get("classname", "").split(".")
            archivo = "/".join(partes[:2]) + ".py"
            segundos = float(caso.get("time", 0))
            tests["::".join([archivo, *partes[2:], caso.get("name")])] = segundos
            archivos[archivo] = archivos.get(archivo, 0) + segundos
    return tests, archivos, [x.name for x in fuentes]


def main():
    ap = argparse.ArgumentParser(description="Ranking de tests lentos desde los JUnit XML del cierre.")
    ap.add_argument("carpeta", type=Path, help="carpeta con los *.xml que dejó pytest --junitxml")
    ap.add_argument("--salida", type=Path, default=RAIZ / "evidencias" / "tiempos.json",
                    help="JSON de salida (por defecto evidencias/tiempos.json en la raíz del repo)")
    args = ap.parse_args()
    tests, archivos, fuentes = leer(args.carpeta)
    total = round(sum(tests.values()), 3)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps({"tests": tests, "archivos": archivos, "total": total, "fuentes": fuentes},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(tests)} tests, {len(archivos)} archivos, {total:.2f} s en total ({len(fuentes)} xml)")
    for titulo, valores, tope in (("tests", tests, TOPE_TESTS), ("archivos", archivos, TOPE_ARCHIVOS)):
        print(f"\nLos {tope} {titulo} más lentos:")
        for ident, segundos in sorted(valores.items(), key=lambda kv: -kv[1])[:tope]:
            print(f"{segundos:8.2f}  {ident}")


if __name__ == "__main__":
    main()
