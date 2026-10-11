"""Diálogo de jogo: monta seções escuras e salva de ponta a ponta."""
import tempfile
import threading
import time
from pathlib import Path

import bib_core as core
from executar import afirmar


def _app_oculto(db_nome="d.db"):
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        return None, None
    import app_win
    try:
        root = tk.Tk()
    except tk.TclError:
        return None, None
    root.withdraw()
    tmp = Path(tempfile.mkdtemp(prefix="suite-d-"))
    return root, app_win.App(root, tmp / db_nome)


def _bombear(root, pronto, limite=3):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        root.update()
        if pronto():
            return True
        time.sleep(0.01)
    return False


def _dlg(app, root, jogo=None):
    app._dlg_jogo(jogo)
    root.update()
    dlgs = [w for w in root.winfo_children()
            if w.winfo_class() == "Toplevel"]
    afirmar(dlgs, "diálogo não abriu")
    return dlgs[-1]


def teste_dialogo_catalogos_abrem():
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto("cat.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        app.dlg_catalogo("steamrip")
        app.dlg_catalogo("fitgirl")
        app.dlg_catalogo("inexistente")
        root.update()
        titulos = sorted(w.title() for w in root.winfo_children()
                         if w.winfo_class() == "Toplevel")
        afirmar(titulos == ["Catálogo FitGirl", "Catálogo SteamRip",
                            "Catálogo SteamRip"], titulos)
        for w in root.winfo_children():
            if w.winfo_class() == "Toplevel":
                w.destroy()
        root.update()
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def _listas(dlg):
    out = []

    def walk(w):
        for ch in w.winfo_children():
            if ch.winfo_class() in ("Listbox", "Treeview"):
                out.append(ch)
            walk(ch)
    walk(dlg)
    return out


def teste_dialogo_listas_tem_rolagem():
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    import app_win
    root, app = _app_oculto("d4.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        idx = next(i for i, (rot, _s, _f) in enumerate(app_win.NAV)
                   if rot.startswith("🎵"))
        app._ir_nav(idx)  # aba (o modal antigo virou aba)
        root.update()
        lbs = _listas(app.grade)
        afirmar(lbs, "aba sem tabela?")
        for lb in lbs:
            irmas = [ch for ch in lb.master.winfo_children()
                     if ch.winfo_class() == "TScrollbar"]
            afirmar(irmas, "Listbox sem Scrollbar irmã")
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def teste_dialogo_aba_musicas():
    """Aba 🎵 Músicas: entra, lista embutida na grade, volta sem quebrar."""
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    import app_win
    root, app = _app_oculto("d5.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        idx = next(i for i, (rot, _s, _f) in enumerate(app_win.NAV)
                   if rot.startswith("🎵"))
        app._ir_nav(idx)
        root.update()
        afirmar(app._em_musicas(), app.nav_idx)
        afirmar(app.cards == [], app.cards)
        lbs = _listas(app.grade)
        afirmar(lbs, "aba músicas sem lista embutida")
        afirmar(app.btn_jogar.cget("text") == "▶  TOCAR",
                app.btn_jogar.cget("text"))
        afirmar(str(app.btn_det_editar.cget("state")) == "disabled",
                "Editar devia travar na aba")
        afirmar(str(app.btn_det_novo.cget("state")) == "disabled",
                "Novo jogo devia travar na aba")
        afirmar(str(app.btn_det_excluir.cget("state")) == "normal",
                "Excluir vale p/ música")
        app._ir_nav(0)
        root.update()
        afirmar(not app._em_musicas(), app.nav_idx)
        afirmar(app.btn_jogar.cget("text") == "▶  JOGAR",
                app.btn_jogar.cget("text"))
        afirmar(str(app.btn_det_editar.cget("state")) == "normal",
                "Editar devia voltar nos jogos")
        afirmar(str(app.btn_det_novo.cget("state")) == "normal",
                "Novo jogo devia voltar nos jogos")
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def teste_dialogo_aba_fila():
    """Fila na aba: entra, lista pendentes, limpa, volta ao hub."""
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    import app_win
    root, app = _app_oculto("d6.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        con = app._con()
        try:
            core.enfileirar_downloads(con, [
                {"titulo": "Cotidiano", "artista": "Chico Buarque",
                 "uri": "spotify:track:1"},
                {"titulo": "Flor de Lis", "artista": "Djavan",
                 "uri": "spotify:track:2"}])
        finally:
            con.close()
        idx = next(i for i, (rot, _s, _f) in enumerate(app_win.NAV)
                   if rot.startswith("🎵"))
        app._ir_nav(idx)
        app._ir_fila()
        root.update()
        afirmar(app.mus_modo == "fila", app.mus_modo)
        afirmar(len(app.fila) == 2, app.fila)
        lbs = _listas(app.grade)
        afirmar(lbs and len(lbs[0].get_children()) == 2, lbs)
        afirmar(str(app.btn_jogar.cget("state")) == "disabled",
                app.btn_jogar.cget("state"))
        for b in (app.btn_det_editar, app.btn_det_excluir, app.btn_det_novo):
            afirmar(str(b.cget("state")) == "disabled",
                    "detalhe devia travar na fila")
        app.limpar_fila()  # pendentes ficam (Clear Done); marca e limpa
        root.update()
        afirmar(len(app.fila) == 2, app.fila)
        con = app._con()
        try:
            for d in core.listar_downloads(con):
                core.marcar_download(con, d["id"], "pronta")
        finally:
            con.close()
        app.limpar_fila()
        root.update()
        afirmar(app.fila == [], app.fila)
        app._ir_musicas()
        root.update()
        afirmar(app.mus_modo == "hub", app.mus_modo)
        afirmar(str(app.btn_jogar.cget("state")) == "normal",
                app.btn_jogar.cget("state"))
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def teste_dialogo_transporte_interno():
    """Transporte interno na aba: toca/pausa/próxima sem popup e sem áudio."""
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    import app_win
    root, app = _app_oculto("d7.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        class FB:
            def open(self, p):
                return {"ok": True} if p else {"ok": False, "erro": "x"}
            def play(self):
                return {"ok": True}
            def pause(self):
                return {"ok": True}
            def resume(self):
                return {"ok": True}
            def stop(self):
                pass
            def vivo(self):
                return True
            def pos_ms(self):
                return 1
            def dur_ms(self):
                return 9
            def close(self):
                pass
        app.player = core.Player(FB())
        idx = next(i for i, (rot, _s, _f) in enumerate(app_win.NAV)
                   if rot.startswith("🎵"))
        app._ir_nav(idx)
        root.update()
        app.musicas = [{"id": 1, "titulo": "A", "artista": "X", "album": "",
                        "musica_path": "a.mp3"}]
        app.mus_ids = [1]
        app.mus_sel = 0
        app.tocar_musica_selecionada()  # preparação em thread, áudio na UI
        afirmar(_bombear(root, lambda: app.player.estado == "tocando"
                         and not app._mus_carregando), "play não completou")
        afirmar(app.player.estado == "tocando", app.player.estado)
        afirmar("X" in app.lbl_agora.cget("text"), app.lbl_agora.cget("text"))
        afirmar(app._btn_play.cget("text") == "⏸", app._btn_play.cget("text"))
        app.mus_alternar()
        afirmar(app.player.estado == "pausado", app.player.estado)
        app.mus_alternar()
        afirmar(app.player.estado == "tocando", app.player.estado)
        app.mus_proxima()  # só 1 faixa: para no fim
        afirmar(app.player.estado == "parado", app.player.estado)
        app.mus_parar()
        afirmar(app.player.estado == "parado", app.player.estado)
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def teste_dialogo_mci_mesma_thread_e_fim_real():
    """Simula MCI com aliases por thread: erro 263 não deve pular faixas."""
    from bib_nucleo import player as PL
    root, app = _app_oculto("mci-thread.db")
    if root is None:
        print("(sem display: skip)")
        return
    principal = threading.get_ident()

    class Winmm:
        def __init__(self):
            self.dono = None
            self.modo = "stopped"
            self.pos = 0
            self.dur = 10000
            self.aberturas = 0
            self.chamadas = []
            self.erro_status = False

        def mciSendStringW(self, comando, buf, _n, _h):
            tid = threading.get_ident()
            self.chamadas.append(tid)
            if comando.startswith("open "):
                self.dono = tid
                self.modo, self.pos = "stopped", 0
                self.aberturas += 1
                return 0
            if tid != self.dono or (comando.startswith("status ")
                                    and self.erro_status):
                return 263
            if comando.startswith(("play ", "resume ")):
                self.modo = "playing"
            elif comando.startswith("pause "):
                self.modo = "paused"
            elif comando.startswith("stop "):
                self.modo = "stopped"
            elif comando.startswith("status "):
                buf.value = {"mode": self.modo, "position": str(self.pos),
                             "length": str(self.dur)}[comando.split()[-1]]
            return 0

        def mciGetErrorStringW(self, _rc, buf, _n):
            buf.value = "MCI erro 263"
            return True

    velho_nt = PL._eh_nt
    PL._eh_nt = lambda: True
    erros = []
    root.report_callback_exception = lambda *e: erros.append(e)
    be = PL.MciBackend()
    dll = Winmm()
    be._winmm = dll
    preparo_threads = []
    wav = app.db_path.parent / "audio.wav"
    wav.write_bytes(b"RIFFfake")

    def preparar(_path):
        preparo_threads.append(threading.get_ident())
        return {"ok": True, "alvo": str(wav)}

    be.preparar = preparar
    app.player = core.Player(be)
    try:
        import app_win
        idx = next(i for i, (rot, _s, _f) in enumerate(app_win.NAV)
                   if rot.startswith("🎵"))
        app._ir_nav(idx)
        app.musicas = [{"id": 1, "titulo": "A", "musica_path": "a.mp3"},
                       {"id": 2, "titulo": "B", "musica_path": "b.mp3"}]
        app.mus_sel = 0
        app.tocar_musica_selecionada()
        afirmar(_bombear(root, lambda: app.player.estado == "tocando"))
        afirmar(dll.dono == principal, "MCI abriu fora da thread dos controles")
        afirmar(preparo_threads and all(t != principal for t in preparo_threads),
                "conversão bloqueou a UI")
        afirmar(be.vivo() is True and not app.player.terminou())
        app.mus_alternar()
        afirmar(app.player.estado == "pausado" and dll.modo == "paused")
        app.mus_alternar()
        afirmar(app.player.estado == "tocando" and dll.modo == "playing")
        # Erro persistente de consulta não pode virar avanço automático.
        dll.erro_status = True
        fim = time.monotonic() + 1.1
        afirmar(_bombear(root, lambda: time.monotonic() >= fim, limite=2))
        afirmar(app.player.idx == 0 and dll.aberturas == 1)
        dll.erro_status = False
        dll.modo, dll.pos = "stopped", 0
        afirmar(not app.player.terminou(), "stopped no início não é fim")
        # Mesmo na aba Jogos e sem a lista visível, termina e avança uma vez.
        app._ir_nav(0)
        app.musicas = []
        dll.pos = dll.dur
        afirmar(app.player.terminou())
        afirmar(_bombear(root, lambda: app.player.idx == 1
                         and app.player.estado == "tocando"))
        afirmar(dll.aberturas == 2 and app.player.atual()["titulo"] == "B")
        afirmar(app.nav_idx == 0 and not app.player.terminou())
        afirmar(all(t == principal for t in dll.chamadas), dll.chamadas)
        app.mus_parar()
        afirmar(app.player.estado == "parado" and not be.alias)
    finally:
        root.destroy()
        PL._eh_nt = velho_nt
    afirmar(not erros, erros)


def teste_dialogo_troca_rapida_e_cancelamento():
    """Preparação antiga não abre áudio, para a nova ou ressuscita após Stop."""
    from test_player import FakeBackend
    root, app = _app_oculto("troca-rapida.db")
    if root is None:
        print("(sem display: skip)")
        return
    iniciou = threading.Event()
    liberar = threading.Event()
    concluiu = threading.Event()

    class Lento(FakeBackend):
        def __init__(self):
            super().__init__()
            self.threads = []
            self.preparadas = []

        def preparar(self, path):
            self.threads.append(threading.current_thread())
            self.preparadas.append(path)
            if path == "a.mp3":
                iniciou.set()
                afirmar(liberar.wait(3), "preparação não foi liberada")
                concluiu.set()
            return {"ok": True, "alvo": path}

    be = Lento()
    app.player = core.Player(be)
    erros = []
    root.report_callback_exception = lambda *e: erros.append(e)
    app.musicas = [{"id": i, "titulo": nome, "musica_path": f"{nome}.mp3"}
                   for i, nome in enumerate(("a", "b", "c"))]
    try:
        app._tocar_faixa_async(0)
        token_antigo = app._mus_token
        afirmar(iniciou.wait(2))
        heartbeat = []
        root.after(0, lambda: heartbeat.append(True))
        root.update()
        afirmar(heartbeat, "UI bloqueou enquanto convertia")
        app._tocar_faixa_async(1)
        app._tocar_faixa_async(2)
        liberar.set()
        afirmar(_bombear(root, lambda: app.player.estado == "tocando"
                         and app.player.idx == 2))
        afirmar(be.abertos == ["c.mp3"], be.abertos)
        app._pos_tocar(token_antigo, 0, {"ok": True, "alvo": "a.mp3"}, False, False)
        afirmar(app.player.estado == "tocando" and be.abertos == ["c.mp3"])
        # Parar no meio da conversão deve invalidar o resultado.
        iniciou.clear()
        liberar.clear()
        concluiu.clear()
        app._tocar_faixa_async(0)
        afirmar(iniciou.wait(2))
        app.mus_parar()
        liberar.set()
        afirmar(concluiu.wait(2))
        fim = time.monotonic() + 0.2
        afirmar(_bombear(root, lambda: time.monotonic() >= fim))
        afirmar(app.player.estado == "parado" and be.abertos == ["c.mp3"])
        # Fechar a janela no carregamento também não deixa áudio órfão.
        iniciou.clear()
        liberar.clear()
        app._tocar_faixa_async(0)
        afirmar(iniciou.wait(2))
        root.destroy()
        liberar.set()
        for th in be.threads:
            th.join(2)
        afirmar(app._mus_fechado and be.abertos == ["c.mp3"])
    finally:
        liberar.set()
        for th in be.threads:
            th.join(2)
        if not app._mus_fechado:
            root.destroy()
    afirmar(not erros, erros)


def teste_dialogo_volume_pc_global_e_sincronizado():
    """Volume entre abas, sincronização só-leitura e debounce do slider."""
    from unittest.mock import patch
    estado = {"ok": True, "nivel": 50, "mudo": False}
    escritas = []

    def definir(nivel, mudo=None):
        escritas.append((nivel, mudo))
        estado["nivel"] = nivel
        if mudo is not None:
            estado["mudo"] = mudo
        return dict(estado)

    def ajustar(delta):
        return definir(min(100, max(0, estado["nivel"] + delta)), mudo=False)

    def silenciar():
        return definir(estado["nivel"], mudo=not estado["mudo"])

    with patch.object(core, "volume_pc_disponivel", return_value=True), \
            patch.object(core, "ler_volume_pc", side_effect=lambda: dict(estado)), \
            patch.object(core, "definir_volume_pc", side_effect=definir), \
            patch.object(core, "ajustar_volume_pc", side_effect=ajustar), \
            patch.object(core, "alternar_mudo_pc", side_effect=silenciar):
        root, app = _app_oculto("volume-pc.db")
        if root is None:
            print("(sem display: skip)")
            return
        erros = []
        root.report_callback_exception = lambda *e: erros.append(e)
        try:
            root.update()
            afirmar(app.var_volume_pct.get() == "50%")
            afirmar(app.var_volume_pc.get() == 50)
            afirmar(escritas == [], "montagem da UI não pode ajustar o volume")
            estado.update(nivel=63, mudo=True)  # teclas/mixer externos
            app._volume_mostrar(core.ler_volume_pc())
            root.update()
            afirmar(app.var_volume_pct.get() == "63%")
            afirmar(app.btn_volume_mudo.cget("text") == "Ativar som")
            afirmar(app.btn_volume_mudo.master.winfo_reqwidth() <= 180,
                    "controles de volume devem caber na barra lateral")
            afirmar(escritas == [], "sincronizar não pode sobrescrever o PC")
            app.btn_volume_mais.invoke()
            afirmar(estado["nivel"] == 68 and not estado["mudo"])
            app.btn_volume_menos.invoke()
            afirmar(estado["nivel"] == 63)
            app.btn_volume_mudo.invoke()
            afirmar(estado["mudo"] and app.btn_volume_mudo.cget("text") == "Ativar som")
            app.btn_volume_mudo.invoke()
            afirmar(not estado["mudo"])
            escritas.clear()
            app.escala_volume_pc.set(20)
            app.escala_volume_pc.set(35)
            app.escala_volume_pc.set(42)
            afirmar(_bombear(root, lambda: bool(escritas) and app._vol_pendente is None))
            afirmar(escritas == [(42, False)], escritas)
            afirmar(app.var_volume_pct.get() == "42%")
            import app_win
            escala = app.escala_volume_pc
            idx = next(i for i, (rot, _s, _f) in enumerate(app_win.NAV)
                       if rot.startswith("🎵"))
            app._ir_nav(idx)
            app._ir_nav(0)
            afirmar(app.escala_volume_pc is escala and escala.winfo_manager() == "pack")
            app._volume_mostrar({"ok": False, "erro": "sem dispositivo"})
            afirmar(str(app.btn_volume_mais.cget("state")) == "disabled")
            app._volume_mostrar(core.ler_volume_pc())
            afirmar(str(app.btn_volume_mais.cget("state")) == "normal")
            app.escala_volume_pc.set(15)
            antes = len(escritas)
            root.destroy()
            afirmar(app._vol_fechado and app._vol_pendente is None)
            afirmar(len(escritas) == antes, "fechar deve cancelar ajuste pendente")
        finally:
            if not app._vol_fechado:
                root.destroy()
        afirmar(not erros, erros)


def _combos(dlg):
    out = []

    def walk(w):
        for ch in w.winfo_children():
            if ch.winfo_class() == "TCombobox":
                out.append(ch)
            walk(ch)
    walk(dlg)
    return out


def teste_importar_baixadas_contrato_e_callback():
    from unittest.mock import patch

    import app_win
    root, app = _app_oculto("fila-contrato.db")
    if root is None:
        print("(sem display: skip)")
        return
    vistos = []
    try:
        con = app._con()
        core.enfileirar_downloads(con, [{"titulo": "T", "uri": "u"}])
        did = core.listar_downloads(con)[0]["id"]
        core.marcar_download(con, did, "baixado")
        con.close()
        with patch.object(core, "importar_fila_pronta", return_value={
                "novas": 1, "ignoradas": 0, "erros": [], "avisos": [], "capas": 0}), \
                patch.object(app_win.messagebox, "showinfo", side_effect=lambda *_a, **_k: vistos.append(_a)):
            app.importar_baixadas()
            afirmar(_bombear(root, lambda: bool(vistos), limite=5), "callback de conclusão não chegou")
        afirmar("1 nova(s), 0 ignorada(s)" in vistos[0][1], vistos)
    finally:
        root.destroy()


def teste_json_gui_nao_objeto_nao_trava():
    from unittest.mock import patch

    import app_win
    root, app = _app_oculto("json-invalido.db")
    if root is None:
        print("(sem display: skip)")
        return
    erros = []
    arq = app.db_path.parent / "entrada.json"
    try:
        with patch.object(app_win.messagebox, "showerror", side_effect=lambda *_a: erros.append(_a)):
            for valor in ('42', '"texto"', 'null', '{"jogos": 1}'):
                arq.write_text(valor)
                app.importar_json(str(arq))
        afirmar(len(erros) == 4, erros)
    finally:
        root.destroy()


def teste_dialogo_emulador_autodetect():
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto("d3.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        jogo = {"titulo": "Z", "executable_path": "", "exe_win": "", "exe_linux": "",
                "status": "backlog", "nota": None, "horas": 0, "favorito": False,
                "launch_options": "D:\\roms\\jogo.nds", "origem": "rom-nds",
                "azahar_preset": "", "observacoes": "", "capa": ""}
        dlg = _dlg(app, root, jogo)
        combos = _combos(dlg)
        textos = [c.get() for c in combos]
        afirmar(any("DeSmuME" in t for t in textos), textos)
        dlg.destroy()
        jogo3 = dict(jogo, origem="rom-3ds", launch_options="D:\\roms\\jogo.3ds")
        dlg = _dlg(app, root, jogo3)
        textos = [c.get() for c in _combos(dlg)]
        afirmar(any("Azahar" in t for t in textos), textos)
        dlg.destroy()
        dlg = _dlg(app, root, None)
        textos = [c.get() for c in _combos(dlg)]
        afirmar(any(t == "—" for t in textos), textos)
        dlg.destroy()
    finally:
        root.destroy()


def teste_resolver_jogo_cli():
    import tempfile

    import app_win
    tmp = Path(tempfile.mkdtemp(prefix="suite-dj-"))
    con = core.get_db(tmp / "j.db")
    try:
        a = core.criar_jogo(con, {"titulo": "Megabonk", "executable_path": "",
                                  "status": "backlog"})
        core.criar_jogo(con, {"titulo": "Megabonk 2", "executable_path": "",
                              "status": "backlog"})
        afirmar(app_win.resolver_jogo_cli(con, str(a["id"]))["id"] == a["id"])
        afirmar(app_win.resolver_jogo_cli(con, "megabonk")["id"] == a["id"])
        try:
            app_win.resolver_jogo_cli(con, "megabonk 2 x")
            afirmar(False, "devia levantar")
        except LookupError:
            pass
        try:
            app_win.resolver_jogo_cli(con, "mega")
            afirmar(False, "ambíguo devia levantar")
        except LookupError as e:
            afirmar("ambíguo" in str(e), e)
        try:
            app_win.resolver_jogo_cli(con, "   ")
            afirmar(False, "vazio devia levantar")
        except LookupError:
            pass
    finally:
        con.close()


def teste_minimizar_restaurar_janela():
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto("d5.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        app._minimizar_janela()
        root.update()
        app._restaurar_janela()
        root.update()
        afirmar(root.winfo_exists(), "janela sumiu")
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def teste_dialogo_secoes_escuras():
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto()
    if root is None:
        print("(sem display: skip)")
        return
    try:
        dlg = _dlg(app, root, None)
        secs = [w for w in dlg.winfo_children()
                if w.winfo_class() == "TLabelframe"]
        afirmar(len(secs) == 6, [s.cget("text") for s in secs])
        estilos = {s.cget("style") for s in secs}
        afirmar(estilos == {"Sec.TLabelframe"}, estilos)
        dlg.destroy()
    finally:
        root.destroy()


def teste_dialogo_salva():
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto("d2.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        dlg = _dlg(app, root, None)
        entradas = [w for w in dlg.winfo_children()
                    for w in ([w] + list(w.winfo_children()))
                    if w.winfo_class() == "TEntry"]
        afirmar(entradas, "sem entries")
        entradas[0].delete(0, tk.END)
        entradas[0].insert(0, "Jogo Teste Diálogo")
        botoes = [w for w in dlg.winfo_children()
                  for w in ([w] + list(w.winfo_children()))
                  if w.winfo_class() == "TButton" and "Salvar" in str(w.cget("text"))]
        afirmar(botoes, "sem botão Salvar")
        orig_info = messagebox.showinfo
        messagebox.showinfo = lambda *a, **k: None
        try:
            botoes[0].invoke()
            root.update()
        finally:
            messagebox.showinfo = orig_info
        con = core.get_db(app.db_path)
        try:
            n = con.execute("SELECT COUNT(*) AS n FROM jogos WHERE titulo=?",
                            ("Jogo Teste Diálogo",)).fetchone()["n"]
        finally:
            con.close()
        afirmar(n == 1, "linha não foi salva")
    finally:
        root.destroy()


def teste_desejos_sincronizar_nao_orfana_modal():
    """Regressão: Sincronizar erguia NameError (fim fora do trabalho) e
    orfanava o modal 'Lendo wishlist Steam…' sem thread."""
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    import app_win
    root, app = _app_oculto("des-sync.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        idx = next(i for i, (rot, _s, _f) in enumerate(app_win.NAV)
                   if rot.startswith("☆"))
        app._ir_nav(idx)
        root.update()
        v_princ = core.steam_principal
        v_ler = core.ler_wishlist
        core.steam_principal = lambda: {"steamid": "10", "persona": "t"}
        core.ler_wishlist = lambda _sid, **k: {
            "itens": [{"appid": "10", "titulo": "Alvo"}], "erros": []}
        avisos = []
        orig_info = messagebox.showinfo
        messagebox.showinfo = lambda *a, **k: avisos.append(a)
        try:
            app.sincronizar_desejos_ui()  # NameError aqui = modal órfão
            ok = _bombear(root, lambda: avisos, limite=8)
        finally:
            messagebox.showinfo = orig_info
            core.steam_principal = v_princ
            core.ler_wishlist = v_ler
        afirmar(ok, "fim do sync nunca rodou (modal órfão?)")
        pendentes = [w.title() for w in root.winfo_children()
                     if w.winfo_class() == "Toplevel"]
        afirmar(pendentes == [], pendentes)
        afirmar("1 novo" in str(avisos[0]), avisos)
        con = core.get_db(app.db_path)
        try:
            n = con.execute("SELECT COUNT(*) AS n FROM desejos").fetchone()["n"]
        finally:
            con.close()
        afirmar(n == 1, "desejo não espelhou")
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def teste_gui_sem_bug_modal_orfao():
    """Trava estática da classe 'modal órfão': defaults que quebram no def,
    update() de modal sem guarda e Thread sem daemon em app_win.py."""
    import ast
    import builtins
    from pathlib import Path

    import app_win
    src = Path(app_win.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    globais = set(dir(builtins)) | {"__name__"}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            globais.add(n.name)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    globais.add(t.id)
                elif isinstance(t, ast.Tuple):
                    for e in t.elts:
                        if isinstance(e, ast.Name):
                            globais.add(e.id)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            globais.add(n.target.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                if a.name != "*":
                    globais.add((a.asname or a.name).split(".")[0])

    def locais_de(fn):
        nomes, antes = set(), {}

        def coll(sts, presente):
            for st in sts:
                for no in ast.walk(st):
                    if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef,
                                       ast.ClassDef)):
                        nomes.add(no.name)
                        antes.setdefault(no.name, no.lineno)
                if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.ClassDef)):
                    continue
                for no in ast.walk(st):
                    if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef,
                                       ast.ClassDef, ast.Lambda)):
                        continue
                    if isinstance(no, ast.Name) and isinstance(no.ctx, ast.Store):
                        nomes.add(no.id)
                        antes.setdefault(no.id, no.lineno)
                    elif isinstance(no, ast.ExceptHandler) and no.name:
                        nomes.add(no.name)
                        antes.setdefault(no.name, no.lineno)
                    elif isinstance(no, (ast.Import, ast.ImportFrom)):
                        for a in no.names:
                            if a.name != "*":
                                nm = (a.asname or a.name).split(".")[0]
                                nomes.add(nm)
                                antes.setdefault(nm, no.lineno)
        coll(fn.body, True)
        pars = set()
        for a in list(fn.args.posonlyargs) + list(fn.args.args) \
                + list(fn.args.kwonlyargs):
            pars.add(a.arg)
        if fn.args.vararg:
            pars.add(fn.args.vararg.arg)
        if fn.args.kwarg:
            pars.add(fn.args.kwarg.arg)
        return pars, nomes, antes

    problemas = []

    def visitar(no, pilha):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ext = (list(no.args.defaults)
                   + [d for d in no.args.kw_defaults if d])
            for e in ext:
                for nm in ast.walk(e):
                    if isinstance(nm, ast.Name) and isinstance(nm.ctx, ast.Load):
                        ok = nm.id in globais
                        for (pars, loc, ant) in reversed(pilha):
                            if nm.id in pars or (
                                    nm.id in loc and ant[nm.id] < no.lineno):
                                ok = True
                                break
                        if not ok:
                            problemas.append(
                                f"def {no.name}:{no.lineno} default '{nm.id}'")
            pars, loc, ant = locais_de(no)
            pilha2 = pilha + [(pars, loc, ant)]
            for st in no.body:
                visitar(st, pilha2)
            return
        if isinstance(no, ast.Lambda):
            pars = set()
            for a in list(no.args.posonlyargs) + list(no.args.args) \
                    + list(no.args.kwonlyargs):
                pars.add(a.arg)
            visitar(no.body, pilha + [(pars, set(), {})])
            return
        for f in ast.iter_child_nodes(no):
            visitar(f, pilha)

    visitar(tree, [])
    afirmar(not problemas, problemas[:5])
    # update() de modal: exige ancestral Try (guarda TclError)
    class V(ast.NodeVisitor):
        def __init__(self):
            self.pilha = []
            self.ruins = []

        def generic_visit(self, n):
            self.pilha.append(n)
            super().generic_visit(n)
            self.pilha.pop()

        def visit_Call(self, n):
            # só modal (prog/win/dlg/...): dict.update e root.update
            # não orfanam nada
            if isinstance(n.func, ast.Attribute) and n.func.attr == "update" \
                    and isinstance(n.func.value, ast.Name) \
                    and n.func.value.id in (
                        "prog", "win", "dlg", "caixa", "vw", "opcoes"):
                if not any(isinstance(p, ast.Try) for p in self.pilha):
                    self.ruins.append(n.lineno)
            self.generic_visit(n)

    v = V()
    v.visit(tree)
    afirmar(not v.ruins, f"update() sem guarda: {v.ruins[:8]}")
    # Threads sempre daemon
    class T(ast.NodeVisitor):
        def __init__(self):
            self.ruins = []

        def visit_Call(self, n):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr == "Thread":
                kw = {k.arg: k.value for k in n.keywords}
                d = kw.get("daemon")
                if not (isinstance(d, ast.Constant) and d.value is True):
                    self.ruins.append(n.lineno)
            self.generic_visit(n)

    t = T()
    t.visit(tree)
    afirmar(not t.ruins, f"Thread sem daemon=True: {t.ruins[:8]}")


def teste_desejos_adicionar_e_manual():
    """➕ Adicionar grava manual=1; espelho nunca apaga manual (v17)."""
    import sqlite3
    tmp = Path(tempfile.mkdtemp(prefix="suite-d-"))
    db = tmp / "des-man.db"
    con = core.get_db(db)
    try:
        r = core.adicionar_desejo(con, "2062430", "BALL x PIT")
        afirmar(r == {"ok": True, "novo": True}, r)
        r = core.adicionar_desejo(con, "2062430", "BALL x PIT")
        afirmar(r == {"ok": True, "novo": False}, r)
        try:
            core.adicionar_desejo(con, "xx", "")
            afirmar(False, "devia levantar")
        except ValueError:
            pass
        res = core.sincronizar_desejos(con, [{"appid": "99", "titulo": "Outro"}])
        restam = [d["appid"] for d in core.listar_desejos(con)]
        afirmar("2062430" in restam and "99" in restam, (res, restam))
        core.sincronizar_desejos(con, [{"appid": "2062430", "titulo": "BALL x PIT"}])
        core.sincronizar_desejos(con, [])
        afirmar([d["appid"] for d in core.listar_desejos(con)] == ["2062430"],
                "espelho desprotegeu o desejo adicionado manualmente")
    finally:
        con.close()
    # migração v17: banco v16 real (sem `manual`) ganha a coluna sem perder linha
    db2 = tmp / "des-leg.db"
    con = core.get_db(db2)
    try:
        core.adicionar_desejo(con, "10", "Alvo")
    finally:
        con.close()
    c2 = sqlite3.connect(str(db2))
    try:
        c2.execute("ALTER TABLE desejos DROP COLUMN manual")
        c2.commit()
        cols = {r[1] for r in c2.execute("PRAGMA table_info(desejos)").fetchall()}
        afirmar("manual" not in cols, cols)
    finally:
        c2.close()
    con = core.get_db(db2)
    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(desejos)")}
        afirmar("manual" in cols, cols)
        ds = core.listar_desejos(con)
        afirmar(len(ds) == 1 and ds[0]["titulo"] == "Alvo", ds)
    finally:
        con.close()


def teste_desejos_json_na_steam_abre_url():
    """🌐 na Steam: abre a wishlist do steamid (mock, sem rede)."""
    try:
        from tkinter import messagebox
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    import webbrowser
    root, app = _app_oculto("des-json.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        v_princ = core.steam_principal
        core.steam_principal = lambda: {"steamid": "10", "persona": "t"}
        aberto = []
        velho_open = webbrowser.open
        webbrowser.open = lambda url: aberto.append(url) or True
        orig_info = messagebox.showinfo
        messagebox.showinfo = lambda *a, **k: None
        try:
            app.abrir_wishlist_json_na_steam()
        finally:
            messagebox.showinfo = orig_info
            webbrowser.open = velho_open
            core.steam_principal = v_princ
        afirmar(aberto == ["https://store.steampowered.com/wishlist/profiles/"
                           "10/"], aberto)
        webbrowser.open = lambda url: False
        core.steam_principal = lambda: {"steamid": "10", "persona": "t"}
        avisos_w = []
        orig_warn = messagebox.showwarning
        messagebox.showwarning = lambda *a, **k: avisos_w.append(a)
        try:
            app.abrir_wishlist_json_na_steam()
        finally:
            messagebox.showwarning = orig_warn
            webbrowser.open = velho_open
            core.steam_principal = v_princ
        afirmar(avisos_w and "profiles/10/" in str(avisos_w[0]), avisos_w)
    finally:
        try:
            root.destroy()
        except Exception:
            pass
def teste_dialogo_hosts_clicaveis_e_fitgirl():
    """Hosts: clique mostra via/duplo baixa; morte total oferece FitGirl."""
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto("cat-host.db")
    if root is None:
        print("(sem display: skip)")
        return
    v_busca = core.buscar_steamrip
    v_det = core.detalhes_steamrip
    v_baixar = core.baixar_steamrip
    v_fgirl = core.buscar_fitgirl
    core.buscar_steamrip = lambda _t: {
        "itens": [{"titulo": "BALL x PIT Free Download",
                   "url": "https://steamrip.com/x"}], "erros": []}
    core.detalhes_steamrip = lambda _u: {
        "hosts": [{"nome": "gofile", "url": "https://gofile.io/d/xyz"}]}
    core.baixar_steamrip = lambda *a, **k: {
        "ok": False, "erro": "gofile: conteudo expirado (404)"}
    core.buscar_fitgirl = lambda _t: {"itens": [], "erros": []}
    avisos, perguntas, infos = [], [], []
    orig_warn = messagebox.showwarning
    orig_ask = messagebox.askyesno
    orig_info = messagebox.showinfo
    messagebox.showwarning = lambda *a, **k: avisos.append(a)
    messagebox.askyesno = lambda *a, **k: perguntas.append(a) or True
    messagebox.showinfo = lambda *a, **k: infos.append(a)
    try:
        app.dlg_catalogo("steamrip")
        root.update()
        wins = [w for w in root.winfo_children()
                if w.winfo_class() == "Toplevel"]
        afirmar(len(wins) == 1, [w.title() for w in wins])
        win = wins[0]

        def achar_listas(w):
            out = []

            def walk(x):
                for ch in x.winfo_children():
                    if ch.winfo_class() == "Listbox":
                        out.append(ch)
                    walk(ch)
            walk(w)
            return out

        def achar_botao(w, pedaco):
            out = []

            def walk(x):
                for ch in x.winfo_children():
                    if ch.winfo_class() == "TButton" \
                            and pedaco in str(ch.cget("text")):
                        out.append(ch)
                    walk(ch)
            walk(w)
            return out

        def achar_estado(w):
            txts = []

            def walk(x):
                for ch in x.winfo_children():
                    if ch.winfo_class() == "TLabel":
                        try:
                            txts.append(str(ch.cget("text")))
                        except Exception:
                            pass
                    walk(ch)
            walk(w)
            return txts
        lst_r, lst_h = achar_listas(win)
        afirmar(lst_h.bind("<<ListboxSelect>>"), "host sem clique")
        afirmar(lst_h.bind("<Double-Button-1>"), "host sem duplo")
        buscar_btn = achar_botao(win, "Buscar")
        afirmar(buscar_btn, "sem Buscar")
        ents = []

        def walk_ent(x):
            for ch in x.winfo_children():
                if ch.winfo_class() == "TEntry":
                    ents.append(ch)
                walk_ent(ch)

        walk_ent(win)
        afirmar(ents, "sem busca")
        ent = ents
        ent[0].delete(0, tk.END)
        ent[0].insert(0, "BALL x PIT")
        buscar_btn[0].invoke()
        afirmar(_bombear(root, lambda: lst_r.size() > 0, limite=10),
                "busca nao listou")
        afirmar(_bombear(root, lambda: lst_h.size() > 0, limite=10),
                "hosts nao carregaram sozinhos")
        afirmar(lst_r.curselection() == (0,),
                "primeiro resultado nao veio selecionado")
        afirmar(any("duplo-clique baixa" in t
                    for t in achar_estado(win)), achar_estado(win))
        lst_h.selection_set(0)
        baixar_btn = achar_botao(win, "Baixar")
        afirmar(baixar_btn, "sem Baixar")
        baixar_btn[0].invoke()
        afirmar(_bombear(root, lambda: bool(perguntas), limite=15),
                "falha total nao ofereceu FitGirl")
        afirmar(not infos, infos)
        titulos = sorted(w.title() for w in root.winfo_children()
                         if w.winfo_class() == "Toplevel")
        afirmar("Catálogo FitGirl" in titulos, titulos)
        for w in root.winfo_children():
            if w.winfo_class() == "Toplevel":
                try:
                    w.destroy()
                except Exception:
                    pass
        root.update()
    finally:
        messagebox.showwarning = orig_warn
        messagebox.askyesno = orig_ask
        messagebox.showinfo = orig_info
        core.buscar_steamrip = v_busca
        core.detalhes_steamrip = v_det
        core.baixar_steamrip = v_baixar
        core.buscar_fitgirl = v_fgirl
        try:
            root.destroy()
        except Exception:
            pass


def teste_dialogo_aba_downloads():
    import os
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    import app_win
    root, app = _app_oculto("dl.db")
    if root is None:
        print("(sem display: skip)")
        return
    tmp = os.environ.get("BIBLIOTECA_QBIT_DIR")
    os.environ["BIBLIOTECA_QBIT_DIR"] = "/nao-existe-suite-dl"
    try:
        idx = next(i for i, (rot, _s, _f) in enumerate(app_win.NAV)
                   if "Downloads" in rot)
        app._ir_nav(idx)
        root.update()
        afirmar(app._em_downloads(), app.nav_idx)
        lbs = _listas(app.grade)
        afirmar(lbs, "aba downloads sem lista")
        afirmar("PASTA" in app.btn_jogar.cget("text"),
                app.btn_jogar.cget("text"))
        app._ir_nav(0)
        root.update()
        afirmar(not app._em_downloads(), app.nav_idx)
    finally:
        if tmp is None:
            os.environ.pop("BIBLIOTECA_QBIT_DIR", None)
        else:
            os.environ["BIBLIOTECA_QBIT_DIR"] = tmp
        try:
            root.destroy()
        except Exception:
            pass

def teste_dialogo_sidebar_sem_mae_de_um():
    try:
        import tkinter as tk
    except ModuleNotFoundError:
        print("(sem tkinter: skip)")
        return
    root, app = _app_oculto("side.db")
    if root is None:
        print("(sem display: skip)")
        return
    try:
        textos = []

        def walk(x):
            for ch in x.winfo_children():
                if ch.winfo_class() == "TButton":
                    try:
                        textos.append(str(ch.cget("text")))
                    except Exception:
                        pass
                walk(ch)
        walk(root)
        maes = sorted(t for t in textos
                      if t.startswith(("\u25bc", "\u25b6"))
                      and "JOGAR" not in t)
        afirmar(maes == ["▼ ⬇ ARQUIVO", "▼ 🎵 MÚSICAS", "▼ 📚 BIBLIOTECA"],
                maes)
        for sozinho in ("DESEJOS", "DOWNLOADS", "SISTEMA"):
            afirmar(not any(t.startswith(("▼", "▶")) and sozinho in t
                            for t in textos), textos)
        for direto in ("☆ Desejos", "⬇ Downloads",
                       "⚙ Configurações", "🧹 Sanear pasta…"):
            afirmar(any(direto in t for t in textos), direto)
        afirmar(len(app.nav_btns) == 4, len(app.nav_btns))
    finally:
        try:
            root.destroy()
        except Exception:
            pass
