#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TucoTeca — aplicativo local Windows (tkinter, stdlib).
Modo clássico, congelado: só correções críticas. O frontend principal é Qt.
Biblioteca com capas, painel de detalhes e modo Big Picture por teclado.
Mesmo banco e mesmas regras do terminal Linux; nada de navegador.

Uso:
    python codigo/frontends/app_win.py [--db caminho\\biblioteca.db]
    python codigo/frontends/app_win.py --selftest   # monta a UI oculta e sai (verificação)
Ou duplo-clique em BibliotecaHub.bat na raiz do projeto.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bib_core as core
from aparencia import ACC, BG, LINE, MUT, PANEL

OK_C = "#2ecc71"
WARN_C = "#f39c12"
BAD_C = "#e74c3c"

CARD_W, CARD_H = 156, 216
STATUS_CORES = {"backlog": MUT, "jogando": "#7aa2ff", "zerado": OK_C,
                "pausado": WARN_C, "abandonado": BAD_C}

# (rótulo, reservado, reservado) — status/favorito filtram na barra única
NAV = [("📚 Biblioteca", "", False),
       ("🎵 Músicas", "", False),
       ("☆ Desejos", "", False),
       ("⬇ Downloads", "", False)]
STATUS_FILTROS = ("Todos", "backlog", "jogando", "zerado", "pausado",
                  "abandonado")

_MINI_CACHE: dict = {}


def carregar_miniatura(caminho: Path, largura: int = CARD_W,
                       altura: int = CARD_H, master=None) -> tk.PhotoImage | None:
    """PhotoImage reduzido da capa, ou None (vira tile).

    Tenta Pillow (jpg/webp/png/gif) quando instalado; senão, PhotoImage
    nativo (só png/gif). Cacheado por (caminho, mtime, tamanho) p/ não
    recarregar a cada recarregar().
    """
    try:
        st = Path(caminho).stat()
        root = master or tk._default_root
        chave = (id(root.tk) if root is not None else None,
                 str(caminho), st.st_mtime_ns, st.st_size, largura, altura)
    except OSError:
        return None
    if chave in _MINI_CACHE:
        return _MINI_CACHE[chave]
    img = None
    # 1) Pillow (opcional): cobre jpg/webp e reduz com qualidade
    try:
        from PIL import Image, ImageTk  # type: ignore
        pil = Image.open(caminho)
        pil.load()
        pil.thumbnail((largura, altura), Image.LANCZOS)
        img = ImageTk.PhotoImage(pil, master=root)
        _MINI_CACHE[chave] = img
        if len(_MINI_CACHE) > 300:
            _MINI_CACHE.pop(next(iter(_MINI_CACHE)))
        return img
    except Exception:
        pass
    # 2) Nativo Tk (zero deps): png/gif apenas. Teto na divisão para a
    # imagem NUNCA estourar o alvo (piso deixava 141–279px intactos e a
    # grade transbordava a viewport).
    if Path(caminho).suffix.lower() not in (".png", ".gif"):
        return None
    try:
        base = tk.PhotoImage(master=root, file=str(caminho))
    except tk.TclError:
        return None
    try:
        f = max(1, -(-base.width() // largura), -(-base.height() // altura))
        img = base.subsample(f, f) if f > 1 else base
    except tk.TclError:
        return None
    _MINI_CACHE[chave] = img
    if len(_MINI_CACHE) > 300:
        _MINI_CACHE.pop(next(iter(_MINI_CACHE)))
    return img


def _titulo_escuro(janela) -> None:
    """Barra de título escura no Windows 10/11 via DWM (só stdlib).

    Sem efeito em outros SOs ou Windows antigos; nunca levanta.
    """
    try:
        if os.name != "nt":
            return
        import ctypes
        valor = ctypes.c_int(1)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.GetParent.argtypes = [ctypes.c_void_p]
        user32.GetParent.restype = ctypes.c_void_p
        interno = janela.winfo_id()
        hwnd = ctypes.c_void_p(user32.GetParent(interno) or interno)
        for attr in (20, 19):  # 20 = Win11/20H1+; 19 = builds antigas
            try:
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, attr, ctypes.byref(valor),
                        ctypes.sizeof(valor)) == 0:
                    return
            except Exception:
                continue
    except Exception:
        pass


def _com_rolagem(lst):
    """Acopla Scrollbar vertical num Listbox/Treeview já empacotado."""
    try:
        bar = ttk.Scrollbar(lst.master, orient="vertical", command=lst.yview,
                            style="Lista.Vertical.TScrollbar")
        bar.pack(side="right", fill="y", before=lst)
        lst.pack_configure(side="left")
        lst.configure(yscrollcommand=bar.set)
    except (tk.TclError, AttributeError):
        pass
    return lst


def _nova_grade_tv(mae, colunas=("Item", "Detalhe")) -> ttk.Treeview:
    """Lista moderna das abas (Treeview zebrada, 2 colunas)."""
    area = ttk.Frame(mae)
    area.pack(fill="both", expand=True)
    tv = ttk.Treeview(area, columns=list(colunas), show="headings",
                      height=14, selectmode="browse", style="Lista.Treeview")
    for j, col in enumerate(colunas):
        tv.heading(col, text=col)
        tv.column(col, width=(300 if j == 0 else 160), minwidth=40,
                  stretch=True, anchor="w")
    tv.tag_configure("par", background=BG)
    tv.tag_configure("impar", background=PANEL)

    def dimensionar(e):
        largura = max(80, e.width - 4)
        for j, col in enumerate(colunas):
            tv.column(col, width=int(largura * (0.62 if j == 0 else 0.38)))

    tv.bind("<Configure>", dimensionar)
    return tv


def _tv_por(tv: ttk.Treeview, linhas) -> None:
    """Preenche [(col0, col1)] com zebra. Linha ruim é pulada."""
    for i, par in enumerate(linhas):
        try:
            a, b = par
            tv.insert("", "end", iid=str(i), values=(str(a), str(b)),
                      tags=("par" if i % 2 else "impar",))
        except Exception:
            continue


def _tv_sel(tv) -> int | None:
    """Índice selecionado ou None. Nunca levanta."""
    try:
        sel = tv.selection()
    except (tk.TclError, AttributeError):
        return None
    if not sel:
        return None
    try:
        return int(sel[0])
    except (TypeError, ValueError):
        return None


def _tv_marcar(tv, idx) -> None:
    """Seleciona e mostra a linha. Nunca levanta."""
    if idx is None:
        return
    try:
        tv.selection_set(str(idx))
        tv.see(str(idx))
    except tk.TclError:
        pass


def desenhar_tile(cv: tk.Canvas, titulo: str, w: int, h: int,
                   selecionado: bool = False, grande: bool = False,
                   subtitulo: str = ""):
    """Capa local de reserva, com monograma e gradiente discreto."""
    cv.delete("all")
    borda = ACC if selecionado else LINE
    for y in range(0, h, 4):
        t = y / max(1, h)
        cor = "#%02x%02x%02x" % (int(40 - 12 * t), int(47 - 13 * t), int(73 - 30 * t))
        cv.create_rectangle(0, y, w, y + 4, fill=cor, outline="")
    cv.create_oval(w * 0.12, h * 0.16, w * 0.88, h * 0.73, outline="#45405e", width=1)
    cv.create_rectangle(1, 1, w - 1, h - 1, outline=borda, width=2)
    inicial = (titulo.strip()[:1] or "?").upper()
    cor = ACC if selecionado else "#c6baff"
    cx, cy = w / 2, h * 0.44
    if titulo == "⬇":
        cv.create_line(cx, cy - 30, cx, cy + 20, fill=cor, width=5)
        cv.create_line(cx - 17, cy + 5, cx, cy + 22, cx + 17, cy + 5, fill=cor, width=5)
        cv.create_line(cx - 24, cy + 34, cx + 24, cy + 34, fill=cor, width=4)
    elif titulo == "☆":
        pontos = []
        for i in range(10):
            raio = 34 if i % 2 == 0 else 15
            angulo = math.pi * i / 5 - math.pi / 2
            pontos.extend((cx + raio * math.cos(angulo), cy + raio * math.sin(angulo)))
        cv.create_polygon(*pontos, fill="", outline=cor, width=3)
    elif titulo == "♪":
        cv.create_line(cx + 8, cy - 28, cx + 8, cy + 18, fill=cor, width=4)
        cv.create_line(cx + 8, cy - 28, cx + 27, cy - 20, fill=cor, width=5)
        cv.create_oval(cx - 12, cy + 10, cx + 9, cy + 25, fill=cor, outline="")
    else:
        cv.create_text(cx, cy, text=inicial, fill=cor,
                       font=("Segoe UI", 56 if grande else 42, "bold"))
    base_y = h - (30 if grande else 22)
    if subtitulo:
        cv.create_text(w // 2, base_y - (16 if grande else 13), text=subtitulo,
                       fill=ACC, font=("Segoe UI", 10 if grande else 9, "bold"))
    caption = {"⬇": "Download", "♪": "Música local", "☆": "Lista de desejos"}.get(titulo, "sem capa")
    cv.create_text(w // 2, base_y, text=caption,
                   fill=MUT, font=("Segoe UI", 9 if grande else 8))


from app_win_base import MixBase
from app_win_desejos import MixDesejos
from app_win_dialogos import MixDialogos
from app_win_downloads import MixDownloads
from app_win_jogos import MixJogos
from app_win_midia import MixMidia
from app_win_musica import MixMusica
from app_win_scans import MixScans
from app_win_sistema import MixSistema


class App(MixBase, MixJogos, MixMusica, MixDownloads, MixDesejos,
          MixDialogos, MixScans, MixSistema, MixMidia):
    """Classico: estado no __init__ (MixBase), comportamento nos mixins."""




def resolver_jogo_cli(con, busca: str) -> dict:
    """Acha 1 jogo por id ou título (exato vence parcial). Sem Tk.

    Levanta LookupError se zero ou ambíguo. Para `tucoteca --jogar`.
    """
    chave = (busca or "").strip()
    if not chave:
        raise LookupError("informe o id ou parte do título.")
    if chave.isdigit():
        row = con.execute("SELECT * FROM jogos WHERE id=?",
                          (int(chave),)).fetchone()
        if row is None:
            raise LookupError(f"jogo id {chave} não encontrado.")
        return core.row_to_dict(row)
    nsa = chave.lower()
    todos = [core.row_to_dict(r)
             for r in con.execute("SELECT * FROM jogos").fetchall()]
    exatos = [j for j in todos if (j.get("titulo") or "").lower() == nsa]
    if len(exatos) == 1:
        return exatos[0]
    parciais = [j for j in todos if nsa in (j.get("titulo") or "").lower()]
    if len(parciais) == 1:
        return parciais[0]
    if not parciais:
        raise LookupError(f"nenhum jogo bate com '{chave}'.")
    nomes = ", ".join(f"{j['id']}:{j['titulo']}" for j in parciais[:8])
    raise LookupError(f"'{chave}' é ambíguo: {nomes}.")


def main_jogar(args) -> int:
    """`--jogar BUSCA`: abre o jogo sem a janela (p/ atalhos do Desktop)."""
    con = core.get_db(Path(args.db))
    try:
        try:
            j = resolver_jogo_cli(con, args.jogar)
        except (LookupError, ValueError) as e:
            print(f"[erro] {e}")
            return 2
        prep = core.preparar_lancamento(j)
        if prep.get("aviso"):
            print(f"[aviso] {prep['aviso']}")
        pronto: dict = {}
        feito = threading.Event()

        def ao_fim(sessao, rastreado, _gid=j["id"]):
            pronto["sessao"] = sessao
            pronto["rastreado"] = rastreado
            feito.set()

        res = core.executar_monitorado(j, ao_fim=ao_fim)
        if not res.get("ok"):
            print(f"[erro] {res.get('erro', 'falha')}")
            return 1
        if res.get("rastreado"):
            core.marcar_execucao(con, j["id"])
            feito.wait()
            ok, msg = App._registrar_sessao(
                con, j["id"], float(pronto.get("sessao") or 0.0))
            print(f"[ok] Executando ({res.get('modo')}) — {msg}")
            return 0
        try:
            core.iniciar_sessao_manual(j["id"], j.get("titulo") or "")
        except Exception:
            pass
        print("[ok] Executando — ao terminar use o Hub (⏱ Registrar sessão).")
        return 0
    finally:
        try:
            con.close()
        except Exception:
            pass
        try:
            core.liberar_lock()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TucoTeca — app Windows (tkinter)")
    ap.add_argument("--db", default=str(core.DEFAULT_DB))
    ap.add_argument("--selftest", action="store_true",
                    help="monta a UI oculta, recarrega e sai")
    ap.add_argument("--ignorar-lock", action="store_true",
                    help="abre mesmo com lock de outra instância (após crash)")
    ap.add_argument("--jogar", default=None, metavar="BUSCA",
                    help="abre o jogo (id ou título) sem a janela")
    args = ap.parse_args(argv)
    core.garantir_dirs()
    lk = core.adquirir_lock(ignorar=args.ignorar_lock)
    if not lk.get("ok"):
        try:
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("Biblioteca", lk.get("erro", "já aberta"))
            r.destroy()
        except Exception:
            print(f"[erro] {lk.get('erro')}")
        return 2
    import atexit
    atexit.register(core.liberar_lock)
    core.get_db(Path(args.db)).close()
    if args.jogar:
        # mantém o lock adquirido acima durante o jogo (main_jogar libera)
        return main_jogar(args)
    root = tk.Tk()
    _titulo_escuro(root)
    app = App(root, Path(args.db))
    if args.selftest:
        root.withdraw()
        root.update()
        n = len(app.jogos)
        ncards = len(app.cards)
        root.destroy()
        core.liberar_lock()
        print(f"[ok] selftest: UI montada, {n} jogo(s), {ncards} card(s)")
        return 0
    try:
        root.after(1500, app.sincronizar_nomes_boot)
        root.mainloop()
    finally:
        core.liberar_lock()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
