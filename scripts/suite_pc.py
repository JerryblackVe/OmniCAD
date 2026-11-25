#!/usr/bin/env python3
"""Suite completa en la PC (13 GB) gastando poca memoria: sin modelo, de a un lote por vez.

Uso, desde clon/ con el Python del venv:
  ../scripts/suite_pc.py [--lote 20]

Un pytest largo acumula memoria (Qt y OCC no la devuelven); acá cada lote de archivos es un proceso nuevo, con
turno.py (de a uno) y pantalla offscreen. Deja evidencias/suite_pc_<fecha>/parteN.txt y resumen.txt (solo los rojos).
"""
import argparse
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

CLON = Path(__file__).resolve().parent.parent / "clon"
SALIDA = CLON.parent / "evidencias" / f"suite_pc_{date.today():%Y%m%d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lote", type=int, default=20, help="archivos de test por proceso")
    n = ap.parse_args().lote
    archivos = sorted(p.as_posix() for p in (CLON / "tests").glob("test_*.py"))
    archivos = [str(Path(a).relative_to(CLON.as_posix())) for a in archivos]
    SALIDA.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    rojos = []
    for i in range(0, len(archivos), n):
        parte = SALIDA / f"parte{i // n:02d}.txt"
        cmd = [sys.executable, "../scripts/turno.py", "--", sys.executable, "-m", "pytest", "-q",
               "-p", "no:cacheprovider", "--tb=short", *archivos[i:i + n]]
        with open(parte, "w", encoding="utf-8") as f:
            rc = subprocess.run(cmd, cwd=CLON, stdout=f, stderr=subprocess.STDOUT, env=env).returncode
        texto = parte.read_text(encoding="utf-8", errors="replace")
        rojos += [l for l in texto.splitlines() if l.startswith(("FAILED ", "ERROR "))]
        print(f"{parte.name}: rc={rc}", flush=True)
    (SALIDA / "resumen.txt").write_text("\n".join(rojos) + "\n", encoding="utf-8")
    print(f"{len(rojos)} rojos en {SALIDA / 'resumen.txt'}")


if __name__ == "__main__":
    main()
