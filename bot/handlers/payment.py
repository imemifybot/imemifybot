from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.states import BuilderState
from keyboards.inline import get_payment_keyboard, get_start_keyboard
from keyboards.admin import get_admin_approval_keyboard
from database.db import add_transaction, tx_exists, log_activity
from services.bscscan import REQUIRED_AMOUNT_USDT, WALLET_ADDRESS
import os
import logging

router = Router()
logger = logging.getLogger(__name__)

ADMIN_ID = os.getenv("ADMIN_ID")
SOL_WALLET_ADDRESS = os.getenv("SOL_WALLET_ADDRESS")
TRC_WALLET_ADDRESS = os.getenv("TRC_WALLET_ADDRESS")



@router.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery, state: FSMContext):
    project_id = int(callback.data.split("_")[1])

    log_activity(callback.from_user.id, "payment_started", f"project_{project_id}")

    text = (
        f"💳 **Payment Instructions**\n\n"
        f"Price: `{REQUIRED_AMOUNT_USDT} USDT / SOL Equivalent`\n\n"
        f"**Tether (USDT - TRC20):**\n"
        f"`{TRC_WALLET_ADDRESS}`\n\n"
        f"**BNB Smart Chain (BEP20):**\n"
        f"`{WALLET_ADDRESS}`\n\n"
        f"**Solana (SOL):**\n"
        f"`{SOL_WALLET_ADDRESS}`\n\n"
        "Send the exact amount and then click **I Paid** to verify.\n"
        "*(For Solana, send the equivalent value in SOL)*"
    )
    await callback.answer()

    try:
        await callback.message.edit_caption(
            caption=text, parse_mode="Markdown",
            reply_markup=get_payment_keyboard(project_id)
        )
    except Exception:
        try:
            await callback.message.edit_text(
                text, parse_mode="Markdown",
                reply_markup=get_payment_keyboard(project_id)
            )
        except Exception:
            await callback.message.answer(
                text, parse_mode="Markdown",
                reply_markup=get_payment_keyboard(project_id)
            )

@router.callback_query(F.data.startswith("verify_tx_"))
async def verify_tx_start(callback: CallbackQuery, state: FSMContext):
    project_id = int(callback.data.removeprefix("verify_tx_"))
    await state.update_data(project_id=project_id)
    await state.set_state(BuilderState.tx_hash)
    await callback.answer()

    text = (
        "🔗 Please send me the **Transaction Hash (TxID)** of your payment:\n\n"
        "*(Type it in the chat and send)*"
    )
    try:
        await callback.message.edit_caption(caption=text, parse_mode="Markdown")
    except Exception:
        try:
            await callback.message.edit_text(text, parse_mode="Markdown")
        except Exception:
            await callback.message.answer(text, parse_mode="Markdown")


@router.message(BuilderState.tx_hash)
async def verify_tx_hash(message: Message, state: FSMContext):
    tx_hash = message.text.strip()
    data = await state.get_data()
    project_id = data.get("project_id")

    if not project_id:
        await message.answer(
            "Error: Project ID not found. Please start over.",
            reply_markup=get_start_keyboard()
        )
        await state.clear()
        return

    if tx_exists(tx_hash):
        await message.answer(
            "⚠️ This transaction hash has already been used. Please provide a new one."
        )
        return

    # Save transaction as unverified
    add_transaction(tx_hash, message.from_user.id, REQUIRED_AMOUNT_USDT, False)

    await message.answer(
        "⏳ **Payment Submitted!**\n\n"
        "Your transaction is pending admin verification.\n"
        "You will be notified once approved and your site is deployed.",
        parse_mode="Markdown"
    )

    # Notify Admin
    try:
        admin_id = int(os.getenv("ADMIN_ID", "0"))
    except ValueError:
        admin_id = 0
    if admin_id:
        try:
            await message.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🔔 **New Payment Verification Request**\n\n"
                    f"**User ID:** `{message.from_user.id}`\n"
                    f"**Project ID:** `{project_id}`\n"
                    f"**Amount Expected:** `{REQUIRED_AMOUNT_USDT} USDT`\n"
                    f"**Tx Hash:**\n`{tx_hash}`\n\n"
                    "Please verify this transaction manually."
                ),
                parse_mode="Markdown",
                reply_markup=get_admin_approval_keyboard(project_id, message.from_user.id)
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")

    await state.clear()
