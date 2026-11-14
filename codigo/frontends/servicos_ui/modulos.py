"""Registro de módulos do desktop (F0): a navegação nasce daqui.

Cada seção do hub é um módulo declarado — embutido por enquanto. Na F3 o
registro vira contrato para módulos de terceiros (manifesto, permissões,
habilitar/desabilitar). O formato de `apresentar()` é o DTO que a ponte
entrega ao renderer do Electron: mexer nele é mudar o protocolo.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Modulo:
    chave: str
    nome: str
    descricao: str = ""
    icone: str = ""
    ordem: int = 100
    origem: str = "embutido"
    habilitado: bool = True
    permissoes: tuple[str, ...] = ()

    def apresentar(self) -> dict:
        return {"chave": self.chave, "nome": self.nome, "descricao": self.descricao,
                "icone": self.icone, "ordem": self.ordem, "origem": self.origem,
                "habilitado": self.habilitado, "permissoes": list(self.permissoes)}


def modulos_padrao() -> list[Modulo]:
    """Módulos embutidos, na ordem da barra lateral do desktop Electron."""
    return [
        Modulo("inicio", "Início",
               "Continuar, buscar e cuidar da coleção — sem sair do lugar.",
               "inicio", 10),
        Modulo("jogos", "Jogos",
               "Todos os seus jogos. Um lugar para começar.",
               "jogos", 20),
        Modulo("musicas", "Músicas",
               "Sua coleção local, com música em todas as telas.",
               "musicas", 30),
        Modulo("desejos", "Desejos",
               "Guarde os títulos que você quer jogar.",
               "desejos", 40),
        Modulo("downloads", "Downloads",
               "Progresso do qBittorrent, sem sair do Hub.",
               "downloads", 50),
        Modulo("integracoes", "Integrações",
               "Catálogos, emuladores e serviços com responsabilidades independentes.",
               "integracoes", 60),
        Modulo("videos", "Vídeos",
               "Importe arquivos locais, pesquise YouTube e abra no reprodutor escolhido.",
               "videos", 70),
        Modulo("youtube", "YouTube",
               "Navegue no YouTube aqui dentro; baixar é sempre ação sua.",
               "youtube", 80),
        Modulo("notificacoes", "Notificações",
               "Avisos do sistema, histórico e terminal de logs.",
               "notificacoes", 85),
        Modulo("configuracoes", "Configurações",
               "Aparência, provedores, estatísticas, backups e coleção.",
               "configuracoes", 90),
    ]
