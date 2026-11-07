"""Selecciona tests y piezas por imports estáticos y referencias a archivos (plan_velocidad, paquete C).

Uso: python scripts/tests_afectados.py [--desde REF] [--hasta REF] [--correr]
Sin --hasta compara contra el árbol de trabajo, incluidos los archivos sin seguimiento.
El grafo describe el código actual: no ejecuta imports ni reconstruye versiones históricas.
Los imports dinámicos no se pueden deducir con AST; la suite completa sigue siendo el cierre.
"""

import argparse
import ast
import json
import math
import subprocess
import sys
import tokenize
from collections import Counter, defaultdict, deque
from pathlib import Path

# Una estimación prudente deja margen al tope de turno.py cuando faltan mediciones.
SEGUNDOS_SIN_MEDIR = 30


def _git(raiz, *argumentos):
    proceso = subprocess.run(["git", *argumentos], cwd=raiz, capture_output=True)
    if proceso.returncode:
        raise ValueError("Git: " + proceso.stderr.decode("utf-8", errors="replace").strip())
    return proceso.stdout.decode("utf-8", errors="surrogateescape")


def archivos_tocados(raiz, desde="HEAD", hasta=None):
    """Devuelve rutas relativas al repo; incluye cambios preparados, sin preparar y nuevos si no hay hasta."""
    referencias = [desde] + ([hasta] if hasta is not None else [])
    salida = _git(raiz, "diff", "--name-only", "--no-renames", "-z", *referencias, "--")
    tocados = set(salida.split("\0")) - {""}
    if hasta is None:
        tocados.update(_git(raiz, "ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    return sorted(tocados - {""})


def _modulo(ruta):
    partes = list(Path(ruta).with_suffix("").parts)
    if partes[:1] == ["clon"]:
        partes = partes[1:]
    if partes[-1] == "__init__":
        partes.pop()
    return ".".join(partes)


def _imports(arbol, modulo, es_paquete, conocidos):
    paquete = modulo if es_paquete else modulo.rpartition(".")[0]
    dependencias = set()
    pendientes = [arbol]
    while pendientes:
        nodo = pendientes.pop()
        # Un import solo puede estar en un bloque de sentencias, no dentro de expresiones o constantes.
        pendientes.extend(hijo for hijo in ast.iter_child_nodes(nodo)
                          if isinstance(hijo, (ast.stmt, ast.ExceptHandler, ast.match_case)))
        nombres = []
        if isinstance(nodo, ast.Import):
            nombres = [alias.name for alias in nodo.names]
        elif isinstance(nodo, ast.ImportFrom):
            base = nodo.module or ""
            if nodo.level:
                partes = paquete.split(".")
                base = ".".join(partes[:len(partes) - nodo.level + 1] + ([base] if base else []))
            nombres = [base] + [f"{base}.{alias.name}" for alias in nodo.names if alias.name != "*"]
        for nombre in nombres:
            # Las piezas y los tests también importan auxiliares hermanos sin prefijo de paquete.
            local = f"{paquete}.{nombre}"
            if local in conocidos:
                nombre = local
            partes = nombre.split(".")
            for i in range(1, len(partes) + 1):
                prefijo = ".".join(partes[:i])
                if prefijo in conocidos:
                    dependencias.add(prefijo)
    return dependencias


def _piezas(arbol):
    """Lee PIEZAS y sus append literales en todo.py, sin ejecutar el arnés de ventana."""
    nombres = []
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PIEZAS" for t in nodo.targets):
            nombres = list(ast.literal_eval(nodo.value))
        elif (isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Call)
              and isinstance(nodo.value.func, ast.Attribute) and nodo.value.func.attr == "append"
              and isinstance(nodo.value.func.value, ast.Name) and nodo.value.func.value.id == "PIEZAS"):
            nombres.append(ast.literal_eval(nodo.value.args[0]))
    return {f"scripts/prueba_ui/{nombre}.py" for nombre in nombres}


def _referencia(ruta, texto, repetidos):
    archivo = Path(ruta)
    # El nombre solo vale si es único en el repo (README.md no), y las carpetas de docs/ no valen: los tests las
    # nombran en comentarios y un cambio solo en docs elegía 19 tests.
    pistas = [ruta, ruta.removeprefix("clon/")] + ([archivo.name] if archivo.name not in repetidos else []) + [
        p.as_posix() for p in archivo.parents if len(p.parts) >= 2 and p.parts[0] != "docs"]
    return next((pista for pista in pistas if pista in texto), None)


def seleccionar(raiz, desde="HEAD", hasta=None):
    """Devuelve (tests, piezas, causas de suite completa); cada diccionario ruta→motivo está ordenado."""
    raiz = Path(raiz)
    tocados = archivos_tocados(raiz, desde, hasta)
    rutas = sorted({p.relative_to(raiz).as_posix() for carpeta in ("clon/omnicad", "clon/tests", "scripts/prueba_ui")
                    for p in (raiz / carpeta).rglob("*.py")})
    modulos = {_modulo(ruta): ruta for ruta in rutas}
    conocidos = set(modulos) | {_modulo(r) for r in tocados if r.startswith("clon/omnicad/") and r.endswith(".py")}
    tests = {ruta for ruta in rutas if ruta.startswith("clon/tests/") and Path(ruta).name.startswith("test_")}
    piezas, textos = set(), {}
    inverso = defaultdict(set)
    for modulo, ruta in modulos.items():
        with tokenize.open(raiz / ruta) as archivo:
            texto = archivo.read()
        textos[ruta] = texto
        arbol = ast.parse(texto, filename=ruta)
        if ruta == "scripts/prueba_ui/todo.py":
            piezas = _piezas(arbol)
        for dependencia in _imports(arbol, modulo, Path(ruta).name == "__init__.py", conocidos):
            inverso[dependencia].add(modulo)

    globales = [r for r in tocados if r in ("clon/tests/conftest.py", "clon/pyproject.toml")
                or Path(r).name.startswith("requirements")]
    motivos = {r: "suite completa: " + ", ".join(globales) for r in tests} if globales else {}
    nombres = Counter(Path(r).name for r in _git(raiz, "ls-files", "-z").split("\0") if r)
    repetidos = {n for n, veces in nombres.items() if veces > 1}
    elegidas = {}
    pendientes = deque()
    vistos = set()
    for ruta in tocados:
        if ruta in tests:
            motivos[ruta] = "test tocado"
        if ruta in piezas:
            elegidas[ruta] = "pieza tocada"
        if ruta.startswith("clon/omnicad/") and ruta.endswith(".py"):
            modulo = _modulo(ruta)
            pendientes.append((modulo, ruta))
            vistos.add(modulo)
        elif ruta not in tests:
            for test in sorted(tests):
                pista = _referencia(ruta, textos[test], repetidos)
                if pista:
                    motivos.setdefault(test, f"nombra {pista} (cambió {ruta})")
            # test_seguimiento revisa la sección «Prompt para el agente» de todo docs/*.md sin nombrarlos.
            seguimiento = "clon/tests/test_seguimiento.py"
            if Path(ruta).parent.as_posix() == "docs" and ruta.endswith(".md") and seguimiento in tests:
                motivos.setdefault(seguimiento, f"revisa los prompts de docs/*.md (cambió {ruta})")
            # Un auxiliar de prueba tocado también afecta a las piezas/tests que lo importan.
            if ruta in rutas:
                modulo = _modulo(ruta)
                pendientes.append((modulo, ruta))
                vistos.add(modulo)
    while pendientes:
        modulo, origen = pendientes.popleft()
        ruta = modulos.get(modulo)
        if ruta in tests:
            motivos.setdefault(ruta, f"depende por imports de {origen}")
        if ruta in piezas:
            elegidas.setdefault(ruta, f"depende por imports de {origen}")
        for consumidor in sorted(inverso[modulo] - vistos):
            vistos.add(consumidor)
            pendientes.append((consumidor, origen))
    return ({r.removeprefix("clon/"): motivos[r] for r in sorted(motivos)},
            {r: elegidas[r] for r in sorted(elegidas)}, globales)


def agrupar(tests, tiempos):
    """Agrupa archivos ordenados en menos de 600 s estimados; sin medición usa 30 s, uno indivisible va solo."""
    grupos, grupo, total = [], [], 0.0
    for test in sorted(tests):
        segundos = float(tiempos.get(test, SEGUNDOS_SIN_MEDIR))
        if not math.isfinite(segundos) or segundos < 0:
            raise ValueError(f"Tiempo inválido para {test}: {segundos}")
        if grupo and total + segundos >= 600:
            grupos.append(grupo)
            grupo, total = [], 0.0
        grupo.append(test)
        total += segundos
    if grupo:
        grupos.append(grupo)
    return grupos


def main(argumentos=None):
    """Lista la selección o ejecuta sus grupos con turno.py; devuelve 1 si falla algún grupo, 2 ante errores."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--desde", default="HEAD", help="referencia inicial (por defecto HEAD)")
    parser.add_argument("--hasta", help="referencia final (por defecto árbol de trabajo y archivos nuevos)")
    parser.add_argument("--correr", action="store_true", help="ejecutar solo los tests elegidos, con turno.py")
    parser.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parents[1], help="raíz del repo")
    args = parser.parse_args(argumentos)
    try:
        tests, piezas, globales = seleccionar(args.raiz, args.desde, args.hasta)
        if globales:
            print("SUITE COMPLETA por cambio en: " + ", ".join(globales), flush=True)
        print(f"Tests elegidos: {len(tests)}", flush=True)
        for ruta, motivo in tests.items():
            print(f"  {ruta} — {motivo}")
        print(f"Piezas elegidas (solo se listan): {len(piezas)}", flush=True)
        for ruta, motivo in piezas.items():
            print(f"  {ruta} — {motivo}")
        if piezas:
            print("Desde clon/: ../scripts/prueba_ui/todo.py " + " ".join(Path(p).stem for p in piezas), flush=True)
        if not args.correr or not tests:
            return 0
        archivo_tiempos = args.raiz / "evidencias" / "tiempos.json"
        tiempos = json.loads(archivo_tiempos.read_text(encoding="utf-8"))["archivos"] if archivo_tiempos.exists() else {}
        grupos = agrupar(tests, tiempos)
        fallos = 0
        for i, grupo in enumerate(grupos, 1):
            estimado = sum(float(tiempos.get(t, SEGUNDOS_SIN_MEDIR)) for t in grupo)
            print(f"Grupo {i}/{len(grupos)}: {len(grupo)} archivos, {estimado:.1f} s estimados", flush=True)
            if estimado >= 600:
                print("Aviso: un archivo solo alcanza los 600 s; no se puede dividir por archivo.", flush=True)
            comando = [sys.executable, "../scripts/turno.py", "--plazo", "900", "--", sys.executable,
                       "-m", "pytest", *grupo, "-q", "-W", "error", "-p", "no:cacheprovider"]
            codigo = subprocess.run(comando, cwd=args.raiz / "clon").returncode
            fallos += codigo != 0
            print(f"Grupo {i}: salida {codigo}", flush=True)
        print(f"Resultado: {len(grupos)} grupos, {fallos} fallidos", flush=True)
        return int(fallos > 0)
    except (OSError, ValueError, SyntaxError, KeyError) as error:
        print(f"No se pudo seleccionar o correr los tests: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
