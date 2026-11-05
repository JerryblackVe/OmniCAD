"""La API del registro: get_usage_settings y set_usage_logging con todas las opciones y sus rangos."""
import pytest

from omnicad import api
from omnicad import registro_uso as ru


@pytest.fixture(autouse=True)
def aislado(tmp_path, monkeypatch):
    ru.configurar(False)
    ru.aplicar(ru.FABRICA)
    monkeypatch.setenv("OMNICAD_REGISTRO_DIR", str(tmp_path / "registro"))
    monkeypatch.setenv("OMNICAD_AJUSTES_INI", str(tmp_path / "prefs.ini"))
    yield
    ru.configurar(False)
    ru.ultimo = None
    ru.aplicar(ru.FABRICA)


def _llamar(**args):
    return api.llamar(api.Sesion(), "set_usage_logging", args)


def test_get_usage_settings_trae_todo():
    r = api.llamar(api.Sesion(), "get_usage_settings", {})
    assert r["ok"], r
    d = r["result"]
    for clave in ("enabled", "detailed", "capture_on_error", "retention_days", "total_mb",
                  "captures_mb", "min_free_gb", "memory_every_s"):
        assert clave in d["settings"], clave
        assert clave in d["ranges"], clave
        assert clave in d["factory"], clave
    assert d["settings"]["retention_days"] == 7 and d["factory"]["total_mb"] == 150
    assert d["state"]["paused_low_disk"] is False
    assert "folder" in d["state"] and "used_mb" in d["state"] and "sessions" in d["state"]


def test_set_usage_logging_acepta_unas_pocas_o_ninguna():
    assert _llamar(enabled=True)["ok"]
    r = _llamar(detailed=True, retention_days=10, memory_every_s=45)
    assert r["ok"], r
    v = r["result"]
    assert v["settings"]["detailed"] is True and v["settings"]["enabled"] is True
    assert v["settings"]["retention_days"] == 10 and v["settings"]["memory_every_s"] == 45
    assert ru.VALORES["retencion_dias"] == 10                      # rigen sin reiniciar
    assert _llamar()["ok"]                                          # sin parámetros: informa sin cambiar


@pytest.mark.parametrize("clave,valor", [("retention_days", 0), ("retention_days", 91), ("total_mb", 19),
                                         ("total_mb", 2001), ("captures_mb", 501), ("min_free_gb", 0.4),
                                         ("min_free_gb", "dos"), ("memory_every_s", 4), ("memory_every_s", 301)])
def test_rangos_como_en_la_ventana(clave, valor):
    r = _llamar(**{clave: valor})
    assert not r["ok"] and r["error_kind"] == "INVALID_ARGUMENTS"
    textos = " ".join([r["mensaje"], *r.get("pistas", [])]).lower()
    assert "rango" in textos or "número" in textos or "tipo incorrecto" in textos


def test_capturas_nunca_pasán_del_tope_total():
    r = _llamar(total_mb=20, captures_mb=50)
    assert r["ok"], r
    assert r["result"]["settings"]["captures_mb"] == 20          # se recorta al tope total
    assert _llamar(total_mb=20, captures_mb=10)["result"]["settings"]["captures_mb"] == 10


def test_el_detalizado_es_la_clave_de_api_del_punto_5():
    assert _llamar(detailed=True)["result"]["settings"]["detailed"] is True
    assert _llamar(detailed=False)["result"]["settings"]["detailed"] is False


def test_get_usage_log_informa_la_pausa_por_disco(tmp_path, monkeypatch):
    from omnicad.registro_uso import sistema
    assert _llamar(enabled=True)["ok"]
    ru.activo.cola.join()                                        # la primera línea ya está en el disco
    r = api.llamar(api.Sesion(), "get_usage_log", {})
    assert r["ok"] and r["result"]["paused_low_disk"] is False
    monkeypatch.setattr(sistema, "disco_libre", lambda ruta: 1)
    r = api.llamar(api.Sesion(), "get_usage_log", {})
    assert r["ok"] and r["result"]["paused_low_disk"] is True


def test_nombres_de_herramientas_en_el_catalogo():
    from omnicad.api import registro as reg
    claves = {h["nombre"] for h in reg.catalogo()}
    assert {"get_usage_settings", "set_usage_logging", "get_usage_log"} <= claves
