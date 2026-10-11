# Integração final — QoL 1.5 e mídias 2.0

11/10/2026. Integração das duas frentes depois de pausar a árvore compartilhada.
Novas telas e ações foram implementadas somente no desktop Qt. O código legado
tkinter foi preservado como recebido da etapa anterior.

## Entregas consolidadas

- Música: Deezer, iTunes e MusicBrainz sem credencial; Spotify no mesmo modelo
  de resultados, inclusive playlists/curtidas e paginação. Erro de pesquisa
  aparece inline e deixa de ficar eternamente em “Buscando”.
- OAuth Spotify: uma única função de extração; aceita retorno completo do
  callback ou código puro inteiro. Não aceita prefixo de texto inválido.
- Conquistas: IDs oficiais e referência pública em listas separadas. Percentuais
  globais jamais são identificadores. Correspondência usa definição local
  verificável; save e regras do Hub determinam o desbloqueio offline.
- Videoteca Qt: importação local, busca/download YouTube, reprodutor
  automático/VLC/MPV/MPC-HC e Ctrl+7. HUD adaptativo mantém as sete categorias.
- Mídias: painel de detecção/abertura de imagem, áudio e vídeo; EQ produz uma
  cópia importada como música, com backup e original preservado.
- Downloads: publicação atômica, tratamento de fragmentos, deadline de processo,
  reaproveitamento de vídeos existentes e retomada de conversão sem rebaixar áudio.
- Jogos: `Piratas/` como diretório do runtime portátil; qBittorrent recebe
  savepath explícito e autoTMM desligado. O cliente não é considerado bem-sucedido
  se recusar a adição. Configuração pré-migração ganha backup.
- Hell Clock: instalação movida de `D:\Games\Hell Clock` para
  `D:\Games\Piratas\Hell Clock`; entrada 51 atualizada; 372 arquivos conferidos
  por SHA-256. Junction no caminho antigo mantém referências externas.
- Frente Linux preservada: descoberta por SO/permissão, programas exclusivos
  Windows, DeSmuME, AppImage, Wine, players, progresso e instalador/shell.

## Verificações

- **358 casos: 352 PASS, 6 SKIP por ambiente, 0 FAIL**.
- Inclui carga de 1.000 arquivos/128 conteúdos, 20.000 linhas de progresso,
  filhos sem stdout, timeout/recolhimento, falha de banco/disco, GUI e cache.
- Auditoria visual: sete seções em 1440×920 e 960×640; diálogos de música,
  YouTube, ferramentas e integração; zero erro QML crítico.
- Selftest Qt: **26 jogos**. Banco da coleção preservado durante a auditoria,
  conferido por SHA-256; organização do Hell Clock foi uma ação separada com backup.
- Testes do novo painel de mídia simulam a abertura dos programas; não lançam
  jogos ou áudio. Os adaptadores não instalam automaticamente os nove programas.
- O login de conta Spotify requer configuração/consentimento reais. Testes de
  protocolo e catálogo autenticado são simulados; bibliotecas públicas funcionam
  sem esse login. Não se trata de extrair streams Spotify.
- Linux nativo/macOS ainda dependem de validação no sistema real; ver
  [revisão Linux/W11](REVISAO_LINUX_W11.md).

Relatórios de máquina ficam em `IA/TucoTeca/validacao/`; dados pessoais,
credenciais, saves e arquivos baixados permanecem fora do Git.

## Git

O checkout canônico é `Jogos/biblioteca/`, remoto
`https://github.com/Artur-Lucena/Projeto-Launcher.git`. A pasta de sessão
`IA/TucoTeca/` tem outro Git local sem remoto; `projeto/` e `Git-Projeto.bat`
dão acesso ao checkout canônico. O atraso observado era de commits/alterações
não publicados, e não perda do repositório por mudança de pastas.
