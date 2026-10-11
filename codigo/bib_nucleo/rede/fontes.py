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
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from bib_nucleo.arquivos import destino_temporario

STEAM_ID_ENV = "BIBLIOTECA_STEAM_ID"


def _parse_loginusers(texto: str) -> dict:
    """Conta principal do loginusers.vdf (maior Timestamp). Puro, testável."""
    melhor = None
    for m in re.finditer(r'"(765\d{10,})"\s*\{(.*?)\n\s*\}',
                         texto or "", re.DOTALL):
        bloco = m.group(2)
        ts = re.search(r'"Timestamp"\s+"(\d+)"', bloco)
        persona = re.search(r'"PersonaName"\s+"((?:[^"\\]|\\.)*)"', bloco)
        alt = (int(ts.group(1)) if ts else 0, m.group(1),
               persona.group(1) if persona else "")
        if melhor is None or alt[0] > melhor[0]:
            melhor = alt
    if not melhor:
        return {}
    return {"steamid": melhor[1], "persona": melhor[2]}


def steam_principal() -> dict:
    """Conta Steam principal do PC (loginusers.vdf). Só leitura, sem login.

    Retorna {'steamid', 'persona'} ou {} — override `BIBLIOTECA_STEAM_ID`.
    """
    env = (os.environ.get(STEAM_ID_ENV) or "").strip()
    if env.isdigit():
        return {"steamid": env, "persona": ""}
    cands = [Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
             / "Steam" / "config" / "loginusers.vdf"]
    if os.name != "nt":
        home = Path.home()
        cands += [home / ".steam/steam/config/loginusers.vdf",
                  home / ".local/share/Steam/config/loginusers.vdf"]
    for arq in cands:
        try:
            if not arq.is_file():
                continue
            conta = _parse_loginusers(arq.read_text(encoding="utf-8",
                                                   errors="ignore"))
        except OSError:
            continue
        if conta:
            return conta
    return {}


def ler_wishlist(steamid: str, timeout: int = 20,
                 max_paginas: int = 20) -> dict:
    """[{'appid','titulo'}] da wishlist pública (paginado). Erro vira `erros`.

    HTML não é interpretado como lista vazia nem como prova de perfil privado.
    """
    steamid = (steamid or "").strip()
    if not steamid.isdigit():
        return {"itens": [], "erros": ["sem SteamID (BIBLIOTECA_STEAM_ID?)"]}
    itens: list[dict] = []
    vistos: set[str] = set()
    try:
        for pagina in range(max(1, max_paginas)):
            req = urllib.request.Request(
                "https://store.steampowered.com/wishlist/profiles/"
                f"{steamid}/wishlistdata/?p={pagina}", headers=_UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                corpo = r.read(5_000_000).decode("utf-8", "replace")
            if corpo.lstrip()[:1] == "<":
                return {"itens": [], "erros": [
                    "O endpoint antigo da Steam devolveu uma página, não a lista. "
                    "Sincronização indisponível; use Adicionar ou um JSON exportado."]}
            try:
                dados = json.loads(corpo)
            except ValueError:
                return {"itens": [], "erros": ["resposta inválida da Steam"]}
            if not isinstance(dados, dict):
                return {"itens": itens, "erros": ["formato inesperado da Steam"]}
            if not dados:
                break
            for appid, info in dados.items():
                appid = str(appid).strip()
                if not appid.isdigit() or appid in vistos:
                    continue
                nome = ""
                if isinstance(info, dict):
                    nome = str(info.get("name") or "").strip()
                if not nome:
                    continue
                vistos.add(appid)
                itens.append({"appid": appid, "titulo": nome})
            if len(dados) < 100:
                break
    except Exception as e:
        return {"itens": itens, "erros": [f"wishlist falhou: {e}"]}
    return {"itens": itens, "erros": []}


def ler_wishlist_arquivo(caminho) -> dict:
    """[{'appid','titulo'}] de um wishlistdata/?p=N salvo no navegador.

    Aceita o JSON cru da Steam (dict appid→{name}) ou lista de
    {appid, name/titulo}. Erro vira `erros`, nunca levanta.
    """
    try:
        texto = Path(caminho).read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"itens": [], "erros": [f"arquivo ilegível: {e}"]}
    if texto.lstrip()[:1] == "<":
        return {"itens": [], "erros": [
            "O arquivo contém HTML, não uma lista JSON. "
            "Importe um JSON exportado ou use Adicionar."]}
    try:
        dados = json.loads(texto)
    except ValueError:
        return {"itens": [], "erros": ["arquivo não é um JSON válido"]}
    itens: list[dict] = []
    vistos: set[str] = set()
    pares = dados.items() if isinstance(dados, dict) else (
        enumerate(dados) if isinstance(dados, list) else [])
    for chave, info in pares:
        if isinstance(dados, dict):
            if not isinstance(info, dict):
                continue
            appid = str(chave).strip()
            nome = str(info.get("name") or info.get("titulo") or "").strip()
        elif isinstance(info, dict):
            appid = str(info.get("appid") or "").strip()
            nome = str(info.get("name") or info.get("titulo") or "").strip()
        else:
            continue
        if not appid.isdigit() or appid in vistos or not (nome or "").strip():
            continue
        vistos.add(appid)
        itens.append({"appid": appid, "titulo": str(nome).strip()})
    if not itens:
        return {"itens": [], "erros": ["nenhum jogo no arquivo"]}
    return {"itens": itens, "erros": []}


def buscar_jogos_steam(termo: str, timeout: int = 20, limite: int = 8) -> dict:
    """[{'appid','titulo'}] pela busca pública da loja (sem login).

    API storesearch (a mesma do autocomplete). Erro vira `erros`.
    """
    termo = (termo or "").strip()
    if not termo:
        return {"itens": [], "erros": ["busca vazia"]}
    try:
        url = ("https://store.steampowered.com/api/storesearch/?term="
               + urllib.parse.quote(termo) + "&cc=BR&l=english")
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            dados = json.loads(r.read(500_000).decode("utf-8", "replace"))
        itens = []
        for it in (dados.get("items") or [])[:max(1, limite)]:
            if not isinstance(it, dict):
                continue
            appid = str(it.get("id") or "").strip()
            nome = str(it.get("name") or "").strip()
            if not appid.isdigit() or not nome:
                continue
            itens.append({"appid": appid, "titulo": nome})
    except Exception as e:
        return {"itens": [], "erros": [f"busca Steam falhou: {e}"]}
    if not itens:
        return {"itens": [], "erros": [f"nada achado p/ '{termo}'"]}
    return {"itens": itens, "erros": []}


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
            if urllib.parse.urlsplit(url).hostname not in ("steamrip.com", "www.steamrip.com"):
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


class _LinksDownload(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titulo = ""
        self.hosts = []
        self.href = ""
        self.texto = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("property") == "og:title":
            self.titulo = attrs.get("content") or ""
        elif tag == "a":
            self.href = attrs.get("href") or ""
            self.texto = []

    def handle_data(self, data):
        if self.href:
            self.texto.append(data)

    def handle_endtag(self, tag):
        if tag != "a":
            return
        if " ".join("".join(self.texto).split()).casefold() == "download here":
            link = urllib.parse.urljoin(STEAMRIP_BASE + "/", self.href)
            parsed = urllib.parse.urlsplit(link)
            dominio = (parsed.hostname or "").lower()
            if parsed.scheme in ("http", "https") and dominio:
                nome = ("fileditch" if "fileditch" in dominio else
                        "gofile" if dominio.endswith("gofile.io") else
                        "megadb" if dominio.endswith("megadb.net") else dominio.split(".")[0])
                self.hosts.append({"nome": nome, "url": link})
        self.href, self.texto = "", []


def detalhes_steamrip(url: str, timeout: int = 20) -> dict:
    """{'titulo', 'hosts': [{'nome', 'url'}]} do post. Erro vira ValueError."""
    try:
        pagina = _ler(url, timeout=timeout, limite=1_500_000)
    except Exception as e:
        raise ValueError(f"página falhou: {e}")
    parser = _LinksDownload()
    parser.feed(pagina)
    titulo = _limpar(parser.titulo).split("»")[0].split("|")[0].strip()
    hosts = parser.hosts
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
        if getattr(e, "code", None) == 404:
            raise ValueError("conteúdo expirado ou removido no gofile (404)")
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
        if getattr(e, "code", None) == 404:
            raise ValueError("conteúdo expirado ou removido no megadb (404)")
        raise ValueError(f"megadb falhou: {e}")
    if "attachment" in disp or not tipo.startswith("text/html"):
        return {"url": final}
    raise ValueError("megadb protegido (abra a página)")


def _nome_saida(titulo: str, url: str) -> str:
    from bib_nucleo.rede.repacks import ARQUIVO_EXTS
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qs(parsed.query)
    caminho = (query.get("f") or [parsed.path])[0]
    base = PurePosixPath(urllib.parse.unquote(caminho).replace("\\", "/")).name
    base = re.sub(r'[<>:"|?*\x00-\x1f]', "_", base).strip().rstrip(". ")
    if base and Path(base).suffix.lower() in ARQUIVO_EXTS and len(base) < 160:
        return base
    from bib_nucleo.base import slugify
    return (slugify(titulo) or "jogo") + ".rar"


def baixar_steamrip(url_pagina: str, destino=None, host: str = "",
                    progresso=None, timeout: int = 30) -> dict:
    """Baixa o jogo p/ `Piratas/` (FileDitch direto → gofile → megadb).

    `host`: nome preferido (senão ordem `BIBLIOTECA_STEAMRIP_HOSTS`).
    Nunca levanta cru: erro vira {'ok': False, 'erro', 'tentados': [...]}.
    """
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
            res = _descer(direto, det["titulo"], destino, progresso, timeout=timeout)
            if res.get("ok"):
                return {**res, "host": nome, "tentados": tentados}
            erros.append(f"{nome}: {res.get('erro')}")
        except ValueError as e:
            erros.append(f"{nome}: {e}")
            continue
    return {"ok": False,
            "erro": "; ".join(erros[:3]) or "sem hosts",
            "tentados": tentados}


def _mesmo_host(url: str, final: str) -> bool:
    """Redirect ficou no host (tolerando subdomínio/CDN)? Sem info, não acusa."""
    ha = (urllib.parse.urlsplit(url).hostname or "").lower()
    hb = (urllib.parse.urlsplit(final).hostname or "").lower()
    if not ha or not hb:
        return True
    return ha == hb or ha.endswith("." + hb) or hb.endswith("." + ha)


def _descer(url: str, titulo: str, destino, progresso,
            timeout: int = 60) -> dict:
    from bib_nucleo.rede.repacks import pasta_piratas
    base = Path(destino) if destino else pasta_piratas()
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"ok": False, "erro": f"pasta: {e}", "tentados": []}
    nome = _nome_saida(titulo, url)
    alvo = base / nome
    original = Path(nome)
    n = 1
    while alvo.exists():
        n += 1
        alvo = base / f"{original.stem}-{n}{original.suffix}"
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r, destino_temporario(alvo) as tmp:
            final = r.geturl()
            # Host que expira costuma redirecionar para fora (ex.: homepage):
            # HTML fora do host = arquivo morto, não erro de parse.
            expirou = not _mesmo_host(url, final)
            if "text/html" in (r.headers.get("Content-Type") or "").lower():
                raise ValueError("arquivo expirado ou removido no host"
                                 if expirou else "veio HTML em vez de arquivo")
            total = int(r.headers.get("Content-Length") or 0)
            feito = 0
            with tmp.open("wb") as f:
                while True:
                    parte = r.read(512 * 1024)
                    if not parte:
                        break
                    if parte.lstrip()[:15].lower().startswith(
                            (b"<!doctype html", b"<html")) and feito == 0:
                        raise ValueError("arquivo expirado ou removido no host"
                                         if expirou else "veio HTML em vez de arquivo")
                    f.write(parte)
                    feito += len(parte)
                    if progresso:
                        progresso(feito, total)
            if total and feito != total:
                raise ValueError(f"download incompleto ({feito}/{total} B)")
            if feito < 1_000_000:
                raise ValueError("download curto (<1MB)")
    except ValueError as e:
        return {"ok": False, "erro": str(e), "tentados": []}
    except Exception as e:
        return {"ok": False, "erro": f"download: {e}", "tentados": []}
    return {"ok": True, "path": str(alvo), "bytes": alvo.stat().st_size}


FITGIRL_BASE = "https://fitgirl-repacks.site"


def buscar_fitgirl(termo: str, timeout: int = 20) -> dict:
    """[{'titulo', 'url'}] da busca (posts de repack). Erro vira `erros`."""
    termo = (termo or "").strip()
    if not termo:
        return {"itens": [], "erros": ["busca vazia"]}
    try:
        q = urllib.parse.urlencode({"s": termo})
        pagina = _ler(f"{FITGIRL_BASE}/?{q}", timeout=timeout,
                      limite=1_500_000)
    except Exception as e:
        return {"itens": [], "erros": [f"busca falhou: {e}"]}
    itens: list[dict] = []
    vistos: set[str] = set()
    try:
        achados = re.findall(
            r'<h1 class="entry-title"><a href="([^"]+)"[^>]*>(.*?)</a>',
            pagina, re.IGNORECASE | re.DOTALL)
    except re.error:
        return {"itens": [], "erros": ["busca falhou: parse"]}
    for url, resto in achados:
        url = urllib.parse.urljoin(FITGIRL_BASE + "/", url.strip())
        if urllib.parse.urlsplit(url).hostname not in (
                "fitgirl-repacks.site", "www.fitgirl-repacks.site"):
            continue
        if url in vistos:
            continue
        titulo = _limpar(resto)
        if not titulo or len(titulo) < 3:
            continue
        vistos.add(url)
        itens.append({"titulo": titulo, "url": url})
    return {"itens": itens[:30], "erros": []}


def detalhes_fitgirl(url: str, timeout: int = 20) -> dict:
    """{'titulo', 'espelhos': [{'nome','url'}], 'magnets': [...]} do post."""
    try:
        pagina = _ler(url, timeout=timeout, limite=1_500_000)
    except Exception as e:
        raise ValueError(f"página falhou: {e}")
    titulo = ""
    m = re.search(r"<meta\s+property=\"og:title\"\s+content=\"([^\"]+)\"",
                  pagina, re.IGNORECASE)
    if m:
        titulo = _limpar(m.group(1)).split("- FitGirl")[0].strip()
    if not titulo:
        m = re.search(r'<h1 class="entry-title">(.*?)</h1>', pagina,
                      re.IGNORECASE | re.DOTALL)
        titulo = _limpar(m.group(1)) if m else ""
    espelhos: list[dict] = []
    for link, nome in re.findall(
            r'<li><a href="([^"]+)"[^>]*>Filehoster:\s*([^<]+)</a>',
            pagina, re.IGNORECASE):
        nome = re.sub(r"\s+", " ", _limpar(nome)).strip()
        link = link.strip()
        if link.startswith("//"):
            link = "https:" + link
        if link.startswith("http") and nome:
            espelhos.append({"nome": nome, "url": link})
    magnets: list[str] = []
    for link in re.findall(r'href="(magnet:\?[^"]+)"', pagina, re.IGNORECASE):
        link = _limpar(link)
        if link not in magnets:
            magnets.append(link)
    unicos, vistos = [], set()
    for h in espelhos:
        chave = (h["nome"], h["url"])
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(h)
    if not unicos and not magnets:
        raise ValueError("post sem espelhos nem magnets")
    return {"titulo": titulo, "espelhos": unicos, "magnets": magnets}


def nome_magnet(magnet: str) -> str:
    """Nome do torrent pelo parâmetro dn (ou início do hash)."""
    try:
        qs = urllib.parse.parse_qs(urllib.parse.urlsplit(magnet).query)
        nome = (qs.get("dn") or [""])[0].strip()
        if nome:
            return nome[:80]
    except Exception:
        pass
    m = re.search(r"btih:([A-Za-z0-9]+)", magnet or "")
    return m.group(1)[:16] if m else "magnet"


def abrir_url(url: str) -> dict:
    """Entrega URL/magnet ao SO (navegador ou cliente torrent)."""
    if not (url or "").strip():
        return {"ok": False, "erro": "URL vazia"}
    if url.strip().startswith("magnet:?"):
        from bib_nucleo.qbit import qbit_iniciar
        return qbit_iniciar(url.strip())
    try:
        import webbrowser
        ok = webbrowser.open(url.strip())
        return {"ok": bool(ok)}
    except Exception as e:
        return {"ok": False, "erro": f"falha ao abrir: {e}"}


__all__ = ['STEAMRIP_BASE', 'ordem_hosts', 'buscar_steamrip',
           'detalhes_steamrip', 'resolver_gofile', 'resolver_megadb',
           'baixar_steamrip', 'FITGIRL_BASE', 'buscar_fitgirl',
           'detalhes_fitgirl', 'nome_magnet', 'abrir_url',
            'steam_principal', 'ler_wishlist', 'ler_wishlist_arquivo',
            'buscar_jogos_steam']
