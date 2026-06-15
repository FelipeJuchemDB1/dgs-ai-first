# Cenario 1.1 - Desenvolvedor

## Como conduzi esta analise
Neste exercicio, tratei a avaliacao como uma leitura tecnica de viabilidade para POC, nao como desenho final de producao. Usei o Claude para rascunhar a primeira versao, depois pedi revisao critica para expor pontos fracos e ajustar as premissas.

Objetivo pratico: responder se o assistente e viavel em 3 meses e quais riscos podem comprometer qualidade de resposta.

---

## Prompt principal que usei no Claude
Atue como engenheiro de IA com experiencia em RAG e engenharia de contexto. Gere uma analise tecnica cobrindo obrigatoriamente:

1. desafios, impacto e estrategia para cada fonte (PDF com tabela, PDF escaneado, Confluence com links/macros e planilhas com formulas);
2. estimativa de tokens com calculo explicito;
3. orcamento de contexto em janela de 128K (com 2K para system/instrucoes e chunks de 500 tokens);
4. estrategia de chunking por tipo de documento, considerando lost in the middle.

Peca sempre em formato objetivo, com numero e justificativa.

---

## 1. Analise tecnica

### 1.1 Fontes de dados: desafio, impacto e tratamento

| Fonte | O problema que aparece na pratica | Impacto no RAG | Tratamento recomendado |
|---|---|---|---|
| PDFs com tabelas complexas | parser quebra relacao cabecalho/celula | resposta com valor certo no contexto errado | extracao estrutural + serializacao por linha com cabecalho |
| PDFs escaneados | OCR erra siglas e numeros | recall cai sem ficar obvio | OCR robusto, glossario de dominio, score de confianca |
| Confluence com links/macros | pagina depende de conteudo externo e macro | chunk volta no top-k, mas sem informacao suficiente | resolver links com limite e normalizar macros |
| Planilhas com formulas | formula sem semantica de negocio | regra pode ser interpretada errado | indexar valor materializado com contexto (aba, coluna, linha) |

Observacao de implementacao:
- Em tabela de frete e SLA, chunk por estrutura funciona melhor que chunk fixo por tamanho.
- Em wiki, pagina-indice deve entrar como metadado, nao como conteudo principal.

### 1.2 Estimativa da base em tokens

Premissas usadas (com incerteza):
- 800 PDFs x 10 paginas/doc x 250 palavras/pagina
- 400 paginas wiki x 1.500 palavras/pagina
- 50 planilhas x 3 abas x 200 celulas; 70% realmente indexavel; 10 palavras/celula
- conversao: 1 token ~= 0,75 palavras

Calculo:
- PDFs: 800 x 10 x 250 = 2.000.000 palavras -> ~2.667.000 tokens
- Wiki: 400 x 1.500 = 600.000 palavras -> ~800.000 tokens
- Planilhas: 50 x 3 x 200 = 30.000 celulas; 30.000 x 0,7 x 10 = 210.000 palavras -> ~280.000 tokens

Total aproximado: ~3.747.000 tokens
Faixa razoavel: 2,8M a 4,85M tokens

Leitura rapida:
- a base e muito maior que a janela de 128K;
- retrieval seletivo e obrigatorio;
- a premissa de 10 paginas/doc precisa ser validada com amostragem real antes de fechar custo.

### 1.3 Orcamento de contexto (janela 128K)

Orcamento por query:
- system prompt + instrucoes: ~2.000
- historico curto (3 turnos): ~4.500
- metadados/formatacao: ~500
- reserva para resposta: ~1.500
- sobra para chunks: ~119.500

Capacidade teorica com chunk de 500:
- 119.500 / 500 ~= 239 chunks

Capacidade pratica (melhor qualidade):
- pergunta pontual: 8-12 chunks
- pergunta tabular/multidominio: 15-25 chunks menores

Decisao pratica:
- prefiro recuperar mais candidatos no vetor e reranquear forte antes de montar prompt;
- empilhar chunks demais piora sinal/ruido e aumenta risco de perder trecho importante no meio.

### 1.4 Estrategia de chunking que recomendo

| Tipo de conteudo | Estrategia | Faixa alvo |
|---|---|---|
| PDF narrativo | por secao/paragrafo | 400-600 |
| Tabela frete/SLA | por linha ou bloco com cabecalho repetido | 100-300 |
| Politica/norma | por clausula/artigo | 300-500 |
| Confluence | por heading H2/H3 | 400-700 |
| Planilha materializada | por grupo de linhas com contexto | 200-400 |

Onde chunk fixo por token costuma dar problema:
- quebra tabela no meio;
- separa passo de procedimento;
- separa regra da excecao;
- separa formula do contexto que da significado.

Heuristica de montagem do contexto:
- ordenar chunks por relevancia com estrategia tipo sandwich (mais forte no inicio e no fim).

---

## 2. Revisao critica com Claude

## Prompt de revisao que usei
Revise esta analise de forma critica. Liste:
1. estimativas otimistas;
2. riscos que ficaram de fora;
3. incoerencias tecnicas;
4. o que deve ser mantido.

Para cada ponto, sugira correcao objetiva.

## O que o Claude apontou (resumo)
1. media de 10 paginas por PDF pode estar subestimada.
2. historico de conversa estava subdimensionado na primeira versao.
3. openpyxl nao recalcula formula, apenas le valor cacheado.
4. faltava detalhar ACL no retrieval.
5. faltava estrategia de reindexacao incremental (criacao/atualizacao/delecao).
6. resolucao de links no Confluence precisava limite por tamanho final.
7. lost in the middle nao deve ser tratado como verdade universal sem teste no modelo escolhido.
8. escolha de Azure AI Search estava sem trade-off claro (integracao vs lock-in/custo).

---

## 3. O que eu corrigi na versao final

### 3.1 Ajustes aplicados
- corrigi orcamento de historico para ~4.500 tokens;
- adicionei opcoes reais para planilha, sem forcar uma unica abordagem:
  - openpyxl lendo cache com ressalva;
  - xlwings/Excel para recalculo;
  - exportacao valores-apenas pela area de negocio;
- no Confluence, usei limite de profundidade e limite de tamanho final por chunk;
- explicitei requisito de ACL no retrieval por metadado de permissao;
- inclui fluxo de reindexacao incremental com deteccao de mudanca;
- deixei claro o trade-off de Azure AI Search vs alternativas.

### 3.2 Recomendacoes finais
- retrieval com reranking e filtro por metadado como padrao;
- chunking orientado a estrutura do documento, nao tamanho fixo cego;
- resposta sempre com fonte;
- governanca de versao para evitar conflito entre conteudos antigos e vigentes.

### 3.3 Como verificar se as correcoes foram aplicadas
- ACL no retrieval:
  - criterio: usuario sem permissao nao pode receber chunk protegido;
  - teste: executar mesma pergunta com dois perfis (com e sem acesso) e comparar lista de chunks retornados.
- Reindexacao incremental:
  - criterio: atualizacao substitui versao antiga e delecao remove chunk do indice;
  - teste: alterar um trecho de documento, rodar sincronizacao incremental e verificar se o texto antigo desapareceu do top-k.
- Historico de contexto:
  - criterio: budget de historico nao pode exceder limite definido no orcamento;
  - teste: simular conversa longa e validar truncamento controlado antes da chamada ao LLM.
- Contradicao de versao (PROC-042 v1/v2):
  - criterio: chamado novo deve priorizar v2;
  - teste: pergunta de frete para chamado posterior a 01/12/2023 nao pode trazer multiplicador da v1 no topo.

---

## 4. Conclusao
Conclusao tecnica: viavel.

Ponto de atencao: o risco maior nao esta no modelo de linguagem isolado. O risco esta em ingestao, qualidade do dado indexado, controle de acesso e sincronizacao da base.

Se essas frentes forem tratadas desde o inicio da POC, o cenario e factivel para evoluir sem retrabalho pesado.
