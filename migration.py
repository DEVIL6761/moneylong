import sqlite3


def migrate_db():
    conn = sqlite3.connect('finance.db')
    cursor = conn.cursor()

    try:
        # Проверяем, существует ли уже столбец account_id
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'account_id' not in columns:
            # Добавляем новый столбец
            cursor.execute('''
            ALTER TABLE transactions 
            ADD COLUMN account_id INTEGER 
            REFERENCES accounts(id)
            ''')
            print("Столбец account_id успешно добавлен в таблицу transactions")
        else:
            print("Столбец account_id уже существует")

        conn.commit()
    except Exception as e:
        print(f"Ошибка при миграции: {str(e)}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == '__main__':
    migrate_db()