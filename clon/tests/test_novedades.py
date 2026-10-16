# -*- coding: utf-8 -*-
"""`scripts/novedades.py` (pendiente 12): informe mensual de novedades y pendientes automáticos en los
brechas. Se prueba SIN red: el extractor con HTML sintético y la anotación con archivos temporales."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "novedades.py"
spec = importlib.util.spec_from_file_location("novedades", SCRIPT)
nov = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nov)

HTML = """<html><body><nav><a href="/">Home</a><a href="/docs">Documentation</a></nav>
<article><h2>Blender 5.1 trae geometría nodal nueva</h2><p>texto</p>
<h3>Grease pencil en tiempo real</h3>
<a href="/noticia">Mejoras de rendimiento del viewport</a>
<h2>Blender 5.1 trae geometría nodal nueva</h2></article>
<footer><a href="/privacy">Privacy</a></footer></body></html>"""


def test_extrae_titulares_sin_navegacion_ni_repetidos():
    titulares = nov.titulares_de(HTML)
    assert [t for t, _h, _es in titulares] == ["Blender 5.1 trae geometría nodal nueva",
                                              "Grease pencil en tiempo real",
                                              "Mejoras de rendimiento del viewport"]
    assert titulares[2][1] == "/noticia"                      # conserva el enlace
    assert titulares[0][2] and titulares[1][2]                 # encabezados: van a los brechas
    assert not titulares[2][2]                                 # enlace suelto: solo al informe


def test_html_roto_no_tumba_el_extractor():
    assert nov.titulares_de("esto no es html") == []


def test_correr_offline_escribe_el_informe_y_no_toca_brechas(tmp_path):
    ruta, texto = nov.correr(mes="2026-10", carpeta_novedades=tmp_path, carpeta_brechas=tmp_path, offline=True)
    assert ruta == tmp_path / "2026-10.md" and ruta.is_file()
    assert "Novedades del mes — 2026-10" in texto
    for nombre in ("Fusion 360", "Blender", "Rhino"):
        assert nombre in texto
    assert "corrida sin red" in texto
    assert not list(tmp_path.glob("brechas_*.md"))            # sin titulares, no se anota nada


def test_anota_solo_encabezados_nuevos_y_es_idempotente(tmp_path):
    brechas = tmp_path / "brechas_blender.md"
    brechas.write_text("# Brechas frente a Blender\n\n- Grease pencil en tiempo real\n", encoding="utf-8")
    titulares = [("Grease pencil en tiempo real", None, True),          # ya estaba en el archivo
                 ("Nodos de hair nuevos", None, True),                  # nuevo: se anota
                 ("Get Involved", None, False)]                         # menú: NI al informe NI al brechas
    assert nov.anotar_en_brechas(brechas, "blender", titulares, "2026-10") == 1
    texto = brechas.read_text(encoding="utf-8")
    assert "- [AUTO 2026-10] Nodos de hair nuevos" in texto
    assert "Get Involved" not in texto
    assert "## Novedades automáticas (2026-10, sin clasificar)" in texto
    assert nov.anotar_en_brechas(brechas, "blender", titulares, "2026-10") == 0   # idempotente
    assert brechas.read_text(encoding="utf-8") == texto
