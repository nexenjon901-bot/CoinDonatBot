# CoinDonatBot (PUBG Mobile UC & Akkauntlar Do'koni)

Telegram orqali o'yin donatlari (PUBG Mobile UC), o'yin akkauntlari va raqamli tovarlarni sotish uchun avtomatlashtirilgan bot platformasi.

## Imkoniyatlar
- 🛍 **Katalog va Do'kon:** PUBG Mobile UC (Player ID orqali) va Akkauntlar savdosi.
- 💳 **Balans to'ldirish (Hamyon):** Chek yuklash va admin tomonidan tasdiqlanishi.
- ⚡️ **Atomik tranzaksiyalar:** Poyga holatlariga (race condition) qarshi SQL darajasidagi himoya.
- 🔐 **Xavfsiz ombor:** Akkaunt ma'lumotlari (login/parol) Fernet orqali shifrlangan saqlanadi.
- ⚙️ **Keng qamrovli Admin Panel:** Mahsulotlar, kategoriyalar, kutilayotgan buyurtmalar va balans so'rovlarini tasdiqlash/bekor qilish.
- 🌐 **Ko'p tillilik:** O'zbek, Rus va Ingliz tillari.

## Texnologiyalar
- Python 3.12+
- Aiogram 3.x
- SQLAlchemy 2.0 (Async) + PostgreSQL (NeonDB)
- Redis
- Cryptography (Fernet)
- Docker & Docker Compose
