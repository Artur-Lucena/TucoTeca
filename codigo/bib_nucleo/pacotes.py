#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backup versionado e pacote portátil (.zip) com restore."""
from __future__ import annotations

import datetime
import json
import sqlite3
import zipfile
from pathlib import Path

from bib_nucleo.banco import (CAPA_EXTS, criar_musica, get_db,
                                musica_to_dict, row_to_dict,
                                salvar_capa_bytes)
from bib_nucleo.base import (BACKUP_DIR, CAPAS_DIR, DEFAULT_DB, MUSICAS_DIR,
                               agora_iso, garantir_dirs, nome_arquivo_portatil)
from bib_nucleo.emuladores import (azahar_versao_local,
                                     presets_dir, presets_prov_dir, provedores)
from bib_nucleo.scans import importar_lista


# --------------------------------------------------------------------------
# Pacote portátil (.zip): banco + capas + presets + saves 3DS
# --------------------------------------------------------------------------

PACOTE_ESQUEMA = 4  # v4: +musicas/ (v3 presets/<prov>, v2 uuid, v1 title)

PACOTE_INFO = "pacote-info.json"

PACOTE_JSON = "biblioteca.json"

PACOTE_MANIFESTO = "capas-manifesto.json"


def _jogo_limpo(j: dict) -> dict:
    """Remove campos derivados da UI (exe_existe/traduzido etc) do export."""
    j = dict(j)
    for k in ("exe_existe", "exe_traduzido", "etiquetas_lista", "plataforma",
              "score", "motivos", "fontes", "fonte", "tem_metadados", "rom_path",
              "mods_lista", "mods_off"):
        j.pop(k, None)
    return j


def _dados_exportacao(con: sqlite3.Connection) -> dict:
    rows = con.execute("SELECT * FROM jogos ORDER BY id").fetchall()
    try:
        mus = [musica_to_dict(r)
               for r in con.execute("SELECT * FROM musicas ORDER BY id").fetchall()]
    except sqlite3.OperationalError:
        mus = []  # banco pré-v12: sem tabela, sem músicas
    return {"exportado_em": agora_iso(),
            "jogos": [_jogo_limpo(row_to_dict(r)) for r in rows],
            "musicas": mus}


def exportar_json(destino, db_path=None) -> dict:
    """Exporta biblioteca limpa (sem derivados) para .json."""
    destino = Path(destino)
    if destino.suffix.lower() != ".json":
        destino = destino.with_suffix(".json")
    if str(destino.parent):
        destino.parent.mkdir(parents=True, exist_ok=True)
    con = get_db(Path(db_path) if db_path else DEFAULT_DB)
    try:
        dados = _dados_exportacao(con)
    finally:
        con.close()
    try:
        destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    except OSError as e:
        return {"ok": False, "erro": f"falha ao gravar: {e}"}
    return {"ok": True, "destino": str(destino), "jogos": len(dados["jogos"])}


def _saves_para_pacote() -> list[tuple[str, Path]]:
    """[(membro_no_zip, caminho)] dos saves de todos os providers instalados.

    Nomes estáveis por provider: 'azahar-user/sdmc/...' (compat com pacotes
    já exportados).
    """
    pares: list[tuple[str, Path]] = []
    for prov in provedores().values():
        try:
            ud = prov["user_dir"]() or ""
        except Exception:
            continue
        if not ud:
            continue
        for sub in prov["pacote_subs"]:
            base = Path(ud) / sub
            if not base.is_dir():
                continue
            try:
                arquivos = sorted(p for p in base.rglob("*") if p.is_file())
            except OSError:
                continue
            for arq in arquivos:
                try:
                    rel = arq.relative_to(base).as_posix()
                except ValueError:
                    continue
                pares.append((f"{prov['chave']}-user/{sub}/{rel}", arq))
    return pares


def _musicas_para_pacote(musicas: list[dict]) -> list[tuple[str, Path]]:
    """[(membro_no_zip, caminho)] das músicas (`musicas/<arquivo>`).

    Membro pelo nome do arquivo gravado (único por importação); o restore
    casa pela linha do JSON. Arquivo ausente = fora do pacote.
    """
    from bib_nucleo.base import MUSICA_EXTS
    pares: list[tuple[str, Path]] = []
    vistos: set[str] = set()
    for m in musicas:
        if not isinstance(m, dict):
            continue
        nome = nome_arquivo_portatil(m.get("musica_path") or "")
        arq = MUSICAS_DIR / nome
        try:
            ok = bool(nome) and arq.is_file() \
                and arq.suffix.lower() in MUSICA_EXTS
        except OSError:
            continue
        if not ok or nome in vistos:
            continue
        vistos.add(nome)
        pares.append((f"musicas/{nome}", arq))
    return pares


def exportar_pacote(destino, db_path=None, incluir_saves: bool = True) -> dict:
    """Empacota tudo para levar a outra máquina (ou guardar)."""
    destino = Path(destino)
    if destino.suffix.lower() != ".zip":
        destino = destino.with_suffix(".zip")
    if str(destino.parent):
        destino.parent.mkdir(parents=True, exist_ok=True)
    garantir_dirs()
    con = get_db(Path(db_path) if db_path else DEFAULT_DB)
    try:
        dados = _dados_exportacao(con)
    finally:
        con.close()
    pares_saves = _saves_para_pacote() if incluir_saves else []
    com_saves = bool(pares_saves)
    pares_mus = _musicas_para_pacote(dados.get("musicas") or [])
    info = {"app": "biblioteca-jogos", "esquema": PACOTE_ESQUEMA,
            "exportado_em": dados["exportado_em"], "jogos": len(dados["jogos"]),
            "musicas": len(dados.get("musicas") or []),
            "inclui_saves": com_saves, "azahar_versao": azahar_versao_local(),
            "provedores": sorted(provedores())}
    manifesto = {}
    for j in dados["jogos"]:
        if j.get("capa") and j.get("uuid"):
            manifesto[Path(j["capa"]).name] = j["uuid"]
    for m in dados.get("musicas") or []:
        if isinstance(m, dict) and m.get("musica_capa") and m.get("musica_sha"):
            manifesto[Path(m["musica_capa"]).name] = f"mus:{m['musica_sha']}"
    n = 0
    try:
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(PACOTE_INFO, json.dumps(info, ensure_ascii=False, indent=2))
            z.writestr(PACOTE_JSON, json.dumps(dados, ensure_ascii=False, indent=2))
            z.writestr(PACOTE_MANIFESTO,
                       json.dumps(manifesto, ensure_ascii=False, indent=2))
            n += 3
            for arq in sorted(CAPAS_DIR.glob("*")):
                if arq.is_file() and arq.suffix.lower() in CAPA_EXTS:
                    z.write(arq, f"capas/{arq.name}")
                    n += 1
            base_pre = presets_dir()
            # legado raiz + por provider (presets/<prov>/*.ini)
            vistos_pre: set[str] = set()
            for arq in sorted(base_pre.glob("*.ini")):
                if arq.is_file():
                    membro = f"presets/{arq.name}"
                    if membro not in vistos_pre:
                        z.write(arq, membro)
                        vistos_pre.add(membro)
                        n += 1
            for prov_chave in sorted(provedores()):
                sub = base_pre / prov_chave
                if not sub.is_dir():
                    continue
                try:
                    arquivos = sorted(p for p in sub.glob("*.ini") if p.is_file())
                except OSError:
                    continue
                for arq in arquivos:
                    membro = f"presets/{prov_chave}/{arq.name}"
                    if membro not in vistos_pre:
                        z.write(arq, membro)
                        vistos_pre.add(membro)
                        n += 1
            if com_saves:
                for membro, arq in pares_saves:
                    z.write(arq, membro)
                    n += 1
            for membro, arq in pares_mus:
                z.write(arq, membro)
                n += 1
    except OSError as e:
        return {"ok": False, "erro": f"falha ao gravar pacote: {e}"}
    return {"ok": True, "destino": str(destino), "arquivos": n,
            "bytes": destino.stat().st_size, "jogos": len(dados["jogos"]),
            "musicas": len(dados.get("musicas") or []),
            "inclui_saves": com_saves}


def _membro_pacote_ok(nome: str) -> str | None:
    """Categoria do membro ('json','info','manifesto','capa','preset','save',
    'musica') ou None se proibido (traversal, absoluto, fora da allowlist)."""
    if not nome:
        return None
    n = nome.replace("\\", "/")
    if (".." in n.split("/") or n.startswith("/") or ":" in n
            or "\\" in nome or any(p in ("", ".") for p in n.split("/"))):
        return None
    if n == PACOTE_JSON:
        return "json"
    if n == PACOTE_INFO:
        return "info"
    if n == PACOTE_MANIFESTO:
        return "manifesto"
    if n.startswith("musicas/") and "/" not in n[8:]:
        from bib_nucleo.base import MUSICA_EXTS
        if Path(n).suffix.lower() in MUSICA_EXTS and Path(n).stem \
                and "." not in Path(n).stem:
            return "musica"
        return None
    if n.startswith("capas/") and "/" not in n[6:] \
            and Path(n).suffix.lower() in CAPA_EXTS:
        return "capa"
    if n.startswith("presets/") and n.lower().endswith(".ini"):
        partes_pre = n.split("/")
        if len(partes_pre) == 2 and partes_pre[1]:
            # legado: presets/<nome>.ini (vale p/ Azahar)
            return "preset"
        if len(partes_pre) == 3 and partes_pre[1] and partes_pre[2]:
            # novo: presets/<prov>/<nome>.ini (prov precisa existir)
            if partes_pre[1] in provedores():
                return "preset"
            return None
    partes = n.split("/")
    if len(partes) >= 3 and partes[0].endswith("-user") and not n.endswith("/"):
        prov = provedores().get(partes[0][:-5])
        if prov is not None and partes[1] in prov["pacote_subs"]:
            return "save"
    return None


def importar_pacote(origem, db_path=None, restaurar_saves: bool = False) -> dict:
    """Restaura um pacote: valida TODOS os nomes antes de aplicar qualquer
    coisa (nada parcial em pacote hostil). Capas voltam exatas via manifesto
    {arquivo: uuid} (pacotes v1 com {arquivo: titulo} ainda entram)."""
    origem = Path(origem)
    try:
        zf = zipfile.ZipFile(origem)
    except (OSError, zipfile.BadZipFile) as e:
        return {"ok": False, "erro": f"pacote inválido: {e}"}
    with zf:
        nomes = [i.filename for i in zf.infolist() if not i.is_dir()]
        if len(nomes) != len(set(nomes)):
            return {"ok": False, "erro": "pacote contém nomes duplicados"}
        cats: dict[str, str] = {}
        for nm in nomes:
            cat = _membro_pacote_ok(nm)
            if cat is None:
                return {"ok": False,
                        "erro": f"membro proibido no pacote: {nm!r} (nada foi aplicado)"}
            cats[nm] = cat
        if PACOTE_JSON not in cats:
            return {"ok": False, "erro": "pacote sem biblioteca.json"}
        try:
            esquema = 1
            if PACOTE_INFO in cats:
                info = json.loads(zf.read(PACOTE_INFO).decode("utf-8"))
                esquema = info.get("esquema", 1)
            if esquema not in (1, 2, 3, 4):
                return {"ok": False, "erro": "versão do pacote não suportada"}
            if zf.testzip() is not None:
                return {"ok": False, "erro": "pacote corrompido (CRC)"}
            dados = json.loads(zf.read(PACOTE_JSON).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, AttributeError, zipfile.BadZipFile) as e:
            return {"ok": False, "erro": f"biblioteca.json inválida: {e}"}
        lista = dados if isinstance(dados, list) else dados.get("jogos") if isinstance(dados, dict) else None
        if not isinstance(lista, list):
            return {"ok": False, "erro": "biblioteca.json deve ser lista ou {jogos:[...]}"}
        lista_mus = dados.get("musicas", []) if isinstance(dados, dict) else []
        if not isinstance(lista_mus, list):
            return {"ok": False, "erro": "biblioteca.json: 'musicas' deve ser lista"}
        try:
            manifesto = json.loads(zf.read(PACOTE_MANIFESTO).decode("utf-8")) \
                if PACOTE_MANIFESTO in cats else {}
        except (ValueError, UnicodeDecodeError):
            manifesto = {}
        if not isinstance(manifesto, dict):
            manifesto = {}
        db = Path(db_path) if db_path else DEFAULT_DB
        backup = fazer_backup(db) if db.is_file() else None
        con = get_db(db)
        try:
            res = importar_lista(con, lista)
            avisos = []
            capas = 0
            for arq, ident in manifesto.items():
                cat = cats.get(f"capas/{Path(arq).name}")
                if cat != "capa" or not isinstance(ident, str) or not ident.strip():
                    continue
                if ident.startswith("mus:"):
                    continue  # identidade de áudio é resolvida após restaurar músicas
                try:
                    raw = zf.read(f"capas/{Path(arq).name}")
                except KeyError:
                    continue
                if esquema in (2, 3, 4):
                    alvo = con.execute("SELECT id FROM jogos WHERE uuid=?", (ident.strip(),)).fetchone()
                else:
                    candidatos = con.execute("SELECT id FROM jogos WHERE titulo=?", (ident.strip(),)).fetchall()
                    alvo = candidatos[0] if len(candidatos) == 1 else None
                if alvo is None:
                    avisos.append(f"Capa {arq}: identidade ausente ou ambígua; não aplicada")
                    continue
                r = salvar_capa_bytes(con, alvo["id"], Path(arq).name, raw)
                if r.get("ok"):
                    capas += 1
                else:
                    res["erros"].append(f"Capa {arq}: {r['erro']}")
            presets = 0
            garantir_dirs()
            for nm, cat in cats.items():
                if cat != "preset":
                    continue
                try:
                    partes = nm.split("/")
                    if len(partes) == 3:
                        dest = presets_prov_dir(partes[1]) / Path(partes[2]).name
                    else:
                        dest = presets_dir() / Path(nm).name
                    # anti traversal: destino precisa ficar dentro de presets_dir
                    try:
                        dentro = dest.resolve().parent == dest.parent.resolve() or \
                            presets_dir().resolve() in dest.resolve().parents
                    except OSError:
                        dentro = False
                    if not dentro:
                        res["erros"].append(f"Preset {nm}: fora de presets/")
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(nm))
                    presets += 1
                except OSError as e:
                    res["erros"].append(f"Preset {nm}: {e}")
            saves, saves_ignorados = 0, 0
            tem_saves = any(c == "save" for c in cats.values())
            if tem_saves and restaurar_saves:
                for nm, cat in cats.items():
                    if cat != "save":
                        continue
                    partes = nm.split("/")
                    prov = provedores().get(partes[0][:-5])
                    ud = (prov["user_dir"]() or "") if prov is not None else ""
                    if not ud:
                        saves_ignorados += 1
                        continue
                    try:
                        dest = Path(ud) / partes[1] / Path(*partes[2:])
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(zf.read(nm))
                        saves += 1
                    except (OSError, ValueError):
                        saves_ignorados += 1
            musicas, musicas_ignoradas = 0, 0
            if lista_mus:
                from bib_nucleo.base import MUSICAS_DIR
                MUSICAS_DIR.mkdir(parents=True, exist_ok=True)
                mus_por_sha = {r["musica_sha"]: r["id"]
                               for r in con.execute("SELECT id, musica_sha FROM musicas")}
                for m in lista_mus:
                    if not isinstance(m, dict):
                        musicas_ignoradas += 1
                        continue
                    sha = str(m.get("musica_sha") or "").strip()
                    membro = f"musicas/{nome_arquivo_portatil(m.get('musica_path') or '')}"
                    if not sha or cats.get(membro) != "musica":
                        musicas_ignoradas += 1
                        continue
                    dest = MUSICAS_DIR / Path(membro).name
                    try:
                        if dest.is_file():
                            from bib_nucleo.musicas import sha_arquivo
                            if sha_arquivo(dest) != sha:
                                musicas_ignoradas += 1
                                continue
                        else:
                            import hashlib
                            from bib_nucleo.arquivos import gravar_atomico
                            raw = zf.read(membro)
                            if hashlib.sha256(raw).hexdigest() != sha:
                                musicas_ignoradas += 1
                                avisos.append(f"Música {Path(membro).name}: SHA-256 divergente")
                                continue
                            gravar_atomico(dest, raw)
                        if sha in mus_por_sha:
                            from bib_nucleo.musicas import resolver_musica
                            atual = con.execute("SELECT musica_path FROM musicas WHERE id=?",
                                                (mus_por_sha[sha],)).fetchone()
                            if not resolver_musica(atual["musica_path"]):
                                con.execute("UPDATE musicas SET musica_path=? WHERE id=?",
                                            (str(dest), mus_por_sha[sha]))
                                con.commit()
                            musicas_ignoradas += 1
                            continue
                        nova = criar_musica(con, {
                            "titulo": m.get("titulo") or Path(membro).stem,
                            "artista": m.get("artista") or "",
                            "album": m.get("album") or "",
                            "musica_path": str(dest),
                            "musica_sha": sha,
                            "origem": m.get("origem") or "pacote"})
                        mus_por_sha[sha] = nova["id"]
                        musicas += 1
                    except (OSError, ValueError):
                        musicas_ignoradas += 1
                from bib_nucleo.banco import salvar_capa_musica_bytes
                for arq, ident in manifesto.items():
                    if not (isinstance(ident, str) and ident.startswith("mus:")):
                        continue
                    mid = mus_por_sha.get(ident[4:])
                    if mid is None or cats.get(f"capas/{Path(arq).name}") != "capa":
                        continue
                    try:
                        raw = zf.read(f"capas/{Path(arq).name}")
                    except KeyError:
                        continue
                    r = salvar_capa_musica_bytes(con, mid, Path(arq).name, raw)
                    if r.get("ok"):
                        capas += 1
                    else:
                        res["erros"].append(f"Capa {arq}: {r['erro']}")
        finally:
            con.close()
    return {"ok": True, "novos": res["novos"], "atualizados": res["atualizados"],
            "ignorados": res["ignorados"], "erros": res["erros"],
            "avisos": avisos, "backup": backup,
            "total_no_banco": res["total_no_banco"],
            "capas": capas, "presets": presets, "saves": saves,
            "saves_ignorados": saves_ignorados, "musicas": musicas,
            "musicas_ignoradas": musicas_ignoradas}


def fazer_backup(db_path: Path, manter: int = 10) -> dict:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest_db = BACKUP_DIR / f"biblioteca-{ts}.db"
    dest_json = BACKUP_DIR / f"biblioteca-{ts}.json"
    con = get_db(db_path)
    try:
        dados = _dados_exportacao(con)
        dst = sqlite3.connect(str(dest_db))
        try:
            con.backup(dst)
        finally:
            dst.close()
    finally:
        con.close()
    dest_json.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    # poda: mantém os `manter` mais recentes de cada tipo
    for padrao in ("biblioteca-*.db", "biblioteca-*.json"):
        arqs = sorted(BACKUP_DIR.glob(padrao), key=lambda p: p.name, reverse=True)
        for velho in arqs[manter:]:
            try:
                velho.unlink()
            except OSError:
                pass
    return {"db": str(dest_db), "json": str(dest_json),
            "jogos": len(dados["jogos"]), "mantidos": manter}


def backup_pre_import(db_path=None) -> dict | None:
    """Backup silencioso antes de importar. Nunca levanta; None se falhou."""
    from bib_nucleo.base import log_erro
    try:
        return fazer_backup(Path(db_path) if db_path else DEFAULT_DB)
    except Exception as e:
        try:
            log_erro("backup-pre-import", f"{type(e).__name__}: {e}")
        except Exception:
            pass
        return None


def idade_ultimo_backup_dias() -> float | None:
    """Idade do backup .db mais recente em dias. None se nunca houve."""
    try:
        arqs = sorted(BACKUP_DIR.glob("biblioteca-*.db"))
        if not arqs:
            return None
        mais_recente = max(a.stat().st_mtime for a in arqs)
        import time as _time
        return (_time.time() - mais_recente) / 86400.0
    except OSError:
        return None


__all__ = ['PACOTE_ESQUEMA', 'PACOTE_INFO', 'PACOTE_JSON', 'PACOTE_MANIFESTO', 'exportar_json', 'exportar_pacote', 'importar_pacote', 'fazer_backup', 'backup_pre_import', 'idade_ultimo_backup_dias']
