#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bib_core — núcleo compartilhado da Biblioteca de Jogos (compat).

O código mora em bib_nucleo/ (base, banco, scans, emuladores, pacotes);
aqui só reexporta para frontends e scripts (`import bib_core as core`).
Para monkeypatch em testes, altere bib_nucleo.<modulo> (onde mora a função).

Os reexports são explícitos e nomeados (sem `import *`): cada nome vem de um
único módulo dono e a lista pública está em `__all__`. A fachada guarda só os
nomes que a TUI, os serviços, a ponte, as ferramentas e os testes usam; código
novo importa direto de bib_nucleo.
"""
from __future__ import annotations

# Submódulos usados como atributos da fachada (`core.banco`, `core.scans`,
# `core.baixar`); `x as x` marca reexport explícito.
from bib_nucleo import baixar as baixar
from bib_nucleo import banco as banco
from bib_nucleo import scans as scans
from bib_nucleo.apps_externos import (
    PRESETS_EQ,
    PROVEDORES_EQUALIZADOR,
    PROVEDORES_IMAGEM,
    PROVEDORES_VIDEO,
    abrir_no_editor,
    abrir_no_editor_audio,
    aplicar_eq,
    localizar_editor,
    localizar_equalizador,
    localizar_reprodutor,
    reproduzir_video,
    status_editores,
    status_equalizadores,
    status_reprodutores,
)
from bib_nucleo.baixar import (
    baixar_faixa,
    converter_faixa,
    erro_sem_ytdlp,
    ffmpeg_pronto,
    importar_fila_pronta,
    instalar_ffmpeg,
    instalar_ytdlp,
    ler_csv_exportify,
    localizar_ytdlp,
    ytdlp_pronto,
)
from bib_nucleo.banco import (
    CAMPOS_EDITAVEIS,
    STATUS_VALIDOS,
    adicionar_desejo,
    adicionar_horas,
    atualizar_jogo,
    caminho_capa,
    chave_dedup,
    criar_jogo,
    criar_musica,
    criar_video,
    enfileirar_downloads,
    etiquetas_de,
    excluir_jogo,
    excluir_musica,
    excluir_video,
    get_db,
    limpar_downloads,
    listar_desejos,
    listar_downloads,
    listar_etiquetas,
    listar_jogos,
    listar_musicas,
    listar_videos,
    marcar_desejo_obtido,
    marcar_download,
    marcar_execucao,
    mods_de,
    normalizar_etiquetas,
    normalizar_mods,
    plataforma_de_origem,
    plataforma_jogo,
    remover_desejo,
    row_to_dict,
    salvar_capa_bytes,
    salvar_capa_musica_bytes,
    selo_confianca,
    sincronizar_desejos,
)
from bib_nucleo.base import (
    BACKUP_DIR,
    BAIXAR_DIR,
    CAPAS_DIR,
    DADOS_DIR,
    DEFAULT_DB,
    HOME_DIR,
    MUSICAS_DIR,
    VIDEO_EXTS,
    VIDEOS_DIR,
    adquirir_lock,
    existe_aqui_ou_traduzido,
    garantir_dirs,
    liberar_lock,
    lock_path,
    log_erro,
    traduzir_para_atual,
)
from bib_nucleo.cheats import (
    adicionar_cheat,
    alternar_cheat,
    listar_cheats,
    remover_cheat,
)
from bib_nucleo.config import (
    cfg,
)
from bib_nucleo.controles import (
    NOMES_TIPO,
    aplicar_preset_controle,
    detectar_sdl,
    fotografar_perfil,
    ler_estado_xinput,
    listar_controles,
    listar_presets_controle,
    nomes_sdl,
    resumir_estado,
    salvar_mapa_gerado,
)
from bib_nucleo.emuladores import (
    azahar_status,
    backup_saves_azahar,
    backup_saves_emu,
    default_emu_3ds,
    default_emu_nds,
    diagnosticar_exe,
    diagnosticar_rom,
    encerrar_sessao_manual,
    executar_jogo_dict,
    executar_monitorado,
    importar_mod,
    iniciar_sessao_manual,
    jogos_do_provedor,
    listar_mods,
    listar_presets,
    listar_sessoes_pendentes,
    preparar_lancamento,
    procurar_rom,
    provedor_por_origem,
    provedores,
    remover_mod,
    title_id_da_rom,
)
from bib_nucleo.musicas import (
    baixar_capa_album,
    baixar_capas_faltantes,
    harmoni_dir,
    importar_musicas,
    sugestao_harmoni_dir,
    texto_musica,
    tocar_musica,
)
from bib_nucleo.pacotes import (
    backup_pre_import,
    exportar_json,
    exportar_pacote,
    fazer_backup,
    idade_ultimo_backup_dias,
    importar_pacote,
)
from bib_nucleo.player import (
    Player,
)
from bib_nucleo.qbit import (
    qbit_adicionar,
    qbit_controlar,
    qbit_iniciar,
    qbit_listar,
)
from bib_nucleo.rede.fontes import (
    abrir_url,
    baixar_steamrip,
    buscar_fitgirl,
    buscar_jogos_steam,
    buscar_steamrip,
    detalhes_fitgirl,
    detalhes_steamrip,
    ler_wishlist,
    ler_wishlist_arquivo,
    nome_magnet,
    steam_principal,
)
from bib_nucleo.rede.repacks import (
    abrir_instalador,
    dentro_de_piratas,
    dentro_do_destino,
    eh_pacote_hub,
    ferramenta_7z,
    importar_pasta,
    importar_repack,
    organizar_em_piratas,
    organizar_no_destino,
    pasta_jogos,
    pasta_piratas,
    preparar_pacote,
    sanear_pasta,
)
from bib_nucleo.rede.torrents import (
    encontrar_torrents,
    formatar_tamanho,
    listar_torrents,
)
from bib_nucleo.rede.videos_youtube import (
    baixar_audio_youtube,
    baixar_video_youtube,
    buscar_youtube,
)
from bib_nucleo.scans import (
    analisar_arquivo,
    fundir_duplicados,
    importar_lista,
    ler_do_disco,
    pontuar,
    preview_pasta,
    preview_scan,
    resumo_importacao,
    scan_roms,
)
from bib_nucleo.texturas import (
    definir_textura,
    estado_textura,
    instalar_textura,
)
from bib_nucleo.videos import (
    importar_videos,
)
from bib_nucleo.volume import (
    ajustar_volume_pc,
    alternar_mudo_pc,
    definir_volume_pc,
    ler_volume_pc,
)

__all__ = [
    'BACKUP_DIR', 'BAIXAR_DIR', 'CAMPOS_EDITAVEIS', 'CAPAS_DIR', 'DADOS_DIR', 'DEFAULT_DB',
    'HOME_DIR', 'MUSICAS_DIR', 'NOMES_TIPO', 'PRESETS_EQ', 'PROVEDORES_EQUALIZADOR',
    'PROVEDORES_IMAGEM', 'PROVEDORES_VIDEO', 'Player', 'STATUS_VALIDOS', 'VIDEOS_DIR',
    'VIDEO_EXTS', 'abrir_instalador', 'abrir_no_editor', 'abrir_no_editor_audio', 'abrir_url',
    'adicionar_cheat', 'adicionar_desejo', 'adicionar_horas', 'adquirir_lock',
    'ajustar_volume_pc', 'alternar_cheat', 'alternar_mudo_pc', 'analisar_arquivo', 'aplicar_eq',
    'aplicar_preset_controle', 'atualizar_jogo', 'azahar_status', 'backup_pre_import',
    'backup_saves_azahar', 'backup_saves_emu', 'baixar_audio_youtube', 'baixar_capa_album',
    'baixar_capas_faltantes', 'baixar_faixa', 'baixar_steamrip', 'baixar_video_youtube',
    'buscar_fitgirl', 'buscar_jogos_steam', 'buscar_steamrip', 'buscar_youtube', 'caminho_capa',
    'cfg', 'chave_dedup', 'converter_faixa', 'criar_jogo', 'criar_musica', 'criar_video',
    'default_emu_3ds', 'default_emu_nds', 'definir_textura', 'definir_volume_pc',
    'dentro_de_piratas', 'dentro_do_destino', 'detalhes_fitgirl', 'detalhes_steamrip',
    'detectar_sdl', 'diagnosticar_exe', 'diagnosticar_rom', 'eh_pacote_hub',
    'encerrar_sessao_manual', 'encontrar_torrents', 'enfileirar_downloads', 'erro_sem_ytdlp',
    'estado_textura', 'etiquetas_de', 'excluir_jogo', 'excluir_musica', 'excluir_video',
    'executar_jogo_dict', 'executar_monitorado', 'existe_aqui_ou_traduzido', 'exportar_json',
    'exportar_pacote', 'fazer_backup', 'ferramenta_7z', 'ffmpeg_pronto', 'formatar_tamanho',
    'fotografar_perfil', 'fundir_duplicados', 'garantir_dirs', 'get_db', 'harmoni_dir',
    'idade_ultimo_backup_dias', 'importar_fila_pronta', 'importar_lista', 'importar_mod',
    'importar_musicas', 'importar_pacote', 'importar_pasta', 'importar_repack',
    'importar_videos', 'iniciar_sessao_manual', 'instalar_ffmpeg', 'instalar_textura',
    'instalar_ytdlp', 'jogos_do_provedor', 'ler_csv_exportify', 'ler_do_disco',
    'ler_estado_xinput', 'ler_volume_pc', 'ler_wishlist', 'ler_wishlist_arquivo',
    'liberar_lock', 'limpar_downloads', 'listar_cheats', 'listar_controles', 'listar_desejos',
    'listar_downloads', 'listar_etiquetas', 'listar_jogos', 'listar_mods', 'listar_musicas',
    'listar_presets', 'listar_presets_controle', 'listar_sessoes_pendentes', 'listar_torrents',
    'listar_videos', 'localizar_editor', 'localizar_equalizador', 'localizar_reprodutor',
    'localizar_ytdlp', 'lock_path', 'log_erro', 'marcar_desejo_obtido', 'marcar_download',
    'marcar_execucao', 'mods_de', 'nome_magnet', 'nomes_sdl', 'normalizar_etiquetas',
    'normalizar_mods', 'organizar_em_piratas', 'organizar_no_destino', 'pasta_jogos',
    'pasta_piratas', 'plataforma_de_origem', 'plataforma_jogo', 'pontuar',
    'preparar_lancamento', 'preparar_pacote', 'preview_pasta', 'preview_scan', 'procurar_rom',
    'provedor_por_origem', 'provedores', 'qbit_adicionar', 'qbit_controlar', 'qbit_iniciar',
    'qbit_listar', 'remover_cheat', 'remover_desejo', 'remover_mod', 'reproduzir_video',
    'resumir_estado', 'resumo_importacao', 'row_to_dict', 'salvar_capa_bytes',
    'salvar_capa_musica_bytes', 'salvar_mapa_gerado', 'sanear_pasta', 'scan_roms',
    'selo_confianca', 'sincronizar_desejos', 'status_editores', 'status_equalizadores',
    'status_reprodutores', 'steam_principal', 'sugestao_harmoni_dir', 'texto_musica',
    'title_id_da_rom', 'tocar_musica', 'traduzir_para_atual', 'ytdlp_pronto',
]
