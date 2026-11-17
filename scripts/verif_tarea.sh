#!/usr/bin/env bash
# Verificación rápida de una tarea de la cola de OpenCode/CodeBuddy; la llama el vigía dentro del worktree.
# Regla 4 de CLAUDE.md: ruff + los tests tocados y los que importan directo lo tocado (no todo el grafo: eso
# tardaba más de 1 h por tarea y trababa la cola). La suite completa la corre suite_noche.sh.
# shortcut: sin turno.py (corta a los 900 s); el tope de corridas a la vez lo pone el vigía (MAX).
PY=$HOME/OmniCAD/clon/.venv/bin/python
cd clon || exit 1
$PY -m ruff check . || exit 1
cambiados=$( { git diff --name-only --relative "$(git merge-base HEAD main)"; git ls-files -o --exclude-standard; } | grep '\.py$' | sort -u)
tests=$(for f in $cambiados; do
  case $f in
    tests/test_*.py) echo "$f" ;;
    *) m=$(basename "$f" .py); grep -lE "^\s*(import|from) .*\b$m\b" tests/test_*.py ;;
  esac
done | sort -u | head -30)
[ -z "$tests" ] && { echo "sin tests que importen lo tocado: solo ruff"; exit 0; }
echo "tests: $(echo $tests | wc -w)"
salida=$(timeout 1500 xvfb-run -a $PY -m pytest -q -p no:cacheprovider $tests 2>&1); rc=$?
echo "$salida" | tail -30
[ $rc = 0 ] && exit 0
# Los rojos que ya tiene main (los anota suite_noche.sh) no son culpa de la tarea.
nuevos=$(echo "$salida" | grep -oE "^(FAILED|ERROR) [^ ]+" | cut -d" " -f2 | sort -u | grep -vxFf "$HOME/coordinador/suite_noche/rojos.txt")
[ $rc = 1 ] && [ -z "$nuevos" ] && { echo "solo fallan rojos ya conocidos de main"; exit 0; }
echo "ROJOS NUEVOS: $nuevos"; exit 1
