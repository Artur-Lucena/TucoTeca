"""Portabilidade de sidecars, zipapps e API local (sem processos/rede reais)."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import bib_core as core
from bib_nucleo import base, ferramentas as F, qbit as Q
from executar import afirmar


def _pacote():
    p = Path(tempfile.mkdtemp(prefix="runtime-"))
    (p / "manifesto-runtime.json").write_text(json.dumps({"componentes": {}}), encoding="utf-8")
    return p


def teste_runtime_local_sem_dependencia_do_pc():
    p = _pacote()
    ff = p / "ferramentas/ffmpeg" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    ff.parent.mkdir(parents=True)
    ff.write_bytes(b"MZ")
    ff.chmod(0o755)
    with patch.object(base, "HOME_DIR", p), patch.object(F.shutil, "which", return_value="C:/sistema/ffmpeg.exe") as procura:
        afirmar(F.localizar_ferramenta("ffmpeg") == str(ff))
        afirmar(not F.localizar_ferramenta("ytdlp"), "pacote usou ferramenta do PC")
        afirmar(not procura.called)
        afirmar(F.emulador_local_dir("Azahar") == p / "emuladores/Azahar")
        from bib_nucleo import repacks
        afirmar(repacks.pasta_jogos() == p / "Meus Jogos Locais")


def teste_runtime_manifesto_e_override_editaveis():
    p = _pacote()
    custom = p / "meus-binarios" / ("motor.exe" if os.name == "nt" else "motor")
    custom.parent.mkdir()
    custom.write_bytes(b"bin")
    custom.chmod(0o755)
    (p / "manifesto-runtime.json").write_text(json.dumps({
        "componentes": {"ffmpeg": {"executavel": custom.relative_to(p).as_posix()}}}), encoding="utf-8")
    with patch.object(base, "HOME_DIR", p):
        afirmar(F.localizar_ferramenta("ffmpeg") == str(custom))
        afirmar(F._caminho_local("../fora.exe") is None)
        with patch.dict(os.environ, {"BIBLIOTECA_FFMPEG": str(custom)}):
            afirmar(core.localizar_ffmpeg() == str(custom))
        with patch.dict(os.environ, {"BIBLIOTECA_FFMPEG": str(p / "falta.exe")}):
            afirmar(not core.localizar_ffmpeg(), "override inválido usou outro binário")
    afirmar(F.comando_externo("yt-dlp.pyz")[-1] == "yt-dlp.pyz")
    afirmar(len(F.comando_externo("motor.exe")) == 1)


def teste_runtime_casa_do_bundle_vence_casa_canonica():
    p = _pacote()
    with patch.object(base, "BASE_DIR", p), patch.dict(os.environ, {}, clear=False):
        salvo = os.environ.pop("BIBLIOTECA_HOME", None)
        try:
            afirmar(base.resolve_home() == p)
        finally:
            if salvo is not None:
                os.environ["BIBLIOTECA_HOME"] = salvo


def teste_qbit_perfil_independente_e_comando():
    p = _pacote()
    exe = p / "qbittorrent.exe"
    exe.write_bytes(b"MZ")
    with patch.object(Q, "localizar_ferramenta", return_value=str(exe)), \
            patch.object(base, "HOME_DIR", p), patch.object(base, "DADOS_DIR", p / "dados"), \
            patch.object(Q.subprocess, "Popen") as proc:
        proc.return_value.pid = 123
        r = Q.qbit_iniciar()
        afirmar(r["ok"], r)
        comando = proc.call_args.args[0]
        afirmar(any(x.startswith("--profile=") and str(p) in x for x in comando), comando)
        afirmar("--relative-fastresume" in comando, comando)
        texto = Q.qbit_config_path().read_text(encoding="utf-8")
        afirmar("127.0.0.1" in texto and "LocalHostAuth=false" in texto)
        afirmar("Password_PBKDF2=@ByteArray(" in texto, "GUI sem credencial não habilita a API")
        Q.qbit_config_path().write_text(texto + ";personalizado\n", encoding="utf-8")
        Q.qbit_iniciar()
        afirmar("personalizado" in Q.qbit_config_path().read_text(encoding="utf-8"), "perfil foi sobrescrito")


def teste_qbit_destino_jogos_em_novos_e_perfil_antigo():
    from bib_nucleo import repacks
    jogos = Path(tempfile.mkdtemp(prefix="jogos-"))
    magnet = "magnet:?xt=urn:btih:" + "a" * 40
    with patch.object(Q, "qbit_api_url", return_value=""), \
            patch.dict(os.environ, {"BIBLIOTECA_PIRATAS": str(jogos)}):
        r = Q.qbit_adicionar(magnet)
        afirmar(not r["ok"] and "Iniciar cliente" in r["erro"], r)
        for ruim in ("", "https://example.com/pagina", "C:/jogo.torrent"):
            afirmar(not Q.qbit_adicionar(ruim)["ok"], ruim)
    with patch.object(Q, "qbit_api_url", return_value="http://127.0.0.1:9999"), \
            patch.object(Q, "qbit_request", return_value="") as req, \
            patch.dict(os.environ, {"BIBLIOTECA_PIRATAS": str(jogos)}):
        r = Q.qbit_adicionar(magnet)
        afirmar(r["ok"] and r["destino"] == str(jogos.resolve()), r)
        ep, dados = req.call_args.args
        afirmar(ep == "torrents/add", ep)
        afirmar(dados["urls"] == magnet and dados["category"] == "tucoteca", dados)
        afirmar(Path(dados["savepath"]).resolve() == jogos.resolve(), dados)
    velho = "[BitTorrent]\nSession\\DefaultSavePath=C:/Downloads\nOutro=1\n"
    novo = Q.migrar_save_path(velho, jogos)
    afirmar(f"Session\\DefaultSavePath={jogos.as_posix()}" in novo and "Outro=1" in novo, novo)
    sem_secao = Q.migrar_save_path("[GUI]\nA=1\n", jogos)
    afirmar("[BitTorrent]" in sem_secao and jogos.as_posix() in sem_secao, sem_secao)
    afirmar(Q.migrar_save_path(novo, jogos) == novo, "migração não é idempotente")


def teste_qbit_api_progresso_estado_e_controle():
    raw = json.dumps([{"hash": "a" * 40, "name": "Jogo", "size": 1000,
                       "progress": 0.5, "dlspeed": 120, "eta": 9,
                       "state": "downloading", "content_path": "D:/downloads/Jogo"}])
    with patch.object(Q, "qbit_api_url", return_value="http://127.0.0.1:9999"), \
            patch.object(Q, "qbit_request", return_value=raw):
        r = Q.qbit_listar()
        t = r["torrents"][0]
        afirmar(t["pct"] == 50 and t["velocidade"] == 120 and not t["completo"], r)
        afirmar(t["save_path"] == "D:/downloads/Jogo")
    with patch.object(Q, "qbit_request") as req:
        afirmar(Q.qbit_controlar("a" * 40, "pausar")["ok"])
        afirmar(req.call_args.args == ("torrents/stop", {"hashes": "a" * 40}))
    with patch.dict(os.environ, {"BIBLIOTECA_QBIT_API": "http://example.com:80"}):
        try:
            Q.qbit_api_url()
        except ValueError:
            pass
        else:
            afirmar(False, "API remota aceita no adaptador local")


def teste_banco_cache_preserva_migracao_e_edicao_local():
    from bib_nucleo import banco as B
    db = Path(tempfile.mkdtemp(prefix="db-cache-")) / "b.db"
    with patch.object(B, "_inicializar_db", wraps=B._inicializar_db) as init:
        B.get_db(db).close()
        B.get_db(db).close()
        afirmar(init.call_count == 1, "reinicializou schema idêntico")
        c = B.get_db(db)
        gid = B.criar_jogo(c, {"titulo": "Manual", "executable_path": "game.exe"})["id"]
        c.execute("UPDATE jogos SET uuid='' WHERE id=?", (gid,))
        c.commit()
        c.close()
        c = B.get_db(db)
        afirmar(c.execute("SELECT uuid FROM jogos WHERE id=?", (gid,)).fetchone()[0], "UUID sem backfill")
        c.execute("ALTER TABLE desejos DROP COLUMN manual")
        c.commit()
        c.close()
        c = B.get_db(db)
        afirmar("manual" in {r["name"] for r in c.execute("PRAGMA table_info(desejos)")}, "migração ignorada")
        c.close()


def teste_runtime_build_sem_perfis_e_com_manifesto():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import montar_superhub as MS
    tmp = Path(tempfile.mkdtemp(prefix="build-runtime-"))
    src, dst = tmp / "src", tmp / "pacote"
    (src / "user").mkdir(parents=True)
    (src / "user/save.bin").write_bytes(b"save pessoal")
    (src / "app.exe").write_bytes(b"MZruntime")
    (src / "plugin.pyd").write_bytes(b"extensao")
    (src / "app.pdb").write_bytes(b"debug")
    (src / "config.ini").write_bytes(b"config pessoal")
    MS.copiar_runtime(src, dst, excluir=("user",))
    afirmar(not (dst / "user").exists() and not (dst / "app.pdb").exists())
    afirmar((dst / "plugin.pyd").exists(), "removeu extensão nativa")
    m = MS.criar_manifesto(dst, {}, {"python": "prova"})
    afirmar(m["arquivos"]["app.exe"]["sha256"] == MS.sha_arquivo(dst / "app.exe"))
    afirmar(m["bytes_runtime"] == len(b"MZruntime") + len(b"extensao"))


def teste_runtime_confere_revisao_e_recusa_fontes_obsoletos():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import montar_superhub as MS
    tmp = Path(tempfile.mkdtemp(prefix="fontes-runtime-"))
    repo, runtime = tmp / "repo", tmp / "runtime"
    for origem, _destino in MS.MP.APP_ARQS:
        p = repo / origem
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("# fonte de prova", encoding="utf-8")
    (repo / "codigo/bib_nucleo").mkdir()
    (repo / "codigo/bib_nucleo/__init__.py").write_text("# nucleo", encoding="utf-8")
    (repo / "codigo/frontends/qml/secoes").mkdir(parents=True)
    qml = repo / "codigo/frontends/qml/secoes/Inicio.qml"
    qml.write_text("import QtQuick; Item {}", encoding="utf-8")
    MS.MP.copiar_app(runtime / "app", repo)
    r = MS.validar_fontes_runtime(runtime, repo)
    afirmar(r["arquivos"] == len(MS.MP.APP_ARQS) + 2, r)
    afirmar(len(r["sha256_arvore_app"]) == 64, r)
    (runtime / "app/qml/secoes/Inicio.qml").write_text("# divergente", encoding="utf-8")
    try:
        MS.validar_fontes_runtime(runtime, repo)
    except ValueError as e:
        afirmar("diverge" in str(e), e)
    else:
        afirmar(False, "aceitou código divergente")
    MS.MP.copiar_app(runtime / "app", repo)
    (runtime / "app/obsoleto.py").write_text("# obsoleto", encoding="utf-8")
    try:
        MS.validar_fontes_runtime(runtime, repo)
    except ValueError as e:
        afirmar("obsoleto.py" in str(e), e)
    else:
        afirmar(False, "aceitou fonte antigo no bundle")
