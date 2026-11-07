"""Ranking de tests y archivos lentos a partir de los JUnit XML que deja el cierre.

Lee todos los `*.xml` de la carpeta (los que escribe pytest con `--junitxml`, sueltos o envueltos en
`testsuites`) y escribe en `--salida` un JSON con los segundos de cada test («archivo::nombre»), la suma por
archivo, el total y los XML leídos; además imprime los 30 tests y los 20 archivos más lentos. Paquete A de
docs/plan_velocidad.md; lo llama scripts/cierre_completo.sh. Los segundos son el `time` de JUnit (preparación,
llamada y cierre del test): sin colección ni arranque del intérprete, así que el total queda por debajo del `pytest -q`.

Uso: python scripts/tiempos.py <carpeta_con_xml> [--salida evidencias/tiempos.json]
Tandas: python scripts/tiempos.py <lista.txt> --tandas <carpeta> [--mediciones tiempos.json] [--procesos 4]
"""
import argparse
import json
import math
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


# Sin medición se estima prudente, igual que scripts/tests_afectados.py (P-66).
SEGUNDOS_SIN_MEDIR = 30


def repartir(archivos, tiempos, procesos=4):
    """Arma tandas de unos 600 s por proceso, con archivos enteros y los más lentos primero; sin dato, 30 s."""
    if procesos < 1:
        raise ValueError("La cantidad de procesos debe ser positiva")
    grupos, grupo, cargas = [], [], [0.0] * procesos
    for archivo in sorted(archivos, key=lambda a: -float(tiempos.get(a, SEGUNDOS_SIN_MEDIR))):
        segundos = float(tiempos.get(archivo, SEGUNDOS_SIN_MEDIR))
        if not math.isfinite(segundos) or segundos < 0:
            raise ValueError(f"Tiempo inválido para {archivo}: {segundos}")
        trabajador = min(range(procesos), key=cargas.__getitem__)
        if grupo and cargas[trabajador] + segundos > 600:
            grupos.append(grupo)
            grupo, cargas, trabajador = [], [0.0] * procesos, 0
        grupo.append(archivo)
        cargas[trabajador] += segundos
        if segundos > 600:
            print(f"Aviso: {archivo} tarda {segundos:.1f} s; va solo y no se puede dividir por archivo.")
            grupos.append(grupo)
            grupo, cargas = [], [0.0] * procesos
    if grupo:
        grupos.append(grupo)
    return grupos


def main():
    ap = argparse.ArgumentParser(description="Ranking de tests lentos desde los JUnit XML del cierre.")
    ap.add_argument("carpeta", type=Path, help="carpeta con los *.xml; con --tandas, lista de archivos de test")
    ap.add_argument("--salida", type=Path, default=RAIZ / "evidencias" / "tiempos.json",
                    help="JSON de salida (por defecto evidencias/tiempos.json en la raíz del repo)")
    ap.add_argument("--tandas", type=Path, help="escribir parte_00, parte_01… en esta carpeta en vez del ranking")
    ap.add_argument("--mediciones", type=Path, default=RAIZ / "evidencias" / "tiempos.json",
                    help="JSON de tiempos por archivo para repartir las tandas")
    ap.add_argument("--procesos", type=int, default=4, help="procesos por tanda (1 para serie)")
    args = ap.parse_args()
    if args.tandas is not None:
        tiempos = json.loads(args.mediciones.read_text(encoding="utf-8"))["archivos"]
        grupos = repartir(args.carpeta.read_text(encoding="utf-8").splitlines(), tiempos, args.procesos)
        args.tandas.mkdir(parents=True, exist_ok=True)
        for i, grupo in enumerate(grupos):
            (args.tandas / f"parte_{i:02d}").write_text("\n".join(grupo) + "\n", encoding="utf-8", newline="")
        print(f"{len(grupos)} tandas, {args.procesos} procesos, objetivo 600 s por tanda")
        return
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
