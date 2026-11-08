# Auditoría y reparación de las herramientas 3D contra Fusion 360

Pedido de Gerardo (2026-11-07): auditar, reparar y completar contra Fusion 360 Agujero, Rosca, Prisma rectangular,
Cilindro, Esfera, Toroide, Bobina, Tubería, Engranaje, Eje, Patrón, Simetría, Engrosar, Llenado de contorno, Sólido
delimitador y Volumen de fluido, en todos los espacios donde aparecen (SÓLIDO, SUPERFICIE, PLÁSTICO, CHAPA y los demás).
Mismo procedimiento que [auditoria_boceto_crear_modificar.md](auditoria_boceto_crear_modificar.md): ejecutan los
agentes, Claude solo como última instancia, y al final todo verde.

**Cuándo:** otro día, el que elija Gerardo. Va 2.ª de 6; orden y reparto en [agenda.md](seguimiento/agenda.md) (sección «Orden y reparto de las auditorías»).

## Prompt para el agente

Guardado el 2026-11-07. Modelo sugerido: coordina una sesión Claude Opus 5 con esfuerzo alto; ejecutan Sol (OpenCode) y los agentes gratis aprobados, un ítem por corrida y cada uno en su worktree.

```text
AJUSTE DEL COORDINADOR (2026-11-08; manda sobre todo lo que sigue)
- PORTÓN DE CIERRE OBLIGATORIO: esta auditoría no se cierra hasta pasar los 5 puntos de docs/auditorias/porton_auditoria.md (matriz de combinaciones con invariantes, prueba en la ventana, pieza real, juez independiente con otro modelo y cerrar la clase de cada bug).
- Orden de las seis auditorías (de a una; la siguiente arranca cuando la anterior quedó cerrada y commiteada): 1) CONSTRUIR (AG-7), 2) herramientas 3D (AG-2), 3) MODIFICAR (AG-4), 4) INSERTAR (AG-6), 5) ENSAMBLAR (AG-5), 6) RENDERIZAR (AG-3). Cada herramienta tiene UNA sola auditoría dueña. Las demás solo la usan en sus pruebas combinadas: si encuentran un bug en una herramienta ajena, cargan la fila en docs/seguimiento/ y la arreglan solo si la dueña ya pasó (está antes en el orden); si la dueña viene después, dejan la fila para ella.
- Sos la dueña de las herramientas de tu lista (Agujero a Volumen de fluido, con Patrón, Simetría y Engrosar). NO audites planos, ejes ni puntos de construcción (son de CONSTRUIR, AG-7): si encontrás un bug ahí, cargá la fila y seguí.
- ROSCAS (Gerardo, 2026-11-08): cuando le toque su turno, esta auditoría empieza por el ANEXO del final (Rosca, Agujero roscado, tablas y velocidad contra Fusion); después el resto de la lista.

# PROMPT MAESTRO — AUDITORÍA, REPARACIÓN Y PARIDAD FUNCIONAL DE HERRAMIENTAS 3D DE OMNICAD CON FUSION 360

## 1. MISIÓN PRINCIPAL

Actuá como un **equipo senior de ingeniería y desarrollo de sistemas CAD 3D paramétricos**, especializado en:

- Arquitectura de aplicaciones CAD profesionales.
- Modelado geométrico B-Rep.
- OpenCascade y geometría computacional.
- Modelado sólido y de superficies.
- Diseño de piezas plásticas.
- Diseño de chapa metálica.
- Operaciones booleanas y topología.
- Geometría paramétrica y sistemas de referencias.
- Algoritmos de modelado y estabilidad numérica.
- Interfaces CAD y manipulación tridimensional.
- Automatización de pruebas.
- Optimización de rendimiento.

Tu misión es **auditar, investigar, comparar, corregir, completar y optimizar todas las herramientas identificadas en esta solicitud, en TODOS los espacios de trabajo de OmniCAD donde estén disponibles**.

### OBJETIVO FUNDAMENTAL

Conseguir que las herramientas tengan un comportamiento funcional equivalente al de Autodesk Fusion 360 en:

1. Capacidades disponibles.
2. Opciones y parámetros.
3. Funcionamiento geométrico.
4. Interacción con el usuario.
5. Precisión.
6. Edición paramétrica.
7. Comportamiento de las operaciones.
8. Previsualización.
9. Gestión de referencias.
10. Robustez y estabilidad.

**No quiero únicamente una auditoría documental. Quiero que se detecten los errores, se corrijan los bugs, se completen las opciones faltantes y se validen los resultados reales.**

La meta es alcanzar la mayor paridad funcional verificable posible con Fusion 360, manteniendo a OmniCAD como una implementación independiente.

---

## 2. INSTRUCCIONES OBLIGATORIAS DEL PROYECTO

Antes de comenzar:

1. Leer completamente `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` y `PROJECT_CONTEXT.md`.
2. Invocar las skills `fable-method` y `ponytail` mediante la herramienta Skill.
3. Utilizar `plan-then-do`, `tool-calling-guard` y `verify-before-commit`.
4. Utilizar `ponytail-audit` para auditorías técnicas.
5. Utilizar `omnicad-test` para verificar el funcionamiento real en la interfaz.
6. Invocar `ponytail-review` al finalizar cada corrección.
7. Respetar la arquitectura, las reglas de Git y la política de integración.
8. No instalar dependencias nuevas sin autorización.
9. No copiar código, recursos o implementaciones propietarias de Autodesk.
10. No realizar `git push`.

El agente coordinador deberá organizar las tareas, asignarlas según su complejidad y verificar cada corrección antes de integrarla.

---

# PARTE I — INVESTIGACIÓN OFICIAL DE FUSION 360

## 3. DOCUMENTACIÓN DE REFERENCIA

La fuente principal y obligatoria será la documentación oficial de Autodesk Fusion 360 disponible localmente:

`docs/fusion_docs/`

Consultar especialmente:

- `fusion-model`
- `fusion-patch`
- `fusion-sheet-metal`
- `fusion-assemble`
- `fusion-simulate`
- `fusion-cam`
- `fusion-sketch`

Investigar también la documentación relacionada con diseño plástico, cuando corresponda.

Utilizar el buscador existente:

`scripts/fusion_docs.py buscar`

Y consultar los artículos mediante:

`scripts/fusion_docs.py ver`

No recorrer indiscriminadamente los miles de archivos descargados. Utilizar los índices correspondientes y los mecanismos de búsqueda disponibles.

### Fuentes complementarias

Utilizar también:

- Documentación oficial de Autodesk publicada en Internet.
- Material de referencia existente en el proyecto.
- Capturas de Fusion 360.
- Análisis funcionales previos.
- Ejemplos oficiales de Autodesk.
- Pruebas comparativas entre Fusion 360 y OmniCAD.

Consultar la documentación actual para detectar opciones incorporadas en versiones más recientes.

### REGLA ESTRICTA

**Antes de corregir o implementar una herramienta, investigar todas sus opciones en Fusion 360.**

No desarrollar basándose únicamente en el nombre del comando o en su funcionamiento aparente.

Para cada herramienta, registrar:

- Ubicación en Fusion 360.
- Propósito.
- Modos de operación.
- Parámetros disponibles.
- Opciones avanzadas.
- Valores predeterminados.
- Tipos de entidades admitidas.
- Comportamiento de selección.
- Resultado geométrico esperado.
- Comportamiento de la vista previa.
- Reglas de edición posterior.
- Limitaciones documentadas.

Si una herramienta de OmniCAD no tiene equivalente directo en Fusion 360, identificarlo. No inventar una equivalencia.

---

# PARTE II — ALCANCE DE LA AUDITORÍA

## 4. TODOS LOS ESPACIOS DE TRABAJO

No limitar la investigación al menú de la captura.

Auditar las herramientas en:

### SÓLIDO

Todas las herramientas incluidas en esta solicitud, sus variantes, opciones y conexiones con otras operaciones.

### SUPERFICIE

Todas las herramientas compartidas o equivalentes.

Comprobar que la geometría de superficie conserve el comportamiento correcto y no se convierta injustificadamente en sólidos.

### PLÁSTICO

Todas las herramientas compartidas y sus interacciones con:

- Reglas de diseño plástico.
- Espesores.
- Nervios.
- Salientes.
- Apoyos.
- Fijaciones.
- Redes.
- Operaciones específicas de plástico.

### CHAPA

Auditar las herramientas que estén disponibles en CHAPA o intervengan en sus operaciones.

Comprobar especialmente:

- Conservación del espesor.
- Reglas de chapa.
- Radios y pliegues.
- Desarrollo plano.
- Operaciones compatibles e incompatibles.
- Persistencia de las propiedades de chapa.
- Coherencia con el comportamiento de Fusion 360.

### OTROS ESPACIOS

Incluir cualquier otro entorno donde las herramientas estén disponibles o tengan una implementación relacionada:

- MALLA.
- ENSAMBLAR.
- SIMULACIÓN, si corresponde.
- FABRICACIÓN, si corresponde.
- Otros contextos de diseño.

No asumir que una herramienta debe funcionar idénticamente en todos los espacios. Investigar las diferencias reales de Fusion 360.

**Una herramienta compartida debe conservar un núcleo geométrico coherente, pero respetar los parámetros y reglas particulares de cada contexto.**

---

# PARTE III — INVENTARIO COMPLETO DE HERRAMIENTAS

## 5. HERRAMIENTAS OBLIGATORIAS

Auditar exhaustivamente las siguientes:

1. Agujero.
2. Rosca.
3. Prisma rectangular.
4. Cilindro.
5. Esfera.
6. Toroide.
7. Bobina.
8. Tubería.
9. Engranaje.
10. Eje.
11. Patrón y todas sus variantes.
12. Simetría.
13. Engrosar.
14. Llenado de contorno.
15. Sólido delimitador.
16. Volumen de fluido.

También deben incluirse todos los submenús y modos disponibles de estas herramientas.

**Si un mismo comando aparece en diferentes pestañas, auditar cada acceso y su comportamiento contextual.**

No considerar que una única prueba valida todas las variantes.

---

# PARTE IV — AUDITORÍA INDIVIDUAL

## 6. AGUJERO

Comparar con el comando Hole de Fusion 360.

Auditar:

- Agujero simple.
- Escariado.
- Avellanado.
- Agujeros roscados.
- Agujeros de separación para tornillos, cuando estén disponibles.
- Posicionamiento sobre caras.
- Posicionamiento mediante puntos de boceto.
- Posicionamiento concéntrico.
- Referencias a aristas.
- Profundidad.
- Hasta objeto.
- A través de todo.
- Dirección.
- Punta de perforación.
- Diámetro.
- Ángulos.
- Compensaciones y desfases.
- Selección del cuerpo afectado.
- Edición posterior.

Comprobar la exactitud del resultado en secciones y mediciones geométricas.

Verificar que un agujero no corte accidentalmente otros cuerpos.

## 7. ROSCA

Comparar con Thread de Fusion 360.

Auditar:

- Roscas internas.
- Roscas externas.
- Roscas modeladas.
- Roscas cosméticas.
- Diámetro nominal.
- Paso.
- Perfil.
- Designación.
- Clase.
- Longitud.
- Desfase.
- Sentido derecho e izquierdo.
- Roscas completas y parciales.
- Selección de superficies cilíndricas.
- Compatibilidad entre rosca y agujero roscado.
- Edición.
- Persistencia.
- Integración con bibliotecas de roscas.

Verificar la geometría mediante medidas y operaciones booleanas cuando corresponda.

Comprobar que las roscas modeladas sean compatibles geométricamente con tornillos y tuercas equivalentes.

## 8. PRISMA RECTANGULAR

Auditar:

- Plano o cara base.
- Posición inicial.
- Longitud.
- Anchura.
- Altura.
- Orientación.
- Manipuladores.
- Introducción directa de dimensiones.
- Creación de cuerpo.
- Unión.
- Corte.
- Intersección.
- Creación de componente, cuando corresponda.
- Cambios posteriores de parámetros.

Verificar dimensiones, volumen y caja envolvente.

Comprobar la creación sobre planos inclinados y caras de cuerpos existentes.

## 9. CILINDRO

Comprobar:

- Centro.
- Plano.
- Diámetro.
- Radio cuando corresponda.
- Altura.
- Orientación.
- Sentido.
- Posicionamiento.
- Operaciones booleanas.
- Edición de dimensiones.
- Precisión de superficies cilíndricas.

Probar cilindros concéntricos, tangentes, intersectados y superpuestos.

## 10. ESFERA

Auditar:

- Centro.
- Diámetro.
- Radio.
- Posicionamiento.
- Unión.
- Corte.
- Intersección.
- Cuerpo nuevo.
- Cambios paramétricos.

Verificar volumen, superficie y validez topológica.

Probar esferas que intersecten otras geometrías de forma tangente o casi tangente.

## 11. TOROIDE

Auditar:

- Diámetro principal.
- Diámetro interior.
- Diámetro de sección.
- Centro.
- Plano.
- Orientación.
- Dimensiones.
- Modos de posicionamiento.
- Operaciones booleanas.
- Edición posterior.

Probar límites geométricos, autointersecciones y parámetros que produzcan geometría imposible.

## 12. BOBINA

Comparar con Coil de Fusion 360.

Auditar todos los modos disponibles de:

- Diámetro.
- Altura.
- Paso.
- Número de vueltas.
- Revoluciones.
- Ángulo.
- Sentido de giro.
- Forma de sección.
- Tamaño de sección.
- Posición de sección.
- Orientación.
- Operaciones booleanas.
- Edición paramétrica.

Probar bobinas helicoidales con distintas configuraciones, incluyendo vueltas parciales y parámetros extremos válidos.

Comprobar que el paso, la altura y el número de revoluciones mantengan la relación matemática correcta para cada modo.

## 13. TUBERÍA

Comparar con Pipe de Fusion 360.

Auditar:

- Selección de trayectoria.
- Trayectorias abiertas.
- Trayectorias cerradas.
- Líneas.
- Arcos.
- Splines.
- Cadenas de aristas.
- Sección transversal.
- Dimensiones.
- Tubo sólido.
- Tubo hueco.
- Espesor.
- Orientación de sección.
- Distancia sobre la ruta.
- Operaciones booleanas.
- Edición posterior.

Verificar continuidad geométrica, cambios de dirección y uniones entre segmentos.

Probar radios de curvatura pequeños y situaciones donde la sección se autointersecte.

## 14. ENGRANAJE

Identificar primero la herramienta equivalente, generador, complemento o flujo oficial disponible en Fusion 360.

No asumir que exista un comando nativo idéntico.

Auditar todas las funciones realmente implementadas en OmniCAD:

- Tipo de engranaje.
- Módulo.
- Número de dientes.
- Ángulo de presión.
- Diámetro primitivo.
- Diámetro exterior.
- Diámetro de raíz.
- Espesor.
- Perfil de dientes.
- Agujero central.
- Holgura.
- Modos de generación.
- Parámetros disponibles.
- Edición posterior.

Investigar otros tipos disponibles en OmniCAD y verificar cada uno.

Comprobar matemáticamente el perfil generado y su compatibilidad con engranajes correspondientes.

No limitar la validación a que el sólido se vea como un engranaje.

## 15. EJE

Investigar el equivalente funcional de Fusion 360 y el alcance real del comando de OmniCAD.

Auditar:

- Segmentos.
- Diámetros.
- Longitudes.
- Escalonamientos.
- Chaflanes y empalmes.
- Ranuras.
- Referencias y posiciones.
- Opciones adicionales disponibles.
- Edición paramétrica.
- Generación del sólido.

Verificar dimensiones, continuidad entre segmentos y ausencia de geometría inválida.

Investigar faltantes funcionales sin atribuir a Fusion 360 comandos que no estén documentados.

---

# PARTE V — OPERACIONES GEOMÉTRICAS COMPARTIDAS

## 16. PATRÓN — AUDITORÍA COMPLETA

Esta herramienta requiere una investigación especialmente profunda.

Auditar todos los patrones existentes:

- Rectangular.
- Circular.
- Sobre trayectoria.
- Basado en puntos.
- En caras, cuando corresponda.
- Patrones de operaciones.
- Patrones de cuerpos.
- Patrones de caras.
- Patrones de componentes.
- Patrones de geometría de superficie.
- Patrones de geometría de chapa, cuando sean compatibles.
- Multitransformación, si está implementada.
- Cualquier otro subtipo disponible.

### Parámetros

Revisar:

- Cantidad.
- Distancia.
- Separación.
- Extensión.
- Dirección.
- Ejes.
- Simetría de distribución.
- Orientación.
- Repetición.
- Selección de objetos.
- Instancias omitidas.
- Edición de instancias.
- Recalculo ante cambios.
- Dependencias.

### Métodos de cálculo

Comparar con las modalidades documentadas de Fusion 360, incluyendo, donde correspondan:

- Optimizado.
- Idéntico.
- Ajustar.

Comprobar que cada modalidad realice el cálculo correspondiente y no sea simplemente una opción visual.

Verificar rendimiento, uso de memoria y exactitud geométrica de patrones complejos.

### Casos especiales

Probar:

- Patrones sobre superficies curvas.
- Patrones de operaciones dependientes.
- Patrones que intersectan varios cuerpos.
- Patrones con cortes.
- Patrones con geometría parcialmente superpuesta.
- Patrones editados después de modificar la pieza original.
- Patrones que dependen de referencias externas.

**Verificar que el patrón conserve su identidad paramétrica y que las instancias respondan correctamente a los cambios del elemento original.**

## 17. SIMETRÍA

Auditar la herramienta Mirror en todos los espacios donde aparezca.

Comprobar:

- Simetría de cuerpos.
- Simetría de caras.
- Simetría de operaciones.
- Simetría de componentes.
- Simetría de superficies.
- Plano de referencia.
- Planos de construcción.
- Caras planas como referencia.
- Selección.
- Operaciones de unión cuando corresponda.
- Conservación de referencias.
- Edición posterior.
- Recalculo.

Verificar que el resultado sea una transformación geométrica especular correcta.

Comprobar normales, orientaciones, validez topológica y geometría resultante.

## 18. ENGROSAR

Comparar con Thicken de Fusion 360.

Auditar:

- Selección de superficies.
- Selección de caras.
- Selección encadenada.
- Espesor positivo.
- Espesor negativo.
- Dirección.
- Engrosado hacia un lado.
- Engrosado simétrico.
- Tipos de esquinas.
- Operaciones booleanas.
- Cuerpos afectados.
- Edición posterior.

Probar superficies abiertas, curvas, complejas y combinadas.

Comprobar:

- Correcta generación de paredes.
- Espesor real.
- Ausencia de autointersecciones.
- Calidad topológica.
- Resultado sólido válido.
- Conservación de referencias.

Verificar especialmente que el engrosado no cree material fuera de la región esperada.

## 19. LLENADO DE CONTORNO

Comparar con Boundary Fill de Fusion 360.

Auditar:

- Selección de cuerpos.
- Selección de superficies.
- Selección de planos.
- Herramientas delimitadoras.
- Detección de celdas.
- Selección individual de celdas.
- Selección múltiple.
- Unión.
- Corte.
- Intersección.
- Cuerpo nuevo.
- Componente nuevo, cuando corresponda.
- Objetos afectados.
- Edición posterior.

Comprobar que las celdas producidas correspondan matemáticamente a los volúmenes delimitados por los objetos seleccionados.

Verificar que no se creen volúmenes inexistentes ni desaparezcan celdas válidas.

## 20. SÓLIDO DELIMITADOR

Identificar primero la finalidad exacta del comando implementado en OmniCAD y su referencia funcional en Fusion 360.

Investigar si corresponde a una herramienta de geometría delimitadora, un cuerpo envolvente, un sólido para fabricación u otra función.

No equiparar herramientas distintas por similitud de nombre.

Auditar todas sus opciones reales.

Comprobar:

- Selección de objetos.
- Generación de volumen.
- Ajuste a geometría.
- Desfases.
- Orientación.
- Dimensiones.
- Interacción con cuerpos existentes.
- Uso posterior del resultado.
- Edición y persistencia.

La implementación final debe corresponder al comportamiento oficialmente documentado de la función que se pretende reproducir.

## 21. VOLUMEN DE FLUIDO

Comparar con Fluid Volume de Fusion 360.

Auditar:

- Selección de cuerpos.
- Volúmenes internos.
- Volúmenes externos.
- Cavidades.
- Regiones cerradas.
- Envolventes.
- Selección de herramientas.
- Detección de fugas.
- Definición de dominio.
- Generación del volumen.
- Actualización del modelo.
- Edición posterior.

Probar:

- Recipientes cerrados.
- Recipientes con abertura.
- Conductos.
- Cavidades conectadas.
- Múltiples cuerpos.
- Ensamblajes.
- Espacios internos complejos.

Verificar que el volumen calculado represente correctamente la región física destinada al fluido.

Investigar las restricciones de disponibilidad del comando en Fusion 360, incluyendo diferencias entre modelado directo, diseño paramétrico y entornos de simulación.

No inventar equivalencias entre esos modos.

---

# PARTE VI — AUDITORÍA DE OPCIONES COMUNES

## 22. OPERACIONES SOBRE CUERPOS

En todas las herramientas que permitan operaciones booleanas, auditar:

- Cuerpo nuevo.
- Componente nuevo.
- Unir.
- Cortar.
- Intersecar.

Comprobar que cada modalidad:

1. Seleccione correctamente los cuerpos afectados.
2. Calcule la geometría correcta.
3. Preserve los cuerpos que no deben modificarse.
4. Mantenga las referencias paramétricas.
5. Actualice el timeline.
6. Genere mensajes adecuados ante errores.

No permitir que un comando muestre una opción funcional que internamente no tenga implementación real.

## 23. MANIPULADORES Y VISTA PREVIA

Auditar exhaustivamente:

- Flechas de distancia.
- Controles de diámetro.
- Asas de rotación.
- Controles de ángulo.
- Puntos de posición.
- Controles de dirección.
- Cambio de sentido.
- Entrada numérica sobre el visor.
- Previsualización durante el arrastre.
- Actualización al escribir valores.

**La vista previa debe corresponder al resultado definitivo.**

Probar arrastres:

- Continuos.
- Rápidos.
- Lentos.
- A través del valor cero.
- Con cambios de dirección.
- Con valores límite.
- En vistas ortogonales.
- En vistas isométricas.
- Sobre planos inclinados.

No deben existir saltos geométricos injustificados, movimientos invertidos, manipuladores desalineados ni pérdidas de selección.

## 24. EDICIÓN PARAMÉTRICA Y TIMELINE

Para cada herramienta:

1. Crear una operación.
2. Cambiar parámetros.
3. Recalcular.
4. Editar mediante doble clic en el timeline.
5. Cambiar referencias.
6. Suprimir la operación.
7. Reactivarla.
8. Deshacer.
9. Rehacer.
10. Guardar.
11. Cerrar.
12. Reabrir.
13. Volver a editar.

Comprobar que se conserven la geometría, los parámetros, las dependencias y las referencias válidas.

Prestar especial atención a los cambios topológicos.

---

# PARTE VII — AUDITORÍA DEL KERNEL Y GEOMETRÍA

## 25. VALIDACIÓN GEOMÉTRICA PROFUNDA

Revisar los módulos responsables de estas operaciones en:

- `clon/omnicad/nucleo/`
- `clon/omnicad/timeline/`
- `clon/omnicad/ui/`
- `clon/omnicad/ui/comandos/`
- `clon/omnicad/api/`

Localizar las implementaciones reales, sin asumir que todas las operaciones están en un archivo específico.

Comprobar:

- Validez B-Rep.
- Cuerpos cerrados.
- Orientación de caras.
- Normales.
- Continuidad.
- Intersecciones.
- Aristas degeneradas.
- Autointersecciones.
- Tolerancias.
- Resultados booleanos.
- Volúmenes.
- Áreas.
- Cajas envolventes.
- Topología.
- Referencias persistentes.

Crear pruebas numéricas para las operaciones.

No considerar correcto un resultado únicamente porque OpenCascade devuelva una forma sin lanzar una excepción.

### REGLA OBLIGATORIA

La geometría generada debe superar verificaciones objetivas.

Cuando una operación no pueda producir un resultado válido, debe informar el problema en lugar de entregar silenciosamente un sólido incorrecto.

---

# PARTE VIII — PRUEBAS CRUZADAS ENTRE ESPACIOS

## 26. PRUEBAS DE INTEGRACIÓN

Crear escenarios reales que combinen operaciones.

Ejemplos obligatorios:

1. Prisma rectangular → Agujero → Rosca.
2. Cilindro → Agujero concéntrico → Rosca interna.
3. Esfera → Intersección → Simetría.
4. Toroide → Corte → Patrón circular.
5. Bobina → Modificación de parámetros → Recálculo.
6. Tubería curva → Engrosar → Operaciones booleanas compatibles.
7. Engranaje → Eje → Ensamblaje.
8. Cuerpo → Patrón rectangular → Editar patrón.
9. Superficie → Engrosar → Cuerpo sólido.
10. Superficies intersectadas → Llenado de contorno.
11. Ensamblaje cerrado → Volumen de fluido.
12. Geometría de plástico → Patrón → Modificación de espesores.
13. Geometría de chapa → Operaciones compatibles → Desarrollo plano.
14. Operaciones sobre cuerpos de varios componentes.
15. Operaciones sobre geometría importada desde STEP.
16. Edición de boceto original seguida del recálculo de todas las operaciones dependientes.

Para las combinaciones incompatibles con el flujo de Fusion 360, verificar el rechazo correcto en lugar de forzar un resultado.

Cada escenario debe incluir validación numérica y, cuando sea posible, inspección visual.

---

# PARTE IX — AUDITORÍA FUNCIONAL DE INTERFAZ

## 27. COMPROBACIÓN COMO USUARIO REAL

Utilizar `omnicad-test` y las herramientas de prueba de ventana disponibles.

No sustituir estas pruebas por llamadas directas a funciones Python.

Para cada comando:

1. Abrir el espacio de trabajo.
2. Buscar la herramienta.
3. Abrir su menú.
4. Seleccionarla.
5. Elegir geometría mediante el visor.
6. Introducir parámetros.
7. Verificar la vista previa.
8. Manipular las asas.
9. Cambiar opciones.
10. Confirmar.
11. Comprobar el resultado.
12. Reabrir el comando.
13. Editarlo.
14. Deshacer y rehacer.
15. Guardar y recuperar.

### Detectar y reparar

- Botones que no funcionan.
- Submenús incompletos.
- Opciones deshabilitadas injustificadamente.
- Parámetros que no producen cambios.
- Valores predeterminados incorrectos.
- Asas mal orientadas.
- Selecciones ambiguas.
- Cambios inesperados de dirección.
- Resultados distintos de la vista previa.
- Errores silenciosos.
- Bloqueos de interfaz.
- Problemas de foco.
- Diálogos que no caben en ventanas pequeñas.
- Comandos que siguen activos después de cancelar.

Respetar la política de pruebas que no interfiere con el mouse ni teclado físicos del usuario.

---

# PARTE X — DETECCIÓN Y REPARACIÓN DE BUGS

## 28. REPARACIÓN OBLIGATORIA

**Esta auditoría tiene autorización para corregir el código afectado dentro del alcance establecido.**

El trabajo no termina al encontrar defectos.

Para cada bug confirmado:

1. Reproducir el problema.
2. Registrar evidencia.
3. Localizar la causa raíz.
4. Crear un test que falle antes de la corrección.
5. Reparar la implementación.
6. Verificar el resultado.
7. Ejecutar pruebas de regresión.
8. Probar la herramienta desde la interfaz.
9. Revisar los efectos sobre otros espacios.
10. Ejecutar `ponytail-review`.
11. Documentar y cerrar la corrección.

### Prohibiciones

- No ocultar errores.
- No ignorar tests fallidos.
- No eliminar tests para obtener una suite verde.
- No cambiar resultados esperados sin justificación geométrica.
- No sustituir funcionalidad real por mensajes que simulen éxito.
- No implementar parches específicos para un único modelo cuando la causa sea general.
- No reescribir módulos completos sin justificarlo.
- No dar por corregido algo que no fue probado.

---

## 29. FUNCIONES FALTANTES Y MEJORAS

Comparar cada herramienta con su referencia de Fusion 360.

Identificar:

- Modos faltantes.
- Parámetros faltantes.
- Opciones ausentes.
- Selecciones no implementadas.
- Manipuladores incompletos.
- Errores de edición.
- Funciones disponibles por API pero ausentes en UI.
- Diferencias entre espacios.
- Limitaciones geométricas innecesarias.

**Implementar las funciones faltantes que pertenezcan al alcance de estas herramientas**, respetando la arquitectura y las reglas del proyecto.

No incorporar indiscriminadamente opciones que pertenecen a otro comando o entorno de Fusion 360.

Si una mejora representa una modificación importante, realizarla de manera incremental, con tests y validación después de cada cambio.

---

# PARTE XI — RENDIMIENTO

## 30. AUDITORÍA DE VELOCIDAD Y MEMORIA

Medir el rendimiento con:

- Piezas simples.
- Piezas complejas.
- Cientos de caras.
- Patrones con muchas instancias.
- Operaciones booleanas múltiples.
- Superficies complejas.
- Engrosados difíciles.
- Roscas modeladas.
- Bobinas con numerosas vueltas.
- Ensamblajes de varios cuerpos.

Investigar:

- Cálculos repetidos.
- Recreación innecesaria de geometría.
- Actualizaciones excesivas del visor.
- Bloqueos de interfaz.
- Pérdidas de memoria.
- Recalculo innecesario del timeline.
- Operaciones geométricas costosas.

Optimizar únicamente después de medir.

Considerar Rust/PyO3 para cuellos de botella demostrables, si es técnicamente adecuado y cumple las reglas de dependencias.

Comparar tiempos antes y después.

---

# PARTE XII — API, MCP Y CLI

## 31. PARIDAD INTERNA DE OMNICAD

Cada herramienta y opción deberá funcionar de forma coherente desde:

- Interfaz gráfica.
- API Python.
- MCP.
- CLI.

Auditar:

- Parámetros.
- Tipos admitidos.
- Validaciones.
- Valores predeterminados.
- Opciones disponibles.
- Resultados geométricos.
- Mensajes de error.
- Persistencia.
- Transacciones.

No permitir que el mismo comando produzca geometrías diferentes dependiendo del mecanismo de ejecución, salvo diferencias documentadas de contexto.

Actualizar las herramientas correspondientes y regenerar su documentación cuando sea necesario.

---

# PARTE XIII — ORGANIZACIÓN DE LA AUDITORÍA

## 32. FASES DE TRABAJO

### FASE 1 — INVENTARIO

Identificar todos los comandos, variantes, opciones, módulos y apariciones en los espacios de trabajo.

### FASE 2 — REFERENCIA FUSION 360

Investigar la documentación oficial y establecer los comportamientos esperados.

### FASE 3 — AUDITORÍA

Ejecutar pruebas y detectar:

- Bugs.
- Faltantes.
- Diferencias funcionales.
- Problemas geométricos.
- Problemas paramétricos.
- Problemas de interfaz.
- Problemas de rendimiento.

### FASE 4 — CORRECCIÓN

Resolver los defectos encontrados, uno por uno, con sus respectivas pruebas.

### FASE 5 — IMPLEMENTACIÓN DE FALTANTES

Completar opciones y funciones necesarias para alcanzar la paridad funcional establecida.

### FASE 6 — INTEGRACIÓN

Comprobar todas las herramientas en los espacios de trabajo afectados.

### FASE 7 — REGRESIÓN

Ejecutar pruebas geométricas, unitarias, funcionales y de interfaz.

### FASE 8 — VALIDACIÓN FINAL

Contrastar los resultados con los comportamientos de Fusion 360 documentados.

No solicitar aprobaciones entre tareas ordinarias. Respetar las reglas existentes de sesiones, permisos y revisión.

Cada corrección debe cerrarse individualmente antes de la siguiente, con su evidencia y verificación correspondiente.

No ejecutar pruebas pesadas simultáneas si exceden la capacidad del equipo.

Respetar la política del proyecto respecto de los cierres completos, commits y pruebas nocturnas.

---

# PARTE XIV — DOCUMENTACIÓN Y SEGUIMIENTO

## 33. REGISTRO DEL TRABAJO

Mantener actualizados:

- `docs/seguimiento/bugs.md`
- `docs/seguimiento/faltantes.md`
- `docs/seguimiento/mejoras.md`
- `PROJECT_LOG.md`
- `PROJECT_CONTEXT.md`
- Documentación técnica afectada.
- Pruebas automatizadas.

Respetar el método de seguimiento del proyecto: los elementos resueltos se retiran de las listas de pendientes y quedan documentados en el historial correspondiente.

No declarar como corregidos los problemas que no hayan superado la validación.

---

# PARTE XV — INFORME FINAL

## 34. MATRIZ COMPLETA DE RESULTADOS

Elaborar una matriz por herramienta y espacio de trabajo.

| Herramienta | Espacio | Opciones auditadas | Bugs detectados | Bugs corregidos | Faltantes resueltos | Estado |
|---|---|---|---|---|---|---|
| Agujero | SÓLIDO | Resultado real | Cantidad | Cantidad | Cantidad | Estado |
| Rosca | SÓLIDO | Resultado real | Cantidad | Cantidad | Cantidad | Estado |
| Patrón | SÓLIDO | Resultado real | Cantidad | Cantidad | Cantidad | Estado |
| Patrón | SUPERFICIE | Resultado real | Cantidad | Cantidad | Cantidad | Estado |
| Simetría | CHAPA | Resultado real | Cantidad | Cantidad | Cantidad | Estado |

La tabla debe completarse con el inventario real, incluyendo todas las herramientas, variantes y espacios aplicables.

Clasificar cada caso:

- **VERIFICADO:** funcionamiento correcto y pruebas satisfactorias.
- **CORREGIDO:** defecto solucionado y validado.
- **MEJORADO:** funcionalidad ampliada o comportamiento optimizado.
- **PARCIAL:** funcionamiento incompleto comprobado.
- **PENDIENTE:** problema sin resolver.
- **NO VERIFICADO:** sin evidencia suficiente.
- **NO APLICA:** herramienta no disponible o incompatible según la referencia documentada.

## 35. ENTREGABLES

Producir:

1. Inventario de herramientas.
2. Inventario de variantes y opciones.
3. Comparación con Fusion 360.
4. Bugs identificados.
5. Bugs corregidos.
6. Funciones faltantes.
7. Funciones incorporadas.
8. Mejoras geométricas.
9. Mejoras paramétricas.
10. Mejoras de interfaz.
11. Pruebas ejecutadas y salidas reales.
12. Resultados de pruebas de interfaz.
13. Pruebas cruzadas entre espacios.
14. Mediciones de rendimiento.
15. Limitaciones pendientes.
16. Estado final de cada comando.

No inventar resultados ni presentar pruebas no ejecutadas como exitosas.

---

# PARTE XVI — CRITERIOS DE ACEPTACIÓN

## 36. CONDICIONES OBLIGATORIAS

La auditoría y reparación solamente podrán considerarse completas si:

- Se investigaron todas las herramientas del alcance.
- Se identificaron sus apariciones en todos los espacios aplicables.
- Se auditó cada variante.
- Se compararon sus opciones con Fusion 360.
- Los errores detectados se corrigieron o quedaron expresamente documentados como pendientes.
- Las funciones faltantes del alcance se implementaron o quedaron identificadas con sus motivos.
- La geometría resultante es matemáticamente válida.
- Las operaciones booleanas producen resultados correctos.
- Los parámetros son editables.
- El timeline recalcula adecuadamente.
- Los archivos guardados conservan la geometría y las referencias.
- Las vistas previas coinciden con las operaciones finales.
- Los manipuladores funcionan correctamente.
- Las herramientas se probaron como usuario real.
- API, MCP y CLI son consistentes.
- No existen regresiones nuevas sin registrar.
- El código fue revisado con `ponytail-review`.
- La documentación refleja el estado real.

La paridad completa con Fusion 360 solo podrá declararse si se demuestra con cobertura funcional y evidencia suficiente.

---

# ORDEN FINAL DE EJECUCIÓN

**Realizá una auditoría técnica y funcional exhaustiva de todas las herramientas indicadas en esta solicitud, incluyendo cada uno de los espacios de trabajo donde estén disponibles.**

Tomá la documentación oficial de Autodesk Fusion 360 como fuente principal de comportamiento y capacidades.

No te limites a identificar diferencias.

**INVESTIGÁ → AUDITÁ → REPRODUCÍ → DIAGNOSTICÁ → REPARÁ → COMPLETÁ → OPTIMIZÁ → PROBÁ → VERIFICÁ.**

Corregí los bugs encontrados, implementá las opciones faltantes y mejorá las herramientas existentes.

La prioridad es que OmniCAD ofrezca herramientas 3D profesionales, precisas, estables, intuitivas y paramétricas, con el comportamiento de referencia de Fusion 360.

No marques una función como terminada hasta demostrar que funciona correctamente.

**El resultado esperado no es una lista de recomendaciones: es código corregido, funciones completadas, pruebas reales y una auditoría verificable de extremo a extremo.**

======================================================================
ANEXO — ROSCAS (pedido de Gerardo del 2026-11-08; se hace PRIMERO dentro de esta auditoría)
Videos reales: C:/Users/mosos/Videos/2026-11-07 21-43-39.mp4 (OmniCAD) y C:/Users/mosos/Videos/2026-11-07 21-47-34.mp4 (Fusion 360).
======================================================================

# OMNICAD — AUDITORÍA PROFUNDA, CORRECCIÓN Y OPTIMIZACIÓN DEL SISTEMA DE ROSCAS

## 1. ROL Y OBJETIVO

Actuá como ingeniero senior especializado en:

- Sistemas CAD paramétricos.
- OpenCascade (OCP), geometría B-Rep y operaciones booleanas.
- Algoritmos de generación de roscas helicoidales.
- Python, PySide6, OpenGL y Rust/PyO3.
- Profiling, optimización y concurrencia.
- Normas de roscas ISO, ANSI, UNC, UNF y otras familias compatibles.
- Pruebas automatizadas, precisión geométrica y calidad del software.

**MISIÓN PRINCIPAL:**

Auditar exhaustivamente la sección ROSCAS de OmniCAD, identificar y corregir sus problemas funcionales, geométricos y de rendimiento.

La referencia de comportamiento es Autodesk Fusion 360.

**Objetivo obligatorio: que OmniCAD ofrezca la misma funcionalidad, precisión, facilidad de uso y velocidad de respuesta que Fusion 360, o que lo supere cuando sea técnicamente posible.**

No alcanza con mejorar superficialmente el diálogo. Debés revisar y optimizar todo el sistema, desde las tablas de roscas hasta la geometría final.

## 2. INSTRUCCIONES DEL PROYECTO

Antes de tocar código:

1. Leer `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` y `PROJECT_CONTEXT.md`.
2. Invocar mediante la herramienta Skill `fable-method` y `ponytail`, junto con `plan-then-do`, `tool-calling-guard` y `verify-before-commit`.
3. Usar `omnicad-test` para las pruebas de interfaz.
4. Invocar `ponytail-review` antes del cierre, incluyendo su resultado real.
5. Consultar la documentación oficial descargada de Fusion en `docs/fusion_docs/`, utilizando `scripts/fusion_docs.py buscar` y `ver`.
6. Respetar la arquitectura, el seguimiento, las pruebas y las restricciones de permisos del proyecto.

No copiar código propietario de Autodesk.

## 3. ANÁLISIS DE LOS VIDEOS

El usuario proporcionó dos grabaciones:

- `2026-11-07 21-43-39(1).mp4`: OmniCAD.
- `2026-11-07 21-47-34(1).mp4`: Fusion 360.

Si las grabaciones están disponibles, analizarlas detalladamente.

### Observaciones que deben investigarse

**A. Rendimiento y previsualización**

OmniCAD muestra períodos de cálculo al modificar parámetros, durante los cuales el cilindro puede aparecer sin rosca. Fusion presenta una interacción visual más fluida al recorrer diferentes configuraciones.

Investigar qué provoca las esperas, si los cálculos son redundantes y cómo evitar interrupciones innecesarias de la previsualización.

**B. Selección automática de parámetros**

Investigar cómo OmniCAD determina:

- Tipo de rosca.
- Tamaño.
- Designación.
- Paso.
- Clase.
- Compatibilidad con el diámetro seleccionado.

En la grabación aparecen selecciones automáticas como M2.6 y advertencias de incompatibilidad con el cilindro.

Determinar si corresponden a fallos de selección, tablas incompletas, problemas de validación o configuraciones deliberadamente incompatibles. No asumir una causa sin reproducirla.

**C. Geometría**

Comprobar que las formas de rosca generadas respetan el estándar seleccionado y que las diferencias visuales frente a Fusion responden a perfiles geométricos correctos.

**D. Funcionamiento del diálogo**

Verificar que todos los cambios de familia, tamaño, clase, sentido y opciones adicionales actualicen correctamente la vista previa sin bloquear la aplicación.

**IMPORTANTE:** Las grabaciones son evidencia visual, no benchmarks científicos. No inventar tiempos ni diagnosticar errores exclusivamente por su apariencia.

## 4. AUDITORÍA DEL CÓDIGO

Localizar y analizar todos los módulos involucrados en:

- Comando Rosca.
- Agujero roscado.
- Bibliotecas y tablas de roscas.
- Generación de hélices.
- Perfiles de rosca.
- Barridos y operaciones booleanas.
- Selección de caras cilíndricas.
- Vista previa.
- Timeline y reconstrucción paramétrica.
- API, MCP y CLI.
- Renderizado, teselado y exportación.

Revisar especialmente las implementaciones existentes en `nucleo/`, `timeline/`, `ui/comandos/`, `api/`, `ui/visor3d.py`, `nucleo/tablas_rosca.py` y `scripts/generar_tablas_rosca.py`, verificando primero sus nombres y rutas reales.

Detectar:

1. Cálculos repetidos.
2. Generación innecesaria de geometría.
3. Booleanas demasiado costosas.
4. Reconstrucciones completas del documento cuando solo cambia una rosca.
5. Repetición innecesaria de operaciones OpenCascade.
6. Conversiones y copias evitables de geometría.
7. Teselado excesivo.
8. Actualizaciones redundantes del visor.
9. Bloqueos del hilo principal.
10. Cachés inexistentes, incorrectas o mal invalidadas.
11. Trabajadores que calculan resultados obsoletos.
12. Pérdidas de precisión o geometrías inválidas.

Identificar los cuellos de botella reales utilizando profiling, no suposiciones.

## 5. COMPARACIÓN FUNCIONAL CON FUSION 360

Auditar y corregir:

### Selección y configuración

- Selección automática de caras cilíndricas exteriores e interiores.
- Identificación correcta de diámetros y orientación del eje.
- Familia de rosca.
- Tamaños compatibles.
- Designación y paso.
- Clases y tolerancias compatibles con interior/exterior.
- Roscas derechas e izquierdas.
- Longitud completa.
- Longitud parcial.
- Desfase inicial.
- Opciones para recordar tamaño.
- Rosca modelada y cosmética.
- Edición posterior de parámetros.

Las listas de tamaños, designaciones y clases deben actualizarse coherentemente al cambiar de familia.

No ofrecer combinaciones inválidas como si fueran válidas, pero tampoco ocultar estándares compatibles.

Comparar cada opción contra la documentación y el comportamiento verificable de Fusion.

### Geometría

Verificar:

- Diámetros mayor, menor y de paso.
- Ángulo y forma del perfil.
- Altura y profundidad del filete.
- Paso constante y orientación helicoidal.
- Número de vueltas.
- Inicio y final de rosca.
- Truncamientos y transiciones.
- Dirección izquierda/derecha.
- Roscas interiores y exteriores.
- Coaxialidad de tornillo y tuerca.
- Tolerancias y holguras de impresión 3D.
- Intersecciones, autointersecciones y caras degeneradas.
- Estanqueidad y validez del sólido B-Rep.

Usar verificaciones numéricas de diámetros, volumen, área, caja envolvente y validez topológica.

Una rosca visualmente correcta pero geométricamente inválida se considera un fallo.

## 6. OPTIMIZACIÓN DE VELOCIDAD — PRIORIDAD MÁXIMA

**Meta medible: OmniCAD debe igualar o superar los tiempos de Fusion 360 en operaciones equivalentes, bajo condiciones comparables.**

### Fase A — Benchmark inicial

Construir un benchmark reproducible que mida:

| Operación | Métrica |
|---|---|
| Seleccionar cilindro | Latencia de respuesta |
| Abrir Rosca | Tiempo hasta diálogo utilizable |
| Cambiar tipo de rosca | Tiempo de actualización |
| Cambiar tamaño o designación | Tiempo de actualización |
| Cambiar clase o sentido | Tiempo de actualización |
| Activar Modelado | Tiempo hasta vista previa |
| Modificar longitud/desfase | Tiempo hasta vista previa |
| Aceptar operación | Tiempo de geometría definitiva |
| Editar Rosca | Tiempo de recálculo |
| Deshacer/rehacer | Tiempo de recuperación |

Medir también memoria máxima, uso de CPU, bloqueos de UI y tiempo de teselado/render.

Realizar pruebas en frío y en caliente, con repeticiones suficientes para informar mediana, P95 y variabilidad.

### Fase B — Comparación directa

Ejecutar escenarios equivalentes en OmniCAD y Fusion 360:

- M6 × 1.
- M10 × 1.5.
- M20 × 2.5.
- Rosca fina.
- Rosca interior.
- Rosca exterior.
- Rosca corta y larga.
- Rosca derecha e izquierda.
- Varias roscas dentro de un documento complejo.

Utilizar las mismas dimensiones, calidad de visualización, condiciones de hardware y modalidad geométrica.

Registrar el tiempo de Fusion y OmniCAD en cada escenario.

**Criterio objetivo:** tiempo mediano y P95 de OmniCAD igual o inferior al de Fusion para cada escenario comparable.

Si un escenario todavía no alcanza la meta, continuar buscando mejoras justificadas y documentar la diferencia restante con evidencia.

### Fase C — Optimización

Evaluar e implementar las mejoras que correspondan según el profiling:

**1. Previsualización progresiva**

Separar claramente:

- Respuesta inmediata del diálogo.
- Previsualización visual ligera.
- Generación geométrica exacta.
- Confirmación final de la operación.

La previsualización rápida puede usar una representación simplificada temporal, pero la geometría definitiva debe ser exacta.

Nunca guardar una aproximación gráfica como si fuera una rosca física válida.

**2. Cachés inteligentes**

Reutilizar datos cuando no cambiaron:

- Perfil.
- Familia.
- Tamaño.
- Paso.
- Clase.
- Diámetro.
- Geometría cilíndrica de base.
- Segmentos de hélice.
- Mallas de visualización, cuando corresponda.

Invalidar exclusivamente los elementos afectados por cada modificación.

**3. Optimización geométrica**

Investigar alternativas más eficientes para construir la rosca:

- Generación precisa de perfiles.
- Construcción helicoidal eficiente.
- Reducción de barridos redundantes.
- Operaciones booleanas locales y optimizadas.
- Reducción de reconstrucciones B-Rep.
- Ajuste correcto de tolerancias numéricas.
- Tratamiento adecuado de roscas largas.
- Minimización de caras y aristas innecesarias.

No sacrificar dimensiones, topología ni conformidad con el estándar para ganar velocidad.

**4. Uso de Rust y código nativo**

Perfilar las operaciones Python que consumen tiempo.

Si existen cuellos de botella numéricos, transferir únicamente los componentes adecuados a Rust/PyO3, respetando la arquitectura existente.

No reescribir OpenCascade en Rust ni duplicar funciones nativas que ya son eficientes.

**5. UI asíncrona**

Evaluar el trabajador persistente existente.

Evitar que el cálculo pesado bloquee el hilo de PySide6.

Una modificación de parámetros debe invalidar los resultados anteriores. Un resultado viejo nunca puede sobrescribir una selección más reciente.

Las operaciones deben ser cancelables o descartables con seguridad, sin romper la coherencia del documento ni el estado del kernel.

**Resultado esperado: interacción fluida, sin congelamientos y sin cálculos inútiles.**

## 7. CORRECCIÓN DE BUGS Y PRUEBAS DE ESTRÉS

Crear pruebas que cubran:

- Cambiar repetidamente entre familias.
- Seleccionar tamaños incompatibles.
- Cambiar parámetros muy rápidamente.
- Activar/desactivar Modelado.
- Longitud y desfase en valores límite.
- Roscas internas/externas con caras invertidas.
- Diámetros muy pequeños y muy grandes.
- Pasos finos y gruesos.
- Roscas largas con muchas vueltas.
- Cambios en el diámetro original del cilindro.
- Roscas en caras de cuerpos transformados.
- Edición de una rosca existente.
- Operaciones posteriores sobre sólidos roscados.
- Guardar, cerrar, abrir y recalcular.
- Deshacer, rehacer y modificar el timeline.
- Exportación STL, STEP, 3MF y BREP.
- Roscas complementarias para piezas imprimibles.
- Valores inválidos, NaN, infinitos y expresiones.
- Múltiples roscas en documentos complejos.

Agregar pruebas de regresión para cada problema confirmado.

Revisar los bugs históricos relacionados con roscas, incluidos B-44, B-59, B-122 y el caso de tiempo B-222. No considerar resuelto un problema histórico únicamente porque figure así en la bitácora: comprobar el código y las pruebas actuales.

## 8. AUDITORÍA DE LA INTERFAZ

Probar Rosca como lo haría un usuario real:

- Elegir una cara con el mouse.
- Abrir y cerrar desplegables.
- Cambiar todos los valores disponibles.
- Usar teclas Tab, Enter y Esc.
- Activar/desactivar casillas.
- Arrastrar manipuladores de longitud/desfase.
- Observar la actualización en el visor.
- Editar la operación desde el timeline.
- Cancelar sin modificar el documento.
- Aceptar y comprobar el resultado definitivo.

Verificar además:

- Paneles pequeños de 1024 × 640 y 800 × 520.
- Mensajes de error útiles.
- Ausencia de selecciones obsoletas.
- Estados de carga claros.
- Interfaz siempre responsiva.

La experiencia debe ser comparable con la de Fusion 360, sin copiar sus recursos propietarios.

## 9. METODOLOGÍA DE EJECUCIÓN

Trabajar en este orden:

1. Auditar código y comportamiento.
2. Reproducir los problemas detectados.
3. Medir rendimiento inicial.
4. Identificar causas raíz.
5. Priorizar fallos de corrección y cuellos de botella.
6. Implementar las correcciones necesarias.
7. Optimizar los algoritmos.
8. Comparar nuevamente con Fusion.
9. Ejecutar regresiones y pruebas de usuario.
10. Documentar resultados.

Corregir y verificar un problema por vez, evitando introducir múltiples modificaciones sin pruebas intermedias.

Respetar las reglas del proyecto sobre sesiones, commits del coordinador y recursos compartidos.

No instalar dependencias nuevas sin autorización. No hacer `push`.

No utilizar esperas artificiales para ocultar congelamientos ni modificar los benchmarks para obtener mejores resultados.

## 10. CRITERIOS DE ACEPTACIÓN

La tarea se considera terminada únicamente cuando:

- Las operaciones de rosca de los escenarios de prueba producen geometría válida.
- Las selecciones automáticas y las tablas funcionan correctamente.
- Las roscas modeladas son físicamente correctas.
- Las roscas cosméticas no generan geometría pesada innecesariamente.
- El diálogo responde fluidamente durante la edición.
- No aparecen resultados obsoletos al cambiar parámetros.
- El timeline y los archivos conservan sus operaciones.
- API, MCP, CLI e interfaz ofrecen las funciones correspondientes.
- Los tests afectados, Ruff y las verificaciones de UI pasan.
- La suite completa y el humo se ejecutan cuando lo indique el proceso de cierre del proyecto.
- Existe una comparación cuantitativa antes/después y frente a Fusion.

**No declarar que OmniCAD es más rápido que Fusion sin mediciones reproducibles que lo demuestren.**

## 11. DOCUMENTACIÓN Y ENTREGA

Actualizar:

- `docs/seguimiento/bugs.md`
- `docs/seguimiento/mejoras.md`
- `docs/seguimiento/faltantes.md`, si corresponde.
- `PROJECT_LOG.md`
- `PROJECT_CONTEXT.md`
- Documentación de herramientas MCP/CLI, si hubo cambios.
- Lista de pruebas pendientes según las reglas existentes.

Entregar un informe final que incluya:

1. Problemas encontrados, con causa y evidencia.
2. Correcciones realizadas.
3. Algoritmos optimizados.
4. Archivos y funciones modificados.
5. Validaciones geométricas y resultados.
6. Pruebas ejecutadas con su salida real.
7. Benchmarks anteriores y posteriores.
8. Comparación contra Fusion 360.
9. Limitaciones y problemas que todavía persistan.

Incluir obligatoriamente esta tabla:

| Operación | Fusion 360 | OmniCAD antes | OmniCAD después | Mejora |
|---|---|---|---|---|
| Vista previa modelada | Medido | Medido | Medido | Calculada |
| Cambio de tipo | Medido | Medido | Medido | Calculada |
| Cambio de tamaño | Medido | Medido | Medido | Calculada |
| Cambio de longitud | Medido | Medido | Medido | Calculada |
| Generación definitiva | Medido | Medido | Medido | Calculada |
| Edición paramétrica | Medido | Medido | Medido | Calculada |

No inventar valores si alguna medición no puede realizarse.

## INSTRUCCIÓN FINAL

**No quiero solamente una auditoría ni una lista de recomendaciones. Quiero que investigues, reproduzcas, corrijas, optimices y verifiques los problemas que encuentres.**

Priorizá tres resultados:

1. **Precisión:** roscas físicamente correctas y compatibles con sus normas.
2. **Funcionamiento:** experiencia equivalente a Fusion 360, sin errores ni limitaciones injustificadas.
3. **Velocidad:** generación, edición y previsualización tan rápidas como Fusion 360 o superiores, demostradas con benchmarks.

Trabajá sobre la implementación real de OmniCAD, respetá su arquitectura y entregá únicamente resultados comprobables.
```
