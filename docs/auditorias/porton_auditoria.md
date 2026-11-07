# Portón de cierre de toda auditoría

Una auditoría no se da por cerrada hasta que pasa los cinco puntos. Nació con B-242: la auditoría de restricciones
probó cada restricción sola y no qué les pasa cuando otra herramienta las toca.

1. **Matriz de combinaciones.** Cada herramienta de la auditoría se aplica sobre cada estado típico de la pieza:
   - boceto totalmente restringido;
   - pieza con parámetros, que después se cambian;
   - deshacer y rehacer en cadena;
   - guardar, cerrar y reabrir;
   - el resultado de otra herramienta de la misma auditoría.

   En cada caso se comprueba un invariante medible: grados de libertad, volumen, caja, `geo.es_valida`, ninguna
   restricción o cota borrada sin aviso, y que al arrastrar no se deforme. Va como test parametrizado en `clon/tests/`
   y queda en la suite para siempre.
2. **Como usuario, en la ventana.** Cada herramienta se prueba con `scripts/prueba_ui/` (clics, teclear valores, asas,
   Esc, Enter), no solo por API.
3. **Una pieza real de principio a fin.** Una pieza del rubro de Gerardo, armada con las herramientas de la auditoría,
   cambiando una cota al final, con capturas que se miran de verdad.
4. **Juez independiente.** Una sesión aparte, con otro modelo, que no escribió el código, intenta romper lo auditado
   durante 30 minutos (`fable-judge` y `omnicad-test`). Si encuentra algo, se arregla y el juez vuelve a correr. Se
   cierra con cero hallazgos.
5. **Cerrar la clase, no el caso.** Cada bug que llegue después (un video de Gerardo, la caza automática) se suma
   como fila nueva a la matriz del punto 1 de la auditoría dueña. Así no vuelve el mismo tipo de bug en otra
   herramienta.

Después del portón: `../scripts/caza/cazar.py tema <tema>` sin hallazgos nuevos.
