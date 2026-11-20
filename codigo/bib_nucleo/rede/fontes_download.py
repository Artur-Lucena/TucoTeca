"""Fontes de download no formato do Hydra, adicionadas pelo usuário.

Uma fonte é um JSON público (https) no formato

    {"name": "Nome", "downloads": [{"title": "Jogo", "uris": ["magnet:?…", "https://…"],
                                   "fileSize": "12.3 GB", "uploadDate": "2025-01-31T…"}]}

O app não traz nenhuma fonte: quem escolhe o que adicionar (e responde por
isso) é o usuário. A lista é baixada quando ele adiciona/atualiza e fica em
cache em `dados/fontes-download/`; buscar um jogo não usa rede. Só links
`magnet:` (vão para o qBittorrent integrado) e `https://` (o app baixa para a
pasta de jogos) são aceitos.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from bib_nucleo import base
from bib_nucleo.arquivos import destino_temporario, gravar_json, ler_json
from bib_nucleo.rede import abrir_rede, exigir_rede

LIMITE_FONTE = 60_000_000  # listas grandes passam de 20 MB
MAX_ITENS = 200_000
_UA = {"User-Agent": "TucoTeca (fontes de download)", "Accept": "application/json"}


# ---------------------------------------------------------------- armazenamento

def _pasta() -> Path:
    return base.DADOS_DIR / "fontes-download"


def _arquivo_lista() -> Path:
    return base.DADOS_DIR / "fontes-download.json"


def _ident(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def listar() -> list[dict]:
    """Fontes cadastradas: [{id, url, nome, total, atualizada_em, erro}]."""
    dados = ler_json(_arquivo_lista(), [])
    return [f for f in dados if isinstance(f, dict) and f.get("id") and f.get("url")] if isinstance(dados, list) else []


def _gravar_lista(fontes: list[dict]) -> None:
    gravar_json(_arquivo_lista(), fontes)


def _itens(ident: str) -> list[dict]:
    dados = ler_json(_pasta() / f"{ident}.json", [], limite=LIMITE_FONTE)
    return dados if isinstance(dados, list) else []


# ---------------------------------------------------------------- leitura de uma fonte

def _uri_aceita(uri: str) -> bool:
    uri = str(uri or "").strip()
    if uri.startswith("magnet:?") and "xt=urn:" in uri:
        return True
    try:
        p = urllib.parse.urlsplit(uri)
    except ValueError:
        return False
    return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password


def normalizar_fonte(dados) -> tuple[str, list[dict]]:
    """(nome, itens) de um JSON no formato do Hydra; itens sem link aceito saem. Levanta ValueError."""
    if not isinstance(dados, dict) or not isinstance(dados.get("downloads"), list):
        raise ValueError("Não é uma fonte no formato do Hydra (falta a lista \"downloads\").")
    nome = " ".join(str(dados.get("name") or "").split())[:80] or "Fonte sem nome"
    itens = []
    for d in dados["downloads"][:MAX_ITENS]:
        if not isinstance(d, dict):
            continue
        titulo = " ".join(str(d.get("title") or "").split())[:300]
        uris = [str(u).strip() for u in (d.get("uris") or []) if _uri_aceita(str(u))][:10]
        if not titulo or not uris:
            continue
        itens.append({"titulo": titulo, "uris": uris,
                      "tamanho": str(d.get("fileSize") or "")[:30],
                      "data": str(d.get("uploadDate") or "")[:10]})
    if not itens:
        raise ValueError("A fonte não tem nenhum download com link magnet ou https.")
    return nome, itens


def _baixar_fonte(url: str) -> dict:
    exigir_rede("Atualizar fonte de download")
    req = urllib.request.Request(url, headers=_UA)
    try:
        with abrir_rede(req, timeout=60) as r:
            bruto = r.read(LIMITE_FONTE + 1)
    except Exception as erro:
        raise ValueError(f"Não consegui baixar a fonte ({getattr(erro, 'code', '') or erro}).") from None
    if len(bruto) > LIMITE_FONTE:
        raise ValueError("A fonte é grande demais (mais de 60 MB).")
    try:
        return json.loads(bruto.decode("utf-8-sig"))
    except (UnicodeError, ValueError):
        raise ValueError("A fonte não devolveu um JSON válido.") from None


def _url_valida(url: str) -> str:
    url = str(url or "").strip()
    if not _uri_aceita(url) or not url.startswith("https://"):
        raise ValueError("O endereço da fonte precisa começar com https://.")
    return url


def adicionar(url: str) -> dict:
    """Baixa, valida e cadastra a fonte (ou atualiza, se o endereço já existe)."""
    url = _url_valida(url)
    nome, itens = normalizar_fonte(_baixar_fonte(url))
    ident = _ident(url)
    _pasta().mkdir(parents=True, exist_ok=True)
    gravar_json(_pasta() / f"{ident}.json", itens)
    fonte = {"id": ident, "url": url, "nome": nome, "total": len(itens),
             "atualizada_em": time.strftime("%Y-%m-%dT%H:%M:%S"), "erro": ""}
    _gravar_lista([f for f in listar() if f["id"] != ident] + [fonte])
    return fonte


def atualizar(ident: str = "") -> dict:
    """Rebaixa uma fonte (ou todas). Uma que falhar mantém a lista anterior e registra o erro."""
    fontes = listar()
    alvo = [f for f in fontes if not ident or f["id"] == ident]
    if ident and not alvo:
        raise ValueError("Fonte não encontrada.")
    ok, erros = 0, []
    for f in alvo:
        try:
            adicionar(f["url"])
            ok += 1
        except ValueError as erro:
            erros.append(f"{f['nome']}: {erro}")
            f["erro"] = str(erro)
            _gravar_lista([x if x["id"] != f["id"] else f for x in listar()])
    return {"atualizadas": ok, "erros": erros}


def remover(ident: str) -> dict:
    fontes = listar()
    if not any(f["id"] == ident for f in fontes):
        raise ValueError("Fonte não encontrada.")
    _gravar_lista([f for f in fontes if f["id"] != ident])
    (_pasta() / f"{ident}.json").unlink(missing_ok=True)
    return {"ok": True}


# ---------------------------------------------------------------- busca

_RUIDO = re.compile(r"\b(v\d[\w.\-]*|build \d+|repack|dlcs?|bonus|ost|multi\d*|update \d+|"
                    r"deluxe|ultimate|complete|goty|edition|digital|by \w+)\b", re.IGNORECASE)


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto or ""))
    t = "".join(c for c in t if not unicodedata.combining(c)).casefold()
    return " ".join(re.sub(r"[^0-9a-z]+", " ", t).split())


def _nucleo(titulo: str) -> str:
    """Título sem versão/edição/extras: 'Hades v1.38 + Bonus' → 'hades'."""
    t = re.split(r"[\(\[+–—]| - ", str(titulo or ""))[0]
    return normalizar(_RUIDO.sub(" ", t))


def pontuar(alvo: str, titulo: str) -> float:
    """0..1: mesmo núcleo = 1; um contém o outro como palavras = 0,8; senão a sobreposição."""
    a, b = _nucleo(alvo), _nucleo(titulo)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if re.search(rf"\b{re.escape(a)}\b", b) or re.search(rf"\b{re.escape(b)}\b", a):
        return 0.8 if min(len(a), len(b)) >= 4 else 0.5
    pa, pb = set(a.split()), set(b.split())
    return 0.6 * len(pa & pb) / max(len(pa | pb), 1)


def buscar(titulo: str, minimo: float = 0.75, limite: int = 30) -> dict:
    """Opções de download para o jogo em todas as fontes cadastradas (sem rede)."""
    fontes = listar()
    achados = []
    for f in fontes:
        for item in _itens(f["id"]):
            nota = pontuar(titulo, item.get("titulo", ""))
            if nota >= minimo:
                achados.append({**item, "fonte": f["nome"], "fonte_id": f["id"], "nota": round(nota, 2)})
    achados.sort(key=lambda x: x.get("data") or "", reverse=True)  # mais novo primeiro…
    achados.sort(key=lambda x: -x["nota"])                         # …dentro da mesma nota
    return {"itens": achados[:limite], "fontes": len(fontes)}


# ---------------------------------------------------------------- download direto (https)

def _nome_arquivo(url: str, titulo: str, cabecalho: str = "") -> str:
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cabecalho or "", re.IGNORECASE)
    nome = urllib.parse.unquote(m.group(1)) if m else Path(urllib.parse.urlsplit(url).path).name
    nome = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nome).strip(" .")
    if not nome or "." not in nome:
        nome = (re.sub(r"[^\w\- ]+", "", titulo).strip() or "download")[:80] + ".bin"
    return nome[:160]


def baixar_direto(url: str, titulo: str, destino: Path, progresso=None, cancelado=None) -> dict:
    """Baixa um link https para `destino` (sem sobrescrever); recusa página HTML."""
    if not url.startswith("https://") or not _uri_aceita(url):
        raise ValueError("Só links https:// são baixados direto.")
    exigir_rede("Baixar jogo")
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": _UA["User-Agent"]})
    with abrir_rede(req, timeout=60) as r:
        tipo = (r.headers.get("Content-Type") or "").lower()
        if "text/html" in tipo:
            raise ValueError("O link abre uma página, não um arquivo: ele não serve para download direto.")
        total = int(r.headers.get("Content-Length") or 0)
        nome = _nome_arquivo(r.geturl() or url, titulo, r.headers.get("Content-Disposition") or "")
        alvo = destino / nome
        n = 1
        while alvo.exists():
            n += 1
            alvo = destino / f"{Path(nome).stem}-{n}{Path(nome).suffix}"
        feito = 0
        # o arquivo só aparece na pasta se vier inteiro (cancelar/falhar descarta o parcial)
        with destino_temporario(alvo) as tmp:
            with tmp.open("wb") as f:
                while True:
                    if cancelado is not None and cancelado():
                        raise ValueError("Download cancelado.")
                    parte = r.read(1024 * 1024)
                    if not parte:
                        break
                    f.write(parte)
                    feito += len(parte)
                    if progresso and total:
                        progresso(min(99, int(feito * 100 / total)))
            if total and feito != total:
                raise ValueError(f"Download incompleto ({feito} de {total} bytes).")
    return {"ok": True, "path": str(alvo), "bytes": feito}


__all__ = ["listar", "adicionar", "atualizar", "remover", "normalizar_fonte", "buscar", "pontuar",
           "baixar_direto"]
