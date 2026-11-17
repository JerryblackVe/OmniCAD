#!/usr/bin/env bash
# Vigía de OpenCode sin modelo (crontab de la VPS, cada 10 min; Gerardo, 2026-11-17). Gasto cero de Claude.
# - Una corrida `opencode run` que no escribe nada en sus logs hace más de 20 min se mata (el lanzador sigue solo).
# - Si no corre ni opencode ni un lanzador, arranca el siguiente de la cola: el primer `*.sh` de $COLA (orden
#   alfabético: 01_x.sh, 02_y.sh…), que pasa a $COLA/hechos/. La cola la llena el coordinador.
# Línea de crontab: */10 * * * * bash /home/mosos/OmniCAD/scripts/vigia_opencode.sh
COLA=${VIGIA_COLA:-$HOME/coordinador/opencode_cola}
LOGS=${VIGIA_LOGS:-$HOME/coordinador/e9prompts}     # dónde escriben las corridas (se mira la fecha del archivo más nuevo)
MIN=${VIGIA_MIN:-20}
LOG=$COLA/vigia.log
mkdir -p "$COLA/hechos" "$COLA/logs"
anota() { echo "$(date -u '+%F %T') $*" >> "$LOG"; }

corridas=$(pgrep -f "^[^ ]*/opencode run " || true)     # solo el binario: un comando que nombre «opencode run» (un grep) no cuenta
if [ -n "$corridas" ]; then
  # el log de la corrida casi no se escribe hasta el final; el propio de opencode sí, mientras trabaja
  if [ -z "$(find "$LOGS" "$COLA/logs" "$HOME/.local/share/opencode/log" -type f -newermt "-$MIN min" -print -quit 2>/dev/null)" ]; then
    anota "trabada: sin escribir hace más de $MIN min; mato opencode run ($(echo $corridas))"
    kill $corridas 2>/dev/null; sleep 5; kill -9 $corridas 2>/dev/null
  fi
  exit 0
fi
pgrep -f "lanzador.sh" > /dev/null && exit 0          # un lanzador entre dos pasos (p. ej. corriendo los tests)

siguiente=$(ls "$COLA"/*.sh 2>/dev/null | head -1)
if [ -z "$siguiente" ]; then
  [ "$(tail -1 "$LOG" 2>/dev/null | cut -d' ' -f3-)" = "cola vacía" ] || anota "cola vacía"
  exit 0
fi
nombre=$(basename "$siguiente" .sh)
mv "$siguiente" "$COLA/hechos/$nombre.lanzador.sh"      # el nombre termina en lanzador.sh: el pgrep de arriba lo ve
setsid nohup bash "$COLA/hechos/$nombre.lanzador.sh" > "$COLA/logs/$nombre.log" 2>&1 < /dev/null &
anota "lanzo $nombre (pid $!)"
