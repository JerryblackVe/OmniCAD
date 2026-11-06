#!/bin/bash
# Cierre completo (lo corre el coordinador o la sesión nocturna, nunca dos a la vez): ruff, suite en 10 tandas con -W error, piezas de ventana minimizadas y, con la PC sin uso, humo y piezas con foco real. Resumen en evidencias/cierre_<fecha>/resumen.txt.
cd /d/PROGRAMA/clon || exit 1
S="/d/PROGRAMA/evidencias/cierre_$(date +%F)"
rm -rf "$S"; mkdir -p "$S"
PY=.venv/Scripts/python.exe
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
split -n l/10 -d "$S/lista.txt" "$S/parte_"
for p in "$S"/parte_0*; do
  n=$(basename "$p")
  $PY ../scripts/turno.py --plazo 900 -- $PY -m pytest $(tr '\n' ' ' < "$p") -q -W error -p no:cacheprovider --deselect "$MOTOR" > "$S/$n.txt" 2>&1
  echo "$n exit=$? | $(tail -n 1 "$S/$n.txt")" >> "$R"
done
# Abre otra app entera dentro de pytest: junto a una tanda pasa el tope de memoria de turno.py (MemoryError, 2026-11-01).
$PY ../scripts/turno.py --plazo 900 -- $PY -m pytest "$MOTOR" -q -W error -p no:cacheprovider > "$S/motor.txt" 2>&1
echo "motor exit=$? | $(tail -n 1 "$S/motor.txt")" >> "$R"
$PY ../scripts/prueba_ui/todo.py > "$S/ui.txt" 2>&1
echo "ui exit=$? | $(grep -cE '[1-9][0-9]* con ✗' "$S/ui.txt") piezas con ✗" >> "$R"
if espera_ocio 120 10800; then
  export PYTHONIOENCODING=utf-8
  $PY ../scripts/turno.py --plazo 900 -- $PY OmniCAD.py --prueba-humo > "$S/humo.txt" 2>&1
  echo "humo exit=$? | $(tail -n 2 "$S/humo.txt" | tr '\n' ' ')" >> "$R"
  $PY ../scripts/prueba_ui/todo.py --ventana visible registro_uso asistente > "$S/ui_foco.txt" 2>&1
  echo "ui_foco exit=$? | $(tail -n 4 "$S/ui_foco.txt" | tr '\n' ' ')" >> "$R"
else
  echo "humo y ui_foco: NO corrieron (la PC no quedo sin uso en 3 h)" >> "$R"
fi
echo "fin $(date '+%H:%M:%S') ($(( $(date +%s) - inicio )) s)" >> "$R"
