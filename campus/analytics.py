"""As quatro consultas acadêmicas são executadas no próprio MongoDB."""

from datetime import timedelta
from .domain import now_utc


def query_definitions(block=None):
    scope = {"localizacao.bloco": block} if block else {}
    recent = now_utc() - timedelta(days=30)
    return [
        {
            "id": "urgentes", "titulo": "Pendências prioritárias", "tipo": "find + projeção",
            "descricao": "Ocorrências abertas com prioridade alta ou urgente, ou que afetam a acessibilidade.",
            "filter": {"$and": [scope, {"status": {"$ne": "resolvido"}}, {"$or": [{"prioridade": {"$gte": 3}}, {"acessibilidade": True}]}]},
            "projection": {"titulo": 1, "localizacao": 1, "prioridade": 1, "status": 1, "acessibilidade": 1, "criado_em": 1},
            "sort": [("prioridade", -1), ("criado_em", 1)],
            "operadores": ["$and", "$or", "$ne", "$gte", "projeção", "sort"],
        },
        {
            "id": "categorias", "titulo": "Demanda por categoria", "tipo": "aggregate",
            "descricao": "Volume, pendências e custo estimado de todas as ocorrências por categoria.",
            "pipeline": [
                {"$match": scope},
                {"$group": {"_id": "$categoria", "total": {"$sum": 1}, "pendentes": {"$sum": {"$cond": [{"$ne": ["$status", "resolvido"]}, 1, 0]}}, "custo": {"$sum": "$custo_estimado"}}},
                {"$project": {"_id": 0, "categoria": "$_id", "total": 1, "pendentes": 1, "custo": 1}},
                {"$sort": {"total": -1, "categoria": 1}},
            ],
            "operadores": ["$match", "$group", "$sum", "$cond", "$ne", "$project", "$sort"],
        },
        {
            "id": "resolucao", "titulo": "Tempo médio de resolução", "tipo": "aggregate",
            "descricao": "Média em horas por categoria, considerando somente registros resolvidos com datas válidas.",
            "pipeline": [
                {"$match": {**scope, "status": "resolvido", "resolvido_em": {"$type": "date"}}},
                {"$group": {"_id": "$categoria", "resolvidos": {"$sum": 1}, "media_horas": {"$avg": {"$divide": [{"$subtract": ["$resolvido_em", "$criado_em"]}, 3_600_000]}}}},
                {"$project": {"_id": 0, "categoria": "$_id", "resolvidos": 1, "media_horas": {"$round": ["$media_horas", 1]}}},
                {"$sort": {"media_horas": 1, "categoria": 1}},
            ],
            "operadores": ["$match", "$type", "$group", "$avg", "$subtract", "$divide", "$project", "$round"],
        },
        {
            "id": "locais", "titulo": "Locais com mais ocorrências", "tipo": "aggregate",
            "descricao": "Ranking por bloco nos últimos 30 dias, com categorias distintas e quantidade de urgências.",
            "pipeline": [
                {"$match": {**scope, "criado_em": {"$gte": recent}, "status": {"$in": ["aberto", "em_analise", "em_manutencao", "resolvido"]}}},
                {"$group": {"_id": "$localizacao.bloco", "total": {"$sum": 1}, "categorias": {"$addToSet": "$categoria"}, "urgentes": {"$sum": {"$cond": [{"$and": [{"$eq": ["$prioridade", 4]}, {"$ne": ["$status", "resolvido"]}]}, 1, 0]}}}},
                {"$project": {"_id": 0, "bloco": "$_id", "total": 1, "categorias": 1, "urgentes": 1}},
                {"$sort": {"total": -1, "bloco": 1}},
            ],
            "operadores": ["$match", "$gte", "$in", "$group", "$addToSet", "$cond", "$and", "$project"],
        },
    ]


def run_queries(collection, block=None):
    results = []
    for definition in query_definitions(block):
        if "pipeline" in definition:
            rows = list(collection.aggregate(definition["pipeline"]))
            source = {"aggregate": "ocorrencias", "pipeline": definition["pipeline"]}
        else:
            rows = list(collection.find(definition["filter"], definition["projection"]).sort(definition["sort"]))
            source = {"find": "ocorrencias", "filter": definition["filter"], "projection": definition["projection"], "sort": dict(definition["sort"])}
        results.append({key: definition[key] for key in ["id", "titulo", "tipo", "descricao", "operadores"]} | {"resultados": rows, "consulta": source})
    return results
