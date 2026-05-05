from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_approval_keyboard(project_id: int, user_id: int):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"admin_approve_{project_id}_{user_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"admin_reject_{project_id}_{user_id}")
            ]
        ]
    )
    return keyboard
