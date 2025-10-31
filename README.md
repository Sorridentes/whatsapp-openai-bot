# 🤖 Chatbot WhatsApp com OpenAI e Evolution API

Um chatbot inteligente para WhatsApp que integra a Evolution API com a OpenAI para fornecer respostas automáticas e contextuais.

Um chatbot inteligente para WhatsApp que integra a Evolution API com a OpenAI para fornecer respostas automáticas e contextuais através de processamento assíncrono em lote.

## 🚀 Funcionalidades

- ✅ **Integração com Evolution API** para comunicação via WhatsApp
- ✅ **Respostas inteligentes** usando modelos avançados da OpenAI (GPT-4)
- ✅ **Processamento em lote assíncrono** para melhor performance
- ✅ **Suporte a múltiplos tipos de mídia**: áudio, imagem e documentos
- ✅ **Histórico de conversas** com limite configurável
- ✅ **Sistema de filas com Redis** para processamento escalável
- ✅ **Armazenamento flexível** com MongoDB e Supabase
- ✅ **Descriptografia de mídias** do WhatsApp
- ✅ **Filtro por números autorizados**
- ✅ **Webhook para recebimento de mensagens**
- ✅ **Interface web amigável**

## 🏗️ Arquitetura

Whatsapp -> Evolution API -> Webhook Flask -> Redis Queue -> Batch Processor -> OpenAI -> Response

## 📋 Pré-requisitos

- Python 3.8+
- Docker e Docker Compose
- Conta na [Evolution API](https://evolution-api.com/)
- Conta na [Supbase](https://supabase.com/)
- Chave API da [OpenAI](https://platform.openai.com/)
- Ngrok (para tunnel público) - opcional

## 🔧 Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/Sorridentes/whatsapp-openai-bot.git && cd whatsapp-openai-bot
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

- [Acesse ngrok.com](https://ngrok.com/)
- Faça download e descompacte
- Ou use o npm: npm install -g ngrok
- Gere um dominio

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
ngrok http --url=seu-dominio 8080
```

### 4. Configure o webhook na Evolution API

Use a URL do Ngrok (ex: https://abcd-1234.ngrok.io) para configurar o webhook:

## 🔌 API Endpoints

### GET /

- **Descrição**: Página inicial com informações do projeto
- **Resposta**: HTML com interface amigável

### POST /v1/webhook/whatsapp

- **Descrição**: Webhook para receber mensagens do WhatsApp
- **Payload**: JSON com dados da mensagem Evolution API
- **Respostas**:
  - 200: Mensagem foi saltada
  - 202: Mensagem foi enfilerada
  - 400: Requisição vazia
  - 403: Número não autorizado
  - 500: Erro interno do servidor

## 🔧 Desenvolvimento

### Executando em modo desenvolvimento
```bash
# Ambiente virtual
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Execução
python app.py
```

### Logs:

A aplicação gera logs detalhados para:

- Mensagens recebidas/enviadas
- Erros de API
- Processamento em lote
- Números autorizados/não autorizados

### 🐛 Solução de Problemas

**Erro: "Número não autorizado"**

- Verifique se o número está na lista AUTHORIZED_NUMBERS no formato 511999999999

**Erro: "Falha na descriptografia de mídia"**

- Verifique se as chaves de mídia estão sendo recebidas corretamente
- Confirme as permissões de escrita na pasta static/

**Erro: "Erro ao criar mensagem"**

- Verifique se a chave da OpenAI está correta
- Confirme o Prompt ID na OpenAI

**Erro: "Erro ao enviar mensagem"**

- Verifique a configuração da Evolution API
- Confirme se a instância está ativa

## ⚠️ Avisos Importantes
- Configure corretamente as permissões de números autorizados

## 📞 Suporte
Em caso de problemas:

1. Verifique os logs em app_debug.log
2. Confirme todas as configurações de ambiente
3. Verifique a documentação das APIs:
  * Evolution API Docs
  * OpenAI API Docs

***Desenvolvido com ❤️ para automação inteligente no WhatsApp***
