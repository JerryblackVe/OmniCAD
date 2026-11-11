"""B-326: si falta Arial se usa su equivalente (Liberation Sans, luego DejaVu Sans); no depende del sistema."""
import pytest

from omnicad.nucleo import fuentes


def _sin(monkeypatch, *faltan):
    """Simula un sistema sin esas familias: buscar_fuente las devuelve como no instaladas."""
    real = fuentes.buscar_fuente
    nombres = {f.casefold() for f in faltan}
    monkeypatch.setattr(fuentes, "buscar_fuente",
                        lambda n, negrita=False, cursiva=False: None if str(n).casefold() in nombres
                        else real(n, negrita, cursiva))


def test_arial_faltante_cae_a_liberation_o_dejavu(monkeypatch):
    if fuentes.buscar_fuente("DejaVu Sans") is None:
        pytest.skip("No hay DejaVu Sans instalada")
    _sin(monkeypatch, "Arial", "Liberation Sans")
    reg = fuentes.resolver_fuente("Arial")
    assert reg["familia"] == "DejaVu Sans"
    assert fuentes.buscar_fuente("Arial") is None      # buscar_fuente no sustituye
    assert fuentes.contornos_texto("Hola", "Arial", 10)  # el texto se dibuja igual


def test_fuente_sin_equivalente_sigue_faltando(monkeypatch):
    assert fuentes.resolver_fuente("esta fuente no existe 123") is None
    with pytest.raises(fuentes.ErrorFuente, match="No se encontró"):
        fuentes.contornos_texto("Hola", "esta fuente no existe 123", 10)
