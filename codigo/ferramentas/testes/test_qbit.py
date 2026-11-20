"""qBittorrent integrado: perfil próprio, porta, API em loopback, listar e controlar.

API, executável e processo são simulados: nenhum qBittorrent real é tocado.
"""
import json
import os
import tempfile
import urllib.parse
from pathlib import Path
from unittest.mock import patch

from bib_nucleo import qbit
from executar import afirmar


def _perfil():
    pasta = Path(tempfile.mkdtemp())
    return pasta, patch.dict(os.environ, {"BIBLIOTECA_QBIT_PROFILE": str(pasta), "BIBLIOTECA_QBIT_API": ""})


def teste_perfil_porta_e_api_so_em_loopback():
    pasta, env = _perfil()
    with env:
        afirmar(qbit.perfil_qbit() == pasta)
        afirmar(qbit.qbit_config_path().parent == pasta / "qBittorrent_tucoteca" / "config")
        afirmar(qbit.qbit_backup_local() == pasta / "qBittorrent_tucoteca/data/BT_backup")
        porta = qbit.qbit_porta()
        afirmar(18000 <= porta < 38000 and porta == qbit.qbit_porta(), porta)
        afirmar(qbit.qbit_api_url() == "")  # perfil ainda não criado
        qbit.qbit_config_path().parent.mkdir(parents=True)
        qbit.qbit_config_path().write_text("[Meta]\n", encoding="utf-8")
        afirmar(qbit.qbit_api_url() == f"http://127.0.0.1:{porta}")
        with patch.dict(os.environ, {"BIBLIOTECA_QBIT_API": "http://localhost:8080/"}):
            afirmar(qbit.qbit_api_url() == "http://localhost:8080")
        with patch.dict(os.environ, {"BIBLIOTECA_QBIT_API": "http://exemplo.test:8080"}):
            try:
                qbit.qbit_api_url()
                raise AssertionError("aceitou API fora do loopback")
            except ValueError as e:
                afirmar("loopback" in str(e))


def teste_request_monta_pedido_sem_proxy():
    pasta, env = _perfil()
    pedidos = []

    class Resposta:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self, n):
            return "Ok.".encode()

    class Abridor:
        def open(self, req, timeout):
            pedidos.append((req, timeout))
            return Resposta()

    with env:
        try:
            qbit.qbit_request("app/version")
            raise AssertionError("pediu sem API")
        except ValueError as e:
            afirmar("não iniciado" in str(e))
        with patch.dict(os.environ, {"BIBLIOTECA_QBIT_API": "http://127.0.0.1:9"}), \
                patch.object(qbit.urllib.request, "build_opener", return_value=Abridor()):
            afirmar(qbit.qbit_request("torrents/add", {"urls": "magnet:?x"}, timeout=5) == "Ok.")
    req, timeout = pedidos[0]
    afirmar(req.full_url == "http://127.0.0.1:9/api/v2/torrents/add" and timeout == 5, req.full_url)
    afirmar(urllib.parse.parse_qs(req.data.decode()) == {"urls": ["magnet:?x"]} and req.get_header("Origin") == "http://127.0.0.1:9")


def teste_migrar_save_path_tres_casos():
    destino = Path(tempfile.mkdtemp()) / "Meus Jogos"
    alvo = "Session\\DefaultSavePath=" + destino.as_posix()
    trocado = qbit.migrar_save_path("[BitTorrent]\nSession\\DefaultSavePath=C:/velho\nX=1\n", destino)
    afirmar(trocado == f"[BitTorrent]\n{alvo}\nX=1\n", trocado)
    inserido = qbit.migrar_save_path("[Meta]\n[BitTorrent]\nY=2", destino)
    afirmar(inserido == f"[Meta]\n[BitTorrent]\n{alvo}\nY=2", inserido)
    novo = qbit.migrar_save_path("[Meta]", destino)
    afirmar(novo == f"[Meta]\n[BitTorrent]\n{alvo}\n", novo)


def teste_preparar_perfil_cria_e_migra_com_backup():
    pasta, env = _perfil()
    with env:
        cfg = qbit.qbit_preparar_perfil()
        texto = cfg.read_text(encoding="utf-8")
        afirmar("WebUI\\Address=127.0.0.1" in texto and f"WebUI\\Port={qbit.qbit_porta()}" in texto, texto)
        afirmar("Advanced\\updateCheck=false" in texto and "Session\\DefaultSavePath=" in texto, texto)
        afirmar(qbit.qbit_preparar_perfil() == cfg and not cfg.with_suffix(cfg.suffix + ".bak").exists())
        cfg.write_text("[BitTorrent]\nSession\\DefaultSavePath=D:/outro\n", encoding="utf-8")
        qbit.qbit_preparar_perfil()
        afirmar("D:/outro" not in cfg.read_text(encoding="utf-8"))
        afirmar("D:/outro" in cfg.with_suffix(cfg.suffix + ".bak").read_text(encoding="utf-8"))


def teste_iniciar_valida_e_monta_o_comando():
    pasta, env = _perfil()
    chamadas = []

    class Proc:
        pid = 4242

    with env:
        with patch.object(qbit, "localizar_ferramenta", return_value=None):
            afirmar(qbit.qbit_iniciar()["erro"] == "qBittorrent não encontrado no pacote")
        with patch.object(qbit, "localizar_ferramenta", return_value="qbittorrent.exe"), \
                patch.object(qbit.subprocess, "Popen", side_effect=lambda cmd, **k: chamadas.append(cmd) or Proc()):
            afirmar(qbit.qbit_iniciar("https://site/x.torrent")["erro"] == "torrent/magnet inválido")
            r = qbit.qbit_iniciar("magnet:?xt=urn:btih:ABC")
    afirmar(r["ok"] and r["pid"] == 4242 and r["api"].startswith("http://127.0.0.1:"), r)
    cmd = chamadas[0]
    afirmar(cmd[0] == "qbittorrent.exe" and cmd[-1] == "magnet:?xt=urn:btih:ABC", cmd)
    afirmar("--category=tucoteca" in cmd and any(c.startswith("--profile=") for c in cmd), cmd)


def teste_listar_normaliza_e_marca_completos():
    pasta, env = _perfil()
    dados = [
        {"hash": "aa", "name": "Hades", "size": 1000, "progress": 1, "state": "stalledUP", "content_path": "D:/J/Hades",
         "dlspeed": 0, "eta": 8640000},
        {"hash": "bb", "name": "Celeste", "total_size": 200, "progress": 0.5, "state": "downloading",
         "save_path": "D:/J", "dlspeed": 50, "eta": 4},
        {"hash": "cc", "name": "Quase", "size": 10, "progress": 1, "state": "checkingUP"},
        "lixo",
    ]
    with env:
        afirmar(qbit.qbit_listar() == {"ok": False, "torrents": [], "erro": "API não configurada"})
        with patch.dict(os.environ, {"BIBLIOTECA_QBIT_API": "http://127.0.0.1:9"}):
            with patch.object(qbit, "qbit_request", return_value=json.dumps(dados)):
                r = qbit.qbit_listar()
            with patch.object(qbit, "qbit_request", return_value="{}"):
                ruim = qbit.qbit_listar()
    por = {t["nome"]: t for t in r["torrents"]}
    afirmar(r["ok"] and len(por) == 3, r)
    afirmar(por["Hades"]["completo"] and por["Hades"]["save_path"] == "D:/J/Hades", por["Hades"])
    afirmar(not por["Celeste"]["completo"] and por["Celeste"]["feito"] == 100 and por["Celeste"]["pct"] == 50.0)
    afirmar(Path(por["Celeste"]["save_path"]) == Path("D:/J") / "Celeste", por["Celeste"])
    afirmar(not por["Quase"]["completo"])  # 100% mas ainda conferindo
    afirmar(not ruim["ok"] and "inválida" in ruim["erro"], ruim)


def teste_controlar_pausar_retomar_e_falha():
    chamadas = []
    with patch.object(qbit, "qbit_request", side_effect=lambda ep, dados=None: chamadas.append((ep, dados))):
        afirmar(qbit.qbit_controlar("ab12", "pausar")["ok"] and qbit.qbit_controlar("AB12", "retomar")["ok"])
    afirmar(chamadas == [("torrents/stop", {"hashes": "ab12"}), ("torrents/start", {"hashes": "AB12"})], chamadas)
    with patch.object(qbit, "qbit_request", side_effect=OSError("recusado")):
        afirmar(qbit.qbit_controlar("ab12", "pausar") == {"ok": False, "erro": "recusado"})
