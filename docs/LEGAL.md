# Aviso legal e responsabilidades de uso

> Este documento descreve o papel do TucoTeca e as responsabilidades de quem
> usa o programa. Não é aconselhamento jurídico. Em caso de dúvida sobre
> direitos autorais ou termos de serviço de terceiros, consulte um profissional.

## O que o TucoTeca é

- Um **gerenciador local** de biblioteca de jogos, músicas e vídeos.
- Organiza arquivos e metadados que **você** já possui ou escolheu baixar.
- Os dados ficam na sua máquina (`dados/`). Não há conta obrigatória, servidor
  externo próprio nem telemetria. A API local de leitura é opt-in e somente
  loopback, com token e sem CORS.
- Ferramentas de terceiros (yt-dlp, FFmpeg, 7-Zip, qBittorrent, emuladores)
  são **detectadas ou agregadas** como processos independentes, cada uma com
  a sua própria licença, distribuída junto com o runtime.

## Rede é sempre ação do usuário

- Consultas a catálogos, capas, letras, vídeos e músicas acontecem **somente
  quando você pede**, com tempo limite e cache local.
- Falhas de rede viram aviso; nunca bloqueiam o uso offline da biblioteca.
- `BIBLIOTECA_REDE=0` bloqueia consultas/downloads remotos pelo Hub. Controle
  loopback do qBittorrent e leitura de cache continuam locais. Essa flag não
  é um firewall: um cliente torrent já aberto ou ferramenta externa pode usar
  rede independentemente; pause/feche esses programas se necessário.
- SponsorBlock consulta IDs de vídeos somente depois de ser ativado pelo usuário.

## Integrações e termos de terceiros

Algumas integrações acessam serviços que têm termos próprios. Ao usá-las, você
é responsável por respeitar esses termos e a legislação aplicável no seu país:

- **YouTube:** o navegador embutido carrega o site oficial; o download
  de vídeos é uma ação explícita, sujeita aos termos do YouTube.
- **Spotify, Deezer, iTunes, MusicBrainz, LRCLIB, SponsorBlock e SteamGridDB:**
  possuem limites de uso e exigem
  identificação do aplicativo quando aplicável.
- **Catálogos de terceiros e torrents:** o TucoTeca apenas consulta e organiza
  o que você escolhe. A licitude do conteúdo obtido é de responsabilidade do
  usuário.

## Conteúdo e direitos autorais

- A árvore atual **não contém** capas comerciais versionadas. A pasta opcional
  `midia/fontes-capas/` pode ser criada localmente com placeholders neutros por
  `codigo/ferramentas/gerar_placeholders.py`; ela não é necessária ao runtime.
- O histórico remoto antigo continha capas comerciais e foi preservado durante
  a reconciliação. Sua remoção da árvore atual não elimina os blobs dos commits
  antigos; não foi feita nova reescrita ou force-push. O repositório é privado.
- Capas, letras, trailers e metadados obtidos de terceiros pertencem aos seus
  respectivos titulares e são usados apenas para exibição na sua biblioteca
  pessoal.
- Remoção de conteúdo indevido: se você é titular de direitos sobre algo
  citado no projeto, entre em contato pelo canal indicado em `SECURITY.md` e o
  material será revisado.

## Escopo de uso

- O projeto é **pessoal**, para Tuco/Isa, sem release pública automatizada.
- Os bundles gerados contêm componentes de código aberto; suas licenças
  acompanham cada componente (ver `manifesto-runtime.json`, `FONTE.txt` e
  `LICENSE-TucoTeca.txt` dentro do pacote).
- Este aviso pode ser atualizado a qualquer momento; a versão vigente é a do
  repositório.
