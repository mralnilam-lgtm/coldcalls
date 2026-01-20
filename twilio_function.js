/**
 * Twilio Function - Transfere apenas chamadas atendidas por humanos
 *
 * INSTRUÇÕES DE CONFIGURAÇÃO:
 *
 * 1. Acesse https://www.twilio.com/console/functions/overview
 * 2. Clique em "Create Service"
 * 3. Dê um nome (ex: "cold-calls-transfer")
 * 4. Clique em "Add" > "Add Function"
 * 5. Nomeie a função (ex: "/transfer")
 * 6. Cole este código
 * 7. Configure a variável de ambiente NUMERO_3CX no painel "Environment Variables"
 * 8. Clique em "Deploy All"
 * 9. Copie a URL da função e use como TWIML_BIN_URL no .env
 *
 * URL será algo como: https://cold-calls-transfer-XXXX.twil.io/transfer
 */

exports.handler = function(context, event, callback) {
    // Cria resposta TwiML
    const twiml = new Twilio.twiml.VoiceResponse();

    // Parâmetro AnsweredBy enviado pelo AMD (Answering Machine Detection)
    // Valores possíveis: human, machine_start, machine_end_beep,
    //                    machine_end_silence, machine_end_other, fax, unknown
    const answeredBy = event.AnsweredBy || 'unknown';
    const fromNumber = event.From || '';

    console.log(`Call from ${fromNumber} - AnsweredBy: ${answeredBy}`);

    // Só transfere se foi atendido por humano
    if (answeredBy === 'human') {
        console.log('Human detected - Transferring call to 3CX');

        // Número do 3CX configurado nas variáveis de ambiente
        const numero3cx = context.NUMERO_3CX;

        if (!numero3cx) {
            console.error('NUMERO_3CX environment variable not configured');
            twiml.say({ language: 'pt-BR' }, 'Erro de configuração. Tente novamente mais tarde.');
            twiml.hangup();
        } else {
            // Transfere a chamada mantendo o caller ID original
            const dial = twiml.dial({
                callerId: fromNumber,
                timeout: 30
            });
            dial.number(numero3cx);
        }
    } else {
        // Máquina/voicemail detectado - encerra a chamada
        console.log(`Machine/voicemail detected (${answeredBy}) - Hanging up`);
        twiml.hangup();
    }

    // Retorna o TwiML
    callback(null, twiml);
};
