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
    waiting_champion_game_id = State()  # فقط آیدی بازی
    waiting_champion_display_name = State()

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
    builder.button(text="🏆 تالار افتخارات")
    builder.button(text="📊 آمار کلی")
    
    builder.adjust(2, 2)
    
    return builder.as_markup(
        resize_keyboard=True,
        one_time_keyboard=False
    )

# ---------- ایجاد اینلاین کیبورد همیشگی ----------
def get_persistent_inline_keyboard():
    """اینلاین کیبوردی که همیشه نمایش داده می‌شود"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
    builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
    builder.button(text="➕ ایجاد لیگ", callback_data="create_league_persistent")
    builder.button(text="🔄 بازآوری", callback_data="refresh_admin_panel")
    
    builder.adjust(2, 2)
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
        # ایجاد متن تالار افتخارات - بدون Markdown مشکل‌ساز
        header = " قهرمان های تورنومنت ولیگ های\nPERSIAN FORMATION🏆\n\n"
        
        champions_text = ""
        for league_name, champ_game_id, champ_display, set_date in champions:
            if champ_display:
                display = f"{champ_display}"
            else:
                display = f"{champ_game_id}"
            
            # اضافه کردن کاراکتر ایمن
            champions_text += f"{league_name}: {champ_game_id}({display})🏆\n"
        
        text = header + champions_text
    
    # ترکیب کیبورد تالار افتخارات با کیبورد همیشگی
    if include_persistent_keyboard:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 به‌روزرسانی", callback_data="refresh_hall_of_fame")
        builder.button(text="➕ ثبت قهرمان جدید", callback_data="add_new_champion")
        builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
        builder.button(text="🔙 بازگشت", callback_data="back_to_admin_menu_persistent")
        builder.adjust(2, 2)
        reply_markup = builder.as_markup()
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 به‌روزرسانی", callback_data="refresh_hall_of_fame")
        builder.button(text="➕ ثبت قهرمان جدید", callback_data="add_new_champion")
        builder.adjust(1)
        reply_markup = builder.as_markup()
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(
            text,  # ❌ حذف parse_mode='Markdown'
            reply_markup=reply_markup
        )
    else:
        await message_or_callback.answer(
            text,  # ❌ حذف parse_mode='Markdown'
            reply_markup=reply_markup
        )
# ---------- هندلرهای اصلی با اینلاین کیبورد همیشگی ----------

# دستور /start با اینلاین کیبورد همیشگی
@dp.message(Command("start"))
async def admin_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    
    if user_id in admin_sessions:
        await message.answer(
            "👨‍💼 به پنل مدیریت خوش آمدید!\n\n"
            "از دکمه‌های زیر استفاده کنید:",
            reply_markup=get_persistent_inline_keyboard()
        )
        # تالار افتخارات را هم نمایش بده
        await show_hall_of_fame(message, include_persistent_keyboard=True)
        return
    
    await message.answer("🔐 لطفاً رمز عبور ادمین را وارد کنید:")
    await state.set_state(AdminStates.waiting_password)

# بررسی رمز عبور با اینلاین کیبورد
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
        # تالار افتخارات را نمایش بده
        await show_hall_of_fame(message, include_persistent_keyboard=True)
    else:
        await message.answer(
            "❌ رمز عبور اشتباه است!\nلطفاً دوباره /start را بزنید.",
            reply_markup=get_persistent_inline_keyboard()
        )
        await state.clear()

# اینلاین کیبورد همیشگی - لیست لیگ‌ها
@dp.callback_query(F.data == "list_leagues_persistent")
async def list_leagues_persistent(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id not in admin_sessions:
        await callback.message.edit_text("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await list_leagues_handler(callback, include_persistent_keyboard=True)

# اینلاین کیبورد همیشگی - تالار افتخارات
@dp.callback_query(F.data == "hall_of_fame_persistent")
async def hall_of_fame_persistent(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id not in admin_sessions:
        await callback.message.edit_text("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await show_hall_of_fame(callback, include_persistent_keyboard=True)

# اینلاین کیبورد همیشگی - ایجاد لیگ
@dp.callback_query(F.data == "create_league_persistent")
async def create_league_persistent(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    if user_id not in admin_sessions:
        await callback.message.edit_text("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await callback.message.edit_text("📝 لطفاً نام لیگ جدید را وارد کنید:")
    await state.set_state(AdminStates.waiting_league_name)

# اینلاین کیبورد همیشگی - بازآوری
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

# نمایش لیست لیگ‌ها (اینلاین) با کیبورد همیشگی
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
        league_id, name, capacity, is_active = league
        user_count = db.get_league_user_count(league_id)
        status = "✅" if is_active == 1 else "❌"
        
        # بررسی آیا قهرمان دارد
        has_champion = False
        try:
            champion = db.get_champion(league_id)
            has_champion = champion is not None
        except Exception as e:
            logger.error(f"خطا در بررسی قهرمان لیگ {league_id}: {e}")
            has_champion = False
        
        champion_icon = "👑" if has_champion else ""
        text = f"{status}{champion_icon} {name} ({user_count}/{capacity})"
        builder.button(text=text, callback_data=f"admin_league_{league_id}")
    
    # اضافه کردن دکمه‌های همیشگی
    if include_persistent_keyboard:
        builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
        builder.button(text="➕ ایجاد لیگ", callback_data="create_league_persistent")
        builder.button(text="🔙 بازگشت", callback_data="back_to_admin_menu_persistent")
        builder.adjust(1, 1, 2)
    else:
        builder.button(text="🔙 بازگشت", callback_data="back_to_admin_menu")
        builder.adjust(1)
    
    text = "🏆 لیست لیگ‌ها:\n\nبرای مدیریت روی یک لیگ کلیک کنید:\n👑 = دارای قهرمان"
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await message_or_callback.answer(text, reply_markup=builder.as_markup())

# مدیریت لیگ (جزئیات) با کیبورد همیشگی
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
    
    # بررسی آیا قهرمان دارد
    champion_text = ""
    try:
        champion = db.get_champion(league_id)
        if champion:
            champ_game_id, champ_display, set_at, league_name = champion
            champion_text = f"\n👑 قهرمان: {champ_game_id} ({champ_display})\n📅 تاریخ: {set_at}"
    except Exception as e:
        logger.error(f"خطا در دریافت قهرمان لیگ {league_id}: {e}")
    
    # دریافت لیست کاربران
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
    
    # بررسی وجود قهرمان برای دکمه‌ها
    has_champion = False
    try:
        champion = db.get_champion(league_id)
        has_champion = champion is not None
    except:
        has_champion = False
    
    if is_active == 0:  # فقط لیگ‌های غیرفعال می‌توانند قهرمان داشته باشند
        if has_champion:
            builder.button(text="✏️ ویرایش قهرمان", callback_data=f"edit_champion_{league_id}")
            builder.button(text="🗑️ حذف قهرمان", callback_data=f"remove_champion_{league_id}")
        else:
            builder.button(text="👑 تعیین قهرمان", callback_data=f"set_champion_{league_id}")
    
    builder.button(text="🗑️ حذف لیگ", callback_data=f"delete_league_{league_id}")
    
    # دکمه‌های همیشگی
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
        f"🔧 وضعیت: {status}{champion_text}\n"
        f"📅 تاریخ ایجاد: {created_at}\n\n"
        f"کاربران ثبت‌نام کرده ({user_count} نفر):\n{users_list}",
        reply_markup=builder.as_markup()
    )

# تعیین قهرمان برای لیگ - دریافت آیدی بازی (هر چیزی)
@dp.callback_query(F.data.startswith("set_champion_"))
async def set_champion_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    league_id = int(callback.data.split('_')[2])
    league = db.get_league(league_id)
    
    if not league:
        await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
        return
    
    # ذخیره اطلاعات لیگ
    await state.update_data(champion_league_id=league_id, champion_league_name=league[1])
    
    await callback.message.edit_text(
        f"👑 تعیین قهرمان برای لیگ: {league[1]}\n\n"
        f"لطفاً **آیدی بازی** قهرمان را وارد کنید (هر چیزی می‌تواند باشد):"
    )
    
    await state.set_state(AdminStates.waiting_champion_game_id)

# ویرایش قهرمان - دریافت آیدی بازی جدید
@dp.callback_query(F.data.startswith("edit_champion_"))
async def edit_champion_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    
    league_id = int(callback.data.split('_')[2])
    league = db.get_league(league_id)
    
    if not league:
        await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
        return
    
    # دریافت قهرمان فعلی
    champion = db.get_champion(league_id)
    if not champion:
        await callback.message.edit_text("⚠️ این لیگ قهرمان ندارد!")
        return
    
    champ_game_id, champ_display, set_at, league_name = champion
    
    # ذخیره اطلاعات
    await state.update_data(
        champion_league_id=league_id,
        champion_league_name=league[1],
        existing_game_id=champ_game_id,
        existing_display=champ_display
    )
    
    await callback.message.edit_text(
        f"✏️ ویرایش قهرمان لیگ: {league[1]}\n\n"
        f"قهرمان فعلی: {champ_game_id} ({champ_display})\n\n"
        f"لطفاً **آیدی بازی جدید** را وارد کنید (هر چیزی می‌تواند باشد):"
    )
    
    await state.set_state(AdminStates.waiting_champion_game_id)

# دریافت آیدی بازی قهرمان (هر چیزی می‌تواند باشد)
@dp.message(AdminStates.waiting_champion_game_id)
async def get_champion_game_id(message: types.Message, state: FSMContext):
    game_id = message.text.strip()
    
    if not game_id:
        await message.answer("❌ آیدی بازی نمی‌تواند خالی باشد. لطفاً دوباره وارد کنید:")
        return
    
    await state.update_data(champion_game_id=game_id)
    
    data = await state.get_data()
    league_name = data.get('champion_league_name', 'لیگ')
    
    await message.answer(
        f"👑 قهرمان {league_name}\n\n"
        f"آیدی بازی: {game_id}\n\n"
        f"لطفاً نام نمایشی قهرمان را وارد کنید (مثلاً 'amir'):"
    )
    
    await state.set_state(AdminStates.waiting_champion_display_name)

# دریافت نام نمایشی و ذخیره قهرمان
@dp.message(AdminStates.waiting_champion_display_name)
async def get_champion_display_name(message: types.Message, state: FSMContext):
    display_name = message.text.strip()
    
    if not display_name:
        await message.answer("❌ نام نمایشی نمی‌تواند خالی باشد. لطفاً دوباره وارد کنید:")
        return
    
    data = await state.get_data()
    league_id = data.get('champion_league_id')
    league_name = data.get('champion_league_name')
    game_id = data.get('champion_game_id')
    is_edit = 'existing_game_id' in data
    
    if not league_id or not game_id:
        await message.answer("❌ خطایی رخ داده است. لطفاً دوباره شروع کنید.")
        await state.clear()
        return
    
    # ذخیره قهرمان در دیتابیس (با آیدی بازی)
    success = db.set_champion(league_id, game_id, display_name, message.from_user.id)
    
    if success:
        action = "ویرایش" if is_edit else "ثبت"
        
        # ایجاد اینلاین کیبورد همیشگی برای بازگشت
        builder = InlineKeyboardBuilder()
        builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
        builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
        builder.button(text="➕ ایجاد لیگ", callback_data="create_league_persistent")
        builder.adjust(2, 1)
        
        await message.answer(
            f"✅ {action} قهرمان با موفقیت انجام شد!\n\n"
            f"🏆 لیگ: {league_name}\n"
            f"👑 قهرمان: {game_id} ({display_name})\n\n"
            f"اکنون در تالار افتخارات نمایش داده می‌شود.",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer("❌ خطا در ذخیره قهرمان. لطفاً دوباره تلاش کنید.")
    
    await state.clear()

# اینلاین کیبورد همیشگی - بازگشت به منو
@dp.callback_query(F.data == "back_to_admin_menu_persistent")
async def back_to_admin_menu_persistent(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "👨‍💼 منوی اصلی مدیریت\n\nاز دکمه‌های زیر استفاده کنید:",
        reply_markup=get_persistent_inline_keyboard()
    )

# ---------- توابع موجود (با تغییرات لازم) ----------

# تغییر وضعیت لیگ
@dp.callback_query(F.data.startswith("toggle_"))
async def toggle_league(callback: types.CallbackQuery):
    await callback.answer()
    
    league_id = int(callback.data.split('_')[1])
    new_status = db.toggle_league_status(league_id)
    
    if new_status is not None:
        status_text = "فعال" if new_status == 1 else "غیرفعال"
        # برگشت به مدیریت لیگ
        league = db.get_league(league_id)
        if league:
            league_id, name, capacity, is_active, created_at = league
            user_count = db.get_league_user_count(league_id)
            
            # بررسی آیا قهرمان دارد
            champion_text = ""
            try:
                champion = db.get_champion(league_id)
                if champion:
                    champ_game_id, champ_display, set_at, league_name = champion
                    champion_text = f"\n👑 قهرمان: {champ_game_id} ({champ_display})"
            except:
                pass
            
            users = db.get_league_users(league_id)
            if users:
                users_list = "\n".join([f"{i+1}. {username if username else f'آیدی: {user_id}'}" 
                                       for i, (user_id, username) in enumerate(users)])
            else:
                users_list = "هیچ کاربری ثبت‌نام نکرده است."
            
            builder = InlineKeyboardBuilder()
            builder.button(text=f"🔄 {'غیرفعال' if is_active == 1 else 'فعال'} کردن", callback_data=f"toggle_{league_id}")
            builder.button(text="👥 مشاهده کاربران", callback_data=f"view_users_{league_id}")
            
            # بررسی وجود قهرمان برای دکمه‌ها
            has_champion = False
            try:
                champion = db.get_champion(league_id)
                has_champion = champion is not None
            except:
                has_champion = False
            
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
                f"✅ وضعیت لیگ به '{status_text}' تغییر یافت!{champion_text}\n\n"
                f"🏆 لیگ: {name}\n"
                f"📊 ظرفیت: {user_count}/{capacity}\n"
                f"🔧 وضعیت: {'فعال' if is_active == 1 else 'غیرفعال'}\n"
                f"📅 تاریخ ایجاد: {created_at}\n\n"
                f"کاربران ثبت‌نام کرده ({user_count} نفر):\n{users_list}",
                reply_markup=builder.as_markup()
            )
    else:
        await callback.message.edit_text("⚠️ خطا در تغییر وضعیت لیگ!")

# مشاهده کاربران لیگ
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
    builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
    builder.adjust(1)
    
    await callback.message.edit_text(
        f"👥 کاربران لیگ '{league[1]}':\n\n{users_text}",
        reply_markup=builder.as_markup()
    )

# حذف لیگ - تایید اولیه
@dp.callback_query(F.data.startswith("delete_league_"))
async def delete_league_confirmation(callback: types.CallbackQuery):
    await callback.answer()
    
    league_id = int(callback.data.split('_')[2])
    league = db.get_league(league_id)
    
    if not league:
        await callback.message.edit_text("⚠️ لیگ پیدا نشد!")
        return
    
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
        # حذف قهرمان این لیگ اول (اگر وجود دارد)
        db.remove_champion(league_id)
        
        # سپس حذف کاربران
        cursor = db.conn.cursor()
        cursor.execute("DELETE FROM users WHERE league_id = ?", (league_id,))
        
        # سپس حذف لیگ
        cursor.execute("DELETE FROM leagues WHERE id = ?", (league_id,))
        db.conn.commit()
        
        await callback.message.edit_text(
            f"✅ لیگ '{league_name}' با موفقیت حذف شد!\n"
            f"تمامی کاربران و قهرمان مرتبط نیز حذف شدند."
        )
        
        # برگشت به لیست لیگ‌ها بعد از 2 ثانیه
        await asyncio.sleep(2)
        await list_leagues_handler(callback, include_persistent_keyboard=True)
        
    except Exception as e:
        logger.error(f"خطا در حذف لیگ: {e}")
        await callback.message.edit_text(f"❌ خطا در حذف لیگ: {str(e)}")

# به‌روزرسانی تالار افتخارات
@dp.callback_query(F.data == "refresh_hall_of_fame")
async def refresh_hall_of_fame(callback: types.CallbackQuery):
    await callback.answer()
    await show_hall_of_fame(callback, include_persistent_keyboard=True)

# نمایش تالار افتخارات از اینلاین
@dp.callback_query(F.data == "hall_of_fame")
async def hall_of_fame_callback(callback: types.CallbackQuery):
    await callback.answer()
    await show_hall_of_fame(callback, include_persistent_keyboard=True)

# بازگشت به لیست لیگ‌ها
@dp.callback_query(F.data == "list_leagues_callback")
async def list_leagues_callback(callback: types.CallbackQuery):
    await callback.answer()
    await list_leagues_handler(callback, include_persistent_keyboard=True)

# اضافه کردن قهرمان جدید از تالار افتخارات
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

# دکمه "➕ ایجاد لیگ" از Reply Keyboard
@dp.message(F.text == "➕ ایجاد لیگ")
async def create_league_button(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in admin_sessions:
        await message.answer("❌ دسترسی ندارید. ابتدا /start را بزنید.")
        return
    
    await message.answer("📝 لطفاً نام لیگ جدید را وارد کنید:")
    await state.set_state(AdminStates.waiting_league_name)

# دکمه "📊 آمار کلی" از Reply Keyboard
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
    
    # تعداد قهرمانان
    cursor.execute("SELECT COUNT(*) FROM champions")
    total_champions = cursor.fetchone()[0]
    
    # ظرفیت کل
    cursor.execute("SELECT SUM(capacity) FROM leagues WHERE is_active = 1")
    total_capacity = cursor.fetchone()[0] or 0
    
    # ایجاد اینلاین کیبورد همیشگی
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
    builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
    builder.button(text="➕ ایجاد لیگ", callback_data="create_league_persistent")
    builder.adjust(2, 1)
    
    await message.answer(
        f"📊 آمار کلی سیستم:\n\n"
        f"🏆 تعداد کل لیگ‌ها: {total_leagues}\n"
        f"✅ لیگ‌های فعال: {active_leagues}\n"
        f"❌ لیگ‌های غیرفعال: {total_leagues - active_leagues}\n"
        f"👑 لیگ‌های دارای قهرمان: {total_champions}\n"
        f"👥 کاربران ثبت‌نام کرده: {total_users}\n"
        f"📈 ظرفیت کل فعال: {total_capacity}\n"
        f"📊 درصد پر شدن: {round((total_users / total_capacity * 100) if total_capacity > 0 else 0, 1)}%",
        reply_markup=builder.as_markup()
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
        
        # ایجاد اینلاین کیبورد همیشگی
        builder = InlineKeyboardBuilder()
        builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
        builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
        builder.button(text="➕ ایجاد لیگ", callback_data="create_league_persistent")
        builder.adjust(2, 1)
        
        await message.answer(
            f"✅ لیگ '{league_name}' با ظرفیت {capacity} ایجاد شد!",
            reply_markup=builder.as_markup()
        )
        
        # تالار افتخارات را هم نمایش بده
        await show_hall_of_fame(message, include_persistent_keyboard=True)
        
        # پاک کردن حالت
        await state.clear()
        
    except ValueError:
        await message.answer("⚠️ لطفاً یک عدد صحیح و مثبت وارد کنید:")

# تابع لغو
@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    
    # ایجاد اینلاین کیبورد همیشگی
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 لیست لیگ‌ها", callback_data="list_leagues_persistent")
    builder.button(text="🏆 تالار افتخارات", callback_data="hall_of_fame_persistent")
    builder.button(text="➕ ایجاد لیگ", callback_data="create_league_persistent")
    builder.adjust(2, 1)
    
    await message.answer("❌ عملیات لغو شد.", reply_markup=builder.as_markup())

# ---------- تابع اصلی اجرا ----------
async def main():
    print("🤖 ربات ادمین با aiogram در حال راه‌اندازی...")
    print("✅ اینلاین کیبورد همیشگی فعال شد")
    print("✅ تالار افتخارات با آیدی بازی (هر چیزی) اضافه شد")
    print("✅ فقط آیدی بازی گرفته می‌شود (بدون @username)")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())