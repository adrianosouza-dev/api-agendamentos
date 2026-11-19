from decimal import Decimal


def test_saude(client):
    assert client.get("/saude").json() == {"status": "ok", "banco": "ok"}


def test_site_e_info(client):
    site = client.get("/")
    assert site.status_code == 200
    assert "text/html" in site.headers["content-type"]

    info = client.get("/info").json()
    assert info["abertura"] == "09:00"
    assert info["dias_funcionamento"] == [0, 1, 2, 3, 4, 5]
    assert info["demo"] is False


def test_login_com_senha_errada(client):
    resposta = client.post("/auth/login", data={"username": "admin", "password": "errada"})
    assert resposta.status_code == 401


def test_login_com_usuario_inexistente(client):
    resposta = client.post("/auth/login", data={"username": "ninguem", "password": "x"})
    assert resposta.status_code == 401


def test_criar_servico_exige_login(client):
    resposta = client.post("/servicos", json={"nome": "Corte", "duracao_minutos": 30, "preco": "35"})
    assert resposta.status_code == 401


def test_token_invalido(client):
    resposta = client.post(
        "/servicos",
        json={"nome": "Corte", "duracao_minutos": 30, "preco": "35"},
        headers={"Authorization": "Bearer token-falso"},
    )
    assert resposta.status_code == 401


def test_criar_e_listar_servicos(client, criar_servico):
    criar_servico("Corte", 30, "35.00")
    criar_servico("Barba", 20, "25.00")

    servicos = client.get("/servicos").json()  # rota pública, sem token
    assert [s["nome"] for s in servicos] == ["Barba", "Corte"]
    assert Decimal(str(servicos[1]["preco"])) == Decimal("35.00")


def test_servico_invalido(client, admin_headers):
    resposta = client.post(
        "/servicos",
        json={"nome": "Corte", "duracao_minutos": 0, "preco": "35"},
        headers=admin_headers,
    )
    assert resposta.status_code == 422


def test_atualizar_servico(client, admin_headers, criar_servico):
    servico = criar_servico()
    resposta = client.put(
        f"/servicos/{servico['id']}",
        json={"nome": "Corte degradê", "duracao_minutos": 45, "preco": "40.00"},
        headers=admin_headers,
    )
    assert resposta.status_code == 200
    assert resposta.json()["duracao_minutos"] == 45


def test_desativar_servico(client, admin_headers, criar_servico, segunda):
    servico = criar_servico()
    resposta = client.delete(f"/servicos/{servico['id']}", headers=admin_headers)
    assert resposta.status_code == 204

    assert client.get("/servicos").json() == []
    resposta = client.get(f"/horarios-livres?data={segunda}&servico_id={servico['id']}")
    assert resposta.status_code == 404
