# Sistema de Gestão — Construção Civil

MVP funcional de um sistema modular para gestão na construção civil, com foco em obras, logística de materiais, triagem de candidatos e alertas operacionais.

O projeto foi desenvolvido para fins acadêmicos no curso de Análise e Desenvolvimento de Sistemas, mantendo uma arquitetura simples o suficiente para estudo, mas já organizada com backend, frontend, banco de dados, autenticação, migrations e Docker.

---

## Visão geral

O sistema busca apoiar dois problemas principais em empresas de construção civil:

1. **Atrasos no recebimento de materiais**, por meio do controle de pedidos, fornecedores, histórico de entregas e alertas de risco.
2. **Dificuldade na triagem de mão de obra**, por meio do cadastro de vagas, candidatos, extração de dados de currículos e ranking de compatibilidade.

---

## Stack utilizada

### Backend

* Python 3.11
* FastAPI
* SQLAlchemy
* Alembic
* PostgreSQL
* Pydantic
* Pydantic Settings
* JWT com `python-jose`
* Pandas
* PyMuPDF
* spaCy
* APScheduler
* Pytest

### Frontend

* Next.js 14
* React
* TypeScript
* Recharts
* CSS global

### Infraestrutura

* Docker
* Docker Compose
* PostgreSQL em container

---

## Módulos do sistema

### Core

Responsável pela base administrativa do sistema.

Funcionalidades atuais:

* Cadastro de usuários
* Listagem de usuários
* Cadastro de obras
* Listagem de obras
* Controle de acesso por perfil

Perfis disponíveis:

* `gestor`
* `operador`
* `rh`

---

### Logístico

Responsável pelo controle de fornecedores, pedidos de materiais e alertas de atraso.

Funcionalidades atuais:

* Cadastro de fornecedores
* Listagem de fornecedores
* Edição de fornecedores
* Exclusão de fornecedores com regra de segurança
* Cadastro de histórico de entregas
* Cadastro de pedidos
* Listagem de pedidos
* Filtros por status, obra, fornecedor e nível de alerta
* Edição de pedidos
* Exclusão de pedidos pendentes
* Registro de entrega de pedidos
* Cálculo de média de atraso por fornecedor
* Cálculo de taxa de atraso por fornecedor
* Cálculo de desvio padrão por fornecedor
* Geração de alertas por nível:

  * verde
  * amarelo
  * vermelho
* Dashboard logístico com contagem de pedidos e alertas

---

### RH

Responsável por vagas, candidatos e ranking de compatibilidade.

Funcionalidades atuais:

* Cadastro de vagas
* Listagem de vagas
* Cadastro manual de candidatos
* Upload de currículo em PDF
* Extração de texto do currículo com PyMuPDF
* Extração simples de cargo, experiência e habilidades
* Ranking de candidatos por vaga
* Resumo local do candidato

Observação: a integração real com LLM ainda não está implementada. Atualmente existe configuração prevista para chave OpenAI, mas o resumo usado pelo sistema é local.

---

### Notificações

Responsável por alertas operacionais.

Funcionalidades atuais:

* Geração de e-mails simulados para alertas logísticos
* Endpoint para visualizar alertas de e-mail
* Endpoint para simular envio de alertas
* Job diário com APScheduler para recalcular alertas logísticos

Observação: o envio real por SMTP depende da configuração das variáveis de ambiente.

---

## Funcionalidades já implementadas

* Backend FastAPI com documentação automática em `/docs`
* Frontend Next.js com páginas de Dashboard, Obras, Logística e RH
* Banco PostgreSQL via Docker Compose
* Configurações centralizadas em `backend/app/config.py`
* Autenticação JWT
* Hash de senha com `pbkdf2_sha256`
* Controle de acesso por perfil
* Alembic configurado para versionamento do banco
* Migration inicial criada
* Lifespan configurado no FastAPI
* Seeds automáticos de dados iniciais
* CORS configurado com base na URL do frontend
* Módulo logístico com CRUD parcial/ampliado
* Módulo RH com cadastro, upload de currículo e ranking
* Módulo de notificações com simulação de alertas
* Teste unitário inicial para regras de alerta logístico

---

## Usuários de teste

| Perfil   | E-mail                                              | Senha  |
| -------- | --------------------------------------------------- | ------ |
| Gestor   | [gestor@empresa.com](mailto:gestor@empresa.com)     | 123456 |
| Operador | [operador@empresa.com](mailto:operador@empresa.com) | 123456 |
| RH       | [rh@empresa.com](mailto:rh@empresa.com)             | 123456 |

---

## Como rodar com Docker

### 1. Subir o banco de dados

Na raiz do projeto, execute:

```bash
docker compose up -d db
```

### 2. Aplicar as migrations do Alembic

Execute:

```bash
docker compose run --rm backend alembic upgrade head
```

Esse comando cria as tabelas no PostgreSQL com base nas migrations existentes.

### 3. Subir o sistema completo

Execute:

```bash
docker compose up --build
```

Depois acesse:

* Frontend: http://localhost:3000
* Backend/API: http://localhost:8000
* Swagger/FastAPI: http://localhost:8000/docs
* Health check: http://localhost:8000/health
* PostgreSQL: porta `5432`

---

## Como resetar o banco de dados

Use este comando quando quiser apagar o banco e recriar tudo do zero:

```bash
docker compose down -v
docker compose up -d db
docker compose run --rm backend alembic upgrade head
docker compose up --build
```

Atenção: `docker compose down -v` apaga o volume do PostgreSQL e remove os dados cadastrados.

---

## Como rodar somente o backend localmente

Use este modo caso queira estudar ou testar apenas a API.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Defina a variável de ambiente do banco:

```bash
set DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/construcao_civil
```

Aplique as migrations:

```bash
alembic upgrade head
```

Rode o backend:

```bash
uvicorn app.main:app --reload
```

Acesse:

```text
http://localhost:8000/docs
```

---

## Como rodar somente o frontend localmente

```bash
cd frontend
npm install
npm run dev
```

Acesse:

```text
http://localhost:3000
```

O frontend espera que o backend esteja rodando em:

```text
http://localhost:8000
```

Essa URL pode ser ajustada pela variável:

```text
NEXT_PUBLIC_API_URL
```

---

## Variáveis de ambiente

O projeto possui um arquivo `.env.example` como base.

Principais variáveis:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/construcao_civil
JWT_SECRET=troque_essa_chave_em_producao
ACCESS_TOKEN_EXPIRE_MINUTES=480
FRONTEND_URL=http://localhost:3000
ENVIRONMENT=development

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=alertas@empresa.com

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

NEXT_PUBLIC_API_URL=http://localhost:8000
```

Observação: em ambiente de produção, o `JWT_SECRET` deve ser alterado para uma chave forte.

---

## Estrutura do projeto

```text
sistema_construcao_civil/
├── backend/
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 20260604_001_initial_schema.py
│   ├── alembic.ini
│   ├── app/
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── jobs.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── seed.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── core.py
│   │   │   ├── logistico.py
│   │   │   ├── notificacoes.py
│   │   │   └── rh.py
│   │   └── services/
│   │       ├── logistico_ml.py
│   │       ├── notifications.py
│   │       └── rh_nlp.py
│   ├── tests/
│   │   └── test_logistico.py
│   ├── Dockerfile
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   ├── logistico/
│   │   │   └── page.tsx
│   │   ├── obras/
│   │   │   └── page.tsx
│   │   └── rh/
│   │       └── page.tsx
│   ├── lib/
│   │   └── api.ts
│   ├── Dockerfile
│   ├── package.json
│   └── tsconfig.json
├── docs/
│   └── api/
│       └── localhost_8000 - docs.pdf
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Fluxo básico para testar

1. Suba o banco.
2. Rode as migrations.
3. Suba backend e frontend.
4. Acesse o frontend em http://localhost:3000.
5. Entre com o login de demonstração.
6. Acesse o Dashboard.
7. Acesse Obras.
8. Acesse Logística.
9. Acesse RH.
10. Confira a documentação da API em http://localhost:8000/docs.

---

## Principais endpoints

### Saúde

* `GET /health`

### Autenticação

* `POST /auth/login`

### Core

* `GET /core/usuarios`
* `POST /core/usuarios`
* `GET /core/obras`
* `POST /core/obras`

### Logístico

* `GET /logistico/fornecedores`
* `POST /logistico/fornecedores`
* `PUT /logistico/fornecedores/{fornecedor_id}`
* `DELETE /logistico/fornecedores/{fornecedor_id}`
* `POST /logistico/historico`
* `GET /logistico/pedidos`
* `POST /logistico/pedidos`
* `PUT /logistico/pedidos/{pedido_id}`
* `DELETE /logistico/pedidos/{pedido_id}`
* `PUT /logistico/pedidos/{pedido_id}/entregar`
* `POST /logistico/recalcular-alertas`
* `GET /logistico/alertas`
* `GET /logistico/dashboard`

### RH

* `GET /rh/vagas`
* `POST /rh/vagas`
* `GET /rh/candidatos`
* `POST /rh/candidatos`
* `POST /rh/candidatos/upload`
* `GET /rh/vagas/{vaga_id}/ranking`

### Notificações

* `GET /notificacoes/alertas-email`
* `POST /notificacoes/enviar-alertas-simulados`

---

## Status atual do projeto

O projeto está em estágio de MVP funcional em evolução.

### Concluído ou parcialmente concluído

* Estrutura modular backend/frontend
* Autenticação JWT
* Banco PostgreSQL
* Configurações centralizadas
* Alembic configurado
* Migration inicial
* Dashboard
* Listagem de obras
* Módulo logístico com cadastro, filtros, alertas e ações
* Módulo RH com vagas, candidatos, upload e ranking
* Simulação de notificações
* Documentação automática via Swagger

### Ainda pendente

* Rodar migrations automaticamente no fluxo Docker
* Criar `tests/conftest.py`
* Criar testes de integração para autenticação, Core, Logístico e RH
* Corrigir cálculo logístico para tratar `NaN` no desvio padrão
* Ajustar regra para prioridade não inflar diretamente a probabilidade de atraso
* Melhorar ordenação dos alertas por severidade
* Finalizar CRUD completo no Core
* Finalizar CRUD completo no RH
* Melhorar serviço de notificações com `try/except`, logging e uso completo do `config.py`
* Criar página de Notificações no frontend
* Criar tela real de login
* Criar contexto global de autenticação no frontend
* Separar tipos TypeScript em `frontend/types`
* Integrar LLM real para resumo de candidatos
* Melhorar cobertura de testes
* Preparar configuração diferenciada para desenvolvimento e produção

---

## Observações importantes

* O sistema ainda é um MVP acadêmico, não uma versão final de produção.
* O frontend e o backend estão configurados em modo de desenvolvimento.
* O backend usa `--reload` no Dockerfile, adequado para desenvolvimento.
* O Alembic já existe, mas as migrations precisam ser aplicadas antes do backend operar em banco novo.
* O seed inicial roda no startup do backend e depende das tabelas já existirem.
* O resumo de candidatos ainda é local; a LLM real ainda não foi conectada.
* O SMTP é opcional; sem configuração, o envio de e-mails funciona apenas como simulação.

---

## Próximos passos recomendados

1. Ajustar o Docker para rodar `alembic upgrade head` antes de iniciar o backend.
2. Criar `tests/conftest.py`.
3. Criar testes de integração com `TestClient`.
4. Corrigir os bugs restantes do cálculo logístico.
5. Refatorar `services/notifications.py` para usar `config.py` e tratar falhas SMTP.
6. Completar CRUD de Core e RH.
7. Criar página de Notificações no frontend.
8. Criar tela de login real.
9. Separar tipos TypeScript duplicados.
