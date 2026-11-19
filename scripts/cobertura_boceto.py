# -*- coding: utf-8 -*-
"""Tabla de cobertura de los comandos de la cinta del boceto (plan_boceto_perfecto.md). Uso, desde clon/:
.venv/bin/python ../scripts/cobertura_boceto.py salida.md. Un comando «tiene test» si algún test que no es de catálogo nombra su clave."""
import os, re, subprocess, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, ".")
from omnicad.ui import cinta
def planos(items, ruta):
    for it in items:
        if it == "-" or not isinstance(it, tuple): continue
        if it[0] == "item" and it[2]: yield ruta, it[1], it[2]
        elif it[0] == "sub": yield from planos(it[2], ruta + " › " + it[1])
claves = {}
for grupo in cinta.BOCETO:
    nombre, _iconos, items = grupo[0], grupo[1], grupo[2]
    for g, txt, k in planos(items, nombre): claves.setdefault(k, (g, txt))
def leer(globs):
    t = subprocess.run(["bash", "-c", f"cat {globs} 2>/dev/null"], capture_output=True, text=True).stdout
    return t
import glob
def patron(k):
    base = k[3:] if k.startswith("sk_") else k
    return re.compile(r"""(?:(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])|["']%s["'])""" % (re.escape(k), re.escape(base)))
pats = {k: patron(k) for k in claves}
def por_archivo(patrones_glob):
    res = {}
    for f in glob.glob(patrones_glob):
        t = open(f, encoding="utf-8", errors="ignore").read()
        res[f] = {k for k, p in pats.items() if p.search(t)}
    return res
pt = por_archivo("tests/*.py")
genericos = {f for f in pt if f.endswith(("test_cobertura_ui_api.py", "test_iconos_extra.py", "test_cinta.py", "test_iconos_interfaz.py"))}      # catálogos (cinta, íconos, atajos): no prueban un comando
print("genéricos:", sorted(genericos))
pu = por_archivo("../scripts/prueba_ui/*.py")
guiu = {f for f, ks in pu.items() if len(ks) > 25}
tests = {k: sum(1 for f, ks in pt.items() if k in ks and f not in genericos) for k in claves}
ui = {k: sum(1 for f, ks in pu.items() if k in ks and f not in guiu) for k in claves}
seg = leer("../docs/seguimiento/bugs.md ../docs/seguimiento/faltantes.md ../docs/seguimiento/mejoras.md")
def cuenta(txt, k):
    base = k[3:] if k.startswith("sk_") else k
    return len(re.findall(r"""(?:(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])|["']%s["'])""" % (re.escape(k), re.escape(base)), txt))
filas = []
for k, (g, txt) in claves.items():
    t, u = tests[k], ui[k]
    abiertas = sorted(set(re.findall(r"^\| ([BPFH]-[0-9a-z]+) \|[^\n]*" + re.escape(k), seg, re.M)))
    filas.append((g, txt or k, k, t, u, ",".join(abiertas) or "—"))
tot = len(filas); sin_t = sum(1 for f in filas if f[3] == 0); sin_u = sum(1 for f in filas if f[4] == 0); ninguna = sum(1 for f in filas if f[3] == 0 and f[4] == 0)
out = ["| Grupo | Comando | Clave | Test automático | Probado como usuario | Fila abierta |", "|---|---|---|---|---|---|"]
for g, txt, k, t, u, a in sorted(filas):
    out.append(f"| {g} | {txt} | `{k}` | {'sí (' + str(t) + ')' if t else '**no**'} | {'sí (' + str(u) + ')' if u else '**no**'} | {a} |")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(out) + "\n")
print(tot, sin_t, sin_u, ninguna)
for f in sorted(filas):
    if f[3] == 0 and f[4] == 0: print("NINGUNA", f[0], f[2])
