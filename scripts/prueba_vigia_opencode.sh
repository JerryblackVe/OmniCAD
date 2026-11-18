#!/usr/bin/env bash
# Prueba en seco del vigía con un opencode falso. Sale 0 si todo pasa.
set -u; T=${PRUEBA_T:-$(mktemp -d)}; export VIGIA_COLA=$T/cola VIGIA_LOGS=$T/e9 VIGIA_OC=$T/oc VIGIA_CB=$T/oc VIGIA_LANZ=lanzador_de_prueba_inexistente VIGIA_MAX=1 VIGIA_VERIF=true
mkdir -p $T/cola $T/e9 $T/wt; (cd $T/wt && git init -q)
cat > $T/oc <<'EOF'
#!/usr/bin/env bash
# args: run -m MODELO [--variant V] PROMPT
m=$(echo "$*" | grep -oE -- "(-m|--model) [^ ]+" | head -1 | cut -d" " -f2); p="${@: -1}"; echo "args: $*" >> $(dirname $0)/llamadas
case "$p" in *"Respondé solo"*) [[ "$m" == *deepseek* && -f $(dirname $0)/ds_muerto ]] || echo OK; exit 0;; esac
[[ "$m" == *glm* ]] && { echo "Error: status 429 rate limit"; exit 1; }
echo "trabajo hecho"; exit 0
EOF
chmod +x $T/oc
printf 'WT=%s\nBRIEF=%s\nVARIANTE=high\n' $T/wt $T/brief > $T/cola/01_x.tarea; echo MODELO=opencode/glm-5.3-flash-free >> $T/cola/01_x.tarea; echo "hacé X" > $T/brief
V=$(dirname "$0")/vigia_opencode.sh; ok=1
vuelta() { bash "$V"; sleep 2; }
vuelta; grep -q "lanzo 01_x (intento 1, opencode/glm" $T/cola/vigia.log || { echo "FALLA 1: no lanzó con GLM"; ok=0; }
grep -q -- "--variant high" $T/llamadas || { echo "FALLA 1b: no pasó el esfuerzo"; ok=0; }
vuelta; grep -q "relanzo con opencode/deepseek" $T/cola/vigia.log || { echo "FALLA 2: no rotó a DeepSeek tras 429"; ok=0; }
vuelta; vuelta; grep -q "fin 01_x (rc=0)" $T/cola/vigia.log && [ -f $T/cola/hechos/01_x.tarea ] || { echo "FALLA 3: no cerró bien"; ok=0; }
grep -q "seguí desde ahí" $T/cola/logs/01_x.brief2.md || { echo "FALLA 4: el reintento no retoma"; ok=0; }
# todos fallan: GLM con 429, DeepSeek no responde, MiniMax OK pero lo forzamos a fallar con rc
printf 'WT=%s\nBRIEF=%s\n' $T/wt $T/brief > $T/cola/02_y.tarea; echo MODELO=opencode/glm-5.3-flash-free >> $T/cola/02_y.tarea; touch $T/ds_muerto
sed -i 's/echo "trabajo hecho"; exit 0/echo "rate limit"; exit 1/' $T/oc
for i in 1 2 3 4 5 6 7 8 9; do vuelta; done
grep -q "sin modelo libre para 02_y" $T/cola/vigia.log && [ -f $T/cola/02_y.tarea ] && ! grep -q "TRABADA 02_y" $T/cola/vigia.log || { echo "FALLA 5: sin modelo libre no volvió a la cola (o fue a trabadas)"; ok=0; }
grep -q "relanzo con nvidia/minimaxai" $T/cola/vigia.log && grep -q "relanzo con cb:" $T/cola/vigia.log || { echo "FALLA 6: no salteó al que no responde"; ok=0; }
grep -q "seguí desde ahí" $T/cola/logs/02_y.brief1.md 2>/dev/null || [ -z "$(git -C $T/wt status --porcelain)" ] || { echo "FALLA 6b: al volver de la cola no retoma"; ok=0; }
for i in $(seq 1 30); do vuelta; [ -f $T/cola/trabadas/02_y.tarea ] && break; done
grep -q "TRABADA 02_y (.*sin modelo libre 4 veces" $T/cola/vigia.log || { echo "FALLA 5c: no cortó a la 4.ª vuelta a la cola"; ok=0; }
# falla de verdad (rc=1 sin 429) con 2 modelos distintos: a trabadas/
for i in 1 2 3; do while pgrep -f "$T/oc" > /dev/null; do sleep 1; done; bash "$V"; done; rm -f $T/cola/02_y.tarea $T/cola/corriendo/02_y $T/cola/trabadas/02_y.tarea
sed -i 's/echo "rate limit"; exit 1/echo "rompí algo"; exit 1/' $T/oc
printf 'WT=%s\nBRIEF=%s\nMODELO=cb:hy3\n' $T/wt $T/brief > $T/cola/02_z.tarea
for i in 1 2 3 4 5; do vuelta; done
grep -q "TRABADA 02_z (.*falló de verdad con 2 modelos" $T/cola/vigia.log && [ -f $T/cola/trabadas/02_z.tarea ] || { echo "FALLA 5b: falla real con 2 modelos no fue a trabadas"; ok=0; }
sed -i 's/echo "rompí algo"; exit 1/echo "rate limit"; exit 1/' $T/oc
# en paralelo: 2 tareas lentas, 2 corridas a la vez y de modelos distintos
rm -f $T/ds_muerto; sed -i 's/echo "rate limit"; exit 1/sleep 8; echo listo; exit 0/' $T/oc
for x in 03_a 04_b; do printf 'WT=%s
BRIEF=%s
' $T/wt $T/brief > $T/cola/$x.tarea; done
VIGIA_MAX=2 bash "$V"; sleep 1
[ "$(ls $T/cola/corriendo | wc -l)" = 2 ] || { echo "FALLA 7: no lanzó 2 a la vez"; ok=0; }
sleep 9; VIGIA_MAX=2 bash "$V"; sleep 1; VIGIA_MAX=2 bash "$V"
[ -f $T/cola/hechos/03_a.tarea ] && [ -f $T/cola/hechos/04_b.tarea ] || { echo "FALLA 9: no cerró las 2 en paralelo"; ok=0; }
# reserva: pasa a la cola hasta 8
for x in $(seq 10 19); do printf WT=%snBRIEF=%sn $T/wt $T/brief > $T/cola/reserva/r$x.tarea; done
VIGIA_MAX=0 bash "$V"
[ "$(ls $T/cola/*.tarea | wc -l)" = 8 ] || { echo "FALLA 10: la reserva no llenó la cola a 8"; ok=0; }
# verificación en rojo: se relanza con el error en el brief
printf 'WT=%s\nBRIEF=%s\nMODELO=cb:hy3\n' $T/wt $T/brief > $T/cola/05_v.tarea; rm -f $T/cola/reserva/*.tarea $T/cola/[0-9r]*.tarea.x
for x in $T/cola/*.tarea; do [ "$x" = $T/cola/05_v.tarea ] || mv $x $T/cola/hechos/; done
VIGIA_VERIF="echo ruff dice error; false" bash "$V"; sleep 9; VIGIA_VERIF="echo ruff dice error; false" bash "$V"; sleep 2; VIGIA_VERIF="echo ruff dice error; false" bash "$V"
grep -q "verificación en rojo" $T/cola/vigia.log && grep -q "ruff dice error" $T/cola/logs/05_v.brief2.md || { echo "FALLA 11: el rojo de la verificación no se relanza con el error"; ok=0; }
# B-632: una verificación colgada (sin CPU ni salida) se corta con el tope de quietud y se relanza
printf 'WT=%s\nBRIEF=%s\nMODELO=cb:hy3\n' $T/wt $T/brief > $T/cola/06_c.tarea; mv $T/cola/05_v.tarea $T/cola/hechos/ 2>/dev/null; rm -f $T/cola/corriendo/05_v
export VIGIA_VERIF="sleep 300" VIGIA_MIN=0
bash "$V"; sleep 9; bash "$V"; sleep 1; bash "$V"; bash "$V"
grep -q "falla 06_c (intento 1, cb:hy3: verificación trabada" $T/cola/vigia.log || { echo "FALLA 12: la verificación colgada no se cortó"; ok=0; }
pgrep -f "^sleep 300$" > /dev/null && { echo "FALLA 13: quedó viva la verificación colgada"; ok=0; pkill -f "^sleep 300$"; }
unset VIGIA_VERIF VIGIA_MIN
# sin worktree: a trabadas/ con aviso, sin rotar modelos en vano; latido al día
printf 'WT=%s\nBRIEF=%s\n' $T/no_existe $T/brief > $T/cola/07_w.tarea; VIGIA_MAX=5 bash "$V"
[ -f $T/cola/trabadas/07_w.tarea ] && grep -q "07_w: falta el worktree" $T/cola/avisos.txt || { echo "FALLA 14: tarea sin worktree no pasó a trabadas con aviso"; ok=0; }
[ -n "$(find $T/cola/latido -newermt '-1 min')" ] || { echo "FALLA 15: sin latido"; ok=0; }
# una vuelta a la vez: con el candado tomado, la segunda no hace nada
( exec 9> $T/cola/.vigia.lock; flock 9; sleep 3 ) & sleep 1; bash "$V"; wait
grep -q "la vuelta anterior sigue corriendo" $T/cola/vigia.log || { echo "FALLA 16: dos vueltas a la vez"; ok=0; }
[ $ok = 1 ] && echo "PRUEBA OK" || { cat $T/cola/vigia.log; exit 1; }
rm -rf $T
