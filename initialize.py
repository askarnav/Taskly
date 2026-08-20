import socket
import ssl
import struct
import sqlite3
import time

HOST = "dpg-d9li63u7bikc7393dhp0.oregon-postgres.render.com"
PORT = 5432
USER = "posts_fuui_user"
DB = "posts_fuui"
PASS = "D9VjVBMC5qvlIzx2t7rAv1KC4aFfjp0V"


def build_packet(data):
    return struct.pack("!I", len(data) + 4) + data


s = socket.create_connection((HOST, PORT))

s.sendall(struct.pack("!I", 8) + struct.pack("!I", 80877103))
response = s.recv(1)

if response == b'S':
    ctx = ssl.create_default_context()
    s = ctx.wrap_socket(s, server_hostname=HOST)
elif response != b'N':
    raise Exception("Unexpected connection response from Render server")

startup_data = f"user\x00{USER}\x00database\x00{DB}\x00\x00".encode('utf-8')
s.sendall(build_packet(startup_data))

while True:
    msg_type = s.recv(1)
    if not msg_type:
        break

    msg_len = struct.unpack("!I", s.recv(4))[0] - 4
    msg_body = s.recv(msg_len) if msg_len > 0 else b""

    if msg_type == b'R':
        auth_type = struct.unpack("!I", msg_body[:4])[0]
        if auth_type == 3:
            pass_msg = PASS.encode('utf-8') + b"\x00"
            s.sendall(b'p' + build_packet(pass_msg))
    elif msg_type == b'Z':
        print("Successfully authenticated with Render cloud instance.")
        break
    elif msg_type == b'E':
        print(f"Server Error received: {msg_body.decode('utf-8', errors='ignore')}")
        s.close()
        exit(1)

print("Extracting records from local instance/users.db...")
time.sleep(2)
try:
    lite_conn = sqlite3.connect("instance/users.db")
    lite_cur = lite_conn.cursor()
    lite_cur.execute("SELECT id, username, code, email FROM users")
    users_data = lite_cur.fetchall()
    lite_conn.close()
except sqlite3.Error as e:
    print(f"Local SQLite Error: {e}")
    s.close()
    exit(1)

sql_commands = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY, 
    username VARCHAR(150) NOT NULL UNIQUE, 
    code TEXT NOT NULL, 
    email VARCHAR(150) NOT NULL UNIQUE
);
"""

for row in users_data:
    u_id, username, code, email = row
    username_esc = str(username).replace("'", "''")
    code_esc = str(code).replace("'", "''")
    email_esc = str(email).replace("'", "''")

    sql_commands += f"INSERT INTO users (id, username, code, email) VALUES ({u_id}, '{username_esc}', '{code_esc}', '{email_esc}') ON CONFLICT (id) DO NOTHING;\n"

print("Streaming live SQLite rows into your cloud database over raw socket connection...")
time.sleep(2)
query_packet = b'Q' + build_packet(sql_commands.encode('utf-8') + b'\x00')
s.sendall(query_packet)

while True:
    msg_type = s.recv(1)
    if not msg_type:
        break
    msg_len = struct.unpack("!I", s.recv(4))[0] - 4
    msg_body = s.recv(msg_len) if msg_len > 0 else b""

    if msg_type == b'C':
        print(f"Status: {msg_body.decode('utf-8', errors='ignore').strip()}")
    elif msg_type == b'Z':
        print("Data processing pipeline completed successfully.")
        break
    elif msg_type == b'E':
        print(f"Execution Warning/Error: {msg_body[4:].decode('utf-8', errors='ignore')}")

s.sendall(b'X' + struct.pack("!I", 4))
s.close()
print("Migration process finished.")
time.sleep(2)
print('Migration Successful!')
