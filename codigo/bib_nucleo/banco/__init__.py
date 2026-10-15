#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SQLite: schema, migrações, validação, CRUD, capas, horas e etiquetas.

Pacote fatiado: `_infra` (schema/migrações/FTS/get_db), `jogos` (catálogo,
etiquetas, mods, capas, horas), `catalogo` (músicas/downloads/vídeos) e os
desejos que moram em `banco_desejos`. Esta fachada preserva
`bib_nucleo.banco` como superfície única para consumidores e testes.
"""
from __future__ import annotations

from bib_nucleo.banco._infra import (
    MIGRACOES,
    SCHEMA,
    SCHEMA_DOWNLOADS,
    SCHEMA_MUSICAS,
    SCHEMA_VIDEOS,
    get_db,
)
from bib_nucleo.banco._infra import (
    _inicializar_db as _inicializar_db,
)
from bib_nucleo.banco._infra import (
    garantir_fts as garantir_fts,
)
from bib_nucleo.banco.catalogo import (
    ESTADOS_DOWNLOAD,
    criar_musica,
    criar_video,
    download_to_dict,
    enfileirar_downloads,
    excluir_musica,
    excluir_video,
    limpar_downloads,
    listar_downloads,
    listar_musicas,
    listar_videos,
    marcar_download,
    musica_to_dict,
    video_to_dict,
)
from bib_nucleo.banco.jogos import (
    CAMPOS_EDITAVEIS,
    CAPA_ALT,
    CAPA_EXTS,
    CAPA_LARG,
    ETIQUETA_MAX,
    ETIQUETAS_MAX,
    MODS_MAX_NOME,
    MODS_MAX_QTD,
    STATUS_VALIDOS,
    adicionar_horas,
    atualizar_jogo,
    caminho_capa,
    chave_dedup,
    contar_por_origem,
    criar_jogo,
    etiquetas_de,
    excluir_jogo,
    listar_etiquetas,
    listar_jogos,
    marcar_execucao,
    mods_de,
    normalizar_etiquetas,
    normalizar_mods,
    plataforma_de_origem,
    plataforma_jogo,
    row_to_dict,
    salvar_capa,
    salvar_capa_bytes,
    salvar_capa_musica_bytes,
    selo_confianca,
    validar_dados,
)
from bib_nucleo.banco_desejos import (
    SCHEMA_DESEJOS,
    adicionar_desejo,
    desejo_to_dict,
    listar_desejos,
    marcar_desejo_obtido,
    remover_desejo,
    sincronizar_desejos,
)

__all__ = [
    'STATUS_VALIDOS', 'SCHEMA', 'MIGRACOES', 'CAMPOS_EDITAVEIS',
    'ETIQUETA_MAX', 'ETIQUETAS_MAX', 'normalizar_etiquetas', 'etiquetas_de',
    'MODS_MAX_NOME', 'MODS_MAX_QTD', 'normalizar_mods', 'mods_de',
    'plataforma_de_origem', 'plataforma_jogo', 'get_db', 'row_to_dict',
    'validar_dados', 'chave_dedup', 'listar_jogos', 'listar_etiquetas',
    'criar_jogo', 'atualizar_jogo', 'excluir_jogo', 'SCHEMA_MUSICAS',
    'musica_to_dict', 'criar_musica', 'listar_musicas', 'excluir_musica',
    'salvar_capa_musica_bytes', 'ESTADOS_DOWNLOAD', 'SCHEMA_DOWNLOADS', 'download_to_dict',
    'enfileirar_downloads', 'listar_downloads', 'marcar_download', 'limpar_downloads',
    'SCHEMA_DESEJOS', 'desejo_to_dict', 'listar_desejos', 'sincronizar_desejos',
    'adicionar_desejo', 'marcar_desejo_obtido', 'remover_desejo', 'CAPA_EXTS',
    'CAPA_LARG', 'CAPA_ALT', 'salvar_capa', 'salvar_capa_bytes',
    'caminho_capa', 'marcar_execucao', 'adicionar_horas', 'contar_por_origem',
    'selo_confianca', 'SCHEMA_VIDEOS', 'video_to_dict', 'criar_video',
    'listar_videos', 'excluir_video',
]
