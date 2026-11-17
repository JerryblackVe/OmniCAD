#!/usr/bin/env bash
# Vigía de OpenCode sin modelo (crontab de la VPS, cada 10 min; Gerardo, 2026-11-17). Gasto cero de Claude.
# Cola: archivos `$COLA/NN_nombre.tarea` (orden alfabético) con líneas que se leen con `source`:
#   WT=/home/mosos/OmniCAD-<ID>    BRIEF=/ruta/al/brief.md    MODELO=opencode/glm-5.3-flash-free (opcional)
# - Corre una tarea a la vez (salida en $COLA/logs/<nombre>.log). Al terminar pasa a hechos/.
# - Trabada (ni su log ni el de opencode cambian en 20 min): respaldo de lo que dejó (tgz) y relanza la MISMA tarea
#   con el modelo siguiente y un brief que sigue desde ahí. A la 2.ª trabada, pasa a trabadas/ y sigue la cola.
#   shortcut: retoma con brief (git diff + log), no con `opencode run --session`: el id de sesión no queda a mano.
# - Corridas que no son de la cola (los lanzadores de E9): si se traban, solo se matan; el lanzador sigue solo.
# Línea de crontab: */10 * * * * bash /home/mosos/OmniCAD/scripts/vigia_opencode.sh
COLA=${VIGIA_COLA:-$HOME/coordinador/opencode_cola}
LOGS=${VIGIA_LOGS:-$HOME/coordinador/e9prompts}
OC=${VIGIA_OC:-$HOME/.opencode/bin/opencode}
MIN=${VIGIA_MIN:-20}
MODELOS=(opencode/glm-5.3-flash-free nvidia/minimaxai/minimax-m3.1-flash opencode/deepseek-v4.1-flash-free)
LOG=$COLA/vigia.log; EST=$COLA/actual
mkdir -p "$COLA/hechos" "$COLA/trabadas" "$COLA/logs"
anota() { echo "$(date -u '+%F %T') $*" >> "$LOG"; }
quieto() {   # nada escribió en $MIN minutos (el log de la corrida casi no se escribe hasta el final; el de opencode sí)
  [ -z "$(find "$@" "$HOME/.local/share/opencode/log" -type f -newermt "-$MIN min" -print -quit 2>/dev/null)" ]; }
lanza() {    # nombre intento modelo [brief extra]
  local n=$1 k=$2 m=$3 extra=$4; source "$COLA/$n.tarea"
  { [ -n "$extra" ] && echo "$extra"; cat "$BRIEF"; } > "$COLA/logs/$n.brief$k.md"
  setsid nohup bash -c "cd '$WT' && timeout 1500 '$OC' run -m '$m' \"\$(cat '$COLA/logs/$n.brief$k.md')\" >> '$COLA/logs/$n.log' 2>&1; echo \"rc=\$?\" >> '$COLA/logs/$n.log'" < /dev/null > /dev/null 2>&1 &
  echo "$n $k $m $!" > "$EST"; anota "lanzo $n (intento $k, $m, pid $!)"
}

if [ -f "$EST" ]; then
  read -r n k m pid < "$EST"
  if kill -0 "$pid" 2>/dev/null; then
    quieto "$COLA/logs/$n.log" || exit 0
    pkill -s "$pid"; sleep 5; pkill -9 -s "$pid"     # toda la sesión: `timeout` arma su propio grupo de procesos
    source "$COLA/$n.tarea"
    (cd "$WT" && git ls-files -m -o --exclude-standard | tar -czf "$COLA/logs/$n.respaldo$k.tgz" -T - 2>/dev/null)
    if [ "$k" -ge 2 ]; then
      anota "TRABADA $n: 2 intentos sin avanzar; pasa a trabadas/ (respaldos en logs/)"
      mv "$COLA/$n.tarea" "$COLA/trabadas/"; rm -f "$EST"; exit 0
    fi
    sig=${MODELOS[0]}
    for i in "${!MODELOS[@]}"; do [ "${MODELOS[$i]}" = "$m" ] && sig=${MODELOS[$(( (i + 1) % ${#MODELOS[@]} ))]}; done
    anota "trabada $n (intento $k, $m): relanzo con $sig"
    lanza "$n" $((k + 1)) "$sig" "Ya hay trabajo hecho en $WT: leé \`git diff\` del worktree y las últimas 40 líneas de $COLA/logs/$n.log; seguí desde ahí, no rehagas."
    exit 0
  fi
  anota "fin $n ($(tail -1 "$COLA/logs/$n.log" 2>/dev/null))"; mv "$COLA/$n.tarea" "$COLA/hechos/" 2>/dev/null; rm -f "$EST"
fi

corridas=$(pgrep -f "^[^ ]*/opencode run " || true)   # solo el binario: un comando que nombre «opencode run» no cuenta
if [ -n "$corridas" ]; then
  quieto "$LOGS" && { anota "trabada fuera de la cola: mato $(echo $corridas)"; kill $corridas 2>/dev/null; }
  exit 0
fi
pgrep -f "lanzador.sh" > /dev/null && exit 0          # un lanzador de E9 entre dos pasos (p. ej. corriendo los tests)

siguiente=$(ls "$COLA"/*.tarea 2>/dev/null | head -1)
if [ -z "$siguiente" ]; then
  [ "$(tail -1 "$LOG" 2>/dev/null | cut -d' ' -f3-)" = "cola vacía" ] || anota "cola vacía"
  exit 0
fi
n=$(basename "$siguiente" .tarea); MODELO=; source "$siguiente"
lanza "$n" 1 "${MODELO:-${MODELOS[0]}}"
