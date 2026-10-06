"""Player interno: transporte, playlist e auto-avançar (FakeBackend, sem áudio)."""
import tempfile
from pathlib import Path

import bib_core as core
from executar import afirmar


class FakeBackend:
    """Backend de mentira: `vive_n` polls vivo, depois a faixa 'acaba'."""

    def __init__(self, vive_n=10**9):
        self.vive_n = vive_n
        self.polls = 0
        self.abertos = []
        self.parado = True

    def open(self, path):
        if not path or path == "sumido.mp3":
            return {"ok": False, "erro": "arquivo não encontrado."}
        self.abertos.append(path)
        self.polls = 0
        self.parado = True
        return {"ok": True}

    def play(self):
        self.parado = False
        return {"ok": True}

    def pause(self):
        self.parado = True
        return {"ok": True}

    def resume(self):
        self.parado = False
        return {"ok": True}

    def stop(self):
        self.parado = True

    def vivo(self):
        if self.parado:
            return False
        self.polls += 1
        return self.polls <= self.vive_n

    def pos_ms(self):
        return 1000 * self.polls

    def dur_ms(self):
        return 180000

    def close(self):
        self.parado = True


def _faixas(n=3):
    return [{"path": f"m{i}.mp3", "titulo": f"T{i}"} for i in range(n)]


def teste_player_transporte():
    from bib_nucleo import player as PL
    p = PL.Player(FakeBackend())
    afirmar(p.estado == "parado" and p.atual() is None)
    p.carregar(_faixas())
    r = p.tocar()
    afirmar(r.get("ok") and p.estado == "tocando", (r, p.estado))
    afirmar(p.atual()["titulo"] == "T0" and p.atual()["pos_ms"] is not None)
    r = p.alternar()
    afirmar(r.get("ok") and p.estado == "pausado", (r, p.estado))
    r = p.alternar()
    afirmar(r.get("ok") and p.estado == "tocando", (r, p.estado))
    p.parar()
    afirmar(p.estado == "parado" and not p.terminou())
    r = p.tocar(9)
    afirmar(not r.get("ok"), r)


def teste_player_auto_avancar():
    from bib_nucleo import player as PL
    be = FakeBackend(vive_n=2)
    p = PL.Player(be)
    p.carregar(_faixas())
    p.tocar()
    vistos = 0
    while not p.terminou() and vistos < 10:
        vistos += 1
    afirmar(p.terminou(), vistos)
    r = p.proxima()
    afirmar(r.get("ok") and p.atual()["titulo"] == "T1", (r, p.atual()))
    r = p.anterior()
    afirmar(r.get("ok") and p.atual()["titulo"] == "T0", (r, p.atual()))
    p.tocar(2)
    r = p.proxima()  # última: para, sem wrap
    afirmar(not r.get("ok") and p.estado == "parado", (r, p.estado))
    r = p.anterior()
    afirmar(r.get("ok") and p.atual()["titulo"] == "T1", (r, p.atual()))


def teste_player_falhas():
    from bib_nucleo import player as PL
    p = PL.Player(FakeBackend())
    afirmar(not p.proxima().get("ok"), "fila vazia devia falhar")
    afirmar(not p.anterior().get("ok"), "fila vazia devia falhar")
    afirmar(not p.pausar().get("ok"), "pausar parado devia falhar")
    p.carregar([{"path": "sumido.mp3", "titulo": "X"}])
    r = p.tocar()
    afirmar(not r.get("ok") and p.estado == "parado", (r, p.estado))
    p.carregar([])
    afirmar(p.idx is None and p.atual() is None)


def teste_player_factory_nunca_levanta():
    from bib_nucleo import player as PL
    b = PL.criar_backend()
    for m in ("open", "play", "pause", "resume", "stop", "vivo",
              "pos_ms", "dur_ms", "close"):
        afirmar(callable(getattr(b, m, None)), m)
    r = b.open("")
    afirmar(not r.get("ok"), r)
    nulo = PL.NuloBackend("motivo x")
    afirmar(nulo.open("a")["erro"] == "motivo x")
    afirmar(nulo.vivo() is False)
    mci = PL.MciBackend()
    afirmar(mci._novo_alias() != mci._novo_alias(), "alias devia variar")
    import os
    if os.name != "nt":
        afirmar(not mci.open("a.mp3").get("ok"), "MCI fora do Win devia falhar")
    afirmar("player" in PL.__all__ or "Player" in PL.__all__)
    afirmar("Player" in core.__all__, "bib_core devia reexportar")


def teste_player_mci_rotear_e_cache():
    from bib_nucleo import baixar as BX
    from bib_nucleo import player as PL
    b = PL.MciBackend()
    afirmar(not b._rotear("")["ok"])
    afirmar(not b._rotear("sumido.mp3")["ok"])
    tmp = Path(tempfile.mkdtemp(prefix="suite-pl-"))
    (tmp / "a.wav").write_bytes(b"RIFFfake")
    (tmp / "b.mp3").write_bytes(b"ID3fake" * 100)
    r = b._rotear(str(tmp / "a.wav"))
    afirmar(r.get("ok") and r["modo"] == "direto", r)
    velho_loc = BX.localizar_ffmpeg
    BX.localizar_ffmpeg = lambda: ""
    try:
        r = b._rotear(str(tmp / "b.mp3"))
        afirmar(not r.get("ok") and "ffmpeg" in r.get("erro", "").lower(), r)
    finally:
        BX.localizar_ffmpeg = velho_loc
    BX.localizar_ffmpeg = lambda: "ff-fake"
    try:
        r = b._rotear(str(tmp / "b.mp3"))
        afirmar(r.get("ok") and r["modo"] == "cache"
                and r["alvo"].endswith(".wav"), r)
        # decodificar pula cache existente
        Path(r["alvo"]).write_bytes(b"WAVvelho")
        afirmar(b._decodificar("ff", str(tmp / "b.mp3"), r["alvo"])["ok"])
        Path(r["alvo"]).unlink()
        velho_run = PL.subprocess.run
        try:
            def _ff(*a, **k):
                Path(a[0][-1]).write_bytes(b"WAVnovo")
                class R:
                    returncode = 0
                    stderr = ""
                return R()
            PL.subprocess.run = _ff
            afirmar(b._decodificar("ff", str(tmp / "b.mp3"), r["alvo"])["ok"])
            def _ff_ruim(*a, **k):
                class R:
                    returncode = 1
                    stderr = "ERROR: x"
                return R()
            PL.subprocess.run = _ff_ruim
            Path(r["alvo"]).unlink(missing_ok=True)
            rc = b._decodificar("ff", str(tmp / "b.mp3"), r["alvo"])
            afirmar(not rc.get("ok") and "ERROR" in rc.get("erro", ""), rc)
        finally:
            PL.subprocess.run = velho_run
    finally:
        BX.localizar_ffmpeg = velho_loc
    # poda LRU com teto zerado
    from bib_nucleo.base import CACHE_WAV_DIR
    CACHE_WAV_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_WAV_DIR / "velho.wav").write_bytes(b"0" * 100)
    b.CACHE_MB = 0
    b._podar_cache()
    afirmar(not (CACHE_WAV_DIR / "velho.wav").exists(), "poda devia apagar")
    # open ponta a ponta com MCI falsificado (vale no Linux também)
    velho_nt = PL._eh_nt
    velho_loc2 = BX.localizar_ffmpeg
    BX.localizar_ffmpeg = lambda: "ff-fake"
    PL._eh_nt = lambda: True
    try:
        b._cmd = lambda c: ""
        b._decodificar = lambda f, s, d: {"ok": True}
        r = b.open(str(tmp / "b.mp3"))
        afirmar(r.get("ok") and b.alias, (r, b.alias))
        b.vivo()  # com _cmd falso: só não pode levantar
        b.close()
        afirmar(b.alias == "", b.alias)
    finally:
        PL._eh_nt = velho_nt
        BX.localizar_ffmpeg = velho_loc2
