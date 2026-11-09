# Guia para a IA gerar a apresentação — Resolve Campus

## Instrução principal

Crie uma apresentação acadêmica em português brasileiro sobre o **Resolve Campus**, um sistema web local de gestão de ocorrências da faculdade. O slogan é **“Cuidar faz parte.”** A apresentação deve durar aproximadamente **7 a 10 minutos**, com **10 slides principais** e notas de fala para o apresentador. Deixe material técnico adicional em slides de apoio, se necessário.

O público é o professor de Tópicos Especiais e os colegas de turma. O objetivo é apresentar um problema compreensível, demonstrar uma solução prática e comprovar que o projeto cumpre os requisitos de Flask, MongoDB, CRUD, tipos variados, 30 documentos e quatro consultas.

Use apenas as funcionalidades implementadas neste repositório. Não invente integrações, resultados de usuários reais, números de economia, inteligência artificial, notificações ou recursos futuros como se estivessem prontos.

## Dados de identificação

- Projeto: **Resolve Campus**.
- Disciplina: **Tópicos Especiais**.
- Período: **2º bimestre do 2º semestre de 2026**.
- Autores: **[PREENCHER COM O NOME DO ALUNO OU OS NOMES DA DUPLA]**. Não deduza nomes completos pelo usuário do GitHub.
- GitHub configurado: **https://github.com/LucasMartins17/ProjetoMongoDB**.
- Execução: **http://127.0.0.1:5000** na máquina que está rodando a aplicação.
- MongoDB: **mongodb://localhost:27017**.
- Banco principal: **resolve_campus**.
- Coleção de domínio: **ocorrencias**.
- Coleção interna de controle: **_app_meta**.
- Data de apresentação: no dia da prova do 2º bimestre. O PDF da atividade não informa a data exata; não invente uma.

O endereço local não é um site público. O link GitHub é o endereço configurado no repositório; antes de entregar, conferir se os arquivos finais já foram enviados para ele.

## Fontes que a IA deve consultar

1. `README.md`: instalação, execução, recursos e limites.
2. `app.py`: endpoints, CRUD, proteção por conexão e controle de edição.
3. `campus/database.py`: ping, schema BSON, índices e inicialização.
4. `campus/domain.py`: tipos, enums, validações e datas.
5. `campus/analytics.py`: fonte oficial das quatro consultas.
6. `campus/seed.py`: os 30 exemplos fictícios iniciais.
7. `docs/entrega-projeto.pdf`: relatório com descrição do sistema e JSON completo das coleções.
8. `docs/ocorrencias.json`, `docs/_app_meta.json` e `docs/schema-ocorrencias.json`: exportações e modelo.
9. `docs/imagens/`: capturas reais da interface para usar nos slides.
10. `atividade_nota_2s_2026.pdf`: enunciado original.

O PDF de entrega e os JSONs são fotografias da base na data da geração. A aplicação consulta o MongoDB, sem ler esses arquivos para exibir registros.

## Direção visual

- Formato 16:9, com bastante espaço e texto legível no projetor.
- Verde escuro `#133d31`, verde principal `#174d3b`, verde claro `#d2edb8`, fundo `#f6f7f5` e texto `#24382f`.
- Use títulos curtos, até três ideias por slide e notas de fala para a explicação mais longa.
- Prefira capturas reais, pequenos diagramas e cartões de indicadores a parágrafos extensos.
- Mantenha a linguagem visual da aplicação: organização clara, blocos do campus, cuidado com a comunidade e marcadores de prioridade.
- Preserve a proporção das capturas. Se recortar, mantenha as informações necessárias para entender a tela.
- O mapa mostrado é **esquemático**, com cinco blocos fictícios. Não o apresente como planta oficial, GPS, geolocalização ou mapa de uma instituição específica.
- Não invente logotipo oficial de faculdade, selo de aprovação ou nomes de professores.

## Roteiro dos 10 slides

### Slide 1 — Resolve Campus

**Mensagem:** transformar problemas do cotidiano em registros que podem ser acompanhados.

Na tela: nome, slogan, autores, disciplina e uma imagem do painel.

Visual sugerido: `docs/imagens/visao-geral.png`, com destaque para título, indicadores e mapa.

Fala sugerida: “Um projetor para de funcionar, surge um vazamento ou uma rampa apresenta um defeito. Como registrar o problema e acompanhar se alguém está cuidando dele? Essa é a proposta do Resolve Campus.”

### Slide 2 — O problema que queremos organizar

**Mensagem:** informações espalhadas dificultam o acompanhamento.

Use três exemplos: projetor sem imagem, vazamento e obstáculo de acessibilidade. Explique a necessidade de saber **o que aconteceu, onde aconteceu e em que situação está**.

Apresente isso como motivação do projeto. Não alegue ter feito pesquisa de campo ou medido problemas reais da faculdade.

### Slide 3 — Uma solução prática para a comunidade

**Mensagem:** registrar, localizar e acompanhar em um só lugar.

Mostre as três áreas implementadas: **Visão geral**, **Ocorrências** e **Consultas e indicadores**.

Destaque o mapa clicável dos blocos A a E, a prioridade da ocorrência e o acompanhamento da situação.

Use a captura do painel. Se mostrar números da base inicial, identifique como **dados fictícios de demonstração**.

### Slide 4 — A conexão é a porta de entrada

**Mensagem:** sem MongoDB disponível, os dados e as ações ficam indisponíveis.

Diagrama:

```text
Navegador → Flask → ping no MongoDB
                       ├─ Falhou: HTTP 503, aviso e ações bloqueadas
                       └─ Conectou: preparar banco → consultar dados reais
```

Use `docs/imagens/conexao-indisponivel.png`.

Explique nas notas:

- O ping acontece antes de cada rota da API.
- A primeira conexão prepara banco, coleção, validação, índices e 30 documentos.
- O navegador checa também ao entrar, ao abrir formulário, ao voltar à aba e a cada 8 segundos enquanto a aba está visível.
- Se a conexão cair, a tela oculta o painel, fecha formulários e remove os dados exibidos.
- Ao reconectar, os registros são lidos do MongoDB novamente.
- Os exemplos excluídos não voltam: `_app_meta` registra que a inicialização terminou.
- A detecção de uma queda depende da próxima requisição ou checagem; não chame de detecção instantânea.
- O Compass gerencia o banco. O serviço MongoDB precisa estar ativo para fornecer os dados.

### Slide 5 — Como os dados foram modelados

**Mensagem:** documentos que combinam tipos simples e estruturas aninhadas.

A coleção tem **18 campos incluindo `_id`**. Mostre um recorte legível, sem despejar todos os documentos no slide:

```javascript
{
  titulo: "Projetor sem imagem",         // string
  prioridade: 3,                        // int
  localizacao: { bloco: "B", sala: "Laboratório 02", andar: 0 },
  solicitante: { nome: "Exemplo", email: "exemplo@example.com" },
  tags: ["tecnologia", "demonstração"], // array
  custo_estimado: 450.0,                // double
  acessibilidade: false,                // boolean
  criado_em: ISODate("2026-11-01T10:00:00Z") // BSON Date
}
```

Este trecho é uma **representação didática parcial**, não um documento completo pronto para importar. A data é ilustrativa. O JSON completo está em `docs/ocorrencias.json`.

Nas notas, cite ainda `status`, `responsavel`, `fotos`, `atualizado_em`, `resolvido_em`, `historico` e `demonstracao`.

Explique que as datas são BSON Date no banco, os números não são todos textos, e os campos obrigatórios são validados pelo servidor e pelo MongoDB.

### Slide 6 — CRUD e acompanhamento

**Mensagem:** uma ocorrência tem um ciclo completo, do registro à solução.

Use quatro ações: **Cadastrar → Consultar → Editar → Excluir**.

Mostre separadamente as situações disponíveis: **Aberto → Em análise → Em manutenção → Resolvido**. Elas podem ser selecionadas diretamente; o sistema não exige passar por todas em ordem. Uma ocorrência resolvida pode ser reaberta.

Destaque histórico automático das mudanças de situação, confirmação de exclusão, filtros e busca, validação dos dados e proteção contra sobrescrever uma edição mais recente de outra janela.

As datas de resolução são controladas pelo servidor; não são preenchidas manualmente pelo usuário.

### Slide 7 — Quatro consultas que respondem perguntas

**Mensagem:** MongoDB também ajuda a entender e priorizar o atendimento.

Use uma tabela resumida:

| Consulta | Pergunta | Recursos MongoDB |
| --- | --- | --- |
| Pendências prioritárias | O que exige atenção por prioridade ou acessibilidade? | `find`, `$and`, `$or`, `$ne`, `$gte`, projeção |
| Demanda por categoria | Onde estão o volume, as pendências e o custo estimado? | `$group`, `$sum`, `$cond`, `$project` |
| Tempo médio de resolução | Quanto tempo leva a solução, por categoria? | `$avg`, `$subtract`, `$divide`, `$round` |
| Locais com mais ocorrências | Quais blocos concentram registros recentes? | `$match`, `$gte`, `$in`, `$addToSet`, `$group` |

Explique que são **uma busca com projeção e três pipelines de agregação**. O conjunto atende à variedade de recursos solicitada no enunciado. Não diga que todas as quatro usam todos os operadores ou que todas são agregações.

Se precisar mostrar código, escolha um trecho curto de `campus/analytics.py` e deixe o código completo em um slide de apoio ou na demonstração.

### Slide 8 — Dos documentos aos indicadores

**Mensagem:** resultados de consultas ficam mais compreensíveis em um painel.

Use `docs/imagens/consultas.png`, que mostra um recorte do bloco B.

Destaque o gráfico de demanda por categoria, a média de resolução e o filtro por bloco. Mostre que a própria tela permite abrir a consulta executada no MongoDB.

Cuidados com a explicação:

- O tempo médio é em **horas**, apenas entre registros resolvidos.
- O ranking de locais considera os **últimos 30 dias**. Ele pode mudar com o tempo mesmo sem cadastrar algo novo.
- Custo estimado não é gasto efetivo nem economia obtida.
- Os indicadores refletem documentos fictícios do protótipo. Não são resultados de uso real da faculdade.
- Os gráficos são feitos com HTML, CSS e JavaScript, sem Plotly ou Chart.js. ReportLab é usado no gerador do PDF, não nos gráficos.

### Slide 9 — Demonstração e verificação

**Mensagem:** o fluxo foi testado com MongoDB real.

Reserve aproximadamente 2 minutos para a demonstração ao vivo descrita abaixo. No slide, coloque somente o fluxo principal e uma indicação de que há 15 testes automatizados do servidor e uma verificação real no Edge.

Explique que os testes usam bancos temporários separados e não alteram o banco principal. Nos testes de conexão, somente o cliente da aplicação de teste aponta para uma porta indisponível; o serviço MongoDB do computador continua ativo.

Não descreva esses testes como prova de segurança de produção, teste de carga ou certificação.

### Slide 10 — O que foi entregue

**Mensagem:** uma solução acadêmica funcional, com evidências dos requisitos.

Mostre um checklist curto: **Flask + MongoDB; CRUD; 18 campos; 30 documentos iniciais; quatro consultas; painel, validação e exportação**.

Inclua GitHub, autores e a frase de encerramento: “Cuidar do campus começa por tornar os problemas visíveis e acompanhar as soluções.”

Nas notas, delimite o escopo: protótipo local sem login, notificações ou integração com equipes reais. Fotos são links opcionais; não há upload. Autenticação e notificações podem ser citadas como possibilidades futuras, claramente identificadas assim.

## Roteiro para a demonstração ao vivo

### Preparação antes da apresentação

1. Confirme Python, dependências e serviço MongoDB disponíveis.
2. No terminal, na pasta do projeto, execute **`py app.py`**, conforme solicitado pela professora, e abra `http://127.0.0.1:5000`. O ambiente `.venv` já preparado é reutilizado automaticamente se necessário.
3. Abra o Compass na mesma conexão e localize `resolve_campus.ocorrencias`.
4. Confirme pelo menos 30 documentos antes da entrega. Se excluiu exemplos, cadastre novas ocorrências; eles não voltam automaticamente.
5. Confira a autoria e o link do GitHub no PDF. Se necessário, gere o PDF novamente conforme o README.
6. Deixe as capturas de `docs/imagens/` disponíveis como apoio para uma falha do projetor ou do navegador.

### História sugerida

1. Mostre o painel geral e clique no bloco B do mapa.
2. Cadastre **“Projetor sem imagem no auditório”** com descrição de pelo menos 10 caracteres, categoria Tecnologia, bloco B, sala Auditório, prioridade Urgente, nome e e-mail de exemplo.
3. Encontre a ocorrência usando a busca.
4. Abra o registro, altere a situação para Em manutenção e informe uma equipe responsável. Salve.
5. Abra novamente e mostre o histórico. Marque como Resolvido e salve.
6. Abra Consultas e indicadores, selecione o bloco B e mostre uma consulta executada.
7. Exporte o JSON e mostre no Compass que o registro está no MongoDB.
8. Demonstre a exclusão somente do registro criado na apresentação, com confirmação. Assim a base inicial continua com 30 documentos.

Se o tempo for curto, faça só cadastro, mudança para Resolvido, histórico e uma consulta. A exclusão pode ser explicada com a tela de confirmação.

Para demonstrar o aviso sem MongoDB ao vivo, prepare um momento separado e controlado. Não pare um serviço compartilhado durante o restante da apresentação. A captura `conexao-indisponivel.png` e o roteiro automatizado já permitem comprovar esse comportamento sem interromper o banco principal.

## Perguntas prováveis do professor

**Por que usar MongoDB?**

O documento reúne a ocorrência, a localização, o solicitante, as tags, as fotos e o histórico com objetos e arrays. O projeto também explora filtros, projeções e agregações do banco, conforme o enunciado.

**O Compass é o banco de dados?**

É a interface de administração. O aplicativo conecta ao servidor MongoDB pelo PyMongo; o Compass pode inspecionar os mesmos documentos.

**O que acontece se o MongoDB estiver desligado?**

A API falha na verificação e responde 503. A interface mostra o aviso, bloqueia as ações e oculta os registros. Não existe fonte alternativa de dados para continuar operando.

**O banco é criado automaticamente?**

Sim, após a primeira conexão válida. São preparados coleção, schema, índices e dados iniciais. A criação não acontece antes da confirmação da conexão.

**Se excluir os exemplos, eles voltam?**

Não. A coleção `_app_meta` guarda a conclusão da inicialização. Uma exclusão completa do próprio banco pelo administrador representa uma nova base e permite uma nova inicialização.

**Onde estão os diferentes tipos?**

`titulo` é string, `criado_em` é Date, `localizacao` é objeto, `tags` é array, `prioridade` é int, `custo_estimado` é double e `acessibilidade` é bool.

**Os 30 documentos representam ocorrências reais?**

Não. São exemplos fictícios identificados por `demonstracao: true`. Ocorrências criadas pela interface recebem `demonstracao: false`.

**As consultas são calculadas no JavaScript?**

Não. Filtros e agregações rodam no MongoDB. O JavaScript apresenta os resultados recebidos do Flask.

**Por que há mais de uma coleção nos arquivos da entrega?**

`ocorrencias` contém o domínio do sistema. `_app_meta` é uma pequena coleção técnica de controle da inicialização. Os 30 documentos e os 18 campos se referem à coleção principal.

## Critérios para revisar os slides antes de finalizar

- Autores preenchidos e link GitHub conferido.
- MongoDB e Flask identificados corretamente.
- Explicação clara do bloqueio sem conexão e da preparação automática após conectar.
- Pelo menos um exemplo de objeto, array, data e número mostrado.
- As quatro consultas nomeadas, com finalidade e recursos corretos.
- Capturas reais utilizadas e dados fictícios identificados.
- Mapa apresentado como esquemático.
- Notas de fala incluídas, com pouco texto nos slides.
- Roteiro prático cabe no tempo disponível.
- Nenhuma funcionalidade futura apresentada como já implementada.
