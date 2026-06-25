# Exemplos Necessarios

Prints/capturas de tela gerados como evidencia de execucao dos exercicios. Todos os arquivos estao na pasta capturas/.

---

## Exercicio 2.1 — Configuracao de MCP servers

| Arquivo | O que mostra | Status |
|---|---|---|
| cenario-A-mcp-json-configurado.png | Terminal com conteudo do .mcp/mcp.json e resumo dos 5 servers configurados | Capturado |
| cenario-B-agente-lendo-doc-novatech.png | Agente listando docs/novatech e lendo POL-001-politica-devolucao.md via server filesystem-docs | Capturado |
| cenario-C-agente-recuperando-chunk-corpus.png | Agente recuperando chunk PROC-042v2-B (Norte 1.8) de data/retrieval-corpus, validado contra gabarito Anexo B | Capturado |
| cenario-D-agente-historico-git.png | git log + git show + git diff mostrando commit inicial e modificacao do mcp.json | Capturado |
| cenario-E-copilot-scaffold-final.png | VS Code com arquivo .mcp/mcp.json aberto mostrando configuracao final dos 5 servers | Capturado |
| cenario-E-copilot-scaffold-sugestao.png | VS Code com sugestao do Copilot para o mcp.json (instancia unica de filesystem — antes da correcao) | Capturado |

---

## Exercicio 2.2 — Implementacao com SDD

| Arquivo | O que mostra | Status |
|---|---|---|
| cenario-G-codigo-path-correto.png | Terminal mostrando src/functions/query/ com handler.ts, validator.ts e response-builder.ts no path correto conforme Anexo C | Capturado |

Nota: evidencia de uso do Copilot para handler.ts esta documentada na secao 2.2 do cenario-exercicio-2-2-desenvolvedor.md. O codigo original do Copilot (com context.log e result.error.message) esta preservado no documento; o arquivo handler.ts no repositorio e a versao corrigida.

---

## Exercicio 2.3 — Estrategia de skills

Nota: o arquivo skills/foundation/typescript-conventions.md e a evidencia principal do exercicio 2.3. O SKILL.md foi gerado com auxilio do Copilot e ajustado conforme documentado em cenario-exercicio-2-3-desenvolvedor.md secao 2.
