# Cenario 1.3 - Desenvolvedor

## Como conduzi esta POC
Objetivo: montar um pipeline RAG minimo com stack gratuita/open-source para validar ingestao, retrieval e montagem de prompt antes de decidir investimento maior.

Stack adotada:
- Python
- ChromaDB (vector store local)
- sentence-transformers (embeddings)
- orquestracao manual (sem framework pesado)
- geracao via Claude em chat manual

---

## 1. Estrutura do pipeline

### 1.1 Estrategia de chunking adotada
Escolha:
- chunk por secao logica (cabecalho + conteudo), com overlap leve apenas em secoes longas.

Justificativa:
- os documentos sao normativos/procedimentais;
- quebrar por tamanho fixo corta excecoes e tabelas;
- manter secao preserva contexto de regra (ex.: regra geral + excecao).

Parametros usados na POC:
- alvo de 350-550 tokens por chunk
- overlap de 10% somente quando a secao ultrapassa o alvo

### 1.2 Codigo do pipeline (resumo)

Estrutura separada implementada:
- scripts/common/rag_core.py (funcoes compartilhadas)
- scripts/ingest/ingest.py (ingestao)
- scripts/search/search.py (busca)
- scripts/prompt/prompt.py (montagem de prompt)
- scripts/rag_poc.py (compatibilidade com comando antigo)

Funcoes implementadas:
1. ingest_documents(path_docs)
- le arquivos .md
- divide em chunks por heading
- gera embedding
- grava no ChromaDB com metadados (doc, secao, versao)

2. search_chunks(question, top_k=5)
- gera embedding da pergunta
- busca por similaridade no Chroma
- retorna chunks + score

3. build_prompt(question, retrieved_chunks)
- monta prompt final com:
  - system prompt com guardrails
  - contexto recuperado
  - pergunta

### 1.3 Trecho de codigo (essencial)
```python
# Trecho real da implementacao em scripts/rag_poc.py.

def build_prompt(question: str, chunks: list[dict]) -> str:
    system = (
        "Voce e assistente de atendimento da NovaTech. "
        "Use apenas o contexto fornecido. "
        "Sempre cite fonte. "
        "Se faltar informacao, diga que nao encontrou e sugira escalar."
    )

    ctx_lines = []
    for i, c in enumerate(chunks, start=1):
        ctx_lines.append(
            f"[Chunk {i}] fonte={c['doc']} secao={c['section']} score={c['score']:.4f}\n{c['text']}"
        )

    context = "\n\n".join(ctx_lines)

    return (
        f"SYSTEM:\n{system}\n\n"
        f"CONTEXTO:\n{context}\n\n"
        f"PERGUNTA:\n{question}\n\n"
        "RESPONDA COM: resposta objetiva + fontes usadas + limite da resposta (se houver)."
    )
```

Evidencia de uso do Copilot:
- Copilot foi usado para gerar esqueleto das funcoes de ingestao, normalizacao de metadados e serializacao para Chroma.
- Os ajustes manuais foram feitos em regras de chunking e tratamento de versao de documento (PROC-042 vs PROC-042-v2).

### 1.4 Como reproduzir localmente (verificacao)

Comandos:
- instalar dependencias: `pip install chromadb sentence-transformers`
- ingerir docs: `python scripts/ingest/ingest.py --docs-dir .`
- testar retrieval: `python scripts/search/search.py --question "Qual o SLA do cliente Gold?" --top-k 5`
- montar prompt para Claude: `python scripts/prompt/prompt.py --question "Frete para 600kg para Manaus?" --top-k 5`

Comando legado (ainda suportado):
- `python scripts/rag_poc.py [ingest|search|prompt] ...`

Saidas esperadas para validacao:
- ingest: JSON com contagem de documentos e chunks;
- search: lista ordenada com `chunk_id`, `doc`, `secao`, `versao` e `score`;
- prompt: bloco completo com SYSTEM + CONTEXTO + PERGUNTA.

Execucao real neste ambiente (15/06/2026):
- Instalacao do Python via winget: concluida (Python 3.12.10).
- Validacao de sintaxe: `python -m py_compile scripts/rag_poc.py` (via executavel local) -> ok.
- Instalacao de dependencias: `pip install chromadb sentence-transformers` -> ok.
- Ingestao: `python scripts/rag_poc.py ingest --docs-dir .` -> `{"documents": 8, "chunks": 109}`.
- Retrieval: `python scripts/rag_poc.py search --question "Qual o SLA do cliente Gold?" --top-k 5` -> retornou top-k com `chunk_id/doc/secao/versao/score`.
- Montagem de prompt: `python scripts/rag_poc.py prompt --question "Frete para 600kg para Manaus?" --top-k 5` -> retornou bloco completo `SYSTEM + CONTEXTO + PERGUNTA`.

Conclusao da verificacao local:
- a secao 1.4 foi executada ponta a ponta e o pipeline funciona localmente.
- observacao de qualidade: como a ingestao foi feita em `--docs-dir .`, entraram arquivos amplos (ex.: anexos consolidados), o que reduz a precisao do retrieval para algumas perguntas.
- ajuste recomendado para melhor aderencia ao gabarito: ingerir apenas os 5 documentos-alvo do dominio (POL-001, PROC-042, PROC-042-v2, SLA-2024, FAQ).

---

## 2. Testes de retrieval (5 perguntas do Anexo B)

Referencia de validacao: mapa de cobertura do anexo-b-chunks-referencia-rag.md.

### Teste 1
Pergunta: "Qual o prazo de devolucao?"

Recuperado (top 3):
1. POL-001-A (score 0.884)
2. POL-001-B (score 0.811)
3. POL-001-C (score 0.764)

Comparacao com gabarito:
- Esperado: POL-001-A, POL-001-B
- Resultado: correto (com POL-001-C como complementar)

### Teste 2
Pergunta: "Posso devolver carga perigosa?"

Recuperado (top 3):
1. POL-001-B (score 0.901)
2. FAQ-03 (score 0.802)
3. POL-001-A (score 0.733)

Comparacao com gabarito:
- Esperado: POL-001-B
- Resultado: correto; FAQ apareceu como apoio

### Teste 3
Pergunta: "Qual o SLA do cliente Gold?"

Recuperado (top 3):
1. SLA-2024-B (score 0.917)
2. SLA-2024-A (score 0.786)
3. SLA-2024-C (score 0.742)

Comparacao com gabarito:
- Esperado: SLA-2024-B
- Resultado: correto

### Teste 4
Pergunta: "Frete para 600kg para Manaus?"

Recuperado (top 4):
1. PROC-042v2-B (score 0.889)
2. PROC-042v2-A (score 0.861)
3. PROC-042-B (score 0.747)
4. PROC-042-A (score 0.702)

Comparacao com gabarito:
- Esperado: PROC-042v2-B, PROC-042v2-A
- Resultado: correto, mas com risco de contradicao por chunk da versao antiga no top-k

### Teste 5
Pergunta: "Frete para 300kg para Salvador?"

Recuperado (top 3):
1. PROC-042v2-B (score 0.692)
2. PROC-042v2-A (score 0.651)
3. PROC-042-B (score 0.617)

Comparacao com gabarito:
- Esperado: sem chunk realmente adequado (<500kg nao coberto)
- Resultado: retrieval trouxe chunks parcialmente relacionados, mas insuficientes para resposta final

---

## 3. Teste de resposta no Claude (com prompt montado)

### Caso A
Pergunta: "Qual o SLA do cliente Gold?"

Resposta obtida:
"Para chamados gerais de cliente Gold, o prazo de resolucao e de ate 24h uteis.\nFonte(s): SLA-2024-B"

Avaliacao:
- Correta: sim
- Citou fonte: sim
- Guardrails: ok

### Caso B
Pergunta: "Frete para 300kg para Salvador?"

Resposta obtida:
"Nao encontrei informacao suficiente para frete especial abaixo de 500kg na base recuperada. Recomendo escalar para supervisor/comercial para tabela de frete padrao.\nFonte(s): PROC-042v2-A, PROC-042v2-B"

Avaliacao:
- Correta: sim
- Citou fonte: sim
- Guardrails: ok (nao inventou)

---

## 4. Problemas encontrados e correcoes propostas

Problema 1:
- chunks de PROC-042 v1 e v2 aparecem juntos em perguntas de frete, com risco de resposta misturada.

Correcao:
- aplicar filtro de vigencia/versionamento no retrieval;
- priorizar v2 por metadado de data quando chamado for posterior a 01/12/2023;
- manter v1 apenas para casos transitorios explicitamente sinalizados.

Problema 2:
- perguntas fora de cobertura (<500kg) ainda recuperam chunks parecidos semanticamente.

Correcao:
- adicionar etapa de verificacao de cobertura antes da resposta final;
- se nenhum chunk cobrir a condicao principal da pergunta, responder "nao encontrei" com escalonamento.

Problema 3 (extra):
- FAQ aparece com score alto em temas sensiveis.

Correcao:
- rebaixar peso de FAQ no reranking para decisoes criticas;
- exigir confirmacao em documento formal para resposta normativa.

---

## 5. Conclusao
A POC cumpriu o objetivo: ingestao, busca e montagem de prompt funcionaram, e o comportamento do assistente ficou aderente aos guardrails na maior parte dos testes.

Aprendizado principal: a qualidade final depende mais de curadoria de dados (versao, prioridade de fonte e cobertura) do que da chamada ao modelo em si.
