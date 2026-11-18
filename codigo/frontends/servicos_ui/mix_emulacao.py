"""Emulacao e controles via ServicoBiblioteca: status, update, pads e, por
jogo 3DS, mods/cheats/texturas/presets do Azahar (antes `qt_emulacao.py`)."""
from __future__ import annotations

from bib_nucleo import cheats as CHEATS
from bib_nucleo import controles as nucleo_controles
from bib_nucleo import emuladores as EMU
from bib_nucleo import texturas as TEXTURAS
from bib_nucleo.base import traduzir_para_atual


def _exigir_ok(r, padrao):
    """Domínio devolve {"ok": False, "erro": ...}; a ponte espera exceção."""
    if isinstance(r, dict) and r.get("ok") is False:
        raise ValueError(r.get("erro") or padrao)
    return r


class MixEmulacao:
    _EMU_CHAVES = ("azahar", "desmume")

    # -- por jogo (3DS/Azahar) ------------------------------------------------
    def _tid_jogo(self, jogo):
        launch = (jogo.get("launch_options") or "").strip()
        return EMU.title_id_da_rom(traduzir_para_atual(launch)) if launch else ""

    def emulacao_jogo(self, gid):
        """Estado de mods, cheats, texturas e presets de um jogo 3DS. Só leitura.

        Sem ROM 3DS legível volta `erro` explicando, com listas vazias — a
        interface mostra o aviso em vez de botões que não teriam efeito.
        """
        jogo = self.jogo(gid)
        base = {"id": gid, "titulo": jogo.get("titulo") or "", "tid": "", "erro": "",
                "mods": [], "mods_off": False, "cheats": [],
                "textura": {"instalado": False, "ativo": False, "arquivos": 0},
                "presets": []}
        tid = self._tid_jogo(jogo)
        if not tid:
            base["erro"] = ("Escolha um jogo 3DS com ROM válida para gerenciar mods, "
                            "texturas, cheats e presets.")
            return base
        ativos = set(EMU.mods_ativos(jogo))
        base.update(
            tid=tid,
            mods=[{"nome": n, "ativo": n in ativos} for n in EMU.listar_mods(tid)],
            mods_off=bool(jogo.get("azahar_mods_off")),
            cheats=[dict(c) for c in CHEATS.listar_cheats(tid)],
            textura=dict(TEXTURAS.estado_textura(tid)),
            presets=list(EMU.listar_presets("azahar")),
        )
        return base

    def _tid_exigido(self, gid):
        jogo = self.jogo(gid)
        tid = self._tid_jogo(jogo)
        if not tid:
            raise ValueError("Escolha um jogo 3DS com ROM válida.")
        return jogo, tid

    def emulacao_mod(self, gid, acao, nome="", arquivo=""):
        """alternar | desligar_todos | remover | importar. Devolve o estado novo."""
        jogo, tid = self._tid_exigido(gid)
        atuais = list(EMU.mods_ativos(jogo))
        off = bool(jogo.get("azahar_mods_off"))
        if acao == "alternar":
            if nome not in EMU.listar_mods(tid):
                raise ValueError("Mod não encontrado na biblioteca.")
            ativos = [m for m in atuais if m != nome] if nome in atuais else atuais + [nome]
            self.salvar_mods_jogo(gid, ativos, off)
        elif acao == "desligar_todos":
            self.salvar_mods_jogo(gid, atuais, not off)
        elif acao == "remover":
            _exigir_ok(EMU.remover_mod(tid, nome), "Não foi possível remover o mod.")
            self.salvar_mods_jogo(gid, [m for m in atuais if m != nome], off)
        elif acao == "importar":
            if not str(arquivo or "").strip():
                raise ValueError("Escolha o arquivo ou a pasta do mod.")
            _exigir_ok(EMU.importar_mod(arquivo, tid), "Não foi possível importar o mod.")
        else:
            raise ValueError("Ação de mod inválida.")
        return self.emulacao_jogo(gid)

    def emulacao_cheat(self, gid, acao, nome="", codigo=""):
        """alternar | adicionar | remover. Devolve o estado novo."""
        _jogo, tid = self._tid_exigido(gid)
        if acao == "alternar":
            _exigir_ok(CHEATS.alternar_cheat(tid, nome), "Não foi possível alterar o cheat.")
        elif acao == "adicionar":
            _exigir_ok(CHEATS.adicionar_cheat(tid, nome, codigo), "Não foi possível salvar o cheat.")
        elif acao == "remover":
            _exigir_ok(CHEATS.remover_cheat(tid, nome), "Não foi possível remover o cheat.")
        else:
            raise ValueError("Ação de cheat inválida.")
        return self.emulacao_jogo(gid)

    def emulacao_textura(self, gid, acao, arquivo=""):
        """alternar | instalar. Devolve o estado novo."""
        _jogo, tid = self._tid_exigido(gid)
        if acao == "alternar":
            _exigir_ok(TEXTURAS.alternar_textura(tid), "Não foi possível alterar as texturas.")
        elif acao == "instalar":
            if not str(arquivo or "").strip():
                raise ValueError("Escolha o pacote de texturas.")
            _exigir_ok(TEXTURAS.instalar_textura(tid, arquivo),
                       "Não foi possível instalar as texturas.")
        else:
            raise ValueError("Ação de textura inválida.")
        return self.emulacao_jogo(gid)

    def emulacao_preset(self, acao, nome):
        """aplicar | salvar presets globais do Azahar (qt-config.ini)."""
        nome = str(nome or "").strip()
        if not nome:
            raise ValueError("Informe o nome do preset.")
        if acao == "aplicar":
            r = _exigir_ok(EMU.aplicar_preset(nome, "azahar"), "Não foi possível aplicar o preset.")
        elif acao == "salvar":
            r = _exigir_ok(EMU.salvar_preset_de_atual(nome, "azahar"),
                           "Não foi possível salvar o preset.")
        else:
            raise ValueError("Ação de preset inválida.")
        return {"ok": True, "presets": list(EMU.listar_presets("azahar")),
                "avisos": list((r or {}).get("avisos") or [])}

    def emus_status(self):
        """Status local dos emuladores. Só leitura, sem rede.

        O remoto só aparece depois de emu_consultar (rede explícita).
        """
        itens = []
        for chave, prov in EMU.provedores().items():
            if chave not in self._EMU_CHAVES:
                continue
            try:
                local = prov["versao_local"]() or ""
            except Exception:
                local = ""
            itens.append({"chave": chave, "nome": prov.get("nome", chave),
                          "local": local, "tag": "", "atualizado": None})
        return {"itens": itens}

    def emu_consultar(self, chave):
        """Consulta o release remoto (rede). Devolve local × remoto + info.

        A info volta para a ponte guardar; a instalação só ocorre em
        emu_atualizar, depois de confirmação expressa na UI.
        """
        chave = (chave or "").strip()
        prov = EMU.provedores().get(chave)
        if prov is None:
            raise ValueError("Emulador desconhecido.")
        info = prov["release_info"]()
        if not isinstance(info, dict) or info.get("erro"):
            raise ValueError((info or {}).get("erro", "Não foi possível consultar o release."))
        try:
            local = prov["versao_local"]() or ""
        except Exception:
            local = ""
        tag = info.get("tag") or "?"
        return {"chave": chave, "nome": prov.get("nome", chave), "local": local,
                "tag": tag, "tamanho_mb": round((info.get("size") or 0) / 1048576),
                "atualizado": bool(local and local == tag), "info": dict(info)}

    def emu_atualizar(self, chave, info):
        """Baixa e instala o release já consultado. Rede + escrita, com confirmação da UI."""
        chave = (chave or "").strip()
        prov = EMU.provedores().get(chave)
        if prov is None:
            raise ValueError("Emulador desconhecido.")
        if not isinstance(info, dict) or not info.get("tag"):
            raise ValueError("Consulte o release antes de atualizar.")
        r = prov["instalar"](dict(info))
        if not isinstance(r, dict) or not r.get("ok"):
            raise ValueError((r or {}).get("erro", "Não foi possível instalar o emulador."))
        return r

    def controles_pads(self):
        """Pads detectados. Só leitura; sem pads é lista vazia, não erro."""
        try:
            pads = nucleo_controles.listar_controles() or []
        except Exception:
            pads = []
        return {"pads": [dict(p) for p in pads]}

    def controles_presets(self):
        try:
            nomes = nucleo_controles.listar_presets_controle() or []
        except Exception:
            nomes = []
        return {"presets": [str(n) for n in nomes]}

    def controles_tipos(self):
        tipos = sorted(nucleo_controles.NOMES_TIPO)
        return {"tipos": [{"tipo": t, "nome": nucleo_controles.NOMES_TIPO[t]} for t in tipos]}

    def controle_fotografar(self, nome):
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Dê um nome ao preset.")
        r = nucleo_controles.fotografar_perfil(nome)
        if not isinstance(r, dict) or not r.get("ok"):
            raise ValueError((r or {}).get("erro", "Não foi possível salvar o preset."))
        return r

    def controle_aplicar(self, nome):
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Escolha um preset para aplicar.")
        r = nucleo_controles.aplicar_preset_controle(nome)
        if not isinstance(r, dict) or not r.get("ok"):
            raise ValueError((r or {}).get("erro", "Não foi possível aplicar o preset."))
        return r

    def controle_gerar(self, tipo):
        tipo = (tipo or "").strip()
        if tipo not in nucleo_controles.NOMES_TIPO:
            raise ValueError("Escolha um tipo de controle.")
        guid, port, rot = "", 0, {}
        try:
            det = nucleo_controles.detectar_sdl()
            if det:
                guid, port = det[0].get("guid", ""), det[0].get("port", 0)
            rot = nucleo_controles.nomes_sdl()
        except Exception:
            pass
        r = nucleo_controles.salvar_mapa_gerado(tipo, guid=guid, port=port,
                                    nome=f"{tipo}-hub", rotulos=rot)
        if not isinstance(r, dict) or not r.get("ok"):
            raise ValueError((r or {}).get("erro", "Não foi possível gerar o mapa."))
        return r

    def controle_estado(self):
        """Resumo ao vivo do pad 0. Hardware real em produção; testes simulam."""
        try:
            est = nucleo_controles.ler_estado_xinput(0)
        except Exception as e:
            raise ValueError(f"Sem leitura do controle: {e}")
        return {"resumo": nucleo_controles.resumir_estado(est)}


__all__ = ["MixEmulacao"]
