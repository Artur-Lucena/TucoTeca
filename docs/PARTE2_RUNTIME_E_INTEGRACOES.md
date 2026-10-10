# Parte 2 — runtime independente, otimização e compactação

09/10/2026. Primeira entrega implementada da Parte 2.

## Resultado medido

Tamanhos abaixo em MiB (1.048.576 bytes), arredondados a duas casas.

| Artefato | Tamanho | Comparação com ZIP anterior |
|---|---:|---:|
| Portátil anterior, 23/09 | 298,10 | referência |
| SuperHub completo ZIP | 144,22 | 51,6% menor |
| SuperHub completo 7z/LZMA2 sólido | 97,16 | 67,4% menor |

O runtime novo descompactado ocupa aproximadamente 370,42 MiB. Inclui
mais ferramentas de integração que o anterior; o ganho principal veio
da separação entre programa e estado pessoal, além da poda e compactação.
O ZIP anterior continha cerca de 400 MiB de estado/mods do Azahar. O
qBittorrent instalado também tinha aproximadamente 162 MiB de `.pdb`.

Arquivos gerados em `dist/windows/`:

- `tucoteca-superhub-windows-x64-20261009.zip`
- `tucoteca-superhub-windows-x64-20261009.7z`
- `superhub-verificacao.json`: tamanhos exatos, SHA-256 e provas da árvore
  e dos dois arquivos extraídos.

## Estrutura do pacote

```text
BibliotecaHub.bat / Debug-Console.bat
README-PORTATIL.txt / LICENSE-TucoTeca.txt
manifesto-runtime.json
app/                    fontes locais editáveis
python/                 Python 3.14.7 + Tk + Pillow
ferramentas/
  7zip/                 7z.exe + 7z.dll
  ffmpeg/               FFmpeg 9.0.2
  yt-dlp/               zipapp oficial 2026.08.19, com EJS
  quickjs/              QuickJS-NG 0.17.0
  qbittorrent/          qBittorrent 5.2.4
emuladores/
  Azahar/               2126.1.1, DLLs/plugins e user/ novo
  DeSmuME/              release_0_9_13
dados/                  coleção/perfis criados localmente
```

As fontes da TucoTeca permanecem arquivos `.py`. Os componentes de
terceiros são executados como processos independentes, com suas licenças
e links de fonte junto deles. Não foi aplicado UPX nem alterado um executável
de terceiro. Os codecs de Pillow não usados pela UI (AVIF, fontes e CMS)
foram omitidos; PNG/JPEG/WebP/GIF e redimensionamento continuam disponíveis.

## Integrações e portabilidade

### Descoberta local

`bib_nucleo/ferramentas.py` resolve executáveis pelo manifesto, pastas
relativas e overrides explícitos. No runtime completo não há fallback
silencioso para PATH ou instalações deste PC. O checkout conserva os
fallbacks legados para continuar utilizando suas instalações atuais.

O runtime vence a casa canônica do PC de build, mesmo sem variável
`BIBLIOTECA_HOME`. O manifesto é local/editável e registra caminhos,
plataforma, versões, fontes, licenças, tamanhos e hashes.

O yt-dlp usa a distribuição zipimport oficial, de aproximadamente 3 MiB,
executada pelo Python incluído. Isso evita outro interpretador embutido
no downloader. QuickJS-NG, suportado pelo yt-dlp, fornece o runtime JS
em aproximadamente 2 MiB. Deno continua aceito como override opcional.

### qBittorrent

- Magnets abertos no Hub são encaminhados diretamente ao cliente, sem
  depender da associação magnet/.torrent do Windows.
- O perfil usa `dados/perfis/qBittorrent_tucoteca/`, independente do
  perfil instalado. Fast-resume usa caminhos relativos ao perfil.
- Web API ligada somente a 127.0.0.1, porta determinística por casa.
  Origin/Referer corretos e conexão sem proxy para o endpoint local.
- O GUI exige um hash de credencial mesmo quando o localhost está dispensado
  de autenticação. O bootstrap gera PBKDF2-SHA512 no formato do projeto;
  a prova nativa confirmou que a API inicia corretamente.
- Downloads mostra progresso, velocidade/ETA e pausar/retomar via API.
  Consultas HTTP são feitas fora da thread Tk; a tela usa snapshots e não
  repete a consulta no callback de renderização.
- Se a API estiver indisponível, o histórico em arquivo continua sendo
  fallback. No checkout, o histórico instalado pode aparecer junto ao cliente
  integrado. Itens históricos não recebem controles de uma API que não os possui.

## Otimizações e correções

1. Builder novo monta perfis vazios: não incorpora saves, mods, HD, histórico,
   configurações pessoais, AppImage Linux ou símbolos `.pdb` no runtime Windows.
2. 7-Zip completo: o `7z.exe` do PC carregava a DLL de outro diretório.
   Agora a DLL acompanha o exe; seu caminho de carregamento foi confirmado.
3. **Bug crítico na dieta antiga:** `*.py[cod]` também correspondia a `.pyd`.
   Isso apagava SQLite/Tk e outras extensões depois do selftest do builder.
   A poda agora remove apenas `.pyc/.pyo`; teste protege extensões nativas.
4. Scripts oficiais Tcl/Tk já em cache são reutilizados antes de tentar rede.
5. Manifesto é cacheado por arquivo/mtime/tamanho, preservando edição local.
6. Banco: evita repetir inicialização completa em conexões de um arquivo/schema
   já verificado. Identidade, mtime e `schema_version` invalidam o cache;
   backfill de UUID e migrações continuam sendo verificados em testes.

### Benchmark de conexões

Em snapshot da coleção local, 100 conexões + consulta de contagem, 3 rodadas:

- Antes: 91,74 / 96,57 / 91,63 ms.
- Depois: 57,18 / 54,10 / 52,63 ms.
- Mediana: 91,74 → 54,10 ms, aproximadamente 41% menos tempo nesse cenário.

É uma medição de operações de banco, não uma promessa de acelerar todo o app
por esse percentual.

## Verificação realizada

- Suíte: **251 executados, 6 pulados por condições do Windows, 0 falhas**
  (257 descobertos).
- Sintaxe/diagnóstico: 61 fontes Python, banco real íntegro, 25 jogos,
  51 músicas, 4 desejos; diagnóstico da coleção em somente-leitura.
- Runtime validado após a dieta e **depois da extração do ZIP e do 7z**,
  em diretórios diferentes, com PATH reduzido ao System32.
- Python/Tk/Pillow, criação/leitura JPEG e PhotoImage nativos.
- FFmpeg local: versão e conversão de WAV artificial para MP3.
- yt-dlp local: execução da versão; QuickJS: execução de JavaScript local.
- qBittorrent local: perfil temporário, API de versão, torrent artificial
  com dados já existentes, 100%, pausa, retomada e encerramento.
- Integridade dos arquivos comprimidos e manifesto SHA-256.

As provas não alteraram os perfis do qBittorrent instalado nem migraram a
coleção real para o pacote. O runtime começa vazio; os dados são transferíveis
pelo pacote de coleção da própria TucoTeca.

## Próximas entregas possíveis

1. Fila persistente de conclusão/instalação/importação de jogos, com idempotência
   e identificação da pasta instalada. A importação de concluídos ainda é
   acionada explicitamente; um setup baixado não é um jogo instalado.
2. Atualizador de componentes que mantenha versões/licenças/manifesto em sincronia,
   com publicação atômica e rollback.
3. Pacotes nativos completos Linux/macOS. Os caminhos/overrides e testes de
   compatibilidade continuam funcionando, mas este artefato é Windows x64.
4. Fonte FFmpeg com seleção de codecs específicos de áudio, após provas de
   formatos e reprodução, para reduzir ainda mais o maior sidecar.
5. Resolver metadados por pasta/manifesto/AppID e a wishlist pela API moderna.

## Reproduzir

```powershell
py -3.14 codigo/ferramentas/testes/executar.py
py -3.14 codigo/ferramentas/montar_superhub.py --formato todos
# Atualizar fontes no runtime já montado e repetir provas/compactação:
py -3.14 codigo/ferramentas/montar_superhub.py --reutilizar --formato todos
```

Construir pode obter os componentes oficiais ausentes; depois de empacotado,
executar o programa e trabalhar com arquivos locais não exige instalação ou rede.
