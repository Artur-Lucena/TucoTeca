#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Providers, Azahar (manager/install/presets) e execução com vigia."""
from __future__ import annotations

import configparser
import datetime
import json
import os
import shlex
import shutil
import sqlite3
import subprocess
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from bib_nucleo.base import (BACKUP_DIR, LINUX_ROOT, PRESETS_DIR, ROM_EXTS_3DS,
                               WIN_ROOT, existe_aqui_ou_traduzido, resolver_exe, slugify,
                               traduzir_para_atual)
from bib_nucleo.banco import contar_por_origem



def azahar_dir_override() -> Path | None:
    """Destino explícito do portátil, inclusive antes da primeira instalação."""
    env = (os.environ.get("BIBLIOTECA_AZAHAR_DIR") or "").strip()
    if env:
        return Path(env)
    return None



def default_emu_3ds() -> str:
    """Caminho do Azahar neste SO (BIBLIOTECA_EMULADOR_3DS > BIBLIOTECA_AZAHAR_DIR > padrão)."""
    env = os.environ.get("BIBLIOTECA_EMULADOR_3DS")
    if env:
        return env
    ov = azahar_dir_override()
    if ov is not None:
        if os.name == "nt":
            cand = ov / "azahar.exe"
            return str(cand) if cand.is_file() else ""
        imgs = sorted(ov.glob("azahar*.AppImage"))
        if imgs:
            return str(imgs[-1])
        return ""
    if os.name == "nt":
        cand = Path(WIN_ROOT) / "Games/Emuladores/Azahar/azahar.exe"
        return str(cand) if cand.is_file() else ""
    pasta = Path(LINUX_ROOT) / "Games/Emuladores/Azahar"
    if pasta.is_dir():
        imgs = sorted(pasta.glob("azahar*.AppImage"))
        if imgs:
            return str(imgs[-1])
    return ""



def azahar_user_dir(exe: str = "") -> str:
    """Pasta user do Azahar (portátil ao lado do exe vence os padrões do SO)."""
    exe = exe or default_emu_3ds()
    if exe:
        port = Path(exe).parent / "user"
        if port.is_dir():
            return str(port)
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", "")) / "Azahar"
    else:
        base = Path.home() / ".local/share/azahar-emu"
    return str(base) if base.is_dir() else ""



def azahar_status() -> dict:
    """Saúde do Azahar sem abrir nada: instalado, user dir, configurado, chaves."""
    exe = default_emu_3ds()
    st = {"instalado": bool(exe), "exe": exe, "user_dir": "",
          "configurado": False, "chaves": False,
          "versao_local": azahar_versao_local()}
    if not exe:
        return st
    ud = azahar_user_dir(exe)
    st["user_dir"] = ud
    if ud:
        st["configurado"] = (Path(ud) / "config" / "qt-config.ini").is_file()
        st["chaves"] = (Path(ud) / "sysdata" / "aes_keys.txt").is_file()
    return st



# --------------------------------------------------------------------------
# Gerenciador do Azahar: verifica, baixa, confere sha256 e instala sozinho
# --------------------------------------------------------------------------

AZAHAR_API_LATEST = "https://api.github.com/repos/azahar-emu/azahar/releases/latest"

AZAHAR_VERSAO_ARQ = "versao-azahar.txt"



def _emu_dir() -> Path:
    ov = azahar_dir_override()
    if ov is not None:
        return ov  # bundle: atualiza o emulador dentro do pacote
    if os.name == "nt":
        return Path(WIN_ROOT) / "Games/Emuladores/Azahar"
    return Path(LINUX_ROOT) / "Games/Emuladores/Azahar"



def azahar_versao_local() -> str:
    arq = _emu_dir() / AZAHAR_VERSAO_ARQ
    try:
        if arq.is_file():
            return arq.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""



def azahar_release_info(timeout: int = 25) -> dict:
    """{'tag','nome','size','sha256','url'} do asset deste SO, ou {'erro':...}."""
    try:
        with urllib.request.urlopen(AZAHAR_API_LATEST, timeout=timeout) as r:
            rel = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"erro": f"falha de rede: {type(e).__name__}: {e}"}
    tag = (rel.get("tag_name") or "").strip()
    if os.name == "nt":
        casa = lambda n: n.startswith("azahar-windows-msys2-") and n.endswith(".zip")  # noqa: E731
    else:
        casa = lambda n: n == "azahar.AppImage"  # noqa: E731
    for a in rel.get("assets", []):
        nome = a.get("name") or ""
        if casa(nome):
            digest = a.get("digest") or ""
            sha = digest.split(":", 1)[1].strip() if ":" in digest else ""
            return {"tag": tag, "nome": nome, "size": a.get("size") or 0,
                    "sha256": sha, "url": a.get("browser_download_url") or ""}
    return {"erro": "asset deste SO não encontrado no release"}



AZAHAR_EXE_MINIMO = 10_000_000  # sanidade: menor que isso não é o Azahar



def azahar_instalar(info: dict, progresso=None) -> dict:
    """Atualiza o runtime atual com backup, diário e verificação SHA-256."""
    from bib_nucleo.atualizacao import instalar
    return instalar(info, _emu_dir(), progresso)





# --------------------------------------------------------------------------
# DeSmuME (Nintendo DS): provider nº 2, mesma integração do Azahar
# --------------------------------------------------------------------------

DESMUME_API_LATEST = "https://api.github.com/repos/TASEmulators/desmume/releases/latest"
DESMUME_VERSAO_ARQ = "desmume-versao.txt"


def desmume_dir_override() -> Path | None:
    env = (os.environ.get("BIBLIOTECA_DESMUME_DIR") or "").strip()
    if env and Path(env).is_dir():
        return Path(env)
    return None


def desmume_dir() -> Path:
    ov = desmume_dir_override()
    if ov is not None:
        return ov
    if os.name == "nt":
        return Path(WIN_ROOT) / "Games/Emuladores/DeSmuME"
    return Path(LINUX_ROOT) / "Games/Emuladores/DeSmuME"


def default_emu_nds() -> str:
    """Caminho do DeSmuME (BIBLIOTECA_EMULADOR_NDS > DIR > padrão)."""
    env = os.environ.get("BIBLIOTECA_EMULADOR_NDS")
    if env:
        return env
    ov = desmume_dir_override()
    if ov is not None:
        if os.name == "nt":
            cand = ov / "desmume.exe"
            return str(cand) if cand.is_file() else ""
        imgs = sorted(ov.glob("desmume*.AppImage"))
        return str(imgs[-1]) if imgs else ""
    if os.name == "nt":
        cand = Path(WIN_ROOT) / "Games/Emuladores/DeSmuME/desmume.exe"
        return str(cand) if cand.is_file() else ""
    pasta = Path(LINUX_ROOT) / "Games/Emuladores/DeSmuME"
    if pasta.is_dir():
        imgs = sorted(pasta.glob("desmume*.AppImage"))
        if imgs:
            return str(imgs[-1])
    return ""


def desmume_user_dir(exe: str = "") -> str:
    """DeSmuME é portátil por natureza: config (desmume.ini) mora ao lado do exe."""
    exe = exe or default_emu_nds()
    if exe:
        base = Path(exe).parent
        if base.is_dir():
            return str(base)
    return ""


def desmume_versao_local() -> str:
    arq = desmume_dir() / DESMUME_VERSAO_ARQ
    try:
        if arq.is_file():
            return arq.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return ""


def desmume_release_info(timeout: int = 25) -> dict:
    """{'tag','nome','size','sha256','url'} do win64.zip, ou {'erro':...}."""
    try:
        with urllib.request.urlopen(DESMUME_API_LATEST, timeout=timeout) as r:
            rel = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"erro": f"falha de rede: {type(e).__name__}: {e}"}
    tag = (rel.get("tag_name") or "").strip()
    for a in rel.get("assets", []):
        nome = a.get("name") or ""
        if "-win64.zip" in nome:
            digest = a.get("digest") or ""
            sha = digest.split(":", 1)[1].strip() if ":" in digest else ""
            return {"tag": tag, "nome": nome, "size": a.get("size") or 0,
                    "sha256": sha, "url": a.get("browser_download_url") or ""}
    return {"erro": "asset Windows não encontrado no release"}


def desmume_instalar(info: dict, progresso=None) -> dict:
    """Baixa o win64.zip e instala como desmume.exe (transacional, como Azahar)."""
    from bib_nucleo.atualizacao import instalar
    return instalar(info, desmume_dir(), progresso, exe_nomes=("DeSmuME*.exe",),
                    deps=(), renomear_exe="desmume.exe",
                    versao_nome=DESMUME_VERSAO_ARQ)


def desmume_config_atual() -> Path | None:
    ud = desmume_user_dir()
    if ud:
        cfg = Path(ud) / "desmume.ini"
        if cfg.is_file():
            return cfg
    return None


def desmume_flags() -> list[str]:
    """Flags extras ao bootar ROM NDS (padrão tela cheia em janela)."""
    import shlex
    return shlex.split(os.environ.get("BIBLIOTECA_DESMUME_FLAGS", "--windowed-fullscreen"),
                       posix=(os.name != "nt"))


def _prov_desmume() -> dict:
    from bib_nucleo.scans import icone_nds_para_png, ler_metadados_nds
    return {
        "chave": "desmume",
        "nome": "DeSmuME",
        "sistemas": ("Nintendo DS",),
        "origens": ("rom-nds",),
        "origem": "rom-nds",
        "exe": default_emu_nds,           # () -> str
        "user_dir": desmume_user_dir,     # (exe="") -> str
        "saves_subs": (),                 # .dsv mora ao lado da ROM
        "pacote_subs": (),
        "rom_exts": {".nds", ".dsi"},
        "flags": desmume_flags,           # () -> list[str]
        "aplicar_preset": lambda nome: aplicar_preset(nome, "desmume"),
        "release_info": desmume_release_info,
        "versao_local": desmume_versao_local,
        "instalar": desmume_instalar,
        "ler_metadados": ler_metadados_nds,
        "icone": icone_nds_para_png,
        "dica_instalacao": ("DeSmuME não encontrado — instale em "
                            "Games/Emuladores/DeSmuME ou defina BIBLIOTECA_EMULADOR_NDS."),
    }

# --------------------------------------------------------------------------
# Execução de jogos (Windows + Linux)
# --------------------------------------------------------------------------

def _eh_elevacao_necessaria(e: Exception) -> bool:
    return isinstance(e, OSError) and getattr(e, "winerror", None) == 740



def executar_elevado(executable_path: str, launch_options: str = "") -> dict:
    """Relança via UAC (ShellExecute 'runas'). Só Windows. Abre o prompt do UAC."""
    if os.name == "nt":
        import ctypes
        exe = traduzir_para_atual((executable_path or "").strip())
        p = Path(exe)
        if not p.exists():
            return {"ok": False, "erro": f"Executável não encontrado: {exe}"}
        cwd = str(p.parent) if p.parent.exists() else None
        extra = shlex.split(launch_options.strip(), posix=False) if launch_options.strip() else []
        params = subprocess.list2cmdline(extra) or None
        try:
            rc = ctypes.windll.shell32.ShellExecuteW(
                None, "runas", str(p), params, cwd, 1)
            if int(rc) <= 32:
                return {"ok": False, "erro": f"UAC recusou/falhou (código {int(rc)})"}
            return {"ok": True, "modo": "runas-uac"}
        except Exception as e:
            return {"ok": False, "erro": f"{type(e).__name__}: {e}"}
    return {"ok": False, "erro": "elevação só existe no Windows"}



def _lancar(executable_path: str, wine_prefix: str = "", launch_options: str = "",
            elevar: bool = False) -> tuple[dict, object | None]:
    """Núcleo do lançamento. Retorna (resultado, Popen|None).

    Processo None = sem handle rastreável (startfile, UAC, erro, sem exe).
    """
    exe = (executable_path or "").strip()
    if not exe:
        return {"ok": False, "erro": "Jogo sem caminho de executável cadastrado."}, None
    if elevar:
        return executar_elevado(exe, launch_options), None
    exe = traduzir_para_atual(exe)  # gravado num SO, executando no outro
    p = Path(exe)
    if not p.exists():
        return {"ok": False, "erro": f"Executável não encontrado: {exe}"}, None

    env = os.environ.copy()
    if wine_prefix.strip():
        env["WINEPREFIX"] = wine_prefix.strip()

    # Aspas são só agrupamento p/ o split (Popen recebe lista e cita sozinho):
    # "C:\com espaco\jogo.cci" vira um arg limpo, sem aspas literais.
    extra = shlex.split(launch_options, posix=(os.name != "nt")) if launch_options.strip() else []
    if os.name == "nt":
        extra = [(a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'" else a)
                 for a in extra]

    try:
        cwd = str(p.parent) if p.parent.exists() else None
        if os.name == "nt":
            ext = p.suffix.lower()
            if ext in (".lnk", ".url") or p.is_dir():
                os.startfile(str(p))  # type: ignore[attr-defined]
                return {"ok": True, "modo": "startfile"}, None
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            proc = subprocess.Popen([str(p), *extra], cwd=cwd, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, creationflags=creationflags,
                                    close_fds=True)
            return {"ok": True, "modo": "popen-windows"}, proc
        else:
            if not os.access(str(p), os.X_OK):
                return {"ok": False,
                        "erro": f"Sem permissão de execução: {exe} (rode chmod +x?)"}, None
            cmd = [str(p), *extra]
            proc = subprocess.Popen(cmd, cwd=cwd, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, start_new_session=True,
                                    close_fds=True)
            return {"ok": True, "modo": "popen-linux"}, proc
    except Exception as e:
        if _eh_elevacao_necessaria(e):
            return {"ok": False, "requer_elevacao": True,
                    "erro": f"{type(e).__name__}: {e} — o executável exige administrador."}, None
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}, None



def executar_jogo(executable_path: str, wine_prefix: str = "", launch_options: str = "",
                  elevar: bool = False) -> dict:
    res, _proc = _lancar(executable_path, wine_prefix, launch_options, elevar)
    return res



def _lancar_jogo_dict(jogo: dict, elevar: bool = False) -> tuple[dict, object | None]:
    """Resolve o exe do SO atual (exe_win/exe_linux vencem) e lança.

    Origens com provider (ex.: rom-3ds) usam o exe e as flags do provider.
    """
    origem = (jogo.get("origem") or "")
    prov = provedor_por_origem(origem)
    exe, _origem = resolver_exe(jogo)
    if prov is not None:
        from bib_nucleo.atualizacao import recuperar
        recuperacao = recuperar(_emu_dir())
        if not recuperacao["ok"]:
            return {"ok": False, "erro": recuperacao["erro"]}, None
    if not exe and prov is not None:
        exe = prov["exe"]() or ""  # linha sem emu (ou apagado): o instalado vale
    if not exe and prov is not None:
        return {"ok": False, "erro": prov["dica_instalacao"]}, None
    launch = (jogo.get("launch_options") or "")
    if prov is not None and launch.strip():
        launch = montar_launch_rom(prov, traduzir_para_atual(launch))
    return _lancar(exe, (jogo.get("wine_prefix") or ""), launch, elevar=elevar)



def executar_jogo_dict(jogo: dict, elevar: bool = False) -> dict:
    """Resolve o exe do SO atual (exe_win/exe_linux vencem) e executa."""
    res, _proc = _lancar_jogo_dict(jogo, elevar)
    return res



def diagnosticar_exe(jogo: dict) -> dict:
    """Para o perguntar-antes: o exe gravado existe? E o do provider atual?

    estados: 'ok' | 'sem-exe' | 'trocou-emulador' | 'ausente'.
    'trocou-emulador' = gravado sumiu mas o provider atual tem exe válido.
    """
    exe, _origem = resolver_exe(jogo)
    if not exe:
        return {"estado": "sem-exe", "gravado": "", "atual": ""}
    if existe_aqui_ou_traduzido(exe)[0]:
        return {"estado": "ok", "gravado": exe, "atual": exe}
    prov = provedor_por_origem((jogo.get("origem") or ""))
    atual = ""
    if prov is not None:
        try:
            atual = prov["exe"]() or ""
        except Exception:
            atual = ""
    if atual and Path(atual).is_file():
        return {"estado": "trocou-emulador", "gravado": exe, "atual": atual,
                "provider": prov["chave"], "nome": prov["nome"]}
    return {"estado": "ausente", "gravado": exe, "atual": ""}



def diagnosticar_rom(jogo: dict) -> dict:
    """A ROM (launch_options) existe? Se não, procura candidatas pelo nome."""
    launch = (jogo.get("launch_options") or "").strip().strip('"')
    if provedor_por_origem(jogo.get("origem") or "") is None:
        return {"estado": "nao-rom", "candidatos": []}
    if not launch:
        return {"estado": "nao-rom", "candidatos": []}
    if provedor_por_extensao(Path(launch).suffix) is None:
        return {"estado": "nao-rom", "candidatos": []}  # flags de PC, não arquivo
    if existe_aqui_ou_traduzido(launch)[0]:
        return {"estado": "ok", "candidatos": []}
    base = launch.replace("\\", "/").rsplit("/", 1)[-1]
    return {"estado": "rom-ausente", "candidatos": procurar_rom(base) if base else []}



def procurar_rom(nome_arquivo: str, roots: list[str] | None = None,
                 max_resultados: int = 20) -> list[str]:
    """Acha arquivos pelo nome-base nas raízes de ROMs+scan (p/ religar).

    Só leitura, com teto. Compara case-insensitive pelo nome do arquivo.
    """
    from bib_nucleo.scans import (SKIP_DIRS, default_roms_nds_roots,
                                   default_roms_roots, default_scan_roots)
    alvo = (nome_arquivo or "").strip().lower()
    if not alvo:
        return []
    if roots is None:
        vistas: list[str] = []
        for r in default_roms_roots() + default_roms_nds_roots() + default_scan_roots():
            if r not in vistas:
                vistas.append(r)
        roots = vistas
    achados: list[str] = []
    caminhos_vistos = set()
    vistos = 0
    for raiz in roots:
        rp = Path(raiz)
        if not rp.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(rp):
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
            try:
                if len(Path(dirpath).relative_to(rp).parts) > 6:
                    dirnames[:] = []
                    continue
            except ValueError:
                dirnames[:] = []
                continue
            for fn in filenames:
                vistos += 1
                if vistos > 30_000 or len(achados) >= max_resultados:
                    return sorted(achados)
                if fn.lower() == alvo:
                    p = (Path(dirpath) / fn).resolve()
                    if p not in caminhos_vistos:
                        caminhos_vistos.add(p)
                        achados.append(str(p))
    return sorted(achados)



def azahar_flags() -> list[str]:
    """Flags extras ao bootar ROM (padrão -f fullscreen; vazio desliga)."""
    return shlex.split(os.environ.get("BIBLIOTECA_AZAHAR_FLAGS", "-f"),
                       posix=(os.name != "nt"))



# --------------------------------------------------------------------------
# Sessões rastreadas: horas automáticas (mede o processo lançado)
# --------------------------------------------------------------------------

LIMIAR_SESSAO_S = 30  # sessões mais curtas não contam (clique de teste)



def _vigiar_processo(proc, limiar_s: float, ao_fim) -> None:
    t0 = time.monotonic()
    try:
        proc.wait()
    except Exception:
        pass  # processo já morreu ou handle inválido: conta o decorrido
    decorrido = time.monotonic() - t0
    sessao = round(decorrido / 3600.0, 2) if decorrido >= limiar_s else 0.0
    try:
        ao_fim(sessao, True)
    except Exception:
        pass



def executar_monitorado(jogo: dict, ao_fim=None,
                        limiar_s: float = LIMIAR_SESSAO_S) -> dict:
    """Lança e, havendo handle (Popen), vigia o fim em thread daemon.

    ao_fim(sessao_horas, rastreado) roda na thread vigia — o frontend deve
    despachar para a thread de UI. Sem handle (startfile/UAC) e com ok:
    chama ao_fim(0.0, False) direto. Limite honesto: fechar o launcher
    antes do jogo mata a vigia e perde a sessão.
    """
    res, proc = _lancar_jogo_dict(jogo)
    rastreavel = bool(res.get("ok")) and proc is not None
    res["rastreado"] = rastreavel
    if ao_fim is None:
        return res
    if rastreavel:
        threading.Thread(target=_vigiar_processo, args=(proc, limiar_s, ao_fim),
                         daemon=True).start()
    elif res.get("ok"):
        ao_fim(0.0, False)
    return res



# --------------------------------------------------------------------------
# Provedores de emulação (HUB): um registro, N emuladores
#
# Cada provider descreve UM emulador: que origens de jogo ele atende, onde
# está o exe, onde ficam config/saves, como montar a linha de lançamento e
# como aplicar preset. Azahar é o provider nº 1; o próximo (ex.: NDS, GBA)
# entra aqui sem tocar em lançamento, pacote ou frontends.
# --------------------------------------------------------------------------

def _prov_azahar() -> dict:
    from bib_nucleo.scans import icone_rom_para_png, ler_metadados_3ds
    return {
        "chave": "azahar",
        "nome": "Azahar",
        "sistemas": ("Nintendo 3DS",),
        "origens": ("rom-3ds",),
        "origem": "rom-3ds",
        "exe": default_emu_3ds,          # () -> str
        "user_dir": azahar_user_dir,     # (exe="") -> str
        "saves_subs": ("sdmc", "states"),
        "pacote_subs": ("sdmc",),        # states travam à versão: fora do pacote
        "rom_exts": ROM_EXTS_3DS,
        "flags": azahar_flags,           # () -> list[str]
        "aplicar_preset": aplicar_preset,  # (nome) -> dict
        "ler_metadados": ler_metadados_3ds,
        "icone": icone_rom_para_png,
        "release_info": azahar_release_info,
        "versao_local": azahar_versao_local,
        "instalar": azahar_instalar,
        "dica_instalacao": ("Azahar não encontrado — instale em "
                            "Games/Emuladores/Azahar ou defina BIBLIOTECA_EMULADOR_3DS."),
    }



def provedores() -> dict:
    """chave -> spec. Construído sob demanda (as funções existem no import)."""
    return {"azahar": _prov_azahar(), "desmume": _prov_desmume()}



def provedor_por_origem(origem: str) -> dict | None:
    for prov in provedores().values():
        if (origem or "") in prov["origens"]:
            return prov
    return None



def provedor_por_extensao(ext: str) -> dict | None:
    """Provider que abre essa extensão de ROM ('.3ds' -> Azahar). None = PC."""
    ext = (ext or "").strip().lower()
    if not ext.startswith("."):
        ext = "." + ext
    for prov in provedores().values():
        if ext in prov.get("rom_exts", ()):
            return prov
    return None



def provedor_nome(jogo_ou_origem) -> str:
    """'Azahar · Nintendo 3DS' p/ ROMs; origem crua p/ jogos de PC."""
    origem = jogo_ou_origem.get("origem") if isinstance(jogo_ou_origem, dict) \
        else jogo_ou_origem
    prov = provedor_por_origem(origem or "")
    if prov is None:
        return origem or ""
    return f"{prov['nome']} · {'/'.join(prov['sistemas'])}"



def jogos_do_provedor(jogos: list[dict], chave: str) -> list[dict]:
    """Só os jogos que o provider consegue rodar (p/ filtro da UI)."""
    return [j for j in (jogos or [])
            if (provedor_por_origem(j.get("origem") or "") or {}).get("chave") == chave]



def provedores_resumo(con: sqlite3.Connection) -> list[dict]:
    """Um item por provider: chave, nome, sistemas, nº de jogos, instalado."""
    cont = contar_por_origem(con)
    out = []
    for chave, prov in provedores().items():
        n = sum(cont.get(o, 0) for o in prov["origens"])
        try:
            exe = prov["exe"]() or ""
        except Exception:
            exe = ""
        out.append({"chave": chave, "nome": prov["nome"],
                    "sistemas": prov["sistemas"], "n": n,
                    "instalado": bool(exe)})
    return out



def montar_launch_rom(prov: dict, rom_path: str) -> str:
    """flags do provider + ROM entre aspas quando tem espaço."""
    rom = (rom_path or "").strip()
    if " " in rom and not (rom.startswith('"') and rom.endswith('"')):
        rom = f'"{rom}"'
    flags = " ".join(prov["flags"]())
    return (flags + " " if flags else "") + rom



def backup_saves_emu(chave: str, manter: int = 10) -> dict:
    """Zipa as pastas de save do provider em backups/. Retorna dict (sempre)."""
    prov = provedores().get(chave)
    if prov is None:
        return {"ok": False, "erro": f"emulador '{chave}' desconhecido"}
    ud = prov["user_dir"]() or ""
    if not ud:
        return {"ok": False, "erro": f"{prov['nome']} não instalado"}
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"{chave}-saves-{ts}.zip"
    n = 0
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for sub in prov["saves_subs"]:
                d = Path(ud) / sub
                if not d.is_dir():
                    continue
                for f in sorted(d.rglob("*")):
                    if f.is_file():
                        try:
                            z.write(f, f.relative_to(ud))
                            n += 1
                        except OSError:
                            pass
    except OSError as e:
        return {"ok": False, "erro": f"falha ao zipar: {e}"}
    if n == 0:
        try:
            dest.unlink()
        except OSError:
            pass
        return {"ok": False, "erro": "sem saves ainda (saves vazios ou ausentes)"}
    for padrao in (f"{chave}-saves-*.zip", "azahar-saves-*.zip"):
        arqs = sorted(BACKUP_DIR.glob(padrao), key=lambda p: p.name, reverse=True)
        for velho in arqs[manter:]:
            try:
                velho.unlink()
            except OSError:
                pass
    return {"ok": True, "arquivo": str(dest), "arquivos": n}



def backup_saves_azahar(manter: int = 10) -> dict:
    """Zipa sdmc/ + states/ do Azahar em backups/. Retorna dict (sempre)."""
    return backup_saves_emu("azahar", manter)



# --------------------------------------------------------------------------
# Presets por jogo do Azahar (mescla no qt-config.ini antes de lançar)
# --------------------------------------------------------------------------

def presets_dir() -> Path:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return PRESETS_DIR


def presets_prov_dir(chave: str) -> Path:
    d = presets_dir() / chave
    d.mkdir(parents=True, exist_ok=True)
    return d


def presets_dir() -> Path:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return PRESETS_DIR



def listar_presets(chave: str = "azahar") -> list[str]:
    try:
        nomes = [p.stem for p in presets_prov_dir(chave).glob("*.ini") if p.is_file()]
        if chave == "azahar":  # legado: presets/*.ini na raiz valem p/ Azahar
            nomes += [p.stem for p in presets_dir().glob("*.ini") if p.is_file()]
        return sorted(set(nomes))
    except OSError:
        return []



def azahar_config_atual() -> Path | None:
    ud = azahar_user_dir()
    if ud:
        cfgdir = Path(ud) / "config"
        cfg = cfgdir / "qt-config.ini"
        if cfg.is_file():
            return cfg
        try:
            alts = sorted(p for p in cfgdir.glob("*.ini") if p.is_file())
        except OSError:
            alts = []
        if alts:
            return alts[0]
    return None



def salvar_preset_de_atual(nome: str, chave: str = "azahar") -> dict:
    """Fotografa o ini atual como presets/<provider>/<nome>.ini."""
    cfg = config_atual_emu(chave)
    if cfg is None:
        return {"ok": False,
                "erro": f"config não encontrada (abra o {chave} uma vez)."}
    slug = slugify(nome or "")
    if not slug:
        return {"ok": False, "erro": "nome de preset vazio."}
    dest = presets_prov_dir(chave) / f"{slug}.ini"
    try:
        shutil.copy2(str(cfg), str(dest))
    except OSError as e:
        return {"ok": False, "erro": f"falha ao copiar: {e}"}
    return {"ok": True, "preset": slug, "arquivo": str(dest)}


def config_atual_emu(chave: str) -> Path | None:
    if chave == "desmume":
        return desmume_config_atual()
    return azahar_config_atual()


def _alvo_preset(nome: str, chave: str):
    base = presets_prov_dir(chave)
    alvo = base / Path(nome).name
    if not alvo.suffix:
        alvo = alvo.with_name(alvo.name + ".ini")  # aceita stem ou "x.ini"
    if chave == "azahar" and not alvo.is_file():
        leg = presets_dir() / alvo.name  # legado na raiz
        if leg.suffix.lower() == ".ini" and leg.is_file():
            alvo, base = leg, presets_dir()
    try:
        dentro = alvo.resolve().parent == base.resolve()
    except OSError:
        dentro = False
    if not dentro or alvo.suffix.lower() != ".ini" or not alvo.is_file():
        return None
    return alvo


def aplicar_preset(nome: str, chave: str = "azahar") -> dict:
    """Mescla presets/<provider>/<nome>.ini sobre o ini atual (backup .bak uma vez)."""
    nome = (nome or "").strip()
    if not nome:
        return {"ok": False, "erro": "sem preset"}
    alvo = _alvo_preset(nome, chave)
    if alvo is None:
        return {"ok": False, "erro": f"preset '{nome}' não existe."}
    cfg = config_atual_emu(chave)
    if cfg is None:
        return {"ok": False, "erro": "config do emulador não encontrada."}
    try:
        bak = cfg.with_name(cfg.name + ".bak")
        if not bak.is_file():
            shutil.copy2(str(cfg), str(bak))  # estado pré-preset, uma única vez
        atual, novo = configparser.ConfigParser(), configparser.ConfigParser()
        atual.optionxform = str  # type: ignore[assignment]  # preserva maiúsculas
        novo.optionxform = str  # type: ignore[assignment]
        atual.read(cfg, encoding="utf-8")
        novo.read(alvo, encoding="utf-8")
        for sec in novo.sections():
            if not atual.has_section(sec):
                atual.add_section(sec)
            for k, valor in novo.items(sec):
                atual.set(sec, k, valor)
        with cfg.open("w", encoding="utf-8") as fh:
            atual.write(fh)
    except (OSError, configparser.Error) as e:
        return {"ok": False, "erro": f"falha ao mesclar: {e}"}
    return {"ok": True, "preset": alvo.stem, "config": str(cfg)}


def restaurar_config_emu(chave: str) -> dict:
    """Volta o ini ao estado pré-preset (.bak)."""
    cfg = config_atual_emu(chave)
    if cfg is None:
        return {"ok": False, "erro": "config do emulador não encontrada."}
    bak = cfg.with_name(cfg.name + ".bak")
    if not bak.is_file():
        return {"ok": False, "erro": "sem backup pré-preset (.bak ausente)."}
    try:
        shutil.copy2(str(bak), str(cfg))
    except OSError as e:
        return {"ok": False, "erro": f"falha ao restaurar: {e}"}
    return {"ok": True, "config": str(cfg)}


def restaurar_config_azahar() -> dict:
    """Volta o qt-config.ini ao estado pré-preset (.bak)."""
    return restaurar_config_emu("azahar")


def preparar_lancamento(jogo: dict) -> dict:
    """Aplica o preset do provider do jogo. Nunca bloqueia o play."""
    origem = (jogo.get("origem") or "")
    prov = provedor_por_origem(origem)
    if prov is None:
        return {"preset_aplicado": None, "aviso": None}
    avisos: list[str] = []
    aplicado = None
    nome = (jogo.get("azahar_preset") or "").strip()
    if nome:
        r = prov["aplicar_preset"](nome)
        if r.get("ok"):
            aplicado = r["preset"]
        else:
            avisos.append(f"Preset '{nome}' falhou ({r['erro']}); abrindo com config atual.")
    launch = (jogo.get("launch_options") or "").strip()
    if (launch and prov.get("chave") == "azahar"
            and provedor_por_extensao(Path(launch).suffix) is not None):
        if rom_parece_criptografada(launch) and not azahar_tem_chaves():
            avisos.append("ROM parece criptografada e o Azahar está sem aes_keys.txt "
                          "— o jogo não vai abrir. Faça o dump das chaves do seu 3DS "
                          "(GodMode9) para user/sysdata/aes_keys.txt.")
    return {"preset_aplicado": aplicado, "aviso": " ".join(avisos) or None}



def rom_parece_criptografada(rom_path: str) -> bool:
    """ExeFS sem ícone extraível = quase sempre ROM criptografada."""
    rom = (rom_path or "").strip()
    if not rom or not Path(rom).is_file():
        return False  # ausente é outro erro (o play já reporta)
    try:
        from bib_nucleo.scans import _ler_icon_bin
        with Path(rom).open("rb") as f:
            head = f.read(0x200)
            if head[0x100:0x104] == b"NCSD":
                f.seek(int.from_bytes(head[0x120:0x124], "little") * 0x200)
                head = f.read(0x200)
            return (len(head) >= 0x200 and head[0x100:0x104] == b"NCCH"
                    and not bool(head[0x18F] & 0x04))
    except Exception:
        return False



def azahar_tem_chaves() -> bool:
    ud = azahar_user_dir()
    return bool(ud) and (Path(ud) / "sysdata" / "aes_keys.txt").is_file()

__all__ = ['azahar_dir_override', 'default_emu_3ds', 'desmume_dir_override', 'desmume_dir', 'default_emu_nds', 'desmume_user_dir', 'desmume_versao_local', 'desmume_release_info', 'desmume_instalar', 'desmume_config_atual', 'desmume_flags', '_prov_desmume', 'config_atual_emu', 'presets_prov_dir', 'restaurar_config_emu',  'azahar_user_dir', 'azahar_status', 'AZAHAR_API_LATEST', 'AZAHAR_VERSAO_ARQ', '_emu_dir', 'azahar_versao_local', 'azahar_release_info', 'AZAHAR_EXE_MINIMO', 'azahar_instalar', '_eh_elevacao_necessaria', 'executar_elevado', '_lancar', 'executar_jogo', '_lancar_jogo_dict', 'executar_jogo_dict', 'diagnosticar_exe', 'diagnosticar_rom', 'procurar_rom', 'azahar_flags', 'LIMIAR_SESSAO_S', '_vigiar_processo', 'executar_monitorado', '_prov_azahar', 'provedores', 'provedor_por_origem', 'provedor_por_extensao', 'provedor_nome', 'jogos_do_provedor', 'provedores_resumo', 'montar_launch_rom', 'backup_saves_emu', 'backup_saves_azahar', 'presets_dir', 'presets_prov_dir', 'listar_presets', 'azahar_config_atual', 'config_atual_emu', 'salvar_preset_de_atual', 'aplicar_preset', 'restaurar_config_emu', 'restaurar_config_azahar', 'preparar_lancamento', 'rom_parece_criptografada', 'azahar_tem_chaves']
