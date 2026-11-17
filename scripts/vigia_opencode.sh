#!/usr/bin/env bash
# Vigía de OpenCode sin modelo (crontab de la VPS, cada 20 min; Gerardo, 2026-11-17). Gasto cero de Claude.
# Cola: archivos `$COLA/NN_nombre.tarea` (orden alfabético) con líneas que se leen con `source`:
#   WT=/home/mosos/OmniCAD-<ID>   BRIEF=/ruta/al/brief.md   MODELO=opencode/glm-5.3-flash-free (opcional)
#   VARIANTE=high (opcional: esfuerzo de `opencode run --variant`; sin ella, el del modelo)
# - Al terminar bien, se verifica sola (scripts/verif_tarea.sh en su worktree, sin modelo): verde -> hechos/ (lista para
#   integrar); rojo -> se relanza con el error y el modelo siguiente.
# - Corre hasta $MAX corridas a la vez (tope y reparto: «Protocolo de OpenCode» en docs/coordinacion.md).
#   Salida en $COLA/logs/<nombre>.log; al terminar bien la tarea pasa a hechos/.
# - Falla (trabada 20 min sin escribir, límite/429/cupo, o termina con error): respaldo (tgz) y relanza la MISMA
#   tarea con el siguiente modelo que responda (orden del Protocolo de OpenCode) y un brief que sigue desde ahí.
#   Tras probar todos los de MODELOS, pasa a trabadas/ y sigue la cola.
#   shortcut: retoma con brief (git diff + log), no con `opencode run --session`: el id de sesión no queda a mano.
# - Corridas que no son de la cola (los lanzadores de E9): si se traban, solo se matan; el lanzador sigue solo.
# Línea de crontab: */20 * * * * bash /home/mosos/OmniCAD/scripts/vigia_opencode.sh
COLA=${VIGIA_COLA:-$HOME/coordinador/opencode_cola}
LOGS=${VIGIA_LOGS:-$HOME/coordinador/e9prompts}
OC=${VIGIA_OC:-$HOME/.opencode/bin/opencode}
MIN=${VIGIA_MIN:-20}
CB=${VIGIA_CB:-$HOME/.local/cb/codebuddy}   # CodeBuddy (Node 22 propio); sus modelos van con «cb:»
# Orden por la prueba de carga del 17/11: CodeBuddy contesta en ~8 s y aguanta 4 a la vez; MiniMax ~3; GLM y DeepSeek gratis de OpenCode no contestaron.
MODELOS=(cb:deepseek-v4.1-flash cb:hy3 nvidia/minimaxai/minimax-m3.1-flash opencode/glm-5.3-flash-free opencode/deepseek-v4.1-flash-free)
CORTE='(status|code|error)[^0-9]{0,12}429|rate.?limit|quota|insufficient.?(balance|credit|quota)|overloaded|ModelNotFound|^429 |credits.?exhausted|frequency.?limit'
PY=${VIGIA_PY:-$HOME/OmniCAD/clon/.venv/bin/python}
VERIF=${VIGIA_VERIF:-bash $HOME/OmniCAD/scripts/verif_tarea.sh}   # rápida: ruff + tests que importan directo lo tocado
MAX=${VIGIA_MAX:-6}   # hasta 2 por modelo de CodeBuddy y 1 por modelo de OpenCode
LOG=$COLA/vigia.log; EST=$COLA/corriendo   # un archivo por corrida: «nombre intento modelo pid»
mkdir -p "$COLA/hechos" "$COLA/trabadas" "$COLA/logs" "$COLA/reserva" "$EST"
anota() { echo "$(date -u '+%F %T') $*" >> "$LOG"; }
# Avisos para el coordinador y el chat maestro (el vigía no tiene modelo: los leen en su vigilancia de 2 h).
avisa() { anota "AVISO $*"; echo "$(date -u '+%F %T') $*" >> "$COLA/avisos.txt"; }
# Una vuelta a la vez: si la anterior sigue (p. ej. probando modelos), esta no lanza nada doble. flock se suelta solo.
exec 9> "$COLA/.vigia.lock"; flock -n 9 || { anota "la vuelta anterior sigue corriendo: salto esta"; exit 0; }
touch "$COLA/latido"   # si tiene más de 1 vuelta, el vigía no corre (crontab o máquina): lo mira la vigilancia de 2 h
# Huérfanos: un pytest sin padre (su sesión murió) que pasa de 45 min no lo corta nadie más (3 h el 17/11).
for p in $(pgrep -f "python -m pytest"); do
  [ "$(ps -o ppid= -p "$p" | tr -d ' ')" = 1 ] && [ "$(ps -o etimes= -p "$p" | tr -d ' ')" -gt 2700 ] || continue
  kill "$p" 2>/dev/null && avisa "pytest huérfano cortado (pid $p, más de 45 min)"; done
quieto() {   # nada escribió en $MIN minutos (el log de la corrida casi no se escribe hasta el final; el de opencode sí)
  [ -z "$(find "$@" "$HOME/.local/share/opencode/log" -type f -newermt "-$MIN min" -print -quit 2>/dev/null)" ]; }
cpu() { ps -o times= -s "$1" 2>/dev/null | awk '{s+=$1} END{print s+0}'; }   # segundos de CPU de la sesión (setsid) del pid
ultimo() { awk '/^=== intento /{b=""} {b=b $0 "
"} END{printf "%s", b}' "$COLA/logs/$1.log" 2>/dev/null | tail -20; }  # solo el intento actual
usado() {   # el modelo ya está en su tope de corridas a la vez (CodeBuddy 2, OpenCode 1; cuenta también el lanzador de E9)
  local c tope=1; [ "${1#cb:}" != "$1" ] && tope=2
  c=$(grep -ls " $1 " "$EST"/* | wc -l); pgrep -f -- "^$OC run -m $1 " > /dev/null && c=$((c + 1))
  [ "$c" -ge "$tope" ]; }   # lo corre alguien (la cola o un lanzador de E9)
cmd() { case $1 in cb:*) echo "$CB -p -y --model ${1#cb:}";; *) echo "$OC run -m $1";; esac; }   # modelo -> comando
responde() { timeout 150 $(cmd "$1") "Respondé solo la palabra OK" 2>/dev/null | grep -qi OK; }
siguiente_modelo() {   # modelo_actual -> el próximo de la lista que responde (o vacío)
  local i j m
  for i in "${!MODELOS[@]}"; do [ "${MODELOS[$i]}" = "$1" ] && break; done
  for j in $(seq 1 ${#MODELOS[@]}); do m=${MODELOS[$(( (i + j) % ${#MODELOS[@]} ))]}
    usado "$m" && [ "$m" != "$1" ] && continue   # otro modelo que el de la corrida de al lado
    responde "$m" && { echo "$m"; return; }; done; }
lanza() {    # nombre intento modelo [brief extra]
  local n=$1 k=$2 m=$3 extra=$4 v=; VARIANTE=; source "$COLA/$n.tarea"
  [ -n "$VARIANTE" ] && [ "${m#cb:}" = "$m" ] && v="--variant $VARIANTE"   # CodeBuddy no tiene variante
  { [ -n "$extra" ] && echo "$extra"; cat "$BRIEF"; } > "$COLA/logs/$n.brief$k.md"
  echo "=== intento $k ($m)" >> "$COLA/logs/$n.log"
  setsid nohup bash -c "cd '$WT' && timeout 2700 $(cmd "$m") $v \"\$(cat '$COLA/logs/$n.brief$k.md')\" >> '$COLA/logs/$n.log' 2>&1; echo \"rc=\$?\" >> '$COLA/logs/$n.log'" < /dev/null > /dev/null 2>&1 9>&- &
  echo "$n $k $m $!" > "$EST/$n"; anota "lanzo $n (intento $k, $m, esfuerzo ${VARIANTE:-del modelo}, pid $!)"
}
verifica() {   # nombre intento modelo: corre la verificación aparte y la anota como corrida «VERIF:<modelo>»
  local n=$1; source "$COLA/$n.tarea"
  setsid nohup bash -c "cd '$WT' && { $VERIF; } > '$COLA/logs/$n.verif' 2>&1; echo \"rc=\$?\" >> '$COLA/logs/$n.verif'" < /dev/null > /dev/null 2>&1 9>&- &
  echo "$n $2 VERIF:$3 $!" > "$EST/$n"; anota "verifico $n (verif_tarea.sh, pid $!)"
}
reintenta() {   # nombre intento modelo motivo
  local n=$1 k=$2 m=$3 sig; source "$COLA/$n.tarea"
  (cd "$WT" && git ls-files -m -o --exclude-standard | tar -czf "$COLA/logs/$n.respaldo$k.tgz" -T - 2>/dev/null)
  sig=$( [ "$k" -lt "${#MODELOS[@]}" ] && siguiente_modelo "$m" )
  if [ -z "$sig" ]; then
    avisa "TRABADA $n ($4): sin más modelos que prueben; pasa a trabadas/ (respaldos en logs/)"
    mv "$COLA/$n.tarea" "$COLA/trabadas/"; rm -f "$EST/$n"; return
  fi
  anota "falla $n (intento $k, $m: $4): relanzo con $sig"
  lanza "$n" $((k + 1)) "$sig" "Ya hay trabajo hecho en $WT: leé \`git diff\` del worktree y las últimas 40 líneas de $COLA/logs/$n.log; seguí desde ahí, no rehagas. Motivo del reintento: $4"
}

for f in "$EST"/*; do
  [ -f "$f" ] || continue
  read -r n k m pid < "$f"
  if [ "${m#VERIF:}" != "$m" ]; then   # una verificación: mismo tope de quietud ($MIN) que una corrida (B-632)
    q="$COLA/logs/$n.cpu"
    if kill -0 "$pid" 2>/dev/null; then   # viva: se corta si en $MIN min no usó CPU ni escribió su salida
      c=$(cpu "$pid"); [ "$c" != "$(cat "$q" 2>/dev/null)" ] && { echo "$c" > "$q"; continue; }
      [ $(( $(date +%s) - $(stat -c %Y "$q") )) -lt $(( (MIN - 1) * 60 )) ] && continue
      [ -n "$(find "$COLA/logs/$n.verif" -newermt "-$MIN min" 2>/dev/null)" ] && continue
      kill -- -"$pid" 2>/dev/null; sleep 5; kill -9 -- -"$pid" 2>/dev/null; rm -f "$q"
      reintenta "$n" "$k" "${m#VERIF:}" "verificación trabada: $MIN min sin CPU ni escribir"; continue
    fi
    rm -f "$q"; m=${m#VERIF:}; fin=$(tail -1 "$COLA/logs/$n.verif" 2>/dev/null)
    if [ "$fin" = "rc=0" ]; then anota "VERDE $n: lista para integrar"; mv "$COLA/$n.tarea" "$COLA/hechos/"; rm -f "$f"
    else reintenta "$n" "$k" "$m" "verificación en rojo; arreglá esto: $(tail -40 "$COLA/logs/$n.verif" | tr '\n' ' ' | cut -c1-1500)"; fi
    continue
  fi
  if kill -0 "$pid" 2>/dev/null; then
    if ultimo "$n" | grep -qiE "$CORTE"; then motivo="límite o cupo del modelo"
    elif source "$COLA/$n.tarea"; quieto "$COLA/logs/$n.log" "$HOME/.codebuddy/projects/$(echo "$WT" | tr / -)"; then motivo="$MIN min sin escribir"
    else continue; fi
    kill -- -"$pid" 2>/dev/null; sleep 5; kill -9 -- -"$pid" 2>/dev/null
    reintenta "$n" "$k" "$m" "$motivo"; continue
  fi
  fin=$(tail -1 "$COLA/logs/$n.log" 2>/dev/null)
  if [ "$fin" != "rc=0" ] || ultimo "$n" | grep -qiE "$CORTE"; then
    reintenta "$n" "$k" "$m" "terminó con error ($fin)"; continue
  fi
  anota "fin $n ($fin)"; verifica "$n" "$k" "$m"
done

# Corridas ajenas a la cola (los lanzadores de E9): si se traban, solo se matan; el lanzador sigue solo.
mios=$(cat "$EST"/* 2>/dev/null | awk '{print $4}')
ajenas=$(for p in $(pgrep -f "^$OC run "); do g=$(ps -o pgid= -p "$p" | tr -d ' '); echo "$mios" | grep -qx "$g" || echo "$p"; done)
[ -n "$ajenas" ] && quieto "$LOGS" && { anota "trabada fuera de la cola: mato $(echo $ajenas)"; kill $ajenas 2>/dev/null; ajenas=; }

# Reserva: el coordinador deja muchas tareas en reserva/ y acá se pasan a la cola hasta tener 8 (no depende de ninguna sesión).
for t in $(ls "$COLA"/reserva/*.tarea 2>/dev/null); do
  [ "$(ls "$COLA"/*.tarea 2>/dev/null | wc -l)" -ge 8 ] && break
  mv "$t" "$COLA/" && anota "de reserva a la cola: $(basename "$t")"
done
[ "$(ls "$COLA"/reserva/*.tarea 2>/dev/null | wc -l)" -lt 8 ] && avisa "reserva con menos de 8 tareas"
usadas=$(ls "$EST" | wc -l)
{ [ -n "$ajenas" ] || pgrep -f "${VIGIA_LANZ:-lanzador.sh}" > /dev/null; } && usadas=$((usadas + 1))
while [ "$usadas" -lt "$MAX" ]; do
  siguiente=$(for t in "$COLA"/*.tarea; do [ -f "$t" ] && [ ! -f "$EST/$(basename "$t" .tarea)" ] && echo "$t"; done | head -1)
  if [ -z "$siguiente" ]; then
    [ "$(tail -1 "$LOG" 2>/dev/null | cut -d' ' -f3-)" = "AVISO cola vacía" ] || avisa "cola vacía"
    exit 0
  fi
  n=$(basename "$siguiente" .tarea); MODELO=; WT=; BRIEF=; source "$siguiente"
  if [ ! -d "$WT" ] || [ ! -f "$BRIEF" ]; then   # sin worktree o sin brief no hay corrida posible: no se rota en vano
    avisa "TRABADA $n: falta el worktree o el brief ($WT, $BRIEF); pasa a trabadas/"; mv "$siguiente" "$COLA/trabadas/"; continue
  fi
  m=${MODELO:-${MODELOS[0]}}
  usado "$m" && m=$(siguiente_modelo "$m")   # el primer intento no se prueba antes: los gratis tardan 1–2 min en contestar; si falla, lo agarra la vuelta siguiente
  [ -z "$m" ] && { avisa "ningún modelo libre responde: espero a la próxima vuelta"; exit 0; }
  lanza "$n" 1 "$m"; usadas=$((usadas + 1))
done
