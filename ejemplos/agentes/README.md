# Ejemplos para agentes

Tres formas de armar la MISMA pieza: un soporte en L (mm).

- Base de 80 x 40 x 8 y pared de 80 x 8 x 40.
- Dos agujeros pasantes de diámetro 8 en la base.
- Empalme de radio 6 en el rincón interior y de radio 5 en las dos esquinas del frente.
- Parámetros: `espesor` (8 mm) y `diametro` (8 mm).
- Resultado: 1 cuerpo, volumen 45807,965 mm³, caja 80 x 40 x 40 mm.

| Archivo | Para usar con | Qué muestra |
|---|---|---|
| `soporte_l.jsonl` | `omnicad batch` | los 10 pasos, uno por línea, en un solo proceso |
| `soporte_l.py` | Python (`from omnicad import api`) | la misma pieza con `api.llamar`; guarda `.omnicad`, `.stl` y `.png` |
| `soporte_l.receta.json` | `omnicad call apply_recipe` | la receta ya hecha (lo que devuelve `get_recipe`) |

Todos los comandos se corren desde la raíz del repo. `omnicad` es `clon/.venv/Scripts/omnicad.exe`
(o `clon/.venv/Scripts/python.exe -m omnicad.cli`). En Linux y macOS: `clon/.venv/bin/omnicad` y `clon/.venv/bin/python`.

## 1. Batch

```
omnicad new salida/pieza.omnicad
omnicad batch ejemplos/agentes/soporte_l.jsonl --doc salida/pieza.omnicad
omnicad info salida/pieza.omnicad
omnicad render salida/pieza.omnicad salida/vista.png --size 800x600
omnicad export salida/pieza.omnicad salida/pieza.stl
```

El batch guarda el archivo UNA vez al final. Si un paso falla, se detiene y no guarda nada.

## 2. Script de Python

```
clon/.venv/Scripts/python.exe ejemplos/agentes/soporte_l.py salida
```

Imprime un JSON con el volumen y la caja, y deja `soporte_l.omnicad`, `soporte_l.stl` y `soporte_l.png` en `salida/`.
Sale con 0 si anduvo, 1 si una herramienta falló y 2 si faltó la carpeta.

## 3. Receta

```
omnicad new salida/pieza.omnicad
omnicad call apply_recipe --doc salida/pieza.omnicad --args-file ejemplos/agentes/soporte_l.receta.json
```

`apply_recipe` con `mode` por defecto (`replace`) reemplaza el contenido del documento. El archivo es el argumento
completo de la herramienta: `{"recipe": {...}}`.

## Probar que es paramétrico

```
omnicad call set_parameter --doc salida/pieza.omnicad name=espesor expression="10 mm"
omnicad info salida/pieza.omnicad
```

Con `espesor = 10 mm` el volumen pasa a 55505,443 mm³: los empalmes se recalculan solos.

## Que no se rompan

`clon/tests/test_ejemplos_agentes.py` corre los tres ejemplos y compara el volumen con la fórmula exacta. Si cambia
una herramienta y un ejemplo deja de andar, ese test falla.

Para rehacer la receta después de un cambio en el formato: armar la pieza con el batch, abrirla con `open_document`,
sacar `get_recipe` y guardar `{"recipe": ...}` en `soporte_l.receta.json`.
