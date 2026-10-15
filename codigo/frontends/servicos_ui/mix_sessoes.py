"""Jogo em execucao e sessoes via ServicoBiblioteca."""
from __future__ import annotations

import math
from contextlib import closing
from pathlib import Path

import bib_core as core
from bib_nucleo.arquivos import gravar_atomico


class MixSessoes:
    def iniciar_jogo(self, gid, ao_fim):
        jogo = self.jogo(gid)
        if core.diagnosticar_rom(jogo)["estado"] == "rom-ausente":
            raise ValueError("ROM não encontrada. Atualize o caminho em Editar jogo.")
        preparo = core.preparar_lancamento(jogo)
        resultado = core.executar_monitorado(jogo, ao_fim=ao_fim)
        if not resultado.get("ok"):
            raise ValueError(resultado.get("erro", "Não foi possível iniciar o jogo."))
        with closing(core.get_db(self.db_path)) as con:
            core.marcar_execucao(con, gid)
        resultado["aviso"] = preparo.get("aviso", "")
        return resultado

    def iniciar_jogo_elevado(self, gid):
        """Relança o jogo com elevação explícita (UAC). Confirmação é da UI."""
        jogo = self.jogo(gid)
        preparo = core.preparar_lancamento(jogo)
        r = core.executar_jogo_dict(jogo, elevar=True)
        if not r.get("ok"):
            raise ValueError(r.get("erro", "Não foi possível iniciar com elevação."))
        with closing(core.get_db(self.db_path)) as con:
            core.marcar_execucao(con, gid)
        try:
            core.iniciar_sessao_manual(gid, jogo.get("titulo") or "")
        except Exception as e:
            # sessão manual é rastreamento auxiliar; não falha o lançamento
            core.log_erro("jogar-uac", f"sessão manual não abriu: {e}")
        return {"ok": True, "modo": r.get("modo", "runas-uac"),
                "aviso": preparo.get("aviso", "")}

    def registrar_sessao(self, gid, horas):
        horas = float(horas)
        if not math.isfinite(horas) or horas < 0:
            raise ValueError("Informe um número de horas finito e não negativo.")
        if horas > 0:
            from bib_nucleo.estatisticas import registrar
            from bib_nucleo.preferencias_pessoais import ler_preferencias
            def gravar(con):
                jogo = self.jogo(gid)
                registrar(con, jogo, horas, ler_preferencias()["ativo"], commit=False)
                r = core.adicionar_horas(con, gid, horas)
                if not r.get("ok"):
                    con.rollback()
                return r
            return self.alterar(gravar)
        return {"ok": True}

    def encerrar_sessao(self, arquivo, horas):
        horas = float(horas)
        if not math.isfinite(horas) or horas <= 0:
            raise ValueError("Informe quantas horas você jogou (maior que zero).")
        with self._escrita:
            sessao = next((s for s in self.sessoes() if s.get("_arquivo") == arquivo), None)
            if sessao is None:
                raise ValueError("Esta sessão já foi encerrada ou não está mais disponível.")
            core.fazer_backup(self.db_path)
            marcador = Path(sessao["_arquivo"])
            gravar_atomico(core.BACKUP_DIR / "sessoes" / marcador.name, marcador.read_bytes())
            r = core.encerrar_sessao_manual(str(marcador), horas, db_path=self.db_path)
            return r

    def diagnosticar_jogo(self, gid):
        """Diagnóstico só-leitura de exe/ROM: estado, caminho e candidatos."""
        jogo = self.jogo(gid)
        return {"gid": gid, "titulo": jogo.get("titulo") or "",
                "exe": core.diagnosticar_exe(jogo), "rom": core.diagnosticar_rom(jogo),
                "jogo": jogo}

    _RELIGAR_CAMPOS = ("launch_options", "executable_path", "exe_win", "exe_linux")

    def religar_jogo(self, gid, campo, caminho):
        """Grava um novo caminho de exe/ROM escolhido pelo usuário. Com backup."""
        campo = str(campo or "")
        caminho = str(caminho or "").strip()
        if campo not in self._RELIGAR_CAMPOS:
            raise ValueError("Campo inválido para religar.")
        if not caminho:
            raise ValueError("Informe o novo caminho.")
        return self.alterar(lambda con: core.atualizar_jogo(con, gid, {campo: caminho}))

    def backup_pos_sessao(self, gid):
        from bib_nucleo import saves
        with self._escrita:
            banco = core.fazer_backup(self.db_path)
            jogo = self.jogo(gid)
            r = saves.snapshot_saves(jogo)
            prov = core.provedor_por_origem(jogo.get("origem", ""))
            if not r.get("arquivos") and prov:
                r = core.backup_saves_emu(prov["chave"])
            return {"ok": r.get("ok", True), "banco": banco, "saves": r,
                    "erro": r.get("erro", ""), "avisos": [r["aviso"]] if r.get("aviso") else []}

    def ferramentas_jogo(self, gid):
        from bib_nucleo import saves, screenshots
        jogo = self.jogo(gid)
        return {"saves": saves.caminhos_saves(jogo), "snapshots": saves.listar_snapshots(jogo),
                "screenshots": screenshots.listar_screenshots(jogo),
                "pasta_screenshots": str(screenshots.pasta_screenshots(jogo))}

    def configurar_saves(self, gid, caminhos):
        from bib_nucleo.saves import configurar_saves
        with self._escrita:
            return configurar_saves(self.jogo(gid), caminhos)

    def restaurar_saves(self, gid, caminho):
        from bib_nucleo.saves import restaurar_snapshot
        with self._escrita:
            return restaurar_snapshot(self.jogo(gid), caminho)

    def salvar_mods_jogo(self, gid, ativos, off):
        return self.alterar(lambda con: core.atualizar_jogo(
            con, gid, {"azahar_mods": list(ativos), "azahar_mods_off": 1 if off else 0}))


__all__ = ["MixSessoes"]
