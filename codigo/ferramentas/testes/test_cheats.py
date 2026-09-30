"""Cheats Gateway: parse, toggle *citra_enabled, add/remove, tudo em sandbox."""
import os
import tempfile
from pathlib import Path

from executar import afirmar

TID = "000400000011C400"
COD = "08C650C0 00000002\nD3000000 08000000"


def _emu_fake():
    from executar import azahar_fake
    emu = Path(os.environ.get("BIBLIOTECA_AZAHAR_DIR"))
    (emu / "user").mkdir(parents=True, exist_ok=True)
    return azahar_fake(emu)


def teste_cheats_add_toggle_remove():
    from bib_nucleo import cheats as CH
    tmp = Path(tempfile.mkdtemp(prefix="suite-cheat-"))
    _emu_fake()
    afirmar(CH.listar_cheats(TID) == [])
    afirmar(CH.cheats_ativos(TID) == [])
    r = CH.adicionar_cheat("curto", "C", "00 11")
    afirmar(not r.get("ok"), r)
    r = CH.adicionar_cheat(TID, "60FPS", "08c650c0 00000002")
    afirmar(r.get("ok") and r["linhas"] == 1, r)
    lst = CH.listar_cheats(TID)
    afirmar(len(lst) == 1 and not lst[0]["ativo"], lst)  # nasce OFF
    r = CH.adicionar_cheat(TID, "60FPS", "00112233 44556677")
    afirmar(not r.get("ok") and "existe" in r["erro"], r)
    r = CH.adicionar_cheat(TID, "Ruim", "00112233 44556677\nZZZZZZZZ 00000000")
    afirmar(not r.get("ok") and "inválida" in r["erro"], r)
    r = CH.definir_cheat(TID, "60FPS", True)
    afirmar(r.get("ok") and r["ativo"], r)
    afirmar(CH.cheats_ativos(TID) == ["60FPS"])
    txt = CH.cheats_path(TID).read_text(encoding="utf-8")
    afirmar("[60FPS]\n*citra_enabled\n08C650C0 00000002" in txt, txt)
    r = CH.alternar_cheat(TID, "60FPS")
    afirmar(r.get("ok") and not r["ativo"], r)
    afirmar(CH.cheats_ativos(TID) == [])
    r = CH.adicionar_cheat(TID, "NoOut", "00379EB4 00000000\n*nota\n\n00379EB8 00000000")
    afirmar(r.get("ok") and r["linhas"] == 3, r)
    afirmar(len(CH.listar_cheats(TID)) == 2)
    r = CH.remover_cheat(TID, "60FPS")
    afirmar(r.get("ok"), r)
    afirmar([c["nome"] for c in CH.listar_cheats(TID)] == ["NoOut"])
    r = CH.remover_cheat(TID, "NoOut")
    afirmar(r.get("ok") and r.get("apagado"), r)
    afirmar(not CH.cheats_path(TID).exists())
    afirmar(CH.listar_cheats(TID) == [])


def teste_cheats_preserva_resto():
    from bib_nucleo import cheats as CH
    tmp = Path(tempfile.mkdtemp(prefix="suite-cheat-"))
    _emu_fake()
    arq = CH.cheats_path(TID)
    arq.write_text("# meus cheats\n\n[Um]\n*citra_enabled\n00112233 44556677\n*obs\n\n[Dois]\nAABBCCDD EEFF0011\n",
                   encoding="utf-8")
    lst = CH.listar_cheats(TID)
    afirmar(len(lst) == 2 and lst[0]["ativo"] and not lst[1]["ativo"], lst)
    r = CH.definir_cheat(TID, "Dois", True)
    afirmar(r.get("ok"), r)
    txt = arq.read_text(encoding="utf-8")
    afirmar(txt.startswith("# meus cheats") and "*obs" in txt, txt)
    afirmar(txt.count("*citra_enabled") == 2, txt)
    r = CH.definir_cheat(TID, "Um", False)
    afirmar(r.get("ok"), r)
    txt = arq.read_text(encoding="utf-8")
    afirmar("[Um]\n00112233 44556677\n*obs" in txt, txt)
    r = CH.definir_cheat(TID, "Fantasma", True)
    afirmar(not r.get("ok"), r)
    r = CH.adicionar_cheat(TID, "[Hack]", "00112233 44556677")
    afirmar(not r.get("ok"), r)
