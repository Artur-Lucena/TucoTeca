# Índice da documentação

Mapa por tema dos documentos em `docs/`. Comece por `ARQUITETURA.md` para
se localizar; o fluxo de colaboração está em `docs/CONTRIBUTING.md`.

## Mapa e interface

- [ARQUITETURA.md](ARQUITETURA.md) — mapa de pastas, responsabilidade por
  módulo, modelo de dados, fluxos, concorrência e variáveis de ambiente.
- [DESKTOP_QT.md](DESKTOP_QT.md) — decisão Qt Quick, cobertura por fluxo,
  contratos de integração, concorrência e limites da etapa (A1).
- [VISAO_OS.md](VISAO_OS.md) — visão TucoOS: o Hub como shell pessoal,
  sem reescrita do domínio.

## Releases e legal

- [RELEASES.md](RELEASES.md) — como congelar, gerar bundles, preparar
  anexos e publicar uma release privada (coordenador).
- [LEGAL.md](LEGAL.md) — aviso legal e responsabilidades de uso.
- [RECONCILIACAO_GITHUB.md](RECONCILIACAO_GITHUB.md) — proveniência do
  histórico reconciliado com o remoto e o que nunca vai ao GitHub.

## Revisões técnicas (registro histórico)

- [REVISAO_TECNICA.md](REVISAO_TECNICA.md) — auditoria de código de
  06–07/10/2026: 20 erros comprovados e corrigidos.
- [REVISAO_LINUX_W11.md](REVISAO_LINUX_W11.md) — revisão Linux feita no
  Windows 11: correções verificadas e matriz de compatibilidade por SO.
- [PARTE1_VISUAL_E_AUDITORIA.md](PARTE1_VISUAL_E_AUDITORIA.md) — acabamento
  visual Tk e auditoria de 09/10/2026.
- [PARTE2_RUNTIME_E_INTEGRACOES.md](PARTE2_RUNTIME_E_INTEGRACOES.md) — runtime
  independente, otimização e tamanhos medidos dos artefatos.
- [QOL_1_5.md](QOL_1_5.md) — qualidade de vida 1.5 do desktop Qt (10/10/2026).
- [INTEGRACAO_FINAL_QOL_MIDIAS.md](INTEGRACAO_FINAL_QOL_MIDIAS.md) —
  consolidação de 11/10/2026 das frentes QoL 1.5 e mídias 2.0 no Qt.

## Dados

- [organizacao-local.json](organizacao-local.json) — registro histórico de
  09/10/2026 dos movimentos de artefatos em `dist/`; não é substituto de
  `organizacao_local.py`.
