import psycopg2
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

username = "admin"
password = hash_password("admin123")

cur.execute("""
INSERT INTO users (username, password_hash)
VALUES (%s, %s)
ON CONFLICT (username) DO NOTHING;
""", (username, password))

conn.commit()
cur.close()
conn.close()

print("✅ Admin created | Username: admin | Password: admin123")
