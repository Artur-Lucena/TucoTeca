#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca terminal: MixMenus de Tui (verbatim do modulo original)."""
from __future__ import annotations

from pathlib import Path
from queue import Empty

import bib_core as core


class MixMenus:
    def menu_mods(self, j):
        """Gerenciar mods LayeredFS (só ROM 3DS com title ID legível)."""
        try:
            launch = core.traduzir_para_atual((j.get("launch_options") or "").strip())
            tid = core.title_id_da_rom(launch)
        except Exception:
            tid = ""
        if not tid:
            self.msg = "Mods só para ROMs 3DS com title ID legível."
            return
        con = self._con()
        try:
            while True:
                row = con.execute("SELECT * FROM jogos WHERE id=?",
                                  (j["id"],)).fetchone()
                if row is None:
                    self.msg = "Jogo sumido."
                    return
                atual = core.row_to_dict(row)
                ativos = set(atual.get("mods_lista") or [])
                off = bool(atual.get("azahar_mods_off"))
                try:
                    disp = core.listar_mods(tid)
                except Exception:
                    disp = []
                estado = "Mods: DESLIGADOS (alternar)" if off else "Mods: ligados (alternar)"
                opcoes = ([estado]
                          + [f"[{'x' if m in ativos else ' '}] {m}" for m in disp]
                          + ["Adicionar mod…", "Remover mod…", "Voltar"])
                idx = self.escolher(f"Mods — {j.get('titulo') or ''}", opcoes)
                if idx is None or opcoes[idx] == "Voltar":
                    self.recarregar()
                    return
                escolha = opcoes[idx]
                if escolha == estado:
                    core.atualizar_jogo(con, j["id"],
                                        {"azahar_mods_off": 0 if off else 1})
                    self.msg = ("Mods ligados ✓" if off
                                else "Mods desligados (lista preservada).")
                elif escolha == "Adicionar mod…":
                    r = self.perguntar("Arquivo (.zip/.7z) ou pasta do mod: ")
                    if not r:
                        continue
                    nome = self.perguntar("Nome do mod (vazio=automático): ")
                    if nome is None:
                        continue
                    res = core.importar_mod(r.strip(), tid, (nome or "").strip())
                    if not res.get("ok"):
                        self.msg = f"Falha: {res.get('erro')}"
                        continue
                    nova = [m for m in disp if m in ativos] + [res["mod"]]
                    core.atualizar_jogo(con, j["id"], {"azahar_mods": nova})
                    self.msg = f"Mod {res['mod']} ✓ ({res['arquivos']} arqs)"
                elif escolha == "Remover mod…":
                    if not disp:
                        self.msg = "Nada para remover."
                        continue
                    idx2 = self.escolher("Remover", [*disp, "Voltar"])
                    if idx2 is None or idx2 >= len(disp):
                        continue
                    alvo = disp[idx2]
                    conf = self.perguntar(f"Apagar '{alvo}' da biblioteca? (s/n): ")
                    if (conf or "").strip().lower() not in ("s", "sim"):
                        continue
                    res = core.remover_mod(tid, alvo)
                    if not res.get("ok"):
                        self.msg = f"Falha: {res.get('erro')}"
                        continue
                    core.atualizar_jogo(
                        con, j["id"],
                        {"azahar_mods": [m for m in ativos if m != alvo]})
                    self.msg = f"Mod {alvo} removido."
                else:
                    pos = next((i for i, m in enumerate(disp)
                                if f"[{'x' if m in ativos else ' '}] {m}" == escolha), None)
                    if pos is None:
                        continue
                    nome = disp[pos]
                    nova = ([m for m in disp if m in ativos and m != nome]
                            + ([nome] if nome not in ativos else []))
                    core.atualizar_jogo(con, j["id"], {"azahar_mods": nova})
        finally:
            con.close()
    def menu_texturas(self, j):
        """Liga/desliga texturas HD (só ROM 3DS com title ID legível)."""
        try:
            launch = core.traduzir_para_atual((j.get("launch_options") or "").strip())
            tid = core.title_id_da_rom(launch)
        except Exception:
            tid = ""
        if not tid:
            self.msg = "Texturas só para ROMs 3DS com title ID legível."
            return
        while True:
            try:
                est = core.estado_textura(tid)
            except Exception:
                est = {"instalado": False, "ativo": False,
                       "arquivos": 0, "mb": 0.0}
            if not est.get("instalado"):
                opcoes = ["Instalar de pasta…", "Voltar"]
            else:
                acao = ("DESLIGAR" if est["ativo"] else "LIGAR")
                opcoes = [f"HD {acao} ({est['arquivos']} arqs)",
                          "Instalar de pasta…", "Voltar"]
            idx = self.escolher(f"Texturas — {j.get('titulo') or ''}", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                self.recarregar()
                return
            escolha = opcoes[idx]
            if escolha == "Instalar de pasta…":
                r = self.perguntar("Pasta extraída com os .png: ")
                if not r:
                    continue
                res = core.instalar_textura(tid, r.strip())
                self.msg = (f"HD instalado ✓ ({res['arquivos']} arqs)"
                            if res.get("ok") else f"Falha: {res.get('erro')}")
            else:
                res = core.definir_textura(tid, not est["ativo"])
                self.msg = (f"HD {'ligado ✓' if res.get('ativo') else 'desligado.'}"
                            if res.get("ok") else f"Falha: {res.get('erro')}")
    def menu_cheats(self, j):
        """Liga/desliga cheats Gateway (vale após reiniciar o jogo)."""
        try:
            launch = core.traduzir_para_atual((j.get("launch_options") or "").strip())
            tid = core.title_id_da_rom(launch)
        except Exception:
            tid = ""
        if not tid:
            self.msg = "Cheats só para ROMs 3DS com title ID legível."
            return
        while True:
            try:
                disp = core.listar_cheats(tid)
            except Exception:
                disp = []
            ativos = {c["nome"] for c in disp if c["ativo"]}
            opcoes = ([f"[{'x' if c['nome'] in ativos else ' '}] {c['nome']}"
                       for c in disp]
                      + ["Adicionar cheat…", "Remover cheat…", "Voltar"])
            idx = self.escolher(f"Cheats — {j.get('titulo') or ''} (reinicie p/ valer)",
                                opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                self.recarregar()
                return
            escolha = opcoes[idx]
            if escolha == "Adicionar cheat…":
                nome = self.perguntar("Nome do cheat: ")
                if not nome:
                    continue
                linhas = []
                while True:
                    digitado = self.perguntar(f"Linha {len(linhas) + 1} (vazio termina): ")
                    if digitado is None or not digitado.strip():
                        break
                    linhas.append(digitado)
                if not linhas:
                    continue
                res = core.adicionar_cheat(tid, nome.strip(), "\n".join(linhas))
                self.msg = (f"Cheat {nome.strip()} ✓ (desligado)"
                            if res.get("ok") else f"Falha: {res.get('erro')}")
            elif escolha == "Remover cheat…":
                if not disp:
                    self.msg = "Nada para remover."
                    continue
                idx2 = self.escolher("Remover", [c["nome"] for c in disp]
                                     + ["Voltar"])
                if idx2 is None or idx2 >= len(disp):
                    continue
                alvo = disp[idx2]["nome"]
                conf = self.perguntar(f"Apagar '{alvo}'? (s/n): ")
                if (conf or "").strip().lower() not in ("s", "sim"):
                    continue
                res = core.remover_cheat(tid, alvo)
                self.msg = (f"Cheat {alvo} removido."
                            if res.get("ok") else f"Falha: {res.get('erro')}")
            else:
                pos = next((i for i, c in enumerate(disp)
                            if f"[{'x' if c['nome'] in ativos else ' '}] {c['nome']}"
                            == escolha), None)
                if pos is None:
                    continue
                res = core.alternar_cheat(tid, disp[pos]["nome"])
                self.msg = (f"{disp[pos]['nome']}: "
                            f"{'ligado ✓ (reinicie)' if res.get('ativo') else 'desligado.'}"
                            if res.get("ok") else f"Falha: {res.get('erro')}")
    def menu_principal(self) -> bool:
        """ESC na lista abre as categorias; retorna True se é para sair."""
        opcoes = ["Buscar", "Filtros", "Adicionar jogo", "Importar",
                  "Músicas", "Desejos", "Downloads", "Controles", "Backup e saves", "Sessão",
                  "Emuladores", "Sair"]
        while True:
            idx = self.escolher("TucoTeca", opcoes)
            if idx is None:
                return False
            escolha = opcoes[idx]
            if escolha == "Buscar":
                r = self.perguntar("Buscar: ", self.q)
                if r is not None:
                    self.q = r.strip()
                    self.cur = 0
                    self.recarregar()
            elif escolha == "Filtros":
                self.menu_filtros()
            elif escolha == "Adicionar jogo":
                self.adicionar()
            elif escolha == "Importar":
                self.menu_importar()
            elif escolha == "Músicas":
                self.menu_musicas()
            elif escolha == "Desejos":
                self.menu_desejos()
            elif escolha == "Downloads":
                self.menu_downloads()
            elif escolha == "Controles":
                self.menu_controles()
            elif escolha == "Backup e saves":
                self.menu_backup()
            elif escolha == "Sessão":
                self.menu_sessao()
            elif escolha == "Emuladores":
                self.menu_emuladores()
            elif escolha == "Sair":
                return True
        return False
    def menu_musicas(self):
        """Catálogo de áudio: buscar, tocar, importar, excluir."""
        con = self._con()
        try:
            q = ""
            while True:
                self._vigiar_player()
                try:
                    itens = core.listar_musicas(con, q=q)
                except Exception:
                    itens = []
                try:
                    at = self.player.atual() if self.player else None
                except Exception:
                    at = None
                titulo = f"Músicas ({len(itens)})"
                if at and (self.player.estado if self.player else "") != "parado":
                    titulo += f" · ♪ {at.get('titulo') or ''}"
                rotulos = [core.texto_musica(m) for m in itens]
                try:
                    n_fila = len(core.listar_downloads(con))
                except Exception:
                    n_fila = 0
                opcoes = (rotulos + ["Buscar…", "Importar de pasta…",
                                     "Baixar de CSV…", f"Fila ({n_fila})…",
                                     "Baixar capas…", "Dependências de áudio…",
                                     "Voltar"])
                idx = self.escolher(titulo, opcoes)
                if idx is None or opcoes[idx] == "Voltar":
                    self.recarregar()
                    return
                escolha = opcoes[idx]
                if escolha == "Buscar…":
                    r = self.perguntar("Buscar música: ", q)
                    if r is not None:
                        q = r.strip()
                elif escolha == "Importar de pasta…":
                    sugest = ""
                    try:
                        sugest = (str(core.harmoni_dir() or "")
                                  or str(core.sugestao_harmoni_dir() or ""))
                    except Exception:
                        pass
                    r = self.perguntar("Pasta de áudio"
                                       + (f" [{sugest}]: " if sugest else ": "))
                    if r is None:
                        continue
                    pasta = (r.strip() or sugest)
                    if not pasta:
                        continue
                    self._backup_pre_import()
                    try:
                        res = core.importar_musicas(con, pasta)
                    except Exception as e:
                        res = {"novos": 0, "ignorados": 0, "erros": [str(e)]}
                    detalhe = (f"{res['novos']} nova(s), "
                               f"{res['ignorados']} ignorada(s)")
                    if res["erros"]:
                        detalhe += f" — {res['erros'][0]}"
                    self.msg = detalhe
                elif escolha == "Baixar de CSV…":
                    r = self.perguntar("CSV do Exportify: ")
                    if r is None or not r.strip():
                        continue
                    try:
                        parsed = core.ler_csv_exportify(r.strip())
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    if parsed["erros"] and not parsed["itens"]:
                        self.msg = f"Falha: {parsed['erros'][0]}"
                        continue
                    try:
                        res = core.enfileirar_downloads(con, parsed["itens"])
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    self.msg = (f"{res['novos']} na fila,"
                                f" {res['ignorados']} ignorada(s)")
                elif idx >= len(itens) and escolha.startswith("Fila ("):
                    self.menu_fila(con)
                elif idx >= len(itens) and escolha == "Baixar capas…":
                    try:
                        res = core.baixar_capas_faltantes(con)
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    self.msg = (f"{res['novas']} capa(s),"
                                f" {res['pendentes']} pendente(s)")
                    if res["erros"]:
                        self.msg += f" — {res['erros'][0]}"
                elif idx >= len(itens) and escolha == "Dependências de áudio…":
                    ff_ok = bool(core.ffmpeg_pronto())
                    yt_ok = bool(core.ytdlp_pronto())
                    if ff_ok and yt_ok:
                        self.msg = "ffmpeg ✓ · yt-dlp ✓"
                        continue
                    falta = " e ".join(
                        x for x, ok in (("ffmpeg (~80MB)", ff_ok),
                                        ("yt-dlp (~30MB)", yt_ok)) if not ok)
                    conf = self.perguntar(f"Baixar {falta} do oficial? (s/n): ")
                    if (conf or "").strip().lower() not in ("s", "sim"):
                        continue
                    msgs = []
                    if not ff_ok:
                        try:
                            r = core.instalar_ffmpeg()
                            msgs.append("ffmpeg ✓" if r.get("ok")
                                        else f"ffmpeg: {r.get('erro')}")
                        except Exception as e:
                            msgs.append(f"ffmpeg: {e}")
                    if not yt_ok:
                        try:
                            r = core.instalar_ytdlp()
                            msgs.append("yt-dlp ✓" if r.get("ok")
                                        else f"yt-dlp: {r.get('erro')}")
                        except Exception as e:
                            msgs.append(f"yt-dlp: {e}")
                    self.msg = " · ".join(msgs)
                else:
                    pos = idx
                    if 0 <= pos < len(itens):
                        sub = self.escolher(
                            rotulos[pos],
                            ["Tocar", "Pausar/Continuar", "Próxima", "Parar",
                             "Abrir externo", "Excluir", "Voltar"])
                        if sub == 0:
                            r = self._tocar_interno(itens, pos)
                            self.msg = (f"Tocando '{rotulos[pos]}' ✓"
                                        if r.get("ok")
                                        else f"Falha: {r.get('erro')}")
                        elif sub == 1:
                            r = self._alternar_interno()
                            self.msg = (f"{r.get('estado', 'ok')} ✓"
                                        if r.get("ok")
                                        else f"Falha: {r.get('erro')}")
                        elif sub == 2:
                            r = self._proxima_interno()
                            self.msg = (f"Tocando '{r.get('titulo')}' ✓"
                                        if r.get("ok")
                                        else "Fim da fila.")
                        elif sub == 3:
                            self._parar_interno()
                            self.msg = "Parado."
                        elif sub == 4:
                            self._parar_interno()
                            r = core.tocar_musica(itens[pos].get("musica_path") or "")
                            self.msg = (f"Tocando '{rotulos[pos]}' no player ✓"
                                        " (segue com o jogo aberto)"
                                        if r.get("ok")
                                        else f"Falha: {r.get('erro')}")
                        elif sub == 5:
                            conf = self.perguntar(
                                f"Apagar '{rotulos[pos]}' do Hub? (s/n): ")
                            if (conf or "").strip().lower() in ("s", "sim"):
                                try:
                                    core.excluir_musica(con, itens[pos]["id"])
                                    self.msg = "Música apagada."
                                except (LookupError, ValueError) as e:
                                    self.msg = f"Falha: {e}"
                                    continue
                                try:
                                    at = self.player.atual() \
                                        if self.player else None
                                    if at and at.get("path") == (
                                            itens[pos].get("musica_path")
                                            or ""):
                                        self._parar_interno()
                                except Exception:
                                    pass
        finally:
            con.close()
    def menu_fila(self, con):
        """Fila CSV → mp3: estados + limpar (download vem na Fase B)."""
        while True:
            try:
                fila = core.listar_downloads(con)
            except Exception:
                fila = []
            rotulos = []
            for d in fila:
                base = core.texto_musica(d)
                est = d.get("estado") or ""
                extra = (f" — {d.get('erro')}"
                         if est == "falha" and d.get("erro") else "")
                rotulos.append(f"{base} [{est}]{extra}")
            opcoes = rotulos + ["Baixar fila", "Importar baixadas",
                                 "Limpar prontas/falhas", "Voltar"]
            idx = self.escolher(f"Fila ({len(fila)})", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            if opcoes[idx] == "Baixar fila":
                if not core.localizar_ytdlp():
                    self.msg = core.erro_sem_ytdlp()
                    continue
                alvos = [d for d in fila
                         if d.get("estado") in ("pendente", "falha")]
                if not alvos:
                    self.msg = "Nada pendente."
                    continue
                ok = 0
                for d in alvos:
                    self.msg = f"Baixando {core.texto_musica(d)}…"
                    try:
                        r = core.baixar_faixa(con, d["id"])
                    except Exception as e:
                        r = {"ok": False, "erro": str(e)}
                    ok += 1 if r.get("ok") else 0
                self.msg = f"Baixadas {ok}/{len(alvos)} (Fase C importa)."
                continue
            if opcoes[idx] == "Importar baixadas":
                self._backup_pre_import()
                try:
                    res = core.importar_fila_pronta(con)
                except Exception as e:
                    self.msg = f"Falha: {e}"
                    continue
                self.msg = (f"{res['novas']} nova(s),"
                            f" {res['ignoradas']} ignorada(s)")
                if res["erros"]:
                    self.msg += f" — {res['erros'][0]}"
                continue
            if opcoes[idx] == "Limpar prontas/falhas":
                try:
                    n = core.limpar_downloads(con)
                except ValueError as e:
                    self.msg = f"Falha: {e}"
                    continue
                self.msg = f"Fila limpa ({n} removida(s))."
                continue
            pos = idx
            if 0 <= pos < len(fila):
                d = fila[pos]
                det = " · ".join(x for x in (
                    core.texto_musica(d), d.get("estado") or "",
                    d.get("video_id") or "", d.get("erro") or "") if x)
                self.msg = det
    def menu_desejos(self):
        """Wishlist Steam espelhada: sincronizar, buscar p/ baixar, remover."""
        con = self._con()
        try:
            while True:
                try:
                    itens = core.listar_desejos(con)
                except Exception:
                    itens = []
                rotulos = [d["titulo"] for d in itens]
                opcoes = (rotulos + ["🔄 Sincronizar", "➕ Adicionar…",
                                     "🌐 Wishlist na Steam",
                                     "📄 Arquivo…",
                                     "🔎 Buscar p/ baixar",
                                     "🗑 Remover", "Voltar"])
                idx = self.escolher(f"Desejos ({len(itens)})", opcoes)
                if idx is None or opcoes[idx] == "Voltar":
                    self.recarregar()
                    return
                escolha = opcoes[idx]
                if escolha == "🔄 Sincronizar":
                    try:
                        conta = core.steam_principal()
                        if not conta:
                            self.msg = ("Conta Steam não achada neste PC "
                                        "(BIBLIOTECA_STEAM_ID?).")
                            continue
                        leitura = core.ler_wishlist(conta["steamid"])
                        if leitura["erros"]:
                            self.msg = f"Falha: {leitura['erros'][0]}"
                            continue
                        self._backup_pre_import()
                        res = core.sincronizar_desejos(con, leitura["itens"])
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    self.msg = (f"{res['novos']} novo(s), "
                                f"{res['atualizados']} atualizado(s), "
                                f"{res['removidos']} removido(s)")
                    continue
                if escolha == "➕ Adicionar…":
                    termo = self.perguntar("Buscar na Steam: ", "")
                    if not (termo or "").strip():
                        continue
                    try:
                        busca = core.buscar_jogos_steam(termo.strip())
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    if busca["erros"] and not busca["itens"]:
                        self.msg = f"Falha: {busca['erros'][0]}"
                        continue
                    pos = self._escolher_item(
                        "Adicionar qual?",
                        [d["titulo"] for d in busca["itens"]])
                    if pos is None:
                        continue
                    try:
                        self._backup_pre_import()
                        core.adicionar_desejo(con, busca["itens"][pos]["appid"],
                                              busca["itens"][pos]["titulo"])
                    except (ValueError, LookupError) as e:
                        self.msg = f"Falha: {e}"
                        continue
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    self.msg = (f"Desejo '{busca['itens'][pos]['titulo']}' ✓")
                    continue
                if escolha == "🌐 Wishlist na Steam":
                    conta = core.steam_principal()
                    if not conta:
                        self.msg = ("Conta Steam não achada neste PC "
                                    "(BIBLIOTECA_STEAM_ID?).")
                        continue
                    url = ("https://store.steampowered.com/wishlist/profiles/"
                           f"{conta['steamid']}/")
                    core.abrir_url(url)
                    self.msg = ("Confira a wishlist na Steam; use Adicionar "
                                "ou importe um JSON exportado para alimentar o Hub.")
                    continue
                if escolha == "📄 Arquivo…":
                    caminho = self.perguntar("JSON da wishlist: ", "")
                    if not (caminho or "").strip():
                        continue
                    try:
                        leitura = core.ler_wishlist_arquivo(caminho.strip())
                        if leitura["erros"] and not leitura["itens"]:
                            self.msg = f"Falha: {leitura['erros'][0]}"
                            continue
                        self._backup_pre_import()
                        res = core.sincronizar_desejos(con, leitura["itens"])
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    self.msg = (f"{res['novos']} novo(s), "
                                f"{res['atualizados']} atualizado(s), "
                                f"{res['removidos']} removido(s)")
                    continue
                if escolha == "🔎 Buscar p/ baixar":
                    pos = self._escolher_item(
                        "Buscar qual desejo?",
                        [d["titulo"] for d in itens])
                    if pos is None:
                        continue
                    self.menu_desejo_fontes(itens[pos])
                    continue
                if escolha == "🗑 Remover":
                    pos = self._escolher_item(
                        "Remover qual desejo?",
                        [d["titulo"] for d in itens])
                    if pos is None:
                        continue
                    if not self.confirmar(f"Tirar '{itens[pos]['titulo']}'?"):
                        continue
                    try:
                        core.remover_desejo(con, itens[pos]["id"])
                        self.msg = "Desejo removido."
                    except LookupError as e:
                        self.msg = f"Falha: {e}"
                    continue
        finally:
            con.close()
    def menu_downloads(self):
        """% dos torrents do qBittorrent + importar concluídos."""
        con = self._con()
        try:
            while True:
                try:
                    leitura = core.listar_torrents()
                    dls = leitura.get("torrents") or []
                except Exception:
                    dls = []
                rotulos = [f"{'✓ ' if t['completo'] else ''}{t['nome']} · "
                           f"{t['pct']}% ({core.formatar_tamanho(t['feito'])}/"
                           f"{core.formatar_tamanho(t['total'])})" for t in dls]
                opcoes = (rotulos + ["✅ Verificar concluídos", "Voltar"])
                idx = self.escolher(f"Downloads ({len(dls)})", opcoes)
                if idx is None or opcoes[idx] == "Voltar":
                    self.recarregar()
                    return
                escolha = opcoes[idx]
                if escolha == "✅ Verificar concluídos":
                    prontos = [t for t in dls if t.get("completo")
                               and t.get("save_path")]
                    if not prontos:
                        self.msg = "Nada 100% ainda."
                        continue
                    try:
                        self._backup_pre_import()
                        linhas = []
                        for t in prontos:
                            alvo = Path(t["save_path"])
                            try:
                                if alvo.is_file() and alvo.suffix.lower() in (
                                        ".rar", ".zip", ".7z", ".iso"):
                                    res = core.importar_repack(con, str(alvo))
                                    linhas.append(f"'{res.get('titulo', t['nome'])}'"
                                                   + (" ✓" if res.get("ok")
                                                      else f": {res.get('erro')}"))
                                elif alvo.is_dir():
                                    _r, itens, _i = core.preview_pasta([str(alvo)])
                                    if not itens:
                                        linhas.append(f"'{t['nome']}': sem jogo")
                                        continue
                                    res = core.importar_lista(con, itens)
                                    linhas.append(f"'{t['nome']}': +{res.get('novos', 0)}")
                                else:
                                    linhas.append(f"'{t['nome']}': sumiu do disco")
                            except Exception as e:
                                linhas.append(f"'{t['nome']}': {e}")
                    except Exception as e:
                        self.msg = f"Falha: {e}"
                        continue
                    self.msg = "; ".join(linhas[:4]) or "Nada importado."
                    self.recarregar()
                    continue
                # escolha direta na lista = detalhe (pasta + %)
                if idx < len(dls):
                    t = dls[idx]
                    self.msg = (f"{t['nome']} · {t['pct']}% · "
                                f"Pasta: {t.get('save_path') or '?'}")
                continue
        finally:
            con.close()
    def _escolher_item(self, titulo, rotulos):
        """Índice do item ou None (Voltar/cancelar)."""
        if not rotulos:
            self.msg = "Lista vazia."
            return None
        idx = self.escolher(titulo, rotulos + ["Voltar"])
        if idx is None or idx >= len(rotulos):
            return None
        return idx
    def menu_desejo_fontes(self, desejo):
        """Busca o título nas fontes e entrega (download ou abertura)."""
        try:
            sr = core.buscar_steamrip(desejo["titulo"])
        except Exception as e:
            sr = {"itens": [], "erros": [str(e)]}
        try:
            fg = core.buscar_fitgirl(desejo["titulo"])
        except Exception as e:
            fg = {"itens": [], "erros": [str(e)]}
        opcoes = ([f"SteamRip: {i['titulo']}" for i in sr.get("itens") or []]
                  + [f"FitGirl: {i['titulo']}" for i in fg.get("itens") or []]
                  + ["Abrir na Steam", "Voltar"])
        if sr.get("erros") and fg.get("erros"):
            self.msg = f"Falha: {sr['erros'][0]}"
        idx = self.escolher(f"Baixar '{desejo['titulo']}'", opcoes)
        if idx is None or idx >= len(opcoes) - 2:
            if idx == len(opcoes) - 2:
                self.msg = f"Abra: https://store.steampowered.com/app/{desejo['appid']}/"
            return
        n_sr = len(sr.get("itens") or [])
        if idx < n_sr:
            self._desejo_steamrip((sr["itens"] or [])[idx])
        else:
            pg = (fg["itens"] or [])[idx - n_sr]
            self._desejo_fitgirl(pg)
    def _desejo_steamrip(self, pg):
        try:
            det = core.detalhes_steamrip(pg["url"])
        except ValueError as e:
            self.msg = f"Falha: {e}"
            return
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        hosts = det.get("hosts") or []
        ops = ([h["nome"] for h in hosts]
               + ["Automático", "Abrir página (URL)", "Voltar"])
        h = self.escolher(pg["titulo"], ops)
        if h is None or h >= len(ops) - 2:
            if h == len(ops) - 2:
                self.msg = f"Abra: {pg['url']}"
            return
        host = "" if ops[h] == "Automático" else hosts[h]["nome"] \
            if h < len(hosts) else ""
        self.msg = f"Baixando '{pg['titulo']}'…"
        try:
            res = core.baixar_steamrip(pg["url"], host=host)
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        if not res.get("ok"):
            self.msg = f"Falha: {res.get('erro')}"
            return
        self.msg = f"Em Meus Jogos Locais/: {Path(res['path']).name}"
        if self.confirmar("Importar para o Hub agora?"):
            self._importar_arquivo(res["path"])
    def _desejo_fitgirl(self, pg):
        try:
            det = core.detalhes_fitgirl(pg["url"])
        except ValueError as e:
            self.msg = f"Falha: {e}"
            return
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        links = ([{"tipo": "espelho", **h} for h in det.get("espelhos") or []]
                 + [{"tipo": "magnet", "nome": core.nome_magnet(m), "url": m}
                    for m in det.get("magnets") or []])
        if not links:
            self.msg = "Post sem espelhos nem magnets."
            return
        rotulos = [f"🧲 {e['nome']}" if e["tipo"] == "magnet"
                   else f"{e['nome']} — {e['url'][:60]}" for e in links]
        h = self.escolher(pg["titulo"],
                          rotulos + ["Abrir página (URL)",
                                     "Importar arquivo…", "Voltar"])
        if h is None or h >= len(rotulos + ["Abrir página (URL)",
                                            "Importar arquivo…"]):
            return
        if h < len(links):
            e = links[h]
            if e["tipo"] == "magnet":
                r = core.qbit_adicionar(e["url"])
                self.msg = (f"No Hub → {r.get('destino', 'Meus Jogos Locais/')}"
                            if r.get("ok") else f"Falha: {r.get('erro')}")
            else:
                r = core.abrir_url(e["url"])
                self.msg = (f"Aberto: {e['nome'][:60]}"
                            if r.get("ok") else f"Falha: {r.get('erro')}")
            return
        if h == len(links) + 1:
            arq = self.perguntar("Repack baixado (.rar/.zip/.7z/.iso): ")
            if arq and arq.strip():
                self._importar_arquivo(arq.strip())
            return
        self.msg = f"Abra: {pg['url']}"
    def menu_controles(self):
        """Controles no Hub: listar, testar, fotografar, aplicar, gerar."""
        import time
        while True:
            try:
                pads = core.listar_controles()
            except Exception:
                pads = []
            try:
                presets = core.listar_presets_controle()
            except Exception:
                presets = []
            info = "; ".join(
                f"{p.get('nome') or '?'}"
                f"{' [' + p['familia'] + ']' if p.get('familia') else ''}"
                for p in pads) or "nenhum controle"
            if len(info) > 100:
                info = info[:99] + "…"
            opcoes = [f"Pads: {info}", "Testar apertos (5s)…",
                      "Fotografar perfil do Azahar…", "Aplicar preset…",
                      "Gerar mapa padrão…", "Voltar"]
            idx = self.escolher("Controles (feche o Azahar p/ aplicar)",
                                opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                self.recarregar()
                return
            escolha = opcoes[idx]
            if escolha.startswith("Pads:"):
                continue
            if escolha.startswith("Testar"):
                vistos: set[str] = set()
                t0 = time.monotonic()
                while time.monotonic() - t0 < 5:
                    try:
                        est = core.ler_estado_xinput(0)
                    except Exception:
                        est = None
                    if est:
                        try:
                            vistos.add(core.resumir_estado(est))
                        except Exception:
                            pass
                    time.sleep(0.1)
                vistos.discard("(neutro)")
                self.msg = ("Vistos: " + " | ".join(sorted(vistos))
                            if vistos else "Nada apertado (XInput slot 0).")
            elif escolha.startswith("Fotografar"):
                nome = self.perguntar("Nome do preset: ")
                if not nome:
                    continue
                try:
                    res = core.fotografar_perfil(nome.strip())
                except Exception as e:
                    res = {"ok": False, "erro": str(e)}
                self.msg = (f"Preset {res['preset']} ✓" if res.get("ok")
                            else f"Falha: {res.get('erro')}")
            elif escolha.startswith("Aplicar"):
                if not presets:
                    self.msg = "Sem presets (fotografe ou gere um)."
                    continue
                idx2 = self.escolher("Aplicar", presets + ["Voltar"])
                if idx2 is None or idx2 >= len(presets):
                    continue
                try:
                    res = core.aplicar_preset_controle(presets[idx2])
                except Exception as e:
                    res = {"ok": False, "erro": str(e)}
                self.msg = (f"{res.get('chaves', 0)} binds no Azahar ✓"
                            if res.get("ok")
                            else f"Falha: {res.get('erro')}")
            elif escolha.startswith("Gerar"):
                try:
                    tipos = sorted(core.NOMES_TIPO.items())
                except Exception:
                    continue
                rot = [f"{t} — {core.NOMES_TIPO[t]}" for t, _ in tipos]
                idx2 = self.escolher("Tipo", rot + ["Voltar"])
                if idx2 is None or idx2 >= len(tipos):
                    continue
                tipo = tipos[idx2][0]
                guid, port, rotulos = "", 0, {}
                try:
                    det = core.detectar_sdl()
                    if det:
                        guid, port = det[0]["guid"], det[0]["port"]
                    rotulos = core.nomes_sdl()
                except Exception:
                    pass
                try:
                    res = core.salvar_mapa_gerado(
                        tipo, guid=guid, port=port, nome=f"{tipo}-hub",
                        rotulos=rotulos)
                except ValueError as e:
                    res = {"ok": False, "erro": str(e)}
                if not res.get("ok"):
                    self.msg = f"Falha: {res.get('erro')}"
                    continue
                self.msg = (f"Preset {res['preset']} ✓ "
                            f"({res['chaves']} binds) — aplique p/ usar.")
    def menu_filtros(self):
        while True:
            opcoes = [
                f"Status: {self.statuses[self.si] or 'todos'}",
                f"Favoritos: {'sim' if self.fav else 'não'}",
                f"Provider: {self.filtro_prov or 'todos'}",
                f"Plataforma: {self.filtro_plat or 'todas'}",
                f"Etiquetas: {', '.join(self.filtro_tags) or '—'}",
                "Limpar filtros",
                "Voltar",
            ]
            idx = self.escolher("Filtros", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            escolha = opcoes[idx]
            if escolha.startswith("Status:"):
                self.si = (self.si + 1) % len(self.statuses)
                self.cur = 0
                self.recarregar()
            elif escolha.startswith("Favoritos:"):
                self.fav = not self.fav
                self.cur = 0
                self.recarregar()
            elif escolha.startswith("Provider:"):
                chaves = [None, *core.provedores()]
                i = chaves.index(self.filtro_prov) if self.filtro_prov in chaves else 0
                self.filtro_prov = chaves[(i + 1) % len(chaves)]
                self.cur = 0
                self.recarregar()
                self.msg = f"Filtro prov: {self.filtro_prov or 'todos'}."
            elif escolha.startswith("Plataforma:"):
                plats = [None, "PC", "3DS", "NDS"]
                i = plats.index(self.filtro_plat) if self.filtro_plat in plats else 0
                self.filtro_plat = plats[(i + 1) % len(plats)]
                self.cur = 0
                self.recarregar()
                self.msg = f"Filtro plataforma: {self.filtro_plat or 'todas'}."
            elif escolha.startswith("Etiquetas:"):
                r = self.perguntar("Filtrar etiquetas (vírgula=vazio limpa): ",
                                   ", ".join(self.filtro_tags))
                if r is not None:
                    self.filtro_tags = [t.strip() for t in
                                        r.replace(";", ",").split(",") if t.strip()]
                    self.cur = 0
                    self.recarregar()
            elif escolha == "Limpar filtros":
                self.si = 0
                self.fav = False
                self.filtro_prov = None
                self.filtro_plat = None
                self.filtro_tags = []
                self.cur = 0
                self.recarregar()
                self.msg = "Filtros limpos."
    def menu_importar(self):
        opcoes = ["Arquivo (exe, ROM, JSON, .zip, repack)", "Pasta", "Sanear pasta…", "Disco (Hydra/lojas)",
                  "Catálogo SteamRip", "Catálogo FitGirl", "Voltar"]
        while True:
            idx = self.escolher("Importar", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            escolha = opcoes[idx]
            if escolha.startswith("Arquivo"):
                arq = self.perguntar("Arquivo (exe, ROM, JSON, .zip, repack): ")
                if arq:
                    self._importar_arquivo(arq.strip())
            elif escolha == "Pasta":
                r = self.perguntar("Pasta (; separadas, vazio=tudo): ")
                if r is None:
                    continue
                roots = [x.strip() for x in r.split(";") if x.strip()] or None
                self._prev_pasta(roots)
            elif escolha == "Sanear pasta…":
                r = self.perguntar("Pasta do jogo p/ sanear: ")
                if not (r or "").strip():
                    continue
                try:
                    self._backup_pre_import()
                    res = core.sanear_pasta(r.strip())
                except Exception as e:
                    self.msg = f"Falha: {e}"
                    continue
                if not res.get("ok"):
                    self.msg = f"Falha: {res.get('erro', 'falha')}"
                    continue
                detalhe = f"Pasta: {res['pasta']}"
                if res.get("avisos"):
                    detalhe += " · " + " · ".join(res["avisos"][:3])
                if res.get("precisa_instalar"):
                    self.msg = detalhe + " · Só há instalador — rode o setup."
                    continue
                self.msg = detalhe
                if self.confirmar(f"Importar '{res['pasta']}' para o Hub?"):
                    self._prev_pasta([res["pasta"]])
                    continue
            elif escolha.startswith("Disco"):
                self._prev_disco()
            elif escolha == "Catálogo SteamRip":
                self.menu_steamrip()
            elif escolha == "Catálogo FitGirl":
                self.menu_fitgirl()
    def menu_steamrip(self):
        """Catálogo SteamRip: buscar → hosts → Meus Jogos Locais/ → importar."""
        r = self.perguntar("Buscar no SteamRip: ")
        if r is None or not r.strip():
            return
        try:
            res = core.buscar_steamrip(r.strip())
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        if res.get("erros"):
            self.msg = f"Falha: {res['erros'][0]}"
            return
        itens = res.get("itens") or []
        if not itens:
            self.msg = "Nada encontrado."
            return
        idx = self.escolher(f"SteamRip ({len(itens)})",
                            [i["titulo"] for i in itens] + ["Voltar"])
        if idx is None or idx >= len(itens):
            return
        pg = itens[idx]
        try:
            det = core.detalhes_steamrip(pg["url"])
        except ValueError as e:
            self.msg = f"Falha: {e}"
            return
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        hosts = det.get("hosts") or []
        ops = ([h["nome"] for h in hosts]
               + ["Automático", "Abrir página (URL)", "Voltar"])
        h = self.escolher(pg["titulo"], ops)
        if h is None or h >= len(ops) - 2:
            if h == len(ops) - 2:
                self.msg = f"Abra: {pg['url']}"
            return
        host = "" if ops[h] == "Automático" else hosts[h]["nome"] \
            if h < len(hosts) else ""
        self.msg = f"Baixando '{pg['titulo']}'…"
        try:
            res = core.baixar_steamrip(pg["url"], host=host)
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        if not res.get("ok"):
            self.msg = f"Falha: {res.get('erro')}"
            return
        self.msg = f"Em Meus Jogos Locais/: {Path(res['path']).name}"
        if self.confirmar("Importar para o Hub agora?"):
            self._importar_arquivo(res["path"])
    def menu_fitgirl(self):
        """Catálogo FitGirl: buscar → espelhos/magnets → abrir → importar."""
        r = self.perguntar("Buscar na FitGirl: ")
        if r is None or not r.strip():
            return
        try:
            res = core.buscar_fitgirl(r.strip())
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        if res.get("erros"):
            self.msg = f"Falha: {res['erros'][0]}"
            return
        itens = res.get("itens") or []
        if not itens:
            self.msg = "Nada encontrado."
            return
        idx = self.escolher(f"FitGirl ({len(itens)})",
                            [i["titulo"] for i in itens] + ["Voltar"])
        if idx is None or idx >= len(itens):
            return
        pg = itens[idx]
        try:
            det = core.detalhes_fitgirl(pg["url"])
        except ValueError as e:
            self.msg = f"Falha: {e}"
            return
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        links = ([{"tipo": "espelho", **h} for h in det.get("espelhos") or []]
                 + [{"tipo": "magnet", "nome": core.nome_magnet(m), "url": m}
                    for m in det.get("magnets") or []])
        if not links:
            self.msg = "Post sem espelhos nem magnets."
            return
        rotulos = [f"🧲 {e['nome']}" if e["tipo"] == "magnet"
                   else f"{e['nome']} — {e['url'][:60]}" for e in links]
        h = self.escolher(pg["titulo"],
                          rotulos + ["Abrir página (URL)", "Importar arquivo…",
                                     "Voltar"])
        if h is None or h >= len(rotulos + ["Abrir página (URL)",
                                            "Importar arquivo…"]):
            return
        if h < len(links):
            e = links[h]
            if e["tipo"] == "magnet":
                r = core.qbit_adicionar(e["url"])
                self.msg = (f"No Hub → {r.get('destino', 'Meus Jogos Locais/')}"
                            if r.get("ok") else f"Falha: {r.get('erro')}")
            else:
                r = core.abrir_url(e["url"])
                self.msg = (f"Aberto: {e['nome'][:60]}"
                            if r.get("ok") else f"Falha: {r.get('erro')}")
            return
        if h == len(links) + 1:
            arq = self.perguntar("Repack baixado (.rar/.zip/.7z/.iso): ")
            if arq and arq.strip():
                self._importar_arquivo(arq.strip())
            return
        self.msg = f"Abra: {pg['url']}"
    def menu_backup(self):
        opcoes = ["Backup do banco", "Backup saves 3DS", "Exportar JSON",
                  "Exportar pacote", "Importar pacote", "Voltar"]
        while True:
            idx = self.escolher("Backup e saves", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            escolha = opcoes[idx]
            if escolha == "Backup do banco":
                self.backup()
            elif escolha == "Backup saves 3DS":
                self.backup_saves()
            elif escolha == "Exportar JSON":
                self.exportar_json()
            elif escolha == "Exportar pacote":
                self.exportar_pacote()
            elif escolha == "Importar pacote":
                arq = self.perguntar("Pacote .zip: ")
                if arq:
                    self.importar_pacote(arq.strip())
    def menu_emuladores(self):
        opcoes = ["Atualizar Azahar", "Atualizar DeSmuME", "Voltar"]
        while True:
            idx = self.escolher("Emuladores", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            if opcoes[idx] == "Atualizar Azahar":
                self.atualizar_azahar()
            elif opcoes[idx] == "Atualizar DeSmuME":
                self.atualizar_desmume()
    def _aplicar_sessoes(self):
        """Drena a fila de sessões sem trocar sua referência na thread vigia."""
        pend = []
        while True:
            try:
                pend.append(self.sessoes_pendentes.get_nowait())
            except Empty:
                break
        if not pend:
            return
        con = self._con()
        try:
            msgs = []
            for gid, sessao, rastreado in pend:
                if not rastreado:
                    continue
                if sessao <= 0:
                    msgs.append("sessão curta: nada registrado")
                    continue
                r = core.adicionar_horas(con, gid, sessao)
                msgs.append(f"+{r['somado']}h (total {r['total']}h)"
                            if r.get("ok") else f"sessão: {r.get('erro')}")
            if msgs:
                self.msg = " · ".join(msgs)
                self.recarregar()
        finally:
            con.close()
    def _avisar_preset(self, dados: dict) -> None:
        pres = [(dados.get("azahar_preset") or "").strip()]
        pres = [p for p in pres if p]
        if not pres:
            return
        try:
            todos = set()
            for chave in core.provedores():
                todos |= set(core.listar_presets(chave))
        except Exception:
            return
        for pre in pres:
            if pre not in todos:
                self.msg = f"Preset '{pre}' não existe (play ignora; foto na GUI)."
                return
    def _backup_pre_import(self):
        core.backup_pre_import(self.db_path)

