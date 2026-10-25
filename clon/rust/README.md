# Cálculos nativos

Un módulo PyO3 opcional (`omnicad._rs`, fuentes en `src/`). Python conserva la escena y OpenCascade; Rust recibe y
devuelve arrays. Sin módulo compilado se usa la referencia Python. `OMNICAD_SIN_RUST=1` la fuerza para comparar.

- **Render** (`src/lib.rs`): rasterización, sombras y oclusión ambiental para `get_viewport_image` y el render local.
- **Perfiles de un boceto** (`src/perfiles.rs`, BOC-28): `arreglo_planar` calcula intersecciones, grafo planar, lazos y
  regiones de las curvas del boceto (líneas, círculos, arcos y B-splines) y devuelve, por perfil, área, centroide, caja,
  firma y los tramos de curva de su borde. Python arma la cara exacta de OpenCascade al pedirla
  (`nucleo/perfiles.py` › `_fabrica_caras`), sin `Splitter`. Si no puede certificar el resultado (cruces tangentes, curvas
  superpuestas, autocruces, elipses, un extremo libre a menos de 1e-4 mm de otra curva) devuelve error y rige el
  `Splitter` de siempre. Equivale al `Splitter` salvo en triples puntos casi concurrentes (< 1e-4 mm), donde éste funde
  con su tolerancia y el arreglo no: `tests/test_boc28_rust.py`. Pruebas de Rust: `cargo test`.

Con Rust y maturin **ya autorizados e instalados**, desde esta carpeta:

```powershell
../.venv/Scripts/python.exe -m maturin develop --release
cargo clippy -- -D warnings
cargo test
```

Paridad: desde `clon/`, `.venv/Scripts/python.exe -m pytest tests/test_render_nativo.py -q`.
Las pruebas nativas se saltean si el módulo no está instalado. PyInstaller descubre `omnicad._rs` como
submódulo del paquete y lleva el `.pyd`: la máquina donde se ejecuta la app no necesita Rust ni maturin.
`Cargo.lock` fija las dependencias de compilación; `target/` y el binario quedan fuera de git.

Base y resultados de T-18: `docs/informe_tortura_2026-10-17.md`.
