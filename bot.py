import time
import json
import random
import threading
import websocket
import requests
import shareithub
from shareithub import HTTPTools, ASCIITools
from fake_useragent import UserAgent

ASCIITools.print_ascii_intro()


class BotAPI:
    def __init__(self, url):
        self.url = url
        self.user_id = None
        self.access_token = None
        self.ua = UserAgent()  # Untuk mendapatkan user-agent acak
        self.socket = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5  # Maksimal mencoba reconnect
        self.max_reconnect_interval = 5  # Interval maksimum reconnect dalam detik
        self.ping_interval = 1  # Interval ping dalam detik
        self.points_today = 0
        self.points_total = 0
        self.accounts = []  # Menyimpan akun-akun yang login

    def get_token(self, email, password):
        """
        Mendapatkan token dan userId menggunakan API login dengan email dan password.
        """
        payload = {
            "grant_type": "password",
            "email": email,
            "password": password
        }

        headers = {
            "authority": "node-community-api.teneo.pro",
            "method": "POST",
            "path": "/auth/v1/token?grant_type=password",
            "scheme": "https",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,id;q=0.8",
            "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imlra25uZ3JneHV4Z2pocGxicGV5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjU0MzgxNTAsImV4cCI6MjA0MTAxNDE1MH0.DRAvf8nH1ojnJBc3rD_Nw6t1AV8X_g6gmY_HByG2Mag",  # Ganti dengan API Key yang valid
            "content-length": "84",
            "content-type": "application/json;charset=UTF-8",
            "origin": "chrome-extension://emcclcoaglgcpoognfiggmhnhgabppkm",
            "priority": "u=1, i",
            "sec-ch-ua": "\"Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "user-agent": self.ua.random,  # Menggunakan user-agent acak dari fake_useragent
            "x-client-info": "supabase-js-web/2.45.4",
            "x-supabase-api-version": "2024-01-01"
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()

            # Parsing response
            data = response.json()
            self.access_token = data.get("access_token")
            user = data.get("user")
            self.user_id = user.get("id") if user else None

            print(f"Login berhasil dengan {email}!")
            print(f"Akses Token: {self.access_token}")
            print(f"User ID: {self.user_id}")
        except requests.exceptions.RequestException as e:
            print(f"Error saat login dengan {email}: {e}")

    def on_message(self, ws, message, account):
        """
        Menerima pesan WebSocket dan memprosesnya.
        """
        data = json.loads(message)
        print(f"Received message from {account['email']}: {data}")
        
        # Menyimpan nilai pointsToday dan pointsTotal
        if 'pointsTotal' in data and 'pointsToday' in data:
            account['points_today'] = data['pointsToday']
            account['points_total'] = data['pointsTotal']
            print(f"Points Today: {account['points_today']}")
            print(f"Points Total: {account['points_total']}")

    def on_error(self, ws, error):
        """
        Menangani error WebSocket.
        """
        print(f"Error WebSocket: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        """
        Menangani saat WebSocket tertutup.
        """
        print("WebSocket closed")

    def on_open(self, ws, account):
        """
        Dipanggil saat WebSocket berhasil terhubung.
        """
        print(f"WebSocket connected for {account['email']}.")
        # Mulai thread untuk mengirimkan ping secara periodik setiap 1 detik
        threading.Thread(target=self.start_pinging, args=(ws, account)).start()

    def start_pinging(self, ws, account):
        """
        Mengirimkan ping ke server WebSocket secara periodik dengan interval 1 detik.
        """
        while True:
            if ws.sock and ws.sock.connected:
                ping_message = json.dumps({"type": "PING"})
                ws.send(ping_message)
                print(f"Ping terkirim untuk {account['email']}.")
                
                # Mengirimkan informasi yang diinginkan setelah ping berhasil
                message_data = {
                    "date": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                    "isNewUser": False,  # Atur sesuai dengan kondisi user
                    "message": "Connected successfully",
                    "pointsToday": account['points_today'],
                    "pointsTotal": account['points_total']
                }
                print(f"Account: {account['email']} - Date: {message_data['date']}")
                print(f"Points Today: {message_data['pointsToday']}")
                print(f"Points Total: {message_data['pointsTotal']}")

                time.sleep(self.ping_interval)  # Tunggu 1 detik sebelum mengirim ping lagi
            else:
                print(f"WebSocket tidak terhubung untuk {account['email']}, menghentikan ping.")
                break

    def connect_websocket(self, account):
        """
        Menghubungkan bot ke WebSocket dan mendengarkan pesan.
        """
        ws_url = f"wss://secure.ws.teneo.pro/websocket?userId={account['user_id']}&version=v0.2"

        # Menambahkan header custom sesuai permintaan
        headers = {
            'Host': 'secure.ws.teneo.pro',
            'Connection': 'Upgrade',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Upgrade': 'websocket',
            'Origin': 'chrome-extension://emcclcoaglgcpoognfiggmhnhgabppkm',
            'Sec-WebSocket-Version': '13',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9,id;q=0.8',
            'Sec-WebSocket-Key': 'K3PIM7Cq8CXwQrCmo1x3uA==',
            'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits'
        }

        # Menggunakan websocket-client untuk menghubungkan dengan custom header
        ws = websocket.WebSocketApp(ws_url, header=headers,
                                    on_message=lambda ws, msg: self.on_message(ws, msg, account),
                                    on_error=self.on_error,
                                    on_close=self.on_close,
                                    on_open=lambda ws: self.on_open(ws, account))

        # Menjalankan WebSocket di thread lain
        ws.run_forever()

    def login_from_file(self, file_path):
        """
        Membaca akun dari file dan mencoba login untuk setiap akun.
        """
        try:
            with open(file_path, "r") as file:
                for line in file:
                    line = line.strip()
                    if line:  # Mengabaikan baris kosong
                        email, password = line.split("|")
                        account = {'email': email, 'password': password, 'points_today': 0, 'points_total': 0}
                        self.get_token(email, password)
                        if self.user_id:
                            account['user_id'] = self.user_id
                            self.accounts.append(account)  # Menyimpan akun yang berhasil login
                            threading.Thread(target=self.connect_websocket, args=(account,)).start()  # Menjalankan WebSocket di thread
        except Exception as e:
            print(f"Error saat membaca file: {e}")

    def display_account_status(self):
        """
        Menampilkan status semua akun.
        """
        while True:
            print("\n[INFO] Status Semua Akun:")
            for account in self.accounts:
                print(f"Email: {account['email']} | Points Today: {account['points_today']} | Points Total: {account['points_total']}")
            time.sleep(10)  # Perbarui setiap 10 detik

if __name__ == "__main__":
    bot = BotAPI("https://node-community-api.teneo.pro/auth/v1/token?grant_type=password")

    # Mulai login dan WebSocket untuk banyak akun
    bot.login_from_file("accounts.txt")

    # Menampilkan status akun di terminal
    bot.display_account_status()
