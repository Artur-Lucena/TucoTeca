"""Verificar atualização do TucoTeca: última release no GitHub e o instalador desta máquina.

Só roda quando o usuário clica (Configurações → Geral). O instalador baixado
vai para dados/atualizacoes/ e só fica lá se o SHA-256 bater com o publicado.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
import urllib.request
from pathlib import Path

from bib_nucleo.rede import abrir_rede, exigir_rede
from bib_nucleo.versao import REPOSITORIO, user_agent, versao_app

API = "https://api.github.com/repos/" + REPOSITORIO.removeprefix("https://github.com/") + "/releases/latest"


def plataforma_atual() -> str:
    """windows-x64 | macos-arm64 | macos-x64 | linux-x64 (o que o instalador da release cobre)."""
    if sys.platform == "darwin":
        return "macos-arm64" if platform.machine().lower() in ("arm64", "aarch64") else "macos-x64"
    if sys.platform.startswith("win"):
        return "windows-x64"
    return "linux-x64"


def _numeros(versao: str) -> tuple[int, ...]:
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", (versao or "").strip())
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def mais_nova(candidata: str, atual: str) -> bool:
    return _numeros(candidata) > _numeros(atual)


# nome do anexo por plataforma (ver preparar_release.py)
PADROES = {
    "windows-x64": re.compile(r"^TucoTeca-Setup-[\d.]+-x64\.exe$"),
    "macos-arm64": re.compile(r"^TucoTeca-[\d.]+-mac-arm64\.dmg$"),
    "macos-x64": re.compile(r"^TucoTeca-[\d.]+-mac-x64\.dmg$"),
    "linux-x64": re.compile(r"^TucoTeca-[\d.]+-linux-x64\.AppImage$"),
}


def escolher_instalador(anexos: list, plataforma: str) -> dict | None:
    padrao = PADROES.get(plataforma)
    for a in anexos or []:
        if not isinstance(a, dict) or padrao is None or not padrao.match(str(a.get("name") or "")):
            continue
        url = str(a.get("browser_download_url") or "")
        if not url.startswith("https://github.com/"):
            continue
        digest = str(a.get("digest") or "")
        return {"nome": a["name"], "url": url, "tamanho": int(a.get("size") or 0),
                "sha256": digest.removeprefix("sha256:") if digest.startswith("sha256:") else ""}
    return None


def _obter_release() -> dict:
    exigir_rede("Verificar atualização")
    req = urllib.request.Request(API, headers={"User-Agent": user_agent(), "Accept": "application/vnd.github+json"})
    with abrir_rede(req, timeout=15) as r:
        dados = json.loads(r.read(2_000_000).decode("utf-8"))
    if not isinstance(dados, dict):
        raise ValueError("Resposta inesperada do GitHub.")
    return dados


def verificar(obter=_obter_release, atual: str | None = None, plataforma: str | None = None) -> dict:
    """{atual, ultima, nova, notas, pagina, publicada_em, instalador|None}."""
    atual = atual or versao_app()
    plataforma = plataforma or plataforma_atual()
    rel = obter()
    ultima = str(rel.get("tag_name") or "").lstrip("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", ultima):
        raise ValueError("A última release não tem uma versão válida.")
    nova = mais_nova(ultima, atual)
    return {
        "atual": atual, "ultima": ultima, "nova": nova, "plataforma": plataforma,
        "notas": str(rel.get("body") or "")[:20_000],
        "pagina": str(rel.get("html_url") or REPOSITORIO + "/releases/latest"),
        "publicada_em": str(rel.get("published_at") or "")[:10],
        "instalador": escolher_instalador(rel.get("assets") or [], plataforma) if nova else None,
    }


def pasta_atualizacoes() -> Path:
    from bib_nucleo.base import DADOS_DIR
    return DADOS_DIR / "atualizacoes"


def sha256_de(caminho: Path) -> str:
    h = hashlib.sha256()
    with Path(caminho).open("rb") as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def baixar_instalador(instalador: dict, progresso=None, cancelado=None, baixar=None) -> dict:
    """Baixa o instalador escolhido, confere o SHA-256 e apaga instaladores antigos."""
    from bib_nucleo.rede.fontes_download import baixar_direto
    nome = str(instalador.get("nome") or "")
    url = str(instalador.get("url") or "")
    if not any(p.match(nome) for p in PADROES.values()) or not url.startswith("https://github.com/"):
        raise ValueError("Instalador inválido.")
    pasta = pasta_atualizacoes()
    # baixar de novo: o download direto não sobrescreve (salvaria "…-2.exe", nome que o app recusa abrir)
    (pasta / nome).unlink(missing_ok=True)
    r = (baixar or baixar_direto)(url, nome, pasta, progresso, cancelado)
    arquivo = Path(r["path"])
    esperado = str(instalador.get("sha256") or "").lower()
    if esperado and sha256_de(arquivo) != esperado:
        arquivo.unlink(missing_ok=True)
        raise ValueError("O instalador baixado não confere com o publicado (SHA-256). Nada foi instalado.")
    for velho in pasta.glob("TucoTeca-*"):
        if velho != arquivo and velho.is_file():
            velho.unlink(missing_ok=True)
    if arquivo.suffix == ".AppImage":
        arquivo.chmod(0o755)
    return {"ok": True, "arquivo": str(arquivo), "conferido": bool(esperado)}


__all__ = ["API", "PADROES", "plataforma_atual", "mais_nova", "escolher_instalador", "verificar",
           "pasta_atualizacoes", "baixar_instalador"]
