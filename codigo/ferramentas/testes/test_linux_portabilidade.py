"""Linux simulado sem trocar os.name global nem executar jogos/áudio/rede.

Também roda em Linux real na CI. Fixtures nativas recebem chmod; sinais,
PATH, Wine e filhos são injetados. A sandbox continua protegendo a coleção.
"""
import io
import os
import sqlite3
import subprocess
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import bib_core as core
from bib_nucleo import baixar, base, emuladores, player, processos
from bib_nucleo import editores_imagem as EI
from bib_nucleo import equalizadores as EQ
from bib_nucleo import ferramentas as F
from bib_nucleo import reprodutores_video as RV
from bib_nucleo import videos as VI
from bib_nucleo import videos_youtube as YT
from executar import afirmar


def _nativo(raiz, nome="motor"):
    p = Path(raiz) / nome
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"#!/bin/sh\nexit 0\n")
    p.chmod(0o755)
    return p


def _os_linux():
    # Proxy local: pathlib e o audit hook continuam enxergando o SO hospedeiro.
    return SimpleNamespace(**{**vars(os), "name": "posix"})


def teste_linux_ferramentas_rejeita_exe_sem_x_e_aceita_zipapp():
    tmp = Path(tempfile.mkdtemp())
    exe = _nativo(tmp, "ffmpeg.exe")
    nativo = _nativo(tmp, "ffmpeg")
    pyz = tmp / "yt-dlp.pyz"
    pyz.write_bytes(b"zipapp-fake")
    with patch.object(F.sys, "platform", "linux"), patch.object(F.os, "access", return_value=False):
        for p in (exe, nativo):
            with patch.dict(os.environ, {"BIBLIOTECA_FFMPEG": str(p)}):
                afirmar(F.localizar_ferramenta("ffmpeg") == "", p)
        with patch.dict(os.environ, {"BIBLIOTECA_YTDLP": str(pyz)}):
            afirmar(F.localizar_ferramenta("ytdlp") == str(pyz))
    with patch.object(F.sys, "platform", "linux"), patch.object(F.os, "access", return_value=True), \
            patch.dict(os.environ, {"BIBLIOTECA_FFMPEG": str(nativo)}):
        afirmar(F.localizar_ferramenta("ffmpeg") == str(nativo))


def teste_linux_exclusivos_windows_nao_aparecem_nativos():
    tmp = Path(tempfile.mkdtemp())
    exe = _nativo(tmp, "windows.exe")
    env = {F.FERRAMENTAS[n][0]: str(exe) for n in ("photodemon", "equalizerapo", "peace", "mpchc")}
    with patch.object(F.sys, "platform", "linux"), patch.dict(os.environ, env), \
            patch.object(F.shutil, "which", side_effect=AssertionError("consultou PATH para programa Win")):
        for nome in ("photodemon", "equalizerapo", "peace", "mpchc"):
            afirmar(not F.ferramenta_suportada(nome) and not F.localizar_ferramenta(nome), nome)
        afirmar(RV.localizar_reprodutor("mpchc") == "")
        afirmar("VLC" in RV.erro_sem_reprodutor("mpchc"))
        afirmar("Windows" in EQ.erro_sem_equalizador("peace"))
        afirmar("GIMP" in EI.erro_sem_editor("photodemon"))


def teste_linux_portatil_midias_nao_escapa_para_path():
    tmp = Path(tempfile.mkdtemp())
    (tmp / F.MANIFESTO_RUNTIME).write_text('{"componentes": {}}', encoding="utf-8")
    exe = _nativo(tmp / "ferramentas", "krita/krita")
    with patch.object(base, "HOME_DIR", tmp), patch.object(F.sys, "platform", "linux"), \
            patch.object(F.os, "access", return_value=True), \
            patch.object(F.shutil, "which", side_effect=AssertionError("pacote consultou PATH")):
        afirmar(EI.localizar_editor("krita") == str(exe))
        afirmar(EI.localizar_editor("gimp") == "")
        afirmar(RV.localizar_reprodutor("vlc") == "")
        afirmar(EQ.localizar_equalizador("audacity") == "")


def teste_linux_path_tenacity_e_mpv_com_identidade_correta():
    tmp = Path(tempfile.mkdtemp())
    tenacity, mpv = _nativo(tmp, "tenacity"), _nativo(tmp, "mpv")
    nomes = []
    def which(nome):
        nomes.append(nome)
        return {"tenacity": str(tenacity), "mpv": str(mpv)}.get(nome)
    with patch.object(F.sys, "platform", "linux"), patch.object(F.os, "access", return_value=True), \
            patch.object(F.shutil, "which", side_effect=which):
        afirmar(EQ.localizar_equalizador("audacity") == str(tenacity))
        afirmar(RV.localizar_reprodutor("mpv") == str(mpv))
        afirmar(RV.localizar_reprodutor("mpchc") == "")
    afirmar(not any(n.endswith(".exe") for n in nomes), nomes)


def teste_windows_descoberta_bounded_gimp3_sem_rglob():
    tmp = Path(tempfile.mkdtemp())
    exe = _nativo(tmp, "GIMP 3/bin/gimp-3.0.exe")
    with patch.object(F, "_plataforma_atual", return_value="win32"), \
            patch.dict(os.environ, {"ProgramFiles": str(tmp), "ProgramFiles(x86)": ""}), \
            patch.object(F.shutil, "which", return_value=None), \
            patch.object(Path, "rglob", side_effect=AssertionError("busca recursiva de programa")):
        afirmar(EI.localizar_editor("gimp") == str(exe))


def teste_linux_azahar_appimage_caixa_mista():
    tmp = Path(tempfile.mkdtemp())
    exe = _nativo(tmp, "Azahar-Atual.APPIMAGE")
    with patch.object(emuladores, "os", _os_linux()), \
            patch.object(emuladores, "eh_mac", return_value=False), \
            patch.object(emuladores, "azahar_dir_override", return_value=tmp):
        afirmar(emuladores.default_emu_3ds() == str(exe))


def teste_linux_desmume_usr_games_fora_path():
    with patch.object(emuladores, "os", _os_linux()), \
            patch.object(emuladores, "eh_mac", return_value=False), \
            patch.object(emuladores, "desmume_dir_override", return_value=None), \
            patch.object(emuladores, "_appimage_na_pasta", return_value=""), \
            patch.object(emuladores.shutil, "which", return_value=None), \
            patch.object(Path, "is_file", lambda p: p.as_posix() == "/usr/games/desmume-cli"):
        afirmar(emuladores.default_emu_nds() == "/usr/games/desmume-cli")


def teste_linux_desmume_flags_padrao_e_override():
    os.environ.pop("BIBLIOTECA_DESMUME_FLAGS", None)
    with patch.object(emuladores, "os", _os_linux()), patch.object(emuladores, "eh_mac", return_value=False):
        afirmar(emuladores.desmume_flags() == [])
        with patch.dict(os.environ, {"BIBLIOTECA_DESMUME_FLAGS": '--fwlang=1 --cflash="disco com espaço.img"'}):
            afirmar(emuladores.desmume_flags() == ["--fwlang=1", "--cflash=disco com espaço.img"])


def teste_linux_wine_prefixo_e_argumentos_sem_shell():
    exe = _nativo(tempfile.mkdtemp(), "jogo.exe")
    proxy = _os_linux()
    with patch.object(emuladores, "os", proxy), patch.object(emuladores, "eh_mac", return_value=False), \
            patch.object(emuladores, "traduzir_para_atual", side_effect=lambda p: p), \
            patch.object(emuladores.shutil, "which", side_effect=lambda n: "/usr/bin/wine" if n == "wine" else None), \
            patch.object(emuladores, "_tem_nvidia", return_value="RTX simulada"), \
            patch.object(emuladores.subprocess, "Popen") as pop:
        r, proc = emuladores._lancar(str(exe), launch_options='"argumento com espaço" --teste')
        afirmar(r["ok"] and r["modo"] == "wine-linux" and proc is pop.return_value, r)
        cmd = pop.call_args.args[0]
        kw = pop.call_args.kwargs
        afirmar(cmd == ["/usr/bin/wine", str(exe), "argumento com espaço", "--teste"], cmd)
        afirmar(kw["env"]["WINEPREFIX"] == str(base.WINE_PREFIXO))
        afirmar(kw["env"]["DXVK_FILTER_DEVICE_NAME"] == "RTX simulada")
        afirmar(kw["start_new_session"] and not kw.get("shell", False))


def teste_linux_lancamento_sem_wine_e_sem_permissao():
    tmp = Path(tempfile.mkdtemp())
    win = _nativo(tmp, "jogo.exe")
    native = _nativo(tmp, "azahar.AppImage")
    proxy = _os_linux()
    proxy.access = lambda *_a: False
    with patch.object(emuladores, "os", proxy), patch.object(emuladores, "eh_mac", return_value=False), \
            patch.object(emuladores, "traduzir_para_atual", side_effect=lambda p: p), \
            patch.object(emuladores.shutil, "which", return_value=None), \
            patch.object(emuladores.subprocess, "Popen", side_effect=AssertionError("tentou executar")):
        r, _ = emuladores._lancar(str(win))
        afirmar(not r["ok"] and "Wine" in r["erro"], r)
        r, _ = emuladores._lancar(str(native))
        afirmar(not r["ok"] and "chmod" in r["erro"], r)


class _Proc:
    def __init__(self, stdout=(), rc=0):
        self.stdout = stdout
        self.rc = rc
        self.eventos = []
    def poll(self): return None
    def send_signal(self, sig): self.eventos.append(("sinal", sig))
    def terminate(self): self.eventos.append("terminate")
    def kill(self): self.eventos.append("kill")
    def wait(self, timeout=None):
        self.eventos.append("wait")
        return self.rc


def teste_linux_player_pause_idempotente_e_posicao():
    arq = _nativo(tempfile.mkdtemp(), "áudio com espaço.wav")
    proc = _Proc()
    sinais = SimpleNamespace(SIGSTOP=19, SIGCONT=18)
    b = player._ProcessoBackend()
    with patch.object(b, "_bin", return_value="fake-player"), \
            patch.object(player.subprocess, "Popen", return_value=proc), \
            patch.object(player, "_signal", sinais), \
            patch.object(player.time, "monotonic", side_effect=[10, 12, 22, 30]):
        afirmar(b.open(str(arq))["ok"] and b.play()["ok"])
        afirmar(proc.eventos == [], "play inicial enviou sinal de retomada")
        afirmar(b.pause()["ok"] and b.pause()["ok"])
        afirmar(b.pos_ms() == 2000)
        afirmar(b.resume()["ok"] and b.pos_ms() == 10000)
    afirmar(proc.eventos == [("sinal", 19), ("sinal", 18)], proc.eventos)


def teste_linux_player_parado_retoma_antes_terminate_e_recolhe_kill():
    proc = _Proc()
    b = player._ProcessoBackend()
    b.proc, b._pausado_em, b._aberto = proc, 12, "musica.wav"
    original_wait = proc.wait
    def wait(timeout=None):
        if "kill" not in proc.eventos:
            proc.eventos.append("wait")
            raise subprocess.TimeoutExpired("player", timeout)
        return original_wait(timeout)
    proc.wait = wait
    with patch.object(player, "_signal", SimpleNamespace(SIGCONT=18)):
        b.stop()
    afirmar(proc.eventos == [("sinal", 18), "terminate", "wait", "kill", "wait"], proc.eventos)
    afirmar(b.proc is None and b.pos_ms() is None)
    b.stop()  # idempotente após encerrar


def teste_processos_fundo_windows_sem_console_linux_mantem_grupo():
    for plataforma in ("nt", "posix"):
        proc = _Proc(io.StringIO("[download] 42%\n"))
        linhas = []
        proxy = SimpleNamespace(**{**vars(os), "name": plataforma})
        with patch.object(processos, "os", proxy), \
                patch.object(processos.subprocess, "Popen", return_value=proc) as pop:
            esperado = (getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                        if plataforma == "nt" else 0)
            afirmar(processos.opcoes_sem_janela().get("creationflags", 0) == esperado)
            afirmar(processos.executar_com_progresso(["fake"], linhas.append, timeout=5) == 0)
            afirmar(pop.call_args.kwargs.get("creationflags", 0) == esperado, pop.call_args)
            afirmar(pop.call_args.kwargs["start_new_session"] == (plataforma == "posix"))
        afirmar(linhas == ["[download] 42%\n"] and proc.stdout.closed, linhas)


def teste_emuladores_sondagem_e_extracao_usam_opcoes_de_fundo():
    with patch.object(processos, "opcoes_sem_janela", return_value={"creationflags": 123}), \
            patch.object(emuladores, "_bin_7z", return_value="fake7z"), \
            patch.object(emuladores.shutil, "which", return_value="nvidia-smi"), \
            patch.object(emuladores.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout="GPU fake\n", stderr="")) as executar:
        afirmar(emuladores._tem_nvidia() == "GPU fake")
        afirmar(executar.call_args.kwargs["creationflags"] == 123)
        emuladores._extrair_arquivo("fake.7z", Path(tempfile.mkdtemp()))
        afirmar(executar.call_args.kwargs["creationflags"] == 123)
        afirmar(executar.call_args.kwargs["timeout"] == 600)


def teste_processo_mudo_timeout_encerra_recolhe_e_fecha_pipe():
    liberado = threading.Event()
    class Pipe:
        fechado = False
        def __iter__(self):
            liberado.wait(2)
            return iter(())
        def close(self): self.fechado = True
    pipe = Pipe()
    proc = _Proc(pipe)
    def terminate():
        proc.eventos.append("terminate")
        liberado.set()
    proc.terminate = terminate
    with patch.object(processos.subprocess, "Popen", return_value=proc):
        try:
            processos.executar_com_progresso(["fake"], timeout=0.02)
        except subprocess.TimeoutExpired:
            pass
        else:
            raise AssertionError("leitura de stdout mudo não expirou")
    afirmar(proc.eventos == ["terminate", "wait"] and pipe.fechado, proc.eventos)


def teste_processo_log_pesado_e_callback_falhando():
    saida = io.StringIO("[download] 10%\n" * 20000)
    proc = _Proc(saida)
    chamadas = []
    def callback(linha):
        chamadas.append(linha)
        if len(chamadas) % 13 == 0:
            raise ValueError("UI indisponível")
    with patch.object(processos.subprocess, "Popen", return_value=proc):
        afirmar(processos.executar_com_progresso(["fake"], callback, timeout=10) == 0)
    afirmar(len(chamadas) == 20000 and saida.closed)


def teste_processo_timeout_forca_kill_e_wait_final():
    proc = _Proc(io.StringIO(""))
    def wait(timeout=None):
        proc.eventos.append("wait")
        if "kill" not in proc.eventos:
            raise subprocess.TimeoutExpired("travado", timeout)
        return 0
    proc.wait = wait
    with patch.object(processos.subprocess, "Popen", return_value=proc):
        try:
            processos.executar_com_progresso(["fake"], timeout=0.1)
        except subprocess.TimeoutExpired:
            pass
        else:
            raise AssertionError("filho travado retornou sucesso")
    afirmar(proc.eventos == ["wait", "terminate", "wait", "kill", "wait"], proc.eventos)
    afirmar(proc.stdout.closed)


def teste_linux_processo_timeout_recolhe_grupo_ffmpeg():
    proc = _Proc(io.StringIO(""))
    proc.pid = 12345
    primeiro = True
    def wait(timeout=None):
        nonlocal primeiro
        if primeiro:
            primeiro = False
            raise subprocess.TimeoutExpired("yt-dlp", timeout)
        return 0
    proc.wait = wait
    proxy = _os_linux()
    grupos = []
    proxy.killpg = lambda pid, sig: grupos.append((pid, sig))
    with patch.object(processos, "os", proxy), \
            patch.object(processos, "signal", SimpleNamespace(SIGTERM=15, SIGKILL=9)), \
            patch.object(processos.subprocess, "Popen", return_value=proc) as pop:
        try:
            processos.executar_com_progresso(["fake"], timeout=0.1)
        except subprocess.TimeoutExpired:
            pass
        else:
            raise AssertionError("grupo travado não expirou")
    afirmar(pop.call_args.kwargs["start_new_session"])
    afirmar(grupos == [(12345, 15), (12345, 9)], grupos)


def teste_linux_traducao_exe_windows_e_prioridade_linux():
    tmp = Path(tempfile.mkdtemp())
    lin = tmp / "linux"
    win_exe = _nativo(lin, "Games/Jogo/jogo.exe")
    linux_exe = _nativo(lin, "Games/Jogo/nativo")
    proxy = _os_linux()
    with patch.object(base, "os", proxy), patch.object(base, "eh_mac", return_value=False), \
            patch.object(base, "WIN_ROOT", "D:\\"), patch.object(base, "LINUX_ROOT", str(lin)):
        salvo = "D:\\Games\\Jogo\\jogo.exe"
        exe, origem = base.resolver_exe({"exe_win": salvo})
        afirmar(Path(exe) == win_exe and origem == "exe_win", (exe, origem))
        exe, origem = base.resolver_exe({"exe_win": salvo, "exe_linux": str(linux_exe)})
        afirmar(Path(exe) == linux_exe and origem == "exe_linux", (exe, origem))


def teste_tui_selftest_sem_curses_libera_lock():
    import contextlib

    import app_tui as tui
    db = Path(tempfile.mkdtemp()) / "tui.db"
    con = core.get_db(db)
    core.criar_jogo(con, {"titulo": "Jogo de teste"})
    con.close()
    saida = io.StringIO()
    with patch.object(tui, "curses", None), contextlib.redirect_stdout(saida):
        afirmar(tui.main(["--selftest", "--db", str(db)]) == 0)
    afirmar("1 jogo(s)" in saida.getvalue() and not core.lock_path().exists())


def teste_tui_menu_vazio_e_terminal_fechado_nao_gira():
    import app_tui as tui
    app = object.__new__(tui.Tui)
    afirmar(app.escolher("Vazio", []) is None)
    class Scr:
        def getmaxyx(self): return 24, 80
        def addnstr(self, *_a): pass
        def refresh(self): pass
        def getch(self): raise OSError("terminal fechado")
    app.stdscr, app.cor, app.abold = Scr(), {"mut": 0, "head": 0, "acc": 0, "txt": 0}, 0
    afirmar(app.escolher("Teste", ["Uma"]) is None)


def teste_download_audio_timeout_preserva_arquivo_e_marca_falha():
    con = core.get_db(Path(tempfile.mkdtemp()) / "audio.db")
    try:
        core.enfileirar_downloads(con, [{"titulo": "Áudio"}])
        did = core.listar_downloads(con)[0]["id"]
        arq = _nativo(base.BAIXAR_DIR, "concluido.m4a")
        with patch.object(baixar, "casar_video", return_value={"video_id": "abc123", "video_titulo": "Áudio"}), \
                patch.object(processos, "executar_com_progresso", side_effect=subprocess.TimeoutExpired("yt-dlp", 1800)):
            r = baixar.baixar_faixa(con, did, ytdlp="fake")
        afirmar(not r["ok"] and arq.is_file(), r)
        afirmar(core.listar_downloads(con)[0]["estado"] == "falha")
    finally:
        con.close()


def _meta():
    return {"titulo": "Clipe", "canal": "Canal", "duracao_s": 12, "thumb": ""}


def teste_youtube_falha_recolhe_fragmentos_e_preserva_arquivo_anterior():
    vid = "dQw4w9WgXcQ"
    con = core.get_db(Path(tempfile.mkdtemp()) / "video.db")
    antigo = _nativo(base.VIDEOS_DIR, vid + ".mp4")
    antes = antigo.read_bytes()
    def pop(cmd, **kw):
        saida = Path(cmd[cmd.index("-o") + 1])
        saida.write_bytes(b"parcial")
        saida.with_suffix(".mp4.part").write_bytes(b"fragmento")
        return _Proc(["ERROR: rede interrompida\n"], rc=1)
    try:
        with patch.object(YT, "_ytdlp", return_value="fake"), patch.object(YT, "info_video_youtube", return_value=_meta()), \
                patch.object(processos.subprocess, "Popen", side_effect=pop):
            r = YT.baixar_video_youtube(con, vid)
        afirmar(not r["ok"] and "rede interrompida" in r["erro"], r)
        afirmar(antigo.read_bytes() == antes and list(base.VIDEOS_DIR.iterdir()) == [antigo])
        afirmar(core.listar_videos(con) == [])
    finally:
        con.close()


def teste_youtube_falha_de_banco_recolhe_video_publicado():
    con = core.get_db(Path(tempfile.mkdtemp()) / "video.db")
    def pop(cmd, **kw):
        Path(cmd[cmd.index("-o") + 1]).write_bytes(b"mp4-completo")
        return _Proc()
    try:
        with patch.object(YT, "_ytdlp", return_value="fake"), patch.object(YT, "info_video_youtube", return_value=_meta()), \
                patch.object(processos.subprocess, "Popen", side_effect=pop), \
                patch.object(core.banco, "criar_video", side_effect=sqlite3.OperationalError("disco cheio")):
            r = YT.baixar_video_youtube(con, "dQw4w9WgXcQ")
        afirmar(not r["ok"] and "disco cheio" in r["erro"], r)
        afirmar(not list(base.VIDEOS_DIR.iterdir()))
    finally:
        con.close()


def teste_video_origem_mudou_na_copia_nao_publica():
    tmp = Path(tempfile.mkdtemp())
    src = _nativo(tmp / "origem", "filme.mp4")
    con = core.get_db(tmp / "v.db")
    def copiar(orig, dest): Path(dest).write_bytes(b"arquivo mudou")
    try:
        with patch.object(VI.shutil, "copy2", side_effect=copiar):
            r = VI.importar_videos(con, src.parent)
        afirmar(r["novos"] == 0 and r["ignorados"] == 1 and r["erros"], r)
        afirmar(core.listar_videos(con) == [] and not list(base.VIDEOS_DIR.iterdir()))
    finally:
        con.close()


def teste_eq_permissao_destino_vira_erro_e_preserva_original():
    src = _nativo(tempfile.mkdtemp(), "faixa.mp3")
    antes = src.read_bytes()
    with patch.object(EQ, "_destino_eq", side_effect=PermissionError("sem escrita")):
        r = EQ.aplicar_eq(str(src), ffmpeg="fake")
    afirmar(not r["ok"] and "sem escrita" in r["erro"] and src.read_bytes() == antes, r)


def teste_eq_paineis_windows_nao_recebem_mp3_como_configuracao():
    with patch.object(EQ, "localizar_equalizador", return_value="painel.exe"), \
            patch.object(EQ.subprocess, "Popen") as pop:
        for nome in ("peace", "equalizerapo"):
            afirmar(EQ.abrir_no_editor_audio(nome, "faixa.mp3")["ok"])
            afirmar(pop.call_args.args[0] == ["painel.exe"], pop.call_args)


def teste_carga_videos_mil_arquivos_dedup_e_reimportacao():
    tmp = Path(tempfile.mkdtemp())
    origem = tmp / "origem"
    origem.mkdir()
    for i in range(1000):
        (origem / f"Vídeo São João {i}.MKV").write_bytes((i % 128).to_bytes(2, "little") * 512)
    con = core.get_db(tmp / "carga.db")
    try:
        r = VI.importar_videos(con, origem)
        afirmar(r["novos"] == 128 and r["ignorados"] == 872 and not r["erros"], r)
        r2 = VI.importar_videos(con, origem)
        afirmar(r2["novos"] == 0 and r2["ignorados"] == 1000 and not r2["erros"], r2)
        lista = core.listar_videos(con)
        afirmar(len(lista) == len(list(base.VIDEOS_DIR.iterdir())) == 128)
        afirmar(all(VI.sha_arquivo_video(Path(v["video_path"])) == v["video_sha"] for v in lista))
        afirmar(con.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
    finally:
        con.close()
