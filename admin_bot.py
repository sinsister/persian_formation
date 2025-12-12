# admin_panel.py - نسخه اصلاح شده
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
    waiting_champion_game_id = State()
    waiting_champion_display_name = State()
    waiting_user_action = State()
    waiting_new_username = State()
    waiting_user_id_to_add = State()
    waiting_username_for_new_user = State()

# ---------- متغیرهای سراسری ----------
db = Database()
admin_sessions = set()

# ---------- اینیشیالایز ----------
bot = Bot(token=ADMIN_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ---------- ایجاد اینلاین کیبورد همیشگی ----------
def get_persistent_inline_keyboard():
    """اینلاین کیبوردی که همیشه نمایش داده می‌شود"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
    builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
    builder.button(text="➕ ایجاد لیگ", callback_data="create_league_persistent")
    builder.button(text="📊 آمار کلی", callback_data="show_stats_persistent")
    builder.button(text="🔄 بازآوری", callback_data="refresh_admin_panel")
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()

# ---------- تالار افتخارات ----------
async def show_hall_of_fame(message_or_callback, include_persistent_keyboard=True):
    """نمایش تالار افتخارات"""
    
    champions = db.get_all_champions()
    
    if not champions:
        text = (
            "🏆 تالار افتخارات\n\n"
            "PERSIAN FORMATION🏆\n\n"
            "هنوز هیچ قهرمانی ثبت نشده است.\n"
            "برای ثبت قهرمان، ابتدا یک لیگ را غیرفعال کنید\n"
            "سپس از بخش مدیریت لیگ، قهرمان آن را تعیین کنید."
        )
    else:
        header = " قهرمان های تورنومنت ولیگ های\nPERSIAN FORMATION🏆\n\n"
        
        champions_text = ""
        for league_name, champ_game_id, champ_display, set_date in champions:
            if champ_display:
                display = f"{champ_display}"
            else:
                display = f"{champ_game_id}"
            
            champions_text += f"{league_name}: {champ_game_id}({display})🏆\n"
        
        text = header + champions_text
    
    # ترکیب کیبورد تالار افتخارات
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 به‌روزرسانی", callback_data="refresh_hall_of_fame")
    builder.button(text="➕ ثبت قهرمان جدید", callback_data="add_new_champion")
    
    if include_persistent_keyboard:
        builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
        builder.button(text="🔙 بازگشت", callback_data="back_to_admin_menu_persistent")
        builder.adjust(2, 2)
    else:
        builder.adjust(2)
    
    reply_markup = builder.as_markup()
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(
            text,
            reply_markup=reply_markup
        )
    else:
        await message_or_callback.answer(
            text,
            reply_markup=reply_markup
        )

# ---------- هندلرهای اصلی ----------

@dp.message(Command("start"))
async def admin_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id in admin_sessions:
        await message.answer(
            "👨‍💼 به پنل مدیریت خوش آمدید!\n\n"
            "از دکمه‌های زیر استفاده کنید:",
            reply_markup=get_persistent_inline_keyboard()
        )
        return
    
    await message.answer("🔐 لطفاً رمز عبور ادمین را وارد کنید:")
    await state.set_state(AdminStates.waiting_password)

@dp.message(AdminStates.waiting_password)
async def check_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    
    if password == ADMIN_PASSWORD:
        user_id = message.from_user.id
        admin_sessions.add(user_id)
        await state.clear()
        
        await message.answer(
            "✅ ورود موفق!\nبه پنل مدیریت خوش آمدید.\n\n"
            "از دکمه‌های زیر استفاده کنید:",
            reply_markup=get_persistent_inline_keyboard()
        )
    else:
        await message.answer(
            "❌ رمز عبور اشتباه است!\nلطفاً دوباره /start را بزنید."
        )
        await state.clear()

# ---------- هندلرهای inline کیبورد ----------

@dp.callback_query(F.data == "list_leagues_persistent")
async def list_leagues_persistent(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id not in admin_sessions:
        await callback.message.edit_text("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await list_leagues_handler(callback, include_persistent_keyboard=True)

@dp.callback_query(F.data == "hall_of_fame_persistent")
async def hall_of_fame_persistent(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id not in admin_sessions:
        await callback.message.edit_text("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await show_hall_of_fame(callback, include_persistent_keyboard=True)

@dp.callback_query(F.data == "create_league_persistent")
async def create_league_persistent(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id not in admin_sessions:
        await callback.message.edit_text("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await callback.message.edit_text("📝 لطفاً نام لیگ جدید را وارد کنید:")
    await state.set_state(AdminStates.waiting_league_name)

@dp.callback_query(F.data == "refresh_admin_panel")
async def refresh_admin_panel_persistent(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id not in admin_sessions:
        await callback.message.edit_text("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await callback.message.edit_text(
        "🔄 پنل بازآوری شد!\nاز دکمه‌های زیر استفاده کنید:",
        reply_markup=get_persistent_inline_keyboard()
    )

@dp.callback_query(F.data == "back_to_admin_menu_persistent")
async def back_to_admin_menu_persistent(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "👨‍💼 منوی اصلی مدیریت\n\nاز دکمه‌های زیر استفاده کنید:",
        reply_markup=get_persistent_inline_keyboard()
    )

@dp.callback_query(F.data == "refresh_hall_of_fame")
async def refresh_hall_of_fame(callback: types.CallbackQuery):
    await callback.answer()
    await show_hall_of_fame(callback, include_persistent_keyboard=True)

@dp.callback_query(F.data == "add_new_champion")
async def add_new_champion_from_hall(callback: types.CallbackQuery):
    await callback.answer()
    
    # لیگ‌های غیرفعال بدون قهرمان
    leagues = db.get_leagues_without_champion()
    
    if not leagues:
        builder = InlineKeyboardBuilder()
        builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
        builder.button(text="🔙 بازگشت", callback_data="hall_of_fame_persistent")
        builder.adjust(1)
        
        await callback.message.edit_text(
            "⚠️ هیچ لیگ غیرفعالی برای تعیین قهرمان وجود ندارد.\n\n"
            "برای تعیین قهرمان:\n"
            "1. ابتدا یک لیگ را غیرفعال کنید\n"
            "2. سپس از لیست لیگ‌ها، آن را انتخاب و قهرمان تعیین کنید",
            reply_markup=builder.as_markup()
        )
        return
    
    builder = InlineKeyboardBuilder()
    for league_id, league_name in leagues:
        builder.button(text=f"🏆 {league_name}", callback_data=f"set_champion_{league_id}")
    
    builder.button(text="🔙 بازگشت", callback_data="hall_of_fame_persistent")
    builder.adjust(1)
    
    await callback.message.edit_text(
        "👑 انتخاب لیگ برای تعیین قهرمان:\n\n"
        "لیگ‌های غیرفعال بدون قهرمان:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(F.data == "show_stats_persistent")
async def show_stats_persistent(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id not in admin_sessions:
        await callback.message.edit_text("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    stats = db.get_total_stats()
    
    total_leagues = stats.get('total_leagues', 0)
    active_leagues = stats.get('active_leagues', 0)
    total_users = stats.get('total_users', 0)
    total_champions = stats.get('total_champions', 0)
    total_capacity = stats.get('total_capacity', 0)
    total_registrations = stats.get('total_registrations', 0)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
    builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
    builder.button(text="➕ ایجاد لیگ", callback_data="create_league_persistent")
    builder.adjust(2, 1)
    
    percentage = round((total_registrations / total_capacity * 100) if total_capacity > 0 else 0, 1)
    
    await callback.message.edit_text(
        f"📊 آمار کلی سیستم:\n\n"
        f"🏆 تعداد کل لیگ‌ها: {total_leagues}\n"
        f"✅ لیگ‌های فعال: {active_leagues}\n"
        f"❌ لیگ‌های غیرفعال: {total_leagues - active_leagues}\n"
        f"👑 لیگ‌های دارای قهرمان: {total_champions}\n"
        f"👥 کاربران منحصر به فرد: {total_users}\n"
        f"📝 تعداد کل ثبت‌نام‌ها: {total_registrations}\n"
        f"📈 ظرفیت کل فعال: {total_capacity}\n"
        f"📊 درصد پر شدن: {percentage}%",
        reply_markup=builder.as_markup()
    )

# ---------- نمایش لیست لیگ‌ها ----------

async def list_leagues_handler(message_or_callback, include_persistent_keyboard=True):
    leagues = db.get_all_leagues()
    
    if not leagues:
        text = "⚠️ هنوز لیگی ایجاد نشده است."
        if include_persistent_keyboard:
            builder = InlineKeyboardBuilder()
            builder.button(text="➕ ایجاد لیگ", callback_data="create_league_persistent")
            builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
            builder.button(text="🔙 بازگشت", callback_data="back_to_admin_menu_persistent")
            builder.adjust(1)
            reply_markup = builder.as_markup()
        else:
            reply_markup = None
        
        if isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.message.edit_text(text, reply_markup=reply_markup)
        else:
            await message_or_callback.answer(text, reply_markup=reply_markup)
        return
    
    builder = InlineKeyboardBuilder()
    for league in leagues:
        league_id, name, capacity, is_active, created_at = league
        user_count = db.get_league_user_count(league_id)
        status = "✅" if is_active == 1 else "❌"
        
        # بررسی آیا قهرمان دارد
        has_champion = db.get_champion(league_id) is not None
        champion_icon = "👑" if has_champion else ""
        text = f"{status}{champion_icon} {name} ({user_count}/{capacity})"
        builder.button(text=text, callback_data=f"admin_league_{league_id}")
    
    # اضافه کردن دکمه‌های همیشگی
    if include_persistent_keyboard:
        builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
        builder.button(text="➕ ایجاد لیگ", callback_data="create_league_persistent")
        builder.button(text="📊 آمار کلی", callback_data="show_stats_persistent")
        builder.button(text="🔙 بازگشت", callback_data="back_to_admin_menu_persistent")
        builder.adjust(1, 1, 2, 1)
    else:
        builder.button(text="🔙 بازگشت", callback_data="back_to_admin_menu_persistent")
        builder.adjust(1)
    
    text = "🏆 لیست لیگ‌ها:\n\nبرای مدیریت روی یک لیگ کلیک کنید:\n👑 = دارای قهرمان\n✅ = فعال\n❌ = غیرفعال"
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message_or_callback.answer(text, reply_markup=builder.as_markup())

# ---------- مدیریت لیگ‌ها ----------

@dp.callback_query(F.data.startswith("admin_league_"))
async def manage_league(callback: types.CallbackQuery):
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        league_id = int(parts[2])
        
        if not league_id:
            await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
            return
        
        league_id, name, capacity, is_active, created_at = league_id
        user_count = db.get_league_user_count(league_id)
        status = "فعال" if is_active == 1 else "غیرفعال"
        
        # بررسی آیا قهرمان دارد
        champion_text = ""
        champion = db.get_champion(league_id)
        if champion:
            champ_game_id, champ_display, set_at, league_name = champion
            champion_text = f"\n👑 قهرمان: {champ_game_id} ({champ_display})\n📅 تاریخ: {set_at}"
        
        # دریافت لیست کاربران
        users = db.get_league_users(league_id)
        if users:
            users_list = "\n".join([f"{i+1}. {username if username else f'آیدی: {user_id}'}" 
                                   for i, (user_id, username) in enumerate(users[:10])])  # فقط 10 کاربر اول
            if len(users) > 10:
                users_list += f"\n... و {len(users) - 10} کاربر دیگر"
        else:
            users_list = "هیچ کاربری ثبت‌نام نکرده است."
        
        # ایجاد دکمه‌های مدیریت
        builder = InlineKeyboardBuilder()
        builder.button(text=f"🔄 {'غیرفعال' if is_active == 1 else 'فعال'} کردن", callback_data=f"toggle_{league_id}")
        builder.button(text="👥 مدیریت کاربران", callback_data=f"view_users_{league_id}")
        
        # بررسی وجود قهرمان برای دکمه‌ها
        has_champion = champion is not None
        
        if is_active == 0:  # فقط لیگ‌های غیرفعال می‌توانند قهرمان داشته باشند
            if has_champion:
                builder.button(text="✏️ ویرایش قهرمان", callback_data=f"edit_champion_{league_id}")
                builder.button(text="🗑️ حذف قهرمان", callback_data=f"remove_champion_{league_id}")
            else:
                builder.button(text="👑 تعیین قهرمان", callback_data=f"set_champion_{league_id}")
        
        builder.button(text="🗑️ حذف لیگ", callback_data=f"delete_league_{league_id}")
        builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
        builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
        
        # تنظیم چیدمان دکمه‌ها
        if is_active == 0 and has_champion:
            builder.adjust(2, 2, 2, 2)
        elif is_active == 0:
            builder.adjust(2, 2, 1, 2)
        else:
            builder.adjust(2, 2, 2)
        
        await callback.message.edit_text(
            f"🏆 لیگ: {name}\n"
            f"📊 ظرفیت: {user_count}/{capacity}\n"
            f"🔧 وضعیت: {status}\n"
            f"📅 تاریخ ایجاد: {created_at}{champion_text}\n\n"
            f"کاربران ثبت‌نام کرده ({user_count} نفر):\n{users_list}",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"خطا در مدیریت لیگ: {e}")
        await callback.message.edit_text("⚠️ خطا در نمایش اطلاعات لیگ!")

@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_league(callback: types.CallbackQuery):
    await callback.answer()
    
    try:
        league_id = int(callback.data.split('_')[1])
        new_status = db.toggle_league_status(league_id)
        
        if new_status is not None:
            status_text = "فعال" if new_status == 1 else "غیرفعال"
            await callback.answer(f"✅ وضعیت لیگ به '{status_text}' تغییر یافت!")
            
            # بازگشت به مدیریت لیگ
            league = db.get_league(league_id)
            if league:
                league_id, name, capacity, is_active, created_at = league
                user_count = db.get_league_user_count(league_id)
                
                # بررسی آیا قهرمان دارد
                champion_text = ""
                champion = db.get_champion(league_id)
                if champion:
                    champ_game_id, champ_display, set_at, league_name = champion
                    champion_text = f"\n👑 قهرمان: {champ_game_id} ({champ_display})"
                
                status_text = "فعال" if is_active == 1 else "غیرفعال"
                users = db.get_league_users(league_id)
                if users:
                    users_list = "\n".join([f"{i+1}. {username if username else f'آیدی: {user_id}'}" 
                                           for i, (user_id, username) in enumerate(users[:10])])
                    if len(users) > 10:
                        users_list += f"\n... و {len(users) - 10} کاربر دیگر"
                else:
                    users_list = "هیچ کاربری ثبت‌نام نکرده است."
                
                builder = InlineKeyboardBuilder()
                builder.button(text=f"🔄 {'غیرفعال' if is_active == 1 else 'فعال'} کردن", callback_data=f"toggle_{league_id}")
                builder.button(text="👥 مدیریت کاربران", callback_data=f"view_users_{league_id}")
                
                has_champion = champion is not None
                
                if is_active == 0:
                    if has_champion:
                        builder.button(text="✏️ ویرایش قهرمان", callback_data=f"edit_champion_{league_id}")
                        builder.button(text="🗑️ حذف قهرمان", callback_data=f"remove_champion_{league_id}")
                    else:
                        builder.button(text="👑 تعیین قهرمان", callback_data=f"set_champion_{league_id}")
                
                builder.button(text="🗑️ حذف لیگ", callback_data=f"delete_league_{league_id}")
                builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
                builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
                
                if is_active == 0 and has_champion:
                    builder.adjust(2, 2, 2, 2)
                elif is_active == 0:
                    builder.adjust(2, 2, 1, 2)
                else:
                    builder.adjust(2, 2, 2)
                
                await callback.message.edit_text(
                    f"🏆 لیگ: {name}\n"
                    f"📊 ظرفیت: {user_count}/{capacity}\n"
                    f"🔧 وضعیت: {status_text}{champion_text}\n"
                    f"📅 تاریخ ایجاد: {created_at}\n\n"
                    f"کاربران ثبت‌نام کرده ({user_count} نفر):\n{users_list}",
                    reply_markup=builder.as_markup()
                )
        else:
            await callback.message.edit_text("⚠️ خطا در تغییر وضعیت لیگ!")
    except Exception as e:
        logger.error(f"خطا در تغییر وضعیت لیگ: {e}")
        await callback.message.edit_text("⚠️ خطا در تغییر وضعیت لیگ!")

# ---------- مدیریت کاربران ----------

@dp.callback_query(F.data.startswith("view_users_"))
async def view_users(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    try:
        league_id = int(callback.data.split('_')[2])
        league = db.get_league(league_id)
        
        if not league:
            await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
            return
        
        users = db.get_league_users(league_id)
        
        if not users:
            users_text = "هیچ کاربری ثبت‌نام نکرده است."
            builder = InlineKeyboardBuilder()
            builder.button(text="➕ افزودن کاربر", callback_data=f"add_user_{league_id}")
            builder.button(text="🔙 بازگشت", callback_data=f"admin_league_{league_id}")
            builder.adjust(2)
        else:
            users_text = "\n".join([f"{i+1}. {username if username else f'آیدی: {user_id}'}" 
                                   for i, (user_id, username) in enumerate(users)])
            
            builder = InlineKeyboardBuilder()
            
            # دکمه‌های ویرایش برای هر کاربر
            for user_id, username in users[:15]:  # حداکثر 15 کاربر
                display_name = username if username else str(user_id)
                if len(display_name) > 20:
                    display_name = display_name[:20] + "..."
                builder.button(text=f"✏️ {display_name}", callback_data=f"edit_user_{league_id}_{user_id}")
            
            builder.button(text="➕ افزودن کاربر", callback_data=f"add_user_{league_id}")
            builder.button(text="🔙 بازگشت به مدیریت", callback_data=f"admin_league_{league_id}")
            builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
            
            if len(users) <= 5:
                builder.adjust(1, 2, 1)
            else:
                builder.adjust(2, 2, 1)
        
        await callback.message.edit_text(
            f"👥 کاربران لیگ '{league[1]}' ({len(users)} نفر):\n\n"
            f"{users_text}\n\n"
            f"برای ویرایش یا حذف روی کاربر مورد نظر کلیک کنید:",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"خطا در نمایش کاربران: {e}")
        await callback.message.edit_text("⚠️ خطا در نمایش کاربران!")

@dp.callback_query(F.data.startswith("edit_user_"))
async def edit_user_options(callback: types.CallbackQuery):
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.message.edit_text("⚠️ خطا در شناسایی کاربر!")
            return
        
        league_id = int(parts[2])
        user_id = '_'.join(parts[3:])  # چون user_id می‌تواند شامل _ باشد
        
        user_info = db.get_user_info(league_id, user_id)
        if not user_info:
            await callback.message.edit_text("⚠️ کاربر پیدا نشد!")
            return
        
        league = db.get_league(league_id)
        league_name = league[1] if league else "لیگ"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✏️ تغییر نام کاربری", callback_data=f"change_username_{league_id}_{user_id}")
        builder.button(text="🗑️ حذف کاربر از لیگ", callback_data=f"delete_user_{league_id}_{user_id}")
        builder.button(text="🔙 بازگشت به لیست کاربران", callback_data=f"view_users_{league_id}")
        builder.adjust(2, 1)
        
        await callback.message.edit_text(
            f"⚙️ مدیریت کاربر:\n\n"
            f"🏆 لیگ: {league_name}\n"
            f"👤 آیدی کاربر: {user_id}\n"
            f"📛 نام کاربری: {user_info[1] if user_info[1] else 'ندارد'}\n\n"
            f"عملیات مورد نظر را انتخاب کنید:",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"خطا در ویرایش کاربر: {e}")
        await callback.message.edit_text("⚠️ خطا در نمایش اطلاعات کاربر!")

@dp.callback_query(F.data.startswith("change_username_"))
async def change_username_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.message.edit_text("⚠️ خطا در شناسایی کاربر!")
            return
        
        league_id = int(parts[2])
        user_id = '_'.join(parts[3:])
        
        user_info = db.get_user_info(league_id, user_id)
        if not user_info:
            await callback.message.edit_text("⚠️ کاربر پیدا نشد!")
            return
        
        await state.update_data(
            changing_username_league_id=league_id,
            changing_username_user_id=user_id,
            current_username=user_info[1]
        )
        
        await callback.message.edit_text(
            f"✏️ تغییر نام کاربری\n\n"
            f"آیدی کاربر: {user_id}\n"
            f"نام فعلی: {user_info[1] if user_info[1] else 'ندارد'}\n\n"
            f"لطفاً نام کاربری جدید را وارد کنید:"
        )
        
        await state.set_state(AdminStates.waiting_new_username)
    except Exception as e:
        logger.error(f"خطا در شروع تغییر نام کاربری: {e}")
        await callback.message.edit_text("⚠️ خطا در تغییر نام کاربری!")

@dp.message(AdminStates.waiting_new_username)
async def save_new_username(message: types.Message, state: FSMContext):
    new_username = message.text.strip()
    
    if not new_username:
        await message.answer("❌ نام کاربری نمی‌تواند خالی باشد. لطفاً دوباره وارد کنید:")
        return
    
    if len(new_username) > 50:
        await message.answer("❌ نام کاربری نباید بیشتر از ۵۰ کاراکتر باشد. لطفاً دوباره وارد کنید:")
        return
    
    data = await state.get_data()
    league_id = data.get('changing_username_league_id')
    user_id = data.get('changing_username_user_id')
    
    if not league_id or not user_id:
        await message.answer("❌ خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.")
        await state.clear()
        return
    
    success = db.update_user_username(league_id, user_id, new_username)
    
    if success:
        await message.answer(
            f"✅ نام کاربری با موفقیت به '{new_username}' تغییر یافت!",
            reply_markup=get_persistent_inline_keyboard()
        )
    else:
        await message.answer(
            "❌ خطا در تغییر نام کاربری!",
            reply_markup=get_persistent_inline_keyboard()
        )
    
    await state.clear()

@dp.callback_query(F.data.startswith("delete_user_"))
async def delete_user_confirmation(callback: types.CallbackQuery):
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.message.edit_text("⚠️ خطا در شناسایی کاربر!")
            return
        
        league_id = int(parts[2])
        user_id = '_'.join(parts[3:])
        
        user_info = db.get_user_info(league_id, user_id)
        if not user_info:
            await callback.message.edit_text("⚠️ کاربر پیدا نشد!")
            return
        
        league = db.get_league(league_id)
        league_name = league[1] if league else "لیگ"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ بله، حذف کن", callback_data=f"confirm_delete_user_{league_id}_{user_id}")
        builder.button(text="❌ خیر، انصراف", callback_data=f"edit_user_{league_id}_{user_id}")
        builder.adjust(2)
        
        await callback.message.edit_text(
            f"⚠️ آیا مطمئن هستید می‌خواهید این کاربر را از لیگ حذف کنید؟\n\n"
            f"🏆 لیگ: {league_name}\n"
            f"👤 آیدی کاربر: {user_id}\n"
            f"📛 نام کاربری: {user_info[1] if user_info[1] else 'ندارد'}\n\n"
            f"❌ این عمل قابل بازگشت نیست!",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"خطا در تایید حذف کاربر: {e}")
        await callback.message.edit_text("⚠️ خطا در تایید حذف کاربر!")

@dp.callback_query(F.data.startswith("confirm_delete_user_"))
async def delete_user_final(callback: types.CallbackQuery):
    await callback.answer()
    
    try:
        parts = callback.data.split('_')
        if len(parts) < 4:
            await callback.message.edit_text("⚠️ خطا در شناسایی کاربر!")
            return
        
        league_id = int(parts[2])
        user_id = '_'.join(parts[3:])
        
        user_info = db.get_user_info(league_id, user_id)
        if not user_info:
            await callback.message.edit_text("⚠️ کاربر پیدا نشد!")
            return
        
        league = db.get_league(league_id)
        league_name = league[1] if league else "لیگ"
        
        success = db.remove_user_from_league(league_id, user_id)
        
        if success:
            builder = InlineKeyboardBuilder()
            builder.button(text="🔙 بازگشت به لیست کاربران", callback_data=f"view_users_{league_id}")
            builder.button(text="🏆 مدیریت لیگ", callback_data=f"admin_league_{league_id}")
            builder.adjust(1)
            
            await callback.message.edit_text(
                f"✅ کاربر با موفقیت از لیگ حذف شد!\n\n"
                f"🏆 لیگ: {league_name}\n"
                f"👤 آیدی کاربر: {user_id}\n"
                f"📛 نام کاربری: {user_info[1] if user_info[1] else 'ندارد'}",
                reply_markup=builder.as_markup()
            )
        else:
            await callback.message.edit_text("❌ خطا در حذف کاربر!")
    except Exception as e:
        logger.error(f"خطا در حذف کاربر: {e}")
        await callback.message.edit_text("⚠️ خطا در حذف کاربر!")

# ---------- افزودن کاربر جدید ----------

@dp.callback_query(F.data.startswith("add_user_"))
async def add_user_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    try:
        league_id = int(callback.data.split('_')[2])
        league = db.get_league(league_id)
        
        if not league:
            await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
            return
        
        # بررسی ظرفیت لیگ
        user_count = db.get_league_user_count(league_id)
        if user_count >= league[2]:  # capacity
            await callback.message.edit_text("🚫 ظرفیت این لیگ تکمیل شده است!")
            return
        
        await state.update_data(add_user_league_id=league_id)
        await callback.message.edit_text(
            f"➕ افزودن کاربر جدید به لیگ '{league[1]}'\n\n"
            f"لطفاً آیدی کاربر را وارد کنید (می‌تواند عددی یا متنی باشد):"
        )
        
        await state.set_state(AdminStates.waiting_user_id_to_add)
    except Exception as e:
        logger.error(f"خطا در شروع افزودن کاربر: {e}")
        await callback.message.edit_text("⚠️ خطا در افزودن کاربر!")

@dp.message(AdminStates.waiting_user_id_to_add)
async def get_user_id_for_add(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    
    if not user_id:
        await message.answer("❌ آیدی کاربر نمی‌تواند خالی باشد. لطفاً دوباره وارد کنید:")
        return
    
    if len(user_id) > 100:
        await message.answer("❌ آیدی کاربر نباید بیشتر از ۱۰۰ کاراکتر باشد. لطفاً دوباره وارد کنید:")
        return
    
    data = await state.get_data()
    league_id = data.get('add_user_league_id')
    
    if not league_id:
        await message.answer("❌ خطا در دریافت اطلاعات لیگ.")
        await state.clear()
        return
    
    # بررسی آیا کاربر قبلاً در این لیگ ثبت‌نام کرده
    if db.is_user_in_league(user_id, league_id):
        await message.answer("⚠️ این کاربر قبلاً در این لیگ ثبت‌نام کرده است!")
        await state.clear()
        return
    
    await state.update_data(add_user_id=user_id)
    
    league = db.get_league(league_id)
    league_name = league[1] if league else "لیگ"
    
    await message.answer(
        f"👤 آیدی کاربر: {user_id}\n"
        f"🏆 لیگ: {league_name}\n\n"
        f"لطفاً نام کاربری (نام نمایشی) را وارد کنید:"
    )
    
    await state.set_state(AdminStates.waiting_username_for_new_user)

@dp.message(AdminStates.waiting_username_for_new_user)
async def save_new_user(message: types.Message, state: FSMContext):
    username = message.text.strip()
    
    if not username:
        await message.answer("❌ نام کاربری نمی‌تواند خالی باشد. لطفاً دوباره وارد کنید:")
        return
    
    if len(username) > 50:
        await message.answer("❌ نام کاربری نباید بیشتر از ۵۰ کاراکتر باشد. لطفاً دوباره وارد کنید:")
        return
    
    data = await state.get_data()
    league_id = data.get('add_user_league_id')
    user_id = data.get('add_user_id')
    
    if not league_id or not user_id:
        await message.answer("❌ خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.")
        await state.clear()
        return
    
    # ثبت کاربر
    success = db.register_user(user_id, username, league_id)
    
    if success:
        league = db.get_league(league_id)
        league_name = league[1] if league else "لیگ"
        
        await message.answer(
            f"✅ کاربر با موفقیت به لیگ اضافه شد!\n\n"
            f"🏆 لیگ: {league_name}\n"
            f"👤 آیدی: {user_id}\n"
            f"📛 نام کاربری: {username}",
            reply_markup=get_persistent_inline_keyboard()
        )
    else:
        await message.answer(
            "❌ خطا در افزودن کاربر! ممکن است:\n"
            "1. کاربر قبلاً در لیگ ثبت‌نام کرده باشد\n"
            "2. لیگ غیرفعال شده باشد\n"
            "3. ظرفیت لیگ تکمیل شده باشد",
            reply_markup=get_persistent_inline_keyboard()
        )
    
    await state.clear()

# ---------- مدیریت قهرمانان ----------

@dp.callback_query(F.data.startswith("set_champion_"))
async def set_champion_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    try:
        league_id = int(callback.data.split('_')[2])
        league = db.get_league(league_id)
        
        if not league:
            await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
            return
        
        # بررسی آیا لیگ فعال است (نباید باشد)
        if league[3] == 1:  # is_active = 1
            await callback.message.edit_text("⚠️ ابتدا باید لیگ را غیرفعال کنید!")
            return
        
        await state.update_data(set_champion_league_id=league_id)
        await callback.message.edit_text(
            f"👑 تعیین قهرمان برای لیگ '{league[1]}'\n\n"
            f"لطفاً آیدی بازی قهرمان را وارد کنید:"
        )
        
        await state.set_state(AdminStates.waiting_champion_game_id)
    except Exception as e:
        logger.error(f"خطا در شروع تعیین قهرمان: {e}")
        await callback.message.edit_text("⚠️ خطا در تعیین قهرمان!")

@dp.message(AdminStates.waiting_champion_game_id)
async def get_champion_game_id(message: types.Message, state: FSMContext):
    game_id = message.text.strip()
    
    if not game_id:
        await message.answer("❌ آیدی بازی نمی‌تواند خالی باشد. لطفاً دوباره وارد کنید:")
        return
    
    await state.update_data(champion_game_id=game_id)
    
    await message.answer(
        f"👤 آیدی بازی: {game_id}\n\n"
        f"لطفاً نام نمایشی قهرمان را وارد کنید (اختیاری):\n"
        f"اگر نام نمایشی ندارید، فقط Enter بزنید."
    )
    
    await state.set_state(AdminStates.waiting_champion_display_name)

@dp.message(AdminStates.waiting_champion_display_name)
async def get_champion_display_name(message: types.Message, state: FSMContext):
    display_name = message.text.strip()
    
    data = await state.get_data()
    league_id = data.get('set_champion_league_id')
    game_id = data.get('champion_game_id')
    admin_id = message.from_user.id
    
    if not league_id or not game_id:
        await message.answer("❌ خطا در دریافت اطلاعات. لطفاً دوباره تلاش کنید.")
        await state.clear()
        return
    
    # ذخیره قهرمان
    success = db.set_champion(league_id, game_id, display_name if display_name else "", admin_id)
    
    if success:
        league = db.get_league(league_id)
        league_name = league[1] if league else "لیگ"
        
        display_text = f" ({display_name})" if display_name else ""
        
        await message.answer(
            f"✅ قهرمان با موفقیت ثبت شد!\n\n"
            f"🏆 لیگ: {league_name}\n"
            f"👑 قهرمان: {game_id}{display_text}",
            reply_markup=get_persistent_inline_keyboard()
        )
    else:
        await message.answer(
            "❌ خطا در ثبت قهرمان!",
            reply_markup=get_persistent_inline_keyboard()
        )
    
    await state.clear()

@dp.callback_query(F.data.startswith("edit_champion_"))
async def edit_champion_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    try:
        league_id = int(callback.data.split('_')[2])
        league = db.get_league(league_id)
        champion = db.get_champion(league_id)
        
        if not league:
            await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
            return
        
        if not champion:
            await callback.message.edit_text("⚠️ این لیگ قهرمان ندارد!")
            return
        
        champ_game_id, champ_display, set_at, league_name = champion
        
        await state.update_data(
            edit_champion_league_id=league_id,
            current_game_id=champ_game_id,
            current_display=champ_display
        )
        
        await callback.message.edit_text(
            f"✏️ ویرایش قهرمان لیگ '{league[1]}'\n\n"
            f"آیدی بازی فعلی: {champ_game_id}\n"
            f"نام نمایشی فعلی: {champ_display if champ_display else 'ندارد'}\n\n"
            f"لطفاً آیدی بازی جدید را وارد کنید:"
        )
        
        await state.set_state(AdminStates.waiting_champion_game_id)
    except Exception as e:
        logger.error(f"خطا در شروع ویرایش قهرمان: {e}")
        await callback.message.edit_text("⚠️ خطا در ویرایش قهرمان!")

@dp.callback_query(F.data.startswith("remove_champion_"))
async def remove_champion_confirmation(callback: types.CallbackQuery):
    await callback.answer()
    
    try:
        league_id = int(callback.data.split('_')[2])
        league = db.get_league(league_id)
        champion = db.get_champion(league_id)
        
        if not league:
            await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
            return
        
        if not champion:
            await callback.message.edit_text("⚠️ این لیگ قهرمان ندارد!")
            return
        
        champ_game_id, champ_display, set_at, league_name = champion
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ بله، حذف کن", callback_data=f"confirm_remove_champion_{league_id}")
        builder.button(text="❌ خیر، انصراف", callback_data=f"admin_league_{league_id}")
        builder.adjust(2)
        
        display_text = f" ({champ_display})" if champ_display else ""
        
        await callback.message.edit_text(
            f"⚠️ آیا مطمئن هستید می‌خواهید قهرمان این لیگ را حذف کنید؟\n\n"
            f"🏆 لیگ: {league[1]}\n"
            f"👑 قهرمان: {champ_game_id}{display_text}\n\n"
            f"❌ این عمل قابل بازگشت نیست!",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"خطا در تایید حذف قهرمان: {e}")
        await callback.message.edit_text("⚠️ خطا در تایید حذف قهرمان!")

@dp.callback_query(F.data.startswith("confirm_remove_champion_"))
async def remove_champion_final(callback: types.CallbackQuery):
    await callback.answer()
    
    try:
        league_id = int(callback.data.split('_')[2])
        league = db.get_league(league_id)
        
        if not league:
            await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
            return
        
        success = db.remove_champion(league_id)
        
        if success:
            await callback.message.edit_text(
                f"✅ قهرمان لیگ '{league[1]}' با موفقیت حذف شد!",
                reply_markup=get_persistent_inline_keyboard()
            )
        else:
            await callback.message.edit_text("❌ خطا در حذف قهرمان!")
    except Exception as e:
        logger.error(f"خطا در حذف قهرمان: {e}")
        await callback.message.edit_text("⚠️ خطا در حذف قهرمان!")

# ---------- حذف لیگ ----------

@dp.callback_query(F.data.startswith("delete_league_"))
async def delete_league_confirmation(callback: types.CallbackQuery):
    await callback.answer()
    
    try:
        # دریافت league_id (از index 3)
        parts = callback.data.split('_')
        league_id = int(parts[2])  # "delete_league_123" → index 2
        league = db.get_league(league_id)
        
        if not league:
            await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
            return
        
        user_count = db.get_league_user_count(league_id)
        champion = db.get_champion(league_id)
        
        warning_text = ""
        if user_count > 0:
            warning_text += f"\n⚠️ این لیگ {user_count} کاربر دارد که همگی حذف خواهند شد!"
        
        if champion:
            warning_text += f"\n⚠️ این لیگ دارای قهرمان است که حذف خواهد شد!"
        
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ بله، حذف کن", callback_data=f"confirm_delete_league_{league_id}")
        builder.button(text="❌ خیر، انصراف", callback_data=f"admin_league_{league_id}")
        builder.adjust(2)
        
        await callback.message.edit_text(
            f"⚠️ آیا مطمئن هستید می‌خواهید این لیگ را حذف کنید؟\n\n"
            f"🏆 لیگ: {league[1]}\n"
            f"📊 ظرفیت: {league[2]}\n"
            f"👥 کاربران: {user_count}{warning_text}\n\n"
            f"❌ این عمل قابل بازگشت نیست!",
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logger.error(f"خطا در تایید حذف لیگ: {e}")
        await callback.message.edit_text("⚠️ خطا در تایید حذف لیگ!")
@dp.callback_query(F.data.startswith("confirm_delete_league_"))
async def delete_league_final(callback: types.CallbackQuery):
    await callback.answer()
    
    try:
        # دریافت league_id (از index 3)
        parts = callback.data.split('_')
        league_id = int(parts[3])  # "confirm_delete_league_123" → index 3
        league = db.get_league(league_id)
        
        if not league:
            await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
            return
        
        league_name = league[1]
        success = db.delete_league(league_id)
        
        if success:
            await callback.message.edit_text(
                f"✅ لیگ '{league_name}' با موفقیت حذف شد!",
                reply_markup=get_persistent_inline_keyboard()
            )
        else:
            await callback.message.edit_text("❌ خطا در حذف لیگ!")
    except (IndexError, ValueError) as e:
        logger.error(f"خطا در پارس کردن league_id: {e}")
        logger.error(f"callback.data: {callback.data}")
        logger.error(f"parts: {callback.data.split('_')}")
        await callback.message.edit_text("⚠️ خطا در شناسایی لیگ!")
    except Exception as e:
        logger.error(f"خطا در حذف لیگ: {e}")
        await callback.message.edit_text("⚠️ خطا در حذف لیگ!")
# ---------- ایجاد لیگ ----------

@dp.message(AdminStates.waiting_league_name)
async def get_league_name(message: types.Message, state: FSMContext):
    league_name = message.text.strip()
    
    if not league_name:
        await message.answer("❌ نام لیگ نمی‌تواند خالی باشد. لطفاً دوباره وارد کنید:")
        return
    
    if len(league_name) > 100:
        await message.answer("❌ نام لیگ نباید بیشتر از ۱۰۰ کاراکتر باشد. لطفاً دوباره وارد کنید:")
        return
    
    await state.update_data(new_league_name=league_name)
    await message.answer("🔢 لطفاً ظرفیت لیگ را وارد کنید (عدد):")
    await state.set_state(AdminStates.waiting_league_capacity)

@dp.message(AdminStates.waiting_league_capacity)
async def get_league_capacity(message: types.Message, state: FSMContext):
    try:
        capacity = int(message.text.strip())
        if capacity <= 0:
            await message.answer("⚠️ ظرفیت باید بزرگتر از صفر باشد. لطفاً دوباره وارد کنید:")
            return
        
        if capacity > 1000:
            await message.answer("⚠️ ظرفیت نمی‌تواند بیشتر از ۱۰۰۰ باشد. لطفاً دوباره وارد کنید:")
            return
        
        data = await state.get_data()
        league_name = data.get('new_league_name')
        league_id = db.create_league(league_name, capacity)
        
        if league_id > 0:
            await message.answer(
                f"✅ لیگ '{league_name}' با ظرفیت {capacity} ایجاد شد!",
                reply_markup=get_persistent_inline_keyboard()
            )
        else:
            await message.answer(
                "❌ خطا در ایجاد لیگ!",
                reply_markup=get_persistent_inline_keyboard()
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer("⚠️ لطفاً یک عدد صحیح و مثبت وارد کنید:")

# ---------- تابع لغو ----------
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ عملیات لغو شد.", reply_markup=get_persistent_inline_keyboard())

# ---------- هندلر برای پیام‌های غیرمنتظره ----------
@dp.message()
async def handle_unexpected_messages(message: types.Message, state: FSMContext):
    """هندلر برای پیام‌های غیرمنتظره"""
    current_state = await state.get_state()
    
    if current_state:
        # اگر در حالتی هستیم، پیام لغو بفرست
        await cancel_command(message, state)
    else:
        # اگر در حالتی نیستیم، منوی اصلی را نشان بده
        user_id = message.from_user.id
        if user_id in admin_sessions:
            await message.answer(
                "لطفاً از دکمه‌های منوی اصلی استفاده کنید:",
                reply_markup=get_persistent_inline_keyboard()
            )
        else:
            await message.answer("لطفاً با دستور /start شروع کنید.")

# ---------- تابع اصلی اجرا ----------
async def main():
    print("🤖 ربات ادمین با aiogram در حال راه‌اندازی...")
    print("✅ اینلاین کیبورد همیشگی فعال شد")
    print("✅ تالار افتخارات با آیدی بازی (هر چیزی) اضافه شد")
    print("✅ مدیریت کامل لیگ‌ها و کاربران فعال شد")
    print("✅ تمام توابع database اضافه شدند")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"خطا در اجرای ربات ادمین: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    asyncio.run(main())