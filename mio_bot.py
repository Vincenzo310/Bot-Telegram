import logging
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Impostazione del logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Inserisci qui il TOKEN fornito da @BotFather
TOKEN = "8783678949:AAHqyQyF8zrcg1_xpi30a7ozkz_UGZHV9GM"

# ID utente autorizzato
ADMIN_ID = 1457338119

async def check_auth(update: Update) -> bool:
    user = update.effective_user
    if not user or user.id != ADMIN_ID:
        if update.message:
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        elif update.callback_query:
            await update.callback_query.answer("Non sei autorizzato!", show_alert=True)
        return False
    return True

# Inizializzazione dei dati utente
def init_user_data(context: ContextTypes.DEFAULT_TYPE):
    if "squadre" not in context.user_data:
        context.user_data["squadre"] = []  # Lista nomi squadre
    if "assegnazioni" not in context.user_data:
        context.user_data["assegnazioni"] = {}  # {squadra: [canali]}
    if "attesa_squadre" not in context.user_data:
        context.user_data["attesa_squadre"] = False
    if "sel_ass" not in context.user_data:
        context.user_data["sel_ass"] = []  # Squadre selezionate in ASSEGNA
    if "sel_del_sq" not in context.user_data:
        context.user_data["sel_del_sq"] = []  # Squadre selezionate in RESET PARZIALE
    if "sel_del_ch" not in context.user_data:
        context.user_data["sel_del_ch"] = {}  # {squadra: [canali_da_eliminare]}

# Tastiera del menu principale
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("STATISTICHE", callback_data="statistiche")],
        [InlineKeyboardButton("RESET", callback_data="reset")],
        [InlineKeyboardButton("ASSEGNA", callback_data="assegna")],
        [InlineKeyboardButton("AGGIUNGI SQUADRE", callback_data="aggiungi_squadre")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    init_user_data(context)
    context.user_data["attesa_squadre"] = False
    
    text = "Benvenuto! Scegli un'opzione dal menu sottostante:"
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard())
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard())

# Gestore dei messaggi di testo (per l'inserimento squadre)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    init_user_data(context)
    if context.user_data.get("attesa_squadre"):
        nuove_squadre = [s.strip() for s in update.message.text.split("\n") if s.strip()]
        for sq in nuove_squadre:
            if sq not in context.user_data["squadre"]:
                context.user_data["squadre"].append(sq)
                context.user_data["assegnazioni"][sq] = []
        
        context.user_data["attesa_squadre"] = False
        await update.message.reply_text(
            f"✅ Aggiunte {len(nuove_squadre)} squadre con successo!",
            reply_markup=main_menu_keyboard()
        )

# Gestore unico dei pulsanti inline
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update):
        return
    query = update.callback_query
    init_user_data(context)
    data = query.data

    # Bottone disattivato (usato solo come etichetta per il nome della squadra)
    if data == "ignore":
        await query.answer()
        return

    # --- AGGIUNGI SQUADRE ---
    if data == "aggiungi_squadre":
        context.user_data["attesa_squadre"] = True
        kb = [[InlineKeyboardButton("INDIETRO", callback_data="start")]]
        await query.edit_message_text(
            "Invia un messaggio con i nomi delle squadre che vuoi aggiungere (una per riga):",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # --- STATISTICHE ---
    elif data == "statistiche":
        squadre = context.user_data["squadre"]
        ha_canali = any(context.user_data["assegnazioni"].get(sq, []) for sq in squadre)
        if not squadre or not ha_canali:
            msg = "📊 *STATISTICHE SQUADRE E CANALI:*\n\nAncora non sono stati assegnati canali."
        else:
            msg = "📊 *STATISTICHE SQUADRE E CANALI:*\n\n"
            for sq in squadre:
                canali = context.user_data["assegnazioni"].get(sq, [])
                canali_str = ", ".join(map(str, sorted(canali))) if canali else "Nessun canale"
                msg += f"• *{sq}*: Canali [{canali_str}]\n"
        
        kb = [[InlineKeyboardButton("INDIETRO", callback_data="start")]]
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    # --- ASSEGNA ---
    elif data == "assegna" or data.startswith("toggle_ass_"):
        if not context.user_data["squadre"]:
            await query.answer("Prima devi aggiungere le squadre!", show_alert=True)
            return

        if data.startswith("toggle_ass_"):
            sq_idx = int(data.split("_")[2])
            sq = context.user_data["squadre"][sq_idx]
            if sq in context.user_data["sel_ass"]:
                context.user_data["sel_ass"].remove(sq)
            else:
                context.user_data["sel_ass"].append(sq)

        keyboard = []
        squadre = context.user_data["squadre"]
        row = []
        for i, sq in enumerate(squadre):
            label = f"✅ {sq}" if sq in context.user_data["sel_ass"] else sq
            row.append(InlineKeyboardButton(label, callback_data=f"toggle_ass_{i}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("CONFERMA", callback_data="conferma_assegna")])
        keyboard.append([InlineKeyboardButton("ANNULLA", callback_data="start")])

        await query.edit_message_text("Seleziona le squadre a cui assegnare dei canali:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "conferma_assegna":
        selezionate = context.user_data["sel_ass"]
        if not selezionate:
            await query.answer("Seleziona almeno una squadra!", show_alert=True)
            return
        
        report = "📋 *REPORT ASSEGNAZIONE:*\n\n"
        for sq in selezionate:
            ch = random.randint(1, 9)
            if ch not in context.user_data["assegnazioni"][sq]:
                context.user_data["assegnazioni"][sq].append(ch)
            report += f"• *{sq}* -> Canale {ch}\n"
        
        context.user_data["sel_ass"] = []
        kb = [[InlineKeyboardButton("TORNA AL MENU", callback_data="start")]]
        await query.edit_message_text(report, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    # --- RESET ---
    elif data == "reset":
        keyboard = [
            [InlineKeyboardButton("TUTTO", callback_data="reset_tutto")],
            [InlineKeyboardButton("ELIMINA PARZIALE", callback_data="reset_parziale")],
            [InlineKeyboardButton("INDIETRO", callback_data="start")]
        ]
        await query.edit_message_text("Scegli la modalità di RESET:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "reset_tutto":
        ha_canali = any(context.user_data["assegnazioni"].get(sq, []) for sq in context.user_data["squadre"])
        if not ha_canali:
            await query.answer("Non è stato assegnato nessun canale.", show_alert=True)
            return

        keyboard = [
            [InlineKeyboardButton("CONFERMA", callback_data="conferma_reset_tutto")],
            [InlineKeyboardButton("ANNULLA", callback_data="reset")]
        ]
        await query.edit_message_text("Sei sicuro di voler eliminare TUTTI i canali assegnati?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "conferma_reset_tutto":
        for sq in context.user_data["assegnazioni"]:
            context.user_data["assegnazioni"][sq] = []
        
        kb = [[InlineKeyboardButton("TORNA AL MENU", callback_data="start")]]
        await query.edit_message_text("🗑️ Tutti i canali assegnati sono stati eliminati.", reply_markup=InlineKeyboardMarkup(kb))

    # --- ELIMINA PARZIALE (Passo 1: Selezione Squadre) ---
    elif data == "reset_parziale" or data.startswith("toggle_delsq_"):
        ha_canali = any(context.user_data["assegnazioni"].get(sq, []) for sq in context.user_data["squadre"])
        if not ha_canali:
            await query.answer("Non è stato assegnato nessun canale.", show_alert=True)
            return

        if data == "reset_parziale":
            context.user_data["sel_del_sq"] = []

        if data.startswith("toggle_delsq_"):
            sq_idx = int(data.split("_")[2])
            sq = context.user_data["squadre"][sq_idx]
            if sq in context.user_data["sel_del_sq"]:
                context.user_data["sel_del_sq"].remove(sq)
            else:
                context.user_data["sel_del_sq"].append(sq)

        keyboard = []
        row = []
        for i, sq in enumerate(context.user_data["squadre"]):
            if context.user_data["assegnazioni"].get(sq):
                label = f"✅ {sq}" if sq in context.user_data["sel_del_sq"] else sq
                row.append(InlineKeyboardButton(label, callback_data=f"toggle_delsq_{i}"))
                if len(row) == 3:
                    keyboard.append(row)
                    row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("CONFERMA", callback_data="conf_delsq")])
        keyboard.append([InlineKeyboardButton("ANNULLA", callback_data="reset")])

        await query.edit_message_text("Seleziona le squadre da cui vuoi eliminare i canali:", reply_markup=InlineKeyboardMarkup(keyboard))

    # --- ELIMINA PARZIALE (Passo 2: Selezione Canali con bottoni raggruppati per squadra) ---
    elif data == "conf_delsq" or data.startswith("toggle_delch_"):
        if not context.user_data["sel_del_sq"]:
            await query.answer("Seleziona almeno una squadra!", show_alert=True)
            return

        if data.startswith("toggle_delch_"):
            parts = data.split("_")
            sq = context.user_data["squadre"][int(parts[2])]
            ch = int(parts[3])

            if sq not in context.user_data["sel_del_ch"]:
                context.user_data["sel_del_ch"][sq] = []

            if ch in context.user_data["sel_del_ch"][sq]:
                context.user_data["sel_del_ch"][sq].remove(ch)
            else:
                context.user_data["sel_del_ch"][sq].append(ch)

        keyboard = []
        for sq in context.user_data["sel_del_sq"]:
            sq_idx = context.user_data["squadre"].index(sq)
            canali = context.user_data["assegnazioni"].get(sq, [])
            
            if canali:
                row = [InlineKeyboardButton(sq, callback_data="ignore")]
                for ch in sorted(canali):
                    is_sel = ch in context.user_data["sel_del_ch"].get(sq, [])
                    label_ch = f"✅ {ch}" if is_sel else f"{ch}"
                    row.append(InlineKeyboardButton(label_ch, callback_data=f"toggle_delch_{sq_idx}_{ch}"))
                
                keyboard.append(row)

        keyboard.append([InlineKeyboardButton("CONFERMA", callback_data="conferma_elimina_canali")])
        keyboard.append([InlineKeyboardButton("ANNULLA", callback_data="reset_parziale")])

        await query.edit_message_text("Seleziona i canali specifici da eliminare:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "conferma_elimina_canali":
        del_dict = context.user_data["sel_del_ch"]
        for sq, canali in del_dict.items():
            for ch in canali:
                if ch in context.user_data["assegnazioni"][sq]:
                    context.user_data["assegnazioni"][sq].remove(ch)

        context.user_data["sel_del_sq"] = []
        context.user_data["sel_del_ch"] = {}

        kb = [[InlineKeyboardButton("TORNA AL MENU", callback_data="start")]]
        await query.edit_message_text("🗑️ Canali selezionati eliminati con successo!", reply_markup=InlineKeyboardMarkup(kb))

    # --- INDIETRO / START ---
    elif data == "start":
        await start(update, context)

# Avvio del Bot
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot avviato...")
    app.run_polling()

if __name__ == "__main__":
    main()
