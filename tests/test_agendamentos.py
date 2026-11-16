from datetime import timedelta


def agendar(client, servico_id, inicio, nome="Ana", telefone="(45) 99999-1234"):
    return client.post(
        "/agendamentos",
        json={
            "cliente_nome": nome,
            "cliente_telefone": telefone,
            "servico_id": servico_id,
            "inicio": inicio,
        },
    )


def test_horarios_livres_dia_vazio(client, criar_servico, segunda):
    servico = criar_servico()
    resposta = client.get(f"/horarios-livres?data={segunda}&servico_id={servico['id']}")
    assert resposta.status_code == 200
    horarios = resposta.json()["horarios"]
    assert horarios[0] == "09:00"
    assert horarios[-1] == "18:30"
    assert len(horarios) == 20


def test_agendar_com_sucesso(client, criar_servico, segunda):
    servico = criar_servico(duracao_minutos=30)
    resposta = agendar(client, servico["id"], f"{segunda}T10:00:00")

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["inicio"] == f"{segunda}T10:00:00"
    assert corpo["fim"] == f"{segunda}T10:30:00"
    assert corpo["status"] == "confirmado"
    assert corpo["cliente_telefone"] == "45999991234"  # guardado só com números


def test_horario_agendado_some_dos_livres(client, criar_servico, segunda):
    servico = criar_servico()
    agendar(client, servico["id"], f"{segunda}T10:00:00")

    horarios = client.get(f"/horarios-livres?data={segunda}&servico_id={servico['id']}").json()["horarios"]
    assert "10:00" not in horarios
    assert len(horarios) == 19


def test_mesmo_horario_duas_vezes(client, criar_servico, segunda):
    servico = criar_servico()
    assert agendar(client, servico["id"], f"{segunda}T10:00:00").status_code == 201
    resposta = agendar(client, servico["id"], f"{segunda}T10:00:00", nome="Bia")
    assert resposta.status_code == 409


def test_sobreposicao_parcial(client, criar_servico, segunda):
    combo = criar_servico("Corte + barba", 60, "55.00")
    corte = criar_servico("Corte", 30, "35.00")
    assert agendar(client, combo["id"], f"{segunda}T10:00:00").status_code == 201
    # 10:30 cai no meio do combo (10:00 às 11:00)
    assert agendar(client, corte["id"], f"{segunda}T10:30:00").status_code == 409
    assert agendar(client, corte["id"], f"{segunda}T11:00:00").status_code == 201


def test_horario_com_fuso_e_convertido(client, criar_servico, segunda):
    servico = criar_servico()
    # 13:00 em UTC = 10:00 em Brasília
    resposta = agendar(client, servico["id"], f"{segunda}T13:00:00Z")
    assert resposta.status_code == 201
    assert resposta.json()["inicio"] == f"{segunda}T10:00:00"


def test_regras_de_horario(client, criar_servico, segunda):
    servico = criar_servico()
    domingo = segunda + timedelta(days=6)
    casos = [
        "2020-01-06T10:00:00",  # passado
        f"{domingo}T10:00:00",  # domingo
        f"{segunda}T08:30:00",  # antes de abrir
        f"{segunda}T19:00:00",  # depois de fechar
        f"{segunda}T09:15:00",  # fora da grade de 30 min
    ]
    for inicio in casos:
        resposta = agendar(client, servico["id"], inicio)
        assert resposta.status_code == 400, inicio


def test_dados_invalidos(client, criar_servico, segunda):
    servico = criar_servico()
    assert agendar(client, servico["id"], f"{segunda}T10:00:00", telefone="123").status_code == 422
    assert agendar(client, servico["id"], f"{segunda}T10:00:00", nome="").status_code == 422
    assert agendar(client, servico["id"], f"{segunda}T10:00:00", nome="   ").status_code == 422
    assert agendar(client, 999, f"{segunda}T10:00:00").status_code == 404


def test_agenda_exige_login(client):
    assert client.get("/agendamentos").status_code == 401


def test_listar_agenda_do_dia(client, admin_headers, criar_servico, segunda):
    servico = criar_servico()
    agendar(client, servico["id"], f"{segunda}T11:00:00", nome="Bia")
    agendar(client, servico["id"], f"{segunda}T09:00:00", nome="Ana")
    agendar(client, servico["id"], f"{segunda + timedelta(days=1)}T09:00:00", nome="Caio")

    agenda = client.get(f"/agendamentos?data={segunda}", headers=admin_headers).json()
    assert [a["cliente_nome"] for a in agenda] == ["Ana", "Bia"]  # só o dia, em ordem


def test_cancelar_libera_horario(client, admin_headers, criar_servico, segunda):
    servico = criar_servico()
    agendamento = agendar(client, servico["id"], f"{segunda}T10:00:00").json()

    resposta = client.patch(f"/agendamentos/{agendamento['id']}/cancelar", headers=admin_headers)
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "cancelado"

    # cancelar de novo não faz sentido
    resposta = client.patch(f"/agendamentos/{agendamento['id']}/cancelar", headers=admin_headers)
    assert resposta.status_code == 409

    # o horário volta a ficar livre
    assert agendar(client, servico["id"], f"{segunda}T10:00:00", nome="Bia").status_code == 201

    # o cancelado continua no histórico
    todos = client.get(
        f"/agendamentos?data={segunda}&incluir_cancelados=true", headers=admin_headers
    ).json()
    assert len(todos) == 2
