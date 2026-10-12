"""A2-01 (Assistente 2): Everything com CLI simulada — descoberta, instância, Unicode e fallback.

Complementa test_everything.py sem duplicá-lo: aqui o foco é o contrato
exigido para a revisão (linha literal -search*, shell=False, sem -utf8/
-full-path/-argv, filtro de raízes, fallback em erro/vazio/timeout).
Tudo com subprocess simulado; nenhum es.exe real é executado.
"""
import os
import re
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from bib_nucleo import everything as E
from executar import afirmar


def _fixture():
    raiz = Path(tempfile.mkdtemp(prefix="a2-es-"))
    pasta = raiz / "Aventura (com espaço)"
    pasta.mkdir()
    exe = pasta / "jogo-ação.exe"
    exe.write_bytes(b"MZ-fixture-nao-executar")
    cli = raiz / "es.exe"
    cli.write_bytes(b"MZ-cli-fixture-nao-executar")
    return raiz, pasta, exe, cli


def _windows(cli, instancia=""):
    return patch.object(E, "os", SimpleNamespace(name="nt", sep=os.sep, environ={
        "BIBLIOTECA_EVERYTHING": str(cli), "BIBLIOTECA_EVERYTHING_INSTANCIA": instancia}))


def _exportado(comando):
    match = re.search(r'-export-txt (?:"([^"]+)"|(\S+))', comando)
    afirmar(match, comando)
    return Path(match[1] or match[2])


def teste_assistente2_everything_comando_literal_search_sem_shell():
    _, pasta, exe, cli = _fixture()
    chamadas = []

    def executar(comando, **kwargs):
        chamadas.append((comando, kwargs))
        afirmar(" -search* " in comando, comando)
        afirmar(comando.split(" -search* ", 1)[1].startswith("ext:exe <"), comando)
        afirmar(kwargs.get("shell") is False, "consulta não pode passar por shell")
        afirmar("-argv" not in comando, comando)
        afirmar("-utf8 " not in comando and "-full-path " not in comando, comando)
        afirmar("-utf8-bom" in comando and "-full-path-and-name" in comando, comando)
        afirmar("-timeout" in comando and "15000" in comando, comando)
        afirmar("-export-txt" in comando, comando)
        # Unicode/parênteses viajam literais dentro de path:"..."; < > | são
        # operadores da busca, jamais redirecionamento do Windows.
        afirmar('path:"' in comando and "<" in comando and ">" in comando, comando)
        afirmar(str(pasta) in comando, comando)
        _exportado(comando).write_text(str(exe), encoding="utf-8-sig")
        return SimpleNamespace(returncode=0)

    with _windows(cli, "TucoTeca-Prova"), patch.object(E.subprocess, "run", side_effect=executar):
        afirmar(E.buscar_executaveis([pasta]) == [str(exe.resolve())])
    afirmar(len(chamadas) == 1)


def teste_assistente2_everything_instancia_configuravel():
    _, pasta, exe, cli = _fixture()

    def executar_ok(comando, **kwargs):
        _exportado(comando).write_text(str(exe), encoding="utf-8-sig")
        return SimpleNamespace(returncode=0)

    with _windows(cli, "Minha-Instancia"), patch.object(E.subprocess, "run", side_effect=executar_ok) as run:
        afirmar(E.buscar_executaveis([pasta]) == [str(exe.resolve())])
        afirmar("-instance Minha-Instancia" in run.call_args.args[0])

    with _windows(cli, ""), patch.object(E.subprocess, "run", side_effect=executar_ok) as run:
        afirmar(E.buscar_executaveis([pasta]) == [str(exe.resolve())])
        afirmar("-instance" not in run.call_args.args[0], run.call_args.args[0])


def teste_assistente2_everything_filtra_raizes_e_recusa_symlink():
    raiz, pasta, exe, cli = _fixture()
    fora = raiz / "fora.exe"
    fora.write_bytes(b"fixture")
    maiusculo = pasta / "OUTRO.EXE"
    maiusculo.write_bytes(b"MZ-fixture")
    nao_exe = pasta / "nota.txt"
    nao_exe.write_text("fixture", encoding="utf-8")
    try:
        elo = pasta / "atalho.exe"
        elo.symlink_to(exe)
        tem_elo = True
    except OSError:
        tem_elo = False

    def executar(comando, **kwargs):
        linhas = [str(exe), str(exe.resolve()), str(fora), str(nao_exe),
                   str(pasta / "ausente.exe"), str(maiusculo)]
        if tem_elo:
            linhas.append(str(elo))
        _exportado(comando).write_text("\n".join(linhas), encoding="utf-8-sig")
        return SimpleNamespace(returncode=0)

    with _windows(cli), patch.object(E.subprocess, "run", side_effect=executar):
        obtido = E.buscar_executaveis([pasta])
    esperado = sorted({str(exe.resolve()), str(maiusculo.resolve())})
    afirmar(obtido == esperado, obtido)
    if tem_elo:
        afirmar(str(elo.resolve()) in obtido or str(elo) not in obtido, obtido)


def teste_assistente2_everything_recusa_raiz_com_aspas_sem_executar():
    raiz, pasta, _, cli = _fixture()
    com_aspas = raiz / 'pasta"com-aspas'
    try:
        com_aspas.mkdir()
    except OSError:
        # Windows proíbe `"` em nomes: a raiz nem chega a existir, então
        # nada há para consultar — sem executar a CLI, sem consumir índice.
        with _windows(cli), patch.object(E.subprocess, "run") as run:
            afirmar(E.buscar_executaveis([com_aspas]) == [])
            run.assert_not_called()
        return
    with _windows(cli), patch.object(E.subprocess, "run") as run:
        afirmar(E.buscar_executaveis([com_aspas]) is None)
        run.assert_not_called()


def teste_assistente2_everything_fallback_erro_vazio_timeout_e_limite():
    _, pasta, exe, cli = _fixture()
    with _windows(cli), patch.object(E.subprocess, "run", return_value=SimpleNamespace(returncode=3)):
        afirmar(E.buscar_executaveis([pasta]) is None)
    with _windows(cli), patch.object(E.subprocess, "run", side_effect=OSError("sem cli")):
        afirmar(E.buscar_executaveis([pasta]) is None)
    with _windows(cli), patch.object(E.subprocess, "run", side_effect=subprocess.TimeoutExpired("es", 30)):
        afirmar(E.buscar_executaveis([pasta]) is None)

    def sem_arquivo(comando, **kwargs):
        return SimpleNamespace(returncode=0)
    with _windows(cli), patch.object(E.subprocess, "run", side_effect=sem_arquivo):
        afirmar(E.buscar_executaveis([pasta]) is None, "export ausente deve dar fallback")

    def vazio(comando, **kwargs):
        _exportado(comando).write_text("", encoding="utf-8-sig")
        return SimpleNamespace(returncode=0)
    with _windows(cli), patch.object(E.subprocess, "run", side_effect=vazio):
        afirmar(E.buscar_executaveis([pasta]) is None, "índice vazio não oculta o scanner")

    def acima_do_limite(comando, **kwargs):
        _exportado(comando).write_text("\n".join([str(exe)] * 4), encoding="utf-8-sig")
        return SimpleNamespace(returncode=0)
    with _windows(cli), patch.object(E.subprocess, "run", side_effect=acima_do_limite):
        afirmar(E.buscar_executaveis([pasta], limite=2) is None, "lista além do limite deve dar fallback")


def teste_assistente2_everything_sem_cli_sem_windows_e_sem_raiz_nao_executa():
    _, pasta, _, cli = _fixture()
    with _windows(cli), patch.object(E.subprocess, "run") as run:
        afirmar(E.buscar_executaveis([]) == [])
        run.assert_not_called()
    with patch.object(E, "os", SimpleNamespace(name="posix", environ={})), \
            patch.object(E.subprocess, "run") as run:
        afirmar(E.buscar_executaveis([pasta]) is None)
        run.assert_not_called()
    with _windows(pasta / "ausente-cli.exe"), patch.object(E.subprocess, "run") as run:
        afirmar(E.buscar_executaveis([pasta]) is None, "cli ausente deve dar fallback")
        run.assert_not_called()
