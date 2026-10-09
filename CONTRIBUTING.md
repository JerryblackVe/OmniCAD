# Cómo contribuir a OmniCAD

Gracias por sumarte. OmniCAD crece de forma colaborativa: cualquier mejora sirve, desde un error de tipeo hasta una
operación nueva. *English speakers: contributions in English are welcome too; the codebase is in Spanish for now.*

## Antes de empezar

- Leé [AGENTS.md](AGENTS.md): es el manual del proyecto (vale igual para personas y para agentes de IA). Tiene el mapa de
  carpetas, las reglas y las recetas para agregar una operación (A), un comando de la interfaz (B) o una herramienta
  para agentes (C).
- Para algo grande, abrí primero un [issue](https://github.com/JerryblackVe/OmniCAD/issues) y contá la idea: así no se
  pisa con el trabajo de otro.

## Preparar el entorno

```
git clone https://github.com/<tu-usuario>/OmniCAD.git
cd OmniCAD/clon
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .
```

En Linux: `python3 -m venv .venv` y `.venv/bin/python` en lugar de `.venv\Scripts\python.exe` (las librerías del
sistema que pide Qt están en el [README](README.md#instalación-linux)). Lo mismo en los comandos de abajo.

## Verificar antes de mandar un cambio

Desde `clon/`:

```
.venv/Scripts/python.exe -m ruff check --select F,B023,B905 .
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe OmniCAD.py --prueba-humo
```

O todo junto: `omnicad dev check`. Si tocaste la interfaz, la prueba de humo es obligatoria. La suite completa tarda
un par de minutos y usa bastante memoria: no corras dos a la vez.

## Reglas

- **No se copia código, textos ni recursos de programas propietarios** (Fusion 360, Rhino, Grasshopper, etc.). Sí se
  pueden replicar sus *funciones*: qué opciones tiene un comando y qué resultado da, escrito desde cero.
- **Código GPL de otros proyectos** (por ejemplo Blender, que es GPL-2.0 o posterior) se puede incorporar porque
  OmniCAD es GPL-3.0 o posterior, siempre citando el origen y respetando su aviso de copyright.
- **Idioma:** el código, los comentarios y los mensajes van en español. El soporte en inglés está en la hoja de ruta.
- `nucleo/`, `timeline/`, `restricciones/` e `io_archivos/` **no importan Qt**: solo `ui/` conoce la interfaz.
- Cada función nueva del núcleo lleva al menos un test con un resultado numérico (volumen, área, caja envolvente).
- Unidades internas: milímetros y grados.

## Mandar el cambio

1. Hacé un fork y una rama con un nombre claro (`agregar-rosca-trapezoidal`, `arreglar-empalme-L`).
2. Commits chicos, con un mensaje en español que diga qué cambia y por qué.
3. Abrí el pull request completando la plantilla: qué hace, cómo lo probaste y la salida de la verificación.
4. Si cambiaste herramientas para agentes, regenerá `docs/agentes/herramientas.md` con
   `omnicad tools --markdown --output ../docs/agentes/herramientas.md` (un test avisa si te olvidás).

## Convivencia

Ver [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Para reportar una falla de seguridad, ver [SECURITY.md](SECURITY.md).
