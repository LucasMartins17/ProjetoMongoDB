"""Verificação real no Edge, usando MongoDB e banco de teste descartável.

Requer: pip install -r requirements-dev.txt
Execute a partir da raiz: python scripts/verificar_interface.py
"""

from pathlib import Path
import logging
import sys
from threading import Thread
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from bson import json_util
from playwright.sync_api import expect, sync_playwright
from pymongo import MongoClient
from werkzeug.serving import make_server
from app import create_app


def main():
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    name = "resolve_campus_test_browser_" + uuid4().hex
    app = create_app({"TESTING": True, "MONGO_DB": name, "MONGO_TIMEOUT": 250})
    database = app.extensions["campus_db"]
    original_client = database.client
    unavailable_client = MongoClient("mongodb://127.0.0.1:1", serverSelectionTimeoutMS=100, connectTimeoutMS=100, connect=False)
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    artifacts = Path("test-results")
    artifacts.mkdir(exist_ok=True)
    errors = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
            page = context.new_page()
            page.on("pageerror", lambda exc: errors.append(str(exc)))

            def screenshot(filename):
                # As capturas de documentação não incluem avisos temporários.
                page.locator("#toast-region").evaluate("element => element.replaceChildren()")
                page.screenshot(path=str(artifacts / filename), full_page=True, animations="disabled")

            # Desconexão real no cliente do app de teste; não desliga o serviço do usuário.
            database.client = unavailable_client
            page.goto(url)
            expect(page.locator("#connection-help")).to_be_visible()
            expect(page.locator("#app-shell")).to_be_hidden()
            expect(page.locator("#retry-connection")).to_be_enabled()
            assert not database.db.list_collection_names()
            screenshot("conexao-indisponivel.png")
            print("OK: sem MongoDB, não há registros, banco preparado ou ações liberadas.")

            database.client = original_client
            page.locator("#retry-connection").click()
            expect(page.locator("#app-shell")).to_be_visible(timeout=15000)
            expect(page.locator("#stat-total")).to_have_text("30")
            assert database.occurrences.count_documents({}) == 30
            screenshot("visao-geral.png")
            print("OK: conexão prepara 30 documentos e abre o painel.")

            page.locator('.map-building[data-block="B"]').click()
            expect(page.locator("#view-occurrences")).to_be_visible()
            expect(page.locator("#filter-block")).to_have_value("B")
            expect(page.locator("#occurrence-rows tr")).to_have_count(6)
            assert all("Bloco B" in text for text in page.locator("#occurrence-rows tr").all_text_contents())
            page.locator("#clear-filters").click()
            expect(page.locator("#occurrence-rows tr")).to_have_count(10)
            page.locator("#next-page").click()
            expect(page.locator("#page-info")).to_have_text("Página 2 de 3")

            page.get_by_role("button", name="Nova ocorrência", exact=True).click()
            form = page.locator("#occurrence-form")
            title = "Projetor do auditório - teste de interface"
            for field, value in {
                "titulo": title, "descricao": "Projetor não liga durante as atividades no auditório do bloco B.",
                "sala": "Auditório", "nome": "Pessoa de Teste", "email": "pessoa@example.com", "tags": "auditório, projetor", "custo_estimado": "350.50",
            }.items():
                form.locator(f'[name="{field}"]').fill(value)
            for field, value in {"categoria": "Tecnologia", "prioridade": "4", "bloco": "B"}.items():
                form.locator(f'[name="{field}"]').select_option(value)
            with page.expect_response(lambda response: response.request.method == "POST" and response.url.endswith("/api/ocorrencias")) as created:
                page.locator("#save-occurrence").click()
            assert created.value.status == 201
            identifier = created.value.json()["_id"]
            expect(page.locator("#occurrence-dialog")).not_to_be_visible()
            page.locator("#filter-search").fill(title)
            expect(page.locator("#occurrence-rows tr")).to_have_count(1)
            page.get_by_role("button", name=title, exact=True).click()
            expect(page.locator("#history-section")).to_be_visible()
            form.locator('[name="status"]').select_option("resolvido")
            form.locator('[name="responsavel"]').fill("Manutenção do campus")
            with page.expect_response(lambda response: response.request.method == "PUT") as updated:
                page.locator("#save-occurrence").click()
            assert updated.value.status == 200
            expect(page.locator("#occurrence-dialog")).not_to_be_visible()
            expect(page.locator("#occurrence-rows .status-resolvido")).to_be_visible()
            page.get_by_role("button", name=title, exact=True).click()
            expect(page.locator("#history-list li")).to_have_count(2)
            page.locator("#delete-occurrence").click()
            expect(page.locator("#delete-dialog")).to_be_visible()
            page.locator("#confirm-delete").click()
            expect(page.locator("#delete-dialog")).not_to_be_visible()
            expect(page.locator("#occurrence-dialog")).not_to_be_visible()
            expect(page.locator("#list-empty")).to_be_visible()
            assert database.occurrences.count_documents({}) == 30
            print("OK: mapa, filtros, paginação e CRUD com histórico funcionam pelo navegador.")

            page.locator('[data-view="queries"]').click()
            expect(page.locator(".query-card")).to_have_count(4)
            page.locator(".query-source summary").first.click()
            expect(page.locator(".query-source pre").first).to_be_visible()
            page.locator("#query-block").select_option("B")
            expect(page.locator(".query-card").nth(3).locator(".query-result")).not_to_contain_text("Bloco A")
            expect(page.locator(".query-card").nth(3).locator(".query-result")).to_contain_text("Bloco B")
            screenshot("consultas.png")
            with page.expect_download() as download_info:
                page.locator(".export-button").click()
            download = download_info.value
            data = json_util.loads(Path(download.path()).read_text(encoding="utf-8"))
            assert len(data) == 30
            print("OK: quatro consultas reais, código visível e download de Extended JSON.")

            page.set_viewport_size({"width": 390, "height": 844})
            page.locator('[data-view="overview"]').click()
            expect(page.locator("#view-overview")).to_be_visible()
            screenshot("celular.png")
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cls:e.className?.baseVal??e.className,width:e.getBoundingClientRect().width,right:e.getBoundingClientRect().right})).slice(0,20)")

            # Queda após uso: qualquer ação recebe 503 e a tela apaga os registros.
            database.client = unavailable_client
            page.get_by_role("button", name="Nova ocorrência", exact=True).click()
            expect(page.locator("#connection-gate")).to_be_visible(timeout=10000)
            expect(page.locator("#app-shell")).to_be_hidden()
            expect(page.locator("#recent-list")).to_be_empty()
            expect(page.locator("#occurrence-rows")).to_be_empty()
            expect(page.locator("#query-results")).to_be_empty()
            assert not page.evaluate("Object.keys(localStorage).length || Object.keys(sessionStorage).length")
            database.client = original_client
            page.locator("#retry-connection").click()
            expect(page.locator("#app-shell")).to_be_visible(timeout=15000)
            expect(page.locator("#stat-total")).to_have_text("30")
            print("OK: celular sem overflow; queda bloqueia e limpa a tela; reconexão preserva os dados.")
            assert not errors, errors
            print("OK: nenhum erro JavaScript. Capturas em test-results/.")
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=3)
        database.client = original_client
        if not name.startswith("resolve_campus_test_browser_"):
            raise RuntimeError("Banco de limpeza fora do prefixo de testes.")
        original_client.drop_database(name)
        original_client.close()
        unavailable_client.close()


if __name__ == "__main__":
    main()
