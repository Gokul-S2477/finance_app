from db import get_connection

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        customer_code VARCHAR(50) UNIQUE,
        name VARCHAR(100),
        mobile1 VARCHAR(15),
        mobile2 VARCHAR(15),
        address TEXT,
        reference_name VARCHAR(100),
        dob DATE,
        profile_photo TEXT,
        document_file TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS loans (
        id SERIAL PRIMARY KEY,
        customer_id INT REFERENCES customers(id),
        total_amount INT,
        amount_given INT,
        interest INT,
        daily_amount INT,
        duration_days INT,
        loan_date DATE,
        start_date DATE,
        end_date DATE,
        status VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_collections (
        id SERIAL PRIMARY KEY,
        loan_id INT REFERENCES loans(id),
        collection_date DATE,
        amount_due INT,
        amount_paid INT DEFAULT 0,
        status VARCHAR(20),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id SERIAL PRIMARY KEY,
        loan_id INT,
        collection_date DATE,
        old_amount INT,
        new_amount INT,
        edited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE,
        password_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    create_tables()
    print("✅ Tables created successfully")
