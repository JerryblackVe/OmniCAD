# Ultimate Audit Review — OmniCAD

2026-10-14 · ejes corridos: pipeline-review, vibe-coding-audit, ponytail-audit · ejes NO corridos: thermo-nuclear (no hay diff puntual; además solo el usuario puede tipearla), user-web-audit (no se pidió UX y es app de escritorio sin URL), fable-judge (solo aplica en modo blindado)

## Por qué este alcance (routing trace)

Modo **completo, solo audit** (el usuario eligió "todo el proyecto" + "solo auditar"). Orden de ejecución: pipeline-review primero (su MAPA alimentó el contexto), vibe-coding-audit después (3 dominios en subagentes de solo lectura), ponytail-audit al final (repo entero, no `-review` porque no es un diff). Thermo-nuclear no corre: no hay diff puntual en este pedido y está bloqueada a la invocación programática — si la querés sobre el último commit, tipeala vos: `/thermo-nuclear-code-quality-review`. user-web-audit no corre porque nunca se pidió UX ni hay producto vivo con URL.

## En criollo (3-5 líneas)

El programa está sano: **no hay nada crítico** que rompa al usuario hoy ni agujeros de seguridad explotables. El riesgo más grave es de proceso: **la fábrica de instaladores publica versiones nuevas sin correr ni un solo test** — un día un cambio roto se convierte en instalador público. Segundo: el servidor para agentes (modo `--http`) acepta órdenes de cualquier programa de la misma máquina sin pedir clave, incluyendo "ejecutá este código". Tercero: hay **~160 líneas repetidas o muertas** y cinco ítems del plan marcados "sin programar" que ya están hechos — papeles viejos que hacen perder tiempo a quien planifique.

## Semáforo por eje

| Eje | Skill | Veredicto corto | Reporte completo |
|---|---|---|---|
| Seguridad/QA/deps/deploy | vibe-coding-audit | ⚠️ 0 críticos, 3 altos (MCP --http sin token; CI publica sin tests; permisos CI amplios), 9 medios, 7 bajos — veredicto "listo con remediaciones" | `audit-report-2026-10-14.md` |
| Consistencia del pipeline | pipeline-review | 🟡 0 críticos, 3 medios (plan vs realidad: 5 pendientes "sin programar" ya hechos; cifra 85→167 ops; dup NOMBRES), 1 bajo; 0 código muerto real | `pipeline-review-2026-10-14.md` |
| Sobre-ingeniería | ponytail-audit | 🟡 15 hallazgos lean, ~155-165 líneas borrables (2 constantes muertas, 8 duplicaciones verificadas byte a byte, rotación a mano vs scipy, lru_cache manual); 0 shortcuts declarados; 0 código muerto real | (inline, ver abajo) |

### Hallazgos lean de ponytail-audit (resumen)

**delete:** `timeline/entidades.py:30` `NOMBRES_ORIGEN` muerta (~2 lín) · `ui/analisis_vista.py:21` `NOMBRES` muerta (~4 lín).
**reuse:** `nucleo/analisis.py:212` vs `dibujo.py:233` `_aristas_unicas` idéntica · `construccion.py:59` vs `superficies.py:493` `_rotar` idéntica · `_hits/_hits_cuerpos` ×3 idénticas en `ui/comandos/{malla,modificar,crear}.py` · `ui/dibujo.py:529` vs `render.py:1236` `_accion/_grupo` de cinta (~35 lín) · `animacion.py:1297` vs `render.py:1924` `_resaltar` · `cli/cmd_atajos.py:37` vs `cmd_dev.py:12` `_tamano` · tablas de unión EN↔ES invertidas a mano en `herramientas_documento.py:51` vs `herramientas_ensamble.py:44` · `protocolo_puente.py:37` vs `puente_fusion.py:49` triple `carpeta_info/ruta_info/leer_info` (~15 lín) · `superficies.py:627` empalme/chaflan difieren solo en la clase OCC (~11 lín) · `intercambio.py:53` leer_step/leer_iges idénticas (~8 lín).
**stdlib:** `ui/animacion.py:66-149` ~64 lín de rotación/quaternion/slerp a mano que `scipy.spatial.transform` ya cubre (caveat: import perezoso + validar convención de ejes) · `ui/iconos.py:19` memoización manual → `@lru_cache`.
**yagni/env:** `OMNICAD_PUENTE_DIR` + `OMNICAD_PUENTE_FUSION_DIR` redundantes (un solo override en `carpeta_datos()` las reemplaza).
**Sin hallazgos:** 0 funciones muertas reales, 0 parámetros sin usar, 0 ABCs/factories, 0 `shortcut:`/`ponytail:` en el repo.

## Los 5 arreglos que más importan (cruzando todos los ejes)

| # | Arreglo | Eje de origen | Impacto |
|---|---|---|---|
| 1 | Job `test` en CI (pytest + ruff + humo offscreen) y `publicar: needs: [test]` | vibe-coding-audit (ALTO-02) | Única red entre "commit roto" y "instalador público roto" |
| 2 | Token para el MCP `--http` (o desactivar `execute_code` en ese modo) | vibe-coding-audit (ALTO-01) | Cierra ejecución arbitraria de código por procesos locales |
| 3 | Permisos CI (`contents: read` salvo en `publicar`) + `action-gh-release` pineada a SHA | vibe-coding-audit (ALTO-03) | Reduce superficie de supply chain del pipeline |
| 4 | Actualizar plan/brechas: 5 pendientes "sin programar" ya hechos + cifra "85 operaciones" → 167 | pipeline-review (MEDIO) | Baratísimo; evita re-planificar trabajo ya hecho |
| 5 | Borrador lean: NOMBRES duplicado + 2 constantes muertas + 8 duplicaciones (~155-165 lín) | ponytail-audit (MEDIO) | Menos superficie que mantener; hoy coinciden, mañana divergen |

## Cuando se apliquen los arreglos

Si los arreglás por tu cuenta (sin modo blindado), corré `/fable-judge` después para verificar
que los fixes realmente resolvieron lo que este reporte encontró. El modo blindado ya lo hace solo.

## Qué no se corrió

- thermo-nuclear: no hay diff puntual; además es invocación manual del usuario.
- user-web-audit: no se pidió y no hay URL (app de escritorio).
- Cobertura CVE con pip-audit y corrida completa de la suite: declarados como "requiere verificación manual" en `audit-report-2026-10-14.md` §5.
