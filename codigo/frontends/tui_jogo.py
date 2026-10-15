#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TucoTeca terminal: MixJogo de Tui (verbatim do modulo original)."""
from __future__ import annotations

import os

import bib_core as core


class MixJogo:
    def jogar(self):
        j = self.atual()
        if not j:
            return
        con = self._con()
        try:
            j = self._resolver_antes_de_jogar(con, j)
            if j is None:
                return
            prep = core.preparar_lancamento(j)
            aviso = f" [{prep['aviso']}]" if prep.get("aviso") else ""
            res = core.executar_monitorado(
                j, ao_fim=lambda sessao, rastreado, _gid=j["id"]:
                    self.sessoes_pendentes.put((_gid, sessao, rastreado)))
            if res.get("requer_elevacao") and self.confirmar("Exige administrador. Elevar?"):
                res = core.executar_jogo_dict(j, elevar=True)
                if res.get("ok"):
                    core.marcar_execucao(con, j["id"])
                    try:
                        core.iniciar_sessao_manual(j["id"], j.get("titulo") or "")
                    except Exception:
                        pass
                    self.msg = f"Executando ✓ (UAC — sessão manual; S registra){aviso}"
                else:
                    self.msg = f"Falha: {res.get('erro')}{aviso}"
            elif res.get("ok"):
                core.marcar_execucao(con, j["id"])
                if res.get("rastreado"):
                    extra = " ⏱ tempo será registrado"
                else:
                    extra = " ⏱ sem rastreio — sessão manual; S registra ao terminar"
                self.msg = f"Executando ✓ ({res.get('modo')}){extra}{aviso}"
            else:
                self.msg = f"Falha: {res.get('erro')}{aviso}"
        finally:
            con.close()
    def registrar_sessao_manual(self):
        try:
            pend = core.listar_sessoes_pendentes()
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        if not pend:
            self.msg = "Nenhuma sessão manual pendente."
            return
        alvo = pend[0]
        if len(pend) > 1:
            for i, p in enumerate(pend):
                self.msg = f"{i+1}: {p.get('titulo') or p.get('gid')} · {p.get('inicio')}"
                self.desenhar()
                self.perguntar("Enter p/ continuar…")
            r = self.perguntar(f"Número (1-{len(pend)}, J=primeira): ")
            if r is None:
                return
            r = (r or "").strip().lower()
            if r in ("j", "jogar", ""):
                alvo = pend[0]
            elif r.isdigit() and 1 <= int(r) <= len(pend):
                alvo = pend[int(r) - 1]
            else:
                return
        r = self.perguntar(f"Horas em '{alvo.get('titulo') or alvo.get('gid')}' (0=encerrar sem somar): ")
        if r is None:
            return
        try:
            horas = float((r or "0").strip() or 0)
        except ValueError:
            self.msg = "Horas inválidas."
            return
        try:
            res = core.encerrar_sessao_manual(alvo["_arquivo"], horas, db_path=self.db_path)
        except Exception as e:
            self.msg = f"Falha: {e}"
            return
        self.msg = f"+{horas}h ✓" if res.get("ok") and horas else (res.get("erro") or "Encerrada.")
        self.recarregar()
    def _verificar_pendencias_inicio(self):
        if self._sessoes_verificadas:
            return
        self._sessoes_verificadas = True
        try:
            pend = core.listar_sessoes_pendentes()
            if pend:
                self.msg = f"{len(pend)} sessão(ões) manual(is) pendente(s) — S registra."
        except Exception:
            pass
        if self._backup_verificado:
            return
        self._backup_verificado = True
        try:
            idade = core.idade_ultimo_backup_dias()
            if idade is None:
                self.msg += (" · " if self.msg else "") + "Sem backup — b faz agora."
            elif idade > 7:
                self.msg += (" · " if self.msg else "") + f"Backup há {int(idade)}d — b faz agora."
        except Exception:
            pass
    def _resolver_antes_de_jogar(self, con, j):
        """Perguntar-antes (TUI): emulador trocado? ROM sumida? Jogo ou None."""
        diag = core.diagnosticar_exe(j)
        if diag["estado"] == "trocou-emulador":
            r = self.perguntar(
                f"Emulador gravado sumiu. Usar o atual ({diag['nome']}) e "
                "[G]ravar, só desta [V]ez ou [C]ancelar? ")
            if r is None:
                return None
            op = r.strip().lower()
            if op in ("g", "gravar"):
                j = core.atualizar_jogo(con, j["id"], {"executable_path": "",
                    "exe_win" if os.name == "nt" else "exe_linux": ""})
            elif op in ("v", "vez"):
                j = {**j, "executable_path": "", "exe_win": "", "exe_linux": ""}
            else:
                return None
        drom = core.diagnosticar_rom(j)
        if drom["estado"] == "rom-ausente":
            cands = drom["candidatos"]
            escolhido = None
            if cands:
                for i, p in enumerate(cands):
                    self.msg = f"{i + 1}: {p}"
                    self.desenhar()
                    self.perguntar("Enter para continuar: ")
                r = self.perguntar("Número da ROM (J=primeira, vazio=informar caminho): ")
                if r is None:
                    return None
                if r.lower() in ("j", "jogar"):
                    escolhido = cands[0]
                elif r.isdigit() and 1 <= int(r) <= len(cands):
                    escolhido = cands[int(r) - 1]
            if not escolhido:
                escolhido = self.perguntar("Novo caminho da ROM (vazio=cancela): ")
            if not escolhido:
                self.msg = "Religação cancelada."
                return None
            escolhido = escolhido.strip()
            ok, trad = core.existe_aqui_ou_traduzido(escolhido)
            if not ok:
                self.msg = "Religação cancelada ou arquivo inexistente (nos 2 SOs)."
                return None
            escolhido = trad
            if not self.confirmar(f"Religar para {escolhido}?"):
                return None
            j = core.atualizar_jogo(con, j["id"], {"launch_options": escolhido})
        return j
    def menu_jogo(self):
        """Enter virou select: caixinha de ações do jogo; ESC volta à lista."""
        j = self.atual()
        if not j:
            return
        opcoes = ["Jogar", "Editar", "Mods", "Texturas", "Cheats",
                  "Apagar", "Voltar"]
        idx = self.escolher(j["titulo"], opcoes)
        if idx is None:
            return
        escolha = opcoes[idx]
        if escolha == "Jogar":
            self.jogar()
        elif escolha == "Editar":
            self.editar()
        elif escolha == "Mods":
            self.menu_mods(j)
        elif escolha == "Texturas":
            self.menu_texturas(j)
        elif escolha == "Cheats":
            self.menu_cheats(j)
        elif escolha == "Apagar":
            self.excluir()
    def adicionar(self):
        dados = self.formulario(None)
        if not dados:
            return
        con = self._con()
        try:
            try:
                core.criar_jogo(con, dados)
                self.msg = "Salvo ✓"
                self._avisar_preset(dados)
            except ValueError as e:
                self.msg = f"Erro: {e}"
        finally:
            con.close()
        self.recarregar()
    def editar(self):
        j = self.atual()
        if not j:
            return
        dados = self.formulario(j)
        if not dados:
            return
        con = self._con()
        try:
            try:
                core.atualizar_jogo(con, j["id"], dados)
                self.msg = "Salvo ✓"
                self._avisar_preset(dados)
            except (ValueError, LookupError) as e:
                self.msg = f"Erro: {e}"
        finally:
            con.close()
        self.recarregar()
    def excluir(self):
        j = self.atual()
        if not j:
            return
        if not self.confirmar(f"Excluir '{j['titulo']}'?"):
            return
        con = self._con()
        try:
            try:
                core.excluir_jogo(con, j["id"])
                self.msg = "Excluído."
            except LookupError as e:
                self.msg = f"Erro: {e}"
        finally:
            con.close()
        self.recarregar()
    def menu_sessao(self):
        opcoes = ["Registrar sessão manual", "Voltar"]
        while True:
            idx = self.escolher("Sessão", opcoes)
            if idx is None or opcoes[idx] == "Voltar":
                return
            self.registrar_sessao_manual()

