from database import init_db, seed_db

if __name__ == "__main__":
    print("Создаю таблицы...")
    init_db()
    print("Заполняю тестовыми данными...")
    seed_db()
    print("✅ БД готова: theater.db")