"""Testes de regras críticas com MongoDB real em um banco temporário isolado.

Executar: python -m unittest discover -v
Nenhum teste altera o banco resolve_campus.
"""

from datetime import datetime
import unittest
from unittest.mock import patch
from uuid import uuid4

from bson import json_util
from pymongo.errors import ConnectionFailure, OperationFailure

from app import create_app
from campus.seed import seed_documents


def valid_payload():
    return {
        "titulo": "Projetor de teste sem imagem",
        "descricao": "O projetor não exibe imagem ao conectar o computador da sala.",
        "categoria": "Tecnologia", "prioridade": 3, "status": "aberto",
        "localizacao": {"bloco": "B", "sala": "Laboratório 02", "andar": 1},
        "solicitante": {"nome": "Pessoa de Teste", "email": "pessoa@example.com"},
        "responsavel": "", "tags": ["projetor", "laboratório"], "fotos": [],
        "custo_estimado": 250.5, "acessibilidade": False,
    }


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "MONGO_URI": "mongodb://127.0.0.1:1", "MONGO_DB": "resolve_campus_test_offline", "MONGO_TIMEOUT": 100})
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions["campus_db"].client.close()

    def test_offline_blocks_reads_writes_and_export_without_loading_examples(self):
        routes = [("GET", "/api/status"), ("GET", "/api/ocorrencias"), ("GET", "/api/painel"), ("GET", "/api/consultas"), ("GET", "/api/exportar"), ("POST", "/api/ocorrencias"), ("PUT", "/api/ocorrencias/660000000000000000000001"), ("DELETE", "/api/ocorrencias/660000000000000000000001")]
        with patch("campus.database.seed_documents") as seed:
            for method, path in routes:
                with self.subTest(method=method, path=path):
                    result = self.client.open(path, method=method, json=valid_payload())
                    self.assertEqual(result.status_code, 503)
                    self.assertEqual(result.json["code"], "mongo_offline")
                    self.assertNotIn("items", result.json)
            seed.assert_not_called()

    def test_initial_html_is_available_without_database_and_has_no_records(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'id="app-shell" class="app-shell" hidden', response.data)
        self.assertNotIn(b"Vazamento no bebedouro", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store")


class ConnectedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.name = "resolve_campus_test_" + uuid4().hex
        cls.app = create_app({"TESTING": True, "MONGO_DB": cls.name})
        cls.db = cls.app.extensions["campus_db"]
        try:
            cls.db.ensure_ready()
        except ConnectionFailure:
            cls.db.client.close()
            raise unittest.SkipTest("Ative o MongoDB local para executar os testes de integração.")
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        if not cls.name.startswith("resolve_campus_test_"):
            raise RuntimeError("Limpeza permitida somente no banco temporário dos testes.")
        cls.db.client.drop_database(cls.name)
        cls.db.client.close()

    def setUp(self):
        self.db.occurrences.delete_many({})
        self.db.occurrences.insert_many(seed_documents())

    def test_bootstrap_creates_typed_documents_schema_and_indexes(self):
        self.assertEqual(self.client.get("/api/status").json["total"], 30)
        sample = self.db.occurrences.find_one({})
        self.assertGreaterEqual(len(sample), 10)
        self.assertIsInstance(sample["criado_em"], datetime)
        self.assertIsInstance(sample["localizacao"], dict)
        self.assertIsInstance(sample["tags"], list)
        self.assertIsInstance(sample["prioridade"], int)
        info = self.db.db.command("listCollections", filter={"name": "ocorrencias"})
        self.assertIn("$jsonSchema", info["cursor"]["firstBatch"][0]["options"]["validator"])
        self.assertGreaterEqual(len(self.db.occurrences.index_information()), 4)

    def test_crud_persists_dates_history_and_preserves_fields(self):
        created = self.client.post("/api/ocorrencias", json=valid_payload())
        self.assertEqual(created.status_code, 201)
        document = created.json
        identifier = document["_id"]
        self.assertEqual(self.db.occurrences.count_documents({}), 31)
        self.assertIsNone(document["resolvido_em"])
        self.assertFalse(document["demonstracao"])
        self.assertEqual(self.client.get(f"/api/ocorrencias/{identifier}").json["titulo"], document["titulo"])
        payload = valid_payload() | {"status": "resolvido", "versao": document["atualizado_em"]}
        updated = self.client.put(f"/api/ocorrencias/{identifier}", json=payload)
        self.assertEqual(updated.status_code, 200)
        self.assertIsNotNone(updated.json["resolvido_em"])
        self.assertEqual(len(updated.json["historico"]), 2)
        self.assertEqual(updated.json["criado_em"], document["criado_em"])
        reopened = self.client.put(f"/api/ocorrencias/{identifier}", json=valid_payload() | {"versao": updated.json["atualizado_em"]})
        self.assertEqual(reopened.status_code, 200)
        self.assertIsNone(reopened.json["resolvido_em"])
        self.assertEqual(len(reopened.json["historico"]), 3)
        self.assertEqual(self.client.delete(f"/api/ocorrencias/{identifier}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/ocorrencias/{identifier}").status_code, 404)

    def test_concurrent_edit_does_not_overwrite_newer_version(self):
        created = self.client.post("/api/ocorrencias", json=valid_payload()).json
        url = f"/api/ocorrencias/{created['_id']}"
        original = valid_payload() | {"versao": created["atualizado_em"]}
        first = self.client.put(url, json=original | {"titulo": "Título alterado na primeira aba"})
        self.assertEqual(first.status_code, 200)
        second = self.client.put(url, json=original | {"titulo": "Edição desatualizada da segunda aba"})
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self.client.get(url).json["titulo"], "Título alterado na primeira aba")

    def test_validation_rejects_bad_input_without_writing(self):
        invalid = [
            {"titulo": "abc"}, {"prioridade": True}, {"prioridade": 5}, {"status": "inventado"},
            {"localizacao": {"bloco": "Z", "sala": "Sala", "andar": 1}},
            {"localizacao": {"bloco": "A", "sala": "Sala", "andar": 0.5}},
            {"solicitante": {"nome": "Nome", "email": "sem-arroba"}},
            {"custo_estimado": -10}, {"acessibilidade": "sim"},
            {"fotos": ["javascript:alert(1)"]}, {"tags": ["a"] * 9},
        ]
        for change in invalid:
            with self.subTest(change=change):
                self.assertEqual(self.client.post("/api/ocorrencias", json=valid_payload() | change).status_code, 400)
        self.assertEqual(self.db.occurrences.count_documents({}), 30)

    def test_invalid_json_and_identifiers_are_handled(self):
        self.assertEqual(self.client.post("/api/ocorrencias", data="{oops", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/api/ocorrencias", json=[]).status_code, 400)
        self.assertEqual(self.client.get("/api/ocorrencias/invalid").status_code, 400)
        self.assertEqual(self.client.get("/api/ocorrencias?pagina=abc").status_code, 400)

    def test_collection_schema_rejects_direct_invalid_bson(self):
        sample = seed_documents()[0]
        sample.pop("_id")
        sample["prioridade"] = "urgente"
        with self.assertRaises(OperationFailure) as raised:
            self.db.occurrences.insert_one(sample)
        self.assertEqual(raised.exception.code, 121)

    def test_filter_search_pagination_and_literal_regex(self):
        first = self.client.get("/api/ocorrencias").json
        second = self.client.get("/api/ocorrencias?pagina=2").json
        self.assertEqual(len(first["items"]), 10)
        self.assertEqual(first["total"], 30)
        self.assertFalse({item["_id"] for item in first["items"]} & {item["_id"] for item in second["items"]})
        filtered = self.client.get("/api/ocorrencias?bloco=B&categoria=Tecnologia").json
        self.assertGreater(filtered["total"], 0)
        self.assertTrue(all(item["localizacao"]["bloco"] == "B" and item["categoria"] == "Tecnologia" for item in filtered["items"]))
        self.assertEqual(self.client.get("/api/ocorrencias?busca=.*").json["total"], 0)
        self.assertGreater(self.client.get("/api/ocorrencias?busca=projetor").json["total"], 0)
        self.assertNotIn("solicitante", first["items"][0])

    def test_dashboard_counts_match_database(self):
        panel = self.client.get("/api/painel").json
        self.assertEqual(panel["total"], 30)
        self.assertEqual(panel["pendentes"] + panel["resolvidos"], panel["total"])
        self.assertEqual(sum(block["total"] for block in panel["blocos"]), 30)
        self.assertEqual(panel["urgentes"], self.db.occurrences.count_documents({"status": {"$ne": "resolvido"}, "prioridade": 4}))

    def test_four_real_queries_include_projections_aggregations_and_scope(self):
        response = self.client.get("/api/consultas")
        self.assertEqual(response.status_code, 200)
        queries = {query["id"]: query for query in response.json["consultas"]}
        self.assertEqual(len(queries), 4)
        urgent = queries["urgentes"]["resultados"]
        self.assertTrue(urgent)
        self.assertTrue(all(row["status"] != "resolvido" and (row["prioridade"] >= 3 or row["acessibilidade"]) for row in urgent))
        self.assertNotIn("descricao", urgent[0])
        self.assertEqual(sum(row["total"] for row in queries["categorias"]["resultados"]), 30)
        scoped = self.client.get("/api/consultas?bloco=B").json["consultas"]
        self.assertTrue(all(row["localizacao"]["bloco"] == "B" for row in scoped[0]["resultados"]))
        self.assertTrue(all(row["bloco"] == "B" for row in scoped[3]["resultados"]))
        self.assertTrue(all(row["media_horas"] >= 0 for row in queries["resolucao"]["resultados"]))

    def test_export_is_real_extended_json_and_restores_bson_types(self):
        response = self.client.get("/api/exportar")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.headers["Content-Disposition"])
        documents = json_util.loads(response.get_data(as_text=True))
        self.assertEqual(len(documents), 30)
        self.assertIsInstance(documents[0]["criado_em"], datetime)
        self.assertEqual(len(documents[0]), 18)

    def test_deleting_all_records_does_not_reseed_after_reconnection(self):
        self.db.occurrences.delete_many({})
        self.db.prepared = False  # Simula reinício do servidor da aplicação.
        self.assertEqual(self.client.get("/api/status").json["total"], 0)
        self.assertEqual(self.client.get("/api/painel").json["total"], 0)
        self.assertEqual(self.client.get("/api/consultas").status_code, 200)

    def test_existing_non_demo_documents_are_preserved_on_initialization(self):
        self.db.occurrences.delete_many({})
        created = self.client.post("/api/ocorrencias", json=valid_payload()).json
        self.db.db["_app_meta"].delete_many({})
        self.db.prepared = False
        self.assertEqual(self.client.get("/api/status").json["total"], 1)
        self.assertEqual(self.db.occurrences.find_one({})["titulo"], created["titulo"])

    def test_requests_from_other_origins_cannot_write(self):
        response = self.client.post("/api/ocorrencias", json=valid_payload(), headers={"Origin": "https://outro-site.example"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db.occurrences.count_documents({}), 30)


if __name__ == "__main__":
    unittest.main()
