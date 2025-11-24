#!/usr/bin/env python3
"""
Script de Cold Calls via Twilio otimizado para PythonAnywhere (conta gratuita)
Lê números de numbers.txt e realiza chamadas sequenciais com polling de status
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from twilio.rest import Client


def load_env_file(env_path='.env'):
    """
    Carrega variáveis de ambiente do arquivo .env

    Args:
        env_path: Caminho para o arquivo .env (padrão: .env)
    """
    env_file = Path(env_path)

    if not env_file.exists():
        return

    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()

            # Ignora linhas vazias e comentários
            if not line or line.startswith('#'):
                continue

            # Separa chave=valor
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Remove aspas se existirem
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                # Define a variável de ambiente se ainda não existir
                if key and not os.environ.get(key):
                    os.environ[key] = value


class ColdCallManager:
    """Gerenciador de chamadas cold call via Twilio"""

    def __init__(self):
        """Inicializa o cliente Twilio com credenciais do ambiente"""
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.twilio_number = os.environ.get('TWILIO_PHONE_NUMBER')
        self.twiml_bin_url = os.environ.get('TWIML_BIN_URL')

        # Validação de credenciais
        if not all([self.account_sid, self.auth_token, self.twilio_number, self.twiml_bin_url]):
            raise ValueError(
                "Required environment variables not found:\n"
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, TWIML_BIN_URL"
            )

        self.client = Client(self.account_sid, self.auth_token)
        print(f"[{self._timestamp()}] Twilio client initialized")
        print(f"[{self._timestamp()}] Twilio number: {self.twilio_number}")
        print(f"[{self._timestamp()}] TwiML URL: {self.twiml_bin_url}\n")

    @staticmethod
    def _timestamp():
        """Retorna timestamp formatado para logs"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def load_numbers(self, filename='numbers.txt'):
        """
        Carrega números do arquivo

        Args:
            filename: Nome do arquivo com números (padrão: numbers.txt)

        Returns:
            Lista de números no formato E.164
        """
        try:
            with open(filename, 'r') as f:
                numbers = [line.strip() for line in f if line.strip()]

            # Validação básica de formato E.164
            valid_numbers = []
            for num in numbers:
                if num.startswith('+') and len(num) >= 10:
                    valid_numbers.append(num)
                else:
                    print(f"[{self._timestamp()}] ⚠️  Invalid number ignored: {num}")

            print(f"[{self._timestamp()}] {len(valid_numbers)} numbers loaded from {filename}\n")
            return valid_numbers

        except FileNotFoundError:
            print(f"[{self._timestamp()}] ❌ File {filename} not found")
            sys.exit(1)
        except Exception as e:
            print(f"[{self._timestamp()}] ❌ Error reading file: {e}")
            sys.exit(1)

    def make_call(self, to_number):
        """
        Inicia uma chamada e faz polling do status

        Args:
            to_number: Número de destino no formato E.164

        Returns:
            Status final da chamada
        """
        print(f"[{self._timestamp()}] 📞 Initiating call to {to_number}")

        try:
            # Inicia a chamada
            call = self.client.calls.create(
                to=to_number,
                from_=self.twilio_number,
                url=self.twiml_bin_url,
                timeout=60,
                status_callback_method='GET',
                status_callback_event=['completed']
            )

            call_sid = call.sid
            print(f"[{self._timestamp()}]    Call SID: {call_sid}")

            # Polling do status da chamada
            status = self._poll_call_status(call_sid)

            # Log do resultado
            self._log_call_result(to_number, call_sid, status)

            return status

        except Exception as e:
            print(f"[{self._timestamp()}] ❌ Error initiating call to {to_number}: {e}")
            return 'failed'

    def _poll_call_status(self, call_sid, max_wait=70, poll_interval=2):
        """
        Faz polling do status da chamada até finalizar ou timeout

        Args:
            call_sid: SID da chamada
            max_wait: Tempo máximo de espera em segundos (padrão: 70s)
            poll_interval: Intervalo entre verificações em segundos (padrão: 2s)

        Returns:
            Status final da chamada
        """
        elapsed = 0
        last_status = None

        while elapsed < max_wait:
            try:
                call = self.client.calls(call_sid).fetch()
                current_status = call.status

                # Log apenas quando status mudar
                if current_status != last_status:
                    print(f"[{self._timestamp()}]    Status: {current_status}")
                    last_status = current_status

                # Status finais da chamada
                if current_status in ['completed', 'failed', 'busy', 'no-answer', 'canceled']:
                    return current_status

                # Aguarda antes da próxima verificação
                time.sleep(poll_interval)
                elapsed += poll_interval

            except Exception as e:
                print(f"[{self._timestamp()}] ⚠️  Polling error: {e}")
                time.sleep(poll_interval)
                elapsed += poll_interval

        print(f"[{self._timestamp()}]    ⏱️  Polling timeout")
        return last_status or 'unknown'

    def _log_call_result(self, to_number, call_sid, status):
        """
        Loga o resultado da chamada

        Args:
            to_number: Número de destino
            call_sid: SID da chamada
            status: Status final da chamada
        """
        status_icons = {
            'completed': '✅',
            'in-progress': '✅',
            'no-answer': '📵',
            'busy': '🔇',
            'failed': '❌',
            'canceled': '🚫'
        }

        icon = status_icons.get(status, '❓')

        if status in ['completed', 'in-progress']:
            print(f"[{self._timestamp()}] {icon} ANSWERED: {to_number} ({status})")
        else:
            print(f"[{self._timestamp()}] {icon} NOT ANSWERED: {to_number} ({status})")

        print(f"[{self._timestamp()}]    SID: {call_sid}\n")

    def run_campaign(self, numbers_file='numbers.txt', delay=5):
        """
        Executa campanha de cold calls

        Args:
            numbers_file: Arquivo com números (padrão: numbers.txt)
            delay: Delay entre chamadas em segundos (padrão: 5s)
        """
        numbers = self.load_numbers(numbers_file)

        if not numbers:
            print(f"[{self._timestamp()}] ⚠️  No valid numbers found")
            return

        print(f"[{self._timestamp()}] 🚀 Starting campaign with {len(numbers)} numbers")
        print(f"[{self._timestamp()}] Delay between calls: {delay}s\n")
        print("=" * 70)

        stats = {
            'total': len(numbers),
            'completed': 0,
            'in-progress': 0,
            'no-answer': 0,
            'busy': 0,
            'failed': 0,
            'canceled': 0,
            'unknown': 0
        }

        for idx, number in enumerate(numbers, 1):
            print(f"\n{'=' * 70}")
            print(f"[{self._timestamp()}] Call {idx}/{len(numbers)}")
            print(f"{'=' * 70}\n")

            status = self.make_call(number)

            # Atualiza estatísticas
            if status in stats:
                stats[status] += 1
            else:
                stats['unknown'] += 1

            # Aguarda antes da próxima chamada (exceto na última)
            if idx < len(numbers):
                print(f"[{self._timestamp()}] ⏸️  Waiting {delay}s before next call...")
                time.sleep(delay)

        # Relatório final
        self._print_final_report(stats)

    def _print_final_report(self, stats):
        """
        Imprime relatório final da campanha

        Args:
            stats: Dicionário com estatísticas
        """
        print("\n" + "=" * 70)
        print(f"[{self._timestamp()}] 📊 FINAL CAMPAIGN REPORT")
        print("=" * 70)
        print(f"Total numbers: {stats['total']}")
        print(f"✅ Answered (completed): {stats['completed']}")
        print(f"✅ In progress (in-progress): {stats['in-progress']}")
        print(f"📵 No answer (no-answer): {stats['no-answer']}")
        print(f"🔇 Busy (busy): {stats['busy']}")
        print(f"❌ Failed (failed): {stats['failed']}")
        print(f"🚫 Canceled (canceled): {stats['canceled']}")
        if stats['unknown'] > 0:
            print(f"❓ Unknown status: {stats['unknown']}")

        success_rate = ((stats['completed'] + stats['in-progress']) / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"\nSuccess rate: {success_rate:.1f}%")
        print("=" * 70)


def main():
    """Função principal"""
    # Carrega variáveis de ambiente do arquivo .env (se existir)
    load_env_file('.env')

    print("\n" + "=" * 70)
    print("🤖 COLD CALLS TWILIO - PYTHONANYWHERE")
    print("=" * 70 + "\n")

    try:
        manager = ColdCallManager()
        manager.run_campaign(
            numbers_file='numbers.txt',
            delay=5
        )

    except KeyboardInterrupt:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️  Campaign interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
