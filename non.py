import websocket
import threading
import json
import time
import shareithub
import requests
from fake_useragent import UserAgent
from colorama import init, Fore
from datetime import datetime
from shareithub import shareithub

shareithub()

init(autoreset=True)

class BotAPI:
    def __init__(self, url, stats_url):
        self.url = url
        self.stats_url = stats_url 
        self.access_token = None
        self.ua = UserAgent()  
        self.retry_delay = 60  
        self.connection_delay = 3  

    def log(self, account_name, level, message):
        """
        Fungsi untuk mencetak log dengan level dan format waktu yang lebih mudah dibaca.
        """
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_colors = {
            "INFO": Fore.CYAN,
            "SUCCESS": Fore.GREEN,
            "ERROR": Fore.RED,
            "WARNING": Fore.YELLOW,
        }
        print(f"{level_colors.get(level, Fore.WHITE)}[{time_stamp}] [{account_name}] [{level}] {message}")

    def format_user_stats(self, stats):
        """
        Format statistik pengguna agar lebih mudah dibaca di terminal.
        """
        formatted_stats = [
            f"{'Heartbeats:':<20} {stats['heartbeats']}",
            f"{'Points Today:':<20} {stats['points_today']}",
            f"{'Total Points:':<20} {stats['points_total']}",
            f"{'User ID:':<20} {stats['user_id']}",
            f"{'Heartbeats Genesis Snapshot:':<20} {stats['heartbeats_genesis_snapshot']}",
            f"{'Total Referral Points:':<20} {stats['total_referral_points']}",
            f"{'Total Referrals:':<20} {stats['total_referrals']}",
        ]
        
        
        breakdown = stats.get('points_breakdown', [])
        for category in breakdown:
            formatted_stats.append(f"{category['category']:<20}: {category['value']} points ({category['percentage']}%)")
        
        return "\n".join(formatted_stats)

    def connect_websocket(self, access_token, account_name):
        """
        Menghubungkan bot ke WebSocket menggunakan access token tanpa batasan retry.
        """
        if not access_token:
            self.log(account_name, "ERROR", "Tidak ada token akses. Silakan login terlebih dahulu.")
            return

        ws_url = f"wss://secure.ws.teneo.pro/websocket?accessToken={access_token}&version=v0.2"

        def on_message(ws, message):
            self.log(account_name, "INFO", f"Received message: {message}")

        def on_error(ws, error):
            self.log(account_name, "ERROR", f"Error: {error}")

        def on_close(ws, close_status_code, close_msg):
            self.log(account_name, "WARNING", "WebSocket closed")

        def on_open(ws):
            self.log(account_name, "SUCCESS", "WebSocket connected")
            self.send_ping(ws, account_name)

        headers = {
            "Host": "secure.ws.teneo.pro",
            "Connection": "Upgrade",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": self.ua.random,
            "Upgrade": "websocket",
            "Origin": "chrome-extension://emcclcoaglgcpoognfiggmhnhgabppkm",
            "Sec-WebSocket-Version": "13",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
            "Sec-WebSocket-Key": "g0PDYtLWQOmaBE5upOBXew==",
            "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
        }


        def try_connect():
            attempt = 0
            while True:
                self.log(account_name, "WARNING", f"Mencoba koneksi ke WebSocket... Percobaan ke-{attempt + 1}")
                ws = websocket.WebSocketApp(ws_url,
                                            header=headers,
                                            on_message=on_message,
                                            on_error=on_error,
                                            on_close=on_close,
                                            on_open=on_open)

                
                ws.run_forever()

                
                if ws.sock and ws.sock.connected:
                    self.log(account_name, "SUCCESS", "WebSocket berhasil terhubung!")
                    break
                else:
                    self.log(account_name, "ERROR", "WebSocket gagal terhubung. Mencoba lagi...")
                    time.sleep(self.retry_delay)
                    attempt += 1

        
        time.sleep(self.connection_delay)
        try_connect()

    def send_ping(self, ws, account_name):
        """
        Mengirim pesan {"type": "PING"} setiap 30 detik untuk memastikan WebSocket tetap terhubung.
        """
        def ping():
            try:
                ws.send(json.dumps({"type": "PING"})) 
                self.log(account_name, "INFO", "Sent PING message.")
            except Exception as e:
                self.log(account_name, "ERROR", f"Error saat mengirim PING: {e}")
            threading.Timer(30, ping).start() 

        ping()

    def get_token(self, email, password, account_name):
        """
        Mendapatkan token dan userId menggunakan API login dengan email dan password.
        """
        payload = {
            "grant_type": "password",
            "email": email,
            "password": password
        }

        headers = {
            "authority": "auth.teneo.pro",
            "method": "POST",
            "path": "/api/login",
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,id;q=0.8",
            "content-length": "58",
            "content-type": "application/json",
            "origin": "https://dashboard.teneo.pro",
            "priority": "u=1, i",
            "referer": "https://dashboard.teneo.pro/",
            "sec-ch-ua": "\"Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "\"Android\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": self.ua.random,  
            "x-api-key": "OwAG3kib1ivOJG4Y0OCZ8lJETa6ypvsDtGmdhcjA", 
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            response.raise_for_status()

 
            data = response.json()
            self.access_token = data.get("access_token")
            
            if self.access_token:
                self.log(account_name, "SUCCESS", f"Login berhasil! Akses Token: {self.access_token}")
                return self.access_token
            else:
                self.log(account_name, "ERROR", "Gagal mendapatkan token akses.")
                return None
        except requests.exceptions.RequestException as e:
            self.log(account_name, "ERROR", f"Error saat login: {e}")
            return None

    def get_user_stats(self, access_token, account_name):
        """
        Mendapatkan statistik pengguna menggunakan access token.
        """
        headers = {
            "authority": "api.teneo.pro",
            "method": "GET",
            "path": "/api/users/stats",
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,id;q=0.8",
            "authorization": f"Bearer {access_token}",
            "origin": "https://dashboard.teneo.pro",
            "priority": "u=1, i",
            "referer": "https://dashboard.teneo.pro/",
            "sec-ch-ua": "\"Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": self.ua.random,  
        }

        try:
            response = requests.get(self.stats_url, headers=headers)
            response.raise_for_status()

            
            stats = response.json()
            formatted_stats = self.format_user_stats(stats)
            self.log(account_name, "INFO", f"User Stats:\n{formatted_stats}")
            return stats
        except requests.exceptions.RequestException as e:
            self.log(account_name, "ERROR", f"Error saat mendapatkan statistik pengguna: {e}")
            return None

    def login_from_file(self, file_path):
        """
        Membaca akun dari file dan mencoba login untuk setiap akun secara paralel.
        """
        try:
            with open(file_path, "r") as file:
                accounts = []
                for line in file:
                    line = line.strip()
                    if line:  
                        email, password = line.split(":")
                        account_name = email.split("@")[0]  
                        account = {'email': email, 'password': password, 'account_name': account_name}
                        accounts.append(account)

                threads = []
                for account in accounts:
                    
                    thread = threading.Thread(target=self.login_and_connect, args=(account['email'], account['password'], account['account_name']))
                    thread.start()
                    threads.append(thread)

                
                for thread in threads:
                    thread.join()

        except Exception as e:
            self.log("Global", "ERROR", f"Error saat membaca file: {e}")
            
    def login_and_connect(self, email, password, account_name):
        """
        Login dan menghubungkan WebSocket untuk setiap akun.
        """
        access_token = self.get_token(email, password, account_name)
        if access_token:
            self.get_user_stats(access_token, account_name) 
            self.connect_websocket(access_token, account_name)


if __name__ == "__main__":

    bot = BotAPI("https://auth.teneo.pro/api/login", "https://api.teneo.pro/api/users/stats")

    bot.login_from_file("accounts.txt")
