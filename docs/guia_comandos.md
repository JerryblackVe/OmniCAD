# Cómo se agrega un comando de diseño (para los agentes)

Leé estos archivos como ejemplo antes de escribir nada:
- `clon/omnicad/ui/comando.py` — el panel de comando estilo Fusion: campos `Seleccion`, `Expresion`,
  `Opciones`, `Casilla`, `Entero`, `Texto`, `Info`; clase `Comando` (CLAVE, TITULO, ICONO, ATAJO, AYUDA,
  CLASE_OP, `campos(ctx)`, `construir(v, ctx)`, `desde_op(op, ctx)`, `crear_op(...)`, SIN_OP + `aplicar`,
  `mostrar`, `al_cerrar`); `hit_desde_ref`, `hits`, `refs`, `ref1`, `exigir`, `ErrorComando`.
- `clon/omnicad/ui/comandos/modificar.py` y `superficie.py` — comandos reales de ejemplo.
- `clon/omnicad/timeline/operaciones.py` — `Operacion` (TIPO, ETIQUETA, ICONO, PARAMS, EXPRESIONES,
  `dependencias()`, `ejecutar(estado, ctx)`), `EstadoModelo` (cuerpos, planos, ejes, puntos, componentes…),
  `Cuerpo` (id, nombre, forma, tipo "solido"|"superficie"|"malla", apariencia, material, componente),
  `aplicar_resultado(estado, ctx, op_id, forma, operacion, objetivo, tipo)`, `registrar_operacion`,
  `_resolver`, `_resolver_todas`, `_deps_objetivo`, `ErrorOperacion`, `ctx.evaluar(expr, tipo)`.
- `clon/omnicad/timeline/ops_modificar.py` y `ops_superficie.py` — operaciones reales de ejemplo.
- `clon/omnicad/timeline/entidades.py` — referencias a lo elegido en la vista ({"tipo": "cara"|"arista"|
  "vertice"|"cuerpo"|"plano"|"eje"|"punto"|"perfil"|"curva_boceto"|"punto_boceto"|"boceto", …}),
  `resolver(ref, estado)` → `Entidad` (forma, cuerpo, plano, eje, punto…), `como_plano`, `como_eje`,
  `como_punto`, `direccion`, `dependencias_de`.
- Filtros de selección del visor: `FILTROS` en `ui/visor3d.py` ("cara", "cara_plana", "arista",
  "arista_lineal", "arista_circular", "vertice", "cuerpo", "perfil", "curva_boceto", "punto_boceto", "boceto",
  "plano", "eje", "punto").

Reglas:
1. La operación guarda REFERENCIAS (nunca formas OCC) y es serializable a JSON; en `ejecutar` se resuelven.
2. `dependencias()` devuelve los ids de las operaciones de las que depende (para no romper el timeline).
3. Errores del modelo: `ErrorOperacion` (o `geo.ErrorGeometria` del núcleo). Faltan datos en el diálogo:
   `ErrorComando`.
4. Registro: al final del módulo de operaciones `registrar_operacion(...)`; al final del módulo de
   comandos `registrar(...)` (de `ui/comandos/__init__.py`). La conexión de los módulos nuevos (import en
   `operaciones.py`, `ui/comandos/__init__.py`, ítems de `ui/cinta.py`) la hace el coordinador: avisá en el
   informe los nombres de módulo, las CLAVES de comando y el ícono de cada una.
5. Pruebas como `clon/tests/test_comandos_modificar.py`: arman el diálogo con `ContextoComando(doc)`,
   llenan los valores con selecciones (`hit_desde_ref`) y verifican el resultado numérico en el documento.
6. Íconos: `ui/iconos_extra.py` ya tiene casi todos; usá esos nombres.
