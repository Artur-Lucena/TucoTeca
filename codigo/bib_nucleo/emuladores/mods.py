#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emuladores: mods do Azahar (LayeredFS) — biblioteca no HUB + ativação."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from bib_nucleo import emuladores as _E
from bib_nucleo.cheats import titulo_ok
from bib_nucleo.emuladores.azahar import azahar_mods_dir
from bib_nucleo.emuladores.provedores import (
    provedor_por_extensao,
    provedor_por_origem,
)

# --------------------------------------------------------------------------
# Mods do Azahar (LayeredFS): biblioteca no HUB + ativação via junction
#
# Biblioteca: dados/mods/azahar/<title-id>/<mod>/{romfs,exefs,code.ips}.
# O Azahar lê tudo em user/load/mods/<title-id>/; o play apaga só os
# links do HUB e recria os ativos (pastas reais nunca são removidas).
# --------------------------------------------------------------------------

def title_id_da_rom(rom_path: str) -> str:
    """Title ID (16 hex) lido do header NCCH; '' se ilegível."""
    rom = (rom_path or "").strip().strip("\"'")
    if not rom:
        return ""
    try:
        with Path(rom).open("rb") as f:
            head = f.read(0x200)
            if len(head) < 0x200:
                return ""
            if head[0x100:0x104] == b"NCSD":
                base = int.from_bytes(head[0x120:0x124], "little") * 0x200
                f.seek(base)
                head = f.read(0x200)
                if len(head) < 0x200:
                    return ""
            if head[0x100:0x104] != b"NCCH":
                return ""
            return head[0x118:0x120][::-1].hex().upper()
    except (OSError, ValueError):
        return ""


def mods_lib_dir() -> Path:
    from bib_nucleo.base import MODS_DIR
    d = MODS_DIR / "azahar"
    d.mkdir(parents=True, exist_ok=True)
    return d


def mods_titulo_dir(title_id: str) -> Path:
    tid = titulo_ok(title_id)
    if not tid:
        raise ValueError("title ID inválido")
    d = mods_lib_dir() / tid
    d.mkdir(parents=True, exist_ok=True)
    return d


def _k32():
    """kernel32 com assinaturas explícitas (sem elas, ctypes trunca ponteiro)."""
    import ctypes
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.GetFileAttributesW.argtypes = [ctypes.c_wchar_p]
    k32.GetFileAttributesW.restype = ctypes.c_uint32
    k32.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32,
                                ctypes.c_uint32, ctypes.c_void_p,
                                ctypes.c_uint32, ctypes.c_uint32,
                                ctypes.c_void_p]
    k32.CreateFileW.restype = ctypes.c_void_p
    k32.DeviceIoControl.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                    ctypes.c_void_p, ctypes.c_uint32,
                                    ctypes.c_void_p, ctypes.c_uint32,
                                    ctypes.POINTER(ctypes.c_ulong),
                                    ctypes.c_void_p]
    k32.DeviceIoControl.restype = ctypes.c_bool
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    k32.CloseHandle.restype = ctypes.c_bool
    return k32


def _eh_reparse(p: Path) -> bool:
    """É junction/symlink (link do HUB) e não pasta real?"""
    try:
        if _E.os.name == "nt":
            attrs = _k32().GetFileAttributesW(str(p))
            return attrs != 0xFFFFFFFF and bool(attrs & 0x400)
        return p.is_symlink()
    except OSError:
        return False


def remover_link(link: str) -> None:
    """Remove junction/symlink sem tocar no alvo. Só age em reparse point."""
    alvo = Path(link)
    if _E._eh_reparse(alvo):
        try:
            if alvo.is_symlink():
                alvo.unlink()
            else:
                _E.os.rmdir(alvo)  # junction NTFS
        except OSError as e:
            raise OSError(f"não removi {link}: {e}")


def _eh_mod_valido(p: Path) -> bool:
    try:
        if not p.is_dir() or _E._eh_reparse(p):
            return False
        return ((p / "romfs").is_dir() or (p / "exefs").is_dir()
                or (p / "code.ips").is_file())
    except OSError:
        return False


def listar_mods(title_id: str) -> list[str]:
    """Nomes dos mods na biblioteca p/ este title ID (ordenados)."""
    tid = titulo_ok(title_id)
    if not tid:
        return []
    try:
        base = mods_lib_dir() / tid
        if not base.is_dir():
            return []
        return sorted(p.name for p in base.iterdir() if _eh_mod_valido(p))
    except OSError:
        return []


def remover_mod(title_id: str, nome: str) -> dict:
    """Apaga um mod da biblioteca (só dentro dela; nunca no Azahar)."""
    tid = titulo_ok(title_id)
    if not tid:
        return {"ok": False, "erro": "title ID inválido"}
    alvo = mods_lib_dir() / tid / Path(nome or "").name
    try:
        dentro = alvo.resolve().parent == (mods_lib_dir() / tid).resolve()
    except OSError:
        dentro = False
    if not dentro or not alvo.is_dir() or _E._eh_reparse(alvo):
        return {"ok": False, "erro": f"mod '{nome}' não existe na biblioteca."}
    try:
        shutil.rmtree(alvo)
    except OSError as e:
        return {"ok": False, "erro": f"falha ao apagar: {e}"}
    return {"ok": True, "mod": alvo.name}


def mods_ativos(jogo: dict) -> list[str]:
    from bib_nucleo.banco import mods_de
    return mods_de(jogo)


def _ler_manifesto(pasta: Path) -> dict:
    """Manifesto do HUB (.hub-mods.json): {'mods': [...], 'arquivos': [...] }."""
    import json as _json
    try:
        d = _json.loads((pasta / ".hub-mods.json").read_text(encoding="utf-8"))
        if isinstance(d, dict) and isinstance(d.get("mods"), list) \
                and isinstance(d.get("arquivos"), list):
            return {"mods": [m for m in d["mods"] if isinstance(m, str)],
                    "arquivos": [a for a in d["arquivos"] if isinstance(a, str)],
                    "fontes": d.get("fontes"), "completo": d.get("completo", False)}
    except (OSError, ValueError):
        pass
    return {"mods": [], "arquivos": [], "fontes": None, "completo": False}


def _gravar_manifesto(pasta: Path, mods: list[str], arquivos: list[str],
                     fontes=None, completo=False) -> None:
    """Grava (ou remove, se vazio) o manifesto do HUB. Nunca levanta."""
    import json as _json
    alvo = pasta / ".hub-mods.json"
    try:
        if not mods and not arquivos:
            try:
                alvo.unlink()
            except OSError:
                pass
            return
        tmp = pasta / ".hub-mods.tmp"
        tmp.write_text(_json.dumps({"mods": mods, "arquivos": arquivos,
                                   "fontes": fontes, "completo": completo},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(alvo)
    except OSError:
        pass


def _limpar_hub(pasta: Path, disponiveis: set[str]) -> list[str]:
    """Remove junctions legadas do HUB e arquivos do manifesto anterior.

    Pastas/arquivos do usuário (fora do manifesto, sem ser link com nome
    de mod da biblioteca) nunca são tocados. Retorna avisos.
    """
    avisos: list[str] = []
    mani = _ler_manifesto(pasta)
    for rel in mani["arquivos"]:
        alvo = pasta / Path(*Path(rel).parts)
        try:
            dentro = alvo.resolve().parent == pasta.resolve() \
                or pasta.resolve() in alvo.resolve().parents
        except OSError:
            dentro = False
        if not dentro or _E._eh_reparse(alvo):
            continue
        try:
            if alvo.is_file():
                alvo.unlink()
        except OSError as e:
            avisos.append(f"resto '{rel}' não saiu ({e})")
    try:
        for item in sorted(pasta.iterdir()):
            if item.name in (".hub-mods.json", ".hub-mods.tmp"):
                continue
            if _E._eh_reparse(item) and item.name in disponiveis:
                try:
                    remover_link(str(item))
                except OSError as e:
                    avisos.append(f"link antigo '{item.name}' não saiu ({e})")
                    continue
            try:
                if item.is_dir() and not any(item.iterdir()):
                    item.rmdir()  # dir vazio (sobra de link/junction): some
            except OSError:
                pass
    except OSError as e:
        avisos.append(f"limpeza incompleta ({e})")
    _gravar_manifesto(pasta, [], [])
    return avisos


def aplicar_mods(jogo: dict) -> dict:
    """Copia os mods ativos p/ load/mods/<tid>/ (flat, como o Azahar lê).

    Nunca bloqueia o play. Retorna {'aplicados': [...], 'aviso': None|str}.
    Mods empilham na ordem da lista (o último vence por arquivo). Arquivos
    do usuário fora do manifesto nunca são removidos.
    """
    if provedor_por_origem((jogo.get("origem") or "")) is None:
        return {"aplicados": [], "aviso": None}
    launch = ((jogo.get("launch_options") or "").strip()
              .strip("\"'"))
    if provedor_por_extensao(Path(launch).suffix) is None:
        return {"aplicados": [], "aviso": None}
    tid = _E.title_id_da_rom(_E.traduzir_para_atual(launch))
    if not tid:
        return {"aplicados": [], "aviso": None}
    destino = azahar_mods_dir()
    if not destino:
        return {"aplicados": [],
                "aviso": "Azahar não encontrado — mods não aplicados."}
    avisos: list[str] = []
    aplicados: list[str] = []
    try:
        pasta = Path(destino) / tid
        pasta.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"aplicados": [], "aviso": f"pasta de mods inacessível ({e})"}
    disponiveis = set(listar_mods(tid))
    anterior = _ler_manifesto(pasta)
    try:
        desligados = int(jogo.get("azahar_mods_off") or 0) != 0
    except (TypeError, ValueError):
        desligados = False
    pedidos = [] if desligados else [m for m in mods_ativos(jogo)]
    for nome in pedidos:
        if nome not in disponiveis:
            avisos.append(f"mod '{nome}' marcado mas fora da biblioteca")
    pedidos = [m for m in pedidos if m in disponiveis]
    fontes = []
    try:
        for nome in pedidos:
            origem = mods_lib_dir() / tid / nome
            for arq in sorted(origem.rglob("*")):
                if arq.is_file() and not _E._eh_reparse(arq):
                    st = arq.stat()
                    fontes.append([nome, arq.relative_to(origem).as_posix(), st.st_size, st.st_mtime_ns])
    except OSError as e:
        return {"aplicados": anterior["mods"], "aviso": f"Mods não atualizados: {e}"}
    if (pedidos and anterior["mods"] == pedidos and anterior["completo"]
            and anterior["fontes"] == fontes
            and all((pasta / a).is_file() for a in anterior["arquivos"])):
        return {"aplicados": list(pedidos), "aviso": "; ".join(avisos) or None}
    gerenciados = set(anterior["arquivos"])
    avisos += _limpar_hub(pasta, disponiveis)
    if not pedidos:
        return {"aplicados": [], "aviso": "; ".join(avisos) or None}
    arquivos: list[str] = []
    vistos: set[str] = set()
    for nome in pedidos:
        src = mods_lib_dir() / tid / nome
        try:
            for arq in sorted(src.rglob("*")):
                if not arq.is_file() or _E._eh_reparse(arq):
                    continue
                try:
                    rel = arq.relative_to(src).as_posix()
                except ValueError:
                    continue
                dest = pasta / Path(*Path(rel).parts)
                try:
                    if dest.exists() and rel not in gerenciados and rel not in vistos:
                        avisos.append(f"mod '{nome}': '{rel}' já existe fora do Hub; preservado")
                        continue
                    if pasta.resolve() not in dest.resolve().parents or _E._eh_reparse(dest):
                        avisos.append(f"mod '{nome}': destino de '{rel}' é um link; preservado")
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(arq, dest)
                except OSError as e:
                    avisos.append(f"mod '{nome}': {rel} não copiou ({e})")
                    continue
                if rel not in vistos:
                    vistos.add(rel)
                    arquivos.append(rel)
            aplicados.append(nome)
        except OSError as e:
            avisos.append(f"mod '{nome}' não ativou ({e})")
    _gravar_manifesto(pasta, pedidos, arquivos, fontes=fontes, completo=not avisos)
    return {"aplicados": aplicados, "aviso": "; ".join(avisos) or None}


def _bin_7z() -> str:
    """7z do Hub (Windows) ou do sistema; '' se ausente."""
    if _E.os.name == "nt":
        cand = Path(_E.WIN_ROOT) / "Games/ferramentas/7z.exe"
        if cand.is_file():
            return str(cand)
    return shutil.which("7z") or shutil.which("7zz") or ""


def _extrair_arquivo(arq: str, destino: Path) -> None:
    baixo = arq.lower()
    if baixo.endswith(".zip"):
        import zipfile
        with zipfile.ZipFile(arq) as z:
            for m in z.namelist():
                alvo = (destino / m)
                if not str(alvo.resolve()).startswith(str(destino.resolve())):
                    raise OSError(f"entrada suspeita no zip: {m}")
            z.extractall(destino)
        return
    sete = _bin_7z()
    if not sete:
        raise OSError("archive precisa do 7z (só .zip sem ele"
                      + ("; no Linux instale o p7zip" if _E.os.name != "nt" else "") + ")")
    from bib_nucleo.processos import opcoes_sem_janela
    r = subprocess.run([sete, "x", arq, f"-o{destino}", "-y"],
                       capture_output=True, text=True, timeout=600,
                       **opcoes_sem_janela())
    if r.returncode != 0:
        raise OSError(f"7z falhou ({r.returncode}): {(r.stderr or '').strip()[:200]}")


def _raiz_layeredfs(base: Path) -> tuple[Path | None, str]:
    """(pasta do mod, title-id do caminho luma|) procurando até 3 níveis.

    Ordem: caminho luma/titles/<id> vence; depois raiz com arquivos;
    depois qualquer raiz; por fim conteúdo nu (ex.: 'a/' sem romfs/).
    """
    cands: list[tuple[Path, str, bool]] = []
    nu: Path | None = None
    for raiz, _dirs, _arqs in _E.os.walk(base):
        try:
            rel = Path(raiz).relative_to(base)
        except ValueError:
            continue
        if len(rel.parts) > 3:
            continue
        p = Path(raiz)
        try:
            baixo = {q.name.lower() for q in p.iterdir()}
        except OSError:
            continue
        tid = ""
        partes = p.parts
        if "luma" in partes and "titles" in partes:
            try:
                i = list(partes).index("titles")
                cand = str(partes[i + 1]).upper()
                if len(cand) == 16 and all(c in "0123456789ABCDEF" for c in cand):
                    tid = cand
            except IndexError:
                pass
        if "romfs" in baixo or "exefs" in baixo or "code.ips" in baixo or tid:
            try:
                tem = any(f.is_file() for f in p.rglob("*"))
            except OSError:
                tem = False
            cands.append((p, tid, tem))
        elif nu is None and _tem_conteudo_nu(p):
            nu = p
    for p, tid, _tem in cands:
        if tid:
            return p, tid
    for p, _tid, tem in cands:
        if tem:
            return p, ""
    if cands:
        return cands[0][0], cands[0][1]
    if nu is not None:
        return nu, ""
    return None, ""


def _tem_conteudo_nu(p: Path) -> bool:
    """Pasta parece conteúdo de romfs sem o invólucro (ex.: 'a/' do Pokémon)?"""
    try:
        for item in p.iterdir():
            n = item.name.lower()
            if item.is_dir() and n in ("a", "sound", "m", "data"):
                return True
            if item.is_file() and n.endswith((".cro", ".crr", ".moflex", ".bcstm", ".bcsar")):
                return True
    except OSError:
        pass
    return False


def importar_mod(origem: str, title_id: str = "", nome: str = "") -> dict:
    """Copia pasta ou extrai archive p/ a biblioteca. Retorna dict (sempre).

    Detecta a raiz LayeredFS (romfs/exefs/code.ips, luma/titles/<id> ou
    conteúdo nu como 'a/') e normaliza. title_id vem do caminho luma ou
    deve ser informado (o jogo de destino).
    """
    import tempfile
    src = Path((origem or "").strip().strip("\"'"))
    if not src.exists():
        return {"ok": False, "erro": f"origem não encontrada: {origem}"}
    tid = (title_id or "").strip().upper()
    if tid and (len(tid) != 16 or any(c not in "0123456789ABCDEF" for c in tid)):
        return {"ok": False, "erro": f"title ID inválido: {title_id}"}
    rotulo = (nome or "").strip().replace("/", "-").replace("\\", "-")[:60].strip()
    if not rotulo:
        rotulo = src.stem.strip()[:60].strip()
    if not rotulo or rotulo in (".", ".."):
        return {"ok": False, "erro": "nome de mod vazio."}
    tmp = Path(tempfile.mkdtemp(prefix="hub-mod-"))
    try:
        if src.is_dir():
            shutil.copytree(src, tmp / "m")
        elif src.is_file():
            _E._extrair_arquivo(str(src), tmp / "m")
        else:
            return {"ok": False, "erro": f"origem inválida: {origem}"}
        raiz, tid_luma = _raiz_layeredfs(tmp / "m")
        if raiz is None:
            return {"ok": False, "erro": "estrutura LayeredFS não encontrada (sem romfs/exefs/code.ips)."}
        tid = tid or tid_luma
        if not tid:
            return {"ok": False, "erro": "informe o jogo (title ID) deste mod."}
        dest = mods_titulo_dir(tid) / rotulo
        if dest.exists():
            return {"ok": False, "erro": f"mod '{rotulo}' já existe na biblioteca."}
        if _tem_conteudo_nu(raiz) and not (raiz / "romfs").is_dir() and not (raiz / "exefs").is_dir():
            dest.mkdir(parents=True)
            rf = dest / "romfs"
            rf.mkdir()
            for item in sorted(raiz.iterdir()):
                if item.name.lower() == "code.ips":
                    continue  # vai p/ raiz do mod (Azahar só lê lá)
                if item.suffix.lower() in (".txt", ".md") and item.is_file():
                    continue
                shutil.move(str(item), str(rf / item.name))
            if (raiz / "code.ips").is_file():
                shutil.move(str(raiz / "code.ips"), str(dest / "code.ips"))
        else:
            shutil.copytree(raiz, dest)
        n = sum(1 for _p in dest.rglob("*") if _p.is_file())
        if not _E._eh_mod_valido(dest):
            shutil.rmtree(dest, ignore_errors=True)
            return {"ok": False, "erro": "nada aproveitável (sem romfs/exefs/code.ips)."}
        return {"ok": True, "mod": rotulo, "title_id": tid, "arquivos": n}
    except OSError as e:
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


__all__ = ["_bin_7z", "_eh_mod_valido", "_eh_reparse", "_extrair_arquivo",
           "_gravar_manifesto", "_k32", "_ler_manifesto", "_limpar_hub",
           "_raiz_layeredfs", "_tem_conteudo_nu", "aplicar_mods", "importar_mod",
           "listar_mods", "mods_ativos", "mods_lib_dir", "mods_titulo_dir",
           "remover_link", "remover_mod", "title_id_da_rom"]
