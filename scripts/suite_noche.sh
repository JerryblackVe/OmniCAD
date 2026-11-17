#!/usr/bin/env bash
# Suite completa cada noche, sin modelo (crontab de la VPS, 06:15 UTC = 03:15 de Argentina; Gerardo, 2026-11-17).
# Solo pytest: la humo y las piezas de la ventana siguen en el cierre completo. Resultado en ~/coordinador/suite_noche/.
D=$HOME/coordinador/suite_noche; mkdir -p "$D"; f=$D/$(date -u +%F).txt
cd "$HOME/OmniCAD/clon" || exit 1
timeout 3600 xvfb-run -a .venv/bin/python -m pytest -q -p no:cacheprovider > "$f" 2>&1; echo "rc=$?" >> "$f"
tail -3 "$f" | head -2 > "$D/ultima.txt"; ls -1t "$D"/2*.txt | tail -n +15 | xargs -r rm   # guarda 2 semanas
