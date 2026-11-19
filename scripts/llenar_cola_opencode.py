# -*- coding: utf-8 -*-
"""Llena la reserva de OpenCode sin modelo (regla 18; «Protocolo de OpenCode» en docs/coordinacion.md).
Uso: llenar_cola_opencode.py [--tope N] [--seco]. Fuentes en orden: a) comandos del boceto sin test ni prueba
(scripts/cobertura_boceto.py), b) filas abiertas de boceto sin tarea, c) caza de boceto (una por día).
No repite lo que ya está en la cola, la reserva, corriendo, hechos, descartadas o trabadas."""
import argparse, datetime, os, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
COLA = Path(os.environ.get("VIGIA_COLA", Path.home() / "coordinador/opencode_cola"))
BRIEFS = Path(os.environ.get("LLENAR_BRIEFS", Path.home() / "coordinador/e9prompts/auto"))
PY = os.environ.get("VIGIA_PY", str(Path.home() / "OmniCAD/clon/.venv/bin/python"))
SEGUIMIENTO = REPO / "docs/seguimiento"
CARPETAS = ["", "reserva", "corriendo", "hechos", "hechos/integrados", "descartadas", "trabadas"]
GRANDE = 600      # fila más larga que esto: PREP (repro + test rojo) y no FIX

REGLAS = """/fable-method
/ponytail
{que}
Worktree {wt} (cwd: clon/; Python {py}). NO commit, NO git add. Lee AGENTS.md; copiá Fusion: buscá antes con scripts/fusion_docs.py buscar <palabras> y leé docs/fusion_docs.
Hallazgo fuera de tu ítem: fila nueva en docs/seguimiento/ con el siguiente ID libre (mirá todos los worktrees); no lo arregles.
Si tras 3 intentos distintos no sale, o hace falta decidir algo de producto: pará y escribí qué probaste.
Verificá: ruff check . ; ../scripts/tests_afectados.py --correr (si elige más de 15 grupos, solo tu test y los que importan lo que tocaste). Informe de 5 líneas con la salida real.
/ponytail-review
"""


def existentes():
    nombres = set()
    for c in CARPETAS:
        for t in (COLA / c).glob("*.tarea"):
            nombres.add(re.sub(r"^\w*?_?(?=(FIX|PREP|CAZA|LENTO)-)", "", t.stem))
            nombres.update(re.findall(r"[BPFH]-\d+[a-z]?", t.stem))
    return nombres


def filas_abiertas():
    en_ahora = (SEGUIMIENTO / "ahora.md").read_text(encoding="utf-8")
    for linea in (SEGUIMIENTO / "bugs.md").read_text(encoding="utf-8").splitlines():     # solo bugs: lo de diseño no va a OpenCode
        m = re.match(r"\| (B-\d+[a-z]?) \| Bocetos?\b", linea)
        if m and "| Abierto |" in linea and m.group(1) not in en_ahora:
            yield m.group(1), len(linea)


def sin_cobertura():
    tabla = Path(os.environ.get("TMPDIR", "/tmp")) / "cobertura_boceto_auto.md"
    subprocess.run([PY, "../scripts/cobertura_boceto.py", str(tabla)], cwd=REPO / "clon", capture_output=True, text=True, timeout=300)
    # claves sin test automático (**no** en esa columna), las que además no se probaron como usuario primero
    filas = re.findall(r"^\|[^|]*\|[^|]*\| `([^`]+)` \| (\*\*no\*\*|sí[^|]*) \| (\*\*no\*\*|sí[^|]*) \|", tabla.read_text(encoding="utf-8"), re.M)
    return [k for k, t, u in sorted(filas, key=lambda f: "sí" in f[2]) if t == "**no**"]


def candidatas():
    for k in sin_cobertura():
        yield f"PREP-TEST-{k}", (f"PREPARAR el test del comando de boceto «{k}»: escribí clon/tests/test_prep_cmd_{k}.py "
                                 f"(un caso con valor numérico y un caso borde) según docs/fusion_docs. Si falla, es un bug: fila nueva y xfail. "
                                 f"Solo escribís tests, no código de la app.")
    for i, largo in filas_abiertas():
        if largo > GRANDE:
            yield f"PREP-{i}", (f"{i}: leé su fila en docs/seguimiento/ (grep -n \"| {i} |\"). Reproducilo y dejá un test rojo (xfail con el motivo) "
                                f"y una ficha de 10 líneas en docs/seguimiento/preparado/{i}.md con la causa probable. No toques código de la app.")
        else:
            yield f"FIX-{i}", (f"{i}: leé su fila en docs/seguimiento/ (grep -n \"| {i} |\"). Reproducilo, arreglá la causa con el cambio más chico "
                               f"(UN archivo), dejá un test que falle sin el arreglo, borrá la fila y sumá una viñeta de ≤300 caracteres al Registro de PROJECT_LOG.md.")
    hoy = datetime.date.today().strftime("%Y%m%d")
    yield f"CAZA-boceto-{hoy}", ("Corré desde clon/: ../scripts/caza/cazar.py tema boceto (fecha %s). "
                                  "Cada falla nueva es una fila de boceto en docs/seguimiento/ con su repro; no arregles nada." % hoy)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tope", type=int, default=8)
    ap.add_argument("--seco", action="store_true")
    a = ap.parse_args()
    reserva = COLA / "reserva"
    hay = len(list(reserva.glob("*.tarea")))
    ya = existentes()
    BRIEFS.mkdir(parents=True, exist_ok=True)
    creadas = []
    for nombre, que in candidatas():
        if hay + len(creadas) >= a.tope:
            break
        if nombre in ya:
            continue
        wt = Path.home() / f"OmniCAD-{nombre}"
        if not a.seco:
            if not wt.exists():
                subprocess.run(["bash", str(REPO / "scripts/worktree_item.sh"), "crear", nombre], capture_output=True)
            brief = BRIEFS / f"{nombre}.md"
            brief.write_text(REGLAS.format(que=que, wt=wt, py=PY), encoding="utf-8")
            (reserva / f"70_{nombre}.tarea").write_text(f"WT={wt}\nBRIEF={brief}\n", encoding="utf-8")
        creadas.append(nombre)
    print("reserva:", hay, "→", hay + len(creadas), creadas)


if __name__ == "__main__":
    sys.exit(main())
