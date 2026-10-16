"""`--jogar BUSCA`: abre um jogo sem abrir a janela (atalhos do Desktop).

Usa a mesma coleção e os mesmos serviços do Hub (`servicos_ui`, sem Qt):
resolve o jogo por id ou título, lança com o vigia do núcleo e registra a
sessão ao terminar. É a ponte dos atalhos "via TucoTeca" do Desktop.
"""
from __future__ import annotations

import os
import sys
import threading
from contextlib import closing
from pathlib import Path

_AQUI = Path(__file__).resolve().parent
for _pasta in (str(_AQUI), str(_AQUI.parent)):
    if _pasta not in sys.path:
        sys.path.insert(0, _pasta)

import bib_core as core
from servicos_ui import ServicoBiblioteca

_TITULO_ERRO = "TucoTeca — atalho do jogo"


def erro_visivel(mensagem: str) -> None:
    """Sem console (pythonw), mostra caixa nativa do Windows; senão, stderr."""
    if os.name == "nt" and Path(sys.executable).name.lower().startswith("pythonw"):
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, mensagem, _TITULO_ERRO, 0x10)
        return
    print(f"[erro] {mensagem}", file=sys.stderr)


def resolver_jogo_cli(con, busca: str) -> dict:
    """Acha um jogo por id ou título (exato vence parcial). Sem UI.

    Levanta LookupError quando não há correspondência ou há ambiguidade.
    """
    chave = (busca or "").strip()
    if not chave:
        raise LookupError("informe o id ou parte do título.")
    if chave.isdigit():
        row = con.execute("SELECT * FROM jogos WHERE id=?", (int(chave),)).fetchone()
        if row is None:
            raise LookupError(f"jogo id {chave} não encontrado.")
        return core.row_to_dict(row)
    alvo = chave.lower()
    todos = [core.row_to_dict(r) for r in con.execute("SELECT * FROM jogos").fetchall()]
    exatos = [j for j in todos if (j.get("titulo") or "").lower() == alvo]
    if len(exatos) == 1:
        return exatos[0]
    parciais = [j for j in todos if alvo in (j.get("titulo") or "").lower()]
    if len(parciais) == 1:
        return parciais[0]
    if not parciais:
        raise LookupError(f"nenhum jogo bate com '{chave}'.")
    nomes = ", ".join(f"{j['id']}:{j['titulo']}" for j in parciais[:8])
    raise LookupError(f"'{chave}' é ambíguo: {nomes}.")


def abrir(busca: str, db=None) -> int:
    """Abre o jogo (id ou título) sem a janela; registra a sessão ao fim.

    Códigos: 0 ok, 1 falha ao lançar/registrar, 2 lock ocupado ou busca
    inválida — os mesmos do `--jogar` clássico usado pelos atalhos.
    """
    lock = core.adquirir_lock()
    if not lock.get("ok"):
        erro_visivel(lock.get("erro", "Biblioteca já aberta."))
        return 2
    try:
        return _abrir_com_lock(busca, Path(db) if db else core.DEFAULT_DB)
    finally:
        try:
            core.liberar_lock()
        except Exception:
            pass


def _abrir_com_lock(busca: str, db_path: Path) -> int:
    with closing(core.get_db(db_path)) as con:
        try:
            jogo = resolver_jogo_cli(con, busca)
        except (LookupError, ValueError) as e:
            erro_visivel(str(e))
            return 2
    gid = int(jogo.get("id") or 0)
    if not gid:
        erro_visivel("Jogo sem id na coleção.")
        return 2

    pronto: dict = {}
    feito = threading.Event()

    def ao_fim(sessao, rastreado):
        # Roda na thread vigia do núcleo; só sinaliza o registro da sessão.
        pronto["sessao"], pronto["rastreado"] = sessao, rastreado
        feito.set()

    servico = ServicoBiblioteca(db_path)
    try:
        resultado = servico.iniciar_jogo(gid, ao_fim=ao_fim)
    except ValueError as e:
        erro_visivel(str(e))
        return 1
    if resultado.get("aviso"):
        print(f"[aviso] {resultado['aviso']}", file=sys.stderr)
    if resultado.get("rastreado"):
        feito.wait()
        horas = float(pronto.get("sessao") or 0.0)
        registro = servico.registrar_sessao(gid, horas)
        if not registro.get("ok", True):
            erro_visivel(f"sessão não registrada: {registro.get('erro', 'falha')}")
            return 1
        print(f"[ok] Executando ({resultado.get('modo')}) — sessão registrada ({horas:.2f}h).")
        return 0
    print("[ok] Executando — ao terminar use o Hub (Registrar sessão).")
    return 0
