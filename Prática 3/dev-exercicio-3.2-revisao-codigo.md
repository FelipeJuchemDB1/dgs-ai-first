# Exercício 3.2 — Revisão Crítica de Código Gerado por IA
**Papel:** Desenvolvedor  
**Tópico:** Revisão Crítica de Outputs de IA

---

## 1. Minha Revisão (antes do Claude)

Fui olhar o handler e já anotei o que achei errado:

- `as any` direto no `request.json()` sem nenhuma validação — AGENTS.md fala que tem que usar Zod pra input
- `console.log` no meio do código — projeto usa pino, não console
- `require('@azure/cosmos')` dentro da função, não no topo — import dinâmico, AGENTS.md não permite isso
- o `attendantEmail` tá sendo logado no `JSON.stringify(feedback)` — isso é dado pessoal, não pode ir pra log de jeito nenhum, esse foi o mais grave pra mim

---

## 2. Revisão do Claude

Após submeter o código para o Claude com o contexto do AGENTS.md, ele identificou:

**Problemas encontrados pelo Claude:**

1. **Ausência de validação de schema (Zod)** — `request.json() as any` bypassa o sistema de tipos. Claude recomendou criar um `z.object()` com os campos esperados e usar `safeParse` para tratar erros de validação graciosamente antes de qualquer outra operação.

2. **Uso de `console.log`** — identificou como violação do AGENTS.md e sugeriu instanciar o logger pino fora da função (no escopo do módulo) para reutilização entre invocações.

3. **Import dinâmico (`require`)** — classificou como violação de imports estáticos e destacou o impacto em cold start em ambientes serverless, além do risco de o TypeScript não conseguir inferir tipos corretamente com require dinâmico.

4. **Log de `attendantEmail`** — identificou como exposição de dado pessoal e sugeriu fazer destructuring para separar os campos sensíveis antes de logar, ou usar uma allowlist explícita dos campos que podem aparecer em log.

5. **Ponto adicional levantado pelo Claude:** o `CosmosClient` e a instância do container também deveriam ser criados fora da função para aproveitar o warm start do Azure Functions — instanciar conexões dentro do handler a cada invocação é um antipadrão de performance em serverless.

---

## 3. Comparação: Minha Revisão vs Claude

| Problema | Encontrei? | Claude encontrou? | Observação |
|---|---|---|---|
| `as any` / falta de Zod | ✅ | ✅ | Mesma classificação |
| `console.log` em vez de pino | ✅ | ✅ | Mesma classificação |
| `require` dinâmico | ✅ | ✅ | Claude adicionou contexto de TypeScript types |
| Log de `attendantEmail` | ✅ | ✅ | Ambos classificaram como segurança/LGPD |
| CosmosClient fora do handler | ❌ | ✅ | Não havia pensado nisso — faz sentido pra warm start |

Peguei os 4 principais antes do Claude. O único que ele trouxe a mais foi o CosmosClient fora do handler — faz sentido pra warm start, não tinha pensado nisso. No geral a lista foi a mesma, ele só foi mais detalhado nas justificativas.

---

## 4. Código Reescrito (seguindo AGENTS.md)

```typescript
// /src/functions/feedback/handler.ts
import { app, HttpRequest, HttpResponseInit } from '@azure/functions';
import { CosmosClient } from '@azure/cosmos';
import { z } from 'zod';
import pino from 'pino';

const logger = pino();

const FeedbackSchema = z.object({
  queryId: z.string().min(1),
  rating: z.number().int().min(1).max(5),
  comment: z.string().optional(),
  attendantEmail: z.string().email(),
});

const cosmosClient = new CosmosClient(process.env.COSMOS_CONNECTION_STRING!);
const container = cosmosClient.database('novatech').container('feedbacks');

export async function feedbackHandler(
  request: HttpRequest
): Promise<HttpResponseInit> {
  const raw = await request.json();
  const parsed = FeedbackSchema.safeParse(raw);

  if (!parsed.success) {
    logger.warn({ issues: parsed.error.issues }, 'Feedback com schema inválido rejeitado');
    return { status: 400, body: 'Dados de feedback inválidos' };
  }

  const { attendantEmail, ...safeFields } = parsed.data;

  logger.info(
    { queryId: safeFields.queryId, rating: safeFields.rating },
    'Feedback recebido'
  );

  await container.items.create({
    ...parsed.data,
    timestamp: new Date().toISOString(),
  });

  return { status: 200, body: 'OK' };
}

app.http('feedback', {
  methods: ['POST'],
  handler: feedbackHandler,
});
```

**O que mudou e por quê:**

- `as any` removido → schema Zod com `safeParse`, retorna 400 se inválido
- `console.log` removido → `pino` instanciado no escopo do módulo
- `require` dinâmico removido → import estático no topo
- `attendantEmail` não aparece mais no log → destructuring separa dado sensível antes de logar
- `CosmosClient` e `container` movidos para escopo do módulo → evita re-instanciar conexão a cada invocação
