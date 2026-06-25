# Exercicio 2.2 - Desenvolvedor

## Como conduzi este exercicio

O exercicio pede converter o plan.md do query endpoint em tasks atomicas, implementar a primeira task com Copilot e revisar criticamente o codigo gerado.

Ponto de partida: o plan.md estava no repositorio (specs/query-endpoint/plan.md) e definia 5 etapas de implementacao com decisoes tecnicas (TypeScript, Zod, Azure Functions v4, pino, retry com backoff). Usei o Claude para decompor em tasks com criterios de aceite verificaveis. O Copilot gerou o codigo da primeira task — handler.ts e validator.ts em /src/functions/query/. Depois fiz a revisao critica identificando os dois problemas mais relevantes.

Conexao com o cenario 1: no exercicio 1.3 construi o prototipo de RAG com Python, ChromaDB e sentence-transformers. O prototipo validou a abordagem de top-5 chunks e identificou o problema de documentos contraditórios (PROC-042 v1 vs v2 aparecendo juntos no top-k). Esses dois resultados viraram respectivamente ADR-0002 (context budget) e ADR-0003 (filtro de vigencia). O codigo desta task e a versao TypeScript/Azure do que o prototipo validou: a validacao de input era manual em Python, agora e Zod; o retrieval era ChromaDB, agora sera Azure AI Search; os embeddings eram sentence-transformers, agora serao Azure OpenAI text-embedding-ada-002.

Ferramentas usadas: Claude (chat) para gerar o tasks.md; GitHub Copilot para gerar handler.ts e validator.ts.

---

## Prompt que usei no Claude para gerar o tasks.md

Contexto: projeto novatech-assistant, TypeScript, Azure Functions v4. Tenho o plan.md do query endpoint abaixo.

Converta este plan em tasks.md com tasks atomicas. Cada task deve ter: ID (TASK-NNN), descricao, criterios de aceite verificaveis (nao vagos como "funcionar corretamente" — devem ser especificos o suficiente para um teste automatizado), dependencias entre tasks e estimativa (P/M/G).

A primeira task deve cobrir apenas o HTTP trigger e a validacao de input com Zod — sem logica de negocio. As demais devem cobrir embedding, busca, montagem de prompt, completion e retry.

[colei o plan.md do exercicio]

---

## 1. Tasks geradas (specs/query-endpoint/tasks.md)

O Claude gerou 6 tasks. Ajustei dois criterios de aceite que estavam vagos:

Ajuste 1: na TASK-003, o Claude escreveu "retorna os chunks mais relevantes". Especifiquei para "retorna array de ate 5 objetos {text, source_document, section, score} ordenados por score decrescente". Criterio vago nao e testavel.

Ajuste 2: na TASK-005, o Claude nao incluiu o campo confidence_level na resposta. Adicionei com a logica de derivacao a partir do score do chunk de maior relevancia (>= 0.85 = high, >= 0.70 = medium, < 0.70 = low). Esse campo era necessario para o VC-03 dos requirements (resposta com confianca baixa inclui aviso).

Tasks resultantes:

TASK-001 — HTTP trigger + validacao de input com Zod (P, sem dependencias)
TASK-002 — Geracao de embedding via Azure OpenAI (P, depende de TASK-001)
TASK-003 — Busca de chunks no Azure AI Search (M, depende de TASK-002)
TASK-004 — Montagem do prompt com context budget (P, depende de TASK-003)
TASK-005 — Chamada de completion e formatacao da resposta (M, depende de TASK-004)
TASK-006 — Retry com exponential backoff para chamadas Azure (P, depende de TASK-002 e TASK-005)

Arquivo completo: specs/query-endpoint/tasks.md

---

## Prompt que usei no Copilot para gerar a TASK-001

Prompt enviado no Copilot Chat com o arquivo handler.ts aberto:

Implemente a TASK-001 do query endpoint de um projeto Azure Functions v4 TypeScript.

Requisitos:
- HTTP trigger POST na rota /api/query
- Validacao de input com Zod: campo question (string, obrigatorio, nao vazio), conversationId (UUID, opcional), maxChunks (inteiro 1-10, opcional, default 5)
- Retornar 400 com campo error para input invalido
- Retornar 400 com mensagem "Invalid JSON body" para body nao-JSON
- Sem logica de negocio nesta task — apenas rota e validacao
- Usar pino para logging (nao console.log)
- Seguir Azure Functions v4 com ESM (type: module no package.json)

O validator.ts deve ser separado com o schema Zod e uma funcao formatZodError que formata os issues em string legivel.

Ver print: cenario-F-copilot-gerando-handler.png

---

## 2. Codigo gerado pelo Copilot (TASK-001)

Arquivos implementados pelo Copilot:
- src/functions/query/validator.ts — schema Zod e formatZodError
- src/functions/query/handler.ts — HTTP trigger com validacao

### 2.1 validator.ts

```typescript
import { z } from "zod";

export const QueryRequestSchema = z.object({
  question: z.string().min(1, "question cannot be empty"),
  conversationId: z.string().uuid().optional(),
  maxChunks: z.number().int().min(1).max(10).optional().default(5),
});

export type QueryRequest = z.infer<typeof QueryRequestSchema>;

export function formatZodError(error: z.ZodError): string {
  return error.issues
    .map((issue) => `${issue.path.join(".") || "body"}: ${issue.message}`)
    .join("; ");
}
```

### 2.2 handler.ts (saida do Copilot, antes dos ajustes)

```typescript
import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { QueryRequestSchema } from "./validator.js";

export async function queryHandler(
  request: HttpRequest,
  context: InvocationContext
): Promise<HttpResponseInit> {
  context.log("Processing query request");

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return {
      status: 400,
      jsonBody: { error: "Invalid JSON body" },
    };
  }

  const result = QueryRequestSchema.safeParse(body);
  if (!result.success) {
    return {
      status: 400,
      jsonBody: { error: result.error.message },
    };
  }

  const { question, conversationId, maxChunks } = result.data;

  try {
    context.log(`Received question: ${question}`);

    // TODO: TASK-002, TASK-003, TASK-004, TASK-005
    return {
      status: 200,
      jsonBody: {
        answer: "Not implemented",
        source_document: null,
        conversationId: conversationId ?? null,
      },
    };
  } catch (error: unknown) {
    context.log("Unhandled error in queryHandler", error);
    return {
      status: 500,
      jsonBody: { error: (error as Error).message },
    };
  }
}

app.http("query", {
  methods: ["POST"],
  authLevel: "function",
  route: "query",
  handler: queryHandler,
});
```

O codigo acima e a saida original do Copilot — mantida no documento para evidenciar os problemas identificados na revisao critica (secao 3). Apos a revisao, o arquivo src/functions/query/handler.ts foi corrigido com os dois ajustes descritos abaixo. Path correto conforme Anexo C.

---

## 3. Revisao critica do codigo gerado

### Problema 1: result.error.message retorna JSON bruto do Zod

Linha afetada: `jsonBody: { error: result.error.message }`

O problema: ZodError.message nao e uma string de texto livre. E uma serializacao JSON do array de issues internos do Zod, com campos como "code", "minimum", "type", "inclusive", "exact". Para input {"question": ""}, a resposta seria algo como:

```
{"error": "[\n  {\n    \"code\": \"too_small\",\n    \"minimum\": 1,\n    \"type\": \"string\"..."}
```

Isso e ilegivel para o chamador da API e expoe detalhes do schema de validacao que nao deveriam estar na interface publica.

Correcao necessaria: usar a funcao formatZodError que o proprio Copilot gerou no validator.ts, que formata como "question: question cannot be empty". O Copilot gerou a solucao mas nao a usou no handler.

Linha corrigida:
```typescript
jsonBody: { error: formatZodError(result.error) }
```

### Problema 2: context.log em vez do logger pino do projeto

Linhas afetadas: todas as chamadas a context.log no handler.

O problema: o AGENTS.md do projeto proibe console.log e define que o logging deve ser feito via pino (src/shared/logger.ts). context.log e o equivalente de console.log no ambiente do Azure Functions — funciona, mas bypassa o logger estruturado do projeto.

Consequencias praticas:
- Os logs nao tem os campos padronizados do pino (correlationId, requestId, timestamp ISO)
- Nao e possivel filtrar ou agregar logs por correlationId em producao
- A pergunta do usuario aparece em texto livre no log em vez de campo estruturado, dificultando LGPD/auditoria

O Copilot ignorou a instrucao do prompt de usar pino. Provavelmente porque o arquivo src/shared/logger.ts estava vazio no momento da geracao e o Copilot nao tinha contexto do que o logger exporta.

Correcao necessaria: importar o logger do projeto e substituir todas as chamadas:
```typescript
import { logger } from "../../shared/logger.js";
// substituir context.log("...") por logger.info({ ... }, "mensagem")
```

### Observacao adicional (nao bloqueia code review, mas deve ser corrigido antes de producao)

No catch de 500: `jsonBody: { error: (error as Error).message }` expoe a mensagem interna do erro ao chamador. Em producao, uma excecao pode conter string de conexao, nome de tabela, ou stack interno. O correto e logar internamente e retornar mensagem generica:

```typescript
logger.error({ err: error }, "Unhandled error in queryHandler");
return { status: 500, jsonBody: { error: "Internal server error" } };
```

---

## 4. Versao corrigida aplicada

Apos a revisao critica, o handler.ts foi atualizado com os dois ajustes:

Problema 1 corrigido: substituido result.error.message por formatZodError(result.error)
```typescript
jsonBody: { error: formatZodError(result.error) }
```

Problema 2 corrigido: substituido context.log por logger.info do projeto
```typescript
import { logger } from "../../shared/logger.js";
logger.info("Processing query request");
logger.info({ question, conversationId, maxChunks }, "Received query");
```

O try/catch de 500 foi removido na versao final porque as tasks seguintes (TASK-002 a TASK-005) terao seus proprios blocos de tratamento de erro com tipos especificos. Um catch generico aqui mascararia erros que precisam de tratamento diferenciado.

O arquivo src/functions/query/handler.ts no repositorio e a versao corrigida. O codigo original do Copilot esta preservado na secao 2.2 deste documento para evidenciar a revisao critica.

---

## 5. Conclusao

O tasks.md ficou com 6 tasks com criterios de aceite verificaveis. O codigo da TASK-001 esta no path correto (/src/functions/query/) e segue a estrutura do Azure Functions v4 com Zod. Os dois problemas identificados na revisao critica eram reais: o primeiro comprometia a usabilidade da API (mensagem de erro ilegivel), o segundo violava o padrao de logging do projeto. Ambos foram corrigidos na versao final do arquivo.
