"""Regressões da interface visível: resize, seleção e ações alcançáveis."""
import tempfile
import time
from pathlib import Path

import bib_core as core
from executar import afirmar


def _montar(escala=None):
    try:
        import tkinter as tk

        import app_win
        root = tk.Tk()
        # Suíte roda em segundo plano: janela estacionada fora da área
        # visível e totalmente transparente. withdraw() não serve aqui —
        # o gerenciador só calcula a grade real com a janela mapeada —
        # mas nestas coordenadas nada pisca na tela.
        root.geometry("+10000+10000")
        try:
            root.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        # O desktop virtual pode ter só 1024 px. As geometrias sob teste não
        # devem ser limitadas pelo maxsize implícito do gerenciador de janelas.
        root.maxsize(max(1600, root.winfo_screenwidth()), max(1000, root.winfo_screenheight()))
        if escala is not None:
            root.tk.call("tk", "scaling", escala)
    except (ImportError, RuntimeError):
        print("(sem tkinter: skip)")
        return None, None
    except tk.TclError:
        print("(sem display: skip)")
        return None, None
    tmp = Path(tempfile.mkdtemp(prefix="visual-"))
    db = tmp / "biblioteca.db"
    con = core.get_db(db)
    try:
        for i in range(15):
            core.criar_jogo(con, {"titulo": f"Jogo {i:02d} com título comprido",
                                  "executable_path": str(tmp / f"game{i}.exe")})
        core.adicionar_desejo(con, "10", "Primeiro desejo")
        core.adicionar_desejo(con, "20", "Segundo desejo")
    finally:
        con.close()
    erros = []
    root.report_callback_exception = lambda *exc: erros.append(str(exc))
    app = app_win.App(root, db)
    app._erros_visuais_teste = erros
    return root, app


def _bombear(root):
    for _ in range(8):
        root.update()
        time.sleep(0.01)


def _aguardar(root, pronto, limite=3):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        root.update()
        if pronto():
            return True
        time.sleep(0.01)
    return False


def teste_visual_resize_e_grade_sem_reentrada():
    root, app = _montar()
    if root is None:
        return
    try:
        for largura, altura in ((1280, 800), (960, 600), (860, 560), (1280, 800)):
            root.geometry(f"{largura}x{altura}")
            _bombear(root)
            afirmar(len(app.cards) == 15, "resize perdeu jogos")
            cols = {c["frame"].grid_info()["column"] for c in app.cards}
            afirmar(len(cols) >= 2, (largura, cols))
            for c in app.cards:
                fr = c["frame"]
                afirmar(fr.winfo_x() + fr.winfo_width() <= app.canvas.winfo_width(),
                        (largura, c["jogo"]["titulo"]))
            afirmar(app.canvas.winfo_height() > 180, "filtros engoliram a grade")
        afirmar(not app._erros_visuais_teste, app._erros_visuais_teste)
    finally:
        root.destroy()


def teste_visual_big_picture_teclado_e_retorno():
    from types import SimpleNamespace
    root, app = _montar()
    if root is None:
        return
    try:
        root.geometry("1280x800")
        _bombear(root)
        app._alternar_big_picture()
        afirmar(_aguardar(root, lambda: app.big_picture and root.attributes("-fullscreen")),
                "não entrou em tela cheia")
        _bombear(root)
        afirmar(not app.sidebar.winfo_ismapped(), "sidebar ocupou o modo imersivo")
        afirmar(not app.det_painel.winfo_ismapped(), "painel ocupou o modo imersivo")
        afirmar(not app.filtros_area.winfo_ismapped(), "filtros ocuparam o modo imersivo")
        afirmar(app.destaque.winfo_ismapped(), "destaque ausente")
        for i in (1, 2, 3, 0):
            app.nav_superior_btns[i].invoke()
            _bombear(root)
            afirmar(app.nav_idx == i and app.big_picture, "HUD não navegou em tela cheia")
            afirmar(app.nav_superior.winfo_ismapped(), "navegação superior desapareceu")
            afirmar(bool(app.destaque.winfo_ismapped()) == (i == 0), "destaque de jogo vazou para outra categoria")
        app.nav_superior_btns[1].invoke()
        _bombear(root)
        app._sair_big_picture()
        _bombear(root)
        afirmar(app.nav_idx == 1 and not app.big_picture, "saída trocou de aba")
        app._alternar_big_picture()
        _bombear(root)
        afirmar(app.nav_idx == 1 and app.big_picture, "tela cheia trocou de aba sozinha")
        afirmar(app.nav_superior.winfo_ismapped() and not app.destaque.winfo_ismapped(),
                "HUD inconsistente fora da biblioteca")
        app.nav_superior_btns[0].invoke()
        _bombear(root)
        app._navegar_grade(SimpleNamespace(keysym="F1"))
        afirmar(app.big_picture, "tecla desconhecida saiu da tela cheia")
        afirmar(app._tamanho_card() == (216, 288), "capas não cresceram")
        app._navegar_grade(SimpleNamespace(keysym="End"))
        _bombear(root)
        afirmar(app.sel == 14, "End não selecionou o último card")
        ultimo = app.cards[14]["frame"]
        afirmar(ultimo.winfo_y() >= app.canvas.canvasy(0) - 2 and
                ultimo.winfo_y() + ultimo.winfo_height() <=
                app.canvas.canvasy(app.canvas.winfo_height()) + 2,
                "seleção ficou fora da área visível")
        afirmar(app.destaque_titulo.cget("text") == app.jogos[14]["titulo"], "destaque errado")
        app._navegar_grade(SimpleNamespace(keysym="Right"))
        afirmar(app.sel == 14, "navegação passou do fim")
        app._navegar_grade(SimpleNamespace(keysym="Home"))
        app._navegar_grade(SimpleNamespace(keysym="Right"))
        afirmar(app.sel == 1, "setas não navegaram")
        app._sair_big_picture()
        afirmar(_aguardar(root, lambda: not app.big_picture and not root.attributes("-fullscreen")),
                "não saiu da tela cheia")
        _bombear(root)
        afirmar(app.sidebar.winfo_ismapped() and app.filtros_area.winfo_ismapped(), "layout não restaurado")
        afirmar(not app.destaque.winfo_ismapped(), "destaque permaneceu aberto")
        afirmar(not app._erros_visuais_teste, app._erros_visuais_teste)
    finally:
        root.destroy()


def teste_visual_recarga_preserva_identidade_selecionada():
    root, app = _montar()
    if root is None:
        return
    try:
        _bombear(root)
        app.sel = 5
        escolhido = app.jogos[5]["id"]
        con = app._con()
        try:
            core.criar_jogo(con, {"titulo": "AAA novo primeiro jogo"})
        finally:
            con.close()
        app.recarregar()
        afirmar(app.jogos[app.sel]["id"] == escolhido, "recarga selecionou outro jogo")
        app.var_q.set("sem resultado xyz")
        app.recarregar()
        afirmar(app.sel is None and not app.cards, "seleção fantasma na busca vazia")
        afirmar(str(app.destaque_jogar.cget("state")) == "disabled", "jogar habilitado sem jogo")
        afirmar(not app._erros_visuais_teste, app._erros_visuais_teste)
    finally:
        root.destroy()


def teste_visual_tabelas_e_acoes_sem_cortes():
    from aparencia import BarraAcoes
    root, app = _montar()
    if root is None:
        return
    try:
        root.geometry("860x560")
        for idx in (2, 3, 1):
            app._ir_nav(idx)
            _bombear(root)
            afirmar(not app.vscroll.winfo_ismapped(), "duas rolagens na tabela")
            barras = [w for w in app.grade.winfo_children() if isinstance(w, BarraAcoes)]
            afirmar(barras, "ações ausentes")
            for barra in barras:
                for b in barra._botoes:
                    afirmar(b.winfo_ismapped(), b.cget("text"))
                    afirmar(b.winfo_x() + b.winfo_width() <= barra.winfo_width(), b.cget("text"))
                    afirmar(b.winfo_width() >= b.winfo_reqwidth(), "ação truncada")
                    afirmar(b.winfo_rooty() + b.winfo_height() <=
                            root.winfo_rooty() + root.winfo_height(), "ação fora da janela")
            afirmar(app.canvas.winfo_height() > 200, "tabela engolida pelas ações")
        app._ir_nav(2)
        _bombear(root)
        app._des_lista.selection_set("1")
        _bombear(root)
        afirmar(app.des_sel == 1 and app.det_titulo.cget("text") == "Segundo desejo",
                "seleção abriu o item errado")
        afirmar(not app._erros_visuais_teste, app._erros_visuais_teste)
    finally:
        root.destroy()


def teste_visual_detalhes_compactos_e_navegacao():
    root, app = _montar()
    if root is None:
        return
    try:
        root.geometry("960x600")
        _bombear(root)
        afirmar(app.btn_detalhes.winfo_ismapped(), "detalhes inacessíveis no compacto")
        app.btn_detalhes.invoke()
        _bombear(root)
        afirmar(app.det_janela is not None, "detalhes não abriram")
        app._ir_nav(2)
        _bombear(root)
        afirmar(app._det_replicas[1][0].cget("text") == "Primeiro desejo")
        app._fechar_detalhe()
        root.geometry("1280x800")
        afirmar(_aguardar(root, lambda: root.winfo_width() == 1280 and app.det_painel.winfo_ismapped()),
                f"layout largo não aplicado: largura={root.winfo_width()}")
        _bombear(root)
        afirmar(app.det_painel.winfo_ismapped(), "detalhes não voltaram ao layout largo")
        filhos = len(root.winfo_children())
        for mae in app._maes.values():
            mae["btn"].invoke()
            mae["btn"].invoke()
        _bombear(root)
        afirmar(len(root.winfo_children()) == filhos, "sidebar duplicou a interface")
        app.nav_area.canvas.yview_moveto(1)
        _bombear(root)
        configurar = [w for w in app.nav_area.corpo.winfo_children()
                       if w.winfo_class() == "TButton" and "Configurações" in w.cget("text")]
        afirmar(configurar and configurar[0].winfo_rooty() >= app.nav_area.canvas.winfo_rooty(),
                "Configurações não ficou alcançável ao rolar")
        afirmar(not app._erros_visuais_teste, app._erros_visuais_teste)
    finally:
        root.destroy()


def teste_visual_geometria_larga_em_desktop_pequeno():
    try:
        import tkinter as tk
    except ImportError:
        print("(sem tkinter: skip)")
        return
    from unittest.mock import patch
    criar_root = tk.Tk

    def desktop_pequeno():
        root = criar_root()
        root.maxsize(1024, 768)
        return root

    with patch.object(tk, "Tk", side_effect=desktop_pequeno):
        root, app = _montar()
    if root is None:
        return
    try:
        root.geometry("960x600")
        afirmar(_aguardar(root, lambda: root.winfo_width() == 960 and app.btn_detalhes.winfo_ismapped()),
                "layout compacto não aplicado")
        afirmar(not app.det_painel.winfo_ismapped(), "painel ocupou o compacto")
        root.geometry("1280x800")
        afirmar(_aguardar(root, lambda: root.winfo_width() == 1280 and app.det_painel.winfo_ismapped()),
                f"desktop pequeno limitou o layout de teste: {root.winfo_width()}")
        afirmar(not app._erros_visuais_teste, app._erros_visuais_teste)
    finally:
        root.destroy()


def teste_visual_escala_125_e_busca_limpa():
    root, app = _montar(1.67)
    if root is None:
        return
    try:
        root.geometry("960x600")
        _bombear(root)
        controles = [app.ent_busca, app.cmb_statusfiltro, app.chk_sofav,
                     app.cmb_tagfiltro, *app.plat_btns.values()]
        for w in controles:
            afirmar(w.winfo_width() >= w.winfo_reqwidth() or w is app.ent_busca,
                    "controle truncado: " + str(w))
            afirmar(w.winfo_rootx() + w.winfo_width() <= root.winfo_rootx() + root.winfo_width(),
                    "controle fora da janela")
        app.var_q.set("não existe")
        app.recarregar()
        _bombear(root)
        afirmar(len(app.cards) == 0)
        app.btn_limpar.invoke()
        _bombear(root)
        afirmar(len(app.cards) == 15, "Limpar não restaurou os jogos")
        afirmar(not app._erros_visuais_teste, app._erros_visuais_teste)
    finally:
        root.destroy()


def teste_visual_cache_imagens_por_interpretador():
    try:
        import tkinter as tk

        import app_win
        r1 = tk.Tk()
        r1.withdraw()
    except ImportError:
        print("(sem tkinter: skip)")
        return
    except tk.TclError:
        print("(sem display: skip)")
        return
    tmp = Path(tempfile.mkdtemp(prefix="visual-"))
    arq = tmp / "capa.png"
    try:
        imagem = tk.PhotoImage(master=r1, width=16, height=16)
        imagem.put("#7357e8", to=(0, 0, 16, 16))
        imagem.write(str(arq), format="png")
        a = app_win.carregar_miniatura(arq, master=r1)
        afirmar(a is not None)
    finally:
        r1.destroy()
    r2 = tk.Tk()
    r2.withdraw()
    try:
        b = app_win.carregar_miniatura(arq, master=r2)
        afirmar(b is not a and b.tk is r2.tk, "imagem pertence à janela destruída")
        tk.Label(r2, image=b).pack()
        r2.update_idletasks()
    finally:
        r2.destroy()


def teste_visual_sync_parcial_nao_apaga_desejos():
    from unittest.mock import patch
    root, app = _montar()
    if root is None:
        return
    from tkinter import messagebox
    try:
        con = core.get_db(app.db_path)
        try:
            core.sincronizar_desejos(con, [{"appid": "30", "titulo": "Anterior"}])
        finally:
            con.close()
        avisos = []
        with patch.object(core, "steam_principal", return_value={"steamid": "10"}), \
                patch.object(core, "ler_wishlist", return_value={
                    "itens": [{"appid": "10", "titulo": "Parcial"}], "erros": ["Timeout"]}), \
                patch.object(messagebox, "showwarning", side_effect=lambda *a: avisos.append(a)):
            app.sincronizar_desejos_ui()
            fim = time.monotonic() + 4
            while not avisos and time.monotonic() < fim:
                _bombear(root)
        afirmar(avisos, "falha não foi comunicada")
        con = core.get_db(app.db_path)
        try:
            afirmar(any(d["appid"] == "30" for d in core.listar_desejos(con)),
                    "sync parcial removeu o catálogo anterior")
        finally:
            con.close()
    finally:
        root.destroy()


def teste_visual_downloads_consulta_fora_da_thread_tk():
    import threading
    from unittest.mock import patch
    root, app = _montar()
    if root is None:
        return
    try:
        principal = threading.get_ident()
        chamadas = []
        iniciou, liberar = threading.Event(), threading.Event()

        def consulta():
            chamadas.append(threading.get_ident())
            iniciou.set()
            liberar.wait(2)
            return {"torrents": [], "erros": []}

        with patch.object(core, "listar_torrents", side_effect=consulta):
            app._ir_nav(3)
            afirmar(iniciou.wait(1), "worker não começou")
            afirmar(chamadas and principal not in chamadas, "HTTP executado na thread Tk")
            vivo = []
            root.after_idle(lambda: vivo.append(True))
            root.update()
            afirmar(vivo, "interface não reagiu durante a consulta")
            liberar.set()
            _bombear(root)
        afirmar(not app._erros_visuais_teste, app._erros_visuais_teste)
    finally:
        root.destroy()


def teste_visual_sanear_worker_sem_modal_orfao():
    from unittest.mock import patch
    root, app = _montar()
    if root is None:
        return
    from tkinter import filedialog, messagebox
    try:
        erros = []
        with patch.object(filedialog, "askdirectory", return_value="pasta-falsa"), \
                patch.object(core, "sanear_pasta", side_effect=OSError("disco indisponível")), \
                patch.object(messagebox, "showerror", side_effect=lambda *a: erros.append(a)):
            app.sanear_pasta_ui()
            fim = time.monotonic() + 4
            while not erros and time.monotonic() < fim:
                _bombear(root)
        afirmar(erros and "disco indisponível" in str(erros), erros)
        afirmar(not [w for w in root.winfo_children() if w.winfo_class() == "Toplevel"],
                "Sanear deixou o progresso travado")
        afirmar(not app._erros_visuais_teste, app._erros_visuais_teste)
    finally:
        root.destroy()
