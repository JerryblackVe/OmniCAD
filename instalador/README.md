# Instaladores de OmniCAD

Para que cualquiera instale OmniCAD sin terminal ni Python: un instalador `.exe` para Windows y un AppImage para Linux.
Los dos llevan adentro Python, Qt y OpenCascade (unos 600 MB instalado).

| Sistema | Archivo | Qué hace |
|---|---|---|
| Windows 10/11 (64 bits) | `OmniCAD-<versión>-windows-instalador.exe` | Instala para el usuario sin pedir administrador (o para todos), acceso directo en el menú Inicio, abre los `.omnicad` y trae desinstalador. Tarea opcional: conectar los agentes de IA (`omnicad-cli setup`). |
| Linux x86_64 | `OmniCAD-<versión>-x86_64.AppImage` | Un solo archivo: darle permiso de ejecución y abrirlo. Funciona en distribuciones con glibc 2.35 o más nueva (Ubuntu 22.04 en adelante). |

## Lo que trae la app instalada

| Programa | Para qué |
|---|---|
| `OmniCAD` | la aplicación |
| `omnicad-cli` | la CLI (lo mismo que `omnicad` instalado con pip; en Windows no puede llamarse `omnicad` porque pisaría a `OmniCAD.exe`) |
| `omnicad-mcp` | el servidor MCP para agentes de IA |

- Conectar los agentes: `omnicad-cli setup --cliente todos --aplicar` (en el AppImage: `OmniCAD-….AppImage cli setup …`).
  Registra el `omnicad-mcp` instalado (en el AppImage, el propio `.AppImage` con el argumento `mcp`) y copia la skill.
- Las herramientas de desarrollo (`run_checks`, `app_screenshot`, `run_bench`) necesitan el código fuente: en la app
  instalada devuelven el error `DEV_ONLY`.

## Armarlos en una PC

Hacen falta las dependencias del proyecto y PyInstaller (`requisitos.txt`) en el venv:

```
clon/.venv/Scripts/python.exe -m pip install -r instalador/requisitos.txt
clon/.venv/Scripts/python.exe instalador/armar.py
```

- Windows: además, Inno Setup 6 (`winget install JRSoftware.InnoSetup`). Sale `instalador/dist/OmniCAD-<versión>-windows-instalador.exe`.
- Linux: lo mismo con `clon/.venv/bin/python`. `armar_appimage.sh` baja appimagetool la primera vez. Sale `instalador/dist/OmniCAD-<versión>-x86_64.AppImage`.
- `--sin-pyinstaller` reusa la carpeta congelada y solo vuelve a empaquetar.
- `instalador/build/` y `instalador/dist/` no se suben al repo (ocupan ~1,5 GB).

## Archivos

| Archivo | Qué es |
|---|---|
| `armar.py` | arma todo para el sistema donde corre |
| `omnicad.spec` | receta de PyInstaller: los tres programas en una carpeta, con el ícono, los datos del paquete y la skill |
| `lanzadores/` | entradas de `omnicad-cli` y `omnicad-mcp` |
| `windows/omnicad.iss` | instalador de Windows (Inno Setup); las imágenes del asistente salen de la portada y del ícono |
| `linux/` | `armar_appimage.sh`, `AppRun` (abre la app, o `cli`/`mcp`), `omnicad.desktop` y el tipo MIME de los `.omnicad` |
| `../.github/workflows/instaladores.yml` | GitHub Actions: arma los dos con cada etiqueta `v*` y los publica en Releases |

## Publicar una versión

1. Subir el número en `clon/omnicad/__init__.py` (`VERSION`, lo leen la app y los instaladores) y en `clon/pyproject.toml`
   (`tests/test_recursos.py` falla si no coinciden; `pyproject` no puede leerlo de `omnicad` porque en Windows setuptools
   encuentra `OmniCAD.py`).
2. `git tag v<versión>` y `git push origin v<versión>`: GitHub Actions arma los dos instaladores y los sube a la página de Releases.
