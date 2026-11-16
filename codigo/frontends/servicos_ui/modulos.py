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
    """Módulos embutidos, na ordem da barra lateral do desktop Electron.

    Desejos, Integrações, Vídeos/YouTube e Notificações viraram abas/painéis
    destas seções (o renderer mantém as chaves antigas como apelidos de rota).
    """
    return [
        Modulo("inicio", "Início",
               "Continuar, buscar e cuidar da coleção — sem sair do lugar.",
               "inicio", 10),
        Modulo("jogos", "Jogos",
               "Biblioteca, desejos e tudo dos seus jogos.",
               "jogos", 20),
        Modulo("midia", "Filmes e Séries",
               "Seus vídeos locais e o YouTube; reprodutor interno ou externo.",
               "midia", 30),
        Modulo("musicas", "Músicas",
               "Sua coleção local, com música em todas as telas.",
               "musicas", 40),
        Modulo("downloads", "Downloads",
               "Progresso do qBittorrent, sem sair do Hub.",
               "downloads", 50),
        Modulo("configuracoes", "Configurações",
               "Aparência, integrações, estatísticas, backups e coleção.",
               "configuracoes", 90),
    ]
