"""`--jogar` headless: resolve por id/título e erra sem abrir jogo ou janela."""
import tempfile
from contextlib import closing
from pathlib import Path

import bib_core as core
import desktop
from atalho_jogo import abrir, resolver_jogo_cli
from executar import afirmar


def _banco():
    db = Path(tempfile.mkdtemp()) / "biblioteca.db"
    with closing(core.get_db(db)) as con:
        core.criar_jogo(con, {"titulo": "Megabonk",
                              "executable_path": str(db.parent / "megabonk.exe")})
        core.criar_jogo(con, {"titulo": "Ball x Pit",
                              "executable_path": str(db.parent / "ball.exe")})
        core.criar_jogo(con, {"titulo": "Mega Blaster",
                              "executable_path": str(db.parent / "blaster.exe")})
    return db


def teste_resolver_acha_por_id_exato_e_parcial():
    db = _banco()
    with closing(core.get_db(db)) as con:
        afirmar(resolver_jogo_cli(con, "2")["titulo"] == "Ball x Pit",
                "id 2 deveria resolver Ball x Pit")
        afirmar(resolver_jogo_cli(con, "megabonk")["titulo"] == "Megabonk",
                "título exato deveria vencer")
        afirmar(resolver_jogo_cli(con, "ball")["titulo"] == "Ball x Pit",
                "parcial único deveria resolver")


def teste_resolver_recusa_ambiguo_vazio_e_inexistente():
    db = _banco()
    with closing(core.get_db(db)) as con:
        for busca in ("mega", "999", "sem-jogo-assim", "   "):
            try:
                resolver_jogo_cli(con, busca)
            except LookupError:
                continue
            afirmar(False, f"'{busca}' deveria levantar LookupError")


def teste_jogar_rota_headless_devolve_2_sem_abrir_janela():
    db = _banco()
    afirmar(abrir("sem-jogo-assim", db=str(db)) == 2,
            "abrir() deveria devolver 2")
    afirmar(desktop.main(["--jogar", "sem-jogo-assim", "--db", str(db)]) == 2,
            "rota --jogar do desktop deveria devolver 2")
    afirmar(desktop.main(["--jogar=sem-jogo-assim", f"--db={db}"]) == 2,
            "forma --jogar=... deveria devolver 2")
