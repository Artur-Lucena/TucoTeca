#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Providers, Azahar (manager/install/presets) e execução com vigia.

Pacote por contrato (F1 do O2): `azahar`, `desmume`, `provedores`,
`presets`, `mods`, `lancamento` + `_comum`. Compat total: `from bib_nucleo
import emuladores` e `emuladores.X` (inclusive os `_privados` usados pelos
testes e o monkeypatch `emuladores.procurar_rom` / `_lancar_jogo_dict`)
continuam iguais; `__all__` preservado.
"""
from __future__ import annotations

import os
import shutil
import subprocess

from bib_nucleo.base import (
    LINUX_ROOT,
    MAC_ROOT,
    WIN_ROOT,
    eh_mac,
    traduzir_para_atual,
)
from bib_nucleo.emuladores._comum import *
from bib_nucleo.emuladores.azahar import *
from bib_nucleo.emuladores.desmume import *
from bib_nucleo.emuladores.lancamento import *
from bib_nucleo.emuladores.mods import *
from bib_nucleo.emuladores.presets import *
from bib_nucleo.emuladores.provedores import *
from bib_nucleo.sessoes_manuais import (
    encerrar_sessao_manual,
    iniciar_sessao_manual,
    listar_sessoes_pendentes,
)

__all__ = ['azahar_dir_override', 'default_emu_3ds', 'desmume_dir_override', 'desmume_dir', 'default_emu_nds', 'desmume_user_dir', 'desmume_versao_local', 'desmume_release_info', 'desmume_instalar', 'desmume_config_atual', 'desmume_flags', 'config_atual_emu', 'presets_prov_dir', 'azahar_user_dir', 'azahar_status', 'AZAHAR_API_LATEST', 'AZAHAR_VERSAO_ARQ', 'azahar_versao_local', 'azahar_release_info', 'azahar_instalar', 'executar_elevado', 'executar_jogo_dict', 'diagnosticar_exe', 'diagnosticar_rom', 'procurar_rom', 'azahar_flags', 'LIMIAR_SESSAO_S', 'executar_monitorado', 'iniciar_sessao_manual', 'listar_sessoes_pendentes', 'encerrar_sessao_manual', 'provedores', 'provedor_por_origem', 'provedor_por_extensao', 'provedor_nome', 'jogos_do_provedor', 'provedores_resumo', 'montar_launch_rom', 'backup_saves_emu', 'backup_saves_azahar', 'presets_dir', 'listar_presets', 'azahar_config_atual', 'salvar_preset_de_atual', 'aplicar_preset', 'preparar_lancamento', 'rom_parece_criptografada', 'azahar_tem_chaves',
 'title_id_da_rom', 'mods_lib_dir', 'mods_titulo_dir', 'remover_link', 'listar_mods', 'remover_mod', 'azahar_mods_dir', 'mods_ativos', 'aplicar_mods', 'importar_mod']
