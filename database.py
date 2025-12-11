# test_db.py
from database import Database

db = Database()

# تست تابع get_champion
test_league_id = 1
result = db.get_champion(test_league_id)
print(f"نتایج get_champion برای league_id={test_league_id}: {result}")

# تست ایجاد یک لیگ و قهرمان
league_id = db.create_league("تست لیگ", 10)
print(f"لیگ ایجاد شد با ID: {league_id}")

# ست کردن قهرمان
success = db.set_champion(league_id, "test_user", "تست نمایش", 12345)
print(f"ست کردن قهرمان: {success}")

# دریافت دوباره
champion = db.get_champion(league_id)
print(f"قهرمان دریافت شده: {champion}")

db.close()