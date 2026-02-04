import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# GANTI DENGAN TOKEN BOT ANDA
TOKEN = "8558512003:AAELITbNnzNGeaV9KRVuvLt5bxR17hB4OgM"

# Inisialisasi database
def init_db():
    conn = sqlite3.connect("finance.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            category TEXT,
            amount REAL,
            description TEXT
        )
    """)
    conn.commit()
    conn.close()

# Mulai tambah transaksi
async def add_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE, trans_type: str):
    keyboard = [["Tunai", "Non Tunai"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        f"Pilih kategori untuk {trans_type} (Tunai / Non Tunai):",
        reply_markup=reply_markup
    )
    context.user_data["trans_type"] = trans_type
    context.user_data["step"] = "category"

# Handle input user
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_data = context.user_data

    if user_data.get("step") == "category":
        if text in ["Tunai", "Non Tunai"]:
            user_data["category"] = text.lower()
            user_data["step"] = "amount"
            await update.message.reply_text("Masukkan jumlah (contoh: 10000):")
        else:
            await update.message.reply_text("Pilih Tunai atau Non Tunai.")

    elif user_data.get("step") == "amount":
        try:
            user_data["amount"] = float(text)
            user_data["step"] = "description"
            await update.message.reply_text("Masukkan deskripsi:")
        except ValueError:
            await update.message.reply_text("Jumlah harus berupa angka.")

    elif user_data.get("step") == "description":
        description = text
        date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect("finance.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO transactions (date, type, category, amount, description) VALUES (?, ?, ?, ?, ?)",
            (date, user_data["trans_type"], user_data["category"], user_data["amount"], description)
        )
        conn.commit()
        conn.close()

        await update.message.reply_text("✅ Transaksi berhasil disimpan")
        user_data.clear()

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Financial Tracker Bot\n\n"
        "/add_income - Tambah pemasukan\n"
        "/add_expense - Tambah pengeluaran\n"
        "/balance - Saldo hari ini\n"
        "/today_expenses - Pengeluaran hari ini\n"
        "/net_today - Total plus / minus hari ini"
    )

async def add_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_transaction(update, context, "income")

async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await add_transaction(update, context, "expense")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("finance.db")
    c = conn.cursor()
    c.execute("""
        SELECT category,
        SUM(CASE WHEN type='income' THEN amount ELSE -amount END)
        FROM transactions
        WHERE date=?
        GROUP BY category
    """, (today,))
    rows = c.fetchall()
    conn.close()

    cash = non_cash = 0
    for cat, val in rows:
        if cat == "tunai":
            cash = val
        elif cat == "non tunai":
            non_cash = val

    await update.message.reply_text(
        f"💰 Saldo Hari Ini:\nTunai: {cash}\nNon Tunai: {non_cash}"
    )

async def today_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("finance.db")
    c = conn.cursor()
    c.execute("""
        SELECT category, amount, description
        FROM transactions
        WHERE date=? AND type='expense'
        ORDER BY amount DESC
    """, (today,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Tidak ada pengeluaran hari ini.")
        return

    msg = "📉 Pengeluaran Hari Ini:\n"
    for cat, amt, desc in rows:
        msg += f"- {cat}: {amt} ({desc})\n"
    await update.message.reply_text(msg)

async def net_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("finance.db")
    c = conn.cursor()
    c.execute("""
        SELECT SUM(CASE WHEN type='income' THEN amount ELSE -amount END)
        FROM transactions WHERE date=?
    """, (today,))
    net = c.fetchone()[0] or 0
    conn.close()

    status = "PLUS" if net >= 0 else "MINUS"
    await update.message.reply_text(f"📊 Hari ini: {status} ({net})")

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_income", add_income))
    app.add_handler(CommandHandler("add_expense", add_expense))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("today_expenses", today_expenses))
    app.add_handler(CommandHandler("net_today", net_today))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()

