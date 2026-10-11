"""Marcadores persistentes de sessões não rastreáveis (UAC/startfile)."""
from __future__ import annotations

import datetime
import math
from pathlib import Path

from bib_nucleo.arquivos import gravar_json, ler_json


def iniciar_sessao_manual(gid: int, titulo: str = "") -> dict:
    from bib_nucleo.base import SESSOES_DIR, agora_iso
    try:
        SESSOES_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        arq = SESSOES_DIR / f"sessao-{int(gid)}-{ts}.json"
        gravar_json(arq, {"gid": int(gid), "titulo": titulo, "inicio": agora_iso(), "modo": "manual"})
        return {"ok": True, "arquivo": str(arq)}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


def listar_sessoes_pendentes() -> list[dict]:
    from bib_nucleo.base import SESSOES_DIR
    out = []
    try:
        for arq in sorted(SESSOES_DIR.glob("sessao-*.json")):
            if arq.is_symlink():
                continue
            d = ler_json(arq)
            if isinstance(d, dict):
                out.append(dict(d, _arquivo=str(arq)))
    except OSError:
        pass
    return out


def encerrar_sessao_manual(arquivo: str, horas: float = 0.0, db_path=None) -> dict:
    from bib_nucleo.banco import adicionar_horas, get_db
    from bib_nucleo.base import DEFAULT_DB, SESSOES_DIR
    p = Path(arquivo)
    if p.is_symlink() or p.resolve().parent != SESSOES_DIR.resolve() or not p.name.startswith("sessao-"):
        return {"ok": False, "erro": "marcador fora da pasta de sessões; nada foi alterado"}
    try:
        horas = float(horas)
        if not math.isfinite(horas) or horas < 0:
            raise ValueError("horas inválidas")
    except (TypeError, ValueError):
        return {"ok": False, "erro": "horas deve ser número finito >= 0"}
    d = ler_json(p)
    try:
        if not isinstance(d, dict):
            raise ValueError("marcador não é objeto")
        gid = int(d.get("gid") or 0)
    except (ValueError, TypeError):
        p.unlink(missing_ok=True)
        return {"ok": False, "erro": "marcador inválido (removido)"}
    res = {"ok": True, "somado": 0.0}
    if horas > 0 and gid:
        try:
            con = get_db(Path(db_path) if db_path is not None else DEFAULT_DB)
            try:
                con.execute("CREATE TABLE IF NOT EXISTS sessoes_reconciliadas (marcador TEXT PRIMARY KEY)")
                ja = con.execute("SELECT 1 FROM sessoes_reconciliadas WHERE marcador=?", (p.name,)).fetchone()
                if ja:
                    r = {"ok": True, "somado": 0.0}
                else:
                    jogo = con.execute("SELECT uuid,titulo FROM jogos WHERE id=?", (gid,)).fetchone()
                    if jogo is None:
                        return {"ok": False, "erro": "jogo inexistente; marcador preservado"}
                    from bib_nucleo.estatisticas import registrar
                    from bib_nucleo.preferencias_pessoais import ler_preferencias
                    registrar(con, dict(jogo), horas, ler_preferencias()["ativo"], commit=False)
                    con.execute("INSERT INTO sessoes_reconciliadas(marcador) VALUES(?)", (p.name,))
                    # adicionar_horas confirma horas + histórico + marcador na
                    # mesma transação: falha ao apagar o JSON não duplica horas.
                    r = adicionar_horas(con, gid, horas)
                    if not r.get("ok"):
                        con.rollback()
            finally:
                con.close()
            if not r.get("ok"):
                return {"ok": False, "erro": r.get("erro", "falha")}
            res["somado"] = r["somado"]
        except Exception as e:
            return {"ok": False, "erro": f"{type(e).__name__}: {e}"}
    try:
        p.unlink()
    except OSError:
        pass
    return res
