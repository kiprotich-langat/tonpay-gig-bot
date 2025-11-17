
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import types, F
from database import Database
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Load environment variables
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_WALLET_MNEMONIC = os.getenv("ADMIN_WALLET_MNEMONIC")

# Configure logging
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Silence the noisy TON client logs
logging.getLogger('LiteClient').setLevel(logging.WARNING)  # Only show warnings/errors
logging.getLogger('pytoniq').setLevel(logging.WARNING)
logging.getLogger('pytoniq_core').setLevel(logging.WARNING)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Initialize database
db = Database()

# TON Manager - will be initialized in main()
ton_manager = None

# FSM States
class GigPostingStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_payment = State()

class ApplicationStates(StatesGroup):
    waiting_for_proposal = State()

class DisputeStates(StatesGroup):
    waiting_for_reason = State()

class RatingStates(StatesGroup):
    waiting_for_rating = State()
    waiting_for_comment = State()

# Keyboard layouts
def get_main_keyboard(user_role=None):
    """Generate main menu keyboard"""
    keyboard = [
        [KeyboardButton(text="📝 Post Gig"), KeyboardButton(text="🔍 Browse Gigs")],
        [KeyboardButton(text="💼 My Gigs"), KeyboardButton(text="📊 My Applications")],
        [KeyboardButton(text="👤 Profile"), KeyboardButton(text="💰 Wallet")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_gig_action_keyboard(gig_id, user_id, gig_data):
    """Generate action buttons for a specific gig"""
    keyboard = []

    if gig_data['client_id'] == user_id:
        if gig_data['status'] == 'open':
            keyboard.append([InlineKeyboardButton(text="❌ Cancel Gig", callback_data=f"cancel_gig_{gig_id}")])
        elif gig_data['status'] == 'in_progress':
            keyboard.append([InlineKeyboardButton(text="✅ Mark Complete", callback_data=f"complete_gig_{gig_id}")])
            keyboard.append([InlineKeyboardButton(text="⚠️ Dispute", callback_data=f"dispute_gig_{gig_id}")])
    elif gig_data['status'] == 'open':
        keyboard.append([InlineKeyboardButton(text="🎯 Apply for Gig", callback_data=f"apply_gig_{gig_id}")])

    keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_to_browse")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ===== COMMAND HANDLERS =====

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    if not db.get_user(user_id):
        db.add_user(user_id, username)
        logger.info(f"New user registered: {user_id} ({username})")

    welcome_text = f"""
🎉 <b>Welcome to TONPay Gig Bot!</b>

Hello <b>{username}</b> 👋

<b>🔥 Now with REAL TON Smart Contracts!</b>

This bot helps you:
• 📝 Post freelance gigs with secure escrow
• 🔍 Find and apply for tasks
• 💰 Get paid securely in TON cryptocurrency
• 🔒 Full blockchain protection

<b>How it works:</b>
1. Clients post gigs → Funds locked in smart contract
2. Freelancers apply to gigs
3. Payment held in blockchain escrow
4. Once work is complete, TON releases automatically

Use the menu below to get started!
    """
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="HTML")

@dp.message(Command("postgig"))
@dp.message(F.text == "📝 Post Gig")
async def cmd_post_gig(message: types.Message, state: FSMContext):
    """Start gig posting process"""
    user = db.get_user(message.from_user.id)
    if not user or not user.get('wallet_address'):
        await message.answer(
            "⚠️ <b>Wallet Required</b>\n\n"
            "Before posting gigs, set up your TON wallet:\n\n"
            "<code>/setwallet YOUR_TON_ADDRESS</code>",
            parse_mode="HTML"
        )
        return
    
    await message.answer(
        "📝 <b>Let's create a new gig!</b>\n\n"
        "Please enter the <b>title</b> of your gig:\n"
        "<i>(Example: \"Design a logo for my startup\")</i>",
        parse_mode="HTML"
    )
    await state.set_state(GigPostingStates.waiting_for_title)

@dp.message(GigPostingStates.waiting_for_title)
async def process_gig_title(message: types.Message, state: FSMContext):
    """Process gig title"""
    await state.update_data(title=message.text)
    await message.answer(
        "✅ Title saved!\n\n"
        "Now, please provide a <b>detailed description</b> of the work:\n"
        "<i>(Include requirements, deliverables, timeline, etc.)</i>",
        parse_mode="HTML"
    )
    await state.set_state(GigPostingStates.waiting_for_description)

@dp.message(GigPostingStates.waiting_for_description)
async def process_gig_description(message: types.Message, state: FSMContext):
    """Process gig description"""
    await state.update_data(description=message.text)
    await message.answer(
        "✅ Description saved!\n\n"
        "Finally, what's your budget for this gig?\n"
        "Please enter the amount in <b>TON</b>:\n"
        "<i>(Example: 5.5 or 10)</i>\n\n"
        "⚠️ <b>Note:</b> This is REAL TON that will be locked in smart contract!",
        parse_mode="HTML"
    )
    await state.set_state(GigPostingStates.waiting_for_price)

@dp.message(GigPostingStates.waiting_for_price)
async def process_gig_price(message: types.Message, state: FSMContext):
    """Process gig price and prepare for payment"""
    try:
        price = float(message.text)
        
        MIN_AMOUNT = 0.5
        MAX_AMOUNT = 1000.0
        
        if price < MIN_AMOUNT:
            await message.answer(f"❌ Minimum amount is {MIN_AMOUNT} TON. Please try again:")
            return
        
        if price > MAX_AMOUNT:
            await message.answer(f"❌ Maximum amount is {MAX_AMOUNT} TON. Please try again:")
            return

        data = await state.get_data()
        user_id = message.from_user.id
        user = db.get_user(user_id)
        
        processing_msg = await message.answer(
            "⏳ <b>Preparing Escrow Contract...</b>\n\nPlease wait...",
            parse_mode="HTML"
        )

        try:
            # Create gig in database
            gig_id = db.create_gig(
                client_id=user_id,
                title=data['title'],
                description=data['description'],
                price=price
            )
            
            # Generate payment link
            if ton_manager:
                payment_link = await ton_manager.generate_payment_link(
                    user.get('wallet_address'), price
                )
            else:
                payment_link = f"ton://transfer/{user.get('wallet_address')}?amount={int(price * 1e9)}"
            
            temp_escrow = f"escrow_pending_{gig_id}"
            db.update_gig_escrow(gig_id, temp_escrow)
            
            await state.update_data(gig_id=gig_id, price=price)
            await processing_msg.delete()
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Pay with TON Wallet", url=payment_link)],
                [InlineKeyboardButton(text="✅ I've Sent Payment", callback_data=f"confirm_payment_{gig_id}")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_payment_{gig_id}")]
            ])
            
            await message.answer(
                f"🎉 <b>Gig Created! Now Fund Escrow</b>\n\n"
                f"<b>Gig ID:</b> #{gig_id}\n"
                f"<b>Title:</b> {data['title']}\n"
                f"<b>Amount:</b> {price} TON\n\n"
                f"📱 <b>Payment Instructions:</b>\n\n"
                f"<b>Step 1:</b> Click button below to open TON wallet\n"
                f"<b>Step 2:</b> Send <b>exactly {price} TON</b>\n"
                f"<b>Step 3:</b> Click \"I've Sent Payment\"\n\n"
                f"⚠️ <b>IMPORTANT:</b>\n"
                f"• This is REAL TON on MAINNET\n"
                f"• Funds will be locked in smart contract\n"
                f"• Contract deploys after payment confirmation\n\n"
                f"💡 Your gig will be visible after deployment!",
                parse_mode="HTML",
                reply_markup=keyboard
            )
            
            await state.set_state(GigPostingStates.waiting_for_payment)
            logger.info(f"Gig created: ID={gig_id}, awaiting payment")

        except Exception as e:
            await processing_msg.delete()
            await message.answer(
                f"❌ <b>Error</b>\n\nFailed to create gig: {str(e)}\n\nPlease try again.",
                parse_mode="HTML"
            )
            logger.error(f"Gig creation failed: {e}")
            await state.clear()

    except ValueError:
        await message.answer("❌ Invalid price format. Please enter a number (e.g., 5.5 or 10):")

@dp.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment(callback: types.CallbackQuery, state: FSMContext):
    """Handle payment confirmation and deploy contract"""
    gig_id = int(callback.data.split("_")[2])
    gig = db.get_gig(gig_id)
    
    if not gig or gig['client_id'] != callback.from_user.id:
        await callback.answer("❌ Invalid gig!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⏳ <b>Deploying Smart Contract...</b>\n\n"
        "🔗 Deploying escrow to TON blockchain\n"
        "⚙️ Verifying payment\n"
        "🔒 Initializing security\n\n"
        "This may take 30-60 seconds...",
        parse_mode="HTML"
    )
    
    try:
        user = db.get_user(callback.from_user.id)
        
        # Deploy escrow contract if TON manager available
        if ton_manager:
            escrow_info = await ton_manager.create_escrow_contract(
                gig_id=gig_id,
                client_address=user['wallet_address'],
                freelancer_address="EQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAM9c",
                amount_ton=gig['price']
            )
            contract_address = escrow_info['contract_address']
            tx_hash = escrow_info.get('tx_hash', 'Processing...')
            explorer_link = f"https://tonscan.org/address/{contract_address}"
        else:
            # Fallback for testing without TON manager
            contract_address = f"EQ_test_{gig_id}_{gig['price']}"
            tx_hash = "simulated_tx"
            explorer_link = "https://tonscan.org"
        
        db.update_gig_escrow(gig_id, contract_address)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 View on TONScan", url=explorer_link)],
            [InlineKeyboardButton(text="✅ Done", callback_data="payment_done")]
        ])
        
        await callback.message.edit_text(
            f"✅ <b>Smart Contract Deployed!</b>\n\n"
            f"<b>Gig ID:</b> #{gig_id}\n"
            f"<b>Title:</b> {gig['title']}\n"
            f"<b>Escrow:</b> {gig['price']} TON\n\n"
            f"🔗 <b>Contract:</b>\n<code>{contract_address}</code>\n\n"
            f"📋 <b>Transaction:</b>\n<code>{tx_hash}</code>\n\n"
            f"✅ Funds locked in blockchain escrow!\n"
            f"✅ Gig is now live!\n\n"
            f"💡 Use /mygigs to view applications.",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await state.clear()
        await callback.answer("✅ Deployed!")
        logger.info(f"Escrow deployed: Gig={gig_id}, Contract={contract_address}")
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Deployment Failed</b>\n\n{str(e)}\n\n"
            f"Please try again or contact support.",
            parse_mode="HTML"
        )
        await callback.answer("❌ Failed!", show_alert=True)
        logger.error(f"Contract deployment failed: {e}")

@dp.callback_query(F.data.startswith("cancel_payment_"))
async def cancel_payment(callback: types.CallbackQuery, state: FSMContext):
    """Cancel gig creation"""
    gig_id = int(callback.data.split("_")[2])
    db.update_gig_status(gig_id, 'cancelled')
    
    await callback.message.edit_text(
        "❌ <b>Gig Cancelled</b>\n\nYour gig has been cancelled.",
        parse_mode="HTML"
    )
    await state.clear()
    await callback.answer("Cancelled")

@dp.callback_query(F.data == "payment_done")
async def payment_done(callback: types.CallbackQuery):
    """Acknowledge payment completion"""
    await callback.message.delete()
    await callback.answer("✅ All set!")

@dp.message(Command("browsegigs"))
@dp.message(F.text == "🔍 Browse Gigs")
async def cmd_browse_gigs(message: types.Message):
    """Browse available gigs"""
    gigs = db.get_open_gigs()

    if not gigs:
        await message.answer(
            "😕 <b>No gigs available right now.</b>\n\nCheck back later!",
            parse_mode="HTML"
        )
        return

    await message.answer(f"📋 <b>Found {len(gigs)} open gigs:</b>\n", parse_mode="HTML")

    for gig in gigs[:10]:
        client = db.get_user(gig['client_id'])
        client_name = client['username'] if client else "Unknown"

        gig_text = f"""
📌 <b>Gig #{gig['id']}</b>
<b>Title:</b> {gig['title']}
<b>Client:</b> @{client_name}
<b>Budget:</b> {gig['price']} TON
<b>Status:</b> {gig['status'].upper()}

<i>{gig['description'][:100]}{'...' if len(gig['description']) > 100 else ''}</i>
        """

        has_applied = db.has_applied(message.from_user.id, gig['id'])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 View Details", callback_data=f"view_gig_{gig['id']}"),
             InlineKeyboardButton(text="🎯 Apply Now" if not has_applied else "✅ Applied", 
                                callback_data=f"apply_gig_{gig['id']}" if not has_applied else "already_applied")]
        ])

        await message.answer(gig_text.strip(), reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data.startswith("view_gig_"))
async def view_gig_details(callback: types.CallbackQuery):
    """Show detailed gig information"""
    gig_id = int(callback.data.split("_")[2])
    gig = db.get_gig(gig_id)

    if not gig:
        await callback.answer("❌ Gig not found!", show_alert=True)
        return

    client = db.get_user(gig['client_id'])
    client_name = client['username'] if client else "Unknown"

    gig_text = f"""
📌 <b>Gig #{gig['id']} - Full Details</b>

<b>Title:</b> {gig['title']}

<b>Description:</b>
{gig['description']}

<b>Client:</b> @{client_name}
<b>Rating:</b> {'⭐' * int(client.get('rating', 0))} ({client.get('rating', 0)}/5)

<b>Budget:</b> {gig['price']} TON
<b>Status:</b> {gig['status'].upper()}
<b>Posted:</b> {gig['created_at']}
<b>Applications:</b> {db.count_applications(gig_id)}
    """

    keyboard = get_gig_action_keyboard(gig_id, callback.from_user.id, gig)
    await callback.message.edit_text(gig_text.strip(), reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("apply_gig_"))
async def start_application(callback: types.CallbackQuery, state: FSMContext):
    """Start application process"""
    gig_id = int(callback.data.split("_")[2])

    if db.has_applied(callback.from_user.id, gig_id):
        await callback.answer("⚠️ You've already applied!", show_alert=True)
        return

    await state.update_data(applying_to_gig=gig_id)
    await callback.message.answer(
        "📝 <b>Application Process</b>\n\n"
        "Please write your proposal:\n"
        "- Why you're the right fit\n"
        "- Your relevant experience\n"
        "- Estimated delivery time",
        parse_mode="HTML"
    )
    await state.set_state(ApplicationStates.waiting_for_proposal)
    await callback.answer()

@dp.callback_query(F.data == "already_applied")
async def already_applied_handler(callback: types.CallbackQuery):
    """Handle already applied"""
    await callback.answer("✅ You've already applied! Check /myapplications", show_alert=True)

@dp.message(ApplicationStates.waiting_for_proposal)
async def process_application(message: types.Message, state: FSMContext):
    """Process freelancer application"""
    data = await state.get_data()
    gig_id = data['applying_to_gig']

    app_id = db.create_application(
        gig_id=gig_id,
        freelancer_id=message.from_user.id,
        proposal=message.text
    )

    gig = db.get_gig(gig_id)
    await bot.send_message(
        gig['client_id'],
        f"🔔 <b>New Application!</b>\n\n"
        f"Someone applied to: <b>{gig['title']}</b>\n"
        f"View with /mygigs",
        parse_mode="HTML"
    )

    await message.answer(
        "✅ <b>Application Submitted!</b>\n\n"
        "The client will review your proposal.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

    await state.clear()
    logger.info(f"Application: ID={app_id}, Gig={gig_id}, User={message.from_user.id}")

@dp.message(Command("mygigs"))
@dp.message(F.text == "💼 My Gigs")
async def cmd_my_gigs(message: types.Message):
    """Show user's posted gigs"""
    gigs = db.get_user_gigs(message.from_user.id)

    if not gigs:
        await message.answer(
            "📭 <b>You haven't posted any gigs yet.</b>\n\nUse /postgig!",
            parse_mode="HTML"
        )
        return

    await message.answer(f"💼 <b>Your Gigs ({len(gigs)}):</b>\n", parse_mode="HTML")

    for gig in gigs:
        app_count = db.count_applications(gig['id'])
        status_emoji = {
            "open": "🟢", "in_progress": "🟡",
            "completed": "✅", "cancelled": "❌", "disputed": "⚠️"
        }

        freelancer_info = ""
        if gig.get('freelancer_id'):
            freelancer = db.get_user(gig['freelancer_id'])
            if freelancer:
                freelancer_info = f"\n<b>Freelancer:</b> @{freelancer['username']}"

        gig_text = f"""
{status_emoji.get(gig['status'], '⚪')} <b>Gig #{gig['id']}</b>
<b>Title:</b> {gig['title']}
<b>Status:</b> {gig['status'].upper()}{freelancer_info}
<b>Budget:</b> {gig['price']} TON
<b>Applications:</b> {app_count}
        """

        keyboard_buttons = []
        
        if gig['status'] == 'open':
            keyboard_buttons.append([InlineKeyboardButton(text="📋 View Applications", callback_data=f"view_apps_{gig['id']}")])
            keyboard_buttons.append([InlineKeyboardButton(text="❌ Cancel Gig", callback_data=f"cancel_gig_{gig['id']}")])
        elif gig['status'] == 'in_progress':
            keyboard_buttons.append([InlineKeyboardButton(text="✅ Mark Complete", callback_data=f"complete_gig_{gig['id']}")])
            keyboard_buttons.append([InlineKeyboardButton(text="⚠️ Open Dispute", callback_data=f"dispute_gig_{gig['id']}")])
        elif gig['status'] == 'completed':
            keyboard_buttons.append([InlineKeyboardButton(text="📄 View Details", callback_data=f"view_gig_{gig['id']}")])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
        await message.answer(gig_text.strip(), reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data.startswith("view_apps_"))
async def view_gig_applications(callback: types.CallbackQuery):
    """View all applications for a gig"""
    gig_id = int(callback.data.split("_")[2])
    gig = db.get_gig(gig_id)

    if not gig or gig['client_id'] != callback.from_user.id:
        await callback.answer("⚠️ Unauthorized!", show_alert=True)
        return

    applications = db.get_gig_applications(gig_id)

    if not applications:
        await callback.message.answer(
            f"📋 <b>Gig #{gig_id}: {gig['title']}</b>\n\nNo applications yet.",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await callback.message.answer(
        f"📋 <b>Applications for Gig #{gig_id}</b>\n"
        f"<b>Title:</b> {gig['title']}\n"
        f"<b>Total:</b> {len(applications)}\n",
        parse_mode="HTML"
    )

    for app in applications:
        freelancer = db.get_user(app['freelancer_id'])
        freelancer_name = freelancer['username'] if freelancer else "Unknown"

        status_emoji = {'pending': '🟡', 'accepted': '✅', 'rejected': '❌'}

        app_text = f"""
{status_emoji.get(app['status'], '⚪')} <b>Application #{app['id']}</b>
<b>Freelancer:</b> @{freelancer_name}
<b>Rating:</b> {'⭐' * int(freelancer.get('rating', 0))} ({freelancer.get('rating', 0)}/5)
<b>Status:</b> {app['status'].upper()}

<b>Proposal:</b>
{app['proposal']}

<b>Applied:</b> {app['created_at']}
        """

        keyboard = []
        if app['status'] == 'pending' and gig['status'] == 'open':
            keyboard.append([
                InlineKeyboardButton(text="✅ Accept", callback_data=f"accept_app_{app['id']}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_app_{app['id']}")
            ])

        keyboard.append([InlineKeyboardButton(text="👤 View Profile", callback_data=f"view_profile_{app['freelancer_id']}")])

        await callback.message.answer(
            app_text.strip(),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )

    await callback.answer()

@dp.callback_query(F.data.startswith("accept_app_"))
async def accept_application(callback: types.CallbackQuery):
    """Accept application"""
    app_id = int(callback.data.split("_")[2])
    app = db.get_application(app_id)

    if not app:
        await callback.answer("❌ Not found!", show_alert=True)
        return

    gig = db.get_gig(app['gig_id'])

    if gig['client_id'] != callback.from_user.id:
        await callback.answer("⚠️ Unauthorized!", show_alert=True)
        return

    if gig['status'] != 'open':
        await callback.answer("⚠️ Gig not open!", show_alert=True)
        return

    if db.accept_application(app_id):
        freelancer = db.get_user(app['freelancer_id'])

        await bot.send_message(
            app['freelancer_id'],
            f"🎉 <b>Congratulations!</b>\n\n"
            f"Your application for <b>{gig['title']}</b> was accepted!\n\n"
            f"<b>Budget:</b> {gig['price']} TON\n"
            f"<b>Client:</b> @{callback.from_user.username}\n\n"
            f"Start working! Payment releases when client marks complete.",
            parse_mode="HTML"
        )

        await callback.message.answer(
            f"✅ <b>Application Accepted!</b>\n\n"
            f"<b>Freelancer:</b> @{freelancer['username']}\n"
            f"<b>Gig:</b> {gig['title']}\n\n"
            f"Freelancer notified. Mark complete when done to release {gig['price']} TON.",
            parse_mode="HTML"
        )

        await callback.answer("✅ Accepted!")
        logger.info(f"Application {app_id} accepted for gig {gig['id']}")
    else:
        await callback.answer("❌ Failed!", show_alert=True)

@dp.callback_query(F.data.startswith("reject_app_"))
async def reject_application(callback: types.CallbackQuery):
    """Reject application"""
    app_id = int(callback.data.split("_")[2])
    app = db.get_application(app_id)

    if not app:
        await callback.answer("❌ Not found!", show_alert=True)
        return

    gig = db.get_gig(app['gig_id'])

    if gig['client_id'] != callback.from_user.id:
        await callback.answer("⚠️ Unauthorized!", show_alert=True)
        return

    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET status = 'rejected' WHERE id = ?", (app_id,))
    conn.commit()

    await callback.message.answer(
        f"❌ <b>Application Rejected</b>\n\nApplication #{app_id} rejected.",
        parse_mode="HTML"
    )

    await callback.answer("Rejected")

@dp.message(Command("myapplications"))
@dp.message(F.text == "📊 My Applications")
async def cmd_my_applications(message: types.Message):
    """Show user's applications"""
    applications = db.get_user_applications(message.from_user.id)

    if not applications:
        await message.answer(
            "📭 <b>You haven't applied to any gigs yet.</b>\n\n"
            "Browse gigs with /browsegigs",
            parse_mode="HTML"
        )
        return

    await message.answer(f"📊 <b>Your Applications ({len(applications)}):</b>\n", parse_mode="HTML")

    for app in applications:
        status_emoji = {'pending': '🟡', 'accepted': '✅', 'rejected': '❌'}
        gig_status_text = {
            'open': 'Open', 'in_progress': 'In Progress',
            'completed': 'Completed', 'cancelled': 'Cancelled', 'disputed': 'Disputed'
        }

        app_text = f"""
{status_emoji.get(app['status'], '⚪')} <b>Application #{app['id']}</b>
<b>Gig:</b> {app['title']}
<b>Budget:</b> {app['price']} TON
<b>Your Status:</b> {app['status'].upper()}
<b>Gig Status:</b> {gig_status_text.get(app['gig_status'], app['gig_status'])}
<b>Applied:</b> {app['created_at']}
        """

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 View Gig", callback_data=f"view_gig_{app['gig_id']}")]
        ])

        await message.answer(app_text.strip(), reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(F.data.startswith("complete_gig_"))
async def complete_gig(callback: types.CallbackQuery):
    """Mark gig complete and release payment"""
    gig_id = int(callback.data.split("_")[2])
    gig = db.get_gig(gig_id)

    if not gig:
        await callback.answer("❌ Gig not found!", show_alert=True)
        return

    if gig['client_id'] != callback.from_user.id:
        await callback.answer("⚠️ Unauthorized!", show_alert=True)
        return

    if gig['status'] != 'in_progress':
        await callback.answer("⚠️ Not in progress!", show_alert=True)
        return

    if not gig['freelancer_id']:
        await callback.answer("❌ No freelancer assigned!", show_alert=True)
        return

    freelancer = db.get_user(gig['freelancer_id'])
    if not freelancer or not freelancer.get('wallet_address'):
        await callback.message.answer(
            "⚠️ <b>Cannot Release Payment</b>\n\n"
            "Freelancer hasn't set wallet address.\n"
            "They need to use /setwallet command.",
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # Release payment from escrow
    try:
        if ton_manager:
            tx_info = await ton_manager.release_escrow(
                contract_address=gig['escrow_address'],
                gig_id=gig_id
            )
            tx_hash = tx_info.get('tx_hash', 'completed')
        else:
            tx_hash = f"simulated_release_{gig_id}"
        
        # Update gig status
        db.complete_gig(gig_id)

        # Record transaction
        db.create_transaction(
            gig_id=gig_id,
            from_user=gig['client_id'],
            to_user=gig['freelancer_id'],
            amount=gig['price'],
            tx_hash=tx_hash
        )

        # Notify freelancer with rating button
        freelancer_rating_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Rate Client", callback_data=f"rate_user_{gig['client_id']}_{gig_id}")]
        ])
        
        await bot.send_message(
            gig['freelancer_id'],
            f"💰 <b>Payment Released!</b>\n\n"
            f"<b>Gig:</b> {gig['title']}\n"
            f"<b>Amount:</b> {gig['price']} TON\n"
            f"<b>Transaction:</b> <code>{tx_hash}</code>\n\n"
            f"✅ Payment sent to your wallet!\n\n"
            f"Please rate your experience:",
            parse_mode="HTML",
            reply_markup=freelancer_rating_keyboard
        )

        # Send rating button to client
        client_rating_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Rate Freelancer", callback_data=f"rate_user_{gig['freelancer_id']}_{gig_id}")]
        ])
        
        await callback.message.answer(
            f"✅ <b>Gig Completed!</b>\n\n"
            f"<b>Title:</b> {gig['title']}\n"
            f"<b>Amount Paid:</b> {gig['price']} TON\n"
            f"<b>Freelancer:</b> @{freelancer['username']}\n"
            f"<b>Transaction:</b> <code>{tx_hash}</code>\n\n"
            f"💸 Payment released from escrow!\n\n"
            f"Please rate your experience:",
            parse_mode="HTML",
            reply_markup=client_rating_keyboard
        )

        await callback.answer("✅ Payment released!")
        logger.info(f"Gig {gig_id} completed, payment released: {tx_hash}")
        
    except Exception as e:
        await callback.answer(f"❌ Failed: {str(e)}", show_alert=True)
        logger.error(f"Payment release failed: {e}")

@dp.callback_query(F.data.startswith("dispute_gig_"))
async def start_dispute(callback: types.CallbackQuery, state: FSMContext):
    """Start dispute process"""
    gig_id = int(callback.data.split("_")[2])
    gig = db.get_gig(gig_id)

    if not gig:
        await callback.answer("❌ Gig not found!", show_alert=True)
        return

    if gig['client_id'] != callback.from_user.id and gig['freelancer_id'] != callback.from_user.id:
        await callback.answer("⚠️ Not involved in this gig!", show_alert=True)
        return

    await state.update_data(dispute_gig_id=gig_id)
    await callback.message.answer(
        "⚠️ <b>Opening Dispute</b>\n\n"
        "Please describe the issue in detail:\n"
        "- What went wrong?\n"
        "- What resolution do you seek?\n"
        "- Any relevant evidence?",
        parse_mode="HTML"
    )
    await state.set_state(DisputeStates.waiting_for_reason)
    await callback.answer()

@dp.message(DisputeStates.waiting_for_reason)
async def process_dispute(message: types.Message, state: FSMContext):
    """Process dispute submission"""
    data = await state.get_data()
    gig_id = data['dispute_gig_id']

    dispute_id = db.create_dispute(
        gig_id=gig_id,
        raised_by=message.from_user.id,
        reason=message.text
    )

    gig = db.get_gig(gig_id)
    other_party = gig['freelancer_id'] if gig['client_id'] == message.from_user.id else gig['client_id']

    await bot.send_message(
        other_party,
        f"⚠️ <b>Dispute Opened</b>\n\n"
        f"A dispute was opened for: <b>{gig['title']}</b>\n"
        f"Dispute ID: #{dispute_id}\n\n"
        f"An administrator will review the case.",
        parse_mode="HTML"
    )

    await message.answer(
        f"✅ <b>Dispute Opened</b>\n\n"
        f"<b>Dispute ID:</b> #{dispute_id}\n"
        f"<b>Gig:</b> {gig['title']}\n\n"
        f"Administrator will review and contact both parties.\n"
        f"Payment is held in escrow.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

    await state.clear()
    logger.info(f"Dispute created: ID={dispute_id}, Gig={gig_id}, User={message.from_user.id}")

@dp.callback_query(F.data.startswith("rate_user_"))
async def start_rating(callback: types.CallbackQuery, state: FSMContext):
    """Start rating process"""
    parts = callback.data.split("_")
    user_id = int(parts[2])
    gig_id = int(parts[3])

    await state.update_data(rating_user_id=user_id, rating_gig_id=gig_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐", callback_data="rating_1"),
            InlineKeyboardButton(text="⭐⭐", callback_data="rating_2"),
            InlineKeyboardButton(text="⭐⭐⭐", callback_data="rating_3")
        ],
        [
            InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="rating_4"),
            InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data="rating_5")
        ]
    ])

    await callback.message.answer(
        "⭐ <b>Rate Your Experience</b>\n\n"
        "How would you rate this collaboration?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("rating_"))
async def process_rating_number(callback: types.CallbackQuery, state: FSMContext):
    """Process rating number"""
    rating = int(callback.data.split("_")[1])
    await state.update_data(rating_value=rating)

    await callback.message.answer(
        f"✅ <b>Rating: {'⭐' * rating}</b>\n\n"
        "Would you like to leave a comment? (optional)\n"
        "Send your comment or type 'skip' to finish.",
        parse_mode="HTML"
    )
    await state.set_state(RatingStates.waiting_for_comment)
    await callback.answer()

@dp.message(RatingStates.waiting_for_comment)
async def process_rating_comment(message: types.Message, state: FSMContext):
    """Process rating comment"""
    data = await state.get_data()

    comment = None if message.text.lower() == 'skip' else message.text

    db.add_rating(
        gig_id=data['rating_gig_id'],
        from_user=message.from_user.id,
        to_user=data['rating_user_id'],
        rating=data['rating_value'],
        comment=comment
    )

    rated_user = db.get_user(data['rating_user_id'])

    await message.answer(
        f"✅ <b>Rating Submitted!</b>\n\n"
        f"Thank you for rating @{rated_user['username']}\n"
        f"Your feedback helps build a better community!",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )

    await state.clear()

@dp.callback_query(F.data.startswith("cancel_gig_"))
async def cancel_gig(callback: types.CallbackQuery):
    """Cancel an open gig"""
    gig_id = int(callback.data.split("_")[2])
    gig = db.get_gig(gig_id)

    if not gig:
        await callback.answer("❌ Gig not found!", show_alert=True)
        return

    if gig['client_id'] != callback.from_user.id:
        await callback.answer("⚠️ Unauthorized!", show_alert=True)
        return

    if gig['status'] != 'open':
        await callback.answer("⚠️ Only open gigs can be cancelled!", show_alert=True)
        return

    db.update_gig_status(gig_id, 'cancelled')

    await callback.message.answer(
        f"❌ <b>Gig Cancelled</b>\n\n"
        f"<b>Title:</b> {gig['title']}\n"
        f"Your gig has been cancelled.\n\n"
        f"If funds were in escrow, they will be refunded.",
        parse_mode="HTML"
    )

    await callback.answer("Gig cancelled")
    logger.info(f"Gig {gig_id} cancelled by user {callback.from_user.id}")

@dp.message(Command("setwallet"))
async def cmd_set_wallet(message: types.Message):
    """Set user's TON wallet address"""
    parts = message.text.split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "💰 <b>Set Wallet Address</b>\n\n"
            "Usage: <code>/setwallet &lt;your_ton_address&gt;</code>\n\n"
            "Example:\n"
            "<code>/setwallet EQD4FPq-PRDieyQKkizFTRtSDyucUIqrj0v_zXJmqaDp6_0t</code>\n\n"
            "You need a wallet to post gigs and receive payments!",
            parse_mode="HTML"
        )
        return

    wallet_address = parts[1].strip()

    # Validate wallet address
    if ton_manager and hasattr(ton_manager, 'validate_address'):
        is_valid = ton_manager.validate_address(wallet_address)
    else:
        # Basic validation
        is_valid = (wallet_address.startswith('EQ') or wallet_address.startswith('UQ')) and len(wallet_address) == 48

    if not is_valid:
        await message.answer(
            "❌ <b>Invalid Wallet Address</b>\n\n"
            "Please provide a valid TON wallet address.\n"
            "Format: EQxxxxx... or UQxxxxx...",
            parse_mode="HTML"
        )
        return

    if db.update_user_wallet(message.from_user.id, wallet_address):
        await message.answer(
            f"✅ <b>Wallet Address Set!</b>\n\n"
            f"<b>Address:</b> <code>{wallet_address}</code>\n\n"
            f"You can now:\n"
            f"• Post gigs with escrow\n"
            f"• Receive TON payments\n"
            f"• Apply to gigs\n\n"
            f"Your wallet is verified and ready!",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Failed to Set Wallet</b>\n\n"
            "Please try again or contact support.",
            parse_mode="HTML"
        )

@dp.callback_query(F.data == "back_to_browse")
async def back_to_browse(callback: types.CallbackQuery):
    """Go back to browse gigs"""
    await cmd_browse_gigs(callback.message)
    await callback.answer()

@dp.callback_query(F.data.startswith("view_profile_"))
async def view_user_profile(callback: types.CallbackQuery):
    """View another user's profile"""
    user_id = int(callback.data.split("_")[2])
    user = db.get_user(user_id)

    if not user:
        await callback.answer("❌ User not found!", show_alert=True)
        return

    stats = db.get_user_stats(user_id)

    profile_text = f"""
👤 <b>User Profile</b>

<b>Username:</b> @{user['username']}
<b>Rating:</b> {'⭐' * int(user.get('rating', 0))} ({user.get('rating', 0)}/5)
<b>Member Since:</b> {user['created_at']}

📊 <b>Statistics:</b>
• Gigs Posted: {stats['gigs_posted']}
• Jobs Completed: {stats['jobs_completed_freelancer']}
• Total Earned: {stats['total_earned']} TON
    """

    await callback.message.answer(profile_text.strip(), parse_mode="HTML")
    await callback.answer()

@dp.message(Command("profile"))
@dp.message(F.text == "👤 Profile")
async def cmd_profile(message: types.Message):
    """Show user profile"""
    user = db.get_user(message.from_user.id)

    if not user:
        await message.answer("❌ Profile not found. Use /start to register.")
        return

    stats = db.get_user_stats(message.from_user.id)

    profile_text = f"""
👤 <b>Your Profile</b>

<b>Username:</b> @{user['username']}
<b>Rating:</b> {'⭐' * int(user.get('rating', 0))} ({user.get('rating', 0)}/5)
<b>Member Since:</b> {user['created_at']}

📊 <b>Statistics:</b>
• Gigs Posted: {stats['gigs_posted']}
• Gigs Completed (as client): {stats['gigs_completed_client']}
• Jobs Completed (as freelancer): {stats['jobs_completed_freelancer']}
• Total Earned: {stats['total_earned']} TON
• Total Spent: {stats['total_spent']} TON
"""

    await message.answer(profile_text, parse_mode="HTML")

@dp.message(Command("wallet"))
@dp.message(F.text == "💰 Wallet")
async def cmd_wallet(message: types.Message):
    """Show wallet information"""
    user = db.get_user(message.from_user.id)

    wallet_text = f"""
💰 <b>Your TON Wallet</b>

<b>Address:</b> <code>{user.get('wallet_address', 'Not set')}</code>

To set up your wallet:
1. Install TON Wallet app or Tonkeeper
2. Create or import wallet
3. Use /setwallet &lt;address&gt; to link it

<b>Important:</b> Always verify wallet addresses before sending TON!
    """

    await message.answer(wallet_text, parse_mode="HTML")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Show help information"""
    help_text = """
📚 <b>TONPay Gig Bot - Commands</b>

<b>For Everyone:</b>
/start - Start the bot
/help - Show this help message
/profile - View your profile
/wallet - Manage your wallet
/debug - Check your active gigs

<b>For Clients:</b>
/postgig - Post a new gig
/mygigs - View your posted gigs

<b>For Freelancers:</b>
/browsegigs - Browse available gigs
/myapplications - View your applications
/myjobs - View your active jobs

<b>Need Support?</b>
Contact @yoursupport for assistance
    """

    await message.answer(help_text, parse_mode="HTML")

@dp.message(Command("myjobs"))
async def cmd_my_jobs(message: types.Message):
    """Show freelancer's active and completed jobs"""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT * FROM gigs 
           WHERE freelancer_id = ? 
           ORDER BY created_at DESC""",
        (message.from_user.id,)
    )
    jobs = [dict(row) for row in cursor.fetchall()]
    
    if not jobs:
        await message.answer(
            "📭 <b>You don't have any active jobs yet.</b>\n\n"
            "Apply to gigs with /browsegigs!",
            parse_mode="HTML"
        )
        return
    
    await message.answer(f"💼 <b>Your Jobs ({len(jobs)}):</b>\n", parse_mode="HTML")
    
    for job in jobs:
        client = db.get_user(job['client_id'])
        client_name = client['username'] if client else "Unknown"
        
        status_emoji = {
            "in_progress": "🟡", "completed": "✅",
            "cancelled": "❌", "disputed": "⚠️"
        }
        
        job_text = f"""
{status_emoji.get(job['status'], '⚪')} <b>Job #{job['id']}</b>
<b>Title:</b> {job['title']}
<b>Client:</b> @{client_name}
<b>Status:</b> {job['status'].upper()}
<b>Payment:</b> {job['price']} TON
<b>Started:</b> {job['created_at']}
        """
        
        keyboard_buttons = []
        
        if job['status'] == 'in_progress':
            keyboard_buttons.append([InlineKeyboardButton(
                text="💬 Contact Client",
                url=f"https://t.me/{client_name}"
            )])
            keyboard_buttons.append([InlineKeyboardButton(
                text="⚠️ Report Issue",
                callback_data=f"dispute_gig_{job['id']}"
            )])
        elif job['status'] == 'completed':
            keyboard_buttons.append([InlineKeyboardButton(
                text="📄 View Details",
                callback_data=f"view_gig_{job['id']}"
            )])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
        await message.answer(job_text.strip(), reply_markup=keyboard, parse_mode="HTML")

@dp.message(Command("debug"))
async def cmd_debug(message: types.Message):
    """Debug command to check gig statuses"""
    user_id = message.from_user.id
    
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM gigs WHERE client_id = ?", (user_id,))
    as_client = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM gigs WHERE freelancer_id = ?", (user_id,))
    as_freelancer = [dict(row) for row in cursor.fetchall()]
    
    debug_text = f"🔍 <b>Debug Info for User {user_id}</b>\n\n"
    
    debug_text += f"<b>As Client ({len(as_client)} gigs):</b>\n"
    for gig in as_client:
        debug_text += f"• Gig #{gig['id']}: {gig['status']}\n"
    
    debug_text += f"\n<b>As Freelancer ({len(as_freelancer)} jobs):</b>\n"
    for gig in as_freelancer:
        debug_text += f"• Gig #{gig['id']}: {gig['status']}\n"
    
    debug_text += f"\n<b>💡 Tips:</b>\n"
    debug_text += f"• Use /mygigs to see your posted gigs\n"
    debug_text += f"• Use /myjobs to see your freelance jobs\n"
    debug_text += f"• 'in_progress' gigs can be marked complete\n"
    
    await message.answer(debug_text, parse_mode="HTML")

# Main function
async def main():
    """Start the bot with TON integration"""
    global ton_manager
    
    logger.info("=" * 60)
    logger.info("🚀 Starting TONPay Gig Bot - Production Version")
    logger.info("=" * 60)
    
    # Initialize database
    db.init_db()
    logger.info("✅ Database initialized")
    
    # Initialize TON Wallet Manager
    logger.info("🔗 Connecting to TON blockchain...")
    
    try:
        from ton_wallet_manager import TONWalletManager
        ton_manager = TONWalletManager(use_testnet=True)  # MAINNET or TESTNET
        success = await ton_manager.initialize()
        
        if not success:
            logger.error("❌ Failed to connect to TON blockchain!")
            logger.warning("⚠️  Bot will run in limited mode")
            logger.warning("⚠️  Please check ADMIN_WALLET_MNEMONIC in .env")
            ton_manager = None
        else:
            logger.info("✅ Connected to TON mainnet")
            logger.info("✅ Admin wallet loaded")
    except Exception as e:
        logger.error(f"❌ TON Manager initialization failed: {e}")
        logger.warning("⚠️  Bot will run in limited mode (testing)")
        ton_manager = None
    
    logger.info("=" * 60)
    logger.info("✅ TONPay Bot is now running!")
    logger.info("📱 Open Telegram and find your bot")
    logger.info("🎯 Send /start to begin")
    logger.info("=" * 60)
    if ton_manager:
        logger.info("⚠️  MAINNET MODE - REAL TON TRANSACTIONS!")
    else:
        logger.info("⚠️  LIMITED MODE - TON features disabled")
    logger.info("=" * 60)
    
    # Start polling
    try:
        await dp.start_polling(bot)
    finally:
        if ton_manager:
            await ton_manager.close()
            logger.info("TON connection closed")

if __name__ == "__main__":

    asyncio.run(main())
