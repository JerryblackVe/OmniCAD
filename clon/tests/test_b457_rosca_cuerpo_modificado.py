"""B-457: la rosca modelada rápida (P-78, B-461) da el mismo volumen sobre cuerpos ya modificados (chaflán, empalme, unión
a una base), en cada giro del respaldo, y cae sola al corte de siempre si la vía directa falla.

Referencia: la vía directa (`_rosca_directa`) se comprueba contra el volumen exacto del surco antes de devolver; el corte
con un `geo.booleano` suelto NO sirve de referencia (en un cilindro solo saca 37,4 mm³ de 249,6, ver `_cortar_helicoidal`)."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc

GIROS = (0, 229, 61, 137)


def _llamar(sesion, herramienta, **argumentos):
    resultado = api.llamar(sesion, herramienta, argumentos)
    assert resultado["ok"], resultado


def _cuerpo_modificado(modificacion):
    sesion = api.Sesion()
    _llamar(sesion, "create_cylinder", radius=6, height=12)
    if modificacion == "chaflanado":
        _llamar(sesion, "chamfer", edges=">Z", distance=1)
    elif modificacion == "empalmado":
        _llamar(sesion, "fillet", edges=">Z", radius=1)
    else:
        _llamar(sesion, "create_box", length=24, width=18, height=3, x=2, z=-3, operation="join")
    return sesion


def _volumen(sesion):
    cuerpos = list(sesion.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1 and geo.es_valida(cuerpos[0].forma) and len(geo.solidos(cuerpos[0].forma)) == 1
    return geo.volumen_exacto(cuerpos[0].forma, 1e-6)


def _roscar(modificacion):
    sesion = _cuerpo_modificado(modificacion)
    inicial = _volumen(sesion)
    sc._surco_en_origen.cache_clear()
    _llamar(sesion, "create_thread", faces="%CYLINDER", thread="M12x1.75", thread_class="6g")
    return inicial, _volumen(sesion)


def _corte_desde_giro(original, giro, intentos):
    """BRepAlgoAPI_Cut que falla en los giros anteriores a `giro`, para llegar también a los respaldos de 61° y 137°."""
    class CorteDesdeGiro(original):
        def Build(self, *argumentos):
            indice = len(intentos) % len(GIROS)
            intentos.append(GIROS[indice])
            self.omitido = indice < GIROS.index(giro)
            if not self.omitido:
                return super().Build(*argumentos)

        def IsDone(self):
            return not self.omitido and super().IsDone()
    return CorteDesdeGiro


@pytest.fixture(autouse=True)
def _sin_cache():
    yield
    sc._surco_en_origen.cache_clear()


@pytest.mark.parametrize("modificacion", ["chaflanado", "empalmado", "unido_a_base"])
def test_b457_la_via_directa_y_el_corte_con_cada_giro_dan_el_mismo_volumen(monkeypatch, modificacion):
    cortes = []
    original_corte = sc._cortar_helicoidal
    monkeypatch.setattr(sc, "_cortar_helicoidal", lambda *a: cortes.append(1) or original_corte(*a))
    inicial, directa = _roscar(modificacion)
    assert not cortes and directa < inicial - 1                  # la rosca salió por la vía directa, sin booleana helicoidal

    monkeypatch.setattr(sc, "_rosca_directa", lambda *a: None)    # ahora, el corte de siempre (B-461)
    original = sc.BRepAlgoAPI_Cut
    for giro in GIROS:
        intentos = []
        monkeypatch.setattr(sc, "BRepAlgoAPI_Cut", _corte_desde_giro(original, giro, intentos))
        _, cortado = _roscar(modificacion)
        assert intentos[:GIROS.index(giro) + 1] == list(GIROS[:GIROS.index(giro) + 1])
        assert cortado == pytest.approx(directa, rel=1e-5), f"{modificacion}, {giro}°"
        monkeypatch.setattr(sc, "BRepAlgoAPI_Cut", original)


@pytest.mark.parametrize("modificacion", ["chaflanado", "unido_a_base"])
def test_b457_si_la_via_directa_falla_cae_sola_al_corte_de_siempre(monkeypatch, modificacion):
    _, directa = _roscar(modificacion)

    def falla(*_a):
        raise RuntimeError("falla del kernel")

    monkeypatch.setattr(sc, "_varilla_roscada", falla)           # `_rosca_directa` lo atrapa y devuelve None
    cortes = []
    original = sc._cortar_helicoidal
    monkeypatch.setattr(sc, "_cortar_helicoidal", lambda *a: cortes.append(1) or original(*a))
    _, respaldo = _roscar(modificacion)
    assert cortes and respaldo == pytest.approx(directa, rel=1e-5)
