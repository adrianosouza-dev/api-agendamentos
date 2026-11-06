"""Regras de negócio da agenda.

Funções puras (sem banco de dados), fáceis de entender e de testar.
Todos os horários são "horário local da barbearia", sem fuso.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app import config


def agora_local() -> datetime:
    """Data e hora atuais no fuso da barbearia.

    Importante: servidores na nuvem normalmente rodam em UTC (3h à frente do Brasil).
    """
    return datetime.now(ZoneInfo(config.FUSO_HORARIO)).replace(tzinfo=None)


def para_horario_local(valor: datetime) -> datetime:
    """Converte um horário com fuso (ex.: ...-03:00 ou ...Z) para o horário local sem fuso."""
    if valor.tzinfo is None:
        return valor
    return valor.astimezone(ZoneInfo(config.FUSO_HORARIO)).replace(tzinfo=None)


def conflita(inicio_a: datetime, fim_a: datetime, inicio_b: datetime, fim_b: datetime) -> bool:
    """Dois intervalos se sobrepõem se um começa antes do outro terminar."""
    return inicio_a < fim_b and inicio_b < fim_a


def validar_horario(inicio: datetime, duracao_minutos: int, agora: datetime) -> None:
    """Levanta ValueError com uma mensagem amigável se o horário não puder ser agendado."""
    if inicio <= agora:
        raise ValueError("Não é possível agendar em um horário que já passou")

    if inicio.weekday() not in config.DIAS_FUNCIONAMENTO:
        raise ValueError("A barbearia não abre nesse dia")

    abertura = datetime.combine(inicio.date(), config.HORA_ABERTURA)
    fechamento = datetime.combine(inicio.date(), config.HORA_FECHAMENTO)
    fim = inicio + timedelta(minutes=duracao_minutos)
    if inicio < abertura or fim > fechamento:
        raise ValueError(
            f"Fora do horário de funcionamento "
            f"({config.HORA_ABERTURA:%H:%M} às {config.HORA_FECHAMENTO:%H:%M})"
        )

    minutos_desde_abertura = (inicio - abertura).total_seconds() / 60
    if minutos_desde_abertura % config.INTERVALO_MINUTOS != 0:
        raise ValueError(f"Os horários começam a cada {config.INTERVALO_MINUTOS} minutos")


def horarios_livres(
    dia: date,
    duracao_minutos: int,
    ocupados: list[tuple[datetime, datetime]],
    agora: datetime,
) -> list[datetime]:
    """Lista os horários de início disponíveis em um dia para um serviço."""
    if dia.weekday() not in config.DIAS_FUNCIONAMENTO:
        return []

    abertura = datetime.combine(dia, config.HORA_ABERTURA)
    fechamento = datetime.combine(dia, config.HORA_FECHAMENTO)
    passo = timedelta(minutes=config.INTERVALO_MINUTOS)
    duracao = timedelta(minutes=duracao_minutos)

    livres = []
    atual = abertura
    while atual + duracao <= fechamento:
        fim = atual + duracao
        ocupado = any(conflita(atual, fim, inicio, termino) for inicio, termino in ocupados)
        if atual > agora and not ocupado:
            livres.append(atual)
        atual += passo
    return livres
