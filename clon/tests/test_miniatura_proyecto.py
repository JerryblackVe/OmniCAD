# -*- coding: utf-8 -*-
"""H-112: todo .omnicad guardado lleva `miniatura.png` (sin comprimir, la lee el lector de miniaturas de Windows) y
`omnicad miniaturas` registra y desregistra ese lector en HKCU."""
import sys
import zipfile

import pytest

from omnicad import api
from omnicad.api.sesion import Sesion
from omnicad.io_archivos import proyecto


def _miembro(ruta):
    with zipfile.ZipFile(ruta) as z:
        return z.getinfo("miniatura.png"), z.read("miniatura.png")


def test_guardar_desde_la_api_escribe_la_miniatura(tmp_path):
    s = Sesion()
    assert api.llamar(s, "create_box", {"length": 40, "width": 30, "height": 10})["ok"]
    r = api.llamar(s, "save_document", {"path": str(tmp_path / "caja.omnicad")})
    assert r["ok"], r
    info, png = _miembro(tmp_path / "caja.omnicad")
    assert info.compress_type == zipfile.ZIP_STORED
    assert png.startswith(b"\x89PNG") and int.from_bytes(png[16:20], "big") == 256   # ancho del IHDR
    assert proyecto.leer_miniatura(tmp_path / "caja.omnicad") == png


def test_documento_vacio_se_guarda_sin_miniatura(tmp_path):
    r = api.llamar(Sesion(), "save_document", {"path": str(tmp_path / "vacio.omnicad")})
    assert r["ok"], r
    assert proyecto.leer_miniatura(tmp_path / "vacio.omnicad") is None


def test_si_la_miniatura_falla_igual_se_guarda(tmp_path, monkeypatch):
    from omnicad.api import herramientas_inspeccion
    s = Sesion()
    api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})
    monkeypatch.setattr(herramientas_inspeccion, "get_viewport_image", lambda *a, **k: 1 / 0)
    assert api.llamar(s, "save_document", {"path": str(tmp_path / "x.omnicad")})["ok"]
    assert proyecto.leer_miniatura(tmp_path / "x.omnicad") is None


def test_autoguardado_en_hilo_lleva_la_miniatura(tmp_path):
    s = Sesion()
    api.llamar(s, "create_box", {"length": 10, "width": 10, "height": 10})
    s.doc.ruta = str(tmp_path / "pieza.omnicad")
    resultado = []
    proyecto.autoguardar_en_hilo(s.doc, lambda destino, error: resultado.append((destino, error)), b"\x89PNG fake").join()
    destino, error = resultado[0]
    assert error is None
    assert proyecto.leer_miniatura(destino) == b"\x89PNG fake"


@pytest.mark.skipif(sys.platform != "win32", reason="registro de Windows")
def test_instalar_y_quitar_el_lector_de_miniaturas(tmp_path):
    import winreg

    from omnicad.cli import cmd_miniaturas as m
    raiz = r"Software\OmniCAD_prueba_H112"
    clases = raiz + r"\Classes"
    origen = tmp_path / "origen.dll"
    origen.write_bytes(b"MZ prueba")
    ajena = rf"{clases}\.fclone\ShellEx\{m.LECTOR_MINIATURAS}"
    try:
        destino = m.instalar(origen, tmp_path / "instalada", clases)
        assert destino.read_bytes() == b"MZ prueba"
        e = m.estado(clases)
        assert e["installed"] and e["dll"] == str(destino) and e["dll_exists"]
        assert m._valor(rf"{clases}\.omnicad\ShellEx\{m.LECTOR_MINIATURAS}") == m.CLSID
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, ajena) as k:   # otra extensión de shell en .fclone: no se toca
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, "{00000000-0000-0000-0000-000000000000}")
        assert m.quitar(tmp_path / "instalada", clases) is None
        assert not m.estado(clases)["installed"] and m.estado(clases)["dll"] is None
        assert not destino.exists()
        assert m._valor(ajena) == "{00000000-0000-0000-0000-000000000000}"
    finally:
        import subprocess
        subprocess.run(["reg", "delete", "HKCU\\" + raiz, "/f"], capture_output=True)
