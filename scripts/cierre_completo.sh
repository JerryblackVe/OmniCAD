#!/bin/bash
# Cierre completo (coordinador o sesión nocturna): suite paralela, piezas y humo minimizados, foco real con la PC sin uso.
# --serie conserva la suite sin xdist hasta tener dos noches paralelas verdes. Resumen en evidencias/cierre_<fecha>/.
PROCESOS=4
PARALELO=(-n 4 --dist loadfile)
MEMORIA=(env OMNICAD_TURNO_TOPE_MB=6500 OMNICAD_TURNO_MB=6500)
case "$*" in
  "") ;;
  --serie) PROCESOS=1; PARALELO=(); MEMORIA=() ;;
  *) echo "Uso: bash scripts/cierre_completo.sh [--serie]" >&2; exit 2 ;;
esac
RAIZ=$(cd "$(dirname "$0")/.." && pwd) || exit 1
cd "$RAIZ/clon" || exit 1
S="$RAIZ/evidencias/cierre_$(date +%F)"
rm -rf "$S"; mkdir -p "$S"
PY=.venv/Scripts/python.exe
[ -x "$PY" ] || PY=/d/PROGRAMA/clon/.venv/Scripts/python.exe  # el worktree comparte el venv de main
R="$S/resumen.txt"; inicio=$(date +%s)
echo "inicio $(date '+%H:%M:%S') HEAD $(git rev-parse --short HEAD)" > "$R"
espera_ocio() {
  local necesita=$1 tope=$2 t0; t0=$(date +%s)
  while true; do
    idle=$($PY -c "
import ctypes, ctypes.wintypes as w
class L(ctypes.Structure): _fields_=[('cbSize', w.UINT), ('dwTime', w.DWORD)]
l=L(); l.cbSize=ctypes.sizeof(l); ctypes.windll.user32.GetLastInputInfo(ctypes.byref(l))
print((ctypes.windll.kernel32.GetTickCount() - l.dwTime)//1000)")
    [ "${idle:-0}" -ge "$necesita" ] && return 0
    [ $(( $(date +%s) - t0 )) -ge "$tope" ] && return 1
    sleep 30
  done
}
$PY -m ruff check . > "$S/ruff.txt" 2>&1
echo "ruff exit=$? | $(tail -n 1 "$S/ruff.txt")" >> "$R"
MOTOR=tests/test_motor.py::test_prueba_humo_arranca_con_omnikernel_y_ocp_bloqueado
ls tests/test_*.py | sort > "$S/lista.txt"
if [ -f "$RAIZ/evidencias/tiempos.json" ]; then
  $PY ../scripts/tiempos.py "$S/lista.txt" --tandas "$S" --procesos "$PROCESOS" || exit 1
else
  split -n l/10 -d "$S/lista.txt" "$S/parte_" || exit 1
fi
for p in "$S"/parte_*; do
  [ -s "$p" ] || continue
  n=$(basename "$p")
  mapfile -t archivos < "$p"
  "${MEMORIA[@]}" $PY ../scripts/turno.py --plazo 900 -- $PY -m pytest "${archivos[@]}" "${PARALELO[@]}" -q -W error -p no:cacheprovider --deselect "$MOTOR" --durations=0 --junitxml="$S/$n.xml" > "$S/$n.txt" 2>&1
  echo "$n exit=$? | $(tail -n 1 "$S/$n.txt")" >> "$R"
done
# Abre otra app entera dentro de pytest: junto a una tanda pasa el tope de memoria de turno.py (MemoryError, 2026-11-01).
$PY ../scripts/turno.py --plazo 900 -- $PY -m pytest "$MOTOR" -q -W error -p no:cacheprovider --durations=0 --junitxml="$S/motor.xml" > "$S/motor.txt" 2>&1
echo "motor exit=$? | $(tail -n 1 "$S/motor.txt")" >> "$R"
# Ranking de los tests y archivos lentos de toda la suite (paquete A de docs/plan_velocidad.md).
$PY ../scripts/tiempos.py "$S" > "$S/tiempos.txt" 2>&1
echo "tiempos exit=$? | $(head -n 1 "$S/tiempos.txt")" >> "$R"
$PY ../scripts/prueba_ui/todo.py > "$S/ui.txt" 2>&1
echo "ui exit=$? | $(grep -cE '[1-9][0-9]* con ✗' "$S/ui.txt") piezas con ✗" >> "$R"
# El humo corre con la ventana transparente y sin cursor real ni foco (P-60): no espera que la PC quede sin uso.
PYTHONIOENCODING=utf-8 OMNICAD_PRUEBA_VENTANA=minimizada $PY ../scripts/turno.py --plazo 900 -- $PY OmniCAD.py --prueba-humo > "$S/humo.txt" 2>&1
echo "humo exit=$? | $(tail -n 2 "$S/humo.txt" | tr '\n' ' ')" >> "$R"
if espera_ocio 120 10800; then
  export PYTHONIOENCODING=utf-8
  $PY ../scripts/prueba_ui/todo.py --ventana visible registro_uso asistente > "$S/ui_foco.txt" 2>&1
  echo "ui_foco exit=$? | $(tail -n 4 "$S/ui_foco.txt" | tr '\n' ' ')" >> "$R"
else
  echo "ui_foco: NO corrio (la PC no quedo sin uso en 3 h)" >> "$R"
fi
echo "fin $(date '+%H:%M:%S') ($(( $(date +%s) - inicio )) s)" >> "$R"
