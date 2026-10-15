#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scans: análise unificada (classifica 1 caminho) e fusão de duplicados."""
from __future__ import annotations

from pathlib import Path

from bib_nucleo.base import (
    existe_aqui_ou_traduzido,
    mac_para_linux,
    win_para_linux,
)
from bib_nucleo.emuladores import provedor_por_extensao
from bib_nucleo.scans.disco import (
    SKIP_EXE_RE,
    _titulo_de_exe,
    default_scan_roots,
    preview_scan,
)
from bib_nucleo.scans.lojas import pontuar
from bib_nucleo.scans.roms import (
    _item_rom,
    default_roms_nds_roots,
    default_roms_roots,
    preview_roms,
)

EXE_IMPORTAVEIS = {".exe", ".lnk", ".bat", ".cmd", ".sh", ".appimage"}


def analisar_arquivo(caminho: str) -> dict:
    """Classifica UM caminho p/ a importação unificada. Só leitura.

    Retorna {"tipo", "item", "provedor", "detalhe", "aviso"} onde tipo é
    'pasta' | 'rom' | 'jogo' | 'json' | 'pacote' | 'arquivo-jogo' |
    'desconhecido'. 'pacote' é só o portátil do Hub (com biblioteca.json);
    outro .zip/.rar/.7z/.iso é repack (extrai p/ Meus Jogos Locais e importa).
    Emulador ausente NÃO bloqueia: a ROM importa e o aviso orienta (⬇).
    """
    vazio = {"tipo": "desconhecido", "item": None, "provedor": None,
             "detalhe": "", "aviso": None}
    p = Path((caminho or "").strip())
    if not p.exists():
        return {**vazio, "detalhe": "caminho não existe."}
    if p.is_dir():
        return {**vazio, "tipo": "pasta",
                "detalhe": f"pasta: varre jogos de PC + ROMs ({p})."}
    ext = p.suffix.lower()
    if ext == ".json":
        return {**vazio, "tipo": "json", "detalhe": "lista de jogos (JSON)."}
    from bib_nucleo.rede.repacks import ARQUIVO_EXTS, eh_pacote_hub  # sem ciclo
    if ext == ".zip" and eh_pacote_hub(p):
        return {**vazio, "tipo": "pacote",
                "detalhe": "pacote portátil (.zip) — tenta restaurar."}
    if ext in ARQUIVO_EXTS:
        return {**vazio, "tipo": "arquivo-jogo",
                "detalhe": (f"repack ({p.name}): extrai p/ Meus Jogos Locais, organiza, "
                            "acha o exe e importa.")}
    prov = provedor_por_extensao(ext)
    if prov is not None:
        emu = prov["exe"]() or ""
        item = pontuar(_item_rom(str(p), emu, prov))
        aviso = None
        if not emu:
            aviso = (f"{prov['nome']} não instalado — a ROM importa mesmo assim; "
                     f"depois instale com 'Atualizar {prov['nome']}'.")
        return {"tipo": "rom", "item": item, "provedor": prov["chave"],
                "detalhe": (f"ROM { '/'.join(prov['sistemas'])} → {prov['nome']} "
                            f"· '{item['titulo']}'"),
                "aviso": aviso}
    if ext in EXE_IMPORTAVEIS or not ext:
        item = pontuar({
            "titulo": _titulo_de_exe(p), "executable_path": str(p),
            "shop": "", "object_id": "",
            "horas": 0.0, "origem": "scan-disco",
        })
        aviso = None
        if SKIP_EXE_RE.search(p.name):
            aviso = "parece instalador/suporte (setup, redist…) — confira antes."
        return {"tipo": "jogo", "item": item, "provedor": None,
                "detalhe": f"jogo de PC (roda direto, sem emulador) · '{item['titulo']}'",
                "aviso": aviso}
    return {**vazio, "detalhe": (f"extensão '{ext or '?'}' não suportada "
                                 "(exe, ROM, .json, .zip ou pasta).")}


def preview_pasta(roots: list[str] | None = None) -> tuple[list[str], list[dict], dict]:
    """Uma varredura só: jogos de PC + ROMs nas mesmas raízes.

    (raízes_usadas, itens pontuados mistos e sem duplicatas,
    info{vistos, truncado, raizes, emu}).
    ROMs sem emulador vêm com exe vazio (importam; o play orienta).
    """
    if not roots:
        vistas: list[str] = []
        for r in default_scan_roots() + default_roms_roots() + default_roms_nds_roots():
            if r not in vistas:
                vistas.append(r)
        roots = vistas
    roots_u, itens_disco, info_d = preview_scan(roots)
    _r, itens_rom, info_r, emu = preview_roms(roots, None)
    _r, itens_nds, info_n, emu_nds = preview_roms(roots, None, "desmume")
    itens = sorted(fundir_duplicados(itens_disco + itens_rom + itens_nds),
                   key=lambda j: j["titulo"].lower())
    info = {"vistos": info_d["vistos"] + info_r["vistos"] + info_n["vistos"],
            "truncado": info_d["truncado"] or info_r["truncado"] or info_n["truncado"],
            "raizes": info_d["raizes"], "emu": emu, "emu_nds": emu_nds}
    return roots_u, itens, info


def _norm_titulo(t) -> str:
    return " ".join((t or "").casefold().split())


def _norm_caminho(c) -> str:
    """Mesmo arquivo em SOs distintos compara igual."""
    c = (c or "").strip()
    if not c:
        return ""
    return mac_para_linux(win_para_linux(c)).replace("\\", "/").casefold()


def _dobrar_fundido(atual: dict, novo: dict) -> None:
    """Funde `novo` dentro de `atual` (mesmo jogo, outra fonte)."""
    exe_a, exe_n = (atual.get("executable_path") or ""), (novo.get("executable_path") or "")
    # o exe que existe neste ou no outro SO vence; senão, o não-vazio
    for cand in (exe_n, exe_a):
        if cand and existe_aqui_ou_traduzido(cand)[0]:
            if cand != exe_a:
                atual["executable_path"] = cand
                atual["launch_options"] = novo.get("launch_options") or atual.get("launch_options")
            break
    else:
        if exe_n and not exe_a:
            atual["executable_path"] = exe_n
            atual["launch_options"] = novo.get("launch_options") or atual.get("launch_options")
    if (novo.get("horas") or 0) > (atual.get("horas") or 0):
        atual["horas"] = novo["horas"]
    for campo in ("shop", "object_id", "game_code", "regiao", "rom_path"):
        if not (atual.get(campo) or "") and (novo.get(campo) or ""):
            atual[campo] = novo[campo]
    if novo.get("tem_metadados"):
        atual["tem_metadados"] = True
    for f in novo.get("fontes", [novo.get("fonte") or novo.get("origem") or "?"]):
        if f and f not in atual["fontes"]:
            atual["fontes"].append(f)
    atual["fonte"] = "+".join(atual["fontes"])


def _compativel(atual: dict, novo: dict) -> bool:
    """Podem ser o mesmo jogo? ROMs: mesma rom. PC: exe igual ou ausente."""
    if (atual.get("origem") or "").startswith("rom-"):
        return _norm_caminho(atual.get("rom_path")) == _norm_caminho(novo.get("rom_path"))
    ea, en = _norm_caminho(atual.get("executable_path")), _norm_caminho(novo.get("executable_path"))
    return (not ea) or (not en) or (ea == en)


def fundir_duplicados(itens: list[dict]) -> list[dict]:
    """Junta achados repetidos do preview (mesmo jogo em N fontes).

    Grupo = mesmo título normalizado + mesmo kind (rom/pc). Dentro do grupo,
    exes diferentes e não-vazios = instalações distintas (separa); resto funde:
    herda o melhor exe, soma fontes/horas e re-pontua. Itens já pontuados são
    re-pontuados (idempotente).
    """
    grupos: dict[tuple, list[dict]] = {}
    ordem: list[tuple] = []
    for it in itens:
        t = _norm_titulo(it.get("titulo"))
        kind = "rom" if (it.get("origem") or "").startswith("rom-") else "pc"
        chave = (kind, t) if t else ("unico", id(it))
        if chave not in grupos:
            grupos[chave] = []
            ordem.append(chave)
        grupos[chave].append(dict(it))
    saidas: list[dict] = []
    for chave in ordem:
        fundidos: list[dict] = []
        for it in grupos[chave]:
            it["fontes"] = [it.get("fonte") or it.get("origem") or "?"]
            for f in fundidos:
                if _compativel(f, it):
                    _dobrar_fundido(f, it)
                    break
            else:
                fundidos.append(it)
        for f in fundidos:
            f["fonte"] = "+".join(f["fontes"])
            saida = pontuar(f)
            if len(f["fontes"]) > 1:
                saida["motivos"] = [*saida.get("motivos", []),
                                    f"achado também em: {', '.join(f['fontes'][1:])}"]
            saidas.append(saida)
    return saidas


__all__ = ["EXE_IMPORTAVEIS", "analisar_arquivo", "preview_pasta", "_norm_titulo",
           "_norm_caminho", "_dobrar_fundido", "_compativel", "fundir_duplicados"]
