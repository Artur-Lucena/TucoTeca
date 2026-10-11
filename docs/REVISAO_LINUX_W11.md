# Revisão Linux feita no Windows 11

Data: 10/10/2026. Python oficial 3.14, Git Bash e FFmpeg local.

Esta revisão combina inspeção dos ramos Linux, testes herméticos com SO,
PATH e sinais simulados, execução real dos scripts shell em uma sandbox e
processamento real de áudio sintético. O WSL não está instalado nesta máquina:
nenhum resultado abaixo é apresentado como validação de kernel, GPU, áudio
ou sessão gráfica Linux.

## Correções verificadas

| Área | Problema confirmado | Correção |
|---|---|---|
| Ferramentas | Override/manifesto podiam escolher `.exe` no Linux; arquivo sem permissão de execução aparecia disponível | Descoberta comum verifica SO e `X_OK`; `.py/.pyz` usam Python, sem exigir chmod |
| Integrações 2.0 | Buscas locais percorriam Program Files inteiro e podiam ignorar o isolamento do portátil | Caminhos conhecidos, sem busca recursiva; portátil usa apenas componentes locais e overrides explícitos |
| Players de vídeo | Pedido de MPC-HC no Linux devolvia o executável do MPV | Identidade preservada; MPC-HC indicado como exclusivo do Windows |
| Equalizadores | APO/Peace eram tratados como editores de MP3 e como programas nativos de outros SOs | Abrem painéis de saída no Windows; edição de arquivos usa Audacity/Tenacity |
| EQ por arquivo | Erro de permissão ao criar o destino podia escapar; capas de álbum podiam entrar no mapeamento FFmpeg | Retorno de erro orientado, publicação atômica e mapeamento apenas do primeiro fluxo de áudio |
| DeSmuME | `--windowed-fullscreen` do Windows também era passado à build Linux | Sem flags por padrão no Linux/macOS; override explícito preservado |
| DeSmuME | `/usr/games` nem sempre está no PATH | Busca explícita de `desmume` e `desmume-cli` nessa pasta |
| Azahar | Descoberta dependia da caixa do nome/extensão do AppImage | Busca sem depender de caixa, inclusive em filesystem case-sensitive |
| Player Linux/macOS | Pausar duas vezes alterava a contagem; parar um processo suspenso podia depender de kill e não o recolhia | Pausa idempotente; retoma antes de terminar e executa wait após kill |
| Downloads | Leitura de stdout podia bloquear antes do `wait(timeout)` | Leitor dedicado, fila limitada e prazo total; encerra/recolhe o filho e, no Linux, o grupo com FFmpeg |
| Vídeos | Falhas deixavam fragmentos; falha de banco podia deixar arquivo órfão | Staging descartável, publicação após sucesso e limpeza do arquivo novo em falha |
| Importação local | Origem podia mudar entre o hash e a cópia | Confere SHA-256 da cópia antes de publicar; falha não gera registro/arquivo parcial |
| Torrents | `.fastresume` gravado no Windows mantinha destino Windows no dual boot | Traduz o destino para o SO atual antes de medir arquivos no disco |
| Launcher | Script Linux sobrescrevia `BIBLIOTECA_HOME` informado pelo desenvolvedor | Override preservado, argumentos com espaços mantidos |
| Instalador | Ajuda dizia `--destino DIR`, mas só `--destino=DIR` era aceito | Aceita ambos, rejeita opção desconhecida e argumento ausente |
| Atalho | Caminhos com espaços, `%`, `$`, `&` ou aspas não eram escapados corretamente | Geração conforme Desktop Entry, sem interpolação por sed |
| Desinstalação | Atalho root/usuário era removido do lugar errado | Grava o caminho do atalho criado; preserva dados salvo com `--tudo` |
| Bundle gerado no Windows | Arquivos de controle poderiam sair em CRLF, inclusive o caminho usado na remoção do atalho | Geração explícita com LF |
| TUI | Instruções listavam atalhos antigos; selftest dependia de curses real; menu vazio/terminal fechado não tinham saída adequada | Ajuda descreve menus atuais; selftest simulado sem curses; casos vazios/fechamento retornam normalmente |

## Compatibilidade das integrações

“Integrado” significa localizar/configurar/abrir a ferramenta externa; não
significa que seu binário está instalado ou incluído automaticamente.

| Programa/recurso | Windows | Linux | macOS |
|---|---|---|---|
| Krita / GIMP | Nativo | Nativo | Nativo |
| PhotoDemon | Nativo | Sem integração nativa | Sem integração nativa |
| Audacity / Tenacity | Nativo | Nativo | Nativo |
| Equalizer APO / Peace | EQ da saída do sistema | Sem integração nativa | Sem integração nativa |
| Presets FFmpeg do Hub | Exigem FFmpeg | Exigem FFmpeg | Exigem FFmpeg |
| VLC / MPV | Nativo | Nativo | Nativo |
| MPC-HC | Nativo | Sem integração nativa | Sem integração nativa |
| Busca/download YouTube | Exige yt-dlp | Exige yt-dlp | Exige yt-dlp |

PhotoDemon é um projeto independente; não é Photoshop descompilado.
Peace usa **GPL-2.0**, conforme a [página oficial no SourceForge](https://sourceforge.net/projects/peace-equalizer-apo-extension/).
O endereço de referência do APO é [SourceForge](https://sourceforge.net/projects/equalizerapo/).
As flags comuns do DeSmuME Linux são documentadas nas manpages
[desmume](https://manpages.debian.org/bookworm/desmume/desmume.1.en.html) e
[desmume-cli](https://manpages.debian.org/bookworm/desmume/desmume-cli.1.en.html).

## Configuração Linux

`BIBLIOTECA_HOME` aponta para a **pasta-mãe de `dados/`**. Os overrides de
ferramenta apontam para um arquivo executável, não para uma pasta nem para
uma sequência de comandos. Para AppImage, aponte o arquivo e habilite execução:

```sh
chmod +x "$HOME/Aplicativos/Krita.AppImage"
export BIBLIOTECA_KRITA="$HOME/Aplicativos/Krita.AppImage"
export BIBLIOTECA_VLC="/usr/bin/vlc"
```

No checkout, ferramentas instaladas no PATH podem ser usadas. No runtime
portátil, coloque-as em `ferramentas/<programa>/` ou configure o override.
Scripts/zipapps Python são iniciados com o Python do Hub. Ferramentas sem
suporte nativo informam `suportado=false` nos contratos de status.

No Debian/Ubuntu, ferramentas comuns podem ser instaladas pelo gerenciador
da distribuição, por exemplo:

```sh
sudo apt install python3 python3-tk ffmpeg mpv vlc krita gimp audacity desmume
```

`yt-dlp` e emuladores variam de versão entre distribuições. O Hub usa a
instalação localizada ou o override, e informa a dependência ausente.
DeSmuME Linux não tem updater automático neste Hub. O EQ por arquivo exige
FFmpeg e produz uma cópia; não altera o equalizador da saída do sistema.

## Como repetir as verificações

Resultado final no W11: **355 casos, 349 aprovados, 6 pulados por ambiente,
0 falhas**. A suíte percorreu banco/backup, scanners/ROMs, mods/texturas,
controles, música/Spotify, vídeo, torrents, conquistas, Qt, ferramentas
clássicas, TUI e instaladores. Os selftests TUI e clássico também passaram
numa casa temporária; o diagnóstico somente-leitura confirmou integridade
SQLite, exports e sintaxe compatível com Python 3.10.

Durante a execução, quatro expectativas antigas foram corrigidas: três
associavam IDs de conquistas a percentuais globais, e uma confundia a URI
estável da música com sua URL. As regressões agora exigem vínculo local
verificável nas conquistas e preservação da identidade do catálogo na fila.

Relatório estruturado desta execução:
`%TEMP%/opencode/suite-auditoria-linux-w11.json`.

Windows, na raiz do projeto:

```powershell
py -3.14 -B codigo/ferramentas/testes/executar.py --modulo test_linux_portabilidade
py -3.14 -B codigo/ferramentas/provar_linux_shell.py --ffmpeg
py -3.14 -B codigo/ferramentas/diagnosticar.py --json
```

No Linux, troque `py -3.14` por `python3`. A prova shell usa Bash nativo se
ele estiver no PATH. Sem `--ffmpeg`, testa apenas launchers/instalador.
A CI inclui a prova shell nos jobs Ubuntu, além da suíte principal.

Para testar o selftest numa coleção descartável:

```sh
export BIBLIOTECA_HOME="$(mktemp -d)"
python3 codigo/frontends/app_tui.py --selftest
```

`diagnosticar.py` abre SQLite em modo somente-leitura e não migra o banco.
Os testes usam sandboxes próprias. A prova shell gera e instala um pacote
mínimo descartável; a prova FFmpeg usa WAV sintético e não reproduz áudio.

### Cobertura adicional

- 26 regressões em `test_linux_portabilidade.py`, executáveis também no W11.
- Importação de 1.000 arquivos, 128 conteúdos distintos: SHA-256, dedup,
  reimportação e integridade SQLite verificados.
- 20.000 linhas de progresso com callback falhando periodicamente.
- Filho sem stdout, timeout, terminate/kill/wait e grupo de processos Linux.
- Falhas de banco, disco/permissão e arquivo de origem modificado.
- Executáveis, zipapps, Wine, AppImage, terminal fechado e TUI sem curses.
- Prova real: sintaxe de 4 scripts, 2 launchers, dois formatos de destino,
  instalação/desinstalação com caracteres especiais e 6 presets FFmpeg.

## Validação ainda necessária num Linux real

Executar a suíte e a prova shell em Linux; abrir Qt/TUI em sessão gráfica e
terminal reais; testar áudio com PulseAudio/PipeWire, pausa/retomada e fim
natural; executar um jogo Wine e uma ROM própria no Azahar/DeSmuME; conferir
saves, GPU, FUSE/AppImage e permissões do volume compartilhado; abrir os
programas de mídia nativos e verificar o atalho pelo menu do desktop.

Esses pontos dependem do sistema anfitrião e não são comprovados pela
simulação Windows nem pelo Git Bash.
