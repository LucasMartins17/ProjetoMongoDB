"""30 documentos fictícios. Usados somente para inicializar o MongoDB conectado."""

from datetime import timedelta
from bson import ObjectId
from .domain import now_utc

EXAMPLES = [
    ("Projetor sem imagem", "Tecnologia", "B", "Laboratório 02", 3, "aberto", 450),
    ("Vazamento no bebedouro", "Hidráulica", "A", "Corredor térreo", 4, "em_manutencao", 280),
    ("Lâmpadas apagadas na leitura", "Elétrica", "C", "Sala de leitura", 2, "em_analise", 120),
    ("Rampa com piso solto", "Acessibilidade", "D", "Entrada principal", 4, "aberto", 650),
    ("Tomada sem funcionamento", "Elétrica", "A", "Sala 105", 2, "resolvido", 90),
    ("Ar-condicionado com ruído", "Infraestrutura", "B", "Laboratório 01", 2, "em_manutencao", 380),
    ("Lixeira danificada", "Limpeza", "D", "Área de alimentação", 1, "aberto", 150),
    ("Computador não inicializa", "Tecnologia", "B", "Laboratório 03", 3, "em_analise", 540),
    ("Porta do banheiro travando", "Infraestrutura", "E", "Banheiro térreo", 2, "resolvido", 180),
    ("Sinalização tátil descolada", "Acessibilidade", "C", "Entrada da biblioteca", 3, "aberto", 220),
    ("Torneira pingando", "Hidráulica", "D", "Copa", 2, "resolvido", 75),
    ("Wi-Fi instável na biblioteca", "Tecnologia", "C", "Sala de estudo", 3, "em_manutencao", 320),
    ("Cadeira com encosto quebrado", "Infraestrutura", "A", "Sala 203", 2, "aberto", 130),
    ("Interruptor com mau contato", "Elétrica", "E", "Secretaria", 4, "em_analise", 160),
    ("Limpeza da área externa", "Limpeza", "D", "Jardim central", 1, "resolvido", 0),
    ("Elevador sem sinal sonoro", "Acessibilidade", "A", "Hall do elevador", 3, "em_manutencao", 480),
    ("Infiltração no teto", "Infraestrutura", "C", "Acervo", 4, "em_analise", 1200),
    ("Mouse com botão defeituoso", "Tecnologia", "B", "Laboratório 04", 1, "resolvido", 45),
    ("Entupimento de pia", "Hidráulica", "E", "Copa administrativa", 3, "aberto", 190),
    ("Luminária piscando", "Elétrica", "D", "Corredor coberto", 2, "resolvido", 110),
    ("Acúmulo de resíduos", "Limpeza", "B", "Entrada lateral", 2, "em_analise", 0),
    ("Corrimão solto", "Acessibilidade", "E", "Escada principal", 4, "aberto", 350),
    ("Quadro branco danificado", "Infraestrutura", "A", "Sala 102", 1, "resolvido", 260),
    ("Impressora não conecta", "Tecnologia", "E", "Atendimento", 2, "em_manutencao", 180),
    ("Descarga com vazamento", "Hidráulica", "C", "Banheiro acessível", 3, "aberto", 210),
    ("Iluminação externa insuficiente", "Elétrica", "B", "Acesso ao laboratório", 3, "em_analise", 420),
    ("Higienização de mesas", "Limpeza", "C", "Estudo em grupo", 1, "resolvido", 0),
    ("Maçaneta de difícil acesso", "Acessibilidade", "D", "Sala de convivência", 2, "em_manutencao", 140),
    ("Ventilador sem proteção", "Infraestrutura", "A", "Sala 201", 4, "aberto", 230),
    ("Reposição de sabonete", "Limpeza", "E", "Banheiro do corredor", 1, "resolvido", 35),
]


def seed_documents():
    now = now_utc()
    documents = []
    for index, (title, category, block, room, priority, status, cost) in enumerate(EXAMPLES, 1):
        created = now - timedelta(days=32 - index, hours=index % 7)
        resolved = created + timedelta(hours=8 + index * 2) if status == "resolvido" else None
        changed = resolved or (created + timedelta(hours=4) if status != "aberto" else created)
        history = [{"status": "aberto", "data": created, "observacao": "Ocorrência de demonstração criada."}]
        if status != "aberto":
            history.append({"status": status, "data": changed, "observacao": "Atualização de demonstração."})
        documents.append({
            "_id": ObjectId(f"66000000000000000000{index:04x}"),
            "titulo": title,
            "descricao": f"Foi identificado o seguinte problema: {title.lower()}. Local: {room}, bloco {block}. Solicita-se avaliação da equipe responsável. Registro fictício para demonstração acadêmica.",
            "categoria": category,
            "localizacao": {"bloco": block, "sala": room, "andar": 1 if index % 4 == 0 else 0},
            "prioridade": priority,
            "status": status,
            "solicitante": {"nome": f"Estudante Exemplo {index:02}", "email": f"estudante{index:02}@example.com"},
            "responsavel": "Equipe de manutenção" if status != "aberto" else "",
            "tags": [category.lower(), "demonstração"],
            "fotos": [],
            "custo_estimado": float(cost),
            "acessibilidade": category == "Acessibilidade",
            "criado_em": created,
            "atualizado_em": changed,
            "resolvido_em": resolved,
            "historico": history,
            "demonstracao": True,
        })
    return documents
