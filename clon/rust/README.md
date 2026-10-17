# Cálculos nativos del render

Un módulo PyO3 opcional para `get_viewport_image` y el render local. Rasterización, sombras y oclusión
ambiental trabajan con arrays; Python conserva la escena y OpenCascade. Sin módulo compilado se usa numpy.
`OMNICAD_SIN_RUST=1` fuerza la referencia Python para comparar.

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
