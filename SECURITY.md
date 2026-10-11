# Segurança

O TucoTeca é um aplicativo **local-first**: não há contas, não há servidores
próprios e nenhuma telemetria. Ainda assim:

## Reportar uma vulnerabilidade

Não abra issue pública. Escreva para o mantenedor (perfil do GitHub
`Artur-Lucena`) descrevendo:

- o que acontece e o impacto;
- passos para reproduzir;
- versão (`VERSION`) e SO.

## Escopo e superfície de risco

- **Coleção local** (`dados/`): banco SQLite, saves, pacotes. Backups antes
  de mutações são regra do projeto; a trava `.biblioteca.lock` evita duas
  instâncias na mesma coleção.
- **Rede é sempre sob ação do usuário** (catálogos, capas, yt-dlp,
  atualizações). Downloads verificam integridade quando há SHA publicado.
- **Binários de terceiros** (yt-dlp, FFmpeg, 7-Zip, emuladores, qBittorrent)
  são agregados como processos independentes, com licenças próprias.
- **Credenciais** (ex.: OAuth do Spotify) ficam só na coleção local, nunca no
  repositório. A CI roda gitleaks em todo push.

## Boas práticas para quem desenvolve

- Nunca commitar `dados/`, testes com credenciais reais ou tokens.
- Novas integrações de rede: timeout, falha virando aviso, cache local.
