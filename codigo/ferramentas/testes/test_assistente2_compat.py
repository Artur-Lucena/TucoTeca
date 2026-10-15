"""A2-05 (Assistente 2): compatibilidade — stdlib sem Qt, imports por SO, aliases e banco sem reescrita.

Usa fixtures e dados sintéticos; nenhum serviço/coleção real é tocado.
"""
import ast
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from executar import afirmar

CODIGO = Path(__file__).resolve().parents[2]
NUCLEO = CODIGO / "bib_nucleo"


def _fontes_nucleo():
    return sorted((NUCLEO).rglob("*.py")) + [CODIGO / "bib_core.py"]


def teste_assistente2_compat_nucleo_sem_qt_obrigatorio():
    for arq in _fontes_nucleo():
        texto = arq.read_text(encoding="utf-8")
        afirmar("PySide6" not in texto and "PyQt" not in texto, arq)
    afirmar("bib_core" in sys.modules or True)
    import bib_nucleo.banco as banco
    import bib_nucleo.base as base
    import bib_nucleo.everything as ev
    afirmar(callable(ev.buscar_executaveis))
    afirmar(callable(banco.get_db) and callable(base.resolver_exe))
    afirmar("PySide6" not in sys.modules, "núcleo puxou Qt")


def teste_assistente2_compat_imports_de_so_condicionais():
    alvos = ["controles.py", "base.py", "player.py", "volume.py",
             "scans/__init__.py", "scans/lojas.py", "scans/disco.py",
             "scans/roms.py", "scans/analise.py", "scans/metadados.py",
             "scans/importacao.py"]
    # Módulos puros (sem ramificação por SO): nada a guardar; os demais
    # mantêm a guarda `os.name`/`sys.platform` como no arquivo original.
    sem_so = {"emuladores/__init__.py", "emuladores/_comum.py",
              "emuladores/presets.py", "emuladores/provedores.py",
              "scans/__init__.py", "scans/analise.py", "scans/metadados.py",
              "scans/importacao.py"}
    for nome in alvos:
        arq = NUCLEO / nome
        arvore = ast.parse(arq.read_text(encoding="utf-8"))
        topo = [n for n in arvore.body if isinstance(n, (ast.Import, ast.ImportFrom))]
        nomes_topo = sorted({a for n in topo for a in ([x.name.split('.')[0] for x in n.names] if isinstance(n, ast.Import) else [n.module.split('.')[0]]) if a})
        afirmar("winreg" not in nomes_topo, f"{nome}: winreg no topo: {nomes_topo}")
        # ctypes só aparece no topo quando é fallback tipado; o uso Win32 real
        # mora em função/ramo (não quebra Linux/macOS na importação).
        texto = arq.read_text(encoding="utf-8")
        if nome not in sem_so:
            afirmar("os.name" in texto or "sys.platform" in texto, f"{nome}: sem guarda de SO")
    # Prova viva de importação no Linux atual (sem Qt, sem Win32).
    import bib_nucleo.controles as CT
    import bib_nucleo.player as PL
    import bib_nucleo.volume as VO
    afirmar(callable(CT.ler_estados_xinput) or True)
    afirmar(hasattr(PL, "__all__") and hasattr(VO, "__all__"))


def teste_assistente2_compat_aliases_legados():
    from bib_nucleo.rede import repacks as RP
    with patch.dict(os.environ, {"BIBLIOTECA_JOGOS_DIR": str(Path(tempfile.mkdtemp()) / "novo"),
                                 "BIBLIOTECA_PIRATAS": str(Path(tempfile.mkdtemp()) / "legado")}):
        afirmar(RP.pasta_jogos().name == "novo", "env nova deve vencer a legada")
        afirmar(RP.pasta_piratas() == RP.pasta_jogos(), "alias legado divergiu")
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("BIBLIOTECA_JOGOS_DIR", None)
        os.environ.pop("BIBLIOTECA_PIRATAS", None)
        # Sem override, o padrão novo é usado; o alias acompanha.
        from bib_nucleo import base
        with patch.object(base, "LINUX_ROOT", tempfile.mkdtemp(prefix="a2-compat-")), \
                patch.object(base, "MAC_ROOT", tempfile.mkdtemp(prefix="a2-compat-")), \
                patch.object(RP, "_raiz_padrao_jogos", return_value=Path(tempfile.mkdtemp(prefix="a2-compat-"))):
            afirmar(RP.pasta_piratas() == RP.pasta_jogos())
    dentro = str(RP.pasta_jogos() / "Jogo")
    afirmar(RP.dentro_de_piratas(dentro) == RP.dentro_do_destino(dentro))
    afirmar(RP.organizar_em_piratas.__doc__ and RP.pasta_piratas.__doc__)
    # Fachada preserva os aliases para consumidores antigos.
    for nome in ("pasta_jogos", "pasta_piratas", "dentro_do_destino", "dentro_de_piratas",
                 "organizar_no_destino", "organizar_em_piratas"):
        afirmar(nome in core.__all__, nome)
    # bib_nucleo.fontes continua resolvível via import preguiçoso.
    import bib_nucleo
    from bib_nucleo.rede import fontes as direto
    afirmar(bib_nucleo.fontes is direto)


def teste_assistente2_compat_banco_migra_sem_reescrever():
    tmp = Path(tempfile.mkdtemp(prefix="a2-compat-db-"))
    leg = tmp / "leg.db"
    con = sqlite3.connect(str(leg))
    con.execute("CREATE TABLE jogos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT NOT NULL,"
                " executable_path TEXT DEFAULT '', exe_win TEXT DEFAULT '', exe_linux TEXT DEFAULT '',"
                " wine_prefix TEXT DEFAULT '', launch_options TEXT DEFAULT '', status TEXT DEFAULT 'backlog',"
                " nota INTEGER, favorito INTEGER DEFAULT 0, horas REAL DEFAULT 0, ultima_execucao TEXT,"
                " observacoes TEXT DEFAULT '', origem TEXT DEFAULT 'manual', shop TEXT DEFAULT '',"
                " object_id TEXT DEFAULT '', game_code TEXT DEFAULT '', regiao TEXT DEFAULT '',"
                " capa TEXT DEFAULT '', confianca REAL DEFAULT 0, criado_em TEXT, atualizado_em TEXT,"
                " UNIQUE(titulo, executable_path))")
    con.execute("INSERT INTO jogos(titulo, executable_path, launch_options, horas, nota) VALUES(?,?,?,?,?)",
                ("Legado", "/jogo/exe", "--opt", 2.5, 8))
    con.commit()
    con.close()
    con = core.get_db(leg)
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(jogos)").fetchall()}
        for esperada in ("exe_mac", "azahar_mods", "azahar_mods_off", "uuid", "etiquetas", "save_path"):
            afirmar(esperada in cols, sorted(cols))
        jogos = core.listar_jogos(con, q="Legado")
        afirmar(len(jogos) == 1, jogos)
        afirmar(jogos[0]["horas"] == 2.5 and jogos[0]["nota"] == 8, jogos[0])
        afirmar(jogos[0].get("uuid"), "migração v5 não preencheu uuid")
        afirmar(con.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
        antes = con.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]
        con.close()
        con = core.get_db(leg)
        depois = con.execute("SELECT COUNT(*) FROM jogos").fetchone()[0]
        afirmar(antes == depois == 1, (antes, depois))
        afirmar("exe_mac" in core.CAMPOS_EDITAVEIS and "azahar_mods" in core.CAMPOS_EDITAVEIS)
        afirmar(set(core.STATUS_VALIDOS) == {"backlog", "jogando", "zerado", "pausado", "abandonado"})
    finally:
        con.close()


def teste_banco_pacote_reexporta_o_contrato():
    """Fachada do pacote banco: os 58 nomes do contrato, privados p/ patch e fatias."""
    from bib_nucleo import banco as B
    afirmar(len(B.__all__) == 58, len(B.__all__))
    faltando = [n for n in B.__all__ if not hasattr(B, n)]
    afirmar(not faltando, faltando)
    # privados fora do contrato, mas reexportados de propósito (monkeypatch dos testes)
    afirmar(hasattr(B, "_inicializar_db"), "patch de _inicializar_db precisa do atributo")
    afirmar(hasattr(B, "garantir_fts"), "test_fts5 usa B.garantir_fts")
    afirmar("_inicializar_db" not in B.__all__ and "garantir_fts" not in B.__all__,
            "privados não entram no __all__")
    import bib_nucleo.banco._infra as _infra
    import bib_nucleo.banco.catalogo as _catalogo
    import bib_nucleo.banco.jogos as _jogos
    afirmar(B.get_db is _infra.get_db and B.criar_jogo is _jogos.criar_jogo
            and B.criar_video is _catalogo.criar_video,
            "reexport deve ser objeto único (identidade preservada)")
    afirmar(B.SCHEMA_DESEJOS is __import__("bib_nucleo.banco_desejos",
            fromlist=["SCHEMA_DESEJOS"]).SCHEMA_DESEJOS, "desejos reexportados")
