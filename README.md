# Resolve Campus

**Cuidar faz parte.** Aplicação web local para registrar e acompanhar problemas da faculdade, desenvolvida para o projeto de Tópicos Especiais do 2º bimestre do 2º semestre de 2026.

O sistema usa **Flask + PyMongo + MongoDB**, com interface em português e sem dependências externas de CSS, gráficos ou mapas no navegador. O MongoDB Compass permite inspecionar o mesmo banco usado pela aplicação.

## Abrir o projeto

Requisitos: Python 3.10 ou superior e MongoDB Community Server instalado. O MongoDB 7.3 disponível neste computador foi usado na verificação. Na primeira instalação das dependências, é necessário acesso à internet.

No Windows, abra o terminal na pasta do projeto e execute o comando solicitado pela professora:

```powershell
py app.py
```

Depois abra **http://127.0.0.1:5000**. Mantenha a janela do terminal aberta enquanto usa o sistema. Para encerrar, pressione `Ctrl+C`.

O comando `py app.py` reutiliza automaticamente o ambiente `.venv` do projeto se as dependências não estiverem disponíveis no Python selecionado pelo comando `py`. Não é necessário ativar o ambiente virtual. Neste computador, ele já está preparado.

Em outro computador, prepare as dependências uma única vez, na raiz do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
py app.py
```

Não é necessário alterar a política de execução do PowerShell. O arquivo `iniciar.bat` continua disponível como atalho opcional.

## Conectar ao MongoDB

Conexão padrão: **`mongodb://localhost:27017`**. Banco: **`resolve_campus`**. Coleção principal: **`ocorrencias`**.

1. No Windows, abra **Serviços** (`services.msc`) e inicie o serviço **MongoDB**.
2. Abra o MongoDB Compass e conecte em `mongodb://localhost:27017`.
3. Abra o sistema no navegador. Se o aviso de conexão aparecer, clique em **Tentar conexão**.
4. Na primeira conexão, o sistema cria o banco, a coleção, a validação BSON, os índices e **30 documentos fictícios**. Atualize a lista de bancos no Compass para visualizá-los.

**Compass é a interface de gerenciamento; o serviço MongoDB é o servidor.** O sistema não tenta iniciar o serviço automaticamente, pois isso pode exigir privilégios de administrador.

O comportamento sem conexão é deliberado:

- O servidor executa `ping` **antes de cada rota da API**, incluindo consulta, cadastro, edição, exclusão e exportação.
- Sem MongoDB disponível, a API responde **HTTP 503**. Não há banco em memória, JSON de substituição ou modo de demonstração desconectado.
- A interface verifica a conexão na entrada, antes de abrir formulários, ao voltar à aba e a cada **8 segundos** enquanto a aba estiver visível. Uma ação detecta a indisponibilidade assim que sua requisição falha.
- Se a conexão cair, o sistema fecha formulários, oculta o painel e remove os dados exibidos. A detecção não é instantânea: depende da requisição ou da próxima checagem periódica.
- Ao reconectar, ele consulta os documentos persistidos no MongoDB novamente.
- Exemplos são inseridos somente na inicialização. Registros excluídos não voltam ao reiniciar ou reconectar. A coleção interna `_app_meta` guarda esse controle.
- Uma coleção preexistente com registros não demonstrativos é preservada; o sistema não acrescenta os 30 exemplos nesse caso.

Não exclua `_app_meta` para esvaziar o sistema: use as ações da interface. Remover todo o banco manualmente pelo Compass implica uma nova inicialização na próxima conexão.

Para outra configuração, defina variáveis de ambiente antes de iniciar:

```powershell
$env:MONGO_URI = "mongodb://localhost:27017"
$env:MONGO_DB = "resolve_campus"
$env:PORT = "5000"
py app.py
```

O endereço mostrado na ajuda da interface corresponde à conexão local padrão deste projeto. Um arquivo `.env` não é carregado automaticamente.

## O que dá para fazer

- **Visão geral:** total de ocorrências, pendências, urgências, resoluções e registros recentes.
- **Mapa esquemático:** cinco blocos clicáveis; os marcadores mostram a quantidade de pendências, e a cor indica urgências. Não usa coordenadas reais nem mapas externos.
- **CRUD completo:** cadastrar, consultar, editar e excluir ocorrências com confirmação.
- **Filtros combinados:** texto, bloco, situação, categoria e prioridade; paginação de 10 registros.
- **Acompanhamento:** responsável, histórico automático de mudanças de situação e datas de abertura, atualização e resolução.
- **Fotos opcionais:** até três links HTTP/HTTPS por ocorrência; não há upload de arquivos.
- **Validações:** formulário, servidor e schema BSON na coleção. Uma edição desatualizada recebe conflito HTTP 409, evitando sobrescrever alterações de outra janela.
- **Consultas e indicadores:** quatro consultas reais com recorte por bloco, gráfico de categorias e visualização do comando executado.
- **Exportação:** botão **Exportar JSON** baixa a coleção atual em MongoDB Extended JSON, preservando ObjectIds e datas.

O protótipo é de uso local, sem autenticação ou perfis de usuário. O servidor inicia em `127.0.0.1`, com debug desligado. Todos os exemplos iniciais são fictícios e usam e-mails `example.com`.

## Requisitos da atividade

| Exigência do PDF | Implementação |
| --- | --- |
| Aplicação web Flask ou interface Tkinter | Aplicação web Flask |
| Conexão MongoDB e CRUD | PyMongo e rotas GET, POST, PUT e DELETE |
| Pelo menos 10 campos e tipos diferentes | 18 campos incluindo `_id`; strings, datas, objetos, arrays, inteiros, double e booleanos |
| Pelo menos 30 documentos | 30 registros fictícios inseridos na primeira conexão |
| Pelo menos 4 consultas com operadores, agregações e projeções | 1 busca projetada + 3 agregações em `campus/analytics.py` |
| Diferenciais sugeridos | Validação, painel, gráfico, mapa, histórico, exportação e PDF via ReportLab |
| PDF de entrega | `docs/entrega-projeto.pdf`, gerado a partir do MongoDB |

A coleção principal tem: `_id`, `titulo`, `descricao`, `categoria`, `localizacao`, `prioridade`, `status`, `solicitante`, `responsavel`, `tags`, `fotos`, `custo_estimado`, `acessibilidade`, `criado_em`, `atualizado_em`, `resolvido_em`, `historico` e `demonstracao`.

Datas são BSON Date em UTC, não strings no banco. A interface as apresenta no fuso do navegador. `localizacao` e `solicitante` são objetos; `tags`, `fotos` e `historico` são arrays.

## As quatro consultas

| Consulta | Pergunta respondida | Recursos principais |
| --- | --- | --- |
| Pendências prioritárias | O que exige atenção por prioridade ou acessibilidade? | `find`, `$and`, `$or`, `$ne`, `$gte`, projeção e ordenação |
| Demanda por categoria | Quais áreas concentram registros, pendências e custos estimados? | `$match`, `$group`, `$sum`, `$cond`, `$project`, `$sort` |
| Tempo médio de resolução | Quanto tempo, em média, leva a solução por categoria? | `$type`, `$avg`, `$subtract`, `$divide`, `$round`, `$project` |
| Locais com mais ocorrências | Quais blocos tiveram mais registros nos últimos 30 dias? | `$gte`, `$in`, `$addToSet`, `$group`, `$cond`, `$project` |

As consultas rodam no MongoDB. O navegador apenas apresenta os resultados. A tela mostra o filtro ou pipeline efetivamente executado. A consulta de resolução considera apenas registros resolvidos; a de locais usa uma janela móvel, então os números mudam com a passagem do tempo.

## Documento de entrega

O PDF contém a finalidade do sistema, a arquitetura, os campos, as consultas e o JSON completo das coleções `ocorrencias` e `_app_meta`. O link GitHub configurado neste projeto é `https://github.com/LucasMartins17/ProjetoMongoDB`. **A autoria deve ser preenchida antes da entrega.**

Para gerar novamente com os nomes e os dados atuais do MongoDB:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-documentacao.txt
.\.venv\Scripts\python.exe scripts/gerar_entrega.py --nomes "Nome completo 1; Nome completo 2" --github "https://github.com/LucasMartins17/ProjetoMongoDB"
```

O gerador precisa do MongoDB conectado. Ele também grava os JSONs em `docs/`. Esses arquivos são fotografias da base para a entrega e **não são usados como fonte de dados pela aplicação**. Atualize o PDF após suas alterações e mantenha pelo menos 30 documentos para cumprir o enunciado.

O arquivo **`guia slides.md`** orienta a IA responsável pela apresentação e contém o roteiro de demonstração. A entrega e a apresentação são no dia da prova do 2º bimestre; o enunciado não informa a data exata.

## Testes

Com o MongoDB local ativo:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

São 15 testes cobrindo conexão indisponível, CRUD real, tipos BSON, validação, conflitos de edição, filtros, paginação, consultas, indicadores, exportação e inicialização. Os testes conectados são marcados como ignorados se o MongoDB estiver indisponível. Cada execução usa um banco temporário `resolve_campus_test_<identificador>`, removido ao terminar; o banco principal é preservado.

Para a verificação real da interface com Microsoft Edge instalado:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/verificar_interface.py
```

O roteiro abre o Edge sem janela, usa banco temporário separado e gera capturas em `test-results/`. Ele verifica indisponibilidade inicial, reconexão, 30 registros, mapa, filtros, paginação, CRUD, histórico, consultas, download do JSON e tela de celular. A queda é testada apontando somente o cliente da aplicação de teste para uma porta indisponível: o serviço MongoDB do computador continua ativo.

## Organização

```text
app.py                       Rotas Flask e bloqueio por conexão
campus/database.py           MongoDB, schema, índices e inicialização
campus/domain.py             Validação e regras de negócio
campus/seed.py               30 exemplos fictícios
campus/analytics.py          Quatro consultas acadêmicas
templates/index.html        Interface
static/                     CSS, JavaScript e favicon
tests/test_app.py           Testes de integração e indisponibilidade
scripts/verificar_interface.py  Verificação real no Edge
scripts/gerar_entrega.py     Gerador do PDF e dos JSONs
docs/                       Arquivos da entrega acadêmica
guia slides.md              Orientações para a apresentação
iniciar.bat                 Atalho opcional no Windows
```

Referências técnicas: [testes Flask](https://flask.palletsprojects.com/en/stable/testing/), [conexão com PyMongo](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/), [validação de schema MongoDB](https://www.mongodb.com/docs/manual/core/schema-validation/).
