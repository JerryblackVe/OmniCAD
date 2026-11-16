"""Hooks de .claude/hooks: aviso de contexto por crecimiento y recordatorio de git commit."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[2] / ".claude" / "hooks"


def _cargar():
    spec = importlib.util.spec_from_file_location("ctx25", HOOKS / "ctx25.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _transcript(tmp_path, usos):
    ruta = tmp_path / "t.jsonl"
    ruta.write_text("\n".join(json.dumps({"message": {"usage": {"input_tokens": u}}}) for u in usos), encoding="utf-8")
    return ruta


def test_aviso_ventana_y_rol(tmp_path, monkeypatch):
    monkeypatch.delenv("OMNICAD_CTX_VENTANA", raising=False)
    m = _cargar()
    assert m.aviso(50_000, "claude-sonnet-5-5", "OmniCAD · E1") == ""  # 25 % de 200K: no avisa
    e = m.aviso(75_000, "claude-sonnet-5-5", "OmniCAD · E1 Bocetos")  # 37 % de 200K
    assert "37 %" in e and "35 %" in e and "clear_session + brief" in e
    assert m.aviso(290_000, "claude-opus-5-5[1m]", "OmniCAD · E1") == ""  # 29 % de 1M
    assert m.aviso(310_000, "claude-opus-5-5", "x") != ""  # pasó 200K: ventana 1M, 31 %
    c = m.aviso(70_000, "claude-opus-5-5", "Coordinador principal OmniCAD en VPS")
    assert "40 %" in c and "sin clear_session" in c
    monkeypatch.setenv("OMNICAD_CTX_VENTANA", "1000000")
    assert m.aviso(70_000, "claude-opus-5-5", "x") == ""


def test_leer_transcript(tmp_path):
    m = _cargar()
    ruta = tmp_path / "t.jsonl"
    filas = [{"type": "custom-title", "customTitle": "OmniCAD · E7"},
             {"message": {"model": "claude-sonnet-5-5", "usage": {"input_tokens": 10, "cache_read_input_tokens": 70_000}}}]
    ruta.write_text("\n".join(json.dumps(f) for f in filas), encoding="utf-8")
    assert m.leer(str(ruta)) == (70_010, "claude-sonnet-5-5", "OmniCAD · E7")


def _correr(script, entrada):
    r = subprocess.run([sys.executable, str(HOOKS / script)], input=json.dumps(entrada), capture_output=True, text=True, timeout=30)
    assert r.returncode == 0
    return r.stdout


def test_aviso_commit_solo_si_es_git_commit():
    for c in ("git commit -m x", "git -C /p commit -m y", "git add a && git commit -m x", "git add a\ngit commit -m z"):
        assert "ponytail-review" in _correr("aviso_commit.py", {"tool_input": {"command": c}}), c
    for c in ("echo git commit", "for i in 1 2; do echo git commit; done", "git log --oneline"):
        assert _correr("aviso_commit.py", {"tool_input": {"command": c}}) == "", c


def test_ctx25_sin_transcript_no_falla():
    assert _correr("ctx25.py", {}) == ""
