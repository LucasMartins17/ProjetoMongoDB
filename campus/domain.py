"""Regras de negócio e validação, independentes da interface."""

from datetime import datetime, timezone
import math
import re
from urllib.parse import urlparse

CATEGORIES = ["Infraestrutura", "Elétrica", "Tecnologia", "Hidráulica", "Limpeza", "Acessibilidade"]
BLOCKS = {"A": "Salas de aula", "B": "Laboratórios", "C": "Biblioteca", "D": "Convivência", "E": "Administração"}
STATUSES = {"aberto": "Aberto", "em_analise": "Em análise", "em_manutencao": "Em manutenção", "resolvido": "Resolvido"}
PRIORITIES = {1: "Baixa", 2: "Média", 3: "Alta", 4: "Urgente"}


class ValidationError(ValueError):
    pass


def now_utc():
    value = datetime.now(timezone.utc)
    # BSON Date guarda milissegundos; a resposta do cadastro usa a mesma precisão.
    return value.replace(microsecond=(value.microsecond // 1000) * 1000)


def text_field(data, key, label, minimum=0, maximum=200):
    value = data.get(key, "")
    if not isinstance(value, str):
        raise ValidationError(f"{label}: informe um texto válido.")
    value = value.strip()
    if not minimum <= len(value) <= maximum:
        raise ValidationError(f"{label}: use de {minimum} a {maximum} caracteres.")
    return value


def validate_occurrence(data):
    if not isinstance(data, dict):
        raise ValidationError("Envie os campos da ocorrência em um objeto JSON.")
    result = {
        "titulo": text_field(data, "titulo", "Título", 5, 120),
        "descricao": text_field(data, "descricao", "Descrição", 10, 3000),
        "categoria": text_field(data, "categoria", "Categoria"),
        "status": text_field(data, "status", "Situação"),
        "responsavel": text_field(data, "responsavel", "Responsável", 0, 100),
    }
    if result["categoria"] not in CATEGORIES:
        raise ValidationError("Selecione uma categoria válida.")
    if result["status"] not in STATUSES:
        raise ValidationError("Selecione uma situação válida.")
    priority = data.get("prioridade")
    if type(priority) is not int or priority not in PRIORITIES:
        raise ValidationError("A prioridade deve ser um número inteiro de 1 a 4.")
    result["prioridade"] = priority
    location = data.get("localizacao")
    if not isinstance(location, dict) or location.get("bloco") not in BLOCKS:
        raise ValidationError("Selecione um bloco válido.")
    floor = location.get("andar")
    if type(floor) is not int or not 0 <= floor <= 10:
        raise ValidationError("O andar deve ser um inteiro entre 0 e 10.")
    result["localizacao"] = {
        "bloco": location["bloco"],
        "sala": text_field(location, "sala", "Sala ou referência", 1, 100),
        "andar": floor,
    }
    requester = data.get("solicitante")
    if not isinstance(requester, dict):
        raise ValidationError("Informe os dados do solicitante.")
    name = text_field(requester, "nome", "Nome do solicitante", 2, 100)
    email = text_field(requester, "email", "E-mail", 5, 160).lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValidationError("Informe um e-mail válido.")
    result["solicitante"] = {"nome": name, "email": email}
    cost = data.get("custo_estimado", 0)
    if isinstance(cost, bool) or not isinstance(cost, (int, float)) or not math.isfinite(cost) or not 0 <= cost <= 100_000_000:
        raise ValidationError("O custo estimado deve estar entre R$ 0 e R$ 100.000.000.")
    result["custo_estimado"] = round(float(cost), 2)
    accessibility = data.get("acessibilidade", False)
    if type(accessibility) is not bool:
        raise ValidationError("O campo de acessibilidade deve ser verdadeiro ou falso.")
    result["acessibilidade"] = accessibility
    tags = data.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 8 or any(not isinstance(tag, str) or not 1 <= len(tag.strip()) <= 30 for tag in tags):
        raise ValidationError("Use até 8 tags, com no máximo 30 caracteres cada.")
    result["tags"] = list(dict.fromkeys(tag.strip().lower() for tag in tags))
    photos = data.get("fotos", [])
    if not isinstance(photos, list) or len(photos) > 3:
        raise ValidationError("Informe até 3 links de fotos.")
    for photo in photos:
        if not isinstance(photo, str) or len(photo) > 1000:
            raise ValidationError("Link da foto inválido.")
        url = urlparse(photo)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            raise ValidationError("Fotos precisam de links HTTP ou HTTPS válidos, sem credenciais.")
    result["fotos"] = photos
    return result


def serialize(value):
    """Converte BSON para JSON comum na API; exportação usa Extended JSON."""
    from bson import ObjectId

    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize(item) for item in value]
    return value
