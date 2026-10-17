"""Aceleración opcional: el Python de referencia funciona también sin el módulo Rust."""
import os

try:
    from . import _rs
except ImportError:
    _rs = None


def disponible():
    """Módulo cargado, salvo que OMNICAD_SIN_RUST=1 fuerce el motor de referencia."""
    return _rs if os.environ.get("OMNICAD_SIN_RUST") != "1" else None
