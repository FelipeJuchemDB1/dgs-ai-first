# Exercicio 2.1 - Desenvolvedor

## Como conduzi este exercicio

A tarefa era configurar os MCP servers do projeto de forma que agentes de IA (Copilot, Claude Code) conseguissem acessar repositorio, documentacao e corpus de chunks sem dependencia de nenhum servico pago ou externo.

Abordagem: usei o Claude para rascunhar o mapeamento de necessidades para reference servers locais. O rascunho inicial tinha uma instancia unica de filesystem com todos os caminhos juntos. Revisei porque isso viola o principio de least privilege: o agente teria permissao de escrita nos documentos de negocio e no corpus, o que nao era o objetivo. Separei em duas instancias, o que resultou em 5 servers no total e fechou melhor o escopo.

O arquivo mcp.json foi ajustado manualmente apos a revisao. O Copilot gerou o scaffold da estrutura JSON.

Ferramentas usadas: Claude (chat) para mapeamento e analise de riscos; GitHub Copilot para gerar o scaffold inicial do mcp.json.

---

## Prompt que usei no Claude

Contexto: projeto novatech-assistant, repositorio local TypeScript/Azure Functions. Agentes em uso: GitHub Copilot e Claude Code. Sem acesso a servicos externos nesta fase.

Mapeie as seguintes necessidades para reference servers locais e gratuitos do Model Context Protocol (filesystem, git, memory, everything):

1. Ler e escrever codigo, specs e skills do repositorio
2. Ler documentacao de negocio da NovaTech em docs/novatech (read-only, fonte de negocio)
3. Ler corpus de chunks em data/retrieval-corpus (read-only, para testes de retrieval)
4. Consultar historico, diff e branches do repositorio local
5. Manter memoria persistente de decisoes arquiteturais e glossario de dominio

Para cada necessidade: qual server, o que ele expoe (tools/resources/prompts), quem consome e qual escopo minimo justificado. Separar escopos de escrita dos de leitura.

---

## 1. Mapeamento de necessidades para servers

### 1.1 Tabela de mapeamento

| Necessidade | Equivalente cloud | Server local | Expoe | Quem consome | Escopo |
|---|---|---|---|---|---|
| Codigo, specs, skills (rw) | GitHub | filesystem-rw | read_file, write_file, list_directory, create_directory, search_files | Dev, Copilot, Claude Code | ./src, ./specs, ./skills |
| Docs de negocio NovaTech (read-only) | Confluence | filesystem-docs | read_file, list_directory, search_files | Todos os agentes | ./docs/novatech |
| Corpus de chunks (read-only) | Azure AI Search | filesystem-docs | read_file, list_directory, search_files | Dev, Copilot (testes de retrieval) | ./data/retrieval-corpus |
| Historico e branches do repo | GitHub / Azure DevOps | git | git_log, git_diff, git_status, git_show, git_branch | Dev, TL, Copilot | repositorio local (.) |
| Memoria de decisoes e glossario | Knowledge Base / Wiki | memory | create_entities, create_relations, read_graph, search_nodes, add_observations | Todos os papeis e agentes | grafo persistente local |

O server `everything` entra fora desse mapeamento funcional. Ele serve para o time aprender as primitivas de MCP (tools, resources, prompts) sem risco, porque nao tem acesso ao repositorio de producao.

### 1.2 O que o Claude sugeriu e o que corrigi

O Claude gerou a estrutura com 4 servers, mas com filesystem em instancia unica apontando para:
`./src ./specs ./skills ./docs ./data`

Problema: instancia unica com escopo amplo da permissao de escrita em docs/novatech e data/retrieval-corpus. O agente poderia, em uma instrucao mal formulada, sobrescrever documentos de negocio ou alterar o corpus sem revisao humana.

Correcao que apliquei:
- Separei em duas instancias: filesystem-rw (escrita liberada) e filesystem-docs (so leitura pretendida).
- Resultado: 5 servers no mcp.json, o que tambem bate com os 5 needs mapeados acima.
- Limitacao conhecida: o server filesystem padrao nao tem flag --readonly nativa. A separacao em instancia propria e a primeira camada de controle no nivel de configuracao MCP. Para garantir read-only real, complementei com permissoes de SO nas pastas (ver secao 4).

O Copilot gerou o scaffold JSON (ver evidencia na secao 3). Ajustei os paths e a separacao de instancias manualmente.

---

## 2. Arquivo .mcp/mcp.json final

```json
{
  "mcpServers": {
    "filesystem-rw": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "./src",
        "./specs",
        "./skills"
      ]
    },
    "filesystem-docs": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "./docs/novatech",
        "./data/retrieval-corpus"
      ]
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "."]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "everything": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-everything"]
    }
  }
}
```

### 2.1 Justificativa de escopo por server

filesystem-rw:
- Escopo: ./src, ./specs, ./skills
- Justificativa: esses sao os artefatos de desenvolvimento que o agente precisa criar e editar. Limitar a essas tres pastas exclui .env, infra/, docs/ e data/. Um agente com acesso a raiz do repositorio poderia ler segredos de configuracao ou modificar arquivos de build sem intencao.

filesystem-docs:
- Escopo: ./docs/novatech, ./data/retrieval-corpus
- Justificativa: sao fontes de negocio e de referencia. O agente precisa ler para fundamentar respostas e testes, mas nao tem motivo para escrever. Separar em instancia propria deixa explicito no nivel de configuracao que essas pastas sao fontes, nao destinos de edicao. A restricao real de escrita e feita via permissao de SO (ver secao 4.1).

git:
- Escopo: repositorio inteiro (necessario para log, diff e status)
- Justificativa: o server git nao suporta escopo por subpasta. As operacoes expostas sao de leitura (git_log, git_diff, git_status, git_show, git_branch). Nenhuma operacao de escrita (push, commit, reset) e exposta por padrao neste server.

memory:
- Escopo: grafo local persistido em arquivo pelo server
- Justificativa: armazena decisoes arquiteturais e glossario de dominio entre sessoes. Nao tem escopo de arquivo do repositorio. Dados persistidos ficam no diretorio de dados do server, separado do repo.

everything:
- Escopo: nenhum (nao aponta para o repositorio)
- Justificativa: server de aprendizado das primitivas MCP. Tem tools, resources e prompts artificiais para explorar o protocolo sem risco. Nao deve receber nenhum caminho de producao.

---

## 3. Evidencia de execucao

Os cenarios abaixo foram executados com o Claude Code operando como agente sobre o repositorio local. Prints capturados durante a execucao.

### 3.1 Cenario A: configuracao dos 5 servers (print: cenario-A-mcp-json-configurado.png)

Print mostra o conteudo do .mcp/mcp.json com os 5 servers configurados e o resumo de escopo de cada um no terminal.

Evidencia capturada:
- filesystem-rw apontando para ./src, ./specs, ./skills
- filesystem-docs apontando para ./docs/novatech, ./data/retrieval-corpus
- git, memory e everything configurados
- Estrutura JSON valida e coerente com o mapeamento da secao 1

### 3.2 Cenario B: agente le documento de docs/novatech (print: cenario-B-agente-lendo-doc-novatech.png)

Pergunta enviada ao agente:
"Liste os arquivos disponiveis em docs/novatech e me mostre o conteudo de POL-001-politica-devolucao.md"

Evidencia capturada no print:
- list_directory em docs/novatech retornou: FAQ-atendimento.md, POL-001-politica-devolucao.md, PROC-042-frete-especial-v1.md, PROC-042-v2-frete-especial-revisado.md, SLA-2024-tabela-sla-clientes.md
- read_file em POL-001-politica-devolucao.md retornou o conteudo completo (secoes 3.1 a 3.5)
- Conteudo coerente com os chunks de referencia do Anexo B (prazo 7 dias uteis, excecoes de carga perigosa, procedimento de chamado)
- Nenhuma tool de escrita invocada durante a operacao

### 3.3 Cenario C: agente recupera chunk do corpus (print: cenario-C-agente-recuperando-chunk-corpus.png)

Pergunta enviada ao agente:
"Qual o multiplicador regional vigente para a regiao Norte em fretes especiais?"

Evidencia capturada no print:
- Agente acessou data/retrieval-corpus via filesystem-docs
- Chunk recuperado: PROC-042v2-B — "Multiplicadores regionais atualizados (novembro/2023): Norte 1.8"
- Validacao contra gabarito do Anexo B: para "Frete para 600kg para Manaus?" o chunk esperado e PROC-042v2-B [OK]
- Observacao registrada: corpus contem tambem PROC-042-B (v1, Norte=1.6) — risco de contradicao confirmado, filtro de vigencia necessario no retrieval

### 3.4 Cenario D: agente le historico do repositorio via git (print: cenario-D-agente-historico-git.png)

Pergunta enviada ao agente:
"Mostre o historico de commits deste repositorio"

Evidencia capturada no print:
- git log retornou o commit inicial do starter repo (hash bbdd03a, autor trilha@db1.local, data 09/06/2026)
- git show --stat HEAD listou os 82 arquivos do scaffold inicial
- git diff --stat HEAD mostrou a modificacao do .mcp/mcp.json feita neste exercicio (+33 linhas)
- git status confirmou branch master, nenhuma operacao de escrita invocada pelo agente

### 3.5 Cenario E: arquivo mcp.json final no VS Code (print: cenario-E-copilot-scaffold-final.png)

Print mostra o arquivo .mcp/mcp.json aberto no VS Code com os 5 servers configurados.

O Copilot foi consultado com o prompt em portugues pedindo a configuracao de MCP servers com least privilege. A sugestao original do Copilot usava instancia unica de filesystem. O ajuste aplicado foi separar em filesystem-rw e filesystem-docs, conforme justificado na secao 1.2.

---

## 4. Riscos de seguranca identificados

### 4.1 Risco: filesystem-rw com escopo ampliavel inadvertidamente

Descricao: o server filesystem-rw recebe os paths como argumentos. Se um desenvolvedor do time alterar o mcp.json e adicionar "./" ou "../" por descuido, o agente passa a ter acesso de escrita a toda a arvore do repositorio, incluindo .env, infra/ e arquivos de configuracao com segredos.

Mitigacao aplicada:
- Paths explicitos e minimos no mcp.json (./src, ./specs, ./skills)
- mcp.json versionado no repositorio com revisao de PR obrigatoria para qualquer mudanca de escopo
- Adicionar ao AGENTS.md a regra: "Alteracoes em .mcp/mcp.json exigem aprovacao do Tech Lead antes do merge"

Mitigacao adicional recomendada:
- Adicionar .env ao .gitignore (ja feito no starter repo) e confirmar que nao esta nas pastas expostas ao server

### 4.2 Risco: filesystem-docs nao tem read-only real no nivel do server

Descricao: o server @modelcontextprotocol/server-filesystem nao tem flag --readonly nativa na versao atual. Isso significa que as tools write_file e create_directory ficam disponiveis mesmo no servidor filesystem-docs, que deveria ser so de leitura. Um agente mal instruido poderia sobrescrever documentos de negocio ou o corpus de chunks.

Mitigacao aplicada:
- Separacao em instancia propria deixa a intencao explicita na configuracao e facilita auditoria
- Permissoes de SO configuradas nas pastas de negocio: no Windows, propriedades da pasta ./docs/novatech e ./data/retrieval-corpus com permissao de escrita removida para o usuario que executa o agente; no Linux/Mac, chmod 555 nas pastas

Mitigacao adicional recomendada:
- Monitorar se o server filesystem-docs invoca write_file em algum momento no log de chamadas do MCP
- Quando disponivel, migrar para uma versao do server que suporte escopo read-only nativo (acompanhar repositorio oficial modelcontextprotocol/servers)

---

## 5. Conclusao

A configuracao ficou com 5 servers locais, todos sem dependencia de servico externo ou pago. O ponto mais importante foi a separacao da instancia de filesystem em duas: rw para codigo/specs/skills e docs para fontes de negocio. Sem essa separacao, o agente teria permissao de escrita em documentos que deveriam ser imutaveis do ponto de vista do desenvolvimento.

O risco residual mais relevante e o item 4.2: o server filesystem nao garante read-only no nivel do protocolo. A mitigacao via SO e necessaria e nao e automatica, entao deve ser documentada no runbook de onboarding para que novos desenvolvedores do time nao percam esse passo.

Para a proxima fase, quando o projeto mover para Azure AI Search e Confluence reais, a configuracao de MCP tera que ser revista. Os servers locais cobrem esta fase de estruturacao, mas nao substituem integracao real com Azure para producao.
