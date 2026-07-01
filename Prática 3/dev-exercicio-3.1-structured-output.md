# Exercício 3.1 — Structured Output e Verificações Determinísticas
**Papel:** Desenvolvedor  
**Tópico:** Harness Engineering

---

## 1. Schema Zod do Structured Output

Defini os três campos que o exercício pede. Coloquei `confidence_score` como `number` entre 0 e 1 pra forçar valor numérico — se o modelo mandar "alta" em texto, o Zod rejeita na hora.

```typescript
// /src/services/response-validator.ts
import { z } from 'zod';

export const AssistantResponseSchema = z.object({
  answer: z.string().min(1),
  source_document: z.string().min(1),
  confidence_score: z.number().min(0).max(1),
});

export type AssistantResponse = z.infer<typeof AssistantResponseSchema>;
```

---

## 2. Implementação do `response-validator.ts`

```typescript
// /src/services/response-validator.ts
import { z } from 'zod';
import pino from 'pino';

const logger = pino();

export const AssistantResponseSchema = z.object({
  answer: z.string().min(1),
  source_document: z.string().min(1),
  confidence_score: z.number().min(0).max(1),
});

export type AssistantResponse = z.infer<typeof AssistantResponseSchema>;

const SAFE_DEFAULT: AssistantResponse = {
  answer:
    'Não foi possível processar a resposta. Por favor, reformule sua pergunta ou contate o suporte.',
  source_document: 'N/A',
  confidence_score: 0,
};

const DANGEROUS_CARGO_PATTERN =
  /carga\s+perigosa/i;

const RETURN_AFFIRMATION_PATTERN =
  /\b(pode(?:m)?|é\s+possível|possível|permitid[ao]|autorizado|sim[,.]?\s*(pode|é))\b/i;

export function validateResponse(raw: unknown): AssistantResponse {
  // Validação de schema (structured output)
  const parsed = AssistantResponseSchema.safeParse(raw);

  if (!parsed.success) {
    logger.warn(
      { issues: parsed.error.issues },
      'Guardrail #1: resposta rejeitada — source_document ausente ou schema inválido'
    );
    return SAFE_DEFAULT;
  }

  const response = parsed.data;

  // Guardrail #2: carga perigosa + afirmação de devolução
  const mentionsDangerousCargo = DANGEROUS_CARGO_PATTERN.test(response.answer);
  const affirmsReturn = RETURN_AFFIRMATION_PATTERN.test(response.answer);

  if (mentionsDangerousCargo && affirmsReturn) {
    logger.error(
      { answer_snippet: response.answer.slice(0, 120) },
      'Guardrail #2: resposta bloqueada — afirma devolução de carga perigosa'
    );
    return SAFE_DEFAULT;
  }

  return response;
}
```

Separei em dois patterns porque o guardrail precisa da combinação — mencionar carga perigosa sozinho não é problema, só bloqueia se vier junto com afirmação de devolução. Testei os casos do cenário e funcionou.

---

## 3. Code Review com Claude

Depois de gerar o código com o Copilot e fazer meus ajustes, pedi uma revisão ao Claude.

### O que eu vi antes de mostrar pro Claude:

- o regex de afirmação tá curto — "é viável", "está liberado" não seriam capturados
- não usei `.strict()` no schema, campos extras passariam sem nenhum aviso

### O que o Claude identificou:

**Confirmou os dois problemas que levantei:**

- **Regex incompleto:** sugeriu ampliar o pattern ou usar uma lista de termos de afirmação mais abrangente. Proposta: incluir termos como `viável`, `liberado`, `autorizado`, `pode ser feito`.
- **Schema sem `.strict()`:** campos extras passam silenciosamente. Recomendou usar `.strict()` para rejeitar qualquer campo não declarado, ou pelo menos logar um aviso se campos inesperados chegarem.

**Ponto adicional levantado pelo Claude:**

- O `SAFE_DEFAULT` com `source_document: 'N/A'` pode causar problemas downstream se outro componente do pipeline tentar buscar esse documento. Sugeriu usar uma string claramente inválida como `'__blocked__'` ou um campo separado `blocked: true` para distinguir "resposta bloqueada" de "resposta sem fonte".

### Comparação:

| Problema | Eu identifiquei? | Claude identificou? |
|---|---|---|
| Regex de afirmação incompleto | ✅ | ✅ |
| Schema sem `.strict()` | ✅ | ✅ |
| `source_document: 'N/A'` ambíguo no downstream | ❌ | ✅ |

### Correções aplicadas:

```typescript
// Regex expandido
const RETURN_AFFIRMATION_PATTERN =
  /\b(pode(?:m)?|é\s+possível|possível|permitid[ao]|autorizado|sim[,.]?\s*(pode|é)|viável|liberado|pode\s+ser\s+feito)\b/i;

// Schema com .strict()
export const AssistantResponseSchema = z
  .object({
    answer: z.string().min(1),
    source_document: z.string().min(1),
    confidence_score: z.number().min(0).max(1),
  })
  .strict();

// Safe default com marcador explícito
const SAFE_DEFAULT: AssistantResponse = {
  answer:
    'Não foi possível processar a resposta. Por favor, reformule sua pergunta ou contate o suporte.',
  source_document: '__blocked__',
  confidence_score: 0,
};
```

---

## 4. Probabilístico vs Determinístico

O prompt pede pro modelo incluir `source_document` e não afirmar devolução de carga perigosa — mas isso não é garantia, o modelo pode ignorar. O código é diferente: se faltou o campo, rejeita. Se detectou a combinação bloqueada, rejeita. Sempre, independente do modelo. O prompt reduz os erros, o validator garante que os que escapam não chegam ao usuário.
