# admin_bot_aiogram.py
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder, ReplyKeyboardMarkup
from config import ADMIN_BOT_TOKEN, ADMIN_PASSWORD
from database import Database

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- تعریف حالت‌های FSM ----------
class AdminStates(StatesGroup):
    waiting_password = State()
    waiting_league_name = State()
    waiting_league_capacity = State()
    waiting_delete_confirmation = State()

# ---------- متغیرهای سراسری ----------
db = Database()
admin_sessions = set()

# ---------- اینیشیالایز ----------
bot = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------- ایجاد کیبورد پایین صفحه برای ادمین ----------
def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """ایجاد کیبورد پایین صفحه برای پنل ادمین"""
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="📋 لیست لیگ‌ها")
    builder.button(text="➕ ایجاد لیگ")
    builder.button(text="🔄 بازآوری پنل")
    builder.button(text="📊 آمار کلی")
    
    builder.adjust(2, 2)
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False
    )

# ---------- هندلرها ----------

# دستور /start با کیبورد پایین صفحه
@dp.message(Command("start"))
async def admin_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id in admin_sessions:
        await message.answer(
            "👨‍💼 به پنل مدیریت خوش آمدید!",
            reply_markup=get_admin_keyboard()
        )
        return
    
    await message.answer("🔐 لطفاً رمز عبور ادمین را وارد کنید:")
    await state.set_state(AdminStates.waiting_password)

# بررسی رمز عبور
@dp.message(AdminStates.waiting_password)
async def check_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    
    if password == ADMIN_PASSWORD:
        user_id = message.from_user.id
        admin_sessions.add(user_id)
        await state.clear()
        await message.answer(
            "✅ ورود موفق!\nبه پنل مدیریت خوش آمدید.",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("❌ رمز عبور اشتباه است!\nلطفاً دوباره /start را بزنید.")
        await state.clear()

# دکمه "📋 لیست لیگ‌ها"
@dp.message(F.text == "📋 لیست لیگ‌ها")
async def list_leagues_button(message: types.Message):
    user_id = message.from_user.id
    if user_id not in admin_sessions:
        await message.answer("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await list_leagues_handler(message)

# نمایش لیست لیگ‌ها (اینلاین)
async def list_leagues_handler(message_or_callback):
    leagues = db.get_all_leagues()
    
    if not leagues:
        if isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.message.edit_text("⚠️ هنوز لیگی ایجاد نشده است.")
        else:
            await message_or_callback.answer("⚠️ هنوز لیگی ایجاد نشده است.")
        return
    
    builder = InlineKeyboardBuilder()
    for league in leagues:
        league_id, name, capacity, is_active = league
        user_count = db.get_league_user_count(league_id)
        status = "✅" if is_active == 1 else "❌"
        text = f"{status} {name} ({user_count}/{capacity})"
        builder.button(text=text, callback_data=f"admin_league_{league_id}")
    
    builder.button(text="🔙 بازگشت به منو", callback_data="back_to_menu")
    builder.adjust(1)
    
    text = "🏆 لیست لیگ‌ها:\n\nبرای مدیریت روی یک لیگ کلیک کنید:"
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message_or_callback.answer(text, reply_markup=builder.as_markup())

# دکمه "➕ ایجاد لیگ"
@dp.message(F.text == "➕ ایجاد لیگ")
async def create_league_button(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in admin_sessions:
        await message.answer("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await message.answer("📝 لطفاً نام لیگ جدید را وارد کنید:")
    await state.set_state(AdminStates.waiting_league_name)

# مدیریت لیگ (جزئیات)
@dp.callback_query(F.data.startswith("admin_league_"))
async def manage_league(callback: types.CallbackQuery):
    await callback.answer()
    
    league_id = int(callback.data.split('_')[2])
    league = db.get_league(league_id)
    
    if not league:
        await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
        return
    
    league_id, name, capacity, is_active, created_at = league
    user_count = db.get_league_user_count(league_id)
    status = "فعال" if is_active == 1 else "غیرفعال"
    
    # دریافت لیست کاربران بدون @
    users = db.get_league_users(league_id)
    if users:
        users_list = "\n".join([f"{i+1}. {username if username else f'آیدی: {user_id}'}" 
                               for i, (user_id, username) in enumerate(users)])
    else:
        users_list = "هیچ کاربری ثبت‌نام نکرده است."
    
    # ایجاد دکمه‌های مدیریت (اینلاین)
    builder = InlineKeyboardBuilder()
    builder.button(text=f"🔄 {'غیرفعال' if is_active == 1 else 'فعال'} کردن", callback_data=f"toggle_{league_id}")
    builder.button(text="👥 مشاهده کاربران", callback_data=f"view_users_{league_id}")
    builder.button(text="🗑️ حذف لیگ", callback_data=f"delete_league_{league_id}")
    builder.button(text="🔙 بازگشت به لیست", callback_data="list_leagues_callback")
    builder.adjust(2, 2)
    
    await callback.message.edit_text(
        f"🏆 لیگ: {name}\n"
        f"📊 ظرفیت: {user_count}/{capacity}\n"
        f"🔧 وضعیت: {status}\n"
        f"📅 تاریخ ایجاد: {created_at}\n\n"
        f"کاربران ثبت‌نام کرده ({user_count} نفر):\n{users_list}",
        reply_markup=builder.as_markup()
    )

# تغییر وضعیت لیگ
@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_league(callback: types.CallbackQuery):
    await callback.answer()
    
    league_id = int(callback.data.split('_')[1])
    new_status = db.toggle_league_status(league_id)
    
    if new_status is not None:
        status_text = "فعال" if new_status == 1 else "غیرفعال"
        # بازگشت به مدیریت لیگ
        league = db.get_league(league_id)
        if league:
            league_id, name, capacity, is_active, created_at = league
            user_count = db.get_league_user_count(league_id)
            status = "فعال" if is_active == 1 else "غیرفعال"
            
            users = db.get_league_users(league_id)
            if users:
                users_list = "\n".join([f"{i+1}. {username if username else f'آیدی: {user_id}'}" 
                                       for i, (user_id, username) in enumerate(users)])
            else:
                users_list = "هیچ کاربری ثبت‌نام نکرده است."
            
            builder = InlineKeyboardBuilder()
            builder.button(text=f"🔄 {'غیرفعال' if is_active == 1 else 'فعال'} کردن", callback_data=f"toggle_{league_id}")
            builder.button(text="👥 مشاهده کاربران", callback_data=f"view_users_{league_id}")
            builder.button(text="🗑️ حذف لیگ", callback_data=f"delete_league_{league_id}")
            builder.button(text="🔙 بازگشت به لیست", callback_data="list_leagues_callback")
            builder.adjust(2, 2)
            
            await callback.message.edit_text(
                f"✅ وضعیت لیگ به '{status_text}' تغییر یافت!\n\n"
                f"🏆 لیگ: {name}\n"
                f"📊 ظرفیت: {user_count}/{capacity}\n"
                f"🔧 وضعیت: {status}\n"
                f"📅 تاریخ ایجاد: {created_at}\n\n"
                f"کاربران ثبت‌نام کرده ({user_count} نفر):\n{users_list}",
                reply_markup=builder.as_markup()
            )
    else:
        await callback.message.edit_text("⚠️ خطا در تغییر وضعیت لیگ!")

# مشاهده کاربران لیگ (جداگانه)
@dp.callback_query(F.data.startswith("view_users_"))
async def view_users(callback: types.CallbackQuery):
    await callback.answer()
    
    league_id = int(callback.data.split('_')[2])
    league = db.get_league(league_id)
    
    if not league:
        await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
        return
    
    users = db.get_league_users(league_id)
    
    if not users:
        users_text = "هیچ کاربری ثبت‌نام نکرده است."
    else:
        users_text = "\n".join([f"{i+1}. {username if username else f'آیدی: {user_id}'}" 
                               for i, (user_id, username) in enumerate(users)])
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 بازگشت به مدیریت", callback_data=f"admin_league_{league_id}")
    
    await callback.message.edit_text(
        f"👥 کاربران لیگ '{league[1]}':\n\n{users_text}",
        reply_markup=builder.as_markup()
    )

# حذف لیگ - تایید اولیه
@dp.callback_query(F.data.startswith("delete_league_"))
async def delete_league_confirmation(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    league_id = int(callback.data.split('_')[2])
    league = db.get_league(league_id)
    
    if not league:
        await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
        return
    
    # ذخیره اطلاعات برای حذف
    await state.update_data(league_to_delete=league_id)
    
    # دریافت تعداد کاربران این لیگ
    user_count = db.get_league_user_count(league_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ بله، حذف کن", callback_data=f"confirm_delete_{league_id}")
    builder.button(text="❌ خیر، انصراف", callback_data=f"admin_league_{league_id}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        f"⚠️ آیا مطمئن هستید می‌خواهید لیگ '{league[1]}' را حذف کنید؟\n\n"
        f"📊 اطلاعات:\n"
        f"• ظرفیت: {league[2]}\n"
        f"• کاربران ثبت‌نام کرده: {user_count} نفر\n"
        f"• وضعیت: {'فعال' if league[3] == 1 else 'غیرفعال'}\n\n"
        f"❌ این عمل قابل بازگشت نیست!",
        reply_markup=builder.as_markup()
    )

# حذف نهایی لیگ
@dp.callback_query(F.data.startswith("confirm_delete_"))
async def delete_league_final(callback: types.CallbackQuery):
    await callback.answer()
    
    league_id = int(callback.data.split('_')[2])
    league = db.get_league(league_id)
    
    if not league:
        await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
        return
    
    league_name = league[1]
    
    try:
        # حذف کاربران این لیگ اول
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM users WHERE league_id = ?", (league_id,))
        
        # سپس حذف لیگ
        cursor.execute("DELETE FROM leagues WHERE id = ?", (league_id,))
        db.conn.commit()
        
        await callback.message.edit_text(
            f"✅ لیگ '{league_name}' با موفقیت حذف شد!\n"
            f"تمامی کاربران مرتبط نیز حذف شدند."
        )
        
        # برگشت به لیست لیگ‌ها بعد از 2 ثانیه
        await asyncio.sleep(2)
        await list_leagues_handler(callback)
        
    except Exception as e:
        logger.error(f"خطا در حذف لیگ: {e}")
        await callback.message.edit_text(f"❌ خطا در حذف لیگ: {str(e)}")

# بازگشت به لیست لیگ‌ها
@dp.callback_query(F.data == "list_leagues_callback")
async def list_leagues_callback(callback: types.CallbackQuery):
    await callback.answer()
    await list_leagues_handler(callback)

# بازگشت به منو اصلی
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.answer()
    if isinstance(callback, types.CallbackQuery):
        await callback.message.edit_text(
            "👨‍💼 منوی اصلی مدیریت\n\nاز دکمه‌های پایین صفحه استفاده کنید:",
            reply_markup=None
        )

# دکمه "🔄 بازآوری پنل"
@dp.message(F.text == "🔄 بازآوری پنل")
async def refresh_panel(message: types.Message):
    user_id = message.from_user.id
    if user_id not in admin_sessions:
        await message.answer("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await message.answer(
        "✅ پنل بازآوری شد!\nاز دکمه‌های پایین صفحه استفاده کنید:",
        reply_markup=get_admin_keyboard()
    )

# دکمه "📊 آمار کلی"
@dp.message(F.text == "📊 آمار کلی")
async def show_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id not in admin_sessions:
        await message.answer("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    # آمار کلی
    cursor = db.conn.cursor()
    
    # تعداد کل لیگ‌ها
    cursor.execute("SELECT COUNT(*) FROM leagues")
    total_leagues = cursor.fetchone()[0]
    
    # لیگ‌های فعال
    cursor.execute("SELECT COUNT(*) FROM leagues WHERE is_active = 1")
    active_leagues = cursor.fetchone()[0]
    
    # تعداد کل کاربران
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    # ظرفیت کل
    cursor.execute("SELECT SUM(capacity) FROM leagues WHERE is_active = 1")
    total_capacity = cursor.fetchone()[0] or 0
    
    await message.answer(
        f"📊 آمار کلی سیستم:\n\n"
        f"🏆 تعداد کل لیگ‌ها: {total_leagues}\n"
        f"✅ لیگ‌های فعال: {active_leagues}\n"
        f"❌ لیگ‌های غیرفعال: {total_leagues - active_leagues}\n"
        f"👥 کاربران ثبت‌نام کرده: {total_users}\n"
        f"📈 ظرفیت کل فعال: {total_capacity}\n"
        f"📊 درصد پر شدن: {round((total_users / total_capacity * 100) if total_capacity > 0 else 0, 1)}%"
    )

# دریافت نام لیگ
@dp.message(AdminStates.waiting_league_name)
async def get_league_name(message: types.Message, state: FSMContext):
    league_name = message.text.strip()
    await state.update_data(new_league_name=league_name)
    await message.answer("🔢 لطفاً ظرفیت لیگ را وارد کنید (عدد):")
    await state.set_state(AdminStates.waiting_league_capacity)

# دریافت ظرفیت و ایجاد لیگ
@dp.message(AdminStates.waiting_league_capacity)
async def get_league_capacity(message: types.Message, state: FSMContext):
    try:
        capacity = int(message.text.strip())
        if capacity <= 0:
            raise ValueError
        
        data = await state.get_data()
        league_name = data.get('new_league_name')
        league_id = db.create_league(league_name, capacity)
        
        await message.answer(
            f"✅ لیگ '{league_name}' با ظرفیت {capacity} ایجاد شد!",
            reply_markup=get_admin_keyboard()
        )
        
        # پاک کردن حالت
        await state.clear()
        
    except ValueError:
        await message.answer("⚠️ لطفاً یک عدد صحیح و مثبت وارد کنید:")

# تابع لغو (دستور /cancel)
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ عملیات لغو شد.", reply_markup=get_admin_keyboard())

# ---------- تابع اصلی اجرا ----------
async def main():
    print("🤖 ربات ادمین با aiogram در حال راه‌اندازی...")
    print("✅ کیبورد پایین صفحه فعال شد")
    print("✅ قابلیت حذف لیگ اضافه شد")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())