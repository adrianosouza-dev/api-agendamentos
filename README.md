# API de Agendamentos para Barbearias

API REST para barbearias: o cliente consulta os horários livres e marca um atendimento, e o administrador gerencia os serviços e a agenda.

Feita com **Python + FastAPI**, banco de dados com **SQLModel** (SQLite local, Postgres em produção), login com **JWT** e testes automatizados com **pytest**.

## Funcionalidades

- Cadastro de serviços com duração e preço (corte 30 min, combo 60 min...)
- Cálculo automático dos horários livres de cada dia, conforme a duração do serviço
- Agendamento pelo cliente, com bloqueio de horários sobrepostos
- Painel do admin protegido por login: agenda do dia, cancelamentos, gestão de serviços
- Documentação interativa gerada automaticamente em `/docs`

## Regras de negócio

- Só é possível agendar dentro do horário e dos dias de funcionamento (configuráveis no `.env`)
- Horários seguem uma grade (por padrão, de 30 em 30 minutos)
- Um serviço não pode terminar depois do fechamento
- Não é possível agendar no passado. O "agora" usa o fuso da barbearia, e não o do servidor: servidores na nuvem normalmente rodam em UTC, 3 horas à frente de Brasília
- Dois atendimentos não podem se sobrepor, nem parcialmente (um combo das 10:00 às 11:00 bloqueia um corte às 10:30)
- Cancelar libera o horário, mas o registro continua no histórico. Desativar um serviço também não apaga os agendamentos antigos
- Telefone aceita qualquer formato ("(45) 99999-1234") e é guardado só com os números

## Endpoints

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| POST | `/auth/login` | Público | Login do admin, devolve o token |
| GET | `/servicos` | Público | Lista os serviços |
| POST | `/servicos` | Admin | Cria um serviço |
| PUT | `/servicos/{id}` | Admin | Altera um serviço |
| DELETE | `/servicos/{id}` | Admin | Desativa um serviço |
| GET | `/horarios-livres?data=&servico_id=` | Público | Horários disponíveis no dia |
| POST | `/agendamentos` | Público | Marca um horário |
| GET | `/agendamentos?data=` | Admin | Agenda (filtro opcional por dia) |
| GET | `/agendamentos/{id}` | Admin | Detalhes de um agendamento |
| PATCH | `/agendamentos/{id}/cancelar` | Admin | Cancela e libera o horário |

### Exemplo

```http
GET /horarios-livres?data=2026-11-16&servico_id=1
```
```json
{ "data": "2026-11-16", "servico_id": 1, "horarios": ["09:00", "09:30", "10:30"] }
```

```http
POST /agendamentos
{ "cliente_nome": "João", "cliente_telefone": "(45) 99999-1234", "servico_id": 1, "inicio": "2026-11-16T10:30:00" }
```

Respostas de erro: `400` horário fora das regras, `401` sem login, `404` não encontrado, `409` horário ocupado, `422` dados inválidos.

## Como rodar

Requer Python 3.10 ou mais novo.

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env         # Windows  (Linux/Mac: cp .env.example .env)
uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000/docs. Para usar as rotas de admin, clique em **Authorize** e entre com o usuário e a senha definidos no `.env`.

## Testes

```bash
pytest -v
```

Os testes usam um banco em memória e não dependem do seu `.env`. Eles também rodam automaticamente no GitHub Actions a cada push.

## Estrutura

```
app/
  main.py           cria a aplicação e registra as rotas
  config.py         configurações lidas do .env
  database.py       conexão com o banco
  models.py         tabelas e formatos de entrada/saída
  regras.py         regras de agenda (funções puras, sem banco)
  auth.py           hash de senha, JWT e proteção das rotas de admin
  routers/          rotas agrupadas por assunto
tests/              testes das regras e da API
```

As regras de horário ficam em `regras.py`, separadas das rotas e do banco. Assim dá pra testá-las isoladamente e reaproveitá-las se a API mudar de framework.

## Usando Postgres (Supabase)

1. No Supabase, clique em **Connect** e copie a connection string do **Session pooler**
2. Cole em `DATABASE_URL` no `.env` (ou nas variáveis de ambiente da hospedagem)

O driver (`psycopg`) já está no `requirements.txt`.

As tabelas são criadas automaticamente na primeira execução.

## Próximos passos

- **Concorrência**: se dois clientes confirmarem o mesmo horário no mesmo instante, ambos podem passar pela checagem. Em Postgres isso se resolve no próprio banco, com uma *exclusion constraint* sobre o intervalo de horário
- Vários barbeiros, cada um com a própria agenda
- Pausa para almoço e folgas em datas específicas
- Confirmação e lembrete por WhatsApp
- Migrations com Alembic e deploy com Docker
