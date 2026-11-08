# -*- coding: utf-8 -*-
"""`omnicad miniaturas instalar|quitar|estado`: el lector de miniaturas de Windows para los `.omnicad` (H-112), así el
Explorador muestra la vista del modelo como con los `.f3d` de Fusion. La DLL (Rust, `clon/rust/miniatura/`) se copia
a la carpeta de datos (%LOCALAPPDATA%/OmniCAD/miniaturas) y se registra solo para este usuario (HKCU, sin
administrador). Es configuración de Windows, no del documento: por eso no tiene herramienta en el MCP."""
import os
import shutil
import sys
from pathlib import Path

from . import util

CLSID = "{179505fe-a2aa-4964-a34d-f0bd6c7531fb}"          # CLSID_MINIATURA de rust/miniatura/src/lib.rs
LECTOR_MINIATURAS = "{e357fccd-a995-4576-b01f-234630154e96}"  # IID de IThumbnailProvider: la clave que busca el Explorador
CLASES = r"Software\Classes"
DLL = "omnicad_miniatura.dll"


def dll_compilada():
    return Path(__file__).resolve().parents[2] / "rust" / "miniatura" / "target" / "release" / DLL


def carpeta_instalada():
    from .. import carpeta_datos
    return carpeta_datos() / "miniaturas"


def _extensiones():
    from ..io_archivos.proyecto import EXTENSIONES
    return EXTENSIONES


def _avisar_explorador():
    import ctypes
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)   # SHCNE_ASSOCCHANGED, SHCNF_IDLIST


def instalar(origen, carpeta, clases=CLASES):
    """Copia la DLL a `carpeta` y la registra en HKCU\\`clases`. Devuelve la ruta instalada."""
    import winreg
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / DLL
    if not destino.exists() or destino.read_bytes() != origen.read_bytes():
        try:
            shutil.copyfile(origen, destino)
        except PermissionError:
            raise util.UsoError(f"La DLL instalada está en uso por Windows: {destino}",
                                ["Cerrá sesión de Windows (o reiniciá el Explorador) y repetí el comando."]) from None
    hk = winreg.HKEY_CURRENT_USER
    with winreg.CreateKey(hk, rf"{clases}\CLSID\{CLSID}") as k:
        winreg.SetValueEx(k, None, 0, winreg.REG_SZ, "Miniaturas de OmniCAD")
    with winreg.CreateKey(hk, rf"{clases}\CLSID\{CLSID}\InprocServer32") as k:
        winreg.SetValueEx(k, None, 0, winreg.REG_SZ, str(destino))
        winreg.SetValueEx(k, "ThreadingModel", 0, winreg.REG_SZ, "Apartment")
    for ext in _extensiones():
        with winreg.CreateKey(hk, rf"{clases}\{ext}\ShellEx\{LECTOR_MINIATURAS}") as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, CLSID)
    _avisar_explorador()
    return destino


def _valor(ruta):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, ruta) as k:
            return winreg.QueryValueEx(k, None)[0]
    except OSError:
        return None


def _borrar(ruta):
    import winreg
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, ruta)
    except FileNotFoundError:
        pass


def quitar(carpeta, clases=CLASES):
    """Borra el registro (solo las claves que apuntan a esta DLL) y la DLL. Devuelve un aviso o None."""
    for ext in _extensiones():
        ruta = rf"{clases}\{ext}\ShellEx\{LECTOR_MINIATURAS}"
        if _valor(ruta) == CLSID:              # otra extensión de shell registrada ahí no se toca
            _borrar(ruta)
    _borrar(rf"{clases}\CLSID\{CLSID}\InprocServer32")
    _borrar(rf"{clases}\CLSID\{CLSID}")
    _avisar_explorador()
    try:
        (carpeta / DLL).unlink(missing_ok=True)
    except PermissionError:
        return f"La DLL sigue en uso y quedó en {carpeta / DLL}: se puede borrar después de cerrar sesión."
    return None


def estado(clases=CLASES):
    dll = _valor(rf"{clases}\CLSID\{CLSID}\InprocServer32")
    return {"installed": bool(dll) and all(_valor(rf"{clases}\{e}\ShellEx\{LECTOR_MINIATURAS}") == CLSID
                                           for e in _extensiones()),
            "dll": dll, "dll_exists": bool(dll) and os.path.isfile(dll)}


def miniaturas(ns):
    if sys.platform != "win32":
        raise util.UsoError("Las miniaturas del Explorador son solo de Windows.")
    aviso = None
    if ns.accion == "instalar":
        origen = Path(ns.dll) if ns.dll else dll_compilada()
        if not origen.is_file():
            raise util.UsoError(f"No está la DLL compilada: {origen}",
                                ["Compilala con `cargo build --release` en clon/rust/miniatura, o pasá --dll."])
        instalar(origen, carpeta_instalada())
    elif ns.accion == "quitar":
        aviso = quitar(carpeta_instalada())
    r = estado()
    if ns.json:
        print(util.a_json({"ok": True, "result": r, "avisos": [aviso] if aviso else []}))
    else:
        util.decir(("Instalado: " + r["dll"]) if r["installed"] else "No instalado.")
        if aviso:
            util.decir("aviso: " + aviso)
    return 0


def registrar(sub, comun):
    p = sub.add_parser("miniaturas", parents=[comun],
                       help="muestra la vista del modelo en los .omnicad del Explorador de Windows (instalar, quitar, estado)",
                       description="Instala o quita el lector de miniaturas de Windows para los proyectos .omnicad. "
                                   "Se registra solo para este usuario (HKCU), sin administrador.")
    p.add_argument("accion", choices=["instalar", "quitar", "estado"])
    p.add_argument("--dll", metavar="RUTA", help="DLL a instalar (por defecto la de clon/rust/miniatura/target/release)")
    p.set_defaults(func=miniaturas)
