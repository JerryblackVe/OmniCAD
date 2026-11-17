#!/usr/bin/env bash
# Prueba en seco del vigía con un opencode falso. Sale 0 si todo pasa.
set -u; T=$(mktemp -d); export VIGIA_COLA=$T/cola VIGIA_LOGS=$T/e9 VIGIA_OC=$T/oc VIGIA_CB=$T/oc VIGIA_LANZ=lanzador_de_prueba_inexistente VIGIA_MAX=1
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
vuelta; grep -q "fin 01_x (rc=0)" $T/cola/vigia.log && [ -f $T/cola/hechos/01_x.tarea ] || { echo "FALLA 3: no cerró bien"; ok=0; }
grep -q "seguí desde ahí" $T/cola/logs/01_x.brief2.md || { echo "FALLA 4: el reintento no retoma"; ok=0; }
# todos fallan: GLM con 429, DeepSeek no responde, MiniMax OK pero lo forzamos a fallar con rc
printf 'WT=%s\nBRIEF=%s\n' $T/wt $T/brief > $T/cola/02_y.tarea; echo MODELO=opencode/glm-5.3-flash-free >> $T/cola/02_y.tarea; touch $T/ds_muerto
sed -i 's/echo "trabajo hecho"; exit 0/echo "rate limit"; exit 1/' $T/oc
for i in 1 2 3 4 5 6 7; do vuelta; done
grep -q "TRABADA 02_y" $T/cola/vigia.log && [ -f $T/cola/trabadas/02_y.tarea ] || { echo "FALLA 5: no la pasó a trabadas"; ok=0; }
grep -q "relanzo con nvidia/minimaxai" $T/cola/vigia.log && grep -q "relanzo con cb:" $T/cola/vigia.log || { echo "FALLA 6: no salteó al que no responde"; ok=0; }
# en paralelo: 2 tareas lentas, 2 corridas a la vez y de modelos distintos
rm -f $T/ds_muerto; sed -i 's/echo "rate limit"; exit 1/sleep 8; echo listo; exit 0/' $T/oc
for x in 03_a 04_b; do printf 'WT=%s
BRIEF=%s
' $T/wt $T/brief > $T/cola/$x.tarea; done
VIGIA_MAX=2 bash "$V"; sleep 1
[ "$(ls $T/cola/corriendo | wc -l)" = 2 ] || { echo "FALLA 7: no lanzó 2 a la vez"; ok=0; }
sleep 9; VIGIA_MAX=2 bash "$V"
[ -f $T/cola/hechos/03_a.tarea ] && [ -f $T/cola/hechos/04_b.tarea ] || { echo "FALLA 9: no cerró las 2 en paralelo"; ok=0; }
# reserva: pasa a la cola hasta 8
for x in $(seq 10 19); do printf WT=%snBRIEF=%sn $T/wt $T/brief > $T/cola/reserva/r$x.tarea; done
VIGIA_MAX=0 bash "$V"
[ "$(ls $T/cola/*.tarea | wc -l)" = 8 ] || { echo "FALLA 10: la reserva no llenó la cola a 8"; ok=0; }
[ $ok = 1 ] && echo "PRUEBA OK" || { cat $T/cola/vigia.log; exit 1; }
rm -rf $T
