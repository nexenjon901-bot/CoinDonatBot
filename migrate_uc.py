import asyncio
import sys
from sqlalchemy import text
from db.database import engine

async def run_uc_migration():
    async with engine.begin() as conn:
        print("1. Adding product_type to products...")
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS product_type VARCHAR(50) DEFAULT 'account';"))
        
        print("2. Adding player_id to orders...")
        await conn.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS player_id VARCHAR(100);"))

        print("3. Updating existing category / creating UC category...")
        res = await conn.execute(text("SELECT id, name FROM categories WHERE name ILIKE '%PUBG%' ORDER BY id LIMIT 1;"))
        pubg_cat = res.fetchone()
        
        if pubg_cat:
            cat_id, cat_name = pubg_cat
            await conn.execute(text("""
                UPDATE categories 
                SET name = 'PUBG Mobile Akkauntlar', emoji = '🎮', order_index = 1 
                WHERE id = :cid
            """), {"cid": cat_id})
            print(f"   Updated category {cat_id} to PUBG Mobile Akkauntlar")

        # Create UC Category if not exists
        res_uc = await conn.execute(text("SELECT id FROM categories WHERE name ILIKE '%UC%' LIMIT 1;"))
        uc_cat = res_uc.fetchone()
        
        if not uc_cat:
            res_ins = await conn.execute(text("""
                INSERT INTO categories (name, emoji, order_index, is_active)
                VALUES ('PUBG Mobile UC', '💎', 2, TRUE)
                RETURNING id;
            """))
            uc_cat_id = res_ins.scalar()
            print(f"   Created PUBG Mobile UC category with id: {uc_cat_id}")
        else:
            uc_cat_id = uc_cat[0]
            print(f"   UC category already exists with id: {uc_cat_id}")

        # Add popular UC packs if empty
        res_prods = await conn.execute(text("SELECT count(*) FROM products WHERE category_id = :cid"), {"cid": uc_cat_id})
        count_prods = res_prods.scalar()
        
        if count_prods == 0:
            print("4. Adding default UC packages...")
            uc_packages = [
                ("60 UC", 14000.00, 1.05, 9999, "PUBG Mobile 60 UC. Player ID orqali tezkor tushirib beriladi."),
                ("325 + 25 UC", 70000.00, 5.25, 9999, "PUBG Mobile 350 UC. Player ID orqali tezkor tushirib beriladi."),
                ("660 + 60 UC", 135000.00, 10.50, 9999, "PUBG Mobile 720 UC (Royale Pass uchun). Player ID orqali tushirib beriladi."),
                ("1800 UC", 330000.00, 25.00, 9999, "PUBG Mobile 1800 UC. Player ID orqali tezkor yetkaziladi."),
                ("3850 UC", 660000.00, 50.00, 9999, "PUBG Mobile 3850 UC. Player ID orqali tezkor yetkaziladi."),
                ("8100 UC", 1350000.00, 100.00, 9999, "PUBG Mobile 8100 UC. Player ID orqali tezkor yetkaziladi.")
            ]
            for name, uzs, usd, qty, desc in uc_packages:
                await conn.execute(text("""
                    INSERT INTO products (category_id, name, price_uzs, price_usd, quantity, description, product_type, is_active)
                    VALUES (:cid, :name, :uzs, :usd, :qty, :desc, 'uc', TRUE)
                """), {
                    "cid": uc_cat_id,
                    "name": name,
                    "uzs": uzs,
                    "usd": usd,
                    "qty": qty,
                    "desc": desc
                })
            print("   Default UC packages added successfully!")

        print("Migration UC completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_uc_migration())
