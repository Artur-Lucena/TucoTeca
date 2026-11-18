"""Leituras agregadas do desktop: dashboard, diagnostico e busca global.

Adaptadores retornam dados simples. Cada operação possui sua conexão
SQLite; o frontend escolhe a thread e apresenta erros.
"""
from __future__ import annotations

from bib_nucleo import banco, base, emuladores, pacotes


def capa_url(nome):
    if not nome:
        return ""
    alvo = banco.caminho_capa(nome)
    return alvo.resolve().as_uri() if alvo is not None and alvo.is_file() else ""


def resumo_sistema(jogos, musicas, desejos, downloads=None):
    """Dashboard local OS: só conta estado já em memória + disco/backup. Sem rede."""
    import shutil
    recentes = sorted((j for j in jogos if j.get("ultima_execucao")),
                      key=lambda j: j.get("ultima_execucao") or "", reverse=True)[:4]
    if len(recentes) < 4:
        vistos = {id(j) for j in recentes}
        extra = sorted((j for j in jogos if id(j) not in vistos),
                       key=lambda j: float(j.get("horas") or 0), reverse=True)
        recentes = [*recentes, *extra][:4]
    try:
        pendentes = len(emuladores.listar_sessoes_pendentes())
    except Exception:
        pendentes = 0
    try:
        idade = pacotes.idade_ultimo_backup_dias()
        backup = "sem backup" if idade is None else (
            "backup hoje" if idade < 1 else f"backup há {int(idade)}d")
        backup_estado = "ausente" if idade is None else "antigo" if idade >= 7 else "recente"
    except Exception:
        idade, backup, backup_estado = None, "backup indisponível", "indisponivel"
    try:
        uso = shutil.disk_usage(base.HOME_DIR)
        livre_gb = round(uso.free / 1024 ** 3, 1)
        total_gb = round(uso.total / 1024 ** 3)
    except Exception:
        livre_gb, total_gb = 0, 0
    return {"jogos": len(jogos), "musicas": len(musicas), "desejos": len(desejos),
            "downloads": len(downloads or []), "pendentes": pendentes, "backup": backup,
            "backup_idade_dias": idade, "backup_estado": backup_estado,
            "disco_livre_gb": livre_gb, "disco_total_gb": total_gb,
            "recentes": [dict(r) for r in recentes]}


def saude_colecao(jogos, limite=8):
    """Diagnostica todos os jogos; o limite afeta só o resumo de problemas."""
    problemas = []
    ids_pendentes = []
    for j in jogos:
        try:
            exe = emuladores.diagnosticar_exe(j)["estado"]
        except Exception:
            exe = "?"
        try:
            rom = emuladores.diagnosticar_rom(j)["estado"]
        except Exception:
            rom = "?"
        motivos = []
        if exe not in ("ok",):
            motivos.append("exe " + exe)
        if rom == "rom-ausente":
            motivos.append("rom ausente")
        if motivos:
            ids_pendentes.append(j["id"])
            if len(problemas) < limite:
                problemas.append({"id": j["id"], "titulo": j["titulo"], "motivo": ", ".join(motivos)})
    return {"total": len(jogos), "problemas": problemas, "pendentes": len(ids_pendentes),
            "ids_pendentes": ids_pendentes, "ok": len(jogos) - len(ids_pendentes)}


def _sem_acento(s: str) -> str:
    """Minúsculas sem diacriticos (para busca tolerante, sem depender de ICU)."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "").casefold())
                   if unicodedata.category(c) != "Mn")


def busca_global(jogos, musicas, desejos, downloads, termo, limite=12):
    """Paleta de comandos OS: filtra coleção em memória, sem I/O. Retorna DTOs.

    Busca tolerante a acentos e sem ordem obrigatória das palavras.
    """
    palavras = _sem_acento(termo).split()
    if not palavras:
        return []
    def casa(item, campos):
        texto = _sem_acento(" ".join(str(item.get(k) or "") for k in campos))
        return all(p in texto for p in palavras)
    out = []
    for j in jogos:
        if casa(j, ("titulo", "etiquetas", "plataforma")):
            out.append({"tipo": "jogo", "id": j["id"], "titulo": j["titulo"],
                        "sub": f"{j.get('plataforma') or 'PC'} · {j.get('status') or 'backlog'}",
                        "capa_url": j.get("capa_url", "")})
    for m in musicas:
        if casa(m, ("titulo", "artista", "album")):
            out.append({"tipo": "musica", "id": m["id"], "titulo": m["titulo"],
                        "sub": str(m.get("artista") or "Artista desconhecido"),
                        "capa_url": m.get("capa_url", "")})
    for d in desejos:
        if casa(d, ("titulo",)):
            out.append({"tipo": "desejo", "id": d["id"], "titulo": d["titulo"],
                        "sub": "Desejo · Steam " + str(d.get("appid") or ""), "capa_url": ""})
    for t in downloads or []:
        if casa(t, ("nome",)):
            out.append({"tipo": "download", "id": t.get("hash", ""), "titulo": t.get("nome", ""),
                        "sub": f"{t.get('pct', 0)}% · {t.get('estado') or 'histórico'}",
                        "capa_url": ""})
    return out[:limite]


__all__ = ["capa_url", "resumo_sistema", "saude_colecao", "_sem_acento", "busca_global"]
