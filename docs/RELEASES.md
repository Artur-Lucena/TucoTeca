# Releases privadas da TucoTeca

Uma release é uma entrega congelada, não uma pasta renomeada. Fontes,
bundles, manifestos e tag devem identificar a **mesma versão e revisão**.
O repositório deve permanecer privado. Nenhuma etapa atualiza a instalação
pessoal, a coleção ou o atalho existente.

## 1. Finalizar e congelar

- Atualize `VERSION`, a versão em `pyproject.toml`, README e changelog.
- Não escreva o SHA do próprio commit em um arquivo desse commit. Use a tag;
  o SHA completo vai aos manifestos e a `release.json`, depois do congelamento.
- Execute runner, pytest com cobertura, Ruff e a varredura de segredos.
- Confira o diff e a ausência de dados pessoais; faça commit.
- Antes de enviar, confirme privacidade e avanço remoto. Pare se houver
  divergência. Use push normal; aguarde a CI da revisão exata.

```powershell
$sha = git rev-parse HEAD
py -3.14 -B codigo/ferramentas/testes/executar.py
py -3.14 -B -m pytest --cobertura
ruff check codigo conftest.py
```

## 2. Gerar os bundles

Use staging de build isolado, nunca uma instalação pessoal como destino.
O fluxo SuperHub exclui estado dos emuladores e executa provas com perfis
temporários e conteúdo sintético. O builder portátil legado pode copiar
saves/configuração: **não o use como fluxo de release pessoalmente sanitizada**.

```powershell
py -3.14 -B codigo/ferramentas/montar_superhub.py --extras essencial --formato zip --revisao $sha
py -3.14 -B codigo/ferramentas/montar_superhub.py --extras completo --formato zip --revisao $sha
```

`--reutilizar` só serve para uma árvore SuperHub já sanitizada da mesma variante.
Ele atualiza os fontes, grava a revisão nova e repete todas as provas; não torna
um ZIP antigo em um build novo por renomeação. Preserve antes os pacotes e
relatórios antigos. Os nomes versionados não são sobrescritos automaticamente.

As provas abrangem Python/Tk/Pillow, Qt Quick, FFmpeg, áudio MCI, 7-Zip,
yt-dlp, QuickJS e qBittorrent, além das integrações locais. A variante completa
também prova WebEngine/Multimedia. O ZIP extraído passa pelas mesmas provas.

## 3. Preparar os anexos

```powershell
py -3.14 -B codigo/ferramentas/preparar_release.py --revisao $sha --saida dist/release/v1.0.1
```

O preparador exige HEAD limpo e fontes rastreados. Confere os relatórios,
revisão/versão/variante, hashes, manifestos e os fontes `app/` de cada ZIP.
Recusa arquivos pessoais, caminhos inseguros e provas ausentes. Só renomeia
o staging para a pasta final depois do sucesso; destino existente é recusado.

| Anexo da 1.0.1 | Conteúdo |
|---|---|
| `tucoteca-1.0.1-fontes.zip` | fontes atuais com `MANIFESTO-FONTES.json` |
| `tucoteca-1.0.1-windows-x64-essencial.zip` | runtime sem Qt Addons/Chromium |
| `tucoteca-1.0.1-windows-x64-completo.zip` | runtime com WebEngine/Multimedia |
| `superhub-verificacao-essencial.json` | relatório das provas do essencial |
| `superhub-verificacao-completo.json` | relatório das provas do completo |
| `LICENCAS.md` | versões, avisos e links para os fontes de terceiros |
| `NOTAS-RELEASE.md` | novidades, instalação, atualização e limites |
| `release.json` | revisão e inventário verificável dos anexos |
| `SHA256SUMS.txt` | hashes de todos os outros anexos |

`release.json` não inclui seu próprio hash, para evitar autorreferência;
`SHA256SUMS.txt` o inclui e só exclui o próprio arquivo de checksums.
Relatórios originais e provas detalhadas permanecem locais em `.provas/`.

## 4. Publicar e conferir

1. Confira novamente que o repositório está privado e que as branches não
   divergiram. Crie uma tag anotada na revisão congelada, por push normal.
2. Crie a release com `gh release create --draft --verify-tag`, usando as notas
   geradas e uma lista explícita de anexos.
3. Confira a lista, tamanhos e os digests SHA-256 retornados pela API do GitHub.
   Quando o servidor não oferecer digest, baixe o anexo e confira seu hash.
4. Só depois publique com `gh release edit --draft=false`. Confira a tag,
   a revisão, a privacidade e o inventário final. Registre tudo localmente.

Nunca use `--clobber`, mova uma tag enviada ou reescreva histórico para
corrigir a entrega. A tag `v1.0.0` foi criada na preparação, mas não teve
release; permanece preservada. A primeira publicação é `v1.0.1`.
