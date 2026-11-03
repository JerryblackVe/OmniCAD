# Tarea corta para Qoder

Una sola tarea, la primera parte de PLA-9 (Eliminar caras en SÓLIDO › Simplificar), para probar Qoder CLI. Corre junto
con otros agentes (H-59 en el deshacer, B4 en Vectorizar): no tocan los mismos archivos, ni `docs/seguimiento/` ni
`PROJECT_LOG.md` (eso lo hace el coordinador). Al terminar se borran este documento y sus dos filas de índice
(`docs/README.md` y `docs/seguimiento/README.md`).

## Prompt para el agente

Entregado el 2026-11-03. Modelo sugerido: Ultimate en Qoder CLI, esfuerzo alto. Es la prueba Pro de 300 créditos (×2 por pedido).

```text
ARRIBA DE TODO, ANTES DE TOCAR NADA
Invocá las skills fable-method, ponytail, plan-then-do, tool-calling-guard y verify-before-commit. Si no aparecen como
skills, leé su SKILL.md en C:\Users\mosos\.claude\skills\<nombre>\ y seguilo.

OBJETIVO
PLA-9, primera parte: el comando «Eliminar caras» en SÓLIDO › MODIFICAR › Simplificar, como el «Remove Faces» de Fusion.

CONTEXTO
- Repo D:\PROGRAMA, rama main. Leé AGENTS.md (receta B: comando de la interfaz). Trabajá desde clon/ con clon/.venv.
- Otros agentes trabajan en la misma carpeta (timeline/documento.py, ui/dialogo_parametros.py,
  io_archivos/vectorizar.py, ui/comandos/insertar.py, api/herramientas_vectores.py). Tocá solo los archivos de esta
  tarea. Hay cambios sin commitear de otras tareas (por ejemplo en ui/cinta.py, archivos de malla y render): son de
  otros, no los toques ni los reviertas; en cinta.py cambiá solo tu línea.
- Ayuda oficial de Fusion, local: buscá con
  `clon/.venv/Scripts/python.exe scripts/fusion_docs.py buscar remove faces` y leé el artículo con
  `... fusion_docs.py ver "Remove Faces"`. Replicá sus opciones; lo que OmniCAD no pueda hacer, nombralo en el informe.
- Especificación: docs/brechas_extensiones.md, PLA-9.

QUÉ HAY HOY
- La operación ya existe: `OpBorrarCaras` en clon/omnicad/timeline/ops_modificar.py, y la herramienta de API
  `delete_faces` en clon/omnicad/api/herramientas_dividir.py:171. No hace falta tocarlas.
- Hoy solo se llega con Suprimir (tecla Supr) eligiendo caras: clon/omnicad/ui/comandos/modificar.py, clase `Suprimir`.
- clon/omnicad/ui/cinta.py:119: `_sub("Simplificar", [])`, un submenú vacío.

QUÉ TIENE QUE QUEDAR
1. Un comando «Eliminar caras» (receta B) en clon/omnicad/ui/comandos/modificar.py, con `CLASE_OP = OpBorrarCaras`:
   - campo de selección de caras (varias),
   - vista previa,
   - `desde_op` para que el doble clic en el timeline sobre un paso «Borrar caras» abra este diálogo y se pueda editar.
   Antes de escribir, mirá si `POR_TIPO` ya lleva ese tipo de paso a otro comando: un solo comando para editarlo.
2. El submenú Simplificar con el ítem «Eliminar caras» y su clave. Sin clave el ítem queda gris (regla de honestidad).
3. Ícono: función en clon/omnicad/ui/iconos_extra.py y su entrada en el dict de íconos (ver `_fijacion`).
4. Regenerá la lista de claves: `clon/.venv/Scripts/python.exe scripts/claves_comandos.py` (desde la raíz).
5. Suprimir sigue igual.

TEST (en el tests/test_comandos*.py que ya prueba comandos de modificar; buscá con grep «Suprimir» o «borrar_caras»)
- Una caja, elegir una cara (por ejemplo la de arriba de un escalón o un chaflán) y construir: el timeline suma un paso
  Borrar caras y el volumen o la cantidad de caras cambia como se espera (número concreto).
- `desde_op` sobre ese paso devuelve las mismas caras.
- Sin caras elegidas: el mensaje de `exigir`, sin crear paso.
- Los tests nuevos tienen que fallar sin el cambio.

VERIFICACIÓN (desde clon/)
- .venv/Scripts/python.exe -m ruff check .
- .venv/Scripts/python.exe ../scripts/turno.py -- .venv/Scripts/python.exe -m pytest tests/<archivo del test>.py -q -W error
- También, con turno y de a uno: tests/test_claves_comandos.py y tests/test_cobertura_ui_api.py.

REVISIÓN FINAL OBLIGATORIA: ponytail-review
El coordinador rechaza el trabajo si este paso falta o viene en otro formato. No alcanza con decir que la invocaste.
1. Invocá la skill ponytail-review. Si no aparece, leé ENTERO C:\Users\mosos\.claude\skills\ponytail-review\SKILL.md.
2. Revisá tu diff siguiendo esa skill paso por paso: leé los llamadores de lo que cambiaste y buscá casos borde.
3. Pegá el resultado con ESTE formato exacto, en este orden:
   What this change does: <dos o tres frases>
   Luego los hallazgos numerados, en grupos «Must fix», «Should fix», «Nice to have» (saltá los grupos vacíos).
   Cada hallazgo lleva sus cuatro partes: What this is, Problem, Fix, If we skip it.
   Al final: «Verdict: Ship.» o «Verdict: fix N first.», y «Not checked:» si algo no pudiste ver.
4. Si un hallazgo es «Must fix», arreglalo, volvé a correr los tests y decilo.
Formatos como «net: 0 lines», «shrink:» o «delete:» son de OTRA skill y no sirven.

REGLAS
- SÍ: el cambio más chico que resuelve la tarea, en español, con sus tests.
- NO: alias, parámetros o conversiones que nadie pidió. No hagas «Eliminar operaciones» ni «Reemplazar con primitivas».
- NO: commit, push, instalar paquetes ni gastar en APIs.
- NO: tocar docs/seguimiento/, PROJECT_LOG.md, este documento ni los índices de docs/.
- NO: correr la suite completa, la prueba de humo ni cazar.py.
- NO: abrir ni tocar una app de OmniCAD abierta. No abrir Fusion.
- NO: leer privado/, analisis/, archivos .env ni nada fuera del repo, salvo los SKILL.md nombrados.
- NO: borrar archivos fuera de los que vos creaste, ni comandos de git que cambien el historial o descarten cambios
  (reset, checkout de archivos, stash, clean). No dejes archivos sueltos (salidas de pytest, notas) en el repo.
- NO: convertir finales de línea.
- Si no sale después de dos intentos, pará y explicá por qué.

INFORME FINAL
Resuelto o no, qué opciones de Remove Faces de Fusion quedaron y cuáles no, archivos tocados, tests agregados, la salida
real de pytest antes (falla) y después (pasa), ruff, y la revisión ponytail-review con el formato de arriba.
```
