"""Emulacao e controles via ServicoBiblioteca: status, update e pads."""
from __future__ import annotations

import bib_core as core


class MixEmulacao:
    _EMU_CHAVES = ("azahar", "desmume")

    def emus_status(self):
        """Status local dos emuladores. Só leitura, sem rede.

        O remoto só aparece depois de emu_consultar (rede explícita).
        """
        itens = []
        for chave, prov in core.provedores().items():
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
        prov = core.provedores().get(chave)
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
        prov = core.provedores().get(chave)
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
            pads = core.listar_controles() or []
        except Exception:
            pads = []
        return {"pads": [dict(p) for p in pads]}

    def controles_presets(self):
        try:
            nomes = core.listar_presets_controle() or []
        except Exception:
            nomes = []
        return {"presets": [str(n) for n in nomes]}

    def controles_tipos(self):
        tipos = sorted(core.NOMES_TIPO)
        return {"tipos": [{"tipo": t, "nome": core.NOMES_TIPO[t]} for t in tipos]}

    def controle_fotografar(self, nome):
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Dê um nome ao preset.")
        r = core.fotografar_perfil(nome)
        if not isinstance(r, dict) or not r.get("ok"):
            raise ValueError((r or {}).get("erro", "Não foi possível salvar o preset."))
        return r

    def controle_aplicar(self, nome):
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("Escolha um preset para aplicar.")
        r = core.aplicar_preset_controle(nome)
        if not isinstance(r, dict) or not r.get("ok"):
            raise ValueError((r or {}).get("erro", "Não foi possível aplicar o preset."))
        return r

    def controle_gerar(self, tipo):
        tipo = (tipo or "").strip()
        if tipo not in core.NOMES_TIPO:
            raise ValueError("Escolha um tipo de controle.")
        guid, port, rot = "", 0, {}
        try:
            det = core.detectar_sdl()
            if det:
                guid, port = det[0].get("guid", ""), det[0].get("port", 0)
            rot = core.nomes_sdl()
        except Exception:
            pass
        r = core.salvar_mapa_gerado(tipo, guid=guid, port=port,
                                    nome=f"{tipo}-hub", rotulos=rot)
        if not isinstance(r, dict) or not r.get("ok"):
            raise ValueError((r or {}).get("erro", "Não foi possível gerar o mapa."))
        return r

    def controle_estado(self):
        """Resumo ao vivo do pad 0. Hardware real em produção; testes simulam."""
        try:
            est = core.ler_estado_xinput(0)
        except Exception as e:
            raise ValueError(f"Sem leitura do controle: {e}")
        return {"resumo": core.resumir_estado(est)}


__all__ = ["MixEmulacao"]
