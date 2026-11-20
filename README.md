# API de Agendamentos para Barbearias

[![Testes](https://github.com/adrianosouza-dev/api-agendamentos/actions/workflows/testes.yml/badge.svg)](https://github.com/adrianosouza-dev/api-agendamentos/actions/workflows/testes.yml)

API REST para barbearias: o cliente consulta os horários livres e marca um atendimento, e o barbeiro gerencia os serviços e a agenda. Inclui um site de agendamento que consome a própria API.

**Demo online: https://api-agendamentos-u43c.onrender.com**

<p align="center">
  <img src="docs/demo.gif" width="320" alt="Cliente escolhe Corte + barba, sábado às 11:00, preenche nome e telefone e confirma; em seguida, na agenda do barbeiro, o agendamento de Marcos aparece às 11:00.">
</p>

## Teste em 1 minuto

1. Na [demo](https://api-agendamentos-u43c.onrender.com), escolha um serviço, um dia e um horário, e agende
2. Abra **Agenda do barbeiro** e clique em **Usar conta de demonstração** (usuário `demo`, senha `demo1234`): o seu agendamento aparece na agenda do dia
3. Explore a API em [`/docs`](https://api-agendamentos-u43c.onrender.com/docs): clique em **Authorize** com o mesmo login para testar as rotas de admin

Os dados são fictícios e voltam ao estado inicial todo dia.

## Tecnologias

- **Python 3.12 + FastAPI**: API REST com validação e documentação automáticas
- **SQLModel / SQLAlchemy**: Postgres em produção (Supabase), SQLite no desenvolvimento
- **Alembic**: migrations do banco, aplicadas automaticamente no deploy
- **JWT + bcrypt**: login do administrador
- **pytest + GitHub Actions**: testes a cada push, em SQLite e em Postgres
- **HTML, CSS e JavaScript puros**: site de agendamento servido pela própria API, sem build
- **Render + UptimeRobot**: hospedagem e monitoramento

## Decisões técnicas

**Regras de negócio separadas do framework.** As regras de agenda (horário de funcionamento, grade de horários, sobreposição) ficam em [`regras.py`](app/regras.py), como funções puras: sem banco e sem HTTP. Por isso são testadas isoladamente e não dependem do FastAPI.

**O banco também garante que não há horário duplicado.** Conferir se o horário está livre antes de salvar não basta: dois clientes confirmando ao mesmo tempo passariam os dois pela checagem. No Postgres, uma *exclusion constraint* recusa o segundo, e a API responde `409`. No site publicado, 8 pedidos simultâneos para o mesmo horário resultaram em um `201` e sete `409`. Detalhes em [Concorrência](#concorrência-dois-clientes-no-mesmo-horário).

**Fuso horário da barbearia, não do servidor.** Servidores na nuvem rodam em UTC, 3 horas à frente de Brasília. Sem cuidado, às 22h a API acharia que já é o dia seguinte. O "agora" e os horários com fuso (`...Z`, `-03:00`) são sempre convertidos para o fuso configurado.

**Migrations automáticas, inclusive para o banco antigo.** Ao subir, a API aplica as migrations pendentes. O banco de produção foi criado antes do Alembic; ele é reconhecido e marcado como já estando na primeira versão, sem recriar tabelas nem perder dados. O CI confere se as migrations batem com os modelos (`alembic check`).

**Testes nos dois bancos.** A cada push, o GitHub Actions roda os testes em SQLite e num Postgres 16 de verdade. Um dos testes reproduz a corrida com duas conexões simultâneas. Ele foi validado ao contrário: com a trava desligada, falha.

**Histórico preservado.** Cancelar um agendamento ou excluir um serviço só muda o status; nada é apagado. O horário é liberado, mas o registro continua.

**Segurança.** Senha com bcrypt; login com a mesma resposta e o mesmo tempo para usuário inexistente e senha errada (não revela quais usuários existem); em produção, a API se recusa a subir com a `SECRET_KEY` ou a senha de exemplo.

**Uma demo pública que se mantém sozinha.** Com `DEMO_MODO=true`, a API cria serviços e ocupa parte da agenda, oferece um login público e, todo dia, desfaz o que os visitantes mudaram. Um monitor chama `/saude`, que consulta o banco, a cada 5 minutos: isso evita que o Render desligue o servidor e que o Supabase pause o banco.

## Arquitetura

```mermaid
flowchart LR
    site["Site de agendamento<br/>(HTML, CSS e JS)"] -->|JSON| rotas
    docs["/docs<br/>(Swagger)"] -->|JSON| rotas
    subgraph API["API (FastAPI)"]
        rotas["Rotas<br/>routers/"] --> auth["Login e JWT<br/>auth.py"]
        rotas --> regras["Regras de agenda<br/>regras.py"]
        rotas --> modelos["Modelos<br/>models.py"]
    end
    modelos --> banco[("Postgres<br/>(SQLite no desenvolvimento)")]
    migrations["Migrations<br/>(Alembic)"] --> banco
```

## Funcionalidades

- Cadastro de serviços com duração e preço (corte 30 min, combo 60 min...)
- Cálculo automático dos horários livres de cada dia, conforme a duração do serviço
- Agendamento pelo cliente, com bloqueio de horários sobrepostos
- Agenda do barbeiro protegida por login: agendamentos do dia, valor previsto, cancelamentos, gestão de serviços
- Documentação interativa gerada automaticamente em `/docs`

## Regras de negócio

- Só é possível agendar dentro do horário e dos dias de funcionamento (configuráveis no `.env`)
- Horários seguem uma grade (por padrão, de 30 em 30 minutos)
- Um serviço não pode terminar depois do fechamento
- Não é possível agendar no passado, considerando o fuso da barbearia
- Dois atendimentos não podem se sobrepor, nem parcialmente (um combo das 10:00 às 11:00 bloqueia um corte às 10:30)
- Cancelar libera o horário, mas o registro continua no histórico. Desativar um serviço também não apaga os agendamentos antigos
- Telefone aceita qualquer formato ("(45) 99999-1234") e é guardado só com os números

## Endpoints

| Método | Rota | Acesso | O que faz |
|---|---|---|---|
| GET | `/` | Público | Site de agendamento |
| GET | `/saude` | Público | Healthcheck: API e banco respondendo |
| GET | `/info` | Público | Horário e dias de funcionamento |
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

Abra http://127.0.0.1:8000 para o site e http://127.0.0.1:8000/docs para a documentação. Para usar as rotas de admin, clique em **Authorize** e entre com o usuário e a senha definidos no `.env`.

Para ter dados de exemplo localmente, coloque `DEMO_MODO=true` no `.env`.

## Testes

```bash
pytest -v
```

Os testes usam um banco em memória e não dependem do seu `.env`.

Para rodar também no Postgres, aponte `TEST_DATABASE_URL` para um banco vazio, só para testes (ele é apagado a cada teste):

```bash
TEST_DATABASE_URL=postgresql://usuario:senha@localhost:5432/testes pytest -v
```

No GitHub Actions, a cada push, os testes rodam duas vezes: no SQLite e num Postgres 16. Na rodada do Postgres, o CI também confere se as migrations batem com os modelos (`alembic check`).

## Estrutura

```
app/
  main.py           cria a aplicação e registra as rotas
  config.py         configurações lidas do .env
  database.py       conexão com o banco e migrations
  models.py         tabelas e formatos de entrada/saída
  regras.py         regras de agenda (funções puras, sem banco)
  auth.py           hash de senha, JWT e proteção das rotas de admin
  demo.py           dados de exemplo da versão pública (modo demonstração)
  routers/          rotas agrupadas por assunto
  static/           site de agendamento (HTML, CSS e JS, sem build)
migrations/         migrations do banco (Alembic)
tests/              testes das regras, da API e do banco
docs/               imagens do README
```

## Usando Postgres (Supabase)

1. No Supabase, clique em **Connect** e copie a connection string do **Session pooler**
2. Cole em `DATABASE_URL` no `.env` (ou nas variáveis de ambiente da hospedagem)

O driver (`psycopg`) já está no `requirements.txt`.

Ao subir, a API aplica sozinha as migrations pendentes (o mesmo que `alembic upgrade head`), então um deploy novo atualiza o banco sem passo manual.

Por segurança, com Postgres a API se recusa a subir se `SECRET_KEY` ou `ADMIN_SENHA` ainda estiverem com os valores de exemplo.

## Migrations (Alembic)

A estrutura do banco é versionada em `migrations/versions/`. Para mudar um modelo:

```bash
alembic revision --autogenerate -m "descrição da mudança"   # gera a migration a partir dos modelos
# revise o arquivo gerado
alembic upgrade head                                         # aplica (a API também aplica ao subir)
```

Bancos criados antes do Alembic (pelo antigo `create_all`) são reconhecidos e marcados como já estando na primeira versão, sem recriar nada.

## Concorrência: dois clientes no mesmo horário

A API confere se o horário está livre antes de salvar. Mas, se dois clientes confirmarem o mesmo horário no mesmo instante, os dois consultam o banco, os dois veem o horário livre e os dois salvariam.

No Postgres, quem impede isso é o próprio banco, com uma *exclusion constraint* (migration `0002`):

```sql
ALTER TABLE agendamento ADD CONSTRAINT agendamento_sem_sobreposicao
  EXCLUDE USING gist (tsrange(inicio, fim) WITH &&)
  WHERE (status = 'confirmado');
```

Ou seja: dois agendamentos confirmados não podem ter intervalos `[inicio, fim)` que se sobreponham. Os cancelados não contam, e 10:00–10:30 com 10:30–11:00 não conflitam. Quando o banco recusa, a API responde `409`, igual a um horário já ocupado.

O teste `test_dois_clientes_ao_mesmo_tempo` reproduz a corrida com duas conexões simultâneas: as duas veem o horário livre, e o banco aceita só uma.

## Versão pública (Render)

A demo roda no plano gratuito do Render com `DEMO_MODO=true`. Nesse modo:

- a API cria serviços e ocupa parte da agenda dos próximos 14 dias, sempre respeitando as regras de horário
- existe um login de admin público (`demo` / `demo1234`)
- na primeira requisição de cada dia, tudo volta ao estado inicial, desfazendo o que os visitantes mudaram

O plano gratuito desliga o servidor após 15 minutos sem acesso, e o primeiro acesso seguinte demora cerca de 1 minuto. Para evitar isso, um monitor externo gratuito (UptimeRobot) chama `/saude` a cada 5 minutos. Como o `/saude` consulta o banco, isso também impede que o Supabase pause o projeto por inatividade.

## Próximos passos

- Vários barbeiros, cada um com a própria agenda
- Pausa para almoço e folgas em datas específicas
- O cliente consultar e cancelar o próprio horário
- Confirmação e lembrete por WhatsApp
- Deploy com Docker
