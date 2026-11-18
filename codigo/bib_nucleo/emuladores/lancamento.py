#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emuladores: execução de jogos (elevação, Wine, vigia, sessões) e diagnóstico."""
from __future__ import annotations

import shlex
import shutil
import subprocess
import threading
import time
from pathlib import Path

from bib_nucleo import emuladores as _E
from bib_nucleo.base import (
    existe_aqui_ou_traduzido,
    resolver_exe,
)
from bib_nucleo.emuladores.azahar import azahar_tem_chaves
from bib_nucleo.emuladores.mods import aplicar_mods
from bib_nucleo.emuladores.provedores import (
    provedor_por_extensao,
    provedor_por_origem,
)
from bib_nucleo.sessoes_manuais import iniciar_sessao_manual

# --------------------------------------------------------------------------
# Execução de jogos (Windows + Linux)
# --------------------------------------------------------------------------

def _eh_elevacao_necessaria(e: Exception) -> bool:
    return isinstance(e, OSError) and getattr(e, "winerror", None) == 740


def executar_elevado(executable_path: str, launch_options: str = "") -> dict:
    """Relança via UAC (ShellExecute 'runas'). Só Windows. Abre o prompt do UAC."""
    if _E.os.name == "nt":
        import ctypes
        exe = _E.traduzir_para_atual((executable_path or "").strip())
        p = Path(exe)
        if not p.exists():
            return {"ok": False, "erro": f"Executável não encontrado: {exe}"}
        cwd = str(p.parent) if p.parent.exists() else None
        try:
            extra = _argumentos_lancamento(launch_options)
            params = subprocess.list2cmdline(extra) or None
            from ctypes import wintypes
            shell = ctypes.WinDLL("shell32", use_last_error=True)
            shell.ShellExecuteW.argtypes = [wintypes.HWND, wintypes.LPCWSTR,
                                            wintypes.LPCWSTR, wintypes.LPCWSTR,
                                            wintypes.LPCWSTR, ctypes.c_int]
            shell.ShellExecuteW.restype = wintypes.HINSTANCE
            rc = shell.ShellExecuteW(
                None, "runas", str(p), params, cwd, 1)
            if int(rc or 0) <= 32:
                return {"ok": False, "erro": f"UAC recusou/falhou (código {int(rc or 0)})"}
            return {"ok": True, "modo": "runas-uac"}
        except Exception as e:
            return {"ok": False, "erro": f"{type(e).__name__}: {e}"}
    return {"ok": False, "erro": "elevação só existe no Windows"}


def _tem_nvidia() -> str:
    """Nome da GPU NVIDIA discreta ou ''. Só liga o PRIME+DXVK se houver."""
    import shutil
    import subprocess

    from bib_nucleo.processos import opcoes_sem_janela
    try:
        if shutil.which("nvidia-smi") is not None:
            out = subprocess.run(["nvidia-smi", "--query-gpu=name",
                                  "--format=csv,noheader"],
                                 capture_output=True, text=True, timeout=10,
                                 **opcoes_sem_janela())
            nomes = (out.stdout or "").strip().splitlines()
            if out.returncode == 0 and nomes:
                return nomes[0].strip()
    except Exception:
        pass
    try:
        if Path("/usr/share/vulkan/icd.d/nvidia_icd.json").is_file():
            return "NVIDIA"
    except OSError:
        pass
    return ""


def prefixo_wine_hub() -> str:
    """Prefixo Wine do HUB (`dados/saves/wine`); cria na primeira chamada."""
    from bib_nucleo.base import WINE_PREFIXO
    try:
        WINE_PREFIXO.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return str(WINE_PREFIXO)


def _argumentos_lancamento(opcoes: str) -> list[str]:
    extra = shlex.split(opcoes, posix=(_E.os.name != "nt")) if opcoes.strip() else []
    if _E.os.name == "nt":
        extra = [(a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'" else a)
                 for a in extra]
    return extra


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
    exe = _E.traduzir_para_atual(exe)  # gravado num SO, executando no outro
    p = Path(exe)
    if not p.exists():
        return {"ok": False, "erro": f"Executável não encontrado: {exe}"}, None

    env = _E.os.environ.copy()
    if wine_prefix.strip():
        env["WINEPREFIX"] = wine_prefix.strip()

    # Aspas são só agrupamento p/ o split (Popen recebe lista e cita sozinho):
    # "C:\com espaco\jogo.cci" vira um arg limpo, sem aspas literais.
    try:
        extra = _argumentos_lancamento(launch_options)
        cwd = str(p.parent) if p.parent.exists() else None
        if _E.os.name == "nt":
            ext = p.suffix.lower()
            if ext in (".lnk", ".url") or p.is_dir():
                _E.os.startfile(str(p))  # type: ignore[attr-defined]
                return {"ok": True, "modo": "startfile"}, None
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            proc = subprocess.Popen([str(p), *extra], cwd=cwd, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, creationflags=creationflags,
                                    close_fds=True)
            return {"ok": True, "modo": "popen-windows"}, proc
        else:
            ext = p.suffix.lower()
            nome_so = "Mac" if _E.eh_mac() else "Linux"
            if _E.eh_mac() and ext == ".app" and p.is_dir():
                # bundle: roda o binário de dentro (processo rastreável, conta horas)
                from bib_nucleo.emuladores._comum import binario_do_app
                interno = binario_do_app(p)
                if not interno:
                    return {"ok": False, "erro": f"App sem executável em Contents/MacOS: {exe}"}, None
                p, ext = Path(interno), ""
                cwd = str(p.parent)
            if ext in (".lnk", ".url") or p.is_dir():
                return {"ok": False,
                        "erro": f"Atalho/pasta Windows não executa no {nome_so}: {exe}"}, None
            if ext in (".exe", ".bat", ".cmd"):
                vinho = shutil.which("wine") or shutil.which("wine64")
                if vinho:
                    if wine_prefix.strip():
                        env["WINEPREFIX"] = _E.traduzir_para_atual(wine_prefix.strip())
                    else:
                        env["WINEPREFIX"] = prefixo_wine_hub()  # saves no HUB
                    # híbrido Intel+NVIDIA: jogo na discreta via PRIME com o
                    # DXVK filtrado para ela; sem NVIDIA, Wine decide sozinho
                    gpu = _E._tem_nvidia()
                    if gpu:
                        env.setdefault("__NV_PRIME_RENDER_OFFLOAD", "1")
                        env.setdefault("__GLX_VENDOR_LIBRARY_NAME", "nvidia")
                        env.setdefault("__VK_LAYER_NV_optimus", "NVIDIA_only_1")
                        env.setdefault("DXVK_FILTER_DEVICE_NAME", gpu)
                    cmd = [vinho, str(p), *extra]
                    try:
                        proc = subprocess.Popen(cmd, cwd=cwd, env=env,
                                                stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL,
                                                stdin=subprocess.DEVNULL,
                                                start_new_session=True,
                                                close_fds=True)
                    except Exception as e:
                        return {"ok": False,
                                "erro": f"{type(e).__name__}: {e}"}, None
                    return {"ok": True, "modo": "wine-linux"}, proc
                if _E.eh_mac():
                    return {"ok": False,
                            "erro": (f"Jogo Windows não executa no Mac: {exe} "
                                     "(sem Wine no Mac; cadastre exe_mac nativo)")}, None
                return {"ok": False,
                        "erro": (f"Jogo Windows no Linux sem Wine: {exe} "
                                 "(instale o wine ou cadastre exe_linux nativo)")}, None
            if not _E.os.access(str(p), _E.os.X_OK):
                return {"ok": False,
                        "erro": f"Sem permissão de execução: {exe} (rode chmod +x?)"}, None
            cmd = [str(p), *extra]
            proc = subprocess.Popen(cmd, cwd=cwd, env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    stdin=subprocess.DEVNULL, start_new_session=True,
                                    close_fds=True)
            return {"ok": True, "modo": "popen-mac" if _E.eh_mac() else "popen-linux"}, proc
    except Exception as e:
        if _eh_elevacao_necessaria(e):
            return {"ok": False, "requer_elevacao": True,
                    "erro": f"{type(e).__name__}: {e} — o executável exige administrador."}, None
        return {"ok": False, "erro": f"{type(e).__name__}: {e}"}, None


def _lancar_jogo_dict(jogo: dict, elevar: bool = False) -> tuple[dict, object | None]:
    """Resolve o exe do SO atual (exe_win/exe_linux vencem) e lança.

    Origens com provider (ex.: rom-3ds) usam o exe e as flags do provider.
    """
    origem = (jogo.get("origem") or "")
    prov = provedor_por_origem(origem)
    exe, _origem = resolver_exe(jogo)
    if prov is not None:
        from bib_nucleo.atualizacao import recuperar
        exe_prov = prov["exe"]() or ""
        # diário do provider atual (não do Azahar fixo): update interrompido
        # de qualquer emulador bloqueia o play com erro claro
        alvo_rec = Path(exe_prov).parent if exe_prov else None
        if alvo_rec is not None:
            recuperacao = recuperar(alvo_rec)
            if not recuperacao["ok"]:
                return {"ok": False, "erro": recuperacao["erro"]}, None
    if not exe and prov is not None:
        exe = prov["exe"]() or ""  # linha sem emu (ou apagado): o instalado vale
    if not exe and prov is not None:
        return {"ok": False, "erro": prov["dica_instalacao"]}, None
    launch = (jogo.get("launch_options") or "")
    if prov is not None and launch.strip():
        launch = montar_launch_rom(prov, _E.traduzir_para_atual(launch))
    return _E._lancar(exe, (jogo.get("wine_prefix") or ""), launch, elevar=elevar)


def executar_jogo_dict(jogo: dict, elevar: bool = False) -> dict:
    """Resolve o exe do SO atual (exe_win/exe_linux vencem) e executa."""
    res, _proc = _E._lancar_jogo_dict(jogo, elevar)
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
    launch = (jogo.get("launch_options") or "").strip().strip("\"'")
    if provedor_por_origem(jogo.get("origem") or "") is None:
        return {"estado": "nao-rom", "candidatos": []}
    if not launch:
        return {"estado": "nao-rom", "candidatos": []}
    if provedor_por_extensao(Path(launch).suffix) is None:
        return {"estado": "nao-rom", "candidatos": []}  # flags de PC, não arquivo
    if existe_aqui_ou_traduzido(launch)[0]:
        return {"estado": "ok", "candidatos": []}
    base = launch.replace("\\", "/").rsplit("/", 1)[-1]
    return {"estado": "rom-ausente", "candidatos": _E.procurar_rom(base) if base else []}


def procurar_rom(nome_arquivo: str, roots: list[str] | None = None,
                 max_resultados: int = 20) -> list[str]:
    """Acha arquivos pelo nome-base nas raízes de ROMs+scan (p/ religar).

    Só leitura, com teto. Compara case-insensitive pelo nome do arquivo.
    """
    from bib_nucleo.scans import (
        SKIP_DIRS,
        default_roms_nds_roots,
        default_roms_roots,
        default_scan_roots,
    )
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
        for dirpath, dirnames, filenames in _E.os.walk(rp):
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
                    try:
                        p = (Path(dirpath) / fn).resolve()
                    except (OSError, RuntimeError):
                        continue
                    if p not in caminhos_vistos:
                        caminhos_vistos.add(p)
                        achados.append(str(p))
    return sorted(achados)


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
    abre sessão manual (arquivo em dados/sessoes/) e chama ao_fim(0.0, False).
    Se o launcher fechar, a sessão manual sobrevive e pode ser reconciliada.
    """
    res, proc = _E._lancar_jogo_dict(jogo)
    rastreavel = bool(res.get("ok")) and proc is not None
    res["rastreado"] = rastreavel
    if ao_fim is None:
        if bool(res.get("ok")) and not rastreavel:
            try:
                iniciar_sessao_manual(int(jogo.get("id") or 0),
                                      str(jogo.get("titulo") or ""))
            except Exception:
                pass
        return res
    if rastreavel:
        threading.Thread(target=_vigiar_processo, args=(proc, limiar_s, ao_fim),
                         daemon=True).start()
    elif res.get("ok"):
        try:
            iniciar_sessao_manual(int(jogo.get("id") or 0),
                                  str(jogo.get("titulo") or ""))
        except Exception:
            pass
        ao_fim(0.0, False)
    return res


def montar_launch_rom(prov: dict, rom_path: str) -> str:
    """flags do provider + ROM entre aspas quando tem espaço."""
    rom = (rom_path or "").strip()
    if " " in rom and not (rom.startswith('"') and rom.endswith('"')):
        rom = f'"{rom}"'
    flags = " ".join(prov["flags"]())
    return (flags + " " if flags else "") + rom


def preparar_lancamento(jogo: dict) -> dict:
    """Aplica preset + mods do provider do jogo. Nunca bloqueia o play."""
    origem = (jogo.get("origem") or "")
    prov = provedor_por_origem(origem)
    if prov is None:
        return {"preset_aplicado": None, "mods_aplicados": [], "aviso": None}
    avisos: list[str] = []
    aplicado = None
    campo = "azahar_preset"
    nome = (jogo.get(campo) or "").strip()
    if nome:
        r = prov["aplicar_preset"](nome)
        if r.get("ok"):
            aplicado = r["preset"]
        else:
            avisos.append(f"Preset '{nome}' falhou ({r['erro']}); abrindo com config atual.")
    launch = (jogo.get("launch_options") or "").strip()
    mods_ok: list[str] = []
    if (launch and prov.get("chave") == "azahar"
            and provedor_por_extensao(Path(launch).suffix) is not None):
        if rom_parece_criptografada(launch) and not azahar_tem_chaves():
            avisos.append("ROM parece criptografada e o Azahar está sem aes_keys.txt "
                          "— o jogo não vai abrir. Faça o dump das chaves do seu 3DS "
                          "(GodMode9) para user/sysdata/aes_keys.txt.")
        mr = aplicar_mods(jogo)
        mods_ok = mr["aplicados"]
        if mr["aviso"]:
            avisos.append(mr["aviso"])
        try:  # texturas HD: pasta ativa sem flag global = HD invisível
            from bib_nucleo import texturas as _TEX
            tid_tex = _E.title_id_da_rom(_E.traduzir_para_atual(launch))
            if tid_tex and _TEX.tem_textura(tid_tex):
                if _TEX.flag_custom_textures() is False:
                    avisos.append("Texturas HD ligadas mas o preset está sem "
                                  "custom textures — troque p/ hd2x.")
        except Exception:
            pass
    return {"preset_aplicado": aplicado, "mods_aplicados": mods_ok,
            "aviso": " ".join(avisos) or None}


def rom_parece_criptografada(rom_path: str) -> bool:
    """ExeFS sem ícone extraível = quase sempre ROM criptografada."""
    rom = (rom_path or "").strip()
    if not rom or not Path(rom).is_file():
        return False  # ausente é outro erro (o play já reporta)
    try:
        with Path(rom).open("rb") as f:
            head = f.read(0x200)
            if head[0x100:0x104] == b"NCSD":
                f.seek(int.from_bytes(head[0x120:0x124], "little") * 0x200)
                head = f.read(0x200)
            return (len(head) >= 0x200 and head[0x100:0x104] == b"NCCH"
                    and not bool(head[0x18F] & 0x04))
    except Exception:
        return False


__all__ = ["LIMIAR_SESSAO_S", "_argumentos_lancamento", "_eh_elevacao_necessaria",
           "_lancar", "_lancar_jogo_dict", "_tem_nvidia", "_vigiar_processo",
           "diagnosticar_exe", "diagnosticar_rom", "executar_elevado",
           "executar_jogo_dict", "executar_monitorado", "montar_launch_rom",
           "prefixo_wine_hub", "preparar_lancamento", "procurar_rom",
           "rom_parece_criptografada"]
