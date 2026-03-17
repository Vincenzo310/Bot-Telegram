import logging
import json
import random
import os
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# --- SERVER WEB PER RENDER ---
# Usiamo un nome diverso da 'app' per non fare confusione con il bot
webapp = Flask('')

@webapp.route('/')
def home():
    return "Il bot è online!"

def run():
    webapp.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURAZIONE BOT ---
TOKEN = "8469087738:AAGjieDhhx_NU8eItWoGWMET8H35S7gLe6g"
IL_TUO_ID_TELEGRAM = 1457338119
DB_FILE = "db_squadre.json"
RANGE_CANALI = list(range(1, 10))

# Log per vedere errori nel terminale
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- FUNZIONI DATABASE ---
def carica_dati():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return {}

def salva_dati(dati):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(dati, f, indent=4, ensure_ascii=False)

def ottieni_canale(squadra, dati):
    if squadra not in dati:
        dati[squadra] = {"disponibili": list(RANGE_CANALI), "usati": []}
    if not dati[squadra]["disponibili"]:
        dati[squadra]["disponibili"], dati[squadra]["usati"] = list(RANGE_CANALI), []
    c = random.choice(dati[squadra]["disponibili"])
    dati[squadra]["disponibili"].remove(c)
    dati[squadra]["usati"].append(c)
    return c

# --- TASTIERE ---
def menu_admin():
    keyboard = [
        [InlineKeyboardButton("📊 CANALI USATI", callback_data='stato')],
        [InlineKeyboardButton("🎲 ASSEGNA", callback_data='help_assegna')],
        [InlineKeyboardButton("🗑️ RESET", callback_data='confirm_reset')]
    ]
    return InlineKeyboardMarkup(keyboard)

def bottone_indietro():
    keyboard = [[InlineKeyboardButton("⬅️ INDIETRO", callback_data='back')]]
    return InlineKeyboardMarkup(keyboard)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != IL_TUO_ID_TELEGRAM: return
    await update.message.reply_text(
        "<b>👮‍♂️| PANNELLO ADMIN</b>\n\nScegli una tra le seguenti opzioni",
        reply_markup=menu_admin(),
        parse_mode='HTML'
    )

async def gestore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != IL_TUO_ID_TELEGRAM:
        await query.answer("Non autorizzato", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == 'back':
        await query.edit_message_text(
            "<b>👮‍♂️| PANNELLO ADMIN</b>\n\nScegli una tra le seguenti opzioni",
            reply_markup=menu_admin(),
            parse_mode='HTML'
        )

    elif data == 'stato':
        dati = carica_dati()
        if not dati:
            txt = "❌ <b>Nessun canale assegnato!</b>"
        else:
            txt = "📊 <b>RIEPILOGO CANALI:</b>\n\n"
            for s, info in dati.items():
                txt += f"• <b>{s}</b>: {info['usati']}\n"
        await query.edit_message_text(txt, reply_markup=bottone_indietro(), parse_mode='HTML')

    elif data == 'help_assegna':
        txt = "ℹ️ <b>COME ASSEGNARE</b>\n\n<i>Scrivi i nomi delle squadre separati da virgola.</i>\n\n<b>Esempio:</b>\n<code>Inter, Milan, Napoli</code>"
        await query.edit_message_text(txt, reply_markup=bottone_indietro(), parse_mode='HTML')

    elif data == 'confirm_reset':
        kb = [[InlineKeyboardButton("✅ CONFERMA", callback_data='reset_do')],
              [InlineKeyboardButton("❌ ANNULLA", callback_data='back')]]
        await query.edit_message_text("⚠️ <b>Sei sicuro di voler resettare tutti i canali assegnati?</b>",
                                    reply_markup=InlineKeyboardMarkup(kb),
                                    parse_mode='HTML')

    elif data == 'reset_do':
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        await query.edit_message_text("✔️ <b>Reset completato.</b>",
                                    reply_markup=bottone_indietro(),
                                    parse_mode='HTML')

async def gestore_testo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != IL_TUO_ID_TELEGRAM: return

    testo = update.message.text
    squadre = [s.strip() for s in testo.split(',') if s.strip()]
    if not squadre: return

    dati, ris = carica_dati(), "✔️ <b>CANALI ASSEGNATI:</b>\n\n"
    for s in squadre:
        c = ottieni_canale(s, dati)
        ris += f"• <b>{s}</b>: Canale {c}\n"
    salva_dati(dati)

    await update.message.reply_text(ris, parse_mode='HTML')
    await update.message.reply_text("<b>👮‍♂️| PANNELLO ADMIN</b>\n\nScegli una tra le seguenti opzioni",
                                   reply_markup=menu_admin(),
                                   parse_mode='HTML')

# --- AVVIO ---
if __name__ == '__main__':
    # Facciamo partire il server web prima del bot
    keep_alive()

    # Avviamo il bot
    bot_app = ApplicationBuilder().token(TOKEN).build()

    bot_app.add_handler(CommandHandler('start', start))
    bot_app.add_handler(CallbackQueryHandler(gestore_callback))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), gestore_testo))

    print("🚀 BOT ONLINE CON SUPPORTO HTML")
    bot_app.run_polling()
