"""Torrents: bencode, % em disco e BT_backup falso (sem rede, sem cliente)."""
import os
import tempfile
from pathlib import Path

from bib_nucleo import torrents as TT
from executar import afirmar


def _bt(tmp: Path) -> Path:
    bt = tmp / "bt"
    bt.mkdir(parents=True, exist_ok=True)
    os.environ[TT.QBIT_DIR_ENV] = str(bt)
    return bt


def teste_bencode_basico():
    from bib_nucleo.rede.torrents import _bdecodificar
    obj, pos = _bdecodificar(b"d4:infod6:lengthi100e4:name6:ARCIVOee")
    afirmar(obj == {b"info": {b"length": 100, b"name": b"ARCIVO"}}, obj)
    obj, _p = _bdecodificar(b"l4:spam4:eggse")
    afirmar(obj == [b"spam", b"eggs"], obj)
    obj, _p = _bdecodificar(b"i-42e")
    afirmar(obj == -42, obj)
    for ruim in (b"", b"x", b"d4:info", b"l4:spam"):
        try:
            _bdecodificar(ruim)
            afirmar(False, f"devia falhar: {ruim}")
        except ValueError:
            pass


def teste_torrents_progresso_em_disco():
    tmp = Path(tempfile.mkdtemp(prefix="suite-to-"))
    bt = _bt(tmp)
    try:
        dest = tmp / "dest"
        (dest / "PACK" / "sub").mkdir(parents=True)
        (dest / "PACK" / "sub" / "f.bin").write_bytes(b"F" * 60)
        (dest / "PACK" / "sub" / "g.bin").write_bytes(b"G" * 10)
        h = "a" * 40
        (bt / f"{h}.torrent").write_bytes(
            b"d4:infod5:filesld6:lengthi60e4:pathl3:sub5:f.bin"
            b"eed6:lengthi40e4:pathl3:sub5:g.bineee4:name4:PACK12:piece lengthi10eee")
        sp = str(dest).encode("utf-8")
        (bt / f"{h}.fastresume").write_bytes(
            b"d12:qBt-savePath" + str(len(sp)).encode() + b":" + sp +
            b"6:pieces10:" + b"\x01" * 7 + b"\x00" * 3 + b"e")
        r = TT.listar_torrents()
        afirmar(not r["erros"] and len(r["torrents"]) == 1, r)
        t = r["torrents"][0]
        afirmar(t["nome"] == "PACK" and t["total"] == 100, t)
        afirmar(t["feito"] == 70 and t["pct"] == 70.0
                and not t["completo"], t)
        afirmar(t["save_path"].endswith("PACK"), t["save_path"])
        (dest / "PACK" / "sub" / "g.bin").write_bytes(b"G" * 40)
        (bt / f"{h}.fastresume").write_bytes(
            b"d12:qBt-savePath" + str(len(sp)).encode() + b":" + sp +
            b"6:pieces10:" + b"\x01" * 10 + b"e")
        t = TT.listar_torrents()["torrents"][0]
        afirmar(t["completo"] and t["pct"] == 100.0, t)
        ach = TT.encontrar_torrents("pa ck")
        afirmar(len(ach) == 1 and not TT.encontrar_torrents("zzz"), ach)
    finally:
        os.environ.pop(TT.QBIT_DIR_ENV, None)


def teste_torrents_sem_backup_e_lixo():
    tmp = Path(tempfile.mkdtemp(prefix="suite-to-"))
    bt = _bt(tmp)
    try:
        r = TT.listar_torrents()
        afirmar(r == {"torrents": [], "erros": []}, r)
        (bt / ("b" * 40 + ".torrent")).write_bytes(b"lixo{{{")
        (bt / "nota.txt").write_text("x", encoding="utf-8")
        r = TT.listar_torrents()
        afirmar(r["torrents"] == [] and not r["erros"], r)
    finally:
        os.environ.pop(TT.QBIT_DIR_ENV, None)
    afirmar(TT.formatar_tamanho(1177) == "1,1 KB", TT.formatar_tamanho(1177))
    afirmar(TT.formatar_tamanho(3 * 1048576) == "3,0 MB",
            TT.formatar_tamanho(3 * 1048576))


def teste_torrents_resume_versoes_e_pre_alocacao():
    # Dados de arquivo já pré-alocado nunca substituem peças recebidas.
    info = {b"piece length": 40}
    afirmar(TT._progresso_resume(info, {b"pieces": b"\x01\x00\x00"}, 100) == 40)
    afirmar(TT._progresso_resume(info, {b"pieces": b"\x00\x00\x01"}, 100) == 20)
    afirmar(TT._progresso_resume(info, {b"file-version": 2, b"pieces": b"\xa0"}, 100) == 60)
    afirmar(TT._progresso_resume(info, {}, 100) is None)
    tmp = Path(tempfile.mkdtemp(prefix="suite-to-"))
    bt = _bt(tmp)
    try:
        (tmp / "arquivo.bin").write_bytes(b"\0" * 100)
        h = "c" * 40
        (bt / f"{h}.torrent").write_bytes(
            b"d4:infod6:lengthi100e4:name11:arquivo.bin12:piece lengthi40eee")
        sp = str(tmp).encode()
        (bt / f"{h}.fastresume").write_bytes(
            b"d12:qBt-savePath" + str(len(sp)).encode() + b":" + sp +
            b"6:pieces3:\x00\x00\x00e")
        t = TT.listar_torrents()["torrents"][0]
        afirmar(t["pct"] == 0 and not t["completo"], t)
        afirmar(Path(t["save_path"]) == tmp / "arquivo.bin", t)
        # Sem peças: ocupa 100 bytes, mas não é confirmado como concluído.
        (bt / f"{h}.fastresume").write_bytes(
            b"d12:qBt-savePath" + str(len(sp)).encode() + b":" + sp + b"e")
        t = TT.listar_torrents()["torrents"][0]
        afirmar(t["fonte_progresso"] == "estimativa" and not t["completo"], t)
    finally:
        os.environ.pop(TT.QBIT_DIR_ENV, None)


def teste_torrents_localappdata_e_metadados_invalidos():
    from types import SimpleNamespace
    from unittest.mock import patch
    tmp = Path(tempfile.mkdtemp(prefix="suite-to-"))
    local, roaming = tmp / "local", tmp / "roaming"
    bt = local / "qBittorrent/BT_backup"
    bt.mkdir(parents=True)
    with patch.object(TT, "os", SimpleNamespace(name="nt", environ=os.environ)), \
            patch.object(TT, "sys_mac", return_value=False), \
            patch.dict(os.environ, {"LOCALAPPDATA": str(local), "APPDATA": str(roaming)}):
        afirmar(TT.bt_backup_dir() == bt, "buscou apenas Roaming")
    for ruim in (b"dli1eee", b"l" * 100 + b"e" * 100):
        try:
            TT._bdecodificar(ruim)
        except ValueError:
            pass
        else:
            afirmar(False, "bencode inválido aceito")
    try:
        TT._arquivos_info({b"name": b"..", b"length": 100})
    except ValueError:
        pass
    else:
        afirmar(False, "nome fora da pasta aceito")
