# Exercicio 2.3 - Desenvolvedor

## Como conduzi este exercicio

O exercicio pede definir a arvore de skills do projeto, mapear criacao e consumo por papel, e criar o SKILL.md da skill Foundation mais importante.

A arvore de diretorios ja estava no starter repo (Anexo C e Anexo D): 3 niveis (foundation, domain, artifact) com 10 arquivos vazios. O trabalho foi definir quem cria cada skill, quem consome, a frase-ativacao para agentes e a frequencia de uso. Depois, preencher o SKILL.md de typescript-conventions — a skill base que todas as outras assumem conhecida.

Usei o Claude para rascunhar o mapeamento de criacao/consumo e identificar os anti-padroes do Copilot. O Copilot gerou o esqueleto do SKILL.md (estrutura de secoes e primeiros exemplos); ajustei os anti-padroes e completei os exemplos com casos especificos do projeto (pino, ESM, config.ts).

Ferramentas usadas: Claude (chat) para mapeamento e levantamento de anti-padroes; GitHub Copilot para estrutura e primeiros exemplos do SKILL.md.

---

## Prompt que usei no Claude para o mapeamento

Contexto: projeto novatech-assistant, TypeScript/Azure Functions. Time: Tech Lead, 2 Devs, QA, Product Specialist, Delivery Manager. Agentes em uso: GitHub Copilot e Claude Code.

O repositorio tem 10 skills organizadas em foundation/, domain/ e artifact/ (ver lista abaixo). Para cada skill defina:
- nome e descricao curta (frase que um agente reconheceria como ativacao)
- quem cria (papel do time)
- quem consome (papel + agente)
- frequencia de uso estimada

Criterio importante: skills nao devem ser criadas e consumidas so por devs. QA e Product Specialist devem aparecer como criadores em pelo menos uma skill cada.

[listei as 10 skills do starter repo]

---

## 1. Arvore de skills e mapeamento de criacao/consumo

### Foundation — convencoes globais (base para todas as outras skills)

| Skill | Frase-ativacao | Quem cria | Quem consome | Frequencia |
|---|---|---|---|---|
| typescript-conventions | "gere codigo TypeScript seguindo os padroes do projeto" | Tech Lead | Dev, QA (testes), Copilot, Claude Code | Alta — toda geracao de codigo |
| error-handling | "implemente tratamento de erro padrao do projeto" | Tech Lead | Dev, Copilot | Alta — todo endpoint e servico |
| project-structure | "crie um novo modulo seguindo a estrutura do repositorio" | Tech Lead | Dev, Copilot, Claude Code | Media — ao iniciar novo modulo |

### Domain — padroes por camada

| Skill | Frase-ativacao | Quem cria | Quem consome | Frequencia |
|---|---|---|---|---|
| azure-functions-endpoint | "crie um Azure Function HTTP trigger com validacao de input" | Dev Senior | Dev, Copilot | Alta — um endpoint por modulo |
| azure-ai-search-integration | "implemente busca semantica no Azure AI Search" | Dev Senior | Dev, Copilot | Media — pipeline e query endpoint |
| react-components | "crie um componente React para o painel web" | Dev | Dev, Copilot | Media — painel web |
| testing-patterns | "escreva testes de integracao para este endpoint" | QA | Dev, QA, Copilot | Alta — todo endpoint precisa de teste |

### Artifact — receitas de geracao especificas

| Skill | Frase-ativacao | Quem cria | Quem consome | Frequencia |
|---|---|---|---|---|
| create-rag-endpoint | "crie um novo endpoint RAG completo (embedding + busca + completion)" | Dev Senior | Dev, Copilot | Media — um por modulo com RAG |
| create-integration-test | "crie o suite de testes de integracao para o endpoint X" | QA | Dev, QA, Copilot | Alta — um por endpoint implementado |
| create-react-card | "crie um novo card de resposta para o painel web" | Dev | Dev, Copilot | Baixa — poucos componentes no painel |

### Observacao sobre multi-papel

O que o Claude apontou e que confirmei: a skill `testing-patterns` e `create-integration-test` devem ser criadas pelo QA, nao pelo Dev. O QA conhece os padroes de teste do projeto e os criterios de aceite dos verification criteria. Se o Dev criar essas skills, o risco e que os testes gerados cubram apenas o happy path e nao os edge cases que o QA priorizaria.

Lacuna identificada: o projeto vai produzir specs SDD repetidamente (requirements.md, plan.md, tasks.md). Seria util ter uma skill de artifact `create-sdd-spec` criada pelo Product Specialist e consumida por PS e TL. Nao esta no starter repo atual — recomendo adicionar no inicio da fase de implementacao.

---

## Prompt que usei no Copilot para o SKILL.md

Prompt enviado no Copilot Chat com o arquivo skills/foundation/typescript-conventions.md aberto:

Crie o conteudo de um SKILL.md para a skill "typescript-conventions" de um projeto TypeScript com Azure Functions v4 e ESM (type: module). A skill deve ter: contexto (quando usar e frase-ativacao), regras prescritivas organizadas por categoria, exemplos DO/DON'T com codigo real e anti-padroes que LLMs geram sem guidance.

Categorias obrigatorias: imports ESM, tipagem (proibir as any), logging com pino (proibir console.log), configuracao de ambiente (proibir process.env direto), constantes.

O Copilot gerou a estrutura de secoes e os primeiros exemplos de imports e tipagem. Ajustei:
- Anti-padroes: adicionei `require()` (ESM) e import sem extensao .js (os dois mais frequentes do Copilot neste projeto)
- Logging: completei com exemplos especificos do pino estruturado (primeiro argumento como objeto)
- Configuracao: adicionei o caso do non-null assertion com process.env que o Copilot frequentemente gera

Ver print: cenario-H-copilot-gerando-skill-md.png

---

## 2. SKILL.md typescript-conventions (resumo dos pontos principais)

Arquivo completo: skills/foundation/typescript-conventions.md

Regras centrais:
- ESM imports com .js obrigatorio
- Nunca `as any` — usar Zod .parse() ou type guard
- `unknown` em catch, nunca `any`
- Logger pino (src/shared/logger.js), nunca console
- Configuracao via src/shared/config.js, nunca process.env direto

6 anti-padroes documentados com exemplo de codigo e motivo:

1. `as any` para silenciar erro de tipagem
2. `console.log` em vez de logger estruturado
3. `require()` em vez de import ESM
4. `process.env` direto fora de config.ts
5. `error: any` em catch
6. Import sem extensao .js em ESM

Os itens 3 e 6 sao os mais especificos deste projeto (ESM com Node.js). Sem essa skill, o Copilot gera `require()` ou imports sem extensao em praticamente todo arquivo novo — o projeto quebra em runtime sem erro de compilacao, o que dificulta o diagnostico.

---

## 3. Como as skills se conectam ao AGENTS.md

As skills de foundation ficam referenciadas no AGENTS.md (secao Coding Standards, responsabilidade do Tech Lead). Quando o Copilot gera codigo, ele le o AGENTS.md primeiro e depois as skills especificas invocadas. A ordem de leitura importa:

1. AGENTS.md define as regras gerais (proibicoes, stack, contexto do projeto)
2. typescript-conventions (foundation) detalha as convencoes com exemplos
3. azure-functions-endpoint (domain) herda as convencoes e adiciona o padrao especifico de endpoint
4. create-rag-endpoint (artifact) herda domain e foundation e descreve a receita completa

Um agente que le apenas a skill artifact sem as de foundation e domain gera codigo funcionalmente correto mas fora do padrao do projeto.

---

## 4. Conclusao

A arvore ficou com 10 skills coerentes com o que o projeto vai gerar repetidamente. A atribuicao por papel ficou distribuida: TL cria as foundation, Dev Senior cria as domain de backend, QA cria as de teste e Dev cria React. A lacuna de spec SDD foi identificada como skill a adicionar.

O SKILL.md de typescript-conventions ficou concreto com 6 anti-padroes reais. Os mais uteis para o Copilot neste projeto sao os de ESM (require e extensao .js) porque causam erros silenciosos em runtime — que sao os piores de diagnosticar.
