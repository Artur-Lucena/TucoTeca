"""Lojas instaladas (Hydra, Steam, Epic, GOG, Riot, Windows) e a nota de confiança.

Tudo em árvores falsas dentro do sandbox: nada do PC real é lido (o registro do
Windows também é simulado).
"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

from bib_nucleo.scans import lojas
from executar import afirmar


def _pasta() -> Path:
    return Path(tempfile.mkdtemp())


def _sem_lojas_reais(raiz: Path):
    """Program Files e raízes de varredura apontam para o sandbox."""
    return patch.dict(os.environ, {"ProgramFiles(x86)": str(raiz / "pf86"), "ProgramFiles": str(raiz / "pf"),
                                   "BIBLIOTECA_SCAN_ROOTS": str(raiz / "nada")})


def teste_pontuar_soma_os_sinais_e_limita_em_um():
    raiz = _pasta()
    exe = raiz / "jogo.exe"
    exe.write_bytes(b"MZ")
    rom = raiz / "jogo.nds"
    rom.write_bytes(b"rom")
    cheio = lojas.pontuar({"executable_path": str(exe), "shop": "Steam", "object_id": "10", "horas": "2.5",
                           "origem": "steam-manifest", "tem_metadados": True})
    afirmar(cheio["score"] == 1.0 and cheio["exe_existe"], cheio)
    afirmar("loja conhecida (steam)" in cheio["motivos"] and "2.5h jogadas" in cheio["motivos"], cheio["motivos"])
    vazio = lojas.pontuar({"executable_path": str(raiz / "sumiu.exe"), "shop": "minha", "horas": "x"})
    afirmar(vazio["score"] == 0.05 and "executável não encontrado em nenhum SO" in vazio["motivos"], vazio)
    r = lojas.pontuar({"origem": "rom-nds", "rom_path": str(rom)})
    afirmar(r["score"] == 0.5 and "ROM existe neste SO" in r["motivos"], r)
    afirmar(lojas.pontuar({"origem": "rom-nds", "launch_options": str(raiz / "x.nds")})["score"] == 0.0)


def teste_hydra_candidatos_detector_e_falha():
    raiz = _pasta()
    db = raiz / "hydra-db"
    db.mkdir()
    with patch.dict(os.environ, {"HYDRA_DB_PATH": str(db)}):
        afirmar(lojas.hydra_db_candidates()[0] == db)
        afirmar(lojas.find_hydra_db() is None)  # pasta vazia não conta
        (db / "000001.log").write_bytes(b"x")
        afirmar(lojas.find_hydra_db() == db)
    with patch.object(lojas, "find_hydra_db", return_value=None):
        afirmar(lojas._detector_hydra() == ("Hydra", [], "ausente neste PC"))
    with patch.object(lojas, "find_hydra_db", return_value=db):
        with patch.object(lojas, "scan_hydra_db", side_effect=OSError("travado")):
            afirmar(lojas._detector_hydra()[2] == "falha ao ler: travado")
        with patch.object(lojas, "scan_hydra_db", return_value=[{"titulo": "Hades"}]):
            nome, itens, det = lojas._detector_hydra()
            afirmar(itens == [{"titulo": "Hades", "fonte": "Hydra"}] and det.startswith("1 em "), (itens, det))


def _steam(raiz: Path) -> Path:
    apps = raiz / "steamapps"
    (apps / "common" / "Hades").mkdir(parents=True)
    for exe in ("unins000.exe", "Hades.exe"):
        (apps / "common" / "Hades" / exe).write_bytes(b"MZ")
    (apps / "appmanifest_1145360.acf").write_text('"AppState" { "name" "Hades" "installdir" "Hades" }', encoding="utf-8")
    (apps / "appmanifest_228980.acf").write_text('"name" "Steamworks Common Redistributables"', encoding="utf-8")
    (apps / "appmanifest_1070560.acf").write_text('"name" "Steam Linux Runtime"', encoding="utf-8")
    (apps / "appmanifest_9.acf").write_text('"name" "Sem Pasta" "installdir" "Nao Existe"', encoding="utf-8")
    return apps


def teste_steam_manifestos_viram_jogos_sem_suporte():
    raiz = _pasta()
    apps = _steam(raiz)
    with _sem_lojas_reais(raiz):
        fonte, itens, det = lojas._detector_steam([apps])
        afirmar(fonte == "Steam" and det == "2 em 1 biblioteca(s)", det)
        hades = next(i for i in itens if i["titulo"] == "Hades")
        afirmar(Path(hades["executable_path"]).name == "Hades.exe" and hades["object_id"] == "1145360", hades)
        afirmar(next(i for i in itens if i["titulo"] == "Sem Pasta")["executable_path"] == "")
        afirmar(lojas._detector_steam([raiz / "vazia"])[2] == "Steam ausente")
    afirmar(lojas._appid_de_manifest("appmanifest_70.ACF") == "70" and lojas._appid_de_manifest("x.acf") == "")


def teste_steam_bibliotecas_extras_pelo_libraryfolders():
    raiz = _pasta()
    padrao = raiz / "pf86" / "Steam" / "steamapps"
    if os.name != "nt":
        padrao = raiz / "home-falso" / ".local/share/Steam/steamapps"
    padrao.mkdir(parents=True)
    extra = raiz / "Jogos Steam"
    (extra / "steamapps").mkdir(parents=True)
    caminho = str(extra).replace("\\", "\\\\")
    (padrao / "libraryfolders.vdf").write_text(
        f'"libraryfolders" {{ "1" {{ "path" "{caminho}" }} "2" {{ "path" "{raiz / "sumiu"}" }} }}', encoding="utf-8")
    with _sem_lojas_reais(raiz), patch.object(Path, "home", return_value=raiz / "home-falso"):
        dirs = lojas._steamapps_dirs()
    afirmar(padrao in dirs and extra / "steamapps" in dirs and len(dirs) == 2, dirs)


def teste_epic_manifestos():
    raiz = _pasta()
    m = raiz / "Manifests"
    m.mkdir()
    (m / "a.item").write_text(json.dumps({"DisplayName": "Alan Wake 2", "InstallLocation": str(raiz / "AW2"),
                                          "LaunchExecutable": "bin/AW2.exe", "AppName": "Dill"}), encoding="utf-8")
    (m / "b.item").write_text(json.dumps({"DisplayName": "Sem Exe"}), encoding="utf-8")
    (m / "c.item").write_text("{quebrado", encoding="utf-8")
    (m / "d.item").write_text("[1]", encoding="utf-8")
    (m / "e.item").write_text(json.dumps({"DisplayName": " "}), encoding="utf-8")
    fonte, itens, det = lojas._detector_epic(m)
    afirmar(det == "2 manifesto(s)" and [i["titulo"] for i in itens] == ["Alan Wake 2", "Sem Exe"], itens)
    afirmar(itens[0]["executable_path"] == str(raiz / "AW2" / "bin" / "AW2.exe") and itens[0]["object_id"] == "Dill")
    afirmar(lojas._detector_epic(raiz / "nada")[2] == "sem manifestos")
    if os.name != "nt":
        afirmar(lojas._detector_epic()[2] == "só no Windows")


def teste_gog_info_nas_raizes():
    raiz = _pasta()
    jogo = raiz / "GOG Games" / "Celeste"
    jogo.mkdir(parents=True)
    (jogo / "goggame-1.info").write_text(json.dumps({"name": "Celeste", "gameId": 1,
                                                     "playTasks": [{"path": "/bin/Celeste.exe"}]}), encoding="utf-8")
    (jogo / "goggame-2.info").write_text(json.dumps({"gameId": 2, "playTasks": []}), encoding="utf-8")
    (jogo / "goggame-3.info").write_text("nao e json", encoding="utf-8")
    fundo = raiz / "a" / "b" / "c" / "d" / "e" / "f"
    fundo.mkdir(parents=True)
    (fundo / "goggame-9.info").write_text(json.dumps({"name": "Fundo Demais"}), encoding="utf-8")
    fonte, itens, det = lojas._detector_gog([str(raiz), str(raiz / "nao-existe")])
    afirmar(det == "1 jogo(s)" and itens[0]["titulo"] == "Celeste" and itens[0]["object_id"] == "1", itens)
    afirmar(itens[0]["executable_path"] == str(jogo / "bin" / "Celeste.exe"), itens[0])
    afirmar(lojas._detector_gog([str(raiz / "nao-existe")])[2] == "sem goggame-*.info nas raízes")


def teste_riot_instalacoes():
    raiz = _pasta()
    arq = raiz / "RiotClientInstalls.json"
    arq.write_text(json.dumps({"associated_client": {"C:/Riot/League": "C:/Riot Games/Riot Client/RiotClientServices.exe"},
                               "rc_default": "C:/Riot Games/Riot Client", "rc_live": ""}), encoding="utf-8")
    ruim = raiz / "ruim.json"
    ruim.write_text("[]", encoding="utf-8")
    fonte, itens, det = lojas._detector_riot([arq, ruim, raiz / "sumiu.json"])
    afirmar(det == "1 instalação(ões)" and len(itens) == 1 and itens[0]["shop"] == "riot", (det, itens))
    afirmar(lojas._detector_riot([raiz / "sumiu.json"]) == ("Riot", [], "Riot ausente"))


class _Chave:
    def __init__(self, valores=None, filhos=None):
        self.valores = valores or {}
        self.filhos = filhos or {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _winreg_falso(programas: dict) -> types.ModuleType:
    w = types.ModuleType("winreg")
    w.HKEY_LOCAL_MACHINE, w.HKEY_CURRENT_USER = "HKLM", "HKCU"
    raiz = _Chave(filhos={nome: _Chave(valores=v) for nome, v in programas.items()})

    def abrir(base, sub):
        if isinstance(base, _Chave):
            return base.filhos[sub]
        if base == "HKLM" and "WOW6432Node" not in sub:
            return raiz
        raise OSError("sem chave")

    def valor(chave, campo):
        if campo not in chave.valores:
            raise OSError(campo)
        return chave.valores[campo], 1

    w.OpenKey = abrir
    w.QueryInfoKey = lambda chave: (len(chave.filhos) + 1, 0, 0)  # +1: índice que falha
    w.EnumKey = lambda chave, i: (list(chave.filhos) + [None])[i] or (_ for _ in ()).throw(OSError("fim"))
    w.QueryValueEx = valor
    w.CloseKey = lambda chave: None
    return w


def teste_windows_programas_instalados_sem_lixo():
    if os.name != "nt":
        afirmar(lojas._detector_windows() == ("Windows", [], "só no Windows"))
        return
    falso = _winreg_falso({
        "hades": {"DisplayName": "Hades", "DisplayIcon": '"C:\\Jogos\\Hades\\Hades.exe",0'},
        "redist": {"DisplayName": "Microsoft Visual C++ 2019 Redistributable"},
        "sistema": {"DisplayName": "Componente", "SystemComponent": 1},
        "desinst": {"DisplayName": "Celeste", "DisplayIcon": "C:\\Jogos\\Celeste\\unins000.exe"},
        "sem-nome": {"DisplayIcon": "x.exe"},
    })
    with patch.dict(sys.modules, {"winreg": falso}):
        fonte, itens, det = lojas._detector_windows()
    por = {i["titulo"]: i for i in itens}
    afirmar(det == "2 programa(s)" and set(por) == {"Hades", "Celeste"}, itens)
    afirmar(por["Hades"]["executable_path"] == "C:\\Jogos\\Hades\\Hades.exe", por["Hades"])
    afirmar(por["Celeste"]["executable_path"] == "", por["Celeste"])  # desinstalador não é jogo


def teste_ler_do_disco_junta_e_nao_cai_por_uma_fonte():
    def quebra():
        raise RuntimeError("sem acesso")
    um = {"titulo": "b", "executable_path": "", "shop": "steam", "object_id": "1", "horas": 0, "origem": "steam-manifest"}
    dois = {"titulo": "A", "executable_path": "", "shop": "gog", "object_id": "2", "horas": 0, "origem": "gog"}
    with patch.object(lojas, "_detector_hydra", quebra), \
            patch.object(lojas, "_detector_steam", lambda: ("Steam", [um], "1")), \
            patch.object(lojas, "_detector_epic", lambda: ("Epic", [], "0")), \
            patch.object(lojas, "_detector_gog", lambda: ("GOG", [dois], "1")), \
            patch.object(lojas, "_detector_riot", lambda: ("Riot", [], "0")), \
            patch.object(lojas, "_detector_windows", lambda: ("Windows", [], "0")):
        itens, info = lojas.ler_do_disco()
    afirmar([i["titulo"] for i in itens] == ["A", "b"] and info["total"] == 2, itens)
    hydra = info["fontes"][0]
    afirmar(hydra == {"fonte": "Hydra", "ok": False, "n": 0, "detalhe": "falha: sem acesso"}, hydra)
    afirmar(all(f["ok"] for f in info["fontes"][1:]), info)
