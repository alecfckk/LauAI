import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")

# Estados de conversación
(
    MENU,
    IMC_ADULTO_SEXO, IMC_ADULTO_EDAD, IMC_ADULTO_ALTURA, IMC_ADULTO_PESO,
    IMC_NINO_SEXO, IMC_NINO_EDAD_ANIOS, IMC_NINO_EDAD_MESES, IMC_NINO_ALTURA, IMC_NINO_PESO,
    PAM_SISTOLICA, PAM_DIASTOLICA,
) = range(12)

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def calcular_imc(peso_kg: float, altura_cm: float) -> float:
    h = altura_cm / 100
    return round(peso_kg / (h * h), 1)

def clasificar_imc_adulto(imc: float) -> str:
    if imc < 16:    return "🔴 Muy Bajo Peso Severo"
    elif imc < 17:  return "🟠 Bajo Peso Severo"
    elif imc < 18.5:return "🟡 Bajo Peso"
    elif imc < 25:  return "🟢 Normal"
    elif imc < 30:  return "🟡 Sobrepeso"
    elif imc < 35:  return "🟠 Obeso Clase I"
    elif imc < 40:  return "🔴 Obeso Clase II"
    else:           return "🔴 Obeso Clase III"

def calcular_grasa_adulto(imc: float, edad: int, sexo: str) -> float:
    """Fórmula de Deurenberg"""
    s = 1 if sexo == "M" else 0
    grasa = (1.20 * imc) + (0.23 * edad) - (10.8 * s) - 5.4
    return round(grasa, 1)

def peso_ideal_adulto(altura_cm: float, sexo: str) -> float:
    """Fórmula de Devine"""
    h_in = (altura_cm - 152.4) / 2.54
    base = 50.0 if sexo == "M" else 45.5
    return round(base + 2.3 * h_in, 1)

def calcular_pam(sistolica: float, diastolica: float) -> float:
    return round(diastolica + (sistolica - diastolica) / 3, 2)

def clasificar_pam(pam: float) -> str:
    if pam < 70:    return "⚠️ PAM baja — riesgo de hipoperfusión"
    elif pam <= 100: return "✅ PAM normal"
    else:           return "⚠️ PAM elevada — evaluar con médico"

# ─────────────────────────────────────────
# MENÚ PRINCIPAL
# ─────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🧑 IMC Adulto", callback_data="imc_adulto")],
        [InlineKeyboardButton("👶 IMC Niño/Adolescente", callback_data="imc_nino")],
        [InlineKeyboardButton("❤️ Presión Arterial Media (PAM)", callback_data="pam")],
    ]
    msg = (
        "👋 *Bot de Calculadoras Médicas*\n\n"
        "Selecciona la herramienta que deseas usar:"
    )
    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown",
                                        reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown",
                                                      reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "imc_adulto":
        keyboard = [
            [InlineKeyboardButton("♂️ Masculino", callback_data="sexo_M"),
             InlineKeyboardButton("♀️ Femenino", callback_data="sexo_F")]
        ]
        await query.edit_message_text("*IMC Adulto* — Paso 1/4\n\n¿Cuál es el sexo?",
                                      parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return IMC_ADULTO_SEXO

    elif data == "imc_nino":
        keyboard = [
            [InlineKeyboardButton("♂️ Niño", callback_data="sexo_M"),
             InlineKeyboardButton("♀️ Niña", callback_data="sexo_F")]
        ]
        await query.edit_message_text("*IMC Niño/Adolescente* — Paso 1/5\n\n¿Sexo?",
                                      parse_mode="Markdown",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return IMC_NINO_SEXO

    elif data == "pam":
        await query.edit_message_text(
            "❤️ *Presión Arterial Media (PAM)* — Paso 1/2\n\n"
            "Ingresa la *Presión Sistólica* (número superior, ej: 120):",
            parse_mode="Markdown"
        )
        return PAM_SISTOLICA

# ─────────────────────────────────────────
# IMC ADULTO
# ─────────────────────────────────────────

async def imc_adulto_sexo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["sexo"] = query.data.replace("sexo_", "")
    await query.edit_message_text("*IMC Adulto* — Paso 2/4\n\n¿Cuántos años tiene? (ej: 38)",
                                  parse_mode="Markdown")
    return IMC_ADULTO_EDAD

async def imc_adulto_edad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["edad"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Ingresa solo el número de años (ej: 38)")
        return IMC_ADULTO_EDAD
    await update.message.reply_text("*IMC Adulto* — Paso 3/4\n\n¿Cuál es la estatura en cm? (ej: 156)",
                                    parse_mode="Markdown")
    return IMC_ADULTO_ALTURA

async def imc_adulto_altura(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["altura"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Ingresa solo el número en cm (ej: 156)")
        return IMC_ADULTO_ALTURA
    await update.message.reply_text("*IMC Adulto* — Paso 4/4\n\n¿Cuál es el peso en kg? (ej: 70.8)",
                                    parse_mode="Markdown")
    return IMC_ADULTO_PESO

async def imc_adulto_peso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        peso = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Ingresa solo el número en kg (ej: 70.8)")
        return IMC_ADULTO_PESO

    d = context.user_data
    imc = calcular_imc(peso, d["altura"])
    grasa = calcular_grasa_adulto(imc, d["edad"], d["sexo"])
    ideal = peso_ideal_adulto(d["altura"], d["sexo"])
    clasif = clasificar_imc_adulto(imc)
    sexo_txt = "Masculino" if d["sexo"] == "M" else "Femenino"

    resultado = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Resultado IMC Adulto*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 Sexo: {sexo_txt} | Edad: {d['edad']} años\n"
        f"📏 Altura: {d['altura']} cm | ⚖️ Peso: {peso} kg\n\n"
        f"🔢 *IMC: {imc}*\n"
        f"📁 Clasificación: {clasif}\n"
        f"🎯 Peso ideal: {ideal} kg\n"
        f"💧 % Grasa corporal: {grasa}%\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    keyboard = [[InlineKeyboardButton("🔄 Nueva consulta", callback_data="reiniciar")]]
    await update.message.reply_text(resultado, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

# ─────────────────────────────────────────
# IMC NIÑO
# ─────────────────────────────────────────

async def imc_nino_sexo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["sexo"] = query.data.replace("sexo_", "")
    await query.edit_message_text(
        "*IMC Niño* — Paso 2/5\n\n¿Cuántos años cumplidos tiene? (2–20, ej: 10)",
        parse_mode="Markdown"
    )
    return IMC_NINO_EDAD_ANIOS

async def imc_nino_edad_anios(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        edad = int(update.message.text.strip())
        if not (2 <= edad <= 20):
            raise ValueError
        context.user_data["edad"] = edad
    except ValueError:
        await update.message.reply_text("⚠️ Ingresa una edad entre 2 y 20 años")
        return IMC_NINO_EDAD_ANIOS
    await update.message.reply_text(
        "*IMC Niño* — Paso 3/5\n\n¿Cuántos meses adicionales? (0–11, ej: 6)",
        parse_mode="Markdown"
    )
    return IMC_NINO_EDAD_MESES

async def imc_nino_edad_meses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        meses = int(update.message.text.strip())
        if not (0 <= meses <= 11):
            raise ValueError
        context.user_data["meses"] = meses
    except ValueError:
        await update.message.reply_text("⚠️ Ingresa los meses entre 0 y 11")
        return IMC_NINO_EDAD_MESES
    await update.message.reply_text(
        "*IMC Niño* — Paso 4/5\n\n¿Cuál es la estatura en cm? (ej: 135)",
        parse_mode="Markdown"
    )
    return IMC_NINO_ALTURA

async def imc_nino_altura(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["altura"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Ingresa solo el número en cm (ej: 135)")
        return IMC_NINO_ALTURA
    await update.message.reply_text(
        "*IMC Niño* — Paso 5/5\n\n¿Cuál es el peso en kg? (ej: 32.5)",
        parse_mode="Markdown"
    )
    return IMC_NINO_PESO

async def imc_nino_peso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        peso = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Ingresa solo el número en kg (ej: 32.5)")
        return IMC_NINO_PESO

    d = context.user_data
    imc = calcular_imc(peso, d["altura"])
    sexo_txt = "Niño" if d["sexo"] == "M" else "Niña"
    edad_txt = f"{d['edad']} años {d['meses']} meses"

    # Percentiles simplificados OMS (referencia general, no reemplaza diagnóstico clínico)
    nota = (
        "⚠️ *Nota:* El IMC en niños debe interpretarse según percentiles por edad y sexo. "
        "Consulta siempre a un médico pediatra para un diagnóstico preciso."
    )

    resultado = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Resultado IMC Niño/Adolescente*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 {sexo_txt} | Edad: {edad_txt}\n"
        f"📏 Estatura: {d['altura']} cm | ⚖️ Peso: {peso} kg\n\n"
        f"🔢 *IMC: {imc}*\n\n"
        f"{nota}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
    )

    keyboard = [[InlineKeyboardButton("🔄 Nueva consulta", callback_data="reiniciar")]]
    await update.message.reply_text(resultado, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

# ─────────────────────────────────────────
# PAM
# ─────────────────────────────────────────

async def pam_sistolica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["sistolica"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Ingresa solo el número (ej: 120)")
        return PAM_SISTOLICA
    await update.message.reply_text(
        "❤️ *PAM* — Paso 2/2\n\nIngresa la *Presión Diastólica* (número inferior, ej: 80):",
        parse_mode="Markdown"
    )
    return PAM_DIASTOLICA

async def pam_diastolica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        diastolica = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ Ingresa solo el número (ej: 80)")
        return PAM_DIASTOLICA

    sistolica = context.user_data["sistolica"]
    pam = calcular_pam(sistolica, diastolica)
    clasif = clasificar_pam(pam)
    pp = round(sistolica - diastolica, 1)

    resultado = (
        f"━━━━━━━━━━━━━━━━━━\n"
        f"❤️ *Resultado PAM*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📈 Presión Sistólica: {sistolica} mmHg\n"
        f"📉 Presión Diastólica: {diastolica} mmHg\n"
        f"↔️ Presión de Pulso: {pp} mmHg\n\n"
        f"🔢 *PAM: {pam} mmHg*\n"
        f"{clasif}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"_Referencia normal: 70–100 mmHg_\n"
    )

    keyboard = [[InlineKeyboardButton("🔄 Nueva consulta", callback_data="reiniciar")]]
    await update.message.reply_text(resultado, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

# ─────────────────────────────────────────
# REINICIAR
# ─────────────────────────────────────────

async def reiniciar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    return await start(update, context)

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Operación cancelada. Usa /start para comenzar.")
    return ConversationHandler.END

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(reiniciar, pattern="^reiniciar$"),
        ],
        states={
            MENU: [CallbackQueryHandler(menu_handler)],
            # IMC Adulto
            IMC_ADULTO_SEXO:   [CallbackQueryHandler(imc_adulto_sexo, pattern="^sexo_")],
            IMC_ADULTO_EDAD:   [MessageHandler(filters.TEXT & ~filters.COMMAND, imc_adulto_edad)],
            IMC_ADULTO_ALTURA: [MessageHandler(filters.TEXT & ~filters.COMMAND, imc_adulto_altura)],
            IMC_ADULTO_PESO:   [MessageHandler(filters.TEXT & ~filters.COMMAND, imc_adulto_peso)],
            # IMC Niño
            IMC_NINO_SEXO:      [CallbackQueryHandler(imc_nino_sexo, pattern="^sexo_")],
            IMC_NINO_EDAD_ANIOS:[MessageHandler(filters.TEXT & ~filters.COMMAND, imc_nino_edad_anios)],
            IMC_NINO_EDAD_MESES:[MessageHandler(filters.TEXT & ~filters.COMMAND, imc_nino_edad_meses)],
            IMC_NINO_ALTURA:    [MessageHandler(filters.TEXT & ~filters.COMMAND, imc_nino_altura)],
            IMC_NINO_PESO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, imc_nino_peso)],
            # PAM
            PAM_SISTOLICA:  [MessageHandler(filters.TEXT & ~filters.COMMAND, pam_sistolica)],
            PAM_DIASTOLICA: [MessageHandler(filters.TEXT & ~filters.COMMAND, pam_diastolica)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    logger.info("Bot iniciado...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
