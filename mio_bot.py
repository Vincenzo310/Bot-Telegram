import logging
import json
import random
import os
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# --- SERVER WEB PER KEEP-ALIVE ---
webapp = Flask('')

@webapp.route('/')
def home():
    return "✅ IL BOT E' ONLINE!"

def run():
    webapp.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURAZIONE BOT ---
TOKEN = "8469087738:AAGjieDhhx_NU8eItWoGWMET8H35S7gLe6g"
IL_TUO_ID_TELEGRAM = 8361466889
DB_FILE = "db_squadre.json"
RANGE_CANALI = list(range(1, 10))

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

def ottieni_canale_random(squadra, dati):
    if squadra not in dati:
        dati[squadra] = {"disponibili": list(RANGE_CANALI), "usati": []}
    if not dati[squadra]["disponibili"]:
        dati[squadra]["disponibili"], dati[squadra]["usati"] = list(RANGE_CANALI), []
    c = random.choice(dati[squadra]["disponibili"])
    dati[squadra]["disponibili"].remove(c)
    dati[squadra]["usati"].append(c)
    return c

def assegna_canale_manuale(squadra, canale, dati):
    if squadra not in dati:
        dati[squadra] = {"disponibili": list(RANGE_CANALI), "usati": []}
    if canale not in dati[squadra]["usati"]:
        dati[squadra]["usati"].append(canale)
        if canale in dati[squadra]["disponibili"]:
            dati[squadra]["disponibili"].remove(canale)
    return canale

# --- TASTIERE ---
def menu_admin():
    keyboard = [
        [InlineKeyboardButton("📊 CANALI USATI", callback_data='stato')],
        [InlineKeyboardButton("📉 CANALI MANCANTI", callback_data='mancanti')],
        [InlineKeyboardButton("🎲 ASSEGNA", callback_data='help_assegna')],
        [InlineKeyboardButton("🗑️ RESET", callback_data='menu_reset')]
    ]
    return InlineKeyboardMarkup(keyboard)

def bottone_indietro():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ INDIETRO", callback_data='back')]])

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != IL_TUO_ID_TELEGRAM: return
    await update.message.reply_text(
        "<b>👮‍♂️| PANNELLO ADMIN</b>\n\nScegli una tra le seguenti opzioni ⤵️",
        reply_markup=menu_admin(),
        parse_mode='HTML'
    )

async def gestore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id != IL_TUO_ID_TELEGRAM: return
    await query.answer()
    data = query.data

    if data == 'back':
        await query.edit_message_text("<b>👮‍♂️| PANNELLO ADMIN</b>\n\nScegli una tra le seguenti opzioni ⤵️", reply_markup=menu_admin(), parse_mode='HTML')

    elif data == 'stato':
        dati = carica_dati()
        txt = "🟢 <b>RIEPILOGO CANALI USATI:</b>\n\n"
        if not dati: txt += "<i><b>Non hai assegnato nessun canale al momento.</b>\n\n<i>Torna indietro per assegnarne uno!</i>"
        else:
            for s, info in dati.items():
                txt += f"• <b>{s}</b>: {sorted(info['usati'])}\n"
        await query.edit_message_text(txt, reply_markup=bottone_indietro(), parse_mode='HTML')

    elif data == 'mancanti':
        dati = carica_dati()
        txt = "🔴 <b>CANALI ANCORA DISPONIBILI:</b>\n\n"
        if not dati: txt += "<i><b>Non hai ancora assegnato nessun canale.</i></b>\n\n<i>Torna indietro per assegnarne uno!</i>"
        else:
            for s, info in dati.items():
                # Calcoliamo i canali mancanti (quelli nel range che NON sono negli usati)
                mancanti = [c for c in RANGE_CANALI if c not in info['usati']]
                txt += f"• <b>{s}</b>: {mancanti if mancanti else '⚠️ FINITI'}\n"
        await query.edit_message_text(txt, reply_markup=bottone_indietro(), parse_mode='HTML')

    elif data == 'menu_reset':
        kb = [[InlineKeyboardButton("💣 RESETTA TUTTO", callback_data='reset_all_do')],
              [InlineKeyboardButton("⚽ RESETTA SINGOLO CANALE", callback_data='help_reset_single')],
              [InlineKeyboardButton("⬅️ INDIETRO", callback_data='back')]]
        await query.edit_message_text("❓ <b>COSA VUOI RESETTARE?</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    elif data == 'help_assegna':
        txt = ("🎲 <b>MODALITÀ ASSEGNAZIONE ⤵️</b>\n\n"
            "1️⃣ <b>CASUALE:</b> <code>Juventus, Milan</code>\n"
            "2️⃣ <b>MANUALE:</b> <code>Inter:5</code>\n\n"
            "⚠️ <i>Ricordati di scrivere i nomi delle squadre separati da una virgola (,)</i>")
        await query.edit_message_text(txt, reply_markup=bottone_indietro(), parse_mode='HTML')

    elif data == 'help_reset_single':
        await query.edit_message_text("🗑 <b>RESET SINGOLO</b>\n\nDIGITA: <code>cancella Napoli, Atalanta</code>", reply_markup=bottone_indietro(), parse_mode='HTML')

    elif data == 'reset_all_do':
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        await query.edit_message_text("✅ <b>Canali cancellati correttamente</b>", reply_markup=bottone_indietro(), parse_mode='HTML')

async def gestore_testo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != IL_TUO_ID_TELEGRAM: return
    testo = update.message.text.strip()

    # --- CANCELLAZIONE SINGOLA ---
    if testo.lower().startswith("cancella "):
        nomi = [s.strip() for s in testo.replace("cancella ", "").split(',') if s.strip()]
        dati = carica_dati()
        rimossi = []
        for n in nomi:
            squadra_trovata = next((k for k in dati.keys() if k.lower() == n.lower()), None)
            if squadra_trovata:
                del dati[squadra_trovata]
                rimossi.append(squadra_trovata)
        salva_dati(dati)
        msg = f"✅ <b>RIMOSSI I CANALI A:</b> {', '.join(rimossi)}" if rimossi else "❌ Nessuna squadra trovata."
        await update.message.reply_text(msg, parse_mode='HTML')
        await update.message.reply_text("<b>👮‍♂️| PANNELLO ADMIN</b>\n\nScegli una tra le seguenti opzioni ⤵️", reply_markup=menu_admin(), parse_mode='HTML')
        return

    # --- ASSEGNAZIONE ---
    elementi = [e.strip() for e in testo.split(',') if e.strip()]
    dati, ris = carica_dati(), " <b>✔️ CANALI ASSEGNATI: ⤵️</b>\n\n"

    for item in elementi:
        if ":" in item:
            try:
                squadra, canale = item.split(":")
                assegna_canale_manuale(squadra.strip(), int(canale.strip()), dati)
                ris += f"✅ <b>{squadra.strip()}</b>: Canale {canale.strip()} (Manuale)\n"
            except: ris += f"❌ Errore formato: RIPROVA! `{item}`\n"
        else:
            c = ottieni_canale_random(item, dati)
            ris += f"⚽ <b>{item}</b>: Canale {c}\n"

    salva_dati(dati)
    await update.message.reply_text(ris, parse_mode='HTML')
    await update.message.reply_text("<b>👮‍♂️| PANNELLO ADMIN</b>\n\nScegli una tra le seguenti opzioni ⤵️", reply_markup=menu_admin(), parse_mode='HTML')

if __name__ == '__main__':
    keep_alive()
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler('start', start))
    bot_app.add_handler(CallbackQueryHandler(gestore_callback))
    bot_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), gestore_testo))
    bot_app.run_polling()
