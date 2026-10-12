"""Contrato do ES atual, Unicode, instâncias e recusa de resultados fora das raízes."""
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
    raiz = Path(tempfile.mkdtemp(prefix="es-contrato-"))
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
    return Path(match[1] or match[2])


def teste_everything_exporta_unicode_e_restringe_a_raiz():
    raiz, pasta, exe, cli = _fixture()
    fora = raiz / "outro.exe"
    fora.write_bytes(b"fixture")
    nao_exe = pasta / "nota.txt"
    nao_exe.write_text("fixture", encoding="utf-8")
    chamadas = []

    def executar(comando, **kwargs):
        chamadas.append(comando)
        afirmar("-utf8 " not in comando and "-full-path " not in comando)
        afirmar("-utf8-bom" in comando and "-full-path-and-name" in comando)
        afirmar(comando.split(" -search* ", 1)[1].startswith("ext:exe <"), comando)
        afirmar("-instance TucoTeca-Prova" in comando)
        afirmar(kwargs.get("shell") is False, "consulta não pode passar por shell")
        arquivo = _exportado(comando)
        arquivo.write_text("\n".join(map(str, (exe, exe, fora, nao_exe, pasta / "ausente.exe"))),
                           encoding="utf-8-sig")
        return SimpleNamespace(returncode=0)

    with _windows(cli, "TucoTeca-Prova"), patch.object(E.subprocess, "run", side_effect=executar):
        afirmar(E.buscar_executaveis([pasta]) == [str(exe.resolve())])
    afirmar(len(chamadas) == 1)
    afirmar(not _exportado(chamadas[0]).exists(),
            "exportação temporária não foi limpa")


def teste_everything_fallback_quando_cli_falha_vazio_ou_timeout():
    _, pasta, _, cli = _fixture()
    with _windows(cli), patch.object(E.subprocess, "run", return_value=SimpleNamespace(returncode=6)):
        afirmar(E.buscar_executaveis([pasta]) is None)
    with _windows(cli), patch.object(E.subprocess, "run", side_effect=subprocess.TimeoutExpired("es", 30)):
        afirmar(E.buscar_executaveis([pasta]) is None)

    def vazio(comando, **kwargs):
        _exportado(comando).write_text("", encoding="utf-8-sig")
        return SimpleNamespace(returncode=0)
    with _windows(cli), patch.object(E.subprocess, "run", side_effect=vazio):
        afirmar(E.buscar_executaveis([pasta]) is None, "índice vazio não deve ocultar o scanner")


def teste_everything_descobre_cliente_local_sem_alterar_o_path():
    raiz = Path(tempfile.mkdtemp(prefix="es-local-"))
    local = raiz / "programa/ferramentas/everything/cli/es.exe"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"fixture")
    with patch.object(E, "HOME_DIR", raiz), patch.object(E, "BASE_DIR", raiz), \
            patch.object(E.shutil, "which", return_value=None), \
            patch.object(E, "os", SimpleNamespace(environ={})):
        afirmar(E._cliente() == (str(local), "TucoTeca"))


def teste_everything_sem_raizes_ou_fora_do_windows_nao_executa_cli():
    _, _, _, cli = _fixture()
    with _windows(cli), patch.object(E.subprocess, "run") as run:
        afirmar(E.buscar_executaveis([]) == [])
        run.assert_not_called()
    with patch.object(E, "os", SimpleNamespace(name="posix", environ={})), \
            patch.object(E.subprocess, "run") as run:
        afirmar(E.buscar_executaveis([]) is None)
        run.assert_not_called()
