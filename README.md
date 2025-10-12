# 🤖 Chatbot WhatsApp com OpenAI e Evolution API

Um chatbot inteligente para WhatsApp que integra a Evolution API com a OpenAI para fornecer respostas automáticas e contextuais.

## 🚀 Funcionalidades

- ✅ Integração com Evolution API para WhatsApp
- ✅ Respostas inteligentes usando OpenAI
- ✅ Histórico de conversas limitado (últimas 6 mensagens)
- ✅ Filtro por números autorizados
- ✅ Webhook para recebimento de mensagens
- ✅ Interface web amigável

## 📋 Pré-requisitos

- Python 3.8+
- Conta na Evolution API
- Chave API da OpenAI
- Ngrok (para tunnel público)

## 🔧 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/Sorridentes/whatsapp-openai-bot.git
cd seu-projeto
```

### 2. Crie um ambiente virtual

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

## ⚙️ Configuração

### 1. Copia das variáveis de ambiente (.env.example)

Copie o arquivo .env.example e mude o nome

```bash
cp .env.example .env
```

Obs: Edite os valores com os seus dados

## 🌐 Uso com Ngrok

### 1. Instale o Ngrok

- Acesse ngrok.com
- Faça download e descompacte
- Ou use o npm: npm install -g ngrok

### 2. Autentique o Ngrok

```bash
ngrok authtoken seu-token-aqui
```

### 3. Execute a aplicação

Terminal 1 - Aplicação Flask:

```bash
python app.py
```

Terminal 2 - Ngrok:

```bash
ngrok http 80
```

### 4. Configure o webhook na Evolution API

Use a URL do Ngrok (ex: https://abcd-1234.ngrok.io) para configurar o webhook:

## 🔌 API Endpoints

GET /

- Descrição: Página inicial com informações do projeto
- Resposta: HTML com interface amigável

POST /v1/webhook/whatsapp

- Descrição: Webhook para receber mensagens do WhatsApp
- Payload: JSON com dados da mensagem Evolution API
- Respostas:
  - 200: Mensagem processada com sucesso
  - 400: Requisição vazia
  - 403: Número não autorizado
  - 500: Erro interno do servidor

## 🔧 Desenvolvimento

### Logs:

A aplicação gera logs detalhados para:

- Mensagens recebidas/enviadas
- Erros de API
- Números autorizados/não autorizados

### 🐛 Solução de Problemas

Erro comum: "Número não autorizado"

- Verifique se o número está na lista AUTHORIZED_NUMBERS no formato 511999999999

Erro comum: "Erro ao criar mensagem"

- Verifique se a chave da OpenAI está correta
- Confirme o Prompt ID na OpenAI

Erro comum: "Erro ao enviar mensagem"

- Verifique a configuração da Evolution API
- Confirme se a instância está ativa

Nota: Lembre-se de nunca commitar chaves de API ou informações sensíveis no repositório! Use sempre variáveis de ambiente.
