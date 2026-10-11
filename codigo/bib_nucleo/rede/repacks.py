#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repacks baixados (.rar/.zip/.7z/.iso…): extrai, organiza, acha o exe e importa.

Procedimento padrão do Hub (antiga pasta Meus Jogos Locais, agora em código): extrair com 7z
(Win) ou stdlib (zip), limpar sobras (Read_Me, .url, _redist, setup
redundante), achar o executável principal e importar sem duplicar.
O archive é apagado após verificação do exe. Sem rede, darwin-safe.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import zipfile
from pathlib import Path

ARQUIVO_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz", ".tbz",
                ".txz", ".iso"}

_LIXO_NOMES = re.compile(
    r"(?i)^(read_?me.*|.*\.url|_redist_readme.*|desktop\.ini|thumbs\.db)$")

_SETUP_RE = re.compile(r"(?i)^setup")


NOME_PASTA_JOGOS = "Meus Jogos Locais"
NOME_PASTA_LEGADA = "Piratas"
JOGOS_DIR_ENV = "BIBLIOTECA_JOGOS_DIR"
JOGOS_DIR_ENV_LEGADO = "BIBLIOTECA_PIRATAS"


def _raiz_padrao_jogos() -> Path:
    """Pasta-pai onde a pasta padrão de jogos é criada (`Games/` do SO)."""
    from bib_nucleo.base import LINUX_ROOT, MAC_ROOT, WIN_ROOT, eh_mac
    from bib_nucleo.ferramentas import raiz_runtime, runtime_portatil
    if runtime_portatil():
        return raiz_runtime()
    if eh_mac():
        return Path(MAC_ROOT) / "Games"
    if os.name == "nt":
        return Path(f"{str(WIN_ROOT).rstrip(chr(92))}\\Games")
    return Path(f"{str(LINUX_ROOT).rstrip('/')}/Games")


def pasta_jogos() -> Path:
    """Destino padrão dos downloads de jogos.

    Ordem: `BIBLIOTECA_JOGOS_DIR`, depois `BIBLIOTECA_PIRATAS` (nome legado,
    ainda aceito). Sem override: "Meus Jogos Locais". Se a pasta antiga
    `Piratas` já existe e a nova não, continua usando a antiga: nada é movido
    e os downloads não se dividem entre duas pastas.
    """
    env = os.environ.get(JOGOS_DIR_ENV) or os.environ.get(JOGOS_DIR_ENV_LEGADO)
    if env:
        return Path(env)
    base = _raiz_padrao_jogos()
    nova, antiga = base / NOME_PASTA_JOGOS, base / NOME_PASTA_LEGADA
    if not nova.exists() and antiga.exists():
        return antiga
    return nova


def pasta_piratas() -> Path:
    """Alias legado de `pasta_jogos()`."""
    return pasta_jogos()


def dentro_do_destino(caminho: str | os.PathLike) -> bool:
    """O caminho já está sob a pasta de jogos (critério padrão de todo download)?"""
    try:
        base = pasta_jogos().resolve()
        alvo = Path(caminho).resolve()
        return alvo == base or base in alvo.parents
    except OSError:
        return False


def dentro_de_piratas(caminho: str | os.PathLike) -> bool:
    """Alias legado de `dentro_do_destino()`."""
    return dentro_do_destino(caminho)


def organizar_no_destino(caminho: str | os.PathLike) -> dict:
    """Move pasta/arquivo de jogo p/ a pasta de jogos (padrão p/ todo download fora do lugar).

    Não move o que já está lá. Colisão de nome ganha sufixo -2, -3…
    Aviso honesto: o cliente torrent original perde o rastro (reaponte nele).
    """
    p = Path(caminho)
    if "\x00" in str(caminho):
        return {"ok": False, "erro": "caminho inválido"}
    if not p.exists():
        return {"ok": False, "erro": "caminho sumiu do disco"}
    if dentro_do_destino(p):
        return {"ok": True, "path": str(p), "movido": False}
    base = pasta_jogos().resolve()
    if p.resolve() in base.parents or not p.name or p.resolve() == Path(p.anchor):
        return {"ok": False, "erro": f"A origem é uma raiz/pasta ancestral de {NOME_PASTA_JOGOS}; não pode ser movida para dentro dela."}
    try:
        base.mkdir(parents=True, exist_ok=True)
        dest = base / p.name
        n = 1
        while dest.exists():
            n += 1
            dest = base / f"{p.stem}-{n}{p.suffix}" if p.is_file() else base / f"{p.name}-{n}"
        shutil.move(str(p), str(dest))
    except (OSError, ValueError) as e:
        return {"ok": False, "erro": f"não movi p/ {NOME_PASTA_JOGOS}: {e}"}
    return {"ok": True, "path": str(dest), "movido": True,
            "aviso": "Reaponte o torrent no cliente original (ele perdeu o rastro)."}


def organizar_em_piratas(caminho: str | os.PathLike) -> dict:
    """Alias legado de `organizar_no_destino()`."""
    return organizar_no_destino(caminho)

def ferramenta_7z() -> Path | None:
    """7z p/ rar/7z/iso (override `BIBLIOTECA_7Z`; None = sem extrator)."""
    from bib_nucleo.ferramentas import localizar_ferramenta, runtime_portatil
    env = os.environ.get("BIBLIOTECA_7Z")
    if env:
        # Mesma validação de SO/chmod das demais ferramentas; sem fallback oculto.
        local = localizar_ferramenta("7z")
        return Path(local) if local else None
    local = localizar_ferramenta("7z")
    if local:
        return Path(local)
    if runtime_portatil():
        return None
    if os.name == "nt":
        from bib_nucleo.base import WIN_ROOT
        cand = Path(f"{str(WIN_ROOT).rstrip(chr(92))}\\Games\\ferramentas\\7z.exe")
        if cand.is_file():
            return cand
        for nome in ("7z.exe", "7z"):
            achado = shutil.which(nome)
            if achado:
                return Path(achado)
        return None
    for nome in ("7zr", "7z", "p7zip"):
        achado = shutil.which(nome)
        if achado:
            return Path(achado)
    return None


def eh_pacote_hub(caminho: str | os.PathLike) -> bool:
    """Zip é pacote portátil do Hub (tem biblioteca.json)? Só leitura."""
    from bib_nucleo.pacotes import PACOTE_JSON
    p = Path(caminho)
    if p.suffix.lower() != ".zip" or not p.is_file():
        return False
    try:
        with zipfile.ZipFile(p) as z:
            return any(i.filename == PACOTE_JSON for i in z.infolist())
    except (OSError, zipfile.BadZipFile):
        return False


def _dentro(base: Path, alvo: Path) -> bool:
    """`alvo` resolvido fica dentro de `base`? (anti traversal/symlink)."""
    try:
        braiz = base.resolve()
        return alvo.resolve() == braiz or braiz in alvo.resolve().parents
    except OSError:
        return False


def _iter_reais(base: Path):
    """Arquivos reais da árvore (não desce em symlink, ignora links)."""
    raiz = Path(base)
    for pasta, dirs, arqs in os.walk(raiz, followlinks=False):
        dirs[:] = [d for d in dirs
                   if not Path(pasta, d).is_symlink()
                   and d.lower() != ".hub-lixo"]
        for nome in arqs:
            p = Path(pasta, nome)
            try:
                if p.is_symlink() or not p.is_file():
                    continue
            except OSError:
                continue
            if _dentro(raiz, p):
                yield p


def _so_dentro(destino: Path) -> bool:
    """Tudo extraído (incl. links) contido em `destino`?"""
    raiz = Path(destino)
    try:
        for pasta, dirs, arqs in os.walk(raiz, followlinks=False):
            for nome in (*dirs, *arqs):
                if not _dentro(raiz, Path(pasta, nome)):
                    return False
    except OSError:
        return False
    return True


def extrair_arquivo(origem: str | os.PathLike, destino: Path) -> dict:
    """Extrai p/ `destino` (cria). .zip via stdlib; resto via 7z.

    Nunca executa nada extraído; traversal/symlink p/ fora é rejeitado
    (zip validado antes, 7z verificado depois de extrair).
    """
    src = Path(origem)
    destino = Path(destino)
    if not src.is_file():
        return {"ok": False, "erro": "arquivo não encontrado."}
    try:
        destino.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"ok": False, "erro": f"falha ao criar destino: {e}"}
    if src.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(src) as z:
                for i in z.infolist():
                    partes = Path(i.filename.replace("\\", "/")).parts
                    if (not partes or ".." in partes
                            or i.filename.startswith(("/", "\\"))
                            or any(":" in p for p in partes)):
                        try:
                            destino.rmdir()  # só criamos: vazio, sem dono
                        except OSError:
                            pass
                        return {"ok": False,
                                "erro": "zip com caminho inválido."}
                z.extractall(destino)
        except (OSError, zipfile.BadZipFile) as e:
            return {"ok": False, "erro": f"zip inválido: {e}"}
        if not _so_dentro(destino):
            shutil.rmtree(destino, ignore_errors=True)
            return {"ok": False, "erro": "zip com link p/ fora."}
        return {"ok": True, "destino": str(destino)}
    exe7z = ferramenta_7z()
    if exe7z is None:
        return {"ok": False,
                "erro": ("sem extrator p/ este formato (instale o 7-Zip "
                         "ou defina BIBLIOTECA_7Z).")}
    try:
        r = subprocess.run([str(exe7z), "x", str(src), f"-o{destino}", "-y"],
                           capture_output=True, text=True, timeout=3600)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "erro": f"falha ao extrair: {e}"}
    if r.returncode != 0:
        detalhe = (r.stderr or r.stdout or "")[-300:]
        return {"ok": False, "erro": f"extrator falhou: {detalhe}"}
    if not _so_dentro(destino):
        shutil.rmtree(destino, ignore_errors=True)
        return {"ok": False,
                "erro": "archive com caminho/link p/ fora da pasta."}
    return {"ok": True, "destino": str(destino)}


def _pasta_conteudo(raiz: Path) -> Path:
    """Desembrulha níveis vazios, sem alterar arquivos antes da detecção."""
    pasta = Path(raiz)
    # desce enquanto houver só 1 subpasta e nenhum exe no nível
    while True:
        try:
            filhos = list(pasta.iterdir())
        except OSError:
            break
        exes = [f for f in filhos
                if f.is_file() and f.suffix.lower() == ".exe"]
        dirs = [f for f in filhos if f.is_dir() and not f.is_symlink()]
        if len(dirs) == 1 and not exes and not any(
                f.is_file() for f in filhos):
            pasta = dirs[0]
        else:
            break
    return pasta


def organizar_extraido(raiz: Path) -> dict:
    """Desembrulha pasta única, limpa sobras. Retorna {pasta, avisos, ...}.

    Mantém `_CommonRedist` do jogo, OSTs, `.bak`s e saves; apaga `Read_Me`,
    `.url`, `_redist_readme` e `_CommonRedist` idêntico da raiz.
    """
    avisos: list[str] = []
    pasta = _pasta_conteudo(raiz)
    removidos = 0
    for p in sorted(_iter_reais(pasta)):
        if _LIXO_NOMES.match(p.name):
            try:
                p.unlink()
                removidos += 1
            except OSError:
                pass
    if removidos:
        avisos.append(f"{removidos} sobra(s) apagada(s).")
    # _CommonRedist duplicado da raiz: mantém os mais fundos
    redists = []
    for _pasta, _dirs, _ in os.walk(pasta, followlinks=False):
        _dirs[:] = [d for d in _dirs
                    if not Path(_pasta, d).is_symlink()]
        for d in _dirs:
            if d.lower() == "_commonredist":
                redists.append(Path(_pasta, d))
    for d in redists:
        # Mesmo nome/profundidade não prova duplicata entre jogos diferentes.
        if d.parent != pasta or not _dentro(pasta, d):
            continue
        if any(outro != d and _pastas_iguais(d, outro) for outro in redists):
            try:
                shutil.rmtree(d)
                avisos.append("_CommonRedist idêntico da raiz apagado.")
            except OSError as e:
                avisos.append(f"Não foi possível limpar _CommonRedist: {e}")
    return {"pasta": str(pasta), "avisos": avisos}


def _pastas_iguais(a: Path, b: Path) -> bool:
    """Compara arquivos por caminho, tamanho e SHA-256 antes de limpar."""
    if not _so_dentro(a) or not _so_dentro(b):
        return False
    try:
        aa = {p.relative_to(a): p for p in _iter_reais(a)}
        bb = {p.relative_to(b): p for p in _iter_reais(b)}
        if not aa or aa.keys() != bb.keys():
            return False
        for nome, pa in aa.items():
            pb = bb[nome]
            if pa.stat().st_size != pb.stat().st_size:
                return False
            hashes = []
            for p in (pa, pb):
                h = hashlib.sha256()
                with p.open("rb") as f:
                    for bloco in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(bloco)
                hashes.append(h.digest())
            if hashes[0] != hashes[1]:
                return False
        return True
    except OSError:
        return False


_REP_TAGS = re.compile(
    r"(?i)\s+(steam\s*rip(\s*com)?|fitgirl(\s+repack)?|dodi(\s+repacks?)?|"
    r"xatab|gog|tinyrepacks|rune|codex|plaza|skidrow|fairlight|"
    r"elamigos|kaoskrew|corepack|vankevil|repack(\s+\w+)?)$")


def _titulo_pasta(pasta: Path) -> str:
    """Título da pasta limpo de tags de repack ([FitGirl], -SteamRIP...)."""
    nome = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", pasta.name)
    nome = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", nome)
    nome = re.sub(r"(?<=[A-Za-z])(?=[0-9])", " ", nome)
    nome = nome.replace("_", " ").replace(".", " ").replace("-", " ")
    nome = re.sub(r"\s+", " ", nome).strip()
    nome = _REP_TAGS.sub("", nome).strip()
    return re.sub(r"\s+", " ", nome).strip()


def _pontuar_exe(p: Path, pasta: Path) -> float:
    from bib_nucleo.scans import SKIP_EXE_RE
    nome = p.name
    if SKIP_EXE_RE.search(nome):
        return -1.0
    pontos = 0.0
    try:
        pontos += min(50.0, p.stat().st_size / (50 * 1024 * 1024))
    except OSError:
        pass
    slug_pasta = re.sub(r"[^a-z0-9]+", "", pasta.name.lower())
    slug_exe = re.sub(r"[^a-z0-9]+", "", p.stem.lower())
    if slug_pasta and (slug_pasta in slug_exe or slug_exe in slug_pasta):
        pontos += 30.0
    try:
        rel = len(p.relative_to(pasta).parts)
    except ValueError:
        rel = 9
    pontos -= min(9.0, float(max(0, rel - 1)) * 3.0)
    # Piso 0: um exe pequeno ou em subpasta não pode desaparecer da lista
    # (antes, 2 bytes em sub/ davam nota -3 e sumiam). Instaladores e lixo
    # continuam barrados por SKIP_EXE_RE; o ranking segue preferindo exe
    # grande na raiz.
    return max(0.0, pontos)


def achar_exe(pasta: str | os.PathLike) -> dict:
    """Melhor .exe jogável (fora _CommonRedist e instaladores). Só leitura."""
    base = Path(pasta)
    cands: list[tuple[float, Path]] = []
    try:
        arquivos = [p for p in _iter_reais(base)
                     if p.suffix.lower() == ".exe"]
    except OSError as e:
        return {"ok": False, "erro": f"falha ao varrer: {e}"}
    for exe in arquivos:
        if "commonredist" in (part.lower() for part in exe.parts):
            continue
        nota = _pontuar_exe(exe, base)
        if nota >= 0:
            cands.append((nota, exe))
    if not cands:
        # sem exe jogável: há setup? (jogo precisa instalar)
        setups = [p for p in arquivos
                  if _SETUP_RE.search(p.name) and p.is_file()]
        if setups:
            return {"ok": False, "precisa_instalar": True,
                    "erro": ("só há instalador (setup) — instale o jogo "
                             "antes de importar.")}
        return {"ok": False, "erro": "nenhum executável jogável achado."}
    cands.sort(key=lambda t: -t[0])
    return {"ok": True, "exe": str(cands[0][1]),
            "candidatos": len(cands)}


def _quarentenar_setups(pasta: Path) -> int:
    """Move `setup_*.exe` p/ `.hub-lixo/` (reversível). Retorna quantos."""
    dest = Path(pasta) / ".hub-lixo"
    n = 0
    for p in _iter_reais(pasta):
        if not (_SETUP_RE.search(p.name) and p.suffix.lower() == ".exe"):
            continue
        try:
            if not _dentro(pasta, p):
                continue
            dest.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest / p.name))
            n += 1
        except OSError:
            pass
    return n


def sanear_pasta(pasta: str | os.PathLike) -> dict:
    """Acha a pasta do jogo e limpa installers/sobras (reversível).

    Reusa `organizar_extraido` (desce pasta única + lixo + redist dup);
    com exe jogável, quarentena `setup_*.exe` em `.hub-lixo` (desfazível);
    sem exe, preserva os setups e avisa `precisa_instalar`.
    """
    base = Path(pasta)
    if not base.is_dir():
        return {"ok": False, "erro": "pasta não encontrada."}
    base = _pasta_conteudo(base)
    ach = achar_exe(base)
    if not ach.get("ok"):
        if ach.get("precisa_instalar"):
            return {"ok": True, "pasta": str(base), "exe": None,
                    "precisa_instalar": True, "quarentenados": 0,
                    "avisos": ["só há instalador — pasta preservada."]}
        return {"ok": False, "erro": ach.get("erro", "sem executável."), "pasta": str(base)}
    org = organizar_extraido(base)
    certa = Path(org.get("pasta") or str(base))
    avisos = list(org.get("avisos") or [])
    ach = achar_exe(certa)
    if not ach.get("ok"):
        if ach.get("precisa_instalar"):
            return {"ok": True, "pasta": str(certa), "exe": None,
                    "precisa_instalar": True, "quarentenados": 0,
                    "avisos": avisos + ["só há instalador — setups preservados."]}
        return {"ok": False, "erro": ach.get("erro", "sem executável."),
                "pasta": str(certa)}
    n = _quarentenar_setups(certa)
    if n:
        avisos.append(f"{n} installer(s) em .hub-lixo (reversível).")
    return {"ok": True, "pasta": str(certa), "exe": ach["exe"],
            "precisa_instalar": False, "quarentenados": n, "avisos": avisos}


def importar_repack(con: sqlite3.Connection, arquivo: str | os.PathLike,
                    destino_raiz: str | os.PathLike | None = None) -> dict:
    """Pipeline completo: extrai → organiza → acha exe → importa → apaga arq.

    O archive original é apagado SÓ após exe verificado e importação ok.
    """
    from bib_nucleo import banco as B
    from bib_nucleo.base import slugify
    from bib_nucleo.scans import _titulo_de_exe, importar_lista, pontuar
    from bib_nucleo.scans import canonizar_steam
    src = Path((str(arquivo) or "").strip())
    if not src.is_file():
        return {"ok": False, "erro": "arquivo não encontrado."}
    if src.suffix.lower() not in ARQUIVO_EXTS:
        return {"ok": False,
                "erro": f"extensão '{src.suffix}' não é pacote de jogo."}
    raiz = Path(destino_raiz) if destino_raiz else pasta_jogos()
    nome = slugify(src.stem) or "jogo"
    dest = raiz / nome
    if dest.exists():
        n = 1
        while (raiz / f"{nome}-{n}").exists():
            n += 1
        dest = raiz / f"{nome}-{n}"
    r = extrair_arquivo(src, dest)
    if not r.get("ok"):
        try:
            shutil.rmtree(dest, ignore_errors=True)
        except OSError:
            pass
        return {"ok": False, "erro": r["erro"]}
    try:
        org = organizar_extraido(dest)
        pasta = Path(org["pasta"])
        ach = achar_exe(pasta)
        if not ach.get("ok"):
            return {"ok": False, "erro": ach["erro"],
                    "pasta": str(pasta),
                    "precisa_instalar": bool(ach.get("precisa_instalar")),
                    "avisos": org["avisos"]}
        apagados = _quarentenar_setups(pasta)
        exe = Path(ach["exe"])
        titulo = _titulo_de_exe(exe)
        pasta_limpo = _titulo_pasta(pasta)
        alnum = re.sub(r"[^a-z0-9]+", "", pasta_limpo.lower())
        if len(pasta_limpo) > len(titulo) and alnum.startswith(
                re.sub(r"[^a-z0-9]+", "", titulo.lower())):
            titulo = pasta_limpo  # pasta diz mais ("CoolGame" > "Cool")
        if titulo.lower() in ("setup", "install", "") or len(titulo) < 2:
            titulo = pasta_limpo or pasta.name
        try:  # nome canônico + appid da loja (padrão; offline preserva local)
            appid_canon, nome_canon = canonizar_steam(titulo, pasta_limpo)
        except Exception:
            appid_canon, nome_canon = "", ""
        if appid_canon:
            titulo, shop_canon, obj_canon = (nome_canon or titulo), "steam", appid_canon
        else:
            shop_canon, obj_canon = "", ""
        item = pontuar({"titulo": titulo, "executable_path": str(exe),
                        "shop": shop_canon, "object_id": obj_canon, "horas": 0.0,
                        "origem": "repack"})
        res = importar_lista(con, [item])
        if res.get("erros") or not (res.get("novos") or res.get("ignorados")):
            return {"ok": False, "erro": "; ".join(res.get("erros") or ["importação não concluída"]),
                    "pasta": str(pasta), "avisos": org["avisos"]}
        capa_auto = False
        try:
            got = B.listar_jogos(con, q=titulo)
            if res.get("novos") and got and not got[0].get("capa"):
                capa_auto = bool(_capa_automatica(con, got[0]["id"], titulo))
        except Exception:
            capa_auto = False
        try:
            src.unlink()
            apagou_arq = True
        except OSError:
            apagou_arq = False
        out = {"ok": True, "pasta": str(pasta), "exe": str(exe),
               "titulo": titulo, "novos": res.get("novos", 0),
               "ignorados": res.get("ignorados", 0),
               "erros": res.get("erros", []),
               "capa_pendente": bool(res.get("novos")) and not capa_auto,
               "capa_auto": capa_auto,
               "apagou_arquivo": apagou_arq,
               "setups_quarentena": apagados,
               "avisos": org["avisos"]}
        if capa_auto:
            out["avisos"] = [*org["avisos"], "capa Steam automática ✓"]
        if not res.get("novos"):
            out["capa_pendente"] = False
        return out
    except Exception as e:
        return {"ok": False, "erro": f"{type(e).__name__}: {e}",
                "pasta": str(dest)}


def _capa_automatica(con: sqlite3.Connection, gid: int, titulo: str) -> bool:
    """Baixa capa Steam pelo título (padrão do import). Nunca levanta."""
    from bib_nucleo.scans import _appid_steam_por_titulo, _capa_steam
    try:
        appid = _appid_steam_por_titulo(titulo)
        if not appid:
            return False
        raw = _capa_steam(appid)
        if not raw:
            return False
        from bib_nucleo.banco import salvar_capa_bytes
        return bool(salvar_capa_bytes(con, gid, f"{appid}.jpg", raw).get("ok"))
    except Exception:
        return False


__all__ = ['ARQUIVO_EXTS', 'pasta_jogos', 'pasta_piratas', 'dentro_do_destino',
           'dentro_de_piratas', 'organizar_no_destino', 'organizar_em_piratas',
           'ferramenta_7z', 'eh_pacote_hub',
           'extrair_arquivo', 'organizar_extraido', 'achar_exe',
           'sanear_pasta', 'importar_repack']
