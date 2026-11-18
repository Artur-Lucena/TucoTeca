#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuração centralizada do TucoTeca (somente stdlib).

Fonte única para as variáveis BIBLIOTECA_* (e HYDRA_DB_PATH), com
tipos, defaults documentados e parsing dos formatos históricos (`;` para
listas de caminhos, `0/false/no/off` para desligar).

O núcleo permanece stdlib: nada aqui importa pacotes externos. `.env` não é
lido automaticamente — use variáveis de ambiente ou um launcher que exporte
as chaves.

Uso:
    from bib_nucleo.config import cfg
    cfg.win_root          # Path("D:/")
    cfg.rede              # bool
    cfg.scan_roots        # tuple[Path, ...]
    cfg.azahar_dir        # Path | None
"""
from __future__ import annotations

import dataclasses
import os
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# Nomes de variável por campo (prefixo BIBLIOTECA_ + exceções históricas)
# --------------------------------------------------------------------------
_ENV_ESPECIAIS = {
    "seven_zip": "BIBLIOTECA_7Z",
    "hydra_db_path": "HYDRA_DB_PATH",
}


def _env_nome(campo: str) -> str:
    return _ENV_ESPECIAIS.get(campo, "BIBLIOTECA_" + campo.upper())


def _txt(v) -> str:
    return "" if v is None else str(v).strip()


def _bool(v, padrao: bool) -> bool:
    """Formato histórico: 0/false/no/off/vazio desligam; resto liga."""
    if v is None:
        return padrao
    t = str(v).strip().lower()
    if t == "":
        return padrao
    return t not in ("0", "false", "no", "off")


def _path(v) -> Path | None:
    t = _txt(v)
    if not t:
        return None
    return Path(os.path.expandvars(t)).expanduser()


def _paths(v) -> tuple[Path, ...]:
    t = _txt(v)
    if not t:
        return ()
    return tuple(p for p in (_path(part) for part in t.split(";")) if p)


def _str_ou_none(v) -> str | None:
    t = _txt(v)
    return t or None


# --------------------------------------------------------------------------
# Campos por tipo de parsing (fonte única da verdade)
# --------------------------------------------------------------------------
_CAMPOS_PATH = (
    "home", "win_root", "linux_root", "mac_root",
    "azahar_dir", "desmume_dir", "jogos_dir", "musica_dir",
    "seven_zip", "ytdlp", "ffmpeg", "quickjs", "deno",
    "qbittorrent", "qbit_dir", "qbit_profile",
    "krita", "gimp", "photodemon",
    "audacity", "equalizerapo", "peace", "vlc", "mpv", "mpchc",
    "everything", "hydra_db_path", "emulador_3ds", "emulador_nds",
)
_CAMPOS_BOOL = {"rede": True, "capa_musica_auto": True}
_CAMPOS_ROOTS = ("scan_roots", "roms_roots", "roms_nds_roots")
_CAMPOS_STR = {"azahar_flags": "-f", "desmume_flags": "", "preco_regiao": "br"}
_CAMPOS_STR_OU_NONE = ("steam_id", "qbit_api", "everything_instancia")


@dataclass(frozen=True)
class Config:
    """Configuração única do TucoTeca (valores imutáveis, lidos do ambiente)."""

    # Casa & raízes de tradução Win/Linux/Mac
    home: Path | None = None
    win_root: Path = Path("D:\\")
    linux_root: Path = Path("/run/media/tuco/Games")
    mac_root: Path = Path("/Volumes/Games")

    # Varredura & ROMs
    scan_roots: tuple[Path, ...] = ()
    roms_roots: tuple[Path, ...] = ()
    roms_nds_roots: tuple[Path, ...] = ()

    # Emuladores
    emulador_3ds: Path | None = None
    azahar_dir: Path | None = None
    azahar_flags: str = "-f"
    emulador_nds: Path | None = None
    desmume_dir: Path | None = None
    desmume_flags: str = ""

    # Diretórios de dados & downloads
    jogos_dir: Path | None = None
    musica_dir: Path | None = None

    # Ferramentas externas (binários)
    seven_zip: Path | None = None
    ytdlp: Path | None = None
    ffmpeg: Path | None = None
    quickjs: Path | None = None
    deno: Path | None = None
    qbittorrent: Path | None = None
    qbit_dir: Path | None = None
    qbit_profile: Path | None = None
    qbit_api: str | None = None

    # Editores / áudio / vídeo
    krita: Path | None = None
    gimp: Path | None = None
    photodemon: Path | None = None
    audacity: Path | None = None
    equalizerapo: Path | None = None
    peace: Path | None = None
    vlc: Path | None = None
    mpv: Path | None = None
    mpchc: Path | None = None

    # Everything / rede / integrações
    everything: Path | None = None
    everything_instancia: str | None = None
    rede: bool = True
    steam_id: str | None = None
    preco_regiao: str = "br"
    hydra_db_path: Path | None = None

    # Comportamento / qualidade de vida
    capa_musica_auto: bool = True

    @classmethod
    def from_env(cls, env: dict | None = None) -> "Config":
        """Lê o ambiente (ou `env` explícito, útil em testes) e devolve a config."""
        fonte = os.environ if env is None else env
        valores: dict = {}
        padroes = {f.name: f.default for f in dataclasses.fields(cls)}
        for campo in padroes:
            bruto = fonte.get(_env_nome(campo))
            if campo in _CAMPOS_PATH:
                convertido = _path(bruto)
                valores[campo] = padroes[campo] if convertido is None else convertido
            elif campo in _CAMPOS_BOOL:
                valores[campo] = _bool(bruto, padroes[campo])
            elif campo in _CAMPOS_ROOTS:
                valores[campo] = _paths(bruto)
            elif campo in _CAMPOS_STR:
                t = _txt(bruto)
                valores[campo] = padroes[campo] if not t else t
            elif campo in _CAMPOS_STR_OU_NONE:
                valores[campo] = _str_ou_none(bruto)
            else:  # pragma: no cover - campo novo sem categoria declarada
                raise RuntimeError(f"campo sem parser: {campo}")
        return cls(**valores)


# --------------------------------------------------------------------------
# Singleton + recarga
# --------------------------------------------------------------------------
_cfg: Config | None = None


def get_config(reload: bool = False) -> Config:
    """Instância compartilhada da configuração (reload=True relê o ambiente)."""
    global _cfg
    if _cfg is None or reload:
        _cfg = Config.from_env()
    return _cfg


def reset_config() -> None:
    """Descarta a instância atual (o próximo get_config relê o ambiente)."""
    global _cfg
    _cfg = None


# --------------------------------------------------------------------------
# Compat: leitura no formato `os.environ.get("BIBLIOTECA_X", ...)`
# --------------------------------------------------------------------------
def _env(name: str, default: str = "") -> str:
    """Valor atual como texto ('' quando vazio), para código legado."""
    atual = get_config()
    valor = getattr(atual, name.lower(), None)
    if valor is None:
        return default
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, (tuple, list)):
        return ";".join(str(x) for x in valor)
    return str(valor)


cfg = get_config()

__all__ = [
    "Config",
    "get_config",
    "reset_config",
    "cfg",
    "_env",
]
