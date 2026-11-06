"""Testes das regras de negócio puras (sem API e sem banco)."""

from datetime import date, datetime

import pytest

from app.regras import conflita, horarios_livres, validar_horario

SEGUNDA = date(2030, 1, 7)
DOMINGO = date(2030, 1, 13)
ANTES = datetime(2000, 1, 1)  # um "agora" bem no passado


def hora(h, m=0, dia=SEGUNDA):
    return datetime(dia.year, dia.month, dia.day, h, m)


def test_datas_de_apoio_estao_certas():
    assert SEGUNDA.weekday() == 0
    assert DOMINGO.weekday() == 6


def test_conflita():
    assert conflita(hora(10), hora(11), hora(10, 30), hora(11, 30))
    assert not conflita(hora(9, 30), hora(10), hora(10), hora(11))  # encostar não é conflito


def test_dia_vazio_tem_todos_os_horarios():
    livres = horarios_livres(SEGUNDA, 30, [], ANTES)
    assert livres[0] == hora(9)
    assert livres[-1] == hora(18, 30)
    assert len(livres) == 20


def test_servico_longo_nao_passa_do_fechamento():
    livres = horarios_livres(SEGUNDA, 60, [], ANTES)
    assert livres[-1] == hora(18)


def test_domingo_fechado():
    assert horarios_livres(DOMINGO, 30, [], ANTES) == []


def test_horario_ocupado_some_da_lista():
    ocupados = [(hora(10), hora(11))]
    livres = horarios_livres(SEGUNDA, 30, ocupados, ANTES)
    assert hora(9, 30) in livres
    assert hora(10) not in livres
    assert hora(10, 30) not in livres
    assert hora(11) in livres


def test_servico_longo_nao_cabe_antes_de_um_ocupado():
    ocupados = [(hora(10), hora(11))]
    livres = horarios_livres(SEGUNDA, 60, ocupados, ANTES)
    assert hora(9) in livres
    assert hora(9, 30) not in livres  # terminaria 10:30, em cima do ocupado


def test_horarios_que_ja_passaram_nao_aparecem():
    agora = hora(12, 10)
    livres = horarios_livres(SEGUNDA, 30, [], agora)
    assert livres[0] == hora(12, 30)


@pytest.mark.parametrize(
    "inicio, duracao, mensagem",
    [
        (hora(9, dia=DOMINGO), 30, "não abre"),
        (hora(8, 30), 30, "Fora do horário"),
        (hora(18, 30), 60, "Fora do horário"),
        (hora(9, 15), 30, "a cada 30 minutos"),
    ],
)
def test_validar_horario_recusa(inicio, duracao, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        validar_horario(inicio, duracao, ANTES)


def test_validar_horario_recusa_passado():
    with pytest.raises(ValueError, match="já passou"):
        validar_horario(hora(10), 30, agora=hora(11))


def test_validar_horario_aceita():
    validar_horario(hora(18), 60, ANTES)  # termina exatamente no fechamento
