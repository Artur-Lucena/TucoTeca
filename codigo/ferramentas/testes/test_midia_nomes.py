"""Leitor de nomes de vídeo (1.4.4): tabela de casos reais de release."""
from bib_nucleo.midia.nomes import legendas_vizinhas, ler_nome
from executar import afirmar

CASOS = [
    # (caminho, titulo, ano, temporada, episodio)
    ("Filmes/The.Matrix.1999.1080p.BluRay.x264-GROUP.mkv", "The Matrix", 1999, None, None),
    ("Filmes/Interestelar (2014) [1080p] [Dublado].mp4", "Interestelar", 2014, None, None),
    ("Filmes/Parasite.2019.KOREAN.2160p.WEB-DL.DDP5.1.HEVC.mkv", "Parasite", 2019, None, None),
    ("Filmes/Duna Parte Dois 2024 WEB-DL 1080p Dual Audio.mkv", "Duna Parte Dois", 2024, None, None),
    ("Filmes/blade_runner_2049_(2017)_720p.mkv", "blade runner 2049", 2017, None, None),
    ("Filmes/1917.2019.1080p.mkv", "1917", 2019, None, None),
    ("Filmes/Up.mp4", "Up", None, None, None),
    ("Filmes/[YTS] Pulp Fiction (1994) [BluRay] [1080p].mp4", "Pulp Fiction", 1994, None, None),
    ("Filmes/O.Auto.da.Compadecida.2000.NACIONAL.1080p.mkv", "O Auto da Compadecida", 2000, None, None),
    ("Séries/Breaking.Bad.S01E01.720p.HDTV.x264.mkv", "Breaking Bad", None, 1, 1),
    ("Séries/the.office.us.s02e05.web.h264.mkv", "the office us", None, 2, 5),
    ("Séries/Dark - S03E08 - Deja-vu.mkv", "Dark", None, 3, 8),
    ("Séries/Friends 1x01.avi", "Friends", None, 1, 1),
    ("Séries/Game of Thrones S08E06 1080p WEB-DL DD5.1 H264.mkv", "Game of Thrones", None, 8, 6),
    ("Séries/Doctor.Who.2005.S01E01.Rose.mkv", "Doctor Who", 2005, 1, 1),
    ("Séries/Severance/Season 1/S01E03.mkv", "Severance", None, 1, 3),
    ("Séries/Severance (2022)/Season 2/Episode 4.mkv", "Severance", 2022, 2, 4),
    ("Séries/Cidade Invisível/Temporada 1/Episódio 2.mp4", "Cidade Invisível", None, 1, 2),
    ("Séries/Arcane/S2/E07.mkv", "Arcane", None, 2, 7),
    ("Séries/Sherlock.S04E01-E02.mkv", "Sherlock", None, 4, 1),
    ("Séries/One Piece - Temporada 1 Episódio 3.mp4", "One Piece", None, 1, 3),
    ("Séries/Better.Call.Saul.S06E13.Saul.Gone.1080p.AMZN.WEB-DL.DDP5.1.H.264-NTb.mkv", "Better Call Saul", None, 6, 13),
    ("Séries/[SubsPlease] Frieren - S01E28 (1080p).mkv", "Frieren", None, 1, 28),
    ("Séries/The Last of Us S01E03 Long Long Time.mkv", "The Last of Us", None, 1, 3),
    ("Séries/Chernobyl.Season.1.Episode.2.mkv", "Chernobyl", None, 1, 2),
    ("D:\\Vídeos\\Filmes\\Cidade.de.Deus.2002.DVDRip.avi", "Cidade de Deus", 2002, None, None),
    ("D:\\Séries\\Lost\\Season 3\\Lost.S03E07.mkv", "Lost", None, 3, 7),
    ("Filmes/Oppenheimer.2023.IMAX.2160p.UHD.HDR10.mkv", "Oppenheimer", 2023, None, None),
    ("Filmes/Tropa de Elite 2 - O Inimigo Agora é Outro (2010).mkv", "Tropa de Elite 2 - O Inimigo Agora é Outro", 2010, None, None),
    ("Filmes/2001.A.Space.Odyssey.1968.mkv", "2001 A Space Odyssey", 1968, None, None),
]


def teste_tabela_de_nomes():
    erros = []
    for caminho, titulo, ano, temp, ep in CASOS:
        r = ler_nome(caminho)
        esperado = {"titulo": titulo, "ano": ano, "temporada": temp, "episodio": ep,
                    "tipo": "series" if ep is not None else "movie"}
        if r != esperado:
            erros.append(f"{caminho}: {r} != {esperado}")
    afirmar(not erros, "\n".join(erros))


def teste_legendas_vizinhas():
    irmaos = ["Filme.mkv", "Filme.srt", "Filme.pt-BR.srt", "Filme.eng.vtt", "Outro.srt", "Filme.ass", "Filme.nfo"]
    r = legendas_vizinhas("C:/x/Filme.mkv", irmaos)
    afirmar(r == [{"arquivo": "Filme.eng.vtt", "idioma": "eng"}, {"arquivo": "Filme.pt-BR.srt", "idioma": "pt-BR"},
                  {"arquivo": "Filme.srt", "idioma": ""}], r)
