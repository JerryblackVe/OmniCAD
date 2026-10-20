# OmniCAD

**CAD 3D paramétrico, libre y abierto, hecho en Python.** Diseñás con un historial de pasos (timeline) que se recalcula
solo cuando cambiás una medida, como en los CAD profesionales. Y además lo pueden manejar **agentes de IA** (Claude Code,
OpenCode, Cursor, Codex…) por MCP o por línea de comandos.

<div align="center">

## ☕ Si OmniCAD te sirve, apoyalo

**OmniCAD es libre y gratis.** Lo hace una sola persona, en su tiempo.<br>
Si te ayuda, una donación me ayuda a seguir.

<a href="https://ko-fi.com/jerryblackve"><img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Apoyame en Ko-fi"></a>

</div>

[English version](README.en.md) · Licencia [GPL-3.0](LICENSE) · Estado: **alfa** (probado en Windows y en Ubuntu 24.04 sobre WSL2)

![OmniCAD](docs/img/omnicad.png)

## Qué tiene

- **Diseño paramétrico:** parámetros con unidades y expresiones (`ancho / 2 + 3 mm`), timeline editable, deshacer y rehacer.
- **Bocetos 2D con restricciones:** líneas, arcos, círculos, polígonos, splines, cotas y un solver de restricciones.
- **Texto y vectores:** texto de boceto con todas las fuentes instaladas (TrueType, OpenType, variables), espaciado, interlineado, alineación, caja, parámetros `{ancho}`, **texto sobre una curva** y un panel **Carácter** (kerning, inclinación, escala horizontal y vertical, línea base, mayúsculas / versalitas, subrayado y tachado que forman perfiles); el texto se edita con cursor, selección y portapapeles; insertar SVG por capas y colores, vectorizar una imagen, marco para mover, escalar, girar y espejar, unir / restar / intersecar perfiles, desfase y limpieza de geometría importada.
- **Sólidos:** extrusión, revolución, barrido, solevación, primitivas, empalme, chaflán, vaciado, desmoldeo, agujeros,
  roscas, nervios, patrones, simetría, booleanas, dividir, escalar, mover y más.
- **Superficies, chapa metálica y mallas:** parches, recortar, coser, engrosar; pestañas, pliegues y desplegado;
  reparar, remallar, reducir y suavizar mallas.
- **Ensamblaje básico:** componentes, uniones, grupos rígidos y fijaciones (tornillería).
- **Archivos:** proyecto `.omnicad` abierto (ZIP con receta JSON); exporta STL, OBJ, 3MF, PLY, STEP, IGES y BREP;
  importa STEP; bocetos desde DXF, SVG e imágenes vectorizadas; guarda bocetos como DXF y SVG.
- **Inspección:** volumen, masa, área, caja envolvente, distancias, ángulos e interferencias.
- **Interfaz:** 5 temas (oscuro moderno, claro moderno, azul profesional, minimalista y clásico) y temas propios del
  usuario en un archivo JSON; caja de herramientas con la tecla S (buscar y fijar comandos).
- **Kernel geométrico:** [OpenCascade](https://dev.opencascade.org/) (B-rep), el mismo tipo de núcleo que usan los CAD comerciales.

## Ejemplos de lo que se hizo

Un **motor turbofán a escala 1:1** (3,86 m de largo, Ø1,43 m), diseñado por un agente de IA en la app abierta (modo en vivo)
y renderizado con el lienzo OpenGL de RENDERIZAR: 86 cuerpos y 174 pasos paramétricos. Perfiles girados para la góndola, el
núcleo y la tobera; fan de 22 álabes con torsión (solevación y patrón circular); compresor de 9 etapas y turbina de 5
(cientos de álabes por patrón); metales y pinturas de la biblioteca de aspectos, y una calcomanía de fibra de carbono
sobre la góndola.

![Motor turbofán 1:1, vista de frente](docs/img/motor_reaccion_frente.png)
![Motor turbofán 1:1, vista trasera](docs/img/motor_reaccion_atras.png)

## Para agentes de IA

OmniCAD trae un **servidor MCP** y una **CLI** (`omnicad`) que salen de un único catálogo de herramientas: lo que hace
uno lo hace el otro. Un agente puede crear piezas, medirlas, mirar una imagen del resultado y exportarlas; también puede
trabajar **en vivo** sobre la ventana abierta.

```
omnicad setup --cliente todos            # muestra qué configuraría en Claude Code, OpenCode y Cline CLI
omnicad setup --cliente todos --aplicar  # lo hace (con copia .bak de cada archivo)
```

Todo está en [docs/agentes/](docs/agentes/README.md): cómo conectar cada cliente, la CLI, el modo en vivo y la lista
completa de herramientas.

## Descargar (sin programar)

Bajá el instalador de la [última versión](https://github.com/JerryblackVe/OmniCAD/releases/latest):

| Sistema | Archivo | Cómo |
|---|---|---|
| Windows 10/11 | `OmniCAD-…-windows-instalador.exe` | Abrilo y seguí los pasos. No pide administrador. |
| Linux (Ubuntu 22.04 o más nuevo) | `OmniCAD-…-x86_64.AppImage` | Dale permiso de ejecución (`chmod +x`) y abrilo. |

- Para conectar Claude Code u OpenCode: marcá la opción en el instalador, o corré `omnicad-cli setup --cliente todos --aplicar`.
- ⚠ Windows puede avisar «Windows protegió su PC» porque el instalador no está firmado: «Más información» › «Ejecutar de todas formas».

Las secciones de abajo son para correrlo desde el código (para programar o probar lo último).

## Instalación (Windows)

Necesitás [Python 3.12](https://www.python.org/downloads/) y Git.

```
git clone https://github.com/JerryblackVe/OmniCAD.git
cd OmniCAD/clon
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\python.exe OmniCAD.py --ejemplo
```

- `OmniCAD.py` abre la app vacía; `OmniCAD.py pieza.omnicad` abre un proyecto.
- Después de `pip install -e .` quedan los comandos `omnicad` (CLI) y `omnicad-mcp` (servidor MCP).
## Instalación (Linux)

Probado en Ubuntu 24.04 dentro de Windows con WSL2 (falta una PC con Linux nativo). Además de Python 3.12 y Git, Qt necesita algunas
librerías del sistema:

```
sudo apt install python3-venv libgl1 libegl1 libxkbcommon0 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 \
  libxcb-keysyms1 libxcb-image0 libxcb-render-util0 libxcb-xinerama0 libxcb-shape0 libxcb-randr0 \
  libfontconfig1 libdbus-1-3 libglib2.0-0t64 fonts-dejavu-core
git clone https://github.com/JerryblackVe/OmniCAD.git
cd OmniCAD/clon
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e .
.venv/bin/python OmniCAD.py --ejemplo
```

- En WSL2, para dibujar con la placa de video (y no con el procesador): `export GALLIUM_DRIVER=d3d12` antes de abrir.
- En Linux la app usa X11 (`xcb`; en escritorios Wayland, por XWayland): con Wayland nativo los menús emergentes
  (menú radial) fallan. Para probar Wayland igual: `QT_QPA_PLATFORM=wayland`.
- La app guarda lo suyo (autoguardado, temas) en `~/.local/share/OmniCAD`.

## Contribuir

El proyecto busca crecer de forma colaborativa. Empezá por [CONTRIBUTING.md](CONTRIBUTING.md).

- Para programar (personas o agentes de IA): [AGENTS.md](AGENTS.md) explica la arquitectura, las reglas y las recetas para
  agregar operaciones, comandos y herramientas.
- Arquitectura: [docs/arquitectura.md](docs/arquitectura.md). Bitácora y pendientes: [PROJECT_LOG.md](PROJECT_LOG.md).
- Errores e ideas: [Issues](https://github.com/JerryblackVe/OmniCAD/issues).

## Hoja de ruta

**¿Querés ayudar? Elegí cualquiera de estos pendientes y abrí un [Issue](https://github.com/JerryblackVe/OmniCAD/issues) o un Pull Request.** Antes leé [CONTRIBUTING.md](CONTRIBUTING.md) y [AGENTS.md](AGENTS.md).

- **Más plataformas:** Linux en una PC nativa (hoy probado en WSL2); macOS (hay que adaptar OpenGL 4.1, compilar el módulo Rust para Mac y firmar el instalador); validar el instalador de Windows en una PC limpia.
- **Impresión 3D:** cortar y dividir con conectores, moldes, canales internos, jarrones y macetas paramétricos, articulaciones, booleanas con holgura, corte por contorno, relieve desde imagen, texturas, color y 3MF multicolor, soportes, disposición en cama, vista en realidad aumentada y video de presentación.
- **Base para imprimir:** perfil de impresora y material, orientación recomendada, estimación de filamento y tiempo, cajas con tapa, bolsillos para imanes, insertos y rodamientos, agujeros que imprimen sin soportes y pieza de calibración de holguras.
- **Engranajes de todo tipo:** una galería con imágenes y explicación corta para crear engranajes cilíndricos, cónicos, sin fin, planetarios, especiales, cremalleras y mecanismos (Ginebra, trinquete, reductores), desde la interfaz, la CLI o un agente de IA.
- **Idioma:** español e inglés en todo (interfaz, mensajes, herramientas y documentación); primer arranque guiado.
- **Integración:** Blender en los dos sentidos; conectar más agentes de IA y completar las herramientas MCP/CLI que faltan.
- **Render:** materiales, colores e iluminación; ideas de KeyShot y V-Ray.
- **Vectores y texto:** curvas Bézier con manijas de tangente y simplificar con curvas ajustadas.
- **Ensamblajes:** animación, simulaciones y movimiento de piezas.
- **Funciones nuevas:** estilo Rhino, programación visual estilo Grasshopper, ideas de FreeCAD y Plasticity.
- **Ideas de SolidCraft:** piezas de referencia para verificar el motor, pruebas de robustez automáticas, nombres estables de caras y aristas, bocetos que no saltan, configuraciones, conjuntos de contacto, vistas guardadas y ratón 3D.
- **Ideas de otros CAD libres:** que cada herramienta para agentes diga qué cambió de verdad, cambios de agente que se revisan antes de aplicarse, colores en el boceto para ver qué se puede mover, elegir caras por descripción y tutoriales que se reproducen paso a paso.
- **Espacio FORMA** (superficies de subdivisión T-splines): no existe todavía; es el pendiente más grande.
- **Menús y navegador:** los menús contextuales y varias opciones de la cinta que faltan frente a Fusion 360.
- **Abrir `.f3d`** de Fusion con su historial; recuperación de trabajo como Fusion.
- **Rendimiento:** pasar los cuellos de botella a Rust y C++.
- **Interfaz:** pulido visual y sistema de temas propios que el usuario pueda crear y compartir.
- **Corrección de errores:** la lista de errores abiertos está en el PROJECT_LOG.

Próximas funciones de boceto y modelado (lo que todavía falta frente a Fusion):

- Boceto 3D: mover los puntos del boceto en altura.
- Hélice como curva de boceto (hoy hay solo espiral plana).
- Aspecto completo: pintar caras sueltas, muestras del diseño y editor de color, brillo y rugosidad.
- Grupos en la línea de tiempo.

Detalle en [PROJECT_LOG.md](PROJECT_LOG.md#pendientes).

## Aviso

OmniCAD es un proyecto independiente. Toma como referencia el **flujo de trabajo** de programas como Fusion 360, Blender
y Rhino, pero **no contiene código, textos ni recursos** de ellos. No está afiliado ni respaldado por Autodesk, la Blender
Foundation ni Robert McNeel & Associates. Fusion 360 es marca de Autodesk, Inc.; Rhinoceros y Grasshopper son marcas de
Robert McNeel & Associates.

## Licencia

[GNU GPL v3.0 o posterior](LICENSE). Podés usarlo, estudiarlo, modificarlo y compartirlo; si distribuís una versión
modificada, tiene que seguir siendo libre con la misma licencia.

## Apoyar el proyecto

OmniCAD es libre y gratis, y lo hace una sola persona. Si te sirve, podés apoyarlo con una donación en
[ko-fi.com/jerryblackve](https://ko-fi.com/jerryblackve). ¡Gracias!
