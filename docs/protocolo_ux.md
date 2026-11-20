# Protocolo UX/UI de OmniCAD

Dueño: Gerardo. Aplica a TODO trabajo nuevo de UI (cinta, paneles, diálogos, Preferencias, ayuda). Fuente única de los números UX (regla 19): este archivo. Obligatorio desde el 2026-11-20.

**Base:** la regla 14 de CLAUDE.md («App para todos») es el principio; acá van las reglas verificables. Lo que ya vive en otro archivo se enlaza.

### Reglas

**Cara de la app**
- **UX-1 Para todos.** Un chico de 10 años y un profesional usan la misma app. Sin jerga, sin siglas, sin códigos (colores como muestra, fuentes con su letra). Ver regla 14 de [CLAUDE.md](../CLAUDE.md).
- **UX-2 Estilo único.** Esquinas redondeadas, tarjetas con sombra suave, espacios y radios salen de los tokens de `ui/temas.py` (radio chico/mediano/grande, espaciado 4-8-12-16). Prohibido `#rrggbb`, `border-radius` o `setFixedSize` sueltos en `ui/` fuera de `temas.py`.
- **UX-3 Visual primero.** Todo lo que se pueda mostrar se muestra: ícono, muestra de color, miniatura, asa, previa. Un texto ocupa 1 renglón. El detalle va al «?».

**Tarjeta por tarea**
- **UX-4 Una tarjeta por tarea.** Una tarea abre UNA tarjeta. Prohibido abrir otra encima o al lado que repita campos (Texto, Patrón, Simetría incluidos). Lo que ya está en la tarjeta no se repite en una barra flotante.
- **UX-5 Máximo 5 campos visibles.** Lo demás va en «Más opciones» plegado, con su resumen. Una selección que define la operación nunca va plegada.
- **UX-6 Orden fijo.** Tipo/modo, objetos, valor principal, opciones. Aceptar abajo a la derecha, Cancelar a su izquierda, siempre en el mismo lugar y visibles (también con scroll y con letra grande).
- **UX-7 Valores por defecto que sirven.** Abrir un comando y apretar Aceptar sin tocar nada da una pieza válida, o Aceptar queda gris con su motivo.
- **UX-8 Previa en vivo.** Todo comando que cambia geometría muestra la previa antes de aceptar. Si no puede, lo dice con «No disponible» (regla 16 de [CLAUDE.md](../CLAUDE.md)).

**Errores, seguridad, honestidad**
- **UX-9 Errores en el dibujo.** El límite se ve en el asa, el campo o la previa en rojo. El mensaje es 1 renglón con ícono (✖ ⚠), máx. 60 caracteres; lo demás, en el «?». (Test: `tests/test_p158_mensajes_cortos.py`.)
- **UX-10 Todo se deshace.** Cada acción es UN paso de deshacer. Lo que no se puede deshacer (borrar un archivo, vaciar la papelera, sobrescribir, sacar datos de la app) pide confirmación con su consecuencia en 1 renglón y el botón de peligro a la izquierda del seguro.
- **UX-11 Lo roto, en gris.** Regla 16 de [CLAUDE.md](../CLAUDE.md) y `deshabilitado.py`. El motivo es 1 renglón sin jerga.

**Nombres y ayuda**
- **UX-12 Nombre al pasar el mouse.** Todo botón con ícono tiene tooltip con su nombre en español y su tecla. Nada de siglas ni letra suelta como ícono.
- **UX-13 «?» de ayuda.** Cada tarjeta tiene «?» con 1–2 frases y, si existe, un clip de menos de 15 s (`docs/ayuda/<clave>.webp` o `.mp4`, sin sonido, en bucle). Sin clip, solo texto; nunca un clip roto.

**Personalizar y accesibilidad**
- **UX-14 Atajos completos.** Todo comando tiene atajo editable en Preferencias › Atajos, con choque en rojo y «Restaurar». Cambiar el atajo desde el botón de la cinta (⋮) abre la misma pantalla. API: `list_shortcuts`, `set_shortcut`, `reset_shortcuts`.
- **UX-15 Cinta personal.** Todo botón se puede anclar, quitar y reordenar; «Restaurar» vuelve a fábrica. API: `set_ribbon_section`, `reset_ribbon`.
- **UX-16 Modo simple y experto.** Preferencia `interfaz/modo` = `simple` | `experto` (por defecto `simple`). Simple: cinta con las herramientas de uso común y «Más opciones» plegado. Experto: cinta completa y «Más opciones» recordado abierto. La API no cambia.
- **UX-17 Tema y letra.** Todo funciona en claro, oscuro y «del sistema», y con letra al 150 %: nada cortado, nada solapado a 1024×700. Contraste mínimo del tema (`MIN_CONTRASTE`).
- **UX-18 Animaciones cortas.** Toda animación dura menos de 0,2 s, sin bloquear la acción, y se apaga con «Reducir movimiento». Constante única `DURACION_ANIM_MS = 150` en `temas.py`.

**Medir**
- **UX-19 Prueba del novato.** Cada tarjeta nueva o cambiada pasa la «tarea de 1 minuto»: una persona que nunca vio el comando lo completa sin ayuda en menos de 60 s (E11 con Computer Use, o la medición de `registro_uso`). Si no, la tarjeta se rehace.
- **UX-20 Una fuente por regla.** Este archivo es la fuente de los números UX. CLAUDE.md, AGENTS.md y el brief solo lo enlazan. `tests/test_ux_protocolo.py` lee las constantes de un único lugar.
- **UX-21 Íconos grandes, propios y claros (Gerardo, 2026-11-20).** Los íconos de la cinta son grandes como los de Fusion y se entienden sin leer, para un chico de 10 y una persona de 100 (regla 14). Diseño propio y original de OmniCAD, nunca copiado de Fusion: una imagen que muestra qué hace el comando (UX-3), sin letras sueltas ni siglas, con el mismo estilo en toda la cinta y legible en claro y oscuro. Todo ícono nuevo o cambiado lo cumple; el rediseño de los existentes es P-200. Estilos solo desde `ui/temas.py`.
  - **Dirección elegida: «Sistema B» (Gerardo, 2026-11-20; imagen `~/coordinador/reportes/2026-11-20_iconos/sistema_b_gerardo.webp`).** Íconos isométricos con volumen: la pieza en gris y la parte que actúa en color por grupo (verde boceto, azul sólido, naranja modificar, violeta construir, turquesa inspeccionar), legibles a 32 px. Al implementar: SVG vectorial redibujado con 3 tonos planos por cara (no la imagen de IA), probado a 20, 32 y 48 px; los colores de grupo viven en `ui/temas.py`.
- **UX-22 Criterio visual con `impeccable` (Gerardo, 2026-11-20).** La sesión que diseña íconos o pantallas nuevas o cambiadas invoca la skill `impeccable` (herramienta Skill) para el criterio visual: jerarquía, contraste, claridad y consistencia. Su parte de código web (HTML/CSS) no aplica: OmniCAD es Qt y los estilos salen de `ui/temas.py`. Se anota en el informe que se invocó.
- **UX-23 Herramientas de diseño (Gerardo, 2026-11-20).** El rediseño de íconos (P-200) usa primero la skill `icon-system` (fija la especificación: grilla, tamaños, trazo y nombres) y después `icon-set-generator` (dibuja el set con un estilo fijado una vez; solo texto y SVG, sin red ni API) más `impeccable` para el criterio (UX-22). Los textos de la UI (etiquetas, avisos, errores, ayudas) pasan por `design:ux-copy`. Las skills se invocan con la herramienta Skill y el informe lo anota.

### Lista de control (la pasa TODA sesión que toque UI antes de cerrar)

Marcar cada punto con evidencia (captura, test o línea). Un punto sin evidencia = ítem no cerrado.

1. [ ] **1 tarjeta**: la tarea abre una sola tarjeta; no se abre otra encima ni se repite un campo (UX-4).
2. [ ] **≤ 5 campos visibles**; lo demás en «Más opciones» con resumen (UX-5).
3. [ ] **Aceptar abajo a la derecha, Cancelar al lado**, a la vista con scroll y con letra al 150 % (UX-6).
4. [ ] **Aceptar sin tocar nada**: da resultado válido o queda gris con motivo (UX-7).
5. [ ] **Previa en vivo** antes de aceptar, o «No disponible» con motivo (UX-8).
6. [ ] **Error en rojo en el dibujo** y mensaje de 1 renglón con ícono, ≤ 60 caracteres (UX-9).
7. [ ] **Deshacer** de la acción en un paso; lo peligroso pide confirmación (UX-10).
8. [ ] **Tooltip con nombre y tecla** en todo ícono; sin siglas ni letras sueltas (UX-12).
9. [ ] **«?» de ayuda** con 1–2 frases (y clip si existe) (UX-13).
10. [ ] **Atajo y cinta**: el comando aparece en Atajos y se puede anclar en la cinta; herramienta MCP/CLI al día (UX-14, UX-15, regla 10).
11. [ ] **Modo simple y experto**: se ve bien en los dos (UX-16).
12. [ ] **Tema claro, oscuro y letra 150 %**: capturas de los tres con la plataforma Qt por defecto (no `offscreen`); sin `#rrggbb` ni `border-radius` fuera de `temas.py` (UX-2, UX-17).
13. [ ] **Animaciones < 0,2 s**, o ninguna (UX-18).
14. [ ] **Prueba del novato** hecha o pedida a E7/E11 con el tiempo medido (UX-19).
15. [ ] **Sin repetir reglas**: nada de este protocolo copiado en otro archivo; solo enlaces (UX-20).

---
