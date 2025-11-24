# Cold Calls Twilio - PythonAnywhere

Script Python para realizar cold calls automatizados usando Twilio, otimizado para rodar no PythonAnywhere (conta gratuita).

## Características

- ✅ Lê números de arquivo `numbers.txt`
- ✅ Usa polling de status (sem necessidade de webhooks)
- ✅ Conecta automaticamente ao 3CX quando atender
- ✅ Logging detalhado com timestamps
- ✅ Tratamento de erros robusto
- ✅ Delay configurável entre chamadas
- ✅ Relatório final com estatísticas

## Configuração

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar TwiML Bin no Twilio

1. Acesse https://www.twilio.com/console/twiml-bins
2. Clique em **Create new TwiML Bin**
3. Nome: `3CX Cold Calls`
4. Cole o conteúdo de [twiml_bin.xml](twiml_bin.xml)
5. **IMPORTANTE**: Substitua `SEU_NUMERO_3CX_AQUI` pelo número de entrada do seu 3CX (formato E.164)
   - Exemplo: `+551141234567` (São Paulo)
6. Clique em **Create**
7. Copie a URL gerada (ex: `https://handler.twilio.com/twiml/EHxxxx...`)

### 3. Configurar variáveis de ambiente

#### No Linux/Mac (terminal local):
```bash
export TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export TWILIO_PHONE_NUMBER=+15551234567
export TWIML_BIN_URL=https://handler.twilio.com/twiml/EHxxxx...
```

#### No PythonAnywhere:

1. Vá para a aba **Files** e edite o arquivo `.bashrc`:
```bash
nano ~/.bashrc
```

2. Adicione no final do arquivo:
```bash
export TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export TWILIO_PHONE_NUMBER=+15551234567
export TWIML_BIN_URL=https://handler.twilio.com/twiml/EHxxxx...
```

3. Salve e recarregue:
```bash
source ~/.bashrc
```

#### Alternativa: usar arquivo .env (opcional)

Copie `.env.example` para `.env` e preencha:
```bash
cp .env.example .env
nano .env
```

Então carregue antes de executar:
```bash
export $(cat .env | xargs)
```

### 4. Preparar lista de números

Edite o arquivo `numbers.txt` e adicione um número por linha no formato E.164:

```
+5511999999999
+5521988888888
+5531977777777
```

**Formato E.164**:
- Começa com `+`
- Código do país (Brasil: 55)
- DDD (2 dígitos)
- Número (8 ou 9 dígitos)
- Exemplo: `+5511987654321`

## Uso

### Execução básica

```bash
python cold_calls.py
```

### Parâmetros configuráveis

Edite a função `main()` no final do arquivo para ajustar:

```python
manager.run_campaign(
    numbers_file='numbers.txt',  # Arquivo com números
    delay=5                       # Delay entre chamadas (segundos)
)
```

## Fluxo de funcionamento

1. **Script inicia**: Carrega números e valida credenciais
2. **Para cada número**:
   - Inicia chamada via Twilio
   - Twilio executa o TwiML Bin
   - TwiML faz `<Dial>` para o 3CX com `callerId` do cliente original
   - Script faz polling do status a cada 2s
   - Quando finalizar (atendeu/não atendeu), loga resultado
   - Aguarda 5s e vai para próximo número
3. **Relatório final**: Exibe estatísticas da campanha

## Status das chamadas

| Status | Descrição | Ícone |
|--------|-----------|-------|
| `completed` | Chamada completada com sucesso | ✅ |
| `in-progress` | Chamada em andamento | ✅ |
| `no-answer` | Não atendeu | 📵 |
| `busy` | Ocupado | 🔇 |
| `failed` | Falha na chamada | ❌ |
| `canceled` | Chamada cancelada | 🚫 |

## Exemplo de saída

```
======================================================================
🤖 COLD CALLS TWILIO - PYTHONANYWHERE
======================================================================

[2025-11-24 10:30:15] Cliente Twilio inicializado
[2025-11-24 10:30:15] Número Twilio: +15551234567
[2025-11-24 10:30:15] TwiML URL: https://handler.twilio.com/twiml/EHxxxx...

[2025-11-24 10:30:15] 3 números carregados de numbers.txt

[2025-11-24 10:30:15] 🚀 Iniciando campanha com 3 números
[2025-11-24 10:30:15] Delay entre chamadas: 5s

======================================================================

======================================================================
[2025-11-24 10:30:15] Chamada 1/3
======================================================================

[2025-11-24 10:30:15] 📞 Iniciando chamada para +5511999999999
[2025-11-24 10:30:15]    Call SID: CAxxxxxxxxxxxxxxxxxxxxxxxxxxxx
[2025-11-24 10:30:16]    Status: queued
[2025-11-24 10:30:18]    Status: ringing
[2025-11-24 10:30:25]    Status: in-progress
[2025-11-24 10:30:55]    Status: completed
[2025-11-24 10:30:55] ✅ ATENDIDA: +5511999999999 (completed)
[2025-11-24 10:30:55]    SID: CAxxxxxxxxxxxxxxxxxxxxxxxxxxxx

[2025-11-24 10:30:55] ⏸️  Aguardando 5s antes da próxima chamada...

======================================================================
[2025-11-24 10:31:00] Chamada 2/3
======================================================================

[2025-11-24 10:31:00] 📞 Iniciando chamada para +5521988888888
[2025-11-24 10:31:00]    Call SID: CAyyyyyyyyyyyyyyyyyyyyyyyyyyyy
[2025-11-24 10:31:01]    Status: queued
[2025-11-24 10:31:03]    Status: ringing
[2025-11-24 10:31:33]    Status: no-answer
[2025-11-24 10:31:33] 📵 NÃO ATENDIDA: +5521988888888 (no-answer)
[2025-11-24 10:31:33]    SID: CAyyyyyyyyyyyyyyyyyyyyyyyyyyyy

======================================================================
[2025-11-24 10:31:38] 📊 RELATÓRIO FINAL DA CAMPANHA
======================================================================
Total de números: 3
✅ Atendidas (completed): 1
✅ Em andamento (in-progress): 0
📵 Sem resposta (no-answer): 2
🔇 Ocupado (busy): 0
❌ Falhas (failed): 0
🚫 Canceladas (canceled): 0

Taxa de sucesso: 33.3%
======================================================================
```

## Limitações do PythonAnywhere (conta gratuita)

- ✅ **Polling**: Funciona perfeitamente (não precisa de webhooks)
- ✅ **API Twilio**: Apenas requisições HTTPS de saída (permitido)
- ⚠️ **Tempo de execução**: Máximo 100 segundos por requisição web
  - Para scripts via console/scheduled tasks: sem limite
  - **Recomendação**: Execute via console Bash, não via web app

## Execução no PythonAnywhere

### Via Console Bash (recomendado):

1. Acesse a aba **Consoles**
2. Inicie um **Bash console**
3. Carregue as variáveis de ambiente:
```bash
source ~/.bashrc
```
4. Execute o script:
```bash
cd ~/coldcalls
python cold_calls.py
```

### Via Scheduled Task (para automação):

1. Acesse a aba **Tasks**
2. Adicione um novo agendamento
3. Comando:
```bash
source ~/.bashrc && cd ~/coldcalls && python cold_calls.py
```
4. Configure horário desejado

## Troubleshooting

### Erro: "Variáveis de ambiente não encontradas"
```bash
source ~/.bashrc
echo $TWILIO_ACCOUNT_SID  # Deve mostrar seu SID
```

### Erro: "Arquivo numbers.txt não encontrado"
```bash
ls -la numbers.txt
pwd  # Confirme que está no diretório correto
```

### Chamadas não conectam ao 3CX
- Verifique se o número do 3CX no TwiML Bin está correto
- Confirme que o número está no formato E.164: `+5511XXXXXXXX`
- Teste manualmente ligando do Twilio para o 3CX

### Status sempre "failed"
- Verifique saldo da conta Twilio
- Confirme que o número Twilio está verificado
- Teste com um número conhecido que atende

## Custos Twilio (estimativa)

- Chamadas de saída (Brasil): ~$0.011/min
- 100 chamadas de 1 minuto: ~$1.10 USD
- Verifique preços atualizados: https://www.twilio.com/voice/pricing/br

## Segurança

⚠️ **NUNCA** commite credenciais no Git:
- `.env` já está no `.gitignore`
- Use variáveis de ambiente sempre que possível
- Rotacione tokens periodicamente

## Licença

MIT

## Suporte

Para dúvidas sobre:
- **Twilio**: https://support.twilio.com
- **PythonAnywhere**: https://help.pythonanywhere.com
- **Script**: Abra uma issue neste repositório
