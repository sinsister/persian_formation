# main_aiogram.py
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder, ReplyKeyboardMarkup
from config import MAIN_BOT_TOKEN, CHANNEL_USERNAME
from database import Database

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- تعریف حالت‌های FSM ----------
class UserStates(StatesGroup):
    waiting_username = State()

# ---------- متغیرهای سراسری ----------
db = Database()

# ---------- اینیشیالایز ----------
bot = Bot(token=MAIN_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------- ایجاد دکمه‌های پایین صفحه ----------
def get_main_keyboard() -> ReplyKeyboardMarkup:
    """ایجاد کیبورد اصلی برای پایین صفحه"""
    builder = ReplyKeyboardBuilder()
    
    builder.button(text="🏆 لیگ‌های فعال")
    builder.button(text="🔄 بررسی عضویت")
    builder.button(text="📊 وضعیت من")
    builder.button(text="👑 تالار افتخارات")
    builder.button(text="ℹ️ راهنما")
    
    builder.adjust(2, 2, 1)
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False
    )

# ---------- تابع بررسی عضویت در کانال ----------
async def check_membership(user_id: int) -> bool:
    """
    بررسی می‌کند کاربر در کانال عضو است یا نه
    """
    try:
        # حذف @ از اول USERNAME اگر وجود دارد
        channel = CHANNEL_USERNAME.lstrip('@')
        
        # بررسی عضویت
        chat_member = await bot.get_chat_member(
            chat_id=f"@{channel}",
            user_id=user_id
        )
        
        # وضعیت‌های مجاز
        allowed_statuses = ['member', 'administrator', 'creator']
        return chat_member.status in allowed_statuses
        
    except Exception as e:
        logger.error(f"خطا در بررسی عضویت برای کاربر {user_id}: {e}")
        
        # اگر خطای "chat not found" بود، یعنی ربات ادمین نیست
        if "chat not found" in str(e).lower() or "forbidden" in str(e).lower():
            logger.error("ربات در کانال ادمین نیست یا کانال وجود ندارد!")
        
        return False

# ---------- تالار افتخارات برای کاربران ----------
async def show_hall_of_fame_to_user(message_or_callback):
    """نمایش تالار افتخارات برای کاربران عادی"""
    
    champions = db.get_all_champions()
    
    if not champions:
        text = (
            "🏆 *تالار افتخارات*\n\n"
            "𝐏𝐄𝐑𝐒𝐈𝐀𝐍 𝐅𝐎𝐑𝐌𝐀𝐓𝐈𝐎𝐍🏆\n\n"
            "هنوز هیچ قهرمانی ثبت نشده است.\n"
            "به زودی قهرمانان لیگ‌ها مشخص می‌شوند."
        )
    else:
        header = "🏆 *قهرمان های تورنومنت ولی های های*\n𝐏𝐄𝐑𝐒𝐈𝐀𝐍 𝐅𝐎𝐑𝐌𝐀𝐓𝐈𝐎𝐍🏆\n\n"
        
        champions_text = ""
        for league_name, champ_username, champ_display, set_date in champions:
            if champ_display:
                display = f"{champ_display}"
            else:
                display = f"{champ_username}"
            
            # اگر champ_username با @ شروع نشده، اضافه کن
            if champ_username and not champ_username.startswith('@'):
                username_display = f"@{champ_username}"
            else:
                username_display = champ_username
            
            champions_text += f"{league_name}: {username_display}({display})🏆\n"
        
        text = header + champions_text
    
    # کیبورد برای بازگشت
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔙 بازگشت به منو")
    builder.adjust(1)
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.answer(
            text, 
            parse_mode='Markdown',
            reply_markup=builder.as_markup()
        )
    else:
        await message_or_callback.answer(
            text, 
            parse_mode='Markdown',
            reply_markup=builder.as_markup()
        )

# ---------- هندلر بررسی عضویت ----------
async def handle_membership_check(message: types.Message):
    """بررسی عضویت و نمایش نتیجه"""
    user_id = message.from_user.id
    
    # چک کردن عضویت
    is_member = await check_membership(user_id)
    
    if is_member:
        await message.answer(
            "✅ شما در کانال عضو هستید!\n"
            "اکنون می‌توانید از امکانات ربات استفاده کنید.",
            reply_markup=get_main_keyboard()
        )
    else:
        # ایجاد دکمه عضویت
        builder = InlineKeyboardBuilder()
        builder.button(
            text="عضویت در کانال", 
            url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
        )
        builder.button(
            text="🔄 بررسی مجدد",
            callback_data="check_again"
        )
        builder.adjust(1)
        
        await message.answer(
            "❌ شما در کانال عضو نیستید!\n\n"
            f"لطفاً در کانال {CHANNEL_USERNAME} عضو شوید "
            "سپس دکمه 'بررسی مجدد' را بزنید.",
            reply_markup=builder.as_markup()
        )

# ---------- هندلر برای دکمه "🔄 بررسی عضویت" ----------
@dp.message(F.text == "🔄 بررسی عضویت")
async def check_membership_button(message: types.Message):
    """هندلر دکمه بررسی عضویت"""
    await handle_membership_check(message)

# ---------- هندلر برای دکمه "🔙 بازگشت به منو" ----------
@dp.message(F.text == "🔙 بازگشت به منو")
async def back_to_menu(message: types.Message):
    """بازگشت به منوی اصلی"""
    await message.answer(
        "منوی اصلی:",
        reply_markup=get_main_keyboard()
    )

# ---------- کالبک برای بررسی مجدد ----------
@dp.callback_query(F.data == "check_again")
async def check_again_callback(callback: types.CallbackQuery):
    """بررسی مجدد عضویت پس از کلیک کاربر"""
    await callback.answer()
    await handle_membership_check(callback.message)

# ---------- دستور /start ----------
@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    """دستور شروع - ابتدا عضویت را بررسی می‌کند"""
    user_id = message.from_user.id
    
    await message.answer(
        "🤖 به ربات لیگ‌های فوتبال خوش آمدید!\n\n"
        "در حال بررسی عضویت شما در کانال..."
    )
    
    # بررسی عضویت
    is_member = await check_membership(user_id)
    
    if is_member:
        await message.answer(
            "✅ تأیید عضویت انجام شد!\n\n"
            "اکنون می‌توانید از دکمه‌های زیر استفاده کنید:",
            reply_markup=get_main_keyboard()
        )
        
        # اگر کاربر قبلاً ثبت‌نام کرده، پیام اضافه
        if db.is_user_registered(user_id):
            await message.answer(
                "📝 شما قبلاً ثبت‌نام کرده‌اید. "
                "برای مشاهده وضعیت از دکمه '📊 وضعیت من' استفاده کنید."
            )
    else:
        # کاربر عضو نیست
        builder = InlineKeyboardBuilder()
        builder.button(
            text="عضویت در کانال", 
            url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
        )
        builder.button(
            text="🔄 بررسی مجدد",
            callback_data="check_again"
        )
        builder.adjust(1)
        
        await message.answer(
            f"⚠️ برای استفاده از ربات باید در کانال عضو شوید.\n\n"
            f"کانال: {CHANNEL_USERNAME}\n"
            f"پس از عضویت، دکمه 'بررسی مجدد' را بزنید.",
            reply_markup=builder.as_markup()
        )

# ---------- هندلر برای دکمه "🏆 لیگ‌های فعال" ----------
@dp.message(F.text == "🏆 لیگ‌های فعال")
async def show_active_leagues(message: types.Message):
    """نمایش لیگ‌های فعال فقط برای اعضای کانال"""
    user_id = message.from_user.id
    
    # بررسی عضویت
    if not await check_membership(user_id):
        await message.answer(
            "❌ ابتدا باید در کانال عضو شوید.\n"
            "از دکمه '🔄 بررسی عضویت' استفاده کنید."
        )
        return
    
    # بررسی ثبت‌نام قبلی
    if db.is_user_registered(user_id):
        await message.answer(
            "✅ شما قبلاً ثبت‌نام کرده‌اید!\n"
            "هر کاربر فقط می‌تواند یک بار ثبت‌نام کند."
        )
        return
    
    # نمایش لیگ‌های فعال
    leagues = db.get_active_leagues()
    if not leagues:
        await message.answer("⚠️ در حال حاضر هیچ لیگ فعالی وجود ندارد.")
        return
    
    # ایجاد دکمه‌های اینلاین
    builder = InlineKeyboardBuilder()
    for league_id, league_name in leagues:
        user_count = db.get_league_user_count(league_id)
        league_data = db.get_league(league_id)
        capacity = league_data[2] if league_data else 0
        
        if user_count >= capacity:
            text = f"🚫 {league_name} (تکمیل)"
        else:
            text = f"🎮 {league_name} ({user_count}/{capacity})"
        
        builder.button(text=text, callback_data=f"league_{league_id}")
    
    builder.adjust(1)
    
    await message.answer(
        "🏆 لیگ‌های فعال:\n\n"
        "لطفاً یک لیگ را انتخاب کنید:",
        reply_markup=builder.as_markup()
    )

# ---------- هندلر برای دکمه "📊 وضعیت من" ----------
@dp.message(F.text == "📊 وضعیت من")
async def show_my_status(message: types.Message):
    user_id = message.from_user.id
    
    # بررسی عضویت
    if not await check_membership(user_id):
        await message.answer(
            "❌ ابتدا باید در کانال عضو شوید.\n"
            "از دکمه '🔄 بررسی عضویت' استفاده کنید."
        )
        return
    
    # بررسی آیا کاربر ثبت‌نام کرده
    if not db.is_user_registered(user_id):
        await message.answer(
            "📝 شما هنوز ثبت‌نام نکرده‌اید.\n"
            "برای ثبت‌نام از دکمه '🏆 لیگ‌های فعال' استفاده کنید."
        )
        return
    
    # پیدا کردن اطلاعات کاربر
    cursor = db.conn.cursor()
    cursor.execute(
        "SELECT u.username, l.name, l.capacity, u.registered_at, l.id FROM users u "
        "JOIN leagues l ON u.league_id = l.id WHERE u.user_id = ?",
        (user_id,)
    )
    user_data = cursor.fetchone()
    
    if user_data:
        username, league_name, capacity, registered_at, league_id = user_data
        # پیدا کردن تعداد کاربران این لیگ
        user_count = db.get_league_user_count(league_id)
        
        # بررسی آیا لیگ قهرمان دارد
        champion_info = ""
        try:
            champion = db.get_champion(league_id)
            if champion:
                champ_username, champ_display, set_at, champ_league_name = champion
                champion_info = f"\n👑 قهرمان لیگ: @{champ_username} ({champ_display})"
        except:
            pass
        
        await message.answer(
            f"📊 وضعیت شما:\n\n"
            f"👤 نام کاربری: {username}\n"
            f"🏆 لیگ: {league_name}\n"
            f"👥 وضعیت لیگ: {user_count}/{capacity}\n"
            f"📅 تاریخ ثبت‌نام: {registered_at}\n"
            f"{champion_info}\n\n"
            f"✅ ثبت‌نام شما تأیید شده است."
        )
    else:
        await message.answer("⚠️ اطلاعات شما یافت نشد.")

# ---------- هندلر برای دکمه "👑 تالار افتخارات" ----------
@dp.message(F.text == "👑 تالار افتخارات")
async def hall_of_fame_button(message: types.Message):
    """نمایش تالار افتخارات برای کاربران"""
    user_id = message.from_user.id
    
    # بررسی عضویت
    if not await check_membership(user_id):
        await message.answer(
            "❌ ابتدا باید در کانال عضو شوید.\n"
            "از دکمه '🔄 بررسی عضویت' استفاده کنید."
        )
        return
    
    await show_hall_of_fame_to_user(message)

# ---------- هندلر برای دکمه "ℹ️ راهنما" ----------
@dp.message(F.text == "ℹ️ راهنما")
async def show_help(message: types.Message):
    help_text = (
        "📖 راهنمای استفاده از ربات:\n\n"
        "1. ابتدا باید در کانال عضو شوید\n"
        "2. برای تأیید عضویت از دکمه '🔄 بررسی عضویت' استفاده کنید\n"
        "3. برای ثبت‌نام در لیگ از '🏆 لیگ‌های فعال' استفاده کنید\n"
        "4. هر کاربر فقط می‌تواند یک بار ثبت‌نام کند\n"
        "5. برای مشاهده وضعیت خود از '📊 وضعیت من' استفاده کنید\n"
        "6. برای مشاهده قهرمانان از '👑 تالار افتخارات' استفاده کنید\n\n"
        "⚠️ توجه: پس از تکمیل ظرفیت یک لیگ، امکان ثبت‌نام وجود ندارد.\n"
        "لیگ‌های تکمیل شده بعداً قهرمان مشخص می‌کنند."
    )
    await message.answer(help_text)

# ---------- انتخاب لیگ ----------
@dp.callback_query(F.data.startswith("league_"))
async def select_league(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    league_id = int(callback.data.split('_')[1])
    league = db.get_league(league_id)
    
    if not league or league[3] == 0:
        await callback.message.edit_text("⚠️ این لیگ دیگر فعال نیست.")
        return
    
    user_count = db.get_league_user_count(league_id)
    if user_count >= league[2]:
        await callback.message.edit_text("🚫 این لیگ تکمیل شده است.")
        return
    
    await state.update_data(selected_league=league_id)
    await callback.message.edit_text(
        f"🏆 لیگ: {league[1]}\n\n"
        "لطفاً نام کاربری خود در بازی را وارد کنید:"
    )
    await state.set_state(UserStates.waiting_username)

# ---------- دریافت نام کاربری ----------
@dp.message(UserStates.waiting_username)
async def get_username(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.text.strip()
    
    data = await state.get_data()
    league_id = data.get('selected_league')
    
    if not league_id:
        await message.answer("خطایی رخ داده است. لطفاً دوباره /start را بزنید.")
        await state.clear()
        return
    
    if db.register_user(user_id, username, league_id):
        await message.answer(
            "✅ ثبت‌نام شما با موفقیت انجام شد!\n\n"
            f"نام کاربری: {username}\n"
            "منتظر اطلاع‌رسانی‌های بعدی باشید.",
            reply_markup=get_main_keyboard()
        )
        
        # نمایش تالار افتخارات همزمان
        champions = db.get_all_champions()
        if champions:
            await message.answer(
                "🏆 حتماً تالار افتخارات را بررسی کنید تا قهرمانان قبلی را ببینید!",
                reply_markup=get_main_keyboard()
            )
    else:
        await message.answer(
            "⚠️ شما قبلاً ثبت‌نام کرده‌اید!",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()

# ---------- تابع لغو ----------
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ عملیات لغو شد.", reply_markup=get_main_keyboard())

# ---------- تابع اصلی اجرا ----------
async def main():
    print("🤖 ربات اصلی با aiogram در حال راه‌اندازی...")
    print(f"📢 کانال مورد بررسی: {CHANNEL_USERNAME}")
    print("✅ تالار افتخارات اضافه شد")
    print("⚠️ نکته: مطمئن شوید ربات در کانال ادمین است!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())