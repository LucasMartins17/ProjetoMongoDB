"""Aplicação Flask. Para executar localmente, use py app.py."""

# O comando pedido na atividade usa o Python Launcher do Windows. Se ele
# selecionar um Python sem as bibliotecas, reutiliza o ambiente deste projeto.
if __name__ == "__main__":
    from importlib.util import find_spec
    from pathlib import Path
    import subprocess
    import sys

    if any(find_spec(module) is None for module in ("flask", "pymongo")):
        local_python = Path(__file__).resolve().parent / ".venv" / "Scripts" / "python.exe"
        if local_python.is_file() and local_python.resolve() != Path(sys.executable).resolve():
            try:
                raise SystemExit(subprocess.call([str(local_python), str(Path(__file__).resolve()), *sys.argv[1:]]))
            except KeyboardInterrupt:
                raise SystemExit(0) from None
        raise SystemExit(
            "Instale as dependencias antes de iniciar:\n"
            "  py -m pip install -r requirements.txt\n"
            "Depois execute: py app.py"
        )

import os
import re
from datetime import datetime, timezone
from io import BytesIO

from bson import ObjectId, json_util
from flask import Flask, g, jsonify, render_template, request, send_file
from pymongo import ReturnDocument
from pymongo.errors import ConnectionFailure, OperationFailure, PyMongoError
from werkzeug.exceptions import BadRequest, HTTPException, UnsupportedMediaType

from campus.analytics import run_queries
from campus.database import Database
from campus.domain import BLOCKS, CATEGORIES, PRIORITIES, STATUSES, ValidationError, now_utc, serialize, validate_occurrence


def create_app(config=None):
    app = Flask(__name__, static_folder="public/static", static_url_path="/static")
    app.config.update(
        MONGO_URI=os.environ.get("MONGO_URI", "mongodb://localhost:27017"),
        MONGO_DB=os.environ.get("MONGO_DB", "resolve_campus"),
        MONGO_TIMEOUT=1500,
        MAX_CONTENT_LENGTH=64 * 1024,
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)
    db = Database(app.config["MONGO_URI"], app.config["MONGO_DB"], app.config["MONGO_TIMEOUT"])
    app.extensions["campus_db"] = db
    app.json.sort_keys = False

    def error(message, status=400, code="invalid_request"):
        return jsonify(error=message, code=code), status

    @app.before_request
    def require_database():
        if request.path.startswith("/api/"):
            # O ping e a preparação acontecem ANTES de qualquer rota de dados.
            db.ensure_ready()
            g.collection = db.occurrences
            if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                # O app usa JSON e mesma origem. Impede escrita por formulário de outro site.
                origin = request.headers.get("Origin")
                if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
                    return error("Origem da requisição não permitida.", 403)
                if request.method != "DELETE" and not request.is_json:
                    return error("Envie o corpo da requisição como JSON.", 415)

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https: http:; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        return response

    @app.errorhandler(ConnectionFailure)
    def offline(_exc):
        return error("Não foi possível conectar ao MongoDB. Ative o serviço MongoDB e clique em Tentar conexão.", 503, "mongo_offline")

    @app.errorhandler(OperationFailure)
    def operation_failure(exc):
        app.logger.error("MongoDB recusou uma operação (código %s).", exc.code)
        if exc.code == 121:
            return error("Os dados não atendem à validação da coleção MongoDB.", 400, "validation_error")
        return error("O MongoDB está acessível, mas recusou a operação. Confira as permissões do usuário e a configuração do banco.", 503, "mongo_unavailable")

    @app.errorhandler(PyMongoError)
    def database_failure(_exc):
        app.logger.exception("Falha na operação MongoDB")
        return error("A operação no MongoDB não pôde ser concluída. Verifique a conexão e tente novamente.", 503, "mongo_unavailable")

    @app.errorhandler(ValidationError)
    def validation_failure(exc):
        return error(str(exc), 400, "validation_error")

    @app.errorhandler(BadRequest)
    @app.errorhandler(UnsupportedMediaType)
    def invalid_json(_exc):
        return error("JSON inválido. Confira os dados enviados.")

    @app.errorhandler(HTTPException)
    def http_error(exc):
        return error("Recurso não encontrado." if exc.code == 404 else exc.description, exc.code)

    @app.get("/")
    def index():
        return render_template("index.html", categories=CATEGORIES, blocks=BLOCKS, statuses=STATUSES, priorities=PRIORITIES)

    @app.get("/api/status")
    def status():
        return jsonify(connected=True, database=app.config["MONGO_DB"], total=g.collection.count_documents({}))

    def object_id(value):
        if not ObjectId.is_valid(value):
            raise ValidationError("Identificador de ocorrência inválido.")
        return ObjectId(value)

    def block_filter():
        block = request.args.get("bloco", "")
        if block and block not in BLOCKS:
            raise ValidationError("Bloco inválido.")
        return block

    @app.get("/api/ocorrencias")
    def list_occurrences():
        filters = {}
        block = block_filter()
        if block:
            filters["localizacao.bloco"] = block
        for key, options in [("status", STATUSES), ("categoria", CATEGORIES)]:
            value = request.args.get(key, "")
            if value:
                if value not in options:
                    raise ValidationError(f"Filtro de {key} inválido.")
                filters[key] = value
        priority = request.args.get("prioridade", "")
        if priority:
            if priority not in {"1", "2", "3", "4"}:
                raise ValidationError("Prioridade inválida.")
            filters["prioridade"] = int(priority)
        search = request.args.get("busca", "").strip()
        if len(search) > 120:
            raise ValidationError("A busca deve ter até 120 caracteres.")
        if search:
            expression = {"$regex": re.escape(search), "$options": "i"}
            filters["$or"] = [{"titulo": expression}, {"descricao": expression}, {"localizacao.sala": expression}, {"tags": expression}]
        try:
            page = max(1, int(request.args.get("pagina", "1")))
        except ValueError:
            raise ValidationError("Página inválida.") from None
        size = 10
        total = g.collection.count_documents(filters)
        pages = max(1, (total + size - 1) // size)
        page = min(page, pages)
        projection = {"descricao": 0, "historico": 0, "fotos": 0, "solicitante": 0}
        rows = list(g.collection.find(filters, projection).sort([("criado_em", -1), ("_id", -1)]).skip((page - 1) * size).limit(size))
        return jsonify(items=serialize(rows), total=total, pagina=page, paginas=pages)

    @app.post("/api/ocorrencias")
    def create_occurrence():
        document = validate_occurrence(request.get_json())
        now = now_utc()
        document.update(criado_em=now, atualizado_em=now,
                        resolvido_em=now if document["status"] == "resolvido" else None,
                        historico=[{"status": document["status"], "data": now, "observacao": "Ocorrência cadastrada."}], demonstracao=False)
        document["_id"] = g.collection.insert_one(document).inserted_id
        return jsonify(serialize(document)), 201

    @app.get("/api/ocorrencias/<identifier>")
    def get_occurrence(identifier):
        document = g.collection.find_one({"_id": object_id(identifier)})
        if not document:
            return error("Ocorrência não encontrada.", 404)
        return jsonify(serialize(document))

    @app.put("/api/ocorrencias/<identifier>")
    def update_occurrence(identifier):
        payload = request.get_json()
        values = validate_occurrence(payload)
        oid = object_id(identifier)
        previous = g.collection.find_one({"_id": oid})
        if not previous:
            return error("Ocorrência não encontrada.", 404)
        # Controle otimista: uma segunda aba não sobrescreve uma edição mais nova.
        version = payload.get("versao")
        try:
            expected = datetime.fromisoformat(version.replace("Z", "+00:00")) if isinstance(version, str) else None
            if expected is None or expected.tzinfo is None:
                raise ValueError
        except ValueError:
            raise ValidationError("Reabra a ocorrência para carregar a versão atual antes de editar.") from None
        now = now_utc()
        # BSON armazena milissegundos. Garante versão diferente mesmo em edições rápidas.
        from datetime import timedelta
        now = max(now, previous["atualizado_em"] + timedelta(milliseconds=1))
        changed = values["status"] != previous["status"]
        values.update(atualizado_em=now, resolvido_em=(previous["resolvido_em"] or now) if values["status"] == "resolvido" else None)
        update = {"$set": values}
        if changed:
            update["$push"] = {"historico": {"status": values["status"], "data": now, "observacao": "Situação atualizada no painel."}}
        updated = g.collection.find_one_and_update({"_id": oid, "atualizado_em": expected.astimezone(timezone.utc)}, update, return_document=ReturnDocument.AFTER)
        if not updated:
            return error("Essa ocorrência foi alterada em outra janela. Feche e abra novamente para atualizar os dados.", 409, "conflict")
        return jsonify(serialize(updated))

    @app.delete("/api/ocorrencias/<identifier>")
    def delete_occurrence(identifier):
        result = g.collection.delete_one({"_id": object_id(identifier)})
        if not result.deleted_count:
            return error("Ocorrência não encontrada.", 404)
        return jsonify(deleted=True)

    @app.get("/api/painel")
    def dashboard():
        total = g.collection.count_documents({})
        active = g.collection.count_documents({"status": {"$ne": "resolvido"}})
        urgent = g.collection.count_documents({"status": {"$ne": "resolvido"}, "prioridade": 4})
        resolved = total - active
        grouped = {item["_id"]: item for item in g.collection.aggregate([
            {"$group": {"_id": "$localizacao.bloco", "total": {"$sum": 1}, "pendentes": {"$sum": {"$cond": [{"$ne": ["$status", "resolvido"]}, 1, 0]}}, "urgentes": {"$sum": {"$cond": [{"$and": [{"$eq": ["$prioridade", 4]}, {"$ne": ["$status", "resolvido"]}]}, 1, 0]}}}}
        ])}
        return jsonify(total=total, pendentes=active, urgentes=urgent, resolvidos=resolved,
                       blocos=[{"bloco": key, "nome": name, "total": grouped.get(key, {}).get("total", 0), "pendentes": grouped.get(key, {}).get("pendentes", 0), "urgentes": grouped.get(key, {}).get("urgentes", 0)} for key, name in BLOCKS.items()])

    @app.get("/api/consultas")
    def analytics():
        return jsonify(consultas=serialize(run_queries(g.collection, block_filter())))

    @app.get("/api/exportar")
    def export():
        # Exporta a coleção real com datas e ObjectIds preservados para o Compass.
        content = json_util.dumps(list(g.collection.find({}).sort("criado_em", -1)), ensure_ascii=False, indent=2)
        return send_file(BytesIO(content.encode("utf-8")), mimetype="application/json", as_attachment=True,
                         download_name="resolve-campus-ocorrencias.json")

    return app


app = create_app()


if __name__ == "__main__":
    try:
        app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
    finally:
        app.extensions["campus_db"].client.close()
