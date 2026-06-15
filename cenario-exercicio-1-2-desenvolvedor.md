# Cenario 1.2 - Desenvolvedor

## Como conduzi esta prototipacao
Neste cenario, tratei o prompt como artefato de engenharia: escrevi versao inicial, testei com perguntas reais e refinei com base nas falhas.

Objetivo pratico: garantir que o assistente responda com fonte, sem inventar dados, e saiba recusar quando faltar informacao.

---

## 1. System prompt v1

### 1.1 Prompt completo (v1)
Voce e um assistente de atendimento da NovaTech.

Identidade:
- Sua funcao e responder duvidas operacionais com base na documentacao oficial recuperada (chunks).
- Sua resposta deve ser em portugues formal e acessivel.

Regras obrigatorias:
1. Sempre citar a fonte do trecho usado (documento e secao/chunk).
2. Nunca inventar prazos, valores, multiplicadores ou regras.
3. Se nao houver informacao suficiente no contexto, diga explicitamente que nao encontrou e sugira escalar para o supervisor.
4. Em caso de conflito entre fontes, priorize documento mais recente com indicacao de vigencia.

Prioridade de instrucoes:
1. Regras deste system prompt.
2. Documentos formais (POL, PROC, SLA).
3. FAQ (apenas apoio, nunca para contradizer documento formal).
4. Historico da conversa.

Formato de resposta:
- Resposta objetiva em 2-5 linhas.
- Bloco "Fonte(s)" ao final.
- Se faltar dado: bloco "Limite da resposta".

Instrucoes de uso dos chunks:
- Use apenas os chunks fornecidos na consulta.
- Nao inferir dado numerico ausente.
- Se a pergunta exigir calculo, explicitar quais entradas faltam.

### 1.2 Estrutura de contexto (estatico x dinamico)

Partes estaticas (toda query):
- System prompt (identidade, regras, formato, prioridade): ~550-700 tokens
- Guardrails do produto: ~120-180 tokens

Partes dinamicas (mudam por query):
- Pergunta do atendente: ~20-60 tokens
- Chunks recuperados (3-8): ~400-2.500 tokens
- Metadados de fonte (id, documento, secao): ~80-250 tokens
- Historico curto (0-3 turnos): ~0-900 tokens

Resumo de composicao:
- Base estatica aproximada: 700-900 tokens
- Base dinamica aproximada: 500-3.700 tokens
- Total tipico por query: 1.200-4.600 tokens

---

## 2. Rodada de testes (v1)

Contexto usado no teste:
- Chunk A (POL-001 secao 3.2 + procedimento resumido)
- Chunk B (SLA-2024 Gold/Silver/Standard)
- Chunk C (PROC-042-v2 multiplicadores regionais para >500kg)

Pergunta 1:
"Qual o prazo de devolucao para carga perigosa?"

Resposta obtida (v1):
"Carga perigosa nao e elegivel para devolucao pelo processo padrao. O atendimento deve orientar tratamento individual com Gestao de Riscos (ramal 4500).\nFonte: POL-001 secao 3.2"

Avaliacao:
- Correta: sim
- Citou fonte: sim
- Guardrails: ok

Pergunta 2:
"Meu cliente e Gold, qual o SLA de resolucao?"

Resposta obtida (v1):
"Para cliente Gold, o tempo de resolucao de chamados gerais e de ate 24h uteis.\nFonte: SLA-2024 tabela de SLA"

Avaliacao:
- Correta: sim
- Citou fonte: sim
- Guardrails: ok

Pergunta 3:
"Quanto custa o frete para 600kg para Manaus?"

Resposta obtida (v1):
"Para 600kg (faixa 500-1000kg), aplicar multiplicador 1.8 (Norte). O valor final estimado e valor base x 1.8."

Avaliacao:
- Correta: parcial
- Problema: faltou explicitar que nao e possivel calcular custo final sem valor base
- Citou fonte: nao (falha)
- Guardrails: falhou no item de resposta incompleta

---

## 3. Ajustes no prompt (iteracao para v2)

Mudancas aplicadas:
1. Reforcei regra de "incompletude": sem valor base, sem custo final.
2. Tornei obrigatorio citar fonte em qualquer resposta, inclusive negativa/parcial.
3. Adicionei template de saida com campo fixo "Dados faltantes".

### 3.1 Trecho revisado do system prompt (v2)
Regra adicional:
- Quando a pergunta envolver calculo e faltar variavel de entrada, voce deve:
  a) declarar que nao e possivel fechar o valor;
  b) listar os dados faltantes;
  c) informar apenas o que e comprovavel nos chunks;
  d) citar a fonte mesmo assim.

Formato obrigatorio:
- Resposta
- Fonte(s)
- Dados faltantes (quando aplicavel)

---

## 4. Rodada de testes (v2)

Pergunta 1:
"Qual o prazo de devolucao para carga perigosa?"

Resposta obtida (v2):
"Carga perigosa (classes 1 a 6 ANTT) nao pode seguir devolucao pelo processo padrao. O caso deve ser tratado individualmente pela Gestao de Riscos (ramal 4500).\nFonte(s): POL-001, secao 3.2"

Validacao:
- Correta: sim
- Fonte: sim
- Guardrails: ok

Pergunta 2:
"Meu cliente e Gold, qual o SLA de resolucao?"

Resposta obtida (v2):
"Para chamados gerais de cliente Gold, a resolucao e de ate 24h uteis.\nFonte(s): SLA-2024, tabela de SLAs"

Validacao:
- Correta: sim
- Fonte: sim
- Guardrails: ok

Pergunta 3:
"Quanto custa o frete para 600kg para Manaus?"

Resposta obtida (v2):
"Nao encontrei dados suficientes para calcular o custo final do frete. Com base nos chunks, para Manaus (regiao Norte) o multiplicador regional e 1.8 e a formula exige valor base x multiplicador regional.\nFonte(s): PROC-042-v2, secao 2 e 2.1\nDados faltantes: valor base da tarifa da rota e fator de peso detalhado da faixa"

Validacao:
- Correta: sim
- Fonte: sim
- Guardrails: ok (nao inventou)

Observacao de verificacao:
- neste teste, o chunk C fornecido no enunciado nao traz o detalhamento do fator de peso;
- por isso, a resposta final ficou restrita ao que era comprovavel no contexto.

---

## 5. Conclusao
A versao v2 ficou mais robusta que a v1 em dois pontos: recusa correta quando falta dado e citacao de fonte consistente.

Para producao, eu manteria este prompt versionado junto com testes de regressao de prompt (as tres perguntas acima + casos sem cobertura), porque a qualidade cai rapido quando o contexto dinamico muda.
