#!/usr/bin/env bash
# Vigía de OpenCode sin modelo (crontab de la VPS, cada 20 min; Gerardo, 2026-11-17). Gasto cero de Claude.
# Cola: archivos `$COLA/NN_nombre.tarea` (orden alfabético) con líneas que se leen con `source`:
#   WT=/home/mosos/OmniCAD-<ID>   BRIEF=/ruta/al/brief.md   MODELO=opencode/glm-5.3-flash-free (opcional)
#   VARIANTE=high (opcional: esfuerzo de `opencode run --variant`; sin ella, el del modelo)
# - Corre una tarea a la vez (salida en $COLA/logs/<nombre>.log). Al terminar bien pasa a hechos/.
# - Falla (trabada 20 min sin escribir, límite/429/cupo, o termina con error): respaldo (tgz) y relanza la MISMA
#   tarea con el siguiente modelo que responda (orden del Protocolo de OpenCode) y un brief que sigue desde ahí.
#   Tras probar los 3 modelos, pasa a trabadas/ y sigue la cola.
#   shortcut: retoma con brief (git diff + log), no con `opencode run --session`: el id de sesión no queda a mano.
# - Corridas que no son de la cola (los lanzadores de E9): si se traban, solo se matan; el lanzador sigue solo.
# Línea de crontab: */20 * * * * bash /home/mosos/OmniCAD/scripts/vigia_opencode.sh
COLA=${VIGIA_COLA:-$HOME/coordinador/opencode_cola}
LOGS=${VIGIA_LOGS:-$HOME/coordinador/e9prompts}
OC=${VIGIA_OC:-$HOME/.opencode/bin/opencode}
MIN=${VIGIA_MIN:-20}
MODELOS=(opencode/glm-5.3-flash-free opencode/deepseek-v4.1-flash-free nvidia/minimaxai/minimax-m3.1-flash)
CORTE='(status|code|error)[^0-9]{0,12}429|rate.?limit|quota|insufficient.?(balance|credit|quota)|overloaded|ModelNotFound'
LOG=$COLA/vigia.log; EST=$COLA/actual
mkdir -p "$COLA/hechos" "$COLA/trabadas" "$COLA/logs"
anota() { echo "$(date -u '+%F %T') $*" >> "$LOG"; }
quieto() {   # nada escribió en $MIN minutos (el log de la corrida casi no se escribe hasta el final; el de opencode sí)
  [ -z "$(find "$@" "$HOME/.local/share/opencode/log" -type f -newermt "-$MIN min" -print -quit 2>/dev/null)" ]; }
ultimo() { awk '/^=== intento /{b=""} {b=b $0 "
"} END{printf "%s", b}' "$COLA/logs/$1.log" 2>/dev/null | tail -20; }  # solo el intento actual
responde() { timeout 90 "$OC" run -m "$1" "Respondé solo la palabra OK" 2>/dev/null | grep -qi OK; }
siguiente_modelo() {   # modelo_actual -> el próximo de la lista que responde (o vacío)
  local i j m
  for i in "${!MODELOS[@]}"; do [ "${MODELOS[$i]}" = "$1" ] && break; done
  for j in 1 2 3; do m=${MODELOS[$(( (i + j) % ${#MODELOS[@]} ))]}; responde "$m" && { echo "$m"; return; }; done; }
lanza() {    # nombre intento modelo [brief extra]
  local n=$1 k=$2 m=$3 extra=$4 v=; VARIANTE=; source "$COLA/$n.tarea"
  [ -n "$VARIANTE" ] && v="--variant $VARIANTE"
  { [ -n "$extra" ] && echo "$extra"; cat "$BRIEF"; } > "$COLA/logs/$n.brief$k.md"
  echo "=== intento $k ($m)" >> "$COLA/logs/$n.log"
  setsid nohup bash -c "cd '$WT' && timeout 1500 '$OC' run -m '$m' $v \"\$(cat '$COLA/logs/$n.brief$k.md')\" >> '$COLA/logs/$n.log' 2>&1; echo \"rc=\$?\" >> '$COLA/logs/$n.log'" < /dev/null > /dev/null 2>&1 &
  echo "$n $k $m $!" > "$EST"; anota "lanzo $n (intento $k, $m, esfuerzo ${VARIANTE:-del modelo}, pid $!)"
}
reintenta() {   # nombre intento modelo motivo
  local n=$1 k=$2 m=$3 sig; source "$COLA/$n.tarea"
  (cd "$WT" && git ls-files -m -o --exclude-standard | tar -czf "$COLA/logs/$n.respaldo$k.tgz" -T - 2>/dev/null)
  sig=$( [ "$k" -lt "${#MODELOS[@]}" ] && siguiente_modelo "$m" )
  if [ -z "$sig" ]; then
    anota "TRABADA $n ($4): sin más modelos que prueben; pasa a trabadas/ (respaldos en logs/)"
    mv "$COLA/$n.tarea" "$COLA/trabadas/"; rm -f "$EST"; return
  fi
  anota "falla $n (intento $k, $m: $4): relanzo con $sig"
  lanza "$n" $((k + 1)) "$sig" "Ya hay trabajo hecho en $WT: leé \`git diff\` del worktree y las últimas 40 líneas de $COLA/logs/$n.log; seguí desde ahí, no rehagas."
}

if [ -f "$EST" ]; then
  read -r n k m pid < "$EST"
  if kill -0 "$pid" 2>/dev/null; then
    if ultimo "$n" | grep -qiE "$CORTE"; then motivo="límite o cupo del modelo"
    elif quieto "$COLA/logs/$n.log"; then motivo="$MIN min sin escribir"
    else exit 0; fi
    kill -- -"$pid" 2>/dev/null; sleep 5; kill -9 -- -"$pid" 2>/dev/null
    reintenta "$n" "$k" "$m" "$motivo"; exit 0
  fi
  fin=$(tail -1 "$COLA/logs/$n.log" 2>/dev/null)
  if [ "$fin" != "rc=0" ] || ultimo "$n" | grep -qiE "$CORTE"; then
    reintenta "$n" "$k" "$m" "terminó con error ($fin)"; exit 0
  fi
  anota "fin $n ($fin)"; mv "$COLA/$n.tarea" "$COLA/hechos/" 2>/dev/null; rm -f "$EST"
fi

corridas=$(pgrep -f "^$OC run " || true)   # solo el binario: un comando que nombre «opencode run» no cuenta
if [ -n "$corridas" ]; then
  quieto "$LOGS" && { anota "trabada fuera de la cola: mato $(echo $corridas)"; kill $corridas 2>/dev/null; }
  exit 0
fi
pgrep -f "${VIGIA_LANZ:-lanzador.sh}" > /dev/null && exit 0         # un lanzador de E9 entre dos pasos (p. ej. corriendo los tests)

siguiente=$(ls "$COLA"/*.tarea 2>/dev/null | head -1)
if [ -z "$siguiente" ]; then
  [ "$(tail -1 "$LOG" 2>/dev/null | cut -d' ' -f3-)" = "cola vacía" ] || anota "cola vacía"
  exit 0
fi
n=$(basename "$siguiente" .tarea); MODELO=; source "$siguiente"
m=${MODELO:-${MODELOS[0]}}
responde "$m" || m=$(siguiente_modelo "$m")
[ -z "$m" ] && { anota "ningún modelo responde: espero a la próxima vuelta"; exit 0; }
lanza "$n" 1 "$m"
