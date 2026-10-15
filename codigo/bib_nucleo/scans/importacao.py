#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scans: importação da lista achada p/ o banco (+ capas automáticas)."""
from __future__ import annotations

import math
import sqlite3
import uuid as uuid_mod

from bib_nucleo import scans as _S
from bib_nucleo.banco import (
    STATUS_VALIDOS,
    chave_dedup,
    normalizar_etiquetas,
    normalizar_mods,
    salvar_capa_bytes,
)
from bib_nucleo.base import agora_iso, slugify
from bib_nucleo.emuladores import provedor_por_origem

# --------------------------------------------------------------------------
# Importação / backup / capas
# --------------------------------------------------------------------------
from bib_nucleo.rede.metadados import _capa_steam, canonizar_steam


def _appid_steam_por_titulo(titulo: str, timeout: int = 15) -> str:
    """Acha o appid Steam pelo nome exato (normalizado). '' se nada.

    Nunca levanta (rede falhou = sem capa automática, sem travar import).
    """
    appid, _nome = canonizar_steam(titulo, timeout=timeout)
    return appid


def importar_lista(con: sqlite3.Connection, itens: list[dict]) -> dict:
    """Importa jogos. Itens com uuid existente ATUALIZAM progresso (restore);
    sem uuid (scans) inserem. Retorna relatório (novos/atualizados/ignorados/erros)."""
    antes = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
    agora = agora_iso()
    novos = atualizados = ignorados = 0
    erros: list[str] = []
    avisos: list[str] = []
    vistos = {chave_dedup(r["titulo"], r["executable_path"], r["launch_options"])
              for r in con.execute(
                  "SELECT titulo, executable_path, launch_options, origem FROM jogos").fetchall()}
    # mesmo exe+lançamento com título diferente também é duplicata
    # (título de scan muda: "Hades2" virou "Hades 2" no exe do "Hades II")
    vistos_exe = {(t[1], t[2]) for t in vistos}
    # ROMs: o emulador muda por SO (azahar.exe × AppImage), então o par
    # (título, ROM) dedupa sozinho, sem o exe
    vistos_rom = set()
    for r in con.execute(
            "SELECT titulo, launch_options, origem FROM jogos").fetchall():
        if (r["origem"] or "").startswith("rom-") and (r["launch_options"] or "").strip():
            vistos_rom.add(chave_dedup(r["titulo"], "", r["launch_options"]))

    def _ignorar(motivo: str):
        nonlocal ignorados
        ignorados += 1
        if len(erros) < 20:
            erros.append(motivo)

    def _mods_seguro(v) -> str:
        try:
            return normalizar_mods(v)
        except ValueError:
            return "[]"

    for pos, j in enumerate(itens):
        if not isinstance(j, dict):
            _ignorar(f"item {pos}: não é objeto")
            continue
        j = {k: (v.replace("\x00", "") if isinstance(v, str) else v)
             for k, v in j.items()}
        if not isinstance(j.get("titulo"), str):
            _ignorar(f"item {pos}: título inválido")
            continue
        titulo = j["titulo"].strip()
        if not titulo:
            _ignorar(f"item {pos}: sem título")
            continue
        try:
            nota = j.get("nota")
            nota = None if nota in (None, "") else int(nota)
            if nota is not None and not 0 <= nota <= 10:
                nota = None
            horas = float(j.get("horas") or 0)
            if not math.isfinite(horas):
                raise ValueError("horas não finitas")
            if horas < 0:
                horas = 0.0
            confianca = float(j.get("score") or j.get("confianca") or 0)
            if not math.isfinite(confianca):
                raise ValueError("confiança não finita")
        except (TypeError, ValueError):
            _ignorar(f"'{titulo}': nota/horas inválidos")
            continue
        try:
            uid = (j.get("uuid") or "").strip() or None
            if uid is not None:
                alvo = con.execute("SELECT * FROM jogos WHERE uuid=?",
                                   (uid,)).fetchone()
            else:
                alvo = None
            if alvo is not None:
                # restore: progresso volta; identidade/caminhos ficam locais.
                # etiquetas voltam se o pacote as trouxe (scans não mandam).
                ultima = j.get("ultima_execucao", alvo["ultima_execucao"])
                etiq_alvo = alvo["etiquetas"] if "etiquetas" in alvo.keys() else ""
                con.execute(
                    """UPDATE jogos SET horas=?, ultima_execucao=?, status=?, nota=?,
                       favorito=?, observacoes=?, azahar_preset=?, etiquetas=?,
                       save_path=?, azahar_mods=?, azahar_mods_off=?, game_code=?, regiao=?,
                       atualizado_em=? WHERE id=?""",
                    (horas if "horas" in j else alvo["horas"], ultima,
                     j.get("status") if j.get("status") in STATUS_VALIDOS else alvo["status"],
                     nota if "nota" in j else alvo["nota"],
                     int(bool(j.get("favorito"))) if "favorito" in j else alvo["favorito"],
                     j.get("observacoes", alvo["observacoes"]),
                      j.get("azahar_preset", alvo["azahar_preset"]),
                      normalizar_etiquetas(j["etiquetas"]) if "etiquetas" in j else etiq_alvo,
                      j.get("save_path", alvo["save_path"]),
                      _mods_seguro(j["azahar_mods"]) if "azahar_mods" in j else alvo["azahar_mods"],
                      int(bool(j["azahar_mods_off"])) if "azahar_mods_off" in j else alvo["azahar_mods_off"],
                      j.get("game_code", alvo["game_code"]), j.get("regiao", alvo["regiao"]),
                      j.get("atualizado_em") or agora, alvo["id"]),
                )
                atualizados += 1
                continue
            if uid is None:
                uid = uuid_mod.uuid4().hex
            chave = chave_dedup(titulo, (j.get("executable_path") or ""),
                                (j.get("launch_options") or ""))
            if chave in vistos or (chave[1] and (chave[1], chave[2]) in vistos_exe):
                ignorados += 1
                continue
            if ((j.get("origem") or "").startswith("rom-")
                    and (j.get("launch_options") or "").strip()
                    and chave_dedup(titulo, "", j.get("launch_options") or "") in vistos_rom):
                ignorados += 1
                continue
            cur = con.execute(
                   """INSERT OR IGNORE INTO jogos
                   (titulo, executable_path, exe_win, exe_linux, exe_mac, wine_prefix, launch_options,
                    status, nota, favorito, horas, ultima_execucao, observacoes, origem, shop, object_id,
                     game_code, regiao, azahar_preset, uuid, etiquetas, save_path, azahar_mods, azahar_mods_off,
                    confianca, criado_em, atualizado_em)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (titulo, (j.get("executable_path") or "").strip(),
                 (j.get("exe_win") or "").strip(), (j.get("exe_linux") or "").strip(),
                 (j.get("exe_mac") or "").strip(),
                 (j.get("wine_prefix") or ""), (j.get("launch_options") or ""),
                 j.get("status") if j.get("status") in STATUS_VALIDOS else "backlog",
                 nota, 1 if j.get("favorito") else 0,
                 horas, (j.get("ultima_execucao") or "").strip() or None,
                 (j.get("observacoes") or ""),
                 j.get("origem") or "manual", (j.get("shop") or ""),
                 (j.get("object_id") or ""), (j.get("game_code") or "").strip(),
                 (j.get("regiao") or "").strip(), (j.get("azahar_preset") or "").strip(),
                   uid, normalizar_etiquetas(j.get("etiquetas") or ""), j.get("save_path") or "",
                  _mods_seguro(j.get("azahar_mods")),
                  1 if j.get("azahar_mods_off") else 0,
                  confianca, j.get("criado_em") or agora, j.get("atualizado_em") or agora),
            )
            novos += cur.rowcount
            if not cur.rowcount:
                ignorados += 1
            else:
                vistos.add(chave)
                vistos_exe.add((chave[1], chave[2]))
                if ((j.get("origem") or "").startswith("rom-")
                        and (j.get("launch_options") or "").strip()):
                    vistos_rom.add(chave_dedup(titulo, "", j.get("launch_options") or ""))
            prov_rom = provedor_por_origem(j.get("origem") or "")
            if cur.rowcount and prov_rom is not None:
                try:  # capa automática: ícone de dentro da própria ROM
                    rom = ((j.get("rom_path") or "").strip()
                           or (j.get("launch_options") or "").strip())
                    png = prov_rom["icone"](rom) if rom else None
                    if png:
                        _S.salvar_capa_bytes(con, cur.lastrowid,
                                             slugify(titulo) + ".png", png)
                    elif len(avisos) < 20:
                        avisos.append(f"'{titulo}': sem ícone extraível na ROM")
                except Exception as e:
                    if len(avisos) < 20:
                        avisos.append(f"'{titulo}': capa falhou ({type(e).__name__})")
            if cur.rowcount and prov_rom is None:
                appid = ((j.get("object_id") or "").strip()
                         if (j.get("shop") or "").strip().lower() == "steam" else "")
                if appid and appid.isdigit():
                    try:  # capa automática: header oficial da Steam
                        raw = _S._capa_steam(appid)
                        if raw:
                            _S.salvar_capa_bytes(con, cur.lastrowid,
                                                 slugify(titulo) + ".jpg", raw)
                    except Exception as e:
                        if len(avisos) < 20:
                            avisos.append(f"'{titulo}': capa Steam falhou ({type(e).__name__})")
        except Exception as e:
            _ignorar(f"'{titulo}': {type(e).__name__}: {e}")
            continue
    con.commit()
    depois = con.execute("SELECT COUNT(*) AS n FROM jogos").fetchone()["n"]
    return {"novos": novos, "atualizados": atualizados, "ignorados": ignorados,
            "erros": erros, "avisos": avisos,
            "total_no_banco": depois, "antes": antes}


def resumo_importacao(res: dict) -> str:
    texto = (f"Novos: {res.get('novos', 0)} · atualizados: {res.get('atualizados', 0)} · "
             f"ignorados: {res.get('ignorados', 0)} · erros: {len(res.get('erros', []))}")
    if res.get("erros"):
        texto += "\n" + "\n".join(res["erros"][:5])
    if res.get("avisos"):
        texto += "\n" + "\n".join(res["avisos"][:5])
    return texto


__all__ = ["_capa_steam", "canonizar_steam", "_appid_steam_por_titulo",
           "importar_lista", "resumo_importacao", "salvar_capa_bytes"]
