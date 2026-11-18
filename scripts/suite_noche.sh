#!/usr/bin/env bash
# Cierre nocturno, sin modelo (crontab de la VPS, 06:15 UTC = 03:15 de Argentina; Gerardo, 2026-11-17): la suite completa
# (incluye tests/test_reglas_coherentes.py) y después la humo. Las piezas de la ventana siguen en el cierre completo
# («corré todo»). Resultado en ~/coordinador/suite_noche/.
# En 4 partes a la vez (en una sola pasaba de 1 h: cortó al 44 % el 17/11). Cada parte, con su pantalla y tope de 3 h.
D=$HOME/coordinador/suite_noche; mkdir -p "$D"; hoy=$(date -u +%F)
cd "$HOME/OmniCAD/clon" || exit 1
for i in 0 1 2 3; do
  archivos=$(ls tests/test_*.py | awk -v i=$i 'NR % 4 == i')
  ( timeout 10800 xvfb-run -a .venv/bin/python -m pytest -q -p no:cacheprovider --durations=20 $archivos > "$D/$hoy.parte$i.txt" 2>&1
    echo "rc=$?" >> "$D/$hoy.parte$i.txt" ) &
done
wait
# La humo va sola después de la suite: abre la ventana real y junto a 4 pytest pasaría el tope de memoria.
PYTHONIOENCODING=utf-8 OMNICAD_PRUEBA_VENTANA=minimizada timeout 1800 xvfb-run -a .venv/bin/python OmniCAD.py --prueba-humo \
  > "$D/$hoy.humo.txt" 2>&1; echo "rc=$?" >> "$D/$hoy.humo.txt"
{ for i in 0 1 2 3; do echo "parte $i: $(tail -2 "$D/$hoy.parte$i.txt" | tr '\n' ' ')"; done
  echo "humo: $(tail -2 "$D/$hoy.humo.txt" | tr '\n' ' ')"
  grep -hE "^(FAILED|ERROR) " "$D/$hoy".parte*.txt | cut -c1-160; } > "$D/ultima.txt"
# Rojos de main para verif_tarea.sh; si una parte cortó por tiempo, la lista vieja se conserva.
grep -q "rc=124" "$D/$hoy".parte*.txt || grep -hoE "^(FAILED|ERROR) [^ ]+" "$D/$hoy".parte*.txt | cut -d" " -f2 | sort -u > "$D/rojos.txt"
# Los 20 más lentos de las 4 partes («Protocolo de tests rápidos» en docs/coordinacion.md): el coordinador los pasa a OpenCode.
grep -hE "^[0-9.]+s (call|setup|teardown) " "$D/$hoy".parte*.txt | sort -rn | head -20 > "$D/lentos.txt"
ls -1t "$D"/2*.txt | tail -n +57 | xargs -r rm   # guarda 2 semanas
