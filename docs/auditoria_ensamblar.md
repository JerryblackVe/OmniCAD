# Auditoría, reparación y paridad del sistema ENSAMBLAR contra Fusion 360

Pedido de Gerardo (2026-11-07): auditar, reparar y completar contra Fusion 360 las 16 herramientas de ENSAMBLAR (Nuevo
componente a Insertar componente), el solver de uniones, jerarquías, movimiento, contactos y estudio de movimiento, en
todos los espacios donde se usan componentes. Mismo procedimiento que
[auditoria_boceto_crear_modificar.md](auditoria_boceto_crear_modificar.md): ejecutan los agentes, Claude solo como
última instancia, y al final todo verde.

**Cuándo:** otro día, el que elija Gerardo. Va 5.ª de 6; orden y reparto en [agenda.md](seguimiento/agenda.md) (sección «Orden y reparto de las auditorías»). Absorbe los ítems de [brechas_ensamblar.md](brechas_ensamblar.md).

## Prompt para el agente

Guardado el 2026-11-07. Modelo sugerido: coordina una sesión Claude Opus 5 con esfuerzo alto; ejecutan Sol (OpenCode) y los agentes gratis aprobados, un ítem por corrida y cada uno en su worktree.

```text
AJUSTE DEL COORDINADOR (2026-11-08; manda sobre todo lo que sigue)
- Orden de las seis auditorías (de a una; la siguiente arranca cuando la anterior quedó cerrada y commiteada): 1) CONSTRUIR (AG-7), 2) herramientas 3D (AG-2), 3) MODIFICAR (AG-4), 4) INSERTAR (AG-6), 5) ENSAMBLAR (AG-5), 6) RENDERIZAR (AG-3). Cada herramienta tiene UNA sola auditoría dueña. Las demás solo la usan en sus pruebas combinadas: si encuentran un bug en una herramienta ajena, cargan la fila en docs/seguimiento/ y la arreglan solo si la dueña ya pasó (está antes en el orden); si la dueña viene después, dejan la fila para ella.
- Sos la dueña de todo ENSAMBLAR, incluidos Duplicar con uniones, Insertar componente y Lista de materiales (la sección 31 de auditoria_modificar.md te dice qué revisar de ella). Mover/copiar y Alinear ya los cerró MODIFICAR (AG-4): solo probalos sobre componentes. Incluí y cerrá los ítems ASM-17 a ASM-20 y SC6/P-25e2 de docs/brechas_ensamblar.md (su prompt viejo se borró: lo reemplaza este).

# PROMPT MAESTRO — AUDITORÍA, REPARACIÓN Y PARIDAD FUNCIONAL DEL SISTEMA ENSAMBLAR DE OMNICAD CON FUSION 360

## 1. MISIÓN PRINCIPAL

Actuá como un equipo senior de ingeniería de software CAD paramétrico, especializado en:

- Arquitectura de sistemas CAD 3D.
- Ensamblajes mecánicos paramétricos.
- Cinemática y dinámica de mecanismos.
- Sistemas de uniones y restricciones 3D.
- Solvers de ensamblajes.
- Transformaciones y matrices 3D.
- Jerarquías de componentes.
- OpenCascade y geometría B-Rep.
- Detección de colisiones y contactos.
- Simulación de movimiento.
- Interfaces CAD profesionales.
- Automatización de pruebas.
- Optimización de rendimiento.

Tu misión es realizar una **AUDITORÍA EXHAUSTIVA, CORRECCIÓN DE BUGS, IMPLEMENTACIÓN DE FUNCIONES FALTANTES Y OPTIMIZACIÓN INTEGRAL DEL SISTEMA ENSAMBLAR DE OMNICAD**.

La referencia principal y obligatoria será **Autodesk Fusion 360**.

### OBJETIVO FUNDAMENTAL

Conseguir que OmniCAD permita crear, organizar, unir, posicionar, restringir, editar, mover y simular ensamblajes mecánicos con un comportamiento funcional equivalente al de Fusion 360.

No quiero solamente un diagnóstico.

**Quiero que investigues, audites, reproduzcas los errores, repares los bugs, completes las funcionalidades faltantes y compruebes que todas las herramientas funcionen correctamente.**

El resultado debe ser un sistema de ensamblajes:

- Preciso.
- Paramétrico.
- Estable.
- Intuitivo.
- Robusto.
- Consistente.
- Capaz de manejar ensamblajes complejos.
- Compatible con el resto de OmniCAD.

---

# PARTE I — INSTRUCCIONES OBLIGATORIAS

## 2. REGLAS DEL PROYECTO

Antes de modificar código:

1. Leer `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` y `PROJECT_CONTEXT.md`.
2. Invocar mediante la herramienta Skill `fable-method` y `ponytail`, conforme a las reglas vigentes del repositorio.
3. Utilizar `plan-then-do`, `tool-calling-guard` y `verify-before-commit`.
4. Utilizar `ponytail-audit` cuando corresponda.
5. Invocar `omnicad-test` para las pruebas reales de interfaz.
6. Finalizar cada corrección mediante `ponytail-review`.
7. Respetar la arquitectura y las convenciones de OmniCAD.
8. No copiar código propietario de Autodesk.
9. No instalar nuevas dependencias sin autorización.
10. No ejecutar `git push`.

Cada corrección deberá cerrarse individualmente, con pruebas y revisión, antes de integrar la siguiente.

Respetar la separación de responsabilidades entre núcleo, timeline, interfaz, API, MCP y CLI.

No considerar terminada una tarea sin evidencia verificable.

---

# PARTE II — DOCUMENTACIÓN OFICIAL DE FUSION 360

## 3. INVESTIGACIÓN OBLIGATORIA

Utilizar como fuente principal:

`docs/fusion_docs/`

Consultar especialmente:

- `fusion-assemble`
- `fusion-designs`
- `fusion-model`
- `fusion-animate`
- `fusion-configurations`

Y cualquier otra sección relacionada.

Utilizar:

`scripts/fusion_docs.py buscar`

`scripts/fusion_docs.py ver`

Consultar también la documentación oficial de Autodesk disponible en Internet cuando sea necesario.

### TEMAS OBLIGATORIOS

Investigar:

- Components.
- New Component.
- Joint.
- As-Built Joint.
- Joint Origin.
- Rigid Group.
- Drive Joints.
- Motion Link.
- Ground.
- Edit Initial Position.
- Capture Position.
- Revert Position.
- Contact Sets.
- Motion Study.
- Insert Component.
- Component Hierarchy.
- External Components.
- Assembly Relationships.

Investigar todas las variantes y opciones disponibles.

### REGLA FUNDAMENTAL

**Antes de modificar una herramienta, estudiar su comportamiento real en Fusion 360.**

Documentar:

1. Funcionalidad.
2. Opciones.
3. Parámetros.
4. Selecciones admitidas.
5. Referencias utilizadas.
6. Comportamiento de movimiento.
7. Restricciones aplicadas.
8. Grados de libertad.
9. Edición posterior.
10. Persistencia.
11. Interacción con otros comandos.
12. Limitaciones conocidas.

No inventar comportamientos cuando falte documentación.

---

# PARTE III — ALCANCE EN TODOS LOS ESPACIOS

## 4. AUDITORÍA TRANSVERSAL

La auditoría debe cubrir todas las herramientas de ensamblaje disponibles en:

### SÓLIDO

Comprobar ensamblajes de cuerpos y componentes creados mediante modelado sólido.

### SUPERFICIE

Verificar componentes que contengan superficies abiertas y cerradas, incluidas sus transformaciones y referencias de unión compatibles.

### PLÁSTICO

Comprobar ensamblajes de componentes diseñados mediante herramientas de plástico, incluidos encastres, fijaciones y subcomponentes.

### CHAPA

Comprobar componentes de chapa, sus transformaciones, ensamblajes y conservación de propiedades paramétricas.

### MALLA

Auditar los ensamblajes que contengan componentes de malla cuando el sistema los admita.

### OTROS ESPACIOS

Incluir cualquier otro entorno que utilice componentes, uniones, posiciones o movimientos.

**No duplicar motores de ensamblaje innecesariamente. Las herramientas compartidas deben utilizar un comportamiento central coherente, respetando las diferencias de cada espacio.**

---

# PARTE IV — INVENTARIO COMPLETO DE ENSAMBLAR

## 5. HERRAMIENTAS OBLIGATORIAS

Auditar todas las herramientas visibles en el menú ENSAMBLAR:

1. Nuevo componente.
2. Unión.
3. Unión como está.
4. Duplicar con uniones.
5. Origen de la unión.
6. Grupo rígido.
7. Accionar uniones.
8. Vínculo de movimiento.
9. Fijar / liberar componente.
10. Anclar / desanclar componente.
11. Editar posición inicial.
12. Capturar posición.
13. Revertir posición.
14. Habilitar todos los conjuntos de contacto, si corresponde al comando mostrado.
15. Estudio de movimiento.
16. Insertar componente.

También inspeccionar:

- Todas las variantes de Unión.
- Todos los submenús.
- Herramientas contextuales.
- Botones adicionales de la cinta.
- Acciones del navegador de componentes.
- Menús del botón derecho.
- Comandos de selección.
- Opciones relacionadas disponibles mediante API/MCP/CLI.

El botón **Unión** de ENSAMBLAR debe investigarse como una relación mecánica entre componentes y no confundirse con la operación booleana Combinar/Unir cuerpos.

No asumir que las funciones están completas porque sus botones aparecen habilitados.

---

# PARTE V — AUDITORÍA DE COMPONENTES

## 6. NUEVO COMPONENTE

Comparar con New Component de Fusion 360.

Auditar:

- Creación de componente interno.
- Creación de componente externo cuando esté soportada.
- Nombre.
- Componente padre.
- Componente activo.
- Origen.
- Posición.
- Orientación.
- Creación desde cuerpos existentes.
- Jerarquía.
- Anidamiento.
- Propiedades.
- Transformaciones.
- Visibilidad.
- Selección.
- Edición.
- Persistencia.

### PRUEBAS OBLIGATORIAS

Crear:

1. Un componente independiente.
2. Varios componentes hermanos.
3. Un componente dentro de otro.
4. Una jerarquía de varios niveles.
5. Componentes creados a partir de cuerpos.
6. Componentes que contengan varios cuerpos.
7. Componentes internos y externos, cuando corresponda.

Comprobar que:

- Cada componente conserve su identidad.
- El sistema de coordenadas sea correcto.
- La geometría esté correctamente posicionada.
- Las transformaciones del padre afecten a sus hijos.
- No existan desplazamientos duplicados.
- La jerarquía sobreviva al guardado.

---

## 7. INSERTAR COMPONENTE

Comparar con Insert Component de Fusion 360.

Auditar:

- Inserción desde archivos.
- Inserción desde proyectos existentes.
- Referencias externas.
- Posición inicial.
- Orientación.
- Unidades.
- Escala cuando corresponda.
- Instancias.
- Duplicados.
- Componentes vinculados.
- Actualización de referencias.
- Reemplazo de componentes.
- Edición posterior.

Probar archivos compatibles:

- STEP.
- Archivos propios de OmniCAD.
- F3D cuando sea aplicable.
- Otros formatos admitidos.

Verificar que las piezas importadas no pierdan sus transformaciones, jerarquías o propiedades.

No convertir silenciosamente referencias vinculadas en copias independientes.

---

# PARTE VI — SISTEMA DE UNIONES

## 8. UNIÓN — AUDITORÍA PRINCIPAL

Comparar con Joint de Fusion 360.

Esta es una de las áreas más importantes de la auditoría.

### TIPOS DE UNIÓN

Investigar y probar todas las variantes disponibles:

- Rígida.
- Revoluta.
- Deslizante.
- Cilíndrica.
- Pasador en ranura.
- Plana.
- Esférica.
- Cualquier otro tipo implementado.

No asumir que todas estas variantes existen en OmniCAD: verificar el inventario real y registrar faltantes.

### PARA CADA TIPO

Auditar:

1. Selección de componentes.
2. Selección de referencias.
3. Posición de origen.
4. Orientación.
5. Ejes.
6. Desfase.
7. Ángulos.
8. Inversión.
9. Grados de libertad.
10. Límites de movimiento.
11. Posición inicial.
12. Edición.
13. Supresión.
14. Reactivación.
15. Persistencia.
16. Recalculo paramétrico.

### COMPORTAMIENTO ESPERADO

La unión debe posicionar y restringir los componentes según la relación mecánica seleccionada.

No debe producir movimientos adicionales inesperados.

Una unión rígida no debe permitir desplazamientos relativos.

Una unión revoluta debe permitir únicamente el movimiento rotacional definido, salvo capacidades adicionales expresamente documentadas.

Una unión deslizante debe respetar su dirección y límites.

Cada tipo debe cumplir matemáticamente sus grados de libertad.

### PRUEBAS REALES

Crear:

- Bisagra.
- Eje dentro de soporte.
- Corredera.
- Unión cilíndrica.
- Mecanismo de pasador y ranura.
- Rótula.
- Mecanismo articulado.

Verificar los movimientos con el mouse y mediante valores numéricos.

---

## 9. UNIÓN COMO ESTÁ

Comparar con As-Built Joint.

Auditar:

- Selección de componentes.
- Conservación de la posición actual.
- Tipo de unión.
- Orígenes.
- Ejes.
- Límites.
- Grados de libertad.
- Edición posterior.
- Recalculo.
- Persistencia.

### REGLA CRÍTICA

**Unión como está no debe reposicionar innecesariamente los componentes al crear la relación.**

Debe conservar su configuración espacial inicial y establecer la relación mecánica correspondiente.

Probar componentes:

- Separados.
- Alineados.
- Rotados.
- En contacto.
- Dentro de subensamblajes.
- Con transformaciones previas.

---

## 10. ORIGEN DE LA UNIÓN

Comparar con Joint Origin.

Auditar:

- Selección de vértices.
- Centros de círculos.
- Centros de agujeros.
- Aristas.
- Caras.
- Puntos medios.
- Ejes.
- Planos.
- Geometría de construcción.
- Posicionamiento manual.
- Orientación.
- Inversión de ejes.
- Desfases.
- Edición.

Verificar que la orientación matemática del sistema de coordenadas sea correcta.

Prestar especial atención a las transformaciones entre coordenadas locales y globales.

### PRUEBA OBLIGATORIA

Crear un origen de unión en un componente dentro de una jerarquía anidada, mover el padre y verificar que el origen conserve su relación con el componente.

---

# PARTE VII — COPIAS Y GRUPOS

## 11. DUPLICAR CON UNIONES

Investigar la función equivalente de Fusion 360 y su comportamiento exacto.

Auditar:

- Selección de componentes.
- Número de copias.
- Posicionamiento.
- Conservación de uniones.
- Duplicación de relaciones.
- Referencias internas.
- Referencias externas.
- Nombres.
- Identificadores.
- Jerarquía.
- Edición posterior.

Comprobar que cada copia tenga referencias válidas y no reutilice accidentalmente identificadores de otra instancia.

Probar duplicaciones de mecanismos completos.

**Las copias deben mantener el comportamiento de unión documentado, sin producir relaciones cruzadas incorrectas.**

---

## 12. GRUPO RÍGIDO

Comparar con Rigid Group.

Auditar:

- Selección múltiple.
- Componentes del grupo.
- Componentes hijos.
- Subensamblajes.
- Transformaciones.
- Posiciones relativas.
- Movimiento conjunto.
- Edición de integrantes.
- Eliminación del grupo.
- Persistencia.

### VALIDACIÓN

Todos los componentes incluidos deben conservar sus posiciones y orientaciones relativas durante el movimiento.

Comprobar que:

- El grupo pueda moverse como conjunto cuando corresponda.
- No existan desplazamientos internos.
- Los componentes mantengan sus referencias.
- Eliminar el grupo restaure los grados de libertad apropiados.
- Los grupos anidados funcionen correctamente.

---

# PARTE VIII — MOVIMIENTO MECÁNICO

## 13. ACCIONAR UNIONES

Comparar con Drive Joints.

Auditar:

- Selección de unión.
- Inicio.
- Final.
- Rango.
- Dirección.
- Velocidad.
- Animación.
- Reproducción.
- Pausa.
- Reinicio.
- Límites.
- Movimiento inverso.
- Movimiento cíclico.
- Posición final.
- Edición de parámetros.

Comprobar que el movimiento corresponda al tipo de unión y a sus restricciones.

### PRUEBAS

- Bisagra de 0° a 90°.
- Eje con rotación completa.
- Corredera de distancia definida.
- Cilindro con giro y desplazamiento.
- Movimiento limitado mecánicamente.

No permitir que Accionar uniones altere permanentemente la configuración paramétrica cuando el comportamiento de referencia sea únicamente de previsualización.

---

## 14. VÍNCULO DE MOVIMIENTO

Comparar con Motion Link.

Auditar:

- Selección de uniones.
- Relación entre movimientos.
- Relaciones angulares.
- Relaciones lineales.
- Factores de transmisión.
- Inversión de sentido.
- Movimiento sincronizado.
- Límites.
- Edición posterior.
- Persistencia.

### ESCENARIOS

Crear:

1. Dos ejes vinculados.
2. Dos uniones revolutas.
3. Una unión revoluta vinculada a una deslizante.
4. Mecanismo tipo piñón-cremallera.
5. Mecanismo con múltiples vínculos.

Verificar matemáticamente la relación entre desplazamientos.

No limitar la comprobación a una animación visualmente aproximada.

---

# PARTE IX — FIJACIÓN Y POSICIONAMIENTO

## 15. FIJAR / LIBERAR COMPONENTE

Auditar la semántica real de este comando en OmniCAD y su equivalente documentado en Fusion 360.

Comprobar:

- Fijación.
- Liberación.
- Posición.
- Orientación.
- Restricciones existentes.
- Movimiento.
- Jerarquía.
- Componentes hijos.
- Edición.
- Persistencia.

Verificar que fijar un componente impida exclusivamente los movimientos que correspondan al comportamiento definido.

No modificar la geometría de las piezas.

---

## 16. ANCLAR / DESANCLAR COMPONENTE

Investigar la diferencia entre Anclar y Fijar.

Comparar con las modalidades de Ground y otros controles de fijación de Fusion 360.

Auditar:

- Componente anclado.
- Componente libre.
- Componente raíz.
- Jerarquía.
- Referencia al sistema global.
- Transformaciones.
- Conservación de posición.
- Edición.
- Persistencia.

### REGLA OBLIGATORIA

No hacer que Anclar y Fijar se comporten idénticamente sin verificar primero que esa sea realmente su semántica.

Distinguir correctamente:

- Componente fijado.
- Componente anclado.
- Componente restringido mediante unión rígida.
- Componente dentro de grupo rígido.

Comprobar las diferencias mediante pruebas reales.

---

## 17. EDITAR POSICIÓN INICIAL

Comparar con Edit Initial Position.

Auditar:

- Transformación inicial.
- Posición.
- Rotación.
- Orientación.
- Sistema de coordenadas.
- Dependencias.
- Actualización de uniones.
- Recalculo.
- Edición posterior.

Verificar que modificar la posición inicial no destruya las relaciones paramétricas existentes.

---

## 18. CAPTURAR POSICIÓN

Comparar con Capture Position.

Auditar:

- Posiciones actuales.
- Transformaciones.
- Componentes movidos.
- Registro de posición.
- Historial paramétrico.
- Dependencias.
- Edición posterior.
- Guardado.

Comprobar que se capture exactamente la configuración espacial esperada.

---

## 19. REVERTIR POSICIÓN

Comparar con Revert Position.

Auditar:

- Restauración.
- Posiciones anteriores.
- Cambios no capturados.
- Relaciones.
- Componentes.
- Jerarquías.
- Transformaciones.
- Historial.
- Deshacer y rehacer.

### PRUEBA FUNDAMENTAL

1. Crear un ensamblaje.
2. Mover varios componentes.
3. Revertir posición.
4. Verificar que regresen a la configuración correspondiente.
5. Repetir con una posición capturada.
6. Guardar y recuperar.

No permitir movimientos residuales ni pérdida de relaciones.

---

# PARTE X — CONTACTOS Y COLISIONES

## 20. CONJUNTOS DE CONTACTO

Auditar el comando de habilitación de conjuntos de contacto y todas las funciones relacionadas presentes en OmniCAD.

Comparar con Contact Sets de Fusion 360.

Investigar:

- Activación.
- Desactivación.
- Selección de componentes.
- Detección de contacto.
- Detección de colisiones.
- Restricción de penetración.
- Superficies de contacto.
- Movimiento condicionado.
- Actualización durante el arrastre.
- Rendimiento.
- Persistencia.

### CASOS DE PRUEBA

- Dos prismas.
- Un eje dentro de un agujero.
- Engranajes en contacto.
- Corredera con topes.
- Mecanismo articulado.
- Componentes con geometría compleja.

### CRITERIO

Los contactos deben responder de forma coherente con las reglas del sistema.

Una detección visual de interferencia no equivale automáticamente a una restricción de contacto.

Investigar qué capacidades corresponden realmente a Fusion 360 y reproducir su comportamiento funcional.

---

# PARTE XI — ESTUDIO DE MOVIMIENTO

## 21. AUDITORÍA COMPLETA

Comparar con Motion Study de Fusion 360.

Auditar:

- Creación de estudio.
- Selección de uniones.
- Variables de movimiento.
- Tiempo.
- Posición.
- Rotación.
- Velocidad.
- Curvas.
- Secuencias.
- Reproducción.
- Pausa.
- Reinicio.
- Edición.
- Persistencia.

Investigar también:

- Movimiento simultáneo.
- Múltiples uniones.
- Vínculos mecánicos.
- Restricciones.
- Configuración inicial.
- Límites de recorrido.
- Actualización del visor.
- Evaluación temporal.
- Integración con ANIMACIÓN cuando corresponda.

### PRUEBAS REALES

Crear:

1. Bisagra animada.
2. Corredera.
3. Mecanismo de cuatro barras.
4. Sistema piñón-cremallera.
5. Mecanismo con varias uniones.
6. Ensamblaje con componentes anidados.

Verificar posiciones y orientaciones en instantes concretos de la simulación.

No considerar que un mecanismo funciona porque se reproduce una animación visualmente convincente.

Los desplazamientos deben corresponder a las relaciones matemáticas definidas.

---

# PARTE XII — AUDITORÍA PROFUNDA DEL SOLVER DE ENSAMBLAJES

## 22. INVESTIGACIÓN MATEMÁTICA

Identificar la arquitectura real del sistema que resuelve las uniones.

Auditar:

- Representación de componentes.
- Transformaciones rígidas.
- Matrices homogéneas.
- Sistemas de coordenadas locales.
- Sistemas de coordenadas globales.
- Cuaterniones.
- Rotaciones.
- Grados de libertad.
- Restricciones.
- Relaciones cinemáticas.
- Jerarquías.
- Dependencias.
- Resolución de sistemas.
- Ciclos.
- Restricciones contradictorias.
- Restricciones redundantes.
- Tolerancias.
- Estabilidad numérica.

### PROBLEMAS QUE DEBEN DETECTARSE

- Componentes que saltan de posición.
- Rotaciones inesperadas.
- Transformaciones aplicadas dos veces.
- Desplazamiento de componentes hijos.
- Pérdida de restricciones.
- Uniones que aparentan funcionar, pero permiten movimientos incorrectos.
- Uniones que impiden movimientos válidos.
- Relaciones matemáticas incompatibles.
- Pérdida de referencias.
- Resultados diferentes después de recalcular.
- Movimientos no deterministas.

**Priorizar la reparación de las causas estructurales frente a parches específicos para determinados mecanismos.**

---

# PARTE XIII — JERARQUÍAS Y SUBENSAMBLAJES

## 23. VALIDACIÓN DE COMPONENTES ANIDADOS

Crear jerarquías complejas.

Ejemplo:

Ensamblaje principal
- Componente A
- Componente B
  - Subcomponente B1
  - Subcomponente B2
- Subensamblaje C
  - Componente C1
  - Componente C2

Auditar:

- Transformaciones heredadas.
- Relaciones internas.
- Relaciones externas.
- Uniones entre niveles.
- Movimiento del padre.
- Movimiento de los hijos.
- Grupos rígidos.
- Referencias.
- Selección.
- Visibilidad.
- Activación.
- Persistencia.

Comprobar que mover un componente padre no provoque desplazamientos duplicados de sus hijos.

Verificar que las uniones mantengan su comportamiento después de reorganizar componentes.

---

# PARTE XIV — INTEGRACIÓN CON OTROS ESPACIOS

## 24. MODELADO Y ENSAMBLAJES

Probar la interacción entre ENSAMBLAR y:

- SÓLIDO.
- SUPERFICIE.
- PLÁSTICO.
- CHAPA.
- MALLA.
- RENDERIZAR.
- ANIMACIÓN.
- DIBUJO, cuando corresponda.

### PRUEBA TRANSVERSAL

1. Crear piezas en SÓLIDO.
2. Convertirlas en componentes.
3. Crear uniones.
4. Configurar límites.
5. Mover componentes.
6. Crear un estudio de movimiento.
7. Cambiar dimensiones de las piezas.
8. Recalcular el ensamblaje.
9. Entrar a RENDERIZAR.
10. Comprobar las posiciones.
11. Guardar.
12. Cerrar.
13. Reabrir.

La edición de una pieza no debe destruir injustificadamente la estructura del ensamblaje.

Cuando una referencia geométrica deje de ser válida, informar el problema en lugar de asociarla silenciosamente a una cara o arista incorrecta.

---

# PARTE XV — INTERFAZ Y EXPERIENCIA DE USUARIO

## 25. AUDITORÍA DE TODOS LOS COMANDOS

Probar cada herramienta mediante interacción real.

Auditar:

- Menús.
- Submenús.
- Iconos.
- Atajos.
- Selección de componentes.
- Selección de caras.
- Selección de aristas.
- Selección de vértices.
- Orígenes.
- Manipuladores.
- Flechas.
- Asas de rotación.
- Controles de posición.
- Campos numéricos.
- Vista previa.
- Aceptar.
- Cancelar.
- Escape.
- Edición posterior.
- Estados visuales.
- Mensajes de error.

### MANIPULACIÓN DIRECTA

Comprobar especialmente que el usuario pueda:

- Seleccionar un componente.
- Arrastrarlo.
- Rotarlo.
- Moverlo dentro de sus grados de libertad.
- Identificar qué movimientos están restringidos.
- Detener el movimiento.
- Revertirlo.
- Capturarlo.

No permitir que el componente se desplace libremente si sus uniones deben restringirlo.

No permitir que una herramienta deje el mecanismo en un estado inconsistente después de cancelar.

---

# PARTE XVI — PRUEBAS DE MECANISMOS

## 26. BANCO OBLIGATORIO DE ENSAMBLAJES

Crear mecanismos de prueba reproducibles:

### A. BISAGRA

Dos componentes conectados mediante unión revoluta.

Verificar rotación y ausencia de traslación relativa indebida.

### B. CORREDERA

Movimiento lineal sobre un eje.

Verificar dirección, recorrido y límites.

### C. EJE Y SOPORTE

Comprobar concentricidad, movimiento y referencias.

### D. MECANISMO DE CUATRO BARRAS

Verificar movimiento acoplado y cierre geométrico.

### E. PIÑÓN Y CREMALLERA

Comprobar el vínculo entre rotación y desplazamiento.

### F. ENGRANAJES VINCULADOS

Verificar relaciones de transmisión mediante vínculos de movimiento.

No asumir que existe simulación de contacto físico de dientes si el sistema solo ofrece relaciones cinemáticas.

### G. GRUPO RÍGIDO

Varios componentes que deben moverse juntos.

### H. SUBENSAMBLAJE ANIDADO

Uniones entre componentes de varios niveles.

### I. ENSAMBLAJE IMPORTADO

Componentes provenientes de formatos externos.

### J. ENSAMBLAJE COMPLEJO

Numerosos componentes, uniones y restricciones.

Cada mecanismo debe contar con:

- Modelo reproducible.
- Configuración inicial conocida.
- Relaciones definidas.
- Grados de libertad esperados.
- Posiciones verificables.
- Pruebas de movimiento.
- Pruebas de edición.
- Pruebas de persistencia.
- Evidencias visuales.

---

# PARTE XVII — DETECCIÓN Y REPARACIÓN DE BUGS

## 27. REPARACIÓN OBLIGATORIA

**La auditoría incluye reparar los bugs encontrados, no solamente documentarlos.**

Para cada defecto:

1. Reproducirlo.
2. Registrar evidencia.
3. Identificar la causa raíz.
4. Crear una prueba que falle antes de corregirlo.
5. Aplicar la corrección.
6. Ejecutar la prueba.
7. Verificar el resultado matemático.
8. Verificar el movimiento real.
9. Probar desde la interfaz.
10. Ejecutar pruebas de regresión.
11. Invocar `ponytail-review`.
12. Documentar e integrar según las reglas del repositorio.

### PROHIBICIONES

- No ocultar errores.
- No ignorar tests fallidos.
- No eliminar pruebas para obtener resultados verdes.
- No modificar resultados esperados sin justificación.
- No corregir un mecanismo rompiendo otro.
- No introducir transformaciones artificiales para ocultar errores del solver.
- No desactivar restricciones válidas para conseguir convergencia.
- No declarar una función terminada sin pruebas reales.

Cuando un bug afecte varias herramientas, corregir la causa en el nivel arquitectónico apropiado.

---

# PARTE XVIII — FUNCIONES FALTANTES

## 28. COMPLETAR EL SISTEMA ENSAMBLAR

Comparar todas las herramientas con Fusion 360.

Identificar:

- Tipos de uniones faltantes.
- Opciones de unión incompletas.
- Grados de libertad incorrectos.
- Límites de movimiento ausentes.
- Manipuladores incompletos.
- Parámetros no implementados.
- Modos de posicionamiento faltantes.
- Funciones de contacto incompletas.
- Funciones de movimiento faltantes.
- Problemas de subensamblajes.
- Problemas de referencias.
- Diferencias entre UI y API.
- Herramientas deshabilitadas.
- Funciones de inserción incompletas.

**Implementar todas las funcionalidades faltantes dentro del alcance que sean técnicamente viables, con pruebas y verificación.**

Si una función requiere cambios profundos de arquitectura, documentar la justificación y ejecutarla incrementalmente, sin comprometer la estabilidad del proyecto.

No presentar una interfaz parcialmente implementada como equivalente funcional a Fusion 360.

---

# PARTE XIX — RENDIMIENTO Y ESTABILIDAD

## 29. AUDITORÍA DE RENDIMIENTO

Medir:

- Tiempo de creación de uniones.
- Tiempo de resolución del ensamblaje.
- Tiempo de recálculo.
- Tiempo de actualización visual.
- Fluidez de arrastre.
- Reproducción de estudios de movimiento.
- Uso de memoria.
- Uso de CPU.
- Comportamiento con muchos componentes.

Probar ensamblajes de:

- 2 componentes.
- 10 componentes.
- 50 componentes.
- 100 componentes.
- Cantidades superiores cuando los recursos lo permitan.

Investigar:

- Cálculos repetidos.
- Transformaciones redundantes.
- Recalculo innecesario.
- Cuellos de botella del solver.
- Actualizaciones excesivas de OpenGL.
- Detección de colisiones costosa.
- Pérdidas de memoria.
- Bloqueos de interfaz.

Medir primero y optimizar después.

Evaluar Rust/PyO3 cuando exista una ventaja demostrable y se respeten las políticas de dependencias.

---

# PARTE XX — API, MCP Y CLI

## 30. PARIDAD DE HERRAMIENTAS

Comprobar que todas las operaciones de ensamblaje funcionen coherentemente desde:

- Interfaz gráfica.
- API Python.
- MCP.
- CLI.

Verificar:

- Creación de componentes.
- Inserción.
- Creación de uniones.
- Edición de uniones.
- Grupos rígidos.
- Posicionamiento.
- Movimiento.
- Límites.
- Vínculos.
- Simulación.
- Persistencia.
- Manejo de errores.

Toda herramienta nueva o modificada deberá respetar el catálogo único de OmniCAD.

Actualizar documentación y pruebas correspondientes.

No permitir resultados matemáticamente distintos según la vía de ejecución, salvo diferencias de contexto justificadas.

---

# PARTE XXI — PRUEBAS AUTOMATIZADAS Y REALES

## 31. VERIFICACIÓN OBLIGATORIA

Utilizar:

- `pytest`.
- `omnicad-test`.
- `scripts/prueba_ui/`.
- Pruebas de API.
- Pruebas MCP.
- Pruebas de persistencia.
- Pruebas de integración.
- Pruebas de humo.
- Caza de errores cuando corresponda.

### PRUEBA COMO USUARIO

Cada herramienta debe probarse mediante acciones sobre la interfaz:

1. Abrir ENSAMBLAR.
2. Seleccionar el comando.
3. Seleccionar componentes.
4. Elegir referencias en el visor.
5. Configurar parámetros.
6. Observar la vista previa.
7. Aceptar.
8. Mover el ensamblaje.
9. Editar.
10. Deshacer.
11. Rehacer.
12. Guardar.
13. Recuperar.

Una prueba únicamente mediante Python o MCP no sustituye la validación de la interfaz.

No mover el cursor físico del usuario durante pruebas automatizadas.

---

# PARTE XXII — ORGANIZACIÓN DE LA AUDITORÍA

## 32. PLAN POR FASES

### FASE 1 — INVENTARIO

Identificar todas las herramientas, variantes e implementaciones.

### FASE 2 — INVESTIGACIÓN

Estudiar la documentación oficial de Fusion 360.

### FASE 3 — AUDITORÍA FUNCIONAL

Probar todas las herramientas e identificar defectos y faltantes.

### FASE 4 — AUDITORÍA MATEMÁTICA

Revisar transformaciones, jerarquías, relaciones y solver.

### FASE 5 — REPARACIÓN

Corregir bugs confirmados, uno por uno.

### FASE 6 — IMPLEMENTACIÓN

Completar funciones y opciones faltantes.

### FASE 7 — INTEGRACIÓN

Verificar todos los espacios, timeline, API, MCP y CLI.

### FASE 8 — OPTIMIZACIÓN

Medir y mejorar rendimiento.

### FASE 9 — REGRESIÓN

Comprobar que las correcciones no afecten otras herramientas.

### FASE 10 — VALIDACIÓN FINAL

Comparar el comportamiento con Fusion 360 y entregar evidencias.

El coordinador debe gestionar las fases sin solicitar aprobación entre tareas ordinarias.

Respetar las reglas vigentes de permisos, dependencias, commits y ejecución de pruebas completas.

Cada corrección debe quedar verificada individualmente antes de pasar a la siguiente.

---

# PARTE XXIII — DOCUMENTACIÓN

## 33. REGISTRO DEL TRABAJO

Actualizar:

- `docs/seguimiento/bugs.md`
- `docs/seguimiento/faltantes.md`
- `docs/seguimiento/mejoras.md`
- `PROJECT_LOG.md`
- `PROJECT_CONTEXT.md`
- Documentación técnica afectada.
- Tests automatizados.
- Documentación API/MCP.

Respetar la fuente única de pendientes del proyecto.

No marcar problemas como resueltos cuando no exista evidencia suficiente.

---

# PARTE XXIV — INFORME FINAL

## 34. MATRIZ DE RESULTADOS

Elaborar una matriz completa:

| Herramienta | Espacio | Variantes | Bugs detectados | Bugs corregidos | Faltantes resueltos | Estado |
|---|---|---|---|---|---|---|
| Nuevo componente | SÓLIDO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Unión | SÓLIDO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Unión como está | SUPERFICIE | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Grupo rígido | PLÁSTICO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Estudio de movimiento | ENSAMBLAR | Resultado | Cantidad | Cantidad | Cantidad | Estado |

Completarla con el inventario real y todos los espacios aplicables.

### CLASIFICACIÓN

- VERIFICADO.
- CORREGIDO.
- MEJORADO.
- PARCIAL.
- PENDIENTE.
- NO VERIFICADO.
- NO APLICA.

### ENTREGABLES

1. Inventario completo de herramientas.
2. Comparación con Fusion 360.
3. Bugs encontrados.
4. Bugs corregidos.
5. Funciones faltantes.
6. Funciones implementadas.
7. Mejoras del solver.
8. Mejoras de interfaz.
9. Mejoras de movimiento.
10. Mejoras de rendimiento.
11. Pruebas automatizadas y resultados reales.
12. Evidencias visuales.
13. Modelos de mecanismos de prueba.
14. Limitaciones pendientes.
15. Estado final del sistema de ensamblajes.

---

# PARTE XXV — CRITERIOS DE ACEPTACIÓN

## 35. CONDICIONES PARA FINALIZAR

La auditoría solamente podrá considerarse completa cuando:

1. Todas las herramientas hayan sido inventariadas.
2. Todas las variantes hayan sido investigadas.
3. Se hayan comparado con Fusion 360.
4. Las uniones funcionen geométricamente.
5. Los grados de libertad sean correctos.
6. Los componentes se posicionen adecuadamente.
7. Las jerarquías funcionen.
8. Los grupos rígidos conserven sus relaciones.
9. Los vínculos de movimiento respeten sus ecuaciones.
10. Capturar y Revertir posición funcionen.
11. Los mecanismos puedan manipularse correctamente.
12. Los estudios de movimiento sean coherentes.
13. Las relaciones paramétricas sobrevivan a los cambios.
14. Los archivos guardados conserven el ensamblaje.
15. Las pruebas de interfaz sean satisfactorias.
16. API, MCP y CLI estén sincronizados.
17. Los bugs detectados se hayan corregido o queden claramente documentados como pendientes.
18. Las funciones faltantes se hayan implementado o sus limitaciones estén justificadas.
19. No existan regresiones nuevas sin registrar.
20. La documentación esté actualizada.

**No declarar paridad completa con Fusion 360 si existen funciones pendientes o comportamientos sin verificar.**

---

# ORDEN FINAL DE EJECUCIÓN

**REALIZÁ UNA AUDITORÍA INTEGRAL DEL SISTEMA ENSAMBLAR DE OMNICAD Y DE TODAS SUS IMPLEMENTACIONES COMPARTIDAS EN SÓLIDO, SUPERFICIE, PLÁSTICO, CHAPA Y LOS DEMÁS ESPACIOS APLICABLES.**

Investigá cada herramienta mediante la documentación oficial de Autodesk Fusion 360.

Auditar todas las variantes, submenús y funciones internas.

**INVESTIGÁ → AUDITÁ → REPRODUCÍ → DIAGNOSTICÁ → REPARÁ → COMPLETÁ → OPTIMIZÁ → PROBÁ → VERIFICÁ.**

No te limites a entregar informes.

**Corregí los bugs encontrados, completá las funciones faltantes y mejorá las implementaciones existentes.**

Prestar especial atención a:

- Uniones mecánicas.
- Grados de libertad.
- Transformaciones espaciales.
- Jerarquías de componentes.
- Subensamblajes.
- Fijación y anclaje.
- Grupos rígidos.
- Movimiento.
- Relaciones cinemáticas.
- Contactos.
- Simulación.
- Persistencia.
- Referencias paramétricas.
- Rendimiento.
- Interacción real con el usuario.

La prioridad absoluta es que OmniCAD permita construir ensamblajes mecánicos **correctos, estables, editables, precisos y funcionalmente comparables con Fusion 360**.

**No declarar el trabajo terminado sin comprobar mediante pruebas matemáticas, geométricas y visuales que cada herramienta funciona correctamente.**
```
