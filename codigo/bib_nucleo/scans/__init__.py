#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Achados: confiança, Hydra, disco, fontes, ROMs 3DS e importação.

Pacote por contrato (F2 do O2): `lojas`, `disco`, `roms`, `analise`,
`metadados`, `importacao`. Compat total: `from bib_nucleo import scans`
e `scans.X` continuam iguais; `__all__` preservado.
"""
from __future__ import annotations

from bib_nucleo.scans.analise import *
from bib_nucleo.scans.disco import *
from bib_nucleo.scans.importacao import *
from bib_nucleo.scans.lojas import *
from bib_nucleo.scans.metadados import *
from bib_nucleo.scans.roms import *

__all__ = ['SHOPS_CONHECIDAS', 'pontuar', 'hydra_db_candidates', 'find_hydra_db', 'TITLE_RE', 'EXEC_RE', 'SHOP_RE', 'OBJID_RE', 'PLAYTIME_RE', 'scan_hydra_db', 'SKIP_DIRS', 'SKIP_EXE_RE', 'RIOT_EXE', 'ACF_NAME_RE', 'ACF_DIR_RE', 'default_scan_roots', 'scan_discos', 'preview_scan', 'JUNK_PROG_RE', 'ler_do_disco', 'default_roms_roots', 'ROM_TAGS_LIXO_RE', 'scan_roms', 'preview_roms', 'EXE_IMPORTAVEIS', 'analisar_arquivo', 'preview_pasta', 'fundir_duplicados', 'SMDH_IDIOMAS', 'SMDH_REGIOES', 'NDS_REGIOES', 'ler_metadados_nds', 'icone_nds_para_png', 'ler_metadados_3ds', 'icone_rom_para_png', 'importar_lista']
__all__ += ['resumo_importacao']
