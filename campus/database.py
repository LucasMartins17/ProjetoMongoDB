"""Conexão real, validação BSON e preparação idempotente da base."""

from threading import Lock
from pymongo import ASCENDING, DESCENDING, MongoClient, UpdateOne
from pymongo.errors import CollectionInvalid
from .domain import BLOCKS, CATEGORIES, STATUSES, now_utc
from .seed import seed_documents

SCHEMA = {
    "bsonType": "object",
    "required": ["titulo", "descricao", "categoria", "localizacao", "prioridade", "status", "solicitante", "responsavel", "tags", "fotos", "custo_estimado", "acessibilidade", "criado_em", "atualizado_em", "resolvido_em", "historico", "demonstracao"],
    "properties": {
        "titulo": {"bsonType": "string", "minLength": 5, "maxLength": 120},
        "descricao": {"bsonType": "string", "minLength": 10, "maxLength": 3000},
        "categoria": {"enum": CATEGORIES},
        "localizacao": {"bsonType": "object", "required": ["bloco", "sala", "andar"], "properties": {
            "bloco": {"enum": list(BLOCKS)}, "sala": {"bsonType": "string"}, "andar": {"bsonType": "int", "minimum": 0, "maximum": 10},
        }},
        "prioridade": {"bsonType": "int", "minimum": 1, "maximum": 4},
        "status": {"enum": list(STATUSES)},
        "solicitante": {"bsonType": "object", "required": ["nome", "email"], "properties": {"nome": {"bsonType": "string"}, "email": {"bsonType": "string"}}},
        "responsavel": {"bsonType": "string"},
        "tags": {"bsonType": "array", "items": {"bsonType": "string"}, "maxItems": 8},
        "fotos": {"bsonType": "array", "items": {"bsonType": "string"}, "maxItems": 3},
        "custo_estimado": {"bsonType": ["double", "int", "long", "decimal"], "minimum": 0},
        "acessibilidade": {"bsonType": "bool"},
        "criado_em": {"bsonType": "date"},
        "atualizado_em": {"bsonType": "date"},
        "resolvido_em": {"bsonType": ["date", "null"]},
        "historico": {"bsonType": "array", "items": {"bsonType": "object", "required": ["status", "data", "observacao"], "properties": {"status": {"enum": list(STATUSES)}, "data": {"bsonType": "date"}, "observacao": {"bsonType": "string"}}}},
        "demonstracao": {"bsonType": "bool"},
    },
}


class Database:
    def __init__(self, uri, name, timeout=1500):
        self.client = MongoClient(uri, serverSelectionTimeoutMS=timeout, connectTimeoutMS=timeout,
                                  socketTimeoutMS=4000, tz_aware=True, connect=False)
        self.db = self.client[name]
        self.lock = Lock()
        self.prepared = False

    @property
    def occurrences(self):
        return self.db.ocorrencias

    def ensure_ready(self):
        # Sempre verifica o servidor; a flag abaixo só evita recriar índices.
        self.client.admin.command("ping")
        with self.lock:
            # A consulta do marcador também detecta remoção externa do banco.
            marker = self.db["_app_meta"].find_one({"_id": "initialization-v1"})
            if self.prepared and marker:
                return
            try:
                self.db.create_collection("ocorrencias", validator={"$jsonSchema": SCHEMA}, validationLevel="strict")
            except CollectionInvalid:
                self.db.command("collMod", "ocorrencias", validator={"$jsonSchema": SCHEMA}, validationLevel="strict")
            self.occurrences.create_index([("status", ASCENDING), ("prioridade", DESCENDING)])
            self.occurrences.create_index([("localizacao.bloco", ASCENDING), ("criado_em", DESCENDING)])
            self.occurrences.create_index([("categoria", ASCENDING)])
            if not marker:
                # IDs fixos e upsert tornam uma inicialização interrompida repetível.
                # Uma coleção já preenchida pelo usuário é preservada.
                if not self.occurrences.find_one({"demonstracao": {"$ne": True}}, {"_id": 1}):
                    self.occurrences.bulk_write([
                        UpdateOne({"_id": doc["_id"]}, {"$setOnInsert": doc}, upsert=True)
                        for doc in seed_documents()
                    ])
                self.db["_app_meta"].update_one({"_id": "initialization-v1"}, {"$setOnInsert": {
                    "criado_em": now_utc(), "versao": 1,
                    "descricao": "Inicialização concluída; não repor exemplos excluídos.",
                }}, upsert=True)
            self.prepared = True
