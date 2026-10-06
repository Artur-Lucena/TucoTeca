#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Catálogo SteamRip no Hub: buscar, listar hosts e baixar p/ `Piratas/`.

Fonte já conhecida do projeto (vigília Hydra); aqui vira catálogo digital:
`?s=` acha o post, o post lista GOFILE/MegaDB/FileDitch/etc. FileDitch é
direto; Gofile resolve via API guest; MegaDB segue redirect com HEAD.
O `.rar` cai em `Piratas/` e o fluxo repack existente importa depois.
Tudo com `urllib` stdlib; rede falhou = erro claro, nunca levanta cru.
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

STEAMRIP_BASE = "https://steamrip.com"
STEAMRIP_HOSTS_ENV = "BIBLIOTECA_STEAMRIP_HOSTS"
_HOSTS_PADRAO = ("fileditch", "gofile", "megadb")

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                       " AppleWebKit/537.36 (KHTML, like Gecko)"
                       " Chrome/126.0.0.0 Safari/537.36",
       "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                 "*/*;q=0.8",
       "Accept-Language": "en-US,en;q=0.9",
       "Referer": "https://www.google.com/",
       "Upgrade-Insecure-Requests": "1"}


def ordem_hosts() -> tuple:
    """Ordem de tentativa (`BIBLIOTECA_STEAMRIP_HOSTS`, default direta 1º)."""
    env = (os.environ.get(STEAMRIP_HOSTS_ENV) or "").strip().lower()
    if not env:
        return _HOSTS_PADRAO
    vistos = []
    for p in re.split(r"[,;\s]+", env):
        p = p.strip()
        if p and p not in vistos:
            vistos.append(p)
    return tuple(vistos) or _HOSTS_PADRAO


def _ler(url: str, timeout: int = 20, limite: int = 2_000_000) -> str:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limite).decode("utf-8", "replace")


def _limpar(texto: str) -> str:
    texto = re.sub(r"<[^>]+>", "", texto or "")
    return _html.unescape(re.sub(r"\s+", " ", texto)).strip()


_POST_IGNORADOS = ("search", "category", "tag", "author", "page", "feed",
                   "comments", "wp-admin", "wp-content", "wp-includes",
                   "wp-json", "steps-for-games", "how-to-run-games",
                   "request-games", "dmca", "privacy-policy", "contact")


def buscar_steamrip(termo: str, timeout: int = 20) -> dict:
    """[{'titulo', 'url'}] da busca (só posts de jogo). Erro vira `erros`."""
    termo = (termo or "").strip()
    if not termo:
        return {"itens": [], "erros": ["busca vazia"]}
    try:
        q = urllib.parse.urlencode({"s": termo})
        pagina = _ler(f"{STEAMRIP_BASE}/?{q}", timeout=timeout,
                      limite=1_500_000)
    except Exception as e:
        return {"itens": [], "erros": [f"busca falhou: {e}"]}
    itens: list[dict] = []
    vistos: set[str] = set()
    pats = [r"<h2[^>]*>\s*<a\s+href=\"([^\"]+)\"[^>]*>(.*?)</a>",
            r"<a\s+href=\"(https?://steamrip\.com/([^\"/]+)/)\"[^>]*>(.*?)</a>"]
    for pat in pats:
        try:
            achados = re.findall(pat, pagina, re.IGNORECASE | re.DOTALL)
        except re.error:
            continue
        for ach in achados:
            url, resto = ach[0], ach[-1]
            slug = (ach[1] if len(ach) == 3 else url.rstrip("/").rsplit("/", 1)[-1])
            slug = slug.strip().lower()
            if not slug or slug in _POST_IGNORADOS or slug.startswith("wp-"):
                continue
            url = urllib.parse.urljoin(STEAMRIP_BASE + "/", url.strip())
            if not url.startswith("http"):
                continue
            if url in vistos:
                continue
            titulo = _limpar(resto)
            if not titulo or len(titulo) < 3:
                continue
            vistos.add(url)
            itens.append({"titulo": titulo, "url": url})
        if itens:
            break
    return {"itens": itens[:30], "erros": []}


def detalhes_steamrip(url: str, timeout: int = 20) -> dict:
    """{'titulo', 'hosts': [{'nome', 'url'}]} do post. Erro vira ValueError."""
    try:
        pagina = _ler(url, timeout=timeout, limite=1_500_000)
    except Exception as e:
        raise ValueError(f"página falhou: {e}")
    titulo = ""
    m = re.search(r"<meta\s+property=\"og:title\"\s+content=\"([^\"]+)\"",
                  pagina, re.IGNORECASE)
    if m:
        titulo = _limpar(m.group(1)).split("»")[0].split("|")[0].strip()
    hosts: list[dict] = []
    for m in re.finditer(
            r"<strong>([^<>]+)</strong>.*?<a\s+href=\"([^\"]+)\"[^>]*>"
            r"\s*DOWNLOAD HERE\s*</a>", pagina,
            re.IGNORECASE | re.DOTALL):
        nome = re.sub(r"\s+", "", _limpar(m.group(1))).lower()
        link = m.group(2).strip()
        if link.startswith("//"):
            link = "https:" + link
        if link.startswith("http") and nome:
            hosts.append({"nome": nome, "url": link})
    if not hosts:
        raise ValueError("post sem links de download")
    vistos: set[str] = set()
    unicos = []
    for h in hosts:
        chave = (h["nome"], h["url"])
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(h)
    return {"titulo": titulo, "hosts": unicos}


def resolver_gofile(url: str, timeout: int = 30) -> list[dict]:
    """Links diretos via API guest ([{'nome','url','tamanho'}]). Levanta ValueError."""
    m = re.search(r"gofile\.io/(?:d/)?([A-Za-z0-9]+)", url or "")
    if not m:
        raise ValueError("link gofile inválido")
    codigo = m.group(1)
    try:
        req = urllib.request.Request(
            "https://api.gofile.io/accounts",
            data=json.dumps({}).encode(), headers={**_UA, "Content-Type":
                                                   "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            conta = json.loads(r.read(100_000).decode("utf-8"))
        token = ((conta.get("data") or {}).get("token") or "").strip()
        if not token:
            raise ValueError("gofile sem token guest")
        req = urllib.request.Request("https://api.gofile.io/servers?zone=eu",
                                     headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            servs = json.loads(r.read(100_000).decode("utf-8"))
        nomes = [s.get("name") for s in (servs.get("data") or {}).get("servers", [])
                 if isinstance(s, dict) and s.get("name")]
        if not nomes:
            raise ValueError("gofile sem servidor")
        req = urllib.request.Request(
            f"https://{nomes[0]}.gofile.io/contents/{codigo}",
            headers={**_UA, "Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            cont = json.loads(r.read(2_000_000).decode("utf-8"))
        filhos = (cont.get("data") or {}).get("children") or {}
        arquivos: list[dict] = []

        def _andar(no):
            if not isinstance(no, dict):
                return
            if no.get("type") == "file" and no.get("link"):
                arquivos.append({"nome": str(no.get("name") or "arquivo"),
                                 "url": str(no["link"]),
                                 "tamanho": int(no.get("size") or 0)})
            for filho in (no.get("children") or {}).values():
                _andar(filho)
        for filho in filhos.values():
            _andar(filho)
        if not arquivos:
            raise ValueError("gofile vazio/expirado")
        return arquivos
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"gofile falhou: {e}")


def resolver_megadb(url: str, timeout: int = 20) -> dict:
    """Segue redirect com HEAD (só baixa se for arquivo). Levanta ValueError."""
    try:
        req = urllib.request.Request(url, headers=_UA, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            final = r.geturl()
            tipo = (r.headers.get("Content-Type") or "").lower()
            disp = (r.headers.get("Content-Disposition") or "").lower()
    except Exception as e:
        raise ValueError(f"megadb falhou: {e}")
    if "attachment" in disp or not tipo.startswith("text/html"):
        return {"url": final}
    raise ValueError("megadb protegido (abra a página)")


def _nome_saida(titulo: str, url: str) -> str:
    base = (url or "").rstrip("/").rsplit("/", 1)[-1]
    base = urllib.parse.unquote(base).split("?")[0].strip()
    if base and "." in base and len(base) < 160:
        return base
    from bib_nucleo.base import slugify
    return (slugify(titulo) or "jogo") + ".rar"


def baixar_steamrip(url_pagina: str, destino=None, host: str = "",
                    progresso=None, timeout: int = 30) -> dict:
    """Baixa o jogo p/ `Piratas/` (FileDitch direto → gofile → megadb).

    `host`: nome preferido (senão ordem `BIBLIOTECA_STEAMRIP_HOSTS`).
    Nunca levanta cru: erro vira {'ok': False, 'erro', 'tentados': [...]}.
    """
    from bib_nucleo.repacks import pasta_piratas
    try:
        det = detalhes_steamrip(url_pagina, timeout=timeout)
    except ValueError as e:
        return {"ok": False, "erro": str(e), "tentados": []}
    ordem = ((host or "").strip().lower(),)
    alvos = [h for h in det["hosts"] if ordem[0] and ordem[0] in h["nome"]] \
        if ordem[0] else []
    for pref in ordem_hosts():
        alvos += [h for h in det["hosts"] if pref in h["nome"]
                  and h not in alvos]
    alvos += [h for h in det["hosts"] if h not in alvos]
    tentados: list[str] = []
    erros: list[str] = []
    for h in alvos:
        nome, link = h["nome"], h["url"]
        tentados.append(nome)
        try:
            if "gofile" in nome:
                arqs = resolver_gofile(link, timeout=timeout)
                direto = max(arqs, key=lambda a: a.get("tamanho", 0))["url"]
            elif "megadb" in nome:
                direto = resolver_megadb(link, timeout=timeout)["url"]
            else:
                direto = link  # fileditch e cia: link direto
            return _descer(direto, det["titulo"], destino, progresso,
                           timeout=timeout)
        except ValueError as e:
            erros.append(f"{nome}: {e}")
            continue
    return {"ok": False,
            "erro": "; ".join(erros[:3]) or "sem hosts",
            "tentados": tentados}


def _descer(url: str, titulo: str, destino, progresso,
            timeout: int = 60) -> dict:
    from bib_nucleo.repacks import pasta_piratas
    base = Path(destino) if destino else pasta_piratas()
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"ok": False, "erro": f"pasta: {e}", "tentados": []}
    nome = _nome_saida(titulo, url)
    alvo = base / nome
    n = 1
    while alvo.exists():
        n += 1
        alvo = base / f"{alvo.stem}-{n}{alvo.suffix}"
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r, \
                alvo.open("wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            feito = 0
            while True:
                parte = r.read(512 * 1024)
                if not parte:
                    break
                if parte.lstrip()[:15].lower().startswith(
                        (b"<!doctype html", b"<html")) and feito == 0:
                    raise ValueError("veio HTML em vez de arquivo")
                f.write(parte)
                feito += len(parte)
                if progresso:
                    try:
                        progresso(feito, total)
                    except Exception:
                        pass
        if alvo.stat().st_size < 1_000_000:
            try:
                alvo.unlink()
            except OSError:
                pass
            return {"ok": False, "erro": "download curto (<1MB)",
                    "tentados": []}
    except ValueError as e:
        return {"ok": False, "erro": str(e), "tentados": []}
    except Exception as e:
        try:
            alvo.unlink()
        except OSError:
            pass
        return {"ok": False, "erro": f"download: {e}", "tentados": []}
    return {"ok": True, "path": str(alvo), "bytes": alvo.stat().st_size}


__all__ = ['STEAMRIP_BASE', 'ordem_hosts', 'buscar_steamrip',
           'detalhes_steamrip', 'resolver_gofile', 'resolver_megadb',
           'baixar_steamrip']
