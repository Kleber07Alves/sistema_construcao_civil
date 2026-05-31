# Sistema de Gestão — Construção Civil

MVP funcional baseado na documentação do projeto: Core, Logístico, RH, Alertas e Dashboard.

A proposta deste projeto é entregar uma versão simples, organizada e executável para estudos em ADS, mantendo os módulos e dados principais descritos no documento original.

## O que já funciona

- Backend FastAPI com documentação automática em `/docs`
- PostgreSQL via Docker Compose
- Autenticação JWT com perfis: `gestor`, `operador`, `rh`
- Hash de senha com `pbkdf2_sha256`, sem dependência de bcrypt/passlib, para evitar falha de login em Docker
- CRUD de usuários, obras, fornecedores, pedidos, vagas e candidatos
- Cálculo automático de média de atraso, taxa de atraso e desvio padrão por fornecedor
- Predição de risco de atraso por pedido com scikit-learn quando há histórico suficiente
- Regra de alerta: vermelho, amarelo e verde conforme probabilidade e prioridade
- Upload de currículo PDF com extração de texto usando PyMuPDF
- Extração simples de cargo, experiência e habilidades com spaCy/fallback local
- Ranking de candidatos por vaga
- Resumo automático local do candidato, com ponto de integração opcional para LLM
- Jobs diários com APScheduler
- Frontend Next.js com painel inicial, obras, logística e RH
- Dados de exemplo carregados automaticamente no primeiro uso

## Usuários de teste

| Perfil | E-mail | Senha |
|---|---|---|
| Gestor | gestor@empresa.com | 123456 |
| Operador | operador@empresa.com | 123456 |
| RH | rh@empresa.com | 123456 |

## Como rodar pelo Docker

Na pasta raiz do projeto, execute:

```bash
docker compose up --build
```

Se você já rodou uma versão anterior e o login não carregou dados, limpe o volume antigo do banco e suba novamente:

```bash
docker compose down -v
docker compose up --build
```

Depois acesse:

- Frontend: http://localhost:3000
- Backend/API: http://localhost:8000
- Swagger/FastAPI: http://localhost:8000/docs
- PostgreSQL: porta 5432

## Como rodar somente o backend localmente

Use este modo caso queira estudar o código aos poucos.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Por padrão, o backend espera PostgreSQL. Para rodar sem Docker, defina a variável `DATABASE_URL` para o banco que deseja usar.

Exemplo PostgreSQL local:

```bash
set DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/construcao_civil
```

## Estrutura do projeto

```text
sistema_construcao_civil/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth.py
│   │   ├── seed.py
│   │   ├── jobs.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── core.py
│   │   │   ├── logistico.py
│   │   │   ├── rh.py
│   │   │   └── notificacoes.py
│   │   └── services/
│   │       ├── logistico_ml.py
│   │       ├── rh_nlp.py
│   │       └── notifications.py
│   └── requirements.txt
├── frontend/
│   ├── app/
│   ├── components/
│   └── lib/
└── docker-compose.yml
```

## Fluxo básico para testar

1. Entre no frontend em http://localhost:3000.
2. Clique para usar o login de demonstração.
3. Veja o painel inicial.
4. Acesse Logística para visualizar fornecedores, pedidos e alertas.
5. Acesse RH para ver vagas, candidatos e ranking.
6. Acesse a API em http://localhost:8000/docs para criar novos dados.

## Observações importantes

- O projeto foi feito como MVP educacional, então algumas partes foram simplificadas para facilitar o entendimento.
- O cálculo logístico funciona com dados históricos cadastrados. Com poucos dados, o sistema usa uma regra heurística simples; com histórico suficiente, usa scikit-learn.
- A integração com LLM foi deixada preparada, mas o sistema funciona sem chave paga. O resumo local permite usar o sistema imediatamente.
- O schema é criado automaticamente no startup pelo SQLAlchemy para facilitar o uso. Em um projeto profissional, o ideal seria evoluir com Alembic.

## Principais endpoints

### Autenticação

- `POST /auth/login`

### Core

- `GET /core/usuarios`
- `POST /core/usuarios`
- `GET /core/obras`
- `POST /core/obras`

### Logístico

- `GET /logistico/fornecedores`
- `POST /logistico/fornecedores`
- `GET /logistico/pedidos`
- `POST /logistico/pedidos`
- `PUT /logistico/pedidos/{pedido_id}/entregar`
- `POST /logistico/recalcular-alertas`
- `GET /logistico/alertas`
- `GET /logistico/dashboard`

### RH

- `GET /rh/vagas`
- `POST /rh/vagas`
- `GET /rh/candidatos`
- `POST /rh/candidatos`
- `POST /rh/candidatos/upload`
- `GET /rh/vagas/{vaga_id}/ranking`

### Notificações

- `GET /notificacoes/alertas-email`
- `POST /notificacoes/enviar-alertas-simulados`
