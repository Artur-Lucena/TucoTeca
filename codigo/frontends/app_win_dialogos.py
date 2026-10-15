#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca classico: MixDialogos de App (verbatim do modulo original)."""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, simpledialog, ttk

import bib_core as core
from aparencia import ACC, TXT, BarraAcoes
from late import ModuloTardio

_W = ModuloTardio("app_win")


class MixDialogos:
    def _janela_mods(self, pai, tid, holder, ao_ok=None):
        win = tk.Toplevel(pai)
        _W._titulo_escuro(win)
        win.title(f"Mods — {tid}" + (" (desligados)" if holder.get("off") else ""))
        win.transient(pai)
        win.grab_set()
        win.minsize(420, 320)
        fr = ttk.Frame(win, padding=12)
        fr.pack(fill="both", expand=True)
        tmp_ativos = set(holder["ativos"])
        lst = tk.Listbox(fr, selectmode="single", width=52, height=10,
                         bg="#0b0d12", fg=TXT, selectbackground=ACC,
                         font=("Segoe UI", 11))
        lst.pack(fill="both", expand=True)
        _W._com_rolagem(lst)

        def disp():
            try:
                return core.listar_mods(tid)
            except Exception:
                return []

        def redesenhar():
            nomes = disp()
            lst.delete(0, "end")
            for nome in nomes:
                lst.insert("end", f"[{'x' if nome in tmp_ativos else ' '}] {nome}")
            tmp_ativos.intersection_update(nomes)
            return nomes

        def alternar(_e=None):
            sel = lst.curselection()
            if not sel:
                return
            nomes = disp()
            if sel[0] >= len(nomes):
                return
            nome = nomes[sel[0]]
            if nome in tmp_ativos:
                tmp_ativos.discard(nome)
            else:
                tmp_ativos.add(nome)
            redesenhar()
            lst.selection_set(sel[0])

        def adicionar():
            if not _W.messagebox.askyesno("Mods", "De arquivo (.zip/.7z)?\n(Não = de pasta)"):
                pasta = filedialog.askdirectory(title="Pasta do mod", parent=win)
                origem = pasta or ""
            else:
                origem = filedialog.askopenfilename(
                    title="Arquivo do mod", parent=win,
                    filetypes=[("Mods", "*.zip *.7z"), ("Todos", "*.*")]) or ""
            if not origem:
                return
            nome = simpledialog.askstring(
                "Mods", "Nome do mod (vazio=automático):", parent=win)
            if nome is None:
                return
            r = core.importar_mod(origem, tid, (nome or "").strip())
            if not r.get("ok"):
                _W.messagebox.showwarning("Mods", r.get("erro", "falha"))
                return
            tmp_ativos.add(r["mod"])
            redesenhar()

        def remover():
            sel = lst.curselection()
            nomes = disp()
            if not sel or sel[0] >= len(nomes):
                return
            nome = nomes[sel[0]]
            if not _W.messagebox.askokcancel(
                    "Mods", f"Apagar '{nome}' da biblioteca?"):
                return
            r = core.remover_mod(tid, nome)
            if not r.get("ok"):
                _W.messagebox.showwarning("Mods", r.get("erro", "falha"))
                return
            tmp_ativos.discard(nome)
            redesenhar()

        def ok():
            holder["ativos"] = [m for m in disp() if m in tmp_ativos]
            if ao_ok:
                try:
                    ao_ok()
                except Exception as e:
                    core.log_erro("mods", f"ao_ok falhou: {e}")
            win.destroy()

        lst.bind("<Double-Button-1>", alternar)
        redesenhar()
        fr_btn = ttk.Frame(fr)
        fr_btn.pack(fill="x", pady=(10, 0))
        ttk.Button(fr_btn, text="Alternar", command=alternar).pack(side="left")
        ttk.Button(fr_btn, text="Adicionar…", command=adicionar).pack(side="left", padx=6)
        ttk.Button(fr_btn, text="Remover", command=remover).pack(side="left")
        ttk.Button(fr_btn, text="OK", command=ok).pack(side="right")
        ttk.Button(fr_btn, text="Cancelar", command=win.destroy).pack(side="right", padx=6)
    def _janela_cheats(self, pai, tid, ao_ok=None):
        win = tk.Toplevel(pai)
        _W._titulo_escuro(win)
        win.title(f"Cheats — {tid} (vale após reiniciar)")
        win.transient(pai)
        win.grab_set()
        win.minsize(420, 320)
        fr = ttk.Frame(win, padding=12)
        fr.pack(fill="both", expand=True)
        lst = tk.Listbox(fr, selectmode="single", width=52, height=10,
                         bg="#0b0d12", fg=TXT, selectbackground=ACC,
                         font=("Segoe UI", 11))
        lst.pack(fill="both", expand=True)
        _W._com_rolagem(lst)

        def redesenhar():
            try:
                nomes = core.listar_cheats(tid)
            except Exception:
                nomes = []
            lst.delete(0, "end")
            for c in nomes:
                lst.insert("end", f"[{'x' if c['ativo'] else ' '}] {c['nome']}")
            return [c["nome"] for c in nomes]

        def alternar(_e=None):
            sel = lst.curselection()
            nomes = redesenhar()
            if not sel or sel[0] >= len(nomes):
                return
            try:
                core.alternar_cheat(tid, nomes[sel[0]])
            except Exception as e:
                _W.messagebox.showwarning("Cheats", f"falha: {e}")
                return
            redesenhar()
            lst.selection_set(sel[0])
            if ao_ok:
                try:
                    ao_ok()
                except Exception as e:
                    core.log_erro("cheats", f"ao_ok falhou: {e}")

        def adicionar():
            nome = simpledialog.askstring(
                "Cheats", "Nome do cheat:", parent=win)
            if not nome:
                return
            caixa = tk.Toplevel(win)
            _W._titulo_escuro(caixa)
            caixa.title("Código (XXXXXXXX YYYYYYYY por linha)")
            caixa.transient(win)
            caixa.grab_set()
            txt = tk.Text(caixa, width=52, height=8, bg="#0b0d12", fg=TXT,
                          insertbackground=TXT, font=("Consolas", 11))
            txt.pack(fill="both", expand=True, padx=12, pady=12)

            def gravar():
                r = core.adicionar_cheat(tid, nome.strip(),
                                         txt.get("1.0", "end"))
                if not r.get("ok"):
                    _W.messagebox.showwarning("Cheats", r.get("erro", "falha"))
                    return
                caixa.destroy()
                redesenhar()

            ttk.Button(caixa, text="Salvar (desligado)",
                       command=gravar).pack(pady=(0, 12))

        def remover():
            sel = lst.curselection()
            nomes = redesenhar()
            if not sel or sel[0] >= len(nomes):
                return
            if not _W.messagebox.askokcancel(
                    "Cheats", f"Apagar '{nomes[sel[0]]}'?"):
                return
            r = core.remover_cheat(tid, nomes[sel[0]])
            if not r.get("ok"):
                _W.messagebox.showwarning("Cheats", r.get("erro", "falha"))
                return
            redesenhar()
            if ao_ok:
                try:
                    ao_ok()
                except Exception as e:
                    core.log_erro("cheats", f"ao_ok falhou: {e}")

        lst.bind("<Double-Button-1>", alternar)
        redesenhar()
        fr_btn = ttk.Frame(fr)
        fr_btn.pack(fill="x", pady=(10, 0))
        ttk.Button(fr_btn, text="Alternar", command=alternar).pack(side="left")
        ttk.Button(fr_btn, text="Adicionar…", command=adicionar).pack(side="left", padx=6)
        ttk.Button(fr_btn, text="Remover", command=remover).pack(side="left")
        ttk.Button(fr_btn, text="Fechar",
                   command=win.destroy).pack(side="right")
    def dlg_catalogo(self, fonte="steamrip", termo=None):
        fontes = {
            "steamrip": {"titulo": "Catálogo SteamRip",
                         "lista": "Hosts da página:",
                         "buscar": core.buscar_steamrip},
            "fitgirl": {"titulo": "Catálogo FitGirl",
                        "lista": "Espelhos e magnets:",
                        "buscar": core.buscar_fitgirl},
        }
        cfg = fontes.get(fonte) or fontes["steamrip"]
        marca = "FitGirl" if fonte == "fitgirl" else "SteamRip"
        win = tk.Toplevel(self.root)
        _W._titulo_escuro(win)
        win.title(cfg["titulo"])
        win.transient(self.root)
        win.minsize(560, 460)
        fr = ttk.Frame(win, padding=12)
        fr.pack(fill="both", expand=True)
        topo = ttk.Frame(fr)
        topo.pack(fill="x")
        var_q = tk.StringVar()
        ent = ttk.Entry(topo, textvariable=var_q, width=40)
        ent.pack(side="left", fill="x", expand=True)
        ent.bind("<Return>", lambda _e: buscar())
        resultados: list[dict] = []
        links: list[dict] = []  # {tipo: host/espelho/magnet, nome, url}
        consulta = {"busca": 0, "hosts": 0}
        suprimir = {"evento": False}  # seleção programática não recarrega
        self._sr_ultimo = getattr(self, "_sr_ultimo", "")
        area_r = ttk.Frame(fr)
        area_r.pack(fill="both", expand=True, pady=(8, 0))
        lst_r = tk.Listbox(area_r, selectmode="single", width=70, height=9,
                           bg="#0b0d12", fg=TXT, selectbackground=ACC,
                           exportselection=False,
                           font=("Segoe UI", 11))
        lst_r.pack(fill="both", expand=True)
        _W._com_rolagem(lst_r)
        ttk.Label(fr, text=cfg["lista"], style="Mut.TLabel").pack(
            anchor="w", pady=(8, 0))
        area_h = ttk.Frame(fr)
        area_h.pack(fill="x")
        lst_h = tk.Listbox(area_h, selectmode="single", width=70, height=4,
                           bg="#0b0d12", fg=TXT, selectbackground=ACC,
                           exportselection=False,
                           font=("Segoe UI", 10))
        lst_h.pack(fill="x")
        _W._com_rolagem(lst_h)
        lbl = ttk.Label(fr, text="Busque um jogo.", style="Mut.TLabel")
        lbl.pack(anchor="w", pady=(8, 0))
        fr_btn = BarraAcoes(fr)
        fr_btn.pack(fill="x", pady=(8, 0))
        fr_btn.adicionar("Buscar", lambda: buscar())
        if fonte == "fitgirl":
            fr_btn.adicionar("Baixar no Hub", lambda: baixar_no_hub())
            fr_btn.adicionar("Abrir selecionado", lambda: abrir_link())
            fr_btn.adicionar("Abrir página", lambda: abrir())
            fr_btn.adicionar("Importar arquivo…", lambda: importar_arquivo())
        else:
            fr_btn.adicionar("⬇ Baixar p/ Meus Jogos Locais", lambda: baixar())
            fr_btn.adicionar("Abrir página", lambda: abrir())
            fr_btn.adicionar("Importar último", lambda: importar_ultimo())
        fr_btn.adicionar("Fechar", win.destroy)

        def estado(txt):
            self._depois(lambda: lbl.configure(text=txt))

        def buscar(q=None):
            termo = (q if q is not None else var_q.get()).strip()
            if not termo:
                return
            consulta["busca"] += 1
            consulta["hosts"] += 1
            meu = consulta["busca"]
            estado(f"Buscando '{termo}'…")

            def trabalho(termo_fx=termo):
                try:
                    res = cfg["buscar"](termo_fx)
                except Exception as e:
                    res = {"itens": [], "erros": [str(e)]}
                self._depois(lambda: fim_busca(res, termo_fx, meu))

            threading.Thread(target=trabalho, daemon=True).start()

        def fim_busca(res, termo, meu):
            if not win.winfo_exists() or meu != consulta["busca"]:
                return
            resultados.clear()
            resultados.extend(res.get("itens") or [])
            links.clear()
            lst_r.delete(0, "end")
            lst_h.delete(0, "end")
            for it in resultados:
                lst_r.insert("end", it["titulo"])
            if res.get("erros"):
                estado(f"Falha: {res['erros'][0]}")
            else:
                estado(f"{len(resultados)} resultado(s) p/ '{termo}'.")
                if resultados:
                    suprimir["evento"] = True
                    try:
                        lst_r.selection_set(0)
                    finally:
                        suprimir["evento"] = False
                    ver_links()

        def pagina_sel():
            sel = lst_r.curselection()
            if not sel or sel[0] >= len(resultados):
                return None
            return resultados[sel[0]]

        def ver_links(_e=None):
            if suprimir["evento"]:
                return
            pg = pagina_sel()
            consulta["hosts"] += 1
            meu = consulta["hosts"]
            links.clear()
            lst_h.delete(0, "end")
            if not pg:
                return
            estado("Consultando links…")

            def trabalho(pg_fx=pg):
                try:
                    if fonte == "fitgirl":
                        det = core.detalhes_fitgirl(pg_fx["url"])
                    else:
                        det = core.detalhes_steamrip(pg_fx["url"])
                except Exception as e:
                    det = {"erro": str(e)}

                def fim():
                    if not win.winfo_exists() or meu != consulta["hosts"]:
                        return
                    if det.get("erro"):
                        estado(f"Falha: {det['erro']}")
                        return
                    if fonte == "fitgirl":
                        for h in det.get("espelhos") or []:
                            links.append({"tipo": "espelho", **h})
                        for m in det.get("magnets") or []:
                            links.append({"tipo": "magnet",
                                          "nome": core.nome_magnet(m),
                                          "url": m})
                    else:
                        for h in det.get("hosts") or []:
                            links.append({"tipo": "host", **h})
                    for e in links:
                        if e["tipo"] == "magnet":
                            lst_h.insert("end", f"🧲 {e['nome']}")
                        else:
                            lst_h.insert("end", f"{e['nome']} — {e['url'][:70]}")
                    estado(f"{pg_fx['titulo']}: {len(links)} link(s) — "
                           "clique escolhe o host, duplo-clique baixa.")
                self._depois(fim)

            threading.Thread(target=trabalho, daemon=True).start()

        def host_sel():
            sel = lst_h.curselection()
            if sel and sel[0] < len(links) \
                    and links[sel[0]]["tipo"] != "magnet":
                return links[sel[0]]["nome"]
            return ""

        def host_feedback(_e=None):
            nome = host_sel()
            if nome:
                estado(f"via {nome} (duplo-clique baixa direto).")
            elif links:
                estado(f"{len(links)} link(s) — automático (todos).")
            else:
                estado("Sem links — busque e escolha um resultado.")

        def link_sel():
            sel = lst_h.curselection()
            if sel and sel[0] < len(links):
                return links[sel[0]]
            return None

        def baixar():
            pg = pagina_sel()
            if not pg:
                _W.messagebox.showinfo(marca, "Escolha um resultado.")
                return
            estado(f"Baixando '{pg['titulo']}'…")

            def trabalho(pg_fx=pg, host_fx=host_sel()):
                try:
                    res = core.baixar_steamrip(
                        pg_fx["url"], host=host_fx,
                        progresso=lambda f, t: estado(
                            f"Baixando: {f/1048576:.0f}/"
                            f"{t/1048576:.0f}MB" if t
                            else f"Baixando: {f/1048576:.0f}MB"))
                except Exception as e:
                    res = {"ok": False, "erro": str(e)}
                self._depois(lambda: fim_baixar(res))

            threading.Thread(target=trabalho, daemon=True).start()

        def fim_baixar(res):
            if not res.get("ok"):
                estado(f"Falha: {res.get('erro', 'falha')}")
                if fonte == "steamrip" and _W.messagebox.askyesno(
                        marca, f"{res.get('erro', 'falha')}\n\n"
                        "Links mortos no SteamRip. Tentar no FitGirl?"):
                    try:
                        termo_atual = var_q.get().strip()
                    except tk.TclError:
                        termo_atual = ""
                    self.dlg_catalogo("fitgirl", termo_atual)
                    return
                _W.messagebox.showwarning(marca, res.get("erro", "falha"))
                return
            self._sr_ultimo = res["path"]
            estado(f"Em Meus Jogos Locais/: {Path(res['path']).name}")
            if _W.messagebox.askyesno(marca,
                                   "Baixado. Importar para o Hub agora?"):
                importar_ultimo()

        def abrir():
            pg = pagina_sel()
            if not pg:
                return
            r = core.abrir_url(pg["url"])
            if not r.get("ok"):
                _W.messagebox.showwarning(marca, r.get("erro", "falha"))

        def abrir_link():
            e = link_sel()
            if not e:
                _W.messagebox.showinfo(marca, "Escolha um espelho ou magnet.")
                return
            r = core.abrir_url(e["url"])
            if r.get("ok"):
                estado(f"Aberto: {e['nome'][:60]}")
            else:
                _W.messagebox.showwarning(marca, r.get("erro", "falha"))

        def baixar_no_hub():
            e = link_sel()
            if not e or not str(e.get("url") or "").startswith("magnet:?"):
                _W.messagebox.showinfo(marca, "Escolha um magnet p/ baixar no Hub.")
                return
            estado("Adicionando no qBittorrent do Hub (Meus Jogos Locais/)…")

            def trabalho(url_fx=e["url"]):
                try:
                    res = core.qbit_adicionar(url_fx)
                except Exception as ex:
                    res = {"ok": False, "erro": str(ex)}
                self._depois(lambda: fim_hub(res))

            threading.Thread(target=trabalho, daemon=True).start()

        def fim_hub(res):
            if res.get("ok"):
                estado(f"No Hub → {res.get('destino', 'Meus Jogos Locais/')}")
                _W.messagebox.showinfo(marca, f"Torrent no cliente do Hub.\nDestino: {res.get('destino', 'Meus Jogos Locais/')}")
            else:
                estado(f"Falha: {res.get('erro', 'falha')}")
                _W.messagebox.showwarning(marca, res.get("erro", "falha"))

        def importar_arquivo():
            try:
                from bib_nucleo.rede.repacks import pasta_jogos
                ini = str(pasta_jogos())
            except Exception:
                ini = ""
            arq = filedialog.askopenfilename(
                title="Repack baixado (.rar/.zip/.7z/.iso)", parent=win,
                initialdir=ini or None,
                filetypes=[("Repacks", "*.rar *.zip *.7z *.iso"),
                           ("Todos", "*.*")]) or ""
            if arq:
                importar_ultimo(arq)

        def importar_ultimo(arq=None):
            if arq is None:
                arq = getattr(self, "_sr_ultimo", "")
            if not arq or not Path(arq).is_file():
                _W.messagebox.showinfo(marca, "Nada baixado ainda.")
                return
            estado("Importando…")

            def trabalho(arq_fx=arq):
                con = None
                try:
                    self._backup_pre_import()
                    con = self._con()
                    res = core.importar_repack(con, arq_fx)
                except Exception as e:
                    res = {"ok": False, "erro": str(e)}
                finally:
                    try:
                        if con is not None:
                            con.close()
                    except Exception:
                        pass
                self._depois(lambda: fim_imp(res))

            threading.Thread(target=trabalho, daemon=True).start()

        def fim_imp(res):
            if res.get("ok"):
                self.recarregar()
                estado("Importado ✓")
                _W.messagebox.showinfo(marca, "Jogo importado ✓")
            else:
                estado(f"Falha: {res.get('erro', 'falha')}")
                _W.messagebox.showwarning(marca, res.get("erro", "falha"))

        lst_r.bind("<<ListboxSelect>>", ver_links)
        lst_h.bind("<<ListboxSelect>>", host_feedback)
        if fonte == "fitgirl":
            lst_r.bind("<Double-Button-1>", lambda _e: abrir())
            lst_h.bind("<Double-Button-1>", lambda _e: abrir_link())
        else:
            lst_r.bind("<Double-Button-1>", lambda _e: baixar())
            lst_h.bind("<Double-Button-1>", lambda _e: baixar())
        ent.focus_set()
        if (termo or "").strip():
            var_q.set(termo.strip())
            buscar(termo.strip())
