"""Conquistas próprias do Hub: Steam como catálogo, save nativo como evidência.

Não consulta conquistas de conta Steam nem usa registros de Steam emulators.
Regras declarativas são avaliadas em dados locais, sem executar código do save.
"""
from __future__ import annotations

import hashlib
import html.parser
import json
import math
import os
import re
import sqlite3
import struct
import threading
import urllib.parse
from contextlib import closing
from pathlib import Path

from bib_nucleo import base, online

_lock = threading.RLock()
MAX_ITENS = 5000


def _objeto(alvo):
    dados = online.ler_json(alvo, {})
    return dados if isinstance(dados, dict) else {}


def pasta_conquistas(jogo):
    uuid = str(jogo.get("uuid") or "")
    ident = uuid if re.fullmatch(r"[a-fA-F0-9]{32}", uuid) else hashlib.sha256(
        (str(jogo.get("executable_path")) + "\0" + str(jogo.get("titulo"))).encode()).hexdigest()
    return base.DADOS_DIR / "conquistas" / ident


def _raizes_jogo(jogo):
    exe, _campo = base.resolver_exe(jogo)
    exe = base.traduzir_para_atual(exe)
    if not exe:
        return []
    pai = Path(exe).parent
    return [pai, pai.parent] if pai.name.lower() in ("ship", "bin", "win64") else [pai]


def appid_referencia(jogo, informado=""):
    if informado:
        if not re.fullmatch(r"[1-9][0-9]{0,9}", informado):
            raise ValueError("App ID Steam inválido.")
        return informado
    vinculo = _objeto(pasta_conquistas(jogo) / "catalogo.json")
    appid = str(vinculo.get("appid") or jogo.get("object_id") or "")
    if re.fullmatch(r"[1-9][0-9]{0,9}", appid) and (vinculo or jogo.get("shop") == "steam"):
        return appid
    for raiz in _raizes_jogo(jogo):
        for arq in (raiz / "steam_appid.txt", raiz / "steam_settings/steam_appid.txt"):
            try:
                valor = arq.read_text(encoding="utf-8").strip()
                if re.fullmatch(r"[1-9][0-9]{0,9}", valor):
                    return valor
            except (OSError, UnicodeError):
                pass
    from bib_nucleo.scans import canonizar_steam
    return canonizar_steam(jogo.get("titulo") or "")[0]


def _texto(valor):
    if isinstance(valor, dict):
        return str(valor.get("pt-BR") or valor.get("brazilian") or valor.get("en") or
                   valor.get("english") or next(iter(valor.values()), ""))
    return str(valor or "")


def definicoes_locais(jogo):
    out = {}
    for raiz in _raizes_jogo(jogo):
        candidatos = [raiz / "achievements/achievements.json", raiz / "steam_settings/achievements.json"]
        candidatos.extend(raiz.glob("*_Data/Plugins/x86_64/steam_settings/achievements.json"))
        for arq in candidatos[:8]:
            dados = online.ler_json(arq)
            itens = dados.get("achievements", []) if isinstance(dados, dict) else dados
            if not isinstance(itens, list):
                continue
            for item in itens[:MAX_ITENS]:
                if not isinstance(item, dict):
                    continue
                stores = item.get("stores") or {}
                cod = (stores.get("steam") or {}).get("id") or item.get("id") or item.get("name")
                if not isinstance(cod, str) or len(cod) > 200:
                    continue
                out[cod] = {"id": cod, "titulo": _texto(item.get("displayName") or item.get("name")) or cod,
                            "requisito": _texto(item.get("description")), "goal": item.get("goal"),
                            "icon": str(item.get("icon") or ""),
                            "hidden": str(item.get("hidden")).lower() in ("1", "true")}
    return out


class _ParseComunidade(html.parser.HTMLParser):
    """Linhas achieveRow da Comunidade Steam (públicas, sem login/chave)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.itens: list[dict] = []
        self._atual: dict | None = None
        self._campo = ""
        self._profundidade = 0

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "")
        if tag == "div" and "achieveRow" in cls:
            self._atual = {"titulo": "", "requisito": "", "icon": "", "percent": ""}
            self.itens.append(self._atual)
            self._campo = ""
            self._profundidade = 1
        elif self._atual is not None and tag == "div":
            self._profundidade += 1
            if "achievePercent" in cls:
                self._campo = "percent"
        elif self._atual is not None and tag in ("h3", "h5"):
            self._campo = tag
        elif self._atual is not None and tag == "img" and not self._atual["icon"]:
            src = dict(attrs).get("src", "")
            if src.startswith("https://"):
                self._atual["icon"] = src
        elif self._atual is not None and tag == "div" and "achievePercent" in cls:
            self._campo = "percent"

    def handle_data(self, data):
        if self._atual is not None and self._campo:
            chave = {"h3": "titulo", "h5": "requisito"}.get(self._campo, self._campo)
            self._atual[chave] += data

    def handle_endtag(self, tag):
        if self._atual is None:
            return
        if tag in ("h3", "h5") and self._campo in ("h3", "h5"):
            self._campo = ""
        elif tag == "div":
            if self._campo == "percent":
                self._campo = ""
            self._profundidade -= 1
            if self._profundidade <= 0:
                for chave in ("titulo", "requisito", "percent"):
                    self._atual[chave] = " ".join(self._atual[chave].split())
                self._atual, self._profundidade = None, 0


def catalogo_comunidade(appid: str) -> list[dict]:
    """Nomes/descrições/ícones/% públicos; sem login e sem chave (fonte: Comunidade)."""
    if not re.fullmatch(r"[1-9][0-9]{0,9}", appid):
        raise ValueError("App ID Steam inválido.")
    erros = []
    for idioma in ("brazilian", "english"):
        try:
            pagina = online.baixar_texto(
                "https://steamcommunity.com/stats/" + appid + "/achievements/?l=" + idioma)
            break
        except ValueError as e:
            erros.append(str(e))
    else:
        raise ValueError("; ".join(erros) or "Comunidade Steam indisponível.")
    parse = _ParseComunidade()
    try:
        parse.feed(pagina)
    except Exception:
        raise ValueError("Comunidade Steam retornou página inválida.") from None
    saidas = []
    for item in parse.itens:
        titulo = " ".join(item["titulo"].split())
        if not titulo:
            continue
        saidas.append({"titulo": titulo, "requisito": " ".join(item["requisito"].split()),
                       "icon": item["icon"], "percent": item["percent"].strip()})
        if len(saidas) >= MAX_ITENS:
            break
    if not saidas:
        raise ValueError("Comunidade Steam sem conquistas públicas p/ este jogo.")
    return saidas


def percentuais_globais(appid: str) -> dict:
    """{nome_interno: percent} públicos; sem login e sem chave."""
    dados = online.requisitar_json(
        "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/?" +
        urllib.parse.urlencode({"gameid": appid, "format": "json"}))
    lista = (dados.get("achievementpercentages") or {}).get("achievements")
    if not isinstance(lista, list):
        raise ValueError("A Steam não retornou percentuais válidos.")
    return {str(a.get("name") or ""): str(a.get("percent") or "").strip().rstrip("%").strip()
            for a in lista[:MAX_ITENS] if isinstance(a, dict) and a.get("name")}


def unir_comunidade(internos: dict, publicas: list[dict], locais: dict) -> list[dict]:
    """Mantém IDs oficiais. Enriquecimento só por título/ícone único declarado.

    Percentuais são estatísticas arredondadas e mutáveis, não identificadores.
    A lista pública fica separada quando não há vínculo verificável com o ID.
    """
    def nome(valor):
        return " ".join(str(valor or "").casefold().split())
    def icone(valor):
        stem = Path(urllib.parse.urlsplit(str(valor or "")).path).stem
        return stem.casefold() if re.fullmatch(r"[0-9a-fA-F]{40}", stem) else ""
    nomes, icones = {}, {}
    for pub in publicas[:MAX_ITENS]:
        if nome(pub.get("titulo")):
            nomes.setdefault(nome(pub.get("titulo")), []).append(pub)
        if icone(pub.get("icon")):
            icones.setdefault(icone(pub.get("icon")), []).append(pub)
    itens = []
    for cod in list(internos)[:MAX_ITENS]:
        local = locais.get(cod, {})
        candidatos = icones.get(icone(local.get("icon")), []) or nomes.get(nome(local.get("titulo")), [])
        pub = candidatos[0] if len(candidatos) == 1 else {}
        itens.append({"id": cod, "titulo": pub.get("titulo") or local.get("titulo") or cod,
                      "requisito": pub.get("requisito") or local.get("requisito") or "Descrição pública sem vínculo verificável com este ID.",
                      "hidden": local.get("hidden", False), "goal": local.get("goal"),
                      "icon": pub.get("icon") or "", "origem": "steam-comunidade",
                      "metadados_pendentes": not bool(pub or local)})
    return itens


def sincronizar_catalogo(jogo, appid="", save=""):
    """Busca metadados/IDs de referência. Não transfere desbloqueios da Steam."""
    appid = appid_referencia(jogo, appid.strip())
    if not appid:
        raise ValueError("Não encontrei este jogo na Steam. Informe o App ID de referência.")
    chave = online.chave_provedor("steam_key")
    locais = definicoes_locais(jogo)
    erros = []
    itens = []
    completo = False
    publicas = []
    if chave:
        try:
            dados = online.requisitar_json("https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?" +
                urllib.parse.urlencode({"appid": appid, "key": chave, "l": "brazilian"}))
            lista = ((dados.get("game") or {}).get("availableGameStats") or {}).get("achievements", [])
            if not isinstance(lista, list):
                raise ValueError("Catálogo Steam inválido.")
            for ach in lista[:MAX_ITENS]:
                if not isinstance(ach, dict):
                    continue
                cod = str(ach.get("name") or "")
                if cod:
                    itens.append({"id": cod, "titulo": ach.get("displayName") or cod,
                                  "requisito": ach.get("description") or "Requisito oculto na referência Steam.",
                                  "hidden": bool(ach.get("hidden")), "icon": ach.get("icon") or ""})
            completo = bool(itens)
        except (ValueError, TypeError, AttributeError):
            erros.append("Não consegui obter o catálogo completo da Steam; tentando a lista pública.")
    if not itens:
        try:
            publicas = catalogo_comunidade(appid)
            internos = percentuais_globais(appid)
            itens = unir_comunidade(internos, publicas, locais)
            erros.append("Catálogo público salvo. IDs sem vínculo verificável usam os metadados locais; percentuais não determinam vínculos.")
        except ValueError as e:
            erros.append(str(e))
    if not itens:
        try:
            internos = percentuais_globais(appid)
        except ValueError as e:
            raise ValueError("A Steam não retornou um catálogo de conquistas válido: " + str(e)) from None
        for cod in list(internos)[:MAX_ITENS]:
            local = locais.get(cod, {})
            itens.append({"id": cod, "titulo": local.get("titulo") or cod,
                          "requisito": local.get("requisito") or "Descrição requer chave Steam Web API.",
                          "hidden": local.get("hidden", False), "goal": local.get("goal"), "icon": ""})
    unicos = {}
    for item in itens:
        unicos.setdefault(item["id"], item)
    itens = list(unicos.values())
    pasta = pasta_conquistas(jogo)
    catalogo = {"versao": 1, "appid": appid, "jogo": jogo.get("titulo"), "completo": completo,
                "fonte": "steam-key" if completo else "steam-comunidade",
                "sincronizado_em": base.agora_iso(), "itens": itens, "referencias_publicas": publicas}
    with _lock:
        online.gravar_json(pasta / "catalogo.json", catalogo, backup=True)
        config = _objeto(pasta / "leitor.json")
        if save.strip():
            config["save"] = save.strip()
        online.gravar_json(pasta / "leitor.json", config, backup=True)
    # Ícones são acessórios; a lista e os requisitos já persistiram.
    for ach in [i for i in [*itens, *publicas] if i.get("icon")][:256]:
        if online.url_https(ach.get("icon") or ""):
            try:
                online.baixar_imagem(ach["icon"], timeout=5)
            except ValueError:
                pass
    resultado = avaliar_save(jogo)
    resultado["avisos"] = erros
    return resultado


def _strings_blob(raw, offset=4):
    """Vetor de strings do save Mewgenics (u64 count/u64 length, little endian)."""
    if not isinstance(raw, bytes) or len(raw) < offset + 8:
        raise ValueError("Bloco do save Mewgenics inválido.")
    count = struct.unpack_from("<Q", raw, offset)[0]
    offset += 8
    if count > 2000:
        raise ValueError("Vetor do save maior que o limite.")
    out = []
    for _ in range(count):
        if offset + 8 > len(raw):
            raise ValueError("Save truncado.")
        tamanho = struct.unpack_from("<Q", raw, offset)[0]
        offset += 8
        if tamanho > 1000 or offset + tamanho > len(raw):
            raise ValueError("String do save inválida.")
        out.append(raw[offset:offset + tamanho].decode("utf-8"))
        offset += tamanho
    return out


def _ler_save_mewgenics(arq):
    """Save SQLite do Mewgenics: propriedades + blobs de desbloqueio."""
    with closing(sqlite3.connect(arq.resolve().as_uri() + "?mode=ro", uri=True)) as con:
        props = {k: v for k, v in con.execute("SELECT key,data FROM properties")
                 if isinstance(v, (str, int, float))}
        classes = []
        casas = []
        blobs = dict(con.execute("SELECT key,data FROM files WHERE key IN ('unlocks','house_unlocks')"))
        raw = blobs.get("unlocks")
        if isinstance(raw, bytes) and raw[:4] == struct.pack("<I", 3):
            classes = _strings_blob(raw)
        else:
            raise ValueError("Versão não reconhecida do save Mewgenics.")
        raw = blobs.get("house_unlocks")
        if isinstance(raw, bytes) and raw[:4] == struct.pack("<I", 1) and len(raw) >= 12:
            tamanho = struct.unpack_from("<Q", raw, 4)[0]
            if tamanho <= 1000 and 12 + tamanho <= len(raw):
                casas = _strings_blob(raw, 12 + tamanho)
    return {"properties": props, "classes": classes, "house_unlocks": casas}


def _regras_howmanydudes(catalogo):
    return {i["id"]: {"path": ["achievement_progress", i["id"], "complete"], "op": "eq", "value": True}
            for i in catalogo["itens"]}


def _regras_mewgenics(catalogo):
    return {"class_unlock_medic": {"path": ["classes"], "op": "contains", "value": "Medic"},
            "map_unlock_sewers": {"path": ["properties", "mapflag_SewersUnlocked"], "op": "eq", "value": 1},
            "house_upgrade_attic": {"path": ["house_unlocks"], "op": "contains", "value": "SmallHouse_Attic"}}


# Jogos com leitor de save conhecido, por appid Steam (referência). Para
# suportar outro jogo, acrescente uma entrada:
#   raiz: (variável de ambiente, subpasta) onde o save costuma ficar;
#   padroes: globs dentro da raiz; leitor: (sufixo, função) para saves que não
#   são JSON; regras: função(catalogo) -> regras padrão de desbloqueio.
LEITORES_SAVE = {
    "3934270": {  # How Many Dudes
        "raiz": ("LOCALAPPDATA", "HowManyDudes"),
        "padroes": ("global.json", "Game/global.json", "*/Game/global.json"),
        "regras": _regras_howmanydudes,
    },
    "686060": {  # Mewgenics
        "raiz": ("APPDATA", "Glaiel Games/Mewgenics"),
        "padroes": ("steamcampaign*.sav", "saves/steamcampaign*.sav", "*/saves/steamcampaign*.sav"),
        "leitor": (".sav", _ler_save_mewgenics),
        "regras": _regras_mewgenics,
    },
}
PADROES_SAVE_GENERICOS = ("save.json", "global.json", "progression.json")


def ler_save_nativo(arq, appid):
    arq = Path(arq)
    if arq.stat().st_size > 32_000_000:
        raise ValueError("Save maior que o limite do leitor.")
    leitor = LEITORES_SAVE.get(appid, {}).get("leitor")
    if leitor and arq.suffix.lower() == leitor[0]:
        return leitor[1](arq)
    dados = online.ler_json(arq)
    if not isinstance(dados, dict):
        raise ValueError("Este save não é JSON compatível; precisa de um leitor próprio.")
    return dados


def localizar_save(jogo, appid, config):
    informado = str(config.get("save") or jogo.get("save_path") or "").strip()
    raizes = [Path(base.traduzir_para_atual(informado))] if informado else []
    conhecido = LEITORES_SAVE.get(appid, {})
    if not raizes and conhecido.get("raiz"):
        variavel, sub = conhecido["raiz"]
        raizes.append(Path(os.environ.get(variavel, "")) / sub)
    padroes = conhecido.get("padroes", PADROES_SAVE_GENERICOS)
    encontrados = []
    for raiz in raizes:
        if raiz.is_file():
            encontrados.append(raiz)
        elif raiz.is_dir():
            for padrao in padroes:
                encontrados.extend(raiz.glob(padrao))
    encontrados = list(dict.fromkeys(p.resolve() for p in encontrados if p.is_file()))
    if len(encontrados) != 1:
        raise ValueError("Selecione o arquivo de save do usuário." if len(encontrados) > 1 else
                         "Save nativo não localizado. Informe o arquivo/pasta do save.")
    return encontrados[0]


def _regras_padrao(appid, catalogo):
    regras = LEITORES_SAVE.get(appid, {}).get("regras")
    return regras(catalogo) if regras else {}


def validar_regras(regras):
    if not isinstance(regras, dict) or len(regras) > MAX_ITENS:
        raise ValueError("Regras devem ser um objeto JSON por ID de referência.")
    for cod, regra in regras.items():
        if not isinstance(cod, str) or not isinstance(regra, dict):
            raise ValueError("Regra inválida.")
        path = regra.get("path")
        if not isinstance(path, list) or not 1 <= len(path) <= 12 or any(
                not isinstance(p, (str, int)) or isinstance(p, bool) for p in path):
            raise ValueError("Cada regra precisa de um path com chaves/índices do save.")
        if regra.get("op") not in ("eq", "gte", "contains", "exists"):
            raise ValueError("Operadores suportados: eq, gte, contains e exists.")
        if regra.get("op") != "exists" and "value" not in regra:
            raise ValueError("A regra precisa do valor de comparação.")
        if isinstance(regra.get("value"), (dict, list)):
            raise ValueError("O valor de comparação deve ser texto, número ou booleano.")
    return regras


def _avaliar_regra(dados, regra):
    valor = dados
    try:
        for chave in regra["path"]:
            valor = valor[chave]
    except (KeyError, IndexError, TypeError):
        return None
    op, esperado = regra["op"], regra.get("value")
    if op == "exists":
        return True
    if op == "eq":
        if isinstance(valor, bool) or isinstance(esperado, bool):
            return type(valor) is type(esperado) and valor == esperado
        return valor == esperado
    if op == "contains":
        return esperado in valor if isinstance(valor, (dict, list, str)) else None
    if op == "gte":
        if isinstance(valor, bool) or isinstance(esperado, bool):
            return None
        try:
            a, b = float(valor), float(esperado)
            return a >= b if math.isfinite(a) and math.isfinite(b) else None
        except (ValueError, TypeError):
            return None
    return None


def salvar_regras(jogo, texto):
    regras = validar_regras(json.loads(texto))
    online.gravar_json(pasta_conquistas(jogo) / "regras.json", regras, backup=True)
    return avaliar_save(jogo)


def avaliar_save(jogo):
    """Só o save nativo e as regras podem desbloquear. Este caminho não usa rede."""
    pasta = pasta_conquistas(jogo)
    catalogo = _objeto(pasta / "catalogo.json")
    if not isinstance(catalogo, dict) or not isinstance(catalogo.get("itens"), list):
        return {"itens": [], "total": 0, "desbloqueadas": 0, "avaliaveis": 0,
                "status": "Sincronize o catálogo de referência para começar.", "appid": "", "save": ""}
    estado = _objeto(pasta / "estado.json")
    ganhos = dict(estado.get("desbloqueadas") or {})
    regras = _regras_padrao(catalogo["appid"], catalogo)
    custom = online.ler_json(pasta / "regras.json", {})
    regras.update(validar_regras(custom))
    config = _objeto(pasta / "leitor.json")
    arquivo = ""
    dados = None
    erro = ""
    try:
        arq = localizar_save(jogo, catalogo["appid"], config)
        arquivo = str(arq)
        dados = ler_save_nativo(arq, catalogo["appid"])
    except (ValueError, OSError, sqlite3.Error, UnicodeError):
        erro = "Save não localizado/compatível. Informe o save ou instale um leitor/regra para este jogo."
    itens = []
    for ach in catalogo["itens"]:
        cod = ach["id"]
        regra = regras.get(cod)
        atingiu = _avaliar_regra(dados, regra) if dados is not None and regra else None
        if atingiu and cod not in ganhos:
            ganhos[cod] = {"quando": base.agora_iso(), "evidencia": arquivo, "regra": regra}
        icon_url = ""
        if ach.get("icon"):
            p = online.cache_path("imagens", ach["icon"], ".img")
            if p.is_file():
                icon_url = p.resolve().as_uri()
        itens.append(dict(ach, desbloqueada=cod in ganhos, avaliavel=atingiu is not None,
                          status="Desbloqueada no Hub" if cod in ganhos else "Requisito não atingido" if atingiu is False else
                          "Leitor/regra pendente", icon_url=icon_url,
                          quando=(ganhos.get(cod) or {}).get("quando", "")))
    if ganhos != (estado.get("desbloqueadas") or {}):
        with _lock:
            atual = _objeto(pasta / "estado.json")
            ganhos = {**(atual.get("desbloqueadas") or {}), **ganhos}
            online.gravar_json(pasta / "estado.json", {"versao": 1, "desbloqueadas": ganhos}, backup=True)
    avaliaveis = sum(i["avaliavel"] for i in itens)
    return {"itens": itens, "total": len(itens), "desbloqueadas": sum(i["desbloqueada"] for i in itens),
            "avaliaveis": avaliaveis, "appid": catalogo["appid"], "save": arquivo,
            "status": erro or f"{avaliaveis} de {len(itens)} requisitos avaliáveis no save local.",
            "catalogo_completo": catalogo.get("completo", False),
            "referencias_publicas": catalogo.get("referencias_publicas", [])}
