# Auditoría, reparación y paridad de las herramientas de MODIFICAR contra Fusion 360

Pedido de Gerardo (2026-11-07): auditar, reparar y completar contra Fusion 360 las 27 herramientas del menú MODIFICAR
(Pulsar/tirar a Lista de materiales) en SÓLIDO, SUPERFICIE, PLÁSTICO, CHAPA, MALLA, ENSAMBLAR y donde más aparezcan.
Mismo procedimiento que [auditoria_boceto_crear_modificar.md](auditoria_boceto_crear_modificar.md): ejecutan los
agentes, Claude solo como última instancia, y al final todo verde.

**Cuándo:** otro día, el que elija Gerardo. Va 3.ª de 6; orden y reparto en [agenda.md](seguimiento/agenda.md) (sección «Orden y reparto de las auditorías»).

## Prompt para el agente

Guardado el 2026-11-07. Modelo sugerido: coordina una sesión Claude Opus 5 con esfuerzo alto; ejecutan Sol (OpenCode) y los agentes gratis aprobados, un ítem por corrida y cada uno en su worktree.

```text
AJUSTE DEL COORDINADOR (2026-11-08; manda sobre todo lo que sigue)
- PORTÓN DE CIERRE OBLIGATORIO: esta auditoría no se cierra hasta pasar los 5 puntos de docs/auditorias/porton_auditoria.md (matriz de combinaciones con invariantes, prueba en la ventana, pieza real, juez independiente con otro modelo y cerrar la clase de cada bug).
- Orden de las seis auditorías (de a una; la siguiente arranca cuando la anterior quedó cerrada y commiteada): 1) CONSTRUIR (AG-7), 2) herramientas 3D (AG-2), 3) MODIFICAR (AG-4), 4) INSERTAR (AG-6), 5) ENSAMBLAR (AG-5), 6) RENDERIZAR (AG-3). Cada herramienta tiene UNA sola auditoría dueña. Las demás solo la usan en sus pruebas combinadas: si encuentran un bug en una herramienta ajena, cargan la fila en docs/seguimiento/ y la arreglan solo si la dueña ya pasó (está antes en el orden); si la dueña viene después, dejan la fila para ella.
- Sos la dueña de las herramientas de tu lista MENOS dos: Aspecto es de Apariencia y materiales (AG-9) y Lista de materiales es de ENSAMBLAR (AG-5); salteá sus secciones 27 y 31. Mover/copiar, Alinear y Apoyar en el plano son tuyos (ENSAMBLAR solo los usa). Patrón, Simetría y Engrosar ya los cerró AG-2.

# PROMPT MAESTRO — AUDITORÍA, REPARACIÓN Y PARIDAD FUNCIONAL DEL SISTEMA MODIFICAR DE OMNICAD

## 1. MISIÓN PRINCIPAL

Actuá como un equipo de ingeniería senior especializado en arquitectura CAD paramétrica, geometría computacional, OpenCascade, modelado de sólidos y superficies, diseño de chapa, diseño plástico, operaciones booleanas, topología B-Rep, interfaces gráficas y pruebas de software CAD profesional.

Tu misión es realizar una **AUDITORÍA EXHAUSTIVA, CORRECCIÓN DE BUGS, IMPLEMENTACIÓN DE FUNCIONES FALTANTES Y OPTIMIZACIÓN DE TODAS LAS HERRAMIENTAS DE MODIFICACIÓN DE OMNICAD**.

La referencia funcional obligatoria es **Autodesk Fusion 360**.

No quiero únicamente identificar problemas o elaborar informes. Quiero que investigues cada herramienta, compruebes su comportamiento, repares los errores encontrados e implementes las opciones que falten.

### OBJETIVO FUNDAMENTAL

Lograr que todas las herramientas auditadas funcionen con la precisión, confiabilidad, comportamiento paramétrico y experiencia de uso de sus equivalentes en Fusion 360.

El alcance comprende todos los espacios de OmniCAD donde existan herramientas de modificación, particularmente:

- SÓLIDO.
- SUPERFICIE.
- PLÁSTICO.
- CHAPA.
- MALLA.
- ENSAMBLAR, cuando corresponda.
- Otros espacios y comandos contextuales que compartan estas funciones.

**No limitar la auditoría a la pestaña SÓLIDO ni a los botones de la captura.**

---

# PARTE I — INSTRUCCIONES OBLIGATORIAS

## 2. REGLAS DEL PROYECTO

Antes de trabajar:

1. Leer `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` y `PROJECT_CONTEXT.md`.
2. Invocar mediante la herramienta Skill `fable-method` y `ponytail`.
3. Utilizar `plan-then-do`, `tool-calling-guard` y `verify-before-commit`.
4. Utilizar `ponytail-audit` cuando corresponda.
5. Invocar `omnicad-test` para pruebas de interfaz.
6. Finalizar cada corrección con `ponytail-review`.
7. Respetar todas las reglas de arquitectura y desarrollo.
8. No copiar código propietario de Autodesk.
9. No instalar dependencias sin autorización.
10. No realizar `git push`.

Respetar la política de sesiones, commits, pruebas pesadas y gestión de memoria del proyecto.

Cada bug debe resolverse y verificarse individualmente antes de integrar el siguiente.

No declarar una corrección terminada sin evidencia.

---

# PARTE II — DOCUMENTACIÓN OFICIAL DE FUSION 360

## 3. INVESTIGACIÓN OBLIGATORIA

Utilizar como fuente principal:

`docs/fusion_docs/`

Consultar los índices:

- `fusion-model`
- `fusion-patch`
- `fusion-sheet-metal`
- `fusion-mesh`
- `fusion-assemble`
- Cualquier otro índice relacionado con las herramientas identificadas.

Utilizar el buscador existente:

`scripts/fusion_docs.py buscar`

Y:

`scripts/fusion_docs.py ver`

Investigar también la documentación oficial en línea cuando sea necesario para verificar funciones recientes o contenido que no esté disponible localmente.

### PARA CADA HERRAMIENTA INVESTIGAR

1. Qué hace en Fusion 360.
2. Dónde está disponible.
3. Qué geometrías admite.
4. Qué opciones contiene.
5. Qué submenús tiene.
6. Qué parámetros utiliza.
7. Cuáles son sus valores predeterminados.
8. Cómo funciona su selección.
9. Cómo funciona la vista previa.
10. Cómo interactúa con el mouse.
11. Cómo se modifica posteriormente.
12. Qué restricciones y limitaciones tiene.
13. Qué resultado geométrico debe generar.
14. Cómo interactúa con el historial paramétrico.

**Prohibido inventar el comportamiento de Fusion 360. Cada comparación debe sustentarse en documentación, pruebas o referencias verificables.**

Si una función de OmniCAD no tiene equivalente directo en Fusion 360, documentar esa diferencia.

---

# PARTE III — INVENTARIO DE HERRAMIENTAS

## 4. ALCANCE COMPLETO DEL MENÚ MODIFICAR

Auditar obligatoriamente las siguientes herramientas visibles en la captura:

1. Pulsar/tirar.
2. Empalme.
3. Chaflán.
4. Quitar empalmes.
5. Vaciado.
6. Desmoldeo.
7. Escala.
8. Combinar.
9. Desfase.
10. Reemplazar cara.
11. Editar cara.
12. Dividir cara.
13. Dividir cuerpo.
14. División de silueta.
15. Entramado volumétrico.
16. Mover/copiar.
17. Alinear.
18. Apoyar en el plano.
19. Suprimir.
20. Quitar.
21. Simplificar.
22. Material físico.
23. Aspecto.
24. Administrar materiales.
25. Cambiar parámetros.
26. Calcular todo.
27. Lista de materiales.

También auditar los accesos directos de la cinta:

- Empalme.
- Vaciado.
- Combinar.
- Dividir cuerpo.
- Mover/copiar.

### REGLA OBLIGATORIA

Inspeccionar todos los submenús, diálogos, opciones ocultas, comandos contextuales y variantes.

No asumir que una herramienta tiene una sola implementación.

Cuando un mismo comando aparezca en diferentes espacios, comparar cada contexto funcional.

Crear una matriz que indique:

- Herramienta.
- Espacio donde aparece.
- Implementación utilizada.
- Variantes disponibles.
- Opciones faltantes.
- Diferencias frente a Fusion 360.
- Bugs detectados.
- Pruebas existentes.

---

# PARTE IV — AUDITORÍA INDIVIDUAL DE HERRAMIENTAS

## 5. PULSAR/TIRAR

Comparar con Press Pull de Fusion 360.

Auditar:

- Selección de caras.
- Selección de perfiles.
- Selección de superficies.
- Desplazamiento.
- Desfase.
- Extrusión contextual, cuando corresponda.
- Dirección positiva y negativa.
- Entrada numérica.
- Manipulador.
- Vista previa.
- Operaciones booleanas.
- Selección de cuerpos afectados.
- Edición posterior.

Investigar cómo decide Fusion 360 qué operación realizar según el elemento seleccionado.

Probar:

- Caras planas.
- Caras cilíndricas.
- Caras curvas.
- Perfiles cerrados.
- Superficies.
- Selecciones múltiples.
- Geometrías parcialmente superpuestas.

No permitir que el comando ejecute una operación distinta de la esperada según el tipo de entidad.

## 6. EMPALME

Comparar con Fillet.

Auditar todas las variantes aplicables:

- Radio constante.
- Radio variable.
- Múltiples aristas.
- Cadenas tangentes.
- Selección de caras.
- Empalmes de caras, cuando estén disponibles.
- Tipos de esquina.
- Condiciones de continuidad.
- Opciones avanzadas.
- Empalmes parciales.
- Edición posterior.

Probar:

- Aristas convexas.
- Aristas cóncavas.
- Aristas muy pequeñas.
- Esquinas complejas.
- Intersecciones de varios empalmes.
- Cuerpos con paredes delgadas.
- Geometría cilíndrica.
- Superficies.
- Radios próximos al máximo geométrico.

Comprobar continuidad, validez B-Rep, normales y conservación de volumen.

**No aceptar empalmes que produzcan caras sueltas, cuerpos abiertos o geometría inválida sin informar un error.**

## 7. CHAFLÁN

Comparar con Chamfer de Fusion 360.

Auditar los modos documentados, incluyendo cuando correspondan:

- Distancias iguales.
- Dos distancias.
- Distancia y ángulo.
- Cadenas de aristas.
- Inversión de dirección.
- Esquinas.
- Selección múltiple.
- Edición posterior.

Probar valores límite, superficies curvas, uniones entre aristas y chaflanes de tamaño próximo al espesor de las paredes.

Verificar matemáticamente distancias y ángulos.

## 8. QUITAR EMPALMES

Auditar:

- Identificación de caras de empalme.
- Selección manual.
- Selección automática, si existe.
- Reconstrucción de caras originales.
- Restauración de aristas.
- Empalmes combinados.
- Empalmes parciales.
- Superficies complejas.
- Edición paramétrica.

Verificar que la eliminación del empalme reconstruya correctamente la geometría subyacente sin generar caras faltantes ni intersecciones inválidas.

## 9. VACIADO

Comparar con Shell de Fusion 360.

Auditar:

- Selección de caras a eliminar.
- Espesor interior.
- Espesor exterior.
- Modos de dirección disponibles.
- Espesores múltiples cuando corresponda.
- Cuerpos cerrados.
- Cuerpos abiertos.
- Superficies curvas.
- Esquinas.
- Geometría con empalmes.
- Paredes delgadas.
- Edición posterior.

Comprobar el espesor geométrico real.

Probar modelos complejos y detectar autointersecciones, paredes degeneradas y errores topológicos.

No aceptar resultados aparentemente exitosos que produzcan cuerpos abiertos o espesores incorrectos.

## 10. DESMOLDEO

Comparar con Draft.

Auditar:

- Plano neutro.
- Línea de partición.
- Caras seleccionadas.
- Dirección de extracción.
- Ángulo.
- Inversión de dirección.
- Selección múltiple.
- Caras tangentes.
- Superficies curvas.
- Edición posterior.

Comprobar que el ángulo de desmoldeo real coincida con el introducido.

Verificar que se mantengan las zonas o referencias que deben permanecer fijas.

## 11. ESCALA

Comparar con Scale de Fusion 360.

Auditar:

- Escala uniforme.
- Escala no uniforme.
- Punto base.
- Factor.
- Selección de cuerpos.
- Selección de componentes.
- Cuerpos de superficie.
- Geometría compleja.
- Transformaciones acumuladas.
- Edición posterior.

Probar factores:

- Mayores que uno.
- Entre cero y uno.
- Uno.
- Cero.
- Negativos, según las reglas reales de cada modo.
- Valores extremos.

Comprobar dimensiones, volumen, orientación y referencias.

Investigar la interacción con cuerpos paramétricos y operaciones posteriores.

## 12. COMBINAR

Comparar con Combine.

Auditar:

- Unir.
- Cortar.
- Intersecar.
- Cuerpo objetivo.
- Cuerpos herramienta.
- Conservar herramientas.
- Selección múltiple.
- Cuerpos separados.
- Cuerpos tangentes.
- Cuerpos parcialmente superpuestos.
- Resultados con múltiples regiones.
- Edición posterior.

Validar mediante volumen, topología y caja envolvente.

Comprobar que no desaparezca material inesperadamente ni se modifiquen cuerpos no seleccionados.

## 13. DESFASE

Auditar el comportamiento de Offset Face y los comandos equivalentes según el espacio.

Incluir:

- Desfase de caras.
- Desfase de superficies.
- Distancia.
- Dirección.
- Caras tangentes.
- Cadenas.
- Superficies abiertas.
- Superficies cerradas.
- Geometría curva.
- Edición posterior.

Verificar la distancia real entre superficies según el método geométrico correspondiente.

Comprobar diferencias entre desfase de caras sólidas y creación de superficies desplazadas.

## 14. REEMPLAZAR CARA

Comparar con Replace Face.

Auditar:

- Cara objetivo.
- Superficie de reemplazo.
- Cuerpo de reemplazo cuando corresponda.
- Extensión de caras.
- Recorte.
- Intersección.
- Caras planas.
- Caras curvas.
- Superficies inclinadas.
- Edición posterior.

Comprobar continuidad geométrica, conservación del volumen correspondiente y validez B-Rep.

## 15. EDITAR CARA

Investigar la función exacta de OmniCAD y su equivalencia documentada en Fusion 360.

Auditar:

- Selección de cara.
- Modificación geométrica.
- Edición de contorno.
- Transformaciones.
- Parámetros disponibles.
- Caras adyacentes.
- Actualización topológica.
- Edición posterior.

No confundir Editar cara con Pulsar/tirar, Desfase o Reemplazar cara si internamente son operaciones distintas.

Verificar que las modificaciones mantengan un cuerpo geométricamente válido.

## 16. DIVIDIR CARA

Comparar con Split Face.

Auditar:

- Selección de caras.
- Herramienta de división.
- Planos.
- Bocetos.
- Superficies.
- Curvas proyectadas.
- Dirección de división.
- Extensión de herramientas.
- Resultados con varias regiones.
- Edición posterior.

Comprobar que se creen las caras correspondientes sin modificar injustificadamente el volumen.

## 17. DIVIDIR CUERPO

Comparar con Split Body.

Auditar:

- Selección del cuerpo.
- Selección de herramienta de corte.
- Planos.
- Caras.
- Superficies.
- Extensión de herramienta.
- Múltiples cuerpos resultantes.
- División parcial.
- Edición posterior.

Comprobar conservación de volumen, validez de los cuerpos y actualización correcta del navegador y timeline.

## 18. DIVISIÓN DE SILUETA

Investigar el comportamiento de Silhouette Split y las funciones relacionadas de Fusion 360.

Auditar:

- Dirección.
- Vector.
- Selección de caras.
- Detección de silueta.
- Geometría curva.
- Superficies tangentes.
- División topológica.
- Casos de varias regiones.
- Edición posterior.

Comprobar que el cálculo de la silueta sea geométricamente correcto y estable.

## 19. ENTRAMADO VOLUMÉTRICO

Identificar la referencia funcional correcta de Fusion 360 y las capacidades implementadas en OmniCAD.

Auditar:

- Tipo de estructura.
- Patrones volumétricos.
- Celdas.
- Densidad.
- Tamaño.
- Espesor.
- Orientación.
- Recorte contra volumen.
- Regiones de aplicación.
- Geometría interna.
- Resultado sólido o de malla.
- Edición posterior.

Incluir las estructuras periódicas y variantes disponibles.

Comprobar:

- Continuidad.
- Ausencia de autointersecciones inválidas.
- Espesores.
- Topología.
- Volumen.
- Rendimiento.
- Exportación compatible con fabricación, cuando corresponda.

No asumir que una representación visual del entramado equivale a una geometría imprimible.

## 20. MOVER/COPIAR

Comparar con Move/Copy de Fusion 360.

Auditar todos los modos:

- Traslación.
- Rotación.
- Traslación libre.
- Traslación punto a punto.
- Rotación alrededor de eje.
- Transformación mediante manipuladores.
- Copiar.
- Mover cuerpos.
- Mover caras.
- Mover componentes.
- Mover superficies.
- Selección múltiple.
- Referencias.
- Coordenadas locales y globales.
- Edición posterior.

Verificar que las transformaciones sean exactas y se apliquen a las entidades correctas.

Comprobar que una copia sea independiente o asociativa según el comportamiento documentado del modo utilizado.

## 21. ALINEAR

Comparar con Align.

Auditar:

- Cara a cara.
- Arista a arista.
- Punto a punto.
- Ejes.
- Planos.
- Orígenes.
- Orientación.
- Inversión.
- Distancia.
- Desfase.
- Posición.
- Selección de cuerpos.
- Selección de componentes.

Verificar que la geometría se alinee correctamente sin movimientos adicionales inesperados.

## 22. APOYAR EN EL PLANO

Identificar el equivalente funcional real en Fusion 360 y auditar:

- Selección de cuerpo.
- Selección de plano.
- Selección de cara.
- Orientación.
- Rotación.
- Contacto.
- Posición.
- Transformación.
- Edición posterior.

Comprobar que la pieza quede apoyada sobre la referencia seleccionada sin penetración ni separación geométrica inesperada.

## 23. SUPRIMIR

Comparar con la supresión de operaciones y entidades en Fusion 360.

Auditar:

- Supresión de operaciones.
- Supresión de componentes.
- Supresión de cuerpos o elementos, según corresponda.
- Reactivación.
- Dependencias.
- Recalculo.
- Referencias.
- Persistencia.
- Deshacer y rehacer.

La supresión debe conservar la posibilidad de recuperación de acuerdo con el modelo paramétrico.

## 24. QUITAR

Investigar la diferencia exacta entre Quitar, Eliminar y Suprimir en Fusion 360 y OmniCAD.

Auditar:

- Eliminación de entidades.
- Eliminación de operaciones.
- Eliminación de cuerpos.
- Dependencias.
- Historial.
- Referencias.
- Recuperación mediante deshacer.
- Recalculo.

**No permitir que Quitar y Suprimir se comporten idénticamente si representan operaciones semánticamente diferentes.**

## 25. SIMPLIFICAR

Investigar los flujos y comandos equivalentes de Fusion 360.

Auditar:

- Eliminación de detalles.
- Simplificación geométrica.
- Simplificación de caras.
- Eliminación de elementos pequeños.
- Reducción de complejidad.
- Conservación del volumen cuando corresponda.
- Precisión.
- Calidad topológica.
- Configuración y parámetros.
- Edición posterior.

Medir cuánto se simplifica realmente el modelo.

Comparar cantidad de caras, tamaño de datos y desviación geométrica.

No aceptar simplificaciones que destruyan detalles esenciales sin advertencia.

## 26. MATERIAL FÍSICO

Comparar con Physical Material.

Auditar:

- Biblioteca.
- Categorías.
- Selección.
- Asignación.
- Edición.
- Material por cuerpo.
- Material por componente.
- Propiedades físicas.
- Densidad.
- Masa.
- Propiedades de material disponibles.
- Persistencia.

Comprobar que cambiar un material actualice correctamente las propiedades físicas dependientes.

## 27. ASPECTO

Comparar con Appearance.

Auditar:

- Biblioteca de apariencias.
- Asignación.
- Cuerpo.
- Cara.
- Componente.
- Colores.
- Texturas.
- Acabados.
- Opacidad.
- Brillo.
- Materiales personalizados.
- Vista previa.
- Persistencia.
- Integración con RENDERIZAR.

Diferenciar correctamente las propiedades visuales de las propiedades físicas.

## 28. ADMINISTRAR MATERIALES

Comprobar si el comando está implementado, deshabilitado o incompleto.

Investigar las herramientas equivalentes documentadas de Fusion 360.

Auditar:

- Gestión de bibliotecas.
- Materiales favoritos.
- Materiales personalizados.
- Propiedades.
- Edición.
- Duplicación.
- Importación.
- Persistencia.
- Integración con materiales físicos y apariencias.

No habilitar un botón sin implementar su funcionamiento real.

## 29. CAMBIAR PARÁMETROS

Comparar con Change Parameters.

Auditar:

- Parámetros de usuario.
- Parámetros del modelo.
- Unidades.
- Expresiones.
- Dependencias.
- Renombrado.
- Evaluación.
- Detección de ciclos.
- Referencias.
- Actualización de cotas.
- Recalculo de operaciones.
- Persistencia.

Comprobar que cambiar un parámetro actualice únicamente las operaciones dependientes, sin generar resultados incoherentes.

## 30. CALCULAR TODO

Comparar con Compute All.

Auditar:

- Recalculo completo.
- Dependencias.
- Orden de operaciones.
- Parámetros.
- Caché.
- Estados inválidos.
- Errores.
- Progreso.
- Cancelación cuando corresponda.
- Rendimiento.
- Consistencia con el resultado guardado.

Probar documentos con numerosas operaciones y dependencias encadenadas.

Comprobar que el resultado final sea determinista dentro de las tolerancias numéricas.

## 31. LISTA DE MATERIALES

Investigar el comportamiento funcional equivalente de Fusion 360.

Auditar:

- Componentes.
- Cuerpos.
- Cantidades.
- Materiales.
- Propiedades.
- Identificadores.
- Actualización.
- Agrupación.
- Exportación cuando esté disponible.
- Integración con ensamblajes.
- Persistencia.

Verificar que las cantidades y propiedades correspondan al modelo real.

---

# PARTE V — AUDITORÍA TRANSVERSAL DE ESPACIOS

## 32. SÓLIDO, SUPERFICIE, PLÁSTICO Y CHAPA

Para cada herramienta, comprobar todas las implementaciones y contextos donde se utiliza.

### SÓLIDO

Validar operaciones B-Rep, volúmenes, caras, aristas y dependencias.

### SUPERFICIE

Validar:

- Superficies abiertas.
- Superficies cerradas.
- Continuidad.
- Bordes.
- Normales.
- Recortes.
- Empalmes.
- Desfases.
- Transformaciones.
- Cosido y engrosado relacionados.

No crear sólidos cuando el comando de referencia debe producir superficies.

### PLÁSTICO

Validar interacción con:

- Espesores.
- Nervios.
- Salientes.
- Redes.
- Labios.
- Fijaciones.
- Desmoldeos.
- Empalmes.
- Reglas de diseño plástico.

Comprobar que las modificaciones mantengan la intención de diseño y no generen paredes inválidas.

### CHAPA

Validar:

- Espesor constante.
- Reglas de chapa.
- Radios de plegado.
- Uniones.
- Desarrollabilidad.
- Patrón plano.
- Compatibilidad de operaciones.
- Conservación de pliegues.

Las modificaciones que no sean compatibles con las reglas de chapa deben rechazarse correctamente, sin corromper la pieza.

### MALLA Y OTROS ESPACIOS

Auditar las herramientas equivalentes cuando existan.

Investigar sus diferencias y evitar utilizar operaciones B-Rep sobre mallas sin una conversión explícita o un método compatible.

---

# PARTE VI — AUDITORÍA GEOMÉTRICA PROFUNDA

## 33. REVISIÓN DEL KERNEL

Inspeccionar las implementaciones en:

- `clon/omnicad/nucleo/`
- `clon/omnicad/timeline/`
- `clon/omnicad/ui/`
- `clon/omnicad/ui/comandos/`
- `clon/omnicad/api/`

Localizar todas las funciones relacionadas con las herramientas de modificación.

Comprobar:

1. Geometría B-Rep válida.
2. Orientación de caras.
3. Normales.
4. Volumen.
5. Área.
6. Caja envolvente.
7. Cuerpos cerrados.
8. Continuidad.
9. Intersecciones.
10. Aristas degeneradas.
11. Autointersecciones.
12. Precisión numérica.
13. Tolerancias.
14. Topología persistente.
15. Referencias paramétricas.
16. Robustez de booleanas.

No considerar correcta una operación únicamente porque OpenCascade no produjo una excepción.

Comprobar el resultado mediante propiedades geométricas medibles.

---

# PARTE VII — SELECCIÓN Y EXPERIENCIA DE USUARIO

## 34. AUDITORÍA DE INTERFAZ

Para cada comando comprobar:

- Selección mediante mouse.
- Selección múltiple.
- Selección de caras.
- Selección de aristas.
- Selección de vértices.
- Selección de cuerpos.
- Selección de componentes.
- Filtros.
- Resaltado.
- Vista previa.
- Asas.
- Flechas.
- Giro.
- Distancia.
- Inversión.
- Entrada numérica.
- Menús.
- Submenús.
- Aceptar.
- Cancelar.
- Escape.
- Enter.
- Atajos.
- Clic derecho.
- Edición posterior.

### MANIPULADORES

Verificar que:

- Las flechas estén correctamente orientadas.
- La distancia responda al arrastre.
- La dirección coincida con la operación.
- El valor mostrado corresponda al movimiento real.
- Se puedan introducir valores precisos.
- No existan saltos inesperados.
- No se pierda la selección.
- La vista previa coincida con el resultado definitivo.

Comparar el comportamiento interactivo con Fusion 360.

---

# PARTE VIII — TIMELINE Y ASOCIATIVIDAD

## 35. PRUEBAS PARAMÉTRICAS

Para todas las herramientas:

1. Crear operación.
2. Modificar parámetros.
3. Editar operación en timeline.
4. Cambiar geometría de origen.
5. Cambiar referencias válidas.
6. Suprimir.
7. Reactivar.
8. Deshacer.
9. Rehacer.
10. Guardar.
11. Cerrar.
12. Reabrir.
13. Recalcular.

Verificar que el sistema no pierda referencias ni genere cambios inesperados.

### ESPECIAL ATENCIÓN A TOPOLOGÍA

Las operaciones de Empalme, Chaflán, Dividir, Combinar, Reemplazar cara, Vaciado y Desfase pueden modificar significativamente la topología.

Auditar la estabilidad de referencias a caras, aristas, cuerpos y perfiles.

Si una referencia deja de existir, informar el conflicto en lugar de reutilizar silenciosamente una entidad incorrecta.

---

# PARTE IX — PRUEBAS COMBINADAS

## 36. ESCENARIOS REALES

Crear y comprobar, como mínimo:

1. Prisma → Empalme → Vaciado.
2. Prisma → Chaflán → Empalme.
3. Cilindro → Desfase de cara → Agujero.
4. Dos cuerpos → Combinar → Empalme.
5. Cuerpo → Dividir cuerpo → Mover/copiar.
6. Superficie → Reemplazar cara → Engrosar.
7. Cuerpo complejo → Quitar empalmes.
8. Cuerpo → Desmoldeo → Vaciado.
9. Componente → Alinear → Mover/copiar.
10. Chapa → Modificación compatible → Patrón plano.
11. Geometría plástica → Vaciado → Nervio.
12. Modelo complejo → Simplificar.
13. Cuerpo → Asignar material físico → Medir masa.
14. Cuerpo → Aspecto → Renderizar.
15. Modificar parámetro → Calcular todo.
16. Dividir cara → Editar cara.
17. Entramado volumétrico → Validar geometría resultante.
18. Suprimir una operación → Reactivarla.
19. Modificar cara → Recalcular operaciones posteriores.
20. Importar STEP → Modificar → Guardar.

Probar también combinaciones adversariales con geometrías extremas, referencias ambiguas y resultados imposibles.

Los casos incompatibles deben generar errores claros y seguros.

---

# PARTE X — DETECCIÓN Y REPARACIÓN

## 37. REPARACIÓN OBLIGATORIA DE BUGS

**La auditoría incluye la autorización para corregir todos los bugs confirmados dentro de este alcance.**

Para cada defecto:

1. Reproducir.
2. Registrar evidencia.
3. Identificar causa raíz.
4. Crear test que falle.
5. Corregir implementación.
6. Ejecutar test.
7. Medir resultado geométrico.
8. Probar desde la interfaz.
9. Ejecutar regresiones.
10. Revisar mediante `ponytail-review`.
11. Documentar e integrar.

No detenerse después de detectar los errores.

### PROHIBIDO

- Ocultar errores.
- Eliminar tests que fallen.
- Cambiar resultados esperados sin justificación.
- Crear soluciones que solo funcionen en un ejemplo.
- Marcar herramientas incompletas como terminadas.
- Aceptar geometría inválida silenciosamente.
- Romper operaciones existentes para corregir otras.
- Introducir dependencias nuevas sin autorización.

---

## 38. FUNCIONES FALTANTES

Comparar todas las herramientas con Fusion 360.

Identificar:

- Modos inexistentes.
- Opciones faltantes.
- Parámetros incompletos.
- Manipuladores ausentes.
- Selecciones no admitidas.
- Errores de edición.
- Diferencias en valores predeterminados.
- Problemas de persistencia.
- Funciones existentes en la API pero ausentes en UI.
- Funciones que aparecen en UI pero no están implementadas.

**Implementar las funciones faltantes pertenecientes al alcance de la auditoría**, de manera incremental, con pruebas completas.

No implementar opciones incompatibles con el contexto de modelado sin justificación.

---

# PARTE XI — RENDIMIENTO

## 39. OPTIMIZACIÓN

Medir:

- Tiempo de ejecución.
- Tiempo de vista previa.
- Tiempo de recálculo.
- Uso de RAM.
- Consumo de CPU.
- Bloqueos de UI.
- Número de operaciones geométricas.
- Geometrías intermedias innecesarias.

Probar modelos pequeños, medianos y complejos.

Investigar optimizaciones en Python, OpenCascade y, cuando sea justificable, Rust/PyO3.

Medir antes y después de cada optimización.

No reescribir módulos completos sin evidencia de necesidad.

---

# PARTE XII — API, MCP Y CLI

## 40. CONSISTENCIA FUNCIONAL

Todas las herramientas auditadas y sus opciones relevantes deben funcionar coherentemente desde:

- Interfaz gráfica.
- API Python.
- MCP.
- CLI.

Auditar:

- Parámetros.
- Validaciones.
- Valores predeterminados.
- Modos de operación.
- Selección de referencias.
- Resultados geométricos.
- Errores.
- Persistencia.
- Deshacer y rehacer.

Corregir diferencias.

Actualizar el catálogo de herramientas y su documentación conforme a las reglas del proyecto.

---

# PARTE XIII — PRUEBAS AUTOMATIZADAS

## 41. VERIFICACIÓN COMO USUARIO REAL

Utilizar:

- `pytest`.
- `omnicad-test`.
- `scripts/prueba_ui/`.
- Herramientas de prueba de API y MCP.
- Pruebas de humo.
- Pruebas de regresión.
- Caza de errores cuando corresponda.

No considerar suficiente una prueba que únicamente llama una función Python.

Simular el uso real:

1. Abrir el espacio de trabajo.
2. Seleccionar el comando.
3. Elegir geometría desde el visor.
4. Introducir valores.
5. Manipular el resultado.
6. Confirmar.
7. Inspeccionar la geometría.
8. Editar.
9. Deshacer y rehacer.
10. Guardar y recuperar.

Ejecutar pruebas en ventanas pequeñas y resoluciones habituales.

No utilizar eventos que interfieran con el cursor físico del usuario.

---

# PARTE XIV — PLAN DE EJECUCIÓN

## 42. FASES

### FASE 1 — INVENTARIO

Identificar todas las herramientas y variantes disponibles en cada espacio.

### FASE 2 — INVESTIGACIÓN

Analizar las funciones oficiales equivalentes de Fusion 360.

### FASE 3 — AUDITORÍA

Reproducir problemas y comparar resultados.

### FASE 4 — CORRECCIÓN

Reparar bugs confirmados.

### FASE 5 — FUNCIONES FALTANTES

Completar las opciones que correspondan.

### FASE 6 — INTEGRACIÓN

Verificar todos los espacios de trabajo, el kernel, timeline, interfaz, API, MCP y CLI.

### FASE 7 — OPTIMIZACIÓN

Medir y corregir cuellos de botella.

### FASE 8 — REGRESIÓN

Comprobar que los cambios no afecten negativamente otras operaciones.

### FASE 9 — VALIDACIÓN FINAL

Confirmar resultados contra la referencia documentada de Fusion 360.

El agente coordinador puede ejecutar estas fases sin solicitar aprobación entre tareas ordinarias.

Respetar las reglas del repositorio sobre permisos, dependencias, commits y pruebas completas.

Cada corrección debe quedar individualmente verificada antes de pasar a la siguiente.

---

# PARTE XV — REGISTRO Y DOCUMENTACIÓN

## 43. SEGUIMIENTO

Actualizar:

- `docs/seguimiento/bugs.md`
- `docs/seguimiento/faltantes.md`
- `docs/seguimiento/mejoras.md`
- `PROJECT_LOG.md`
- `PROJECT_CONTEXT.md`
- Documentación técnica afectada.
- Pruebas automatizadas.
- Documentación de API/MCP.

Respetar la fuente única de pendientes y las reglas de cierre.

Los problemas resueltos deben quedar registrados con evidencia.

Los problemas no resueltos deben permanecer identificados y documentados.

---

# PARTE XVI — INFORME FINAL

## 44. MATRIZ DE RESULTADOS

Crear una matriz completa por herramienta y espacio.

| Herramienta | Espacio | Variantes | Bugs encontrados | Bugs corregidos | Faltantes resueltos | Estado |
|---|---|---|---|---|---|---|
| Empalme | SÓLIDO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Empalme | SUPERFICIE | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Vaciado | SÓLIDO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Desmoldeo | PLÁSTICO | Resultado | Cantidad | Cantidad | Cantidad | Estado |
| Combinar | SÓLIDO | Resultado | Cantidad | Cantidad | Cantidad | Estado |

Completar la matriz con todas las herramientas identificadas.

### ESTADOS

- VERIFICADO.
- CORREGIDO.
- MEJORADO.
- PARCIAL.
- PENDIENTE.
- NO VERIFICADO.
- NO APLICA.

### ENTREGABLES

1. Inventario completo.
2. Comparación funcional con Fusion 360.
3. Bugs detectados.
4. Bugs corregidos.
5. Funciones faltantes.
6. Funciones implementadas.
7. Mejoras de geometría.
8. Mejoras de interfaz.
9. Mejoras paramétricas.
10. Mejoras de rendimiento.
11. Tests ejecutados y sus resultados reales.
12. Capturas y evidencias.
13. Problemas pendientes.
14. Estado final por herramienta y espacio.

---

# PARTE XVII — CRITERIOS DE ACEPTACIÓN

## 45. CONDICIONES PARA FINALIZAR

La auditoría estará completa solamente cuando:

1. Todas las herramientas hayan sido inventariadas.
2. Todas las variantes estén identificadas.
3. Se hayan investigado sus equivalentes de Fusion 360.
4. Se hayan ejecutado pruebas funcionales.
5. Los bugs encontrados se hayan corregido o documentado explícitamente como pendientes.
6. Las opciones faltantes se hayan implementado o se indiquen los bloqueos reales.
7. Las operaciones produzcan geometría válida.
8. Los resultados respeten las tolerancias y dimensiones esperadas.
9. Los manipuladores funcionen correctamente.
10. Las vistas previas coincidan con los resultados finales.
11. Las operaciones se puedan editar.
12. Las referencias paramétricas se conserven.
13. El timeline se recalcule adecuadamente.
14. El guardado y reapertura funcionen.
15. API, MCP y CLI sean consistentes.
16. No existan regresiones nuevas sin registrar.
17. La documentación y los tests estén actualizados.
18. Las diferencias pendientes respecto de Fusion 360 estén identificadas.

**No declarar paridad total con Fusion 360 si existen diferencias funcionales no verificadas o pendientes.**

---

# ORDEN FINAL DE EJECUCIÓN

**Realizá una auditoría completa de todas las herramientas de MODIFICAR de OmniCAD en SÓLIDO, SUPERFICIE, PLÁSTICO, CHAPA, MALLA y cualquier otro espacio donde aparezcan.**

Investigá exhaustivamente su comportamiento en Fusion 360 mediante la documentación oficial.

Inspeccioná todas las variantes y opciones, incluso las que no aparecen directamente en la captura.

**DETECTÁ → REPRODUCÍ → DIAGNOSTICÁ → REPARÁ → COMPLETÁ → OPTIMIZÁ → PROBÁ → VERIFICÁ.**

No quiero únicamente un informe de diferencias.

Quiero código reparado, funciones completadas, operaciones geométricamente correctas, experiencia de usuario profesional y pruebas verificables.

Las herramientas deben funcionar de manera coherente entre todos los espacios aplicables, respetando las diferencias funcionales de Fusion 360.

**La prioridad absoluta es que las operaciones sean geométricamente correctas, paramétricamente estables, fáciles de utilizar y confiables.**

No declares una tarea terminada sin demostrar su funcionamiento real y sin ejecutar las verificaciones correspondientes.
```
