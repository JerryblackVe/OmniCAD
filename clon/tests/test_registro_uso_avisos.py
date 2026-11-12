"""B-332: avisos, «calculando…» e instrucciones van al registro de uso como `aviso`, no como `error`."""
from types import SimpleNamespace

from omnicad import registro_uso as ru
from omnicad.registro_uso import ganchos
from omnicad.ui import comando as mod_comando


class _Falso:
    def __init__(self):
        self.eventos = []

    def emitir(self, tipo, datos=None, **_):
        self.eventos.append((tipo, datos))


def _mostrar(monkeypatch, texto, tipo):
    falso = _Falso()
    monkeypatch.setattr(ru, "activo", falso)
    monkeypatch.setattr(mod_comando, "poner_mensaje", lambda *a: None)
    panel = SimpleNamespace(comando=SimpleNamespace(CLAVE="extruir"), _uso_error=None, icono_mensaje=None,
                            mensaje=None, _reubicar=lambda: None)
    mod_comando.PanelComando._mostrar(panel, texto, tipo=tipo)
    return falso.eventos


def test_aviso_calculando_e_instruccion_no_son_error(monkeypatch):
    for tipo in ("aviso", "calculando", "instruccion"):
        assert [e[0] for e in _mostrar(monkeypatch, "Calculando vista previa…", tipo)] == ["aviso"]


def test_error_e_invalido_siguen_siendo_error_y_resultado_fallido(monkeypatch):
    for tipo in ("error", "invalido"):
        ev = _mostrar(monkeypatch, "Falta un perfil.", tipo)
        assert [e[0] for e in ev] == ["error", "comando_resultado"]
        assert ev[0][1]["excepcion"] == ("EntradaInvalida" if tipo == "invalido" else "ErrorComando")


def test_gancho_aviso_emite_evento_propio(monkeypatch):
    falso = _Falso()
    monkeypatch.setattr(ru, "activo", falso)
    ganchos.aviso(origen="comando", comando="extruir", mensaje="hola")
    assert falso.eventos == [("aviso", {"origen": "comando", "comando": "extruir", "mensaje": "hola"})]


def test_valor_mal_tecleado_es_aviso_baja_y_un_error_real_sigue_siendo_alto(monkeypatch):
    from omnicad.registro_uso import detector

    def hallazgo(tipo):
        ev = _mostrar(monkeypatch, "No es un número.", tipo)[0]
        evento = {"tipo": "error", "t": 1.0, "datos": ev[1]}
        return detector.analizar([evento])[0]

    invalido, error = hallazgo("invalido"), hallazgo("error")
    assert (invalido["severidad"], invalido["tabla"]) == ("baja", "mejoras.md")
    assert (error["severidad"], error["tabla"]) == ("alta", "bugs.md")
