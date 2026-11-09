"""Gera o PDF acadêmico e os JSONs das coleções consultando o MongoDB real.

python scripts/gerar_entrega.py --nomes "Nome 1; Nome 2" --github "https://github.com/usuario/repositorio"
"""

import argparse
import json
import os
from pathlib import Path
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bson import json_util
from pymongo.errors import PyMongoError
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

from campus.analytics import query_definitions
from campus.database import Database, SCHEMA
from campus.domain import now_utc

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    ("_id", "ObjectId", "Identificador gerado pelo MongoDB."),
    ("titulo", "string", "Resumo do problema."),
    ("descricao", "string", "Detalhes e contexto da ocorrência."),
    ("categoria", "string / enum", "Área de atendimento."),
    ("localizacao", "objeto", "Bloco, sala e andar (inteiro)."),
    ("prioridade", "int", "1 baixa, 2 média, 3 alta, 4 urgente."),
    ("status", "string / enum", "Aberto, em análise, em manutenção ou resolvido."),
    ("solicitante", "objeto", "Nome e e-mail de quem registrou."),
    ("responsavel", "string", "Pessoa ou equipe de atendimento."),
    ("tags", "array de strings", "Palavras-chave para pesquisa."),
    ("fotos", "array de strings", "Até três URLs HTTP/HTTPS de fotos."),
    ("custo_estimado", "double", "Estimativa em reais, maior ou igual a zero."),
    ("acessibilidade", "bool", "Indica impacto na acessibilidade."),
    ("criado_em", "date", "Data de abertura em UTC."),
    ("atualizado_em", "date", "Data da última edição em UTC."),
    ("resolvido_em", "date / null", "Data de resolução ou nulo se pendente."),
    ("historico", "array de objetos", "Mudanças de situação, data e observação."),
    ("demonstracao", "bool", "Distingue exemplos de registros novos."),
]


def create_pdf(path, names, github, documents, metadata):
    body_font, bold_font = "Helvetica", "Helvetica-Bold"
    font_path = Path("C:/Windows/Fonts")
    if (font_path / "segoeui.ttf").exists():
        pdfmetrics.registerFont(TTFont("CampusBody", str(font_path / "segoeui.ttf")))
        pdfmetrics.registerFont(TTFont("CampusBold", str(font_path / "segoeuib.ttf")))
        body_font, bold_font = "CampusBody", "CampusBold"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("CampusTitle", fontName=bold_font, fontSize=34, leading=40, textColor=colors.HexColor("#174d3b"), spaceAfter=14))
    styles.add(ParagraphStyle("CampusSubtitle", fontName=body_font, fontSize=15, leading=23, textColor=colors.HexColor("#63795e"), spaceAfter=20))
    styles.add(ParagraphStyle("CampusH2", fontName=bold_font, fontSize=17, leading=23, spaceBefore=18, spaceAfter=10, textColor=colors.HexColor("#174d3b")))
    styles.add(ParagraphStyle("CampusBody", fontName=body_font, fontSize=10, leading=16, spaceAfter=10, textColor=colors.HexColor("#384e3b")))
    styles.add(ParagraphStyle("CampusSmall", parent=styles["CampusBody"], fontSize=8, leading=12, spaceAfter=5))
    styles.add(ParagraphStyle("CampusCode", fontName="Courier", fontSize=6.5, leading=9, textColor=colors.HexColor("#31482f"), leftIndent=6, spaceAfter=0))
    styles.add(ParagraphStyle("CampusLabel", parent=styles["CampusBody"], fontName=bold_font, fontSize=9, textColor=colors.HexColor("#658351"), spaceAfter=8))
    story = []

    def paragraph(text, style="CampusBody"):
        story.append(Paragraph(escape(text), styles[style]))

    def heading(text):
        paragraph(text, "CampusH2")

    def code(content):
        # maxLineLength quebra linhas longas apenas para a leitura no PDF.
        # Os arquivos JSON anexos ao projeto preservam o conteúdo original.
        story.append(Preformatted(content, styles["CampusCode"], maxLineLength=115))

    paragraph("TÓPICOS ESPECIAIS | 2º BIMESTRE | 2º SEMESTRE DE 2026", "CampusLabel")
    story.append(Spacer(1, 18 * mm))
    paragraph("Resolve Campus", "CampusTitle")
    paragraph("Cuidar faz parte.\nGestão colaborativa de ocorrências da faculdade.", "CampusSubtitle")
    paragraph(f"Autores: {names or 'PREENCHER: nome do aluno ou nomes da dupla'}")
    paragraph(f"Repositório GitHub: {github or 'PREENCHER: link do repositório'}")
    paragraph(f"Documento gerado em {now_utc().strftime('%d/%m/%Y %H:%M')} UTC.", "CampusSmall")
    if not names or not github:
        paragraph("VERSÃO PARA REVISÃO: preencha os dados de autoria e/ou GitHub antes da entrega.", "CampusLabel")
    heading("Ideia e finalidade")
    paragraph("O Resolve Campus permite que a comunidade registre problemas de infraestrutura, elétrica, tecnologia, hidráulica, limpeza e acessibilidade. Cada ocorrência tem localização, prioridade e situação de atendimento, tornando o acompanhamento mais claro para alunos e equipe responsável.")
    paragraph("O sistema reúne cadastro, consulta, edição e exclusão em uma aplicação web local. Um painel mostra os indicadores gerais e um mapa esquemático de cinco blocos permite localizar as pendências. As consultas MongoDB ajudam a identificar prioridades, categorias com maior demanda, tempo de resolução e locais recorrentes.")
    paragraph("Todos os documentos iniciais são fictícios para demonstração acadêmica. O mapa é esquemático e não representa a planta ou as coordenadas reais de uma faculdade.")
    story.append(PageBreak())
    heading("1. Atendimento ao enunciado")
    requirements = [
        ("Aplicação com interface", "Flask, HTML, CSS e JavaScript."),
        ("Conexão ao MongoDB", "PyMongo, URI padrão mongodb://localhost:27017."),
        ("CRUD completo", "Cadastrar, listar/detalhar, editar e excluir ocorrências."),
        ("Pelo menos 10 campos", "18 campos incluindo _id, com objetos e arrays."),
        ("Tipos diferentes", "String, Date, ObjectId, int, double, bool, objeto e array."),
        ("Pelo menos 30 documentos", f"A base consultada contém {len(documents)} documentos."),
        ("Pelo menos 4 consultas", "Uma busca com projeção e três pipelines de agregação."),
        ("Diferenciais sugeridos", "Validação, painel, gráfico, mapa, histórico e exportação."),
    ]
    rows = [[Paragraph(escape(a), styles["CampusSmall"]), Paragraph(escape(b), styles["CampusSmall"])] for a, b in requirements]
    table = Table(rows, colWidths=[57 * mm, 116 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef4e8")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (-1, -1), .5, colors.HexColor("#dfe7d9")), ("INNERGRID", (0, 0), (-1, -1), .3, colors.HexColor("#e4eadf")), ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 8)]))
    story.append(table)
    if len(documents) < 30:
        paragraph("ATENÇÃO: há menos de 30 documentos neste momento. Cadastre novos registros antes de gerar a versão final exigida pelo enunciado.", "CampusLabel")
    heading("2. Conexão e persistência")
    paragraph("O servidor verifica o MongoDB com ping antes de cada rota de dados. Sem conexão, responde HTTP 503 e não executa o CRUD nem usa dados locais de substituição. A interface verifica a conexão também ao abrir um formulário, ao voltar para a aba e a cada oito segundos enquanto a aba está visível.")
    paragraph("Na primeira conexão, a aplicação prepara o banco resolve_campus, a coleção ocorrencias, as regras BSON, os índices e os 30 documentos fictícios. A coleção interna _app_meta registra que a inicialização foi concluída, evitando recriar exemplos excluídos. Quedas de conexão ocultam o painel e limpam os dados exibidos. Após a reconexão, os dados são lidos novamente do MongoDB.")
    paragraph("MongoDB Compass é a interface de administração. O serviço MongoDB é quem armazena e fornece os dados; abrir somente o Compass não inicia necessariamente o servidor.")
    heading("3. Arquitetura")
    paragraph("Navegador (HTML/CSS/JavaScript) -> API Flask -> PyMongo -> MongoDB local. O Compass pode acessar o mesmo banco para verificar documentos, índices e validação.")
    paragraph("Arquivos principais: app.py (rotas), campus/database.py (conexão e inicialização), campus/domain.py (validação), campus/analytics.py (consultas), campus/seed.py (exemplos), templates/index.html (interface), static/app.js (interações).")
    heading("4. Modelo da coleção ocorrencias")
    rows = [[Paragraph("Campo", styles["CampusLabel"]), Paragraph("Tipo BSON", styles["CampusLabel"]), Paragraph("Finalidade", styles["CampusLabel"])]]
    rows += [[Paragraph(escape(value), styles["CampusSmall"]) for value in field] for field in FIELDS]
    table = Table(rows, colWidths=[40 * mm, 35 * mm, 98 * mm], repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4e8")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), .3, colors.HexColor("#e4eadf")), ("LEFTPADDING", (0, 0), (-1, -1), 7), ("TOPPADDING", (0, 0), (-1, -1), 6)]))
    story.append(table)
    paragraph("A coleção interna _app_meta contém o identificador da inicialização, data, versão e descrição. Ela não é uma segunda coleção de domínio e não substitui os requisitos da coleção principal.", "CampusSmall")
    story.append(PageBreak())
    heading("5. As quatro consultas MongoDB")
    for index, definition in enumerate(query_definitions(), 1):
        heading(f"5.{index}. {definition['titulo']}")
        paragraph(definition["descricao"])
        paragraph("Operadores: " + ", ".join(definition["operadores"]), "CampusSmall")
        source = definition.get("pipeline") or {"filter": definition["filter"], "projection": definition["projection"], "sort": dict(definition["sort"])}
        code(json_util.dumps(source, ensure_ascii=False, indent=2))
    heading("6. Como executar e demonstrar")
    for step in ["1. Inicie o serviço MongoDB local e conecte o Compass em mongodb://localhost:27017.", "2. No terminal, na raiz do projeto, execute py app.py. Se necessário, o comando reutiliza o ambiente .venv já preparado com Flask e PyMongo.", "3. Abra http://127.0.0.1:5000. A conexão prepara automaticamente a base.", "4. Cadastre um problema, filtre pelo bloco, altere a situação e confira o histórico.", "5. Abra Consultas e indicadores, filtre um bloco e mostre a consulta executada.", "6. Exporte o JSON. Mostre os mesmos registros no MongoDB Compass."]:
        paragraph(step)
    heading("7. Verificação e limites do escopo")
    paragraph("O projeto contém 15 testes automatizados do servidor e um roteiro de verificação real no Edge. Os testes de integração usam bancos temporários com prefixo resolve_campus_test_ e não alteram o banco principal. A verificação inclui CRUD, validação, filtros, consultas, exportação, tela de celular, indisponibilidade e reconexão.")
    paragraph("Este é um protótipo acadêmico local. Não há autenticação, perfis de acesso, notificações, upload de arquivos ou integração com ordens de serviço reais. As fotos são URLs opcionais e dependem da disponibilidade do endereço informado. O servidor é iniciado somente em 127.0.0.1.")
    story.append(PageBreak())
    heading("Anexo A. JSON da coleção ocorrencias")
    paragraph(f"Exportação dos {len(documents)} documentos existentes no MongoDB no momento da geração. Datas e ObjectIds usam MongoDB Extended JSON. O arquivo docs/ocorrencias.json contém o JSON original, sem a quebra de linhas visual usada neste PDF.")
    code(json_util.dumps(documents, ensure_ascii=False, indent=2))
    story.append(PageBreak())
    heading("Anexo B. JSON da coleção interna _app_meta")
    code(json_util.dumps(metadata, ensure_ascii=False, indent=2))
    heading("Anexo C. Validação BSON da coleção principal")
    code(json.dumps({"$jsonSchema": SCHEMA}, ensure_ascii=False, indent=2))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#dfe7d9"))
        canvas.line(18 * mm, 16 * mm, 192 * mm, 16 * mm)
        canvas.setFont(body_font, 7)
        canvas.setFillColor(colors.HexColor("#789068"))
        canvas.drawString(18 * mm, 11 * mm, "Resolve Campus | Projeto acadêmico | 2026")
        canvas.drawRightString(192 * mm, 11 * mm, f"Página {document.page}")
        canvas.restoreState()

    document = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=19 * mm, bottomMargin=23 * mm, title="Resolve Campus - Projeto acadêmico", author=names or "Preencher autoria")
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nomes", default="")
    parser.add_argument("--github", default="")
    parser.add_argument("--saida", default=str(ROOT / "docs" / "entrega-projeto.pdf"))
    args = parser.parse_args()
    database = Database(os.environ.get("MONGO_URI", "mongodb://localhost:27017"), os.environ.get("MONGO_DB", "resolve_campus"))
    try:
        database.ensure_ready()
        documents = list(database.occurrences.find({}).sort("criado_em", -1))
        metadata = list(database.db["_app_meta"].find({}))
        output = Path(args.saida)
        output.parent.mkdir(parents=True, exist_ok=True)
        for filename, data in [("ocorrencias.json", documents), ("_app_meta.json", metadata)]:
            (output.parent / filename).write_text(json_util.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        (output.parent / "schema-ocorrencias.json").write_text(json.dumps({"$jsonSchema": SCHEMA}, ensure_ascii=False, indent=2), encoding="utf-8")
        create_pdf(output, args.nomes, args.github, documents, metadata)
        print(f"PDF gerado: {output}")
        print(f"Documentos reais exportados: {len(documents)}")
        if not args.nomes or not args.github:
            print("Preencha autoria e/ou GitHub e gere novamente antes da entrega final.")
    except PyMongoError:
        print("MongoDB indisponível. Ative o serviço e tente novamente. Nenhum dado fictício local foi usado como substituto.", file=sys.stderr)
        raise SystemExit(1)
    finally:
        database.client.close()


if __name__ == "__main__":
    main()
