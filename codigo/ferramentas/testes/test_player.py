"""Player interno: transporte, playlist e auto-avançar (FakeBackend, sem áudio)."""
import tempfile
import wave
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


def _wav_fake(path):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(8000)
        wav.writeframes(bytes(1600))


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


def teste_player_status_desconhecido_nao_avanca():
    """Erro de consulta é estado desconhecido, não fim da música."""
    from bib_nucleo import player as PL
    be = FakeBackend()
    p = PL.Player(be)
    p.carregar(_faixas())
    p.tocar()
    be.vivo = lambda: None
    for _ in range(20):
        afirmar(not p.terminou(), "erro de consulta não pode avançar a fila")
    afirmar(p.idx == 0 and p.estado == "tocando")
    be.vivo = lambda: False
    afirmar(p.terminou(), "fim confirmado deveria permitir avançar")


def teste_player_mci_fim_confirmado():
    """MCI só termina com stopped e posição/duração válidas no fim."""
    from bib_nucleo import player as PL
    be = PL.MciBackend()
    p = PL.Player(be)
    p.carregar(_faixas())
    p.estado = "tocando"
    be._modo = lambda: ""
    afirmar(be.vivo() is None)
    afirmar(not p.terminou(), "MCI erro 263 não é fim da faixa")
    be._modo = lambda: "stopped"
    be.pos_ms = lambda: 0
    be.dur_ms = lambda: 120000
    afirmar(not p.terminou(), "stopped no início não é fim")
    be.pos_ms = lambda: None
    afirmar(not p.terminou(), "posição indisponível não é fim")
    be.pos_ms = lambda: 120000
    afirmar(p.terminou(), "fim real deveria avançar")
    be._modo = lambda: "paused"
    afirmar(not p.terminou(), "pausa não é fim")
    be._modo = lambda: "playing"
    afirmar(not p.terminou(), "ainda tocando não é fim")


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
        _wav_fake(Path(r["alvo"]))
        afirmar(b._decodificar("ff", str(tmp / "b.mp3"), r["alvo"])["ok"])
        Path(r["alvo"]).unlink()
        velho_run = PL.subprocess.run
        try:
            def _ff(*a, **k):
                _wav_fake(Path(a[0][-1]))
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
        r = b.open(str(tmp / "a.wav"))
        afirmar(r.get("ok") and b.alias, (r, b.alias))
        b._modo = lambda: ""
        afirmar(b.vivo() is None)
        b.close()
        afirmar(b.alias == "", b.alias)
    finally:
        PL._eh_nt = velho_nt
        BX.localizar_ffmpeg = velho_loc2


def teste_cache_wav_parcial_nao_e_publicado():
    from unittest.mock import patch

    from bib_nucleo import player as PL
    tmp = Path(tempfile.mkdtemp(prefix="suite-pl-"))
    destino = tmp / "cache.wav"
    destino.write_bytes(b"cache antigo truncado")
    be = PL.MciBackend()

    def ruim(cmd, **_kwargs):
        Path(cmd[-1]).write_bytes(b"RIFF incompleto")
        from types import SimpleNamespace
        return SimpleNamespace(returncode=0, stderr="")

    with patch.object(PL.subprocess, "run", side_effect=ruim):
        r = be._decodificar("ffmpeg-fake", "x.mp3", str(destino))
    afirmar(not r["ok"], r)
    afirmar(destino.read_bytes() == b"cache antigo truncado", "substituiu com saída parcial")
    afirmar(len(list(tmp.iterdir())) == 1, "temporário não foi removido")


def teste_player_mci_caminho_longo_preparado_preserva_original():
    from unittest.mock import patch

    from bib_nucleo import player as PL
    tmp = Path(tempfile.mkdtemp(prefix="suite-mci-"))
    original = tmp / ("audio-longo-" * 9) / "faixa.wav"
    original.parent.mkdir()
    _wav_fake(original)
    dados = original.read_bytes()
    be = PL.MciBackend()
    cache = tmp / "mci"
    comandos = []
    with patch.object(PL, "_eh_nt", return_value=True), \
         patch.object(be, "_pasta_mci", return_value=cache):
        r = be.preparar(str(original))
        afirmar(r["ok"] and Path(r["alvo"]).parent == cache, r)
        afirmar(Path(r["alvo"]).read_bytes() == dados)
        # Uma cópia interrompida não substitui o cache íntegro.
        Path(r["alvo"]).write_bytes(b"cache parcial")
        def falhar(_src, dest):
            Path(dest).write_bytes(b"copia interrompida")
            raise OSError("copia interrompida")
        with patch.object(PL.shutil, "copyfile", side_effect=falhar):
            ruim = be.preparar(str(original))
        afirmar(not ruim["ok"] and Path(r["alvo"]).read_bytes() == b"cache parcial", ruim)
        afirmar(len(list(cache.iterdir())) == 1, "deixou arquivo parcial")
        r = be.preparar(str(original))
        # O transporte não copia novamente na thread da UI.
        with patch.object(PL.shutil, "copyfile", side_effect=AssertionError("cópia na UI")), \
             patch.object(be, "_cmd", side_effect=lambda c: comandos.append(c) or ""):
            afirmar(be.open_preparado(r["alvo"])["ok"])
            be.close()
        afirmar(str(original) not in comandos[0] and r["alvo"] in comandos[0], comandos)
        afirmar(original.read_bytes() == dados and Path(r["alvo"]).read_bytes() == dados)


def teste_player_mci_cache_curto_indisponivel_nao_mexe_no_original():
    from unittest.mock import patch

    from bib_nucleo import player as PL
    tmp = Path(tempfile.mkdtemp(prefix="suite-mci-"))
    original = tmp / ("audio-longo-" * 9) / "faixa.wav"
    original.parent.mkdir()
    _wav_fake(original)
    dados = original.read_bytes()
    be = PL.MciBackend()
    with patch.object(PL, "_eh_nt", return_value=True), \
         patch.object(be, "_pasta_mci", side_effect=OSError("sem temporário curto")), \
         patch.object(be, "_cmd", side_effect=AssertionError("MCI não deve abrir")):
        r = be.open_preparado(str(original))
    afirmar(not r["ok"] and "temporário curto" in r["erro"], r)
    afirmar(original.read_bytes() == dados and not be.alias)
