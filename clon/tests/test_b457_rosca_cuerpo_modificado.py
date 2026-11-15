"""B-457: el corte rápido de P-78 conserva el volumen sobre cuerpos ya modificados."""
import pytest

from omnicad import api
from omnicad.nucleo import geometria as geo
from omnicad.nucleo import solidos_crear as sc


class _DiferenciaVolumen(AssertionError):
    """Solo la discrepancia conocida de volumen puede quedar como xfail."""


def _llamar(sesion, herramienta, **argumentos):
    resultado = api.llamar(sesion, herramienta, argumentos)
    assert resultado["ok"], resultado


def _cuerpo_modificado(modificacion):
    sesion = api.Sesion()
    _llamar(sesion, "create_cylinder", radius=6, height=12)
    if modificacion == "chaflanado":
        _llamar(sesion, "chamfer", edges=">Z", distance=1)
    else:
        _llamar(sesion, "create_box", length=24, width=18, height=3, x=2, z=-3, operation="join")
    return sesion


def _forma(sesion):
    cuerpos = list(sesion.doc.estado_final.cuerpos.values())
    assert len(cuerpos) == 1
    forma = cuerpos[0].forma
    assert geo.es_valida(forma)
    assert len(geo.solidos(forma)) == 1
    return forma


@pytest.mark.parametrize("modificacion", [
    "chaflanado",
    pytest.param("unido_a_base", marks=pytest.mark.xfail(
        strict=True, raises=_DiferenciaVolumen,
        reason="B-457: M12x1.75 6g unido a una base deja 2394,488 mm³ con P-78 frente a 2323,094 mm³ "
               "con el corte normal (diferencia 71,394 mm³, 3,07 %) en los cuatro giros.",
    )),
])
@pytest.mark.parametrize("giro", [0, 229, 61, 137])
def test_b457_rosca_modificada_coincide_con_el_corte_normal(monkeypatch, modificacion, giro):
    monkeypatch.setattr(sc, "_rosca_directa", lambda *a: None)     # prueba los giros del corte de siempre (B-461)
    sesion = _cuerpo_modificado(modificacion)
    volumen_inicial = geo.volumen_exacto(_forma(sesion), 1e-6)
    giros = (0, 229, 61, 137)
    intentos = []
    original = sc.BRepAlgoAPI_Cut

    class CorteDesdeGiro(original):
        def Build(self, *argumentos):
            indice = len(intentos) % len(giros)
            intentos.append(giros[indice])
            # Simula cortes fallidos anteriores para alcanzar también los respaldos de 61° y 137°.
            self.omitido = indice < giros.index(giro)
            if not self.omitido:
                return super().Build(*argumentos)

        def IsDone(self):
            return not self.omitido and super().IsDone()

    try:
        sc._surco_en_origen.cache_clear()
        monkeypatch.setattr(sc, "BRepAlgoAPI_Cut", CorteDesdeGiro)
        _llamar(sesion, "create_thread", faces="%CYLINDER", thread="M12x1.75", thread_class="6g")
        rapido = geo.volumen_exacto(_forma(sesion), 1e-6)
        assert intentos[:giros.index(giro) + 1] == list(giros[:giros.index(giro) + 1])
        assert rapido < volumen_inicial - 1

        monkeypatch.setattr(sc, "BRepAlgoAPI_Cut", original)
        sesion_normal = _cuerpo_modificado(modificacion)
        cortes_normales = []

        def cortar_normal(cuerpo, herramienta, origen, eje):
            cortes_normales.append(1)
            return geo.booleano(cuerpo, herramienta, "cortar")

        monkeypatch.setattr(sc, "_cortar_helicoidal", cortar_normal)
        sc._surco_en_origen.cache_clear()
        _llamar(sesion_normal, "create_thread", faces="%CYLINDER", thread="M12x1.75", thread_class="6g")
        normal = geo.volumen_exacto(_forma(sesion_normal), 1e-6)
        assert cortes_normales
        assert normal < volumen_inicial - 1
        if rapido != pytest.approx(normal, rel=1e-5):
            raise _DiferenciaVolumen(f"{modificacion}, {giro}°: {rapido=} frente a {normal=} mm³")
    finally:
        sc._surco_en_origen.cache_clear()
