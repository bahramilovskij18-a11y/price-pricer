#!/usr/bin/env python3
"""
Локальный HTTP сервер для тестирования веб-приложения
Используется для быстрого тестирования перед развертыванием на реальном сервере
"""

import http.server
import socketserver
import os
from pathlib import Path

PORT = 8000
DIRECTORY = Path(__file__).parent

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # CORS headers for local testing
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == '__main__':
    os.chdir(DIRECTORY)

    with socketserver.TCPServer(('', PORT), MyHTTPRequestHandler) as httpd:
        print(f'✅ Сервер запущен на http://localhost:{PORT}')
        print(f'📂 Папка: {DIRECTORY}')
        print(f'🌐 Откройте http://localhost:{PORT}/index.html')
        print(f'⚠️  Для Telegram требуется HTTPS URL (используйте ngrok или реальный сервер)')
        print(f'\n💡 Для использования с ngrok:')
        print(f'   1. Установите ngrok: https://ngrok.com')
        print(f'   2. Запустите: ngrok http {PORT}')
        print(f'   3. Используйте HTTPS URL в .env файле')
        print(f'\nНажмите Ctrl+C чтобы остановить сервер')

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n\n👋 Сервер остановлен')
