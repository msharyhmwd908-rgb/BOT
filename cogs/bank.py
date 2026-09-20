import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from datetime import datetime


# =========================================================
# الإعدادات
# =========================================================

DB_FILE = "bank.db"

OWNER_USER_ID = 1495450684731162664

PANEL_IMAGE = "https://b.top4top.io/p_3915466zl0.jp"

SALARY_AMOUNT = 1000
SALARY_COOLDOWN = 24 * 60 * 60


# =========================================================
# قاعدة البيانات
# =========================================================

db = sqlite3.connect(DB_FILE)
db.row_factory = sqlite3.Row

cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS accounts (
    user_id INTEGER PRIMARY KEY,
    cash INTEGER NOT NULL DEFAULT 0,
    bank INTEGER NOT NULL DEFAULT 0,
    last_salary INTEGER NOT NULL DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    amount INTEGER NOT NULL,
    created_at TEXT NOT NULL
)
""")

db.commit()


# =========================================================
# وظائف قاعدة البيانات
# =========================================================

def get_account(user_id: int):

    cursor.execute(
        "SELECT * FROM accounts WHERE user_id = ?",
        (user_id,)
    )

    account = cursor.fetchone()

    if account is None:

        cursor.execute(
            """
            INSERT INTO accounts
            (user_id, cash, bank, last_salary)
            VALUES (?, 0, 0, 0)
            """,
            (user_id,)
        )

        db.commit()

        cursor.execute(
            "SELECT * FROM accounts WHERE user_id = ?",
            (user_id,)
        )

        account = cursor.fetchone()

    return account


def add_transaction(user_id: int, action: str, amount: int):

    cursor.execute(
        """
        INSERT INTO transactions
        (user_id, action, amount, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            action,
            amount,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    db.commit()


def format_money(amount: int):
    return f"{amount:,}"


# =========================================================
# Embed الحساب
# =========================================================

def account_embed(user):

    account = get_account(user.id)

    embed = discord.Embed(
        title="📊 حسابي البنكي",
        color=discord.Color.from_rgb(100, 0, 20)
    )

    embed.set_author(
        name=str(user),
        icon_url=user.display_avatar.url
    )

    embed.set_thumbnail(
        url=user.display_avatar.url
    )

    embed.add_field(
        name="💳 صرافة",
        value=f"**{format_money(account['bank'])}**",
        inline=True
    )

    embed.add_field(
        name="💵 كاش",
        value=f"**{format_money(account['cash'])}**",
        inline=True
    )

    embed.set_footer(
        text="بنك الطناطيح"
    )

    return embed


# =========================================================
# إيداع
# =========================================================

class DepositModal(
    discord.ui.Modal,
    title="💵 إيداع"
):

    amount = discord.ui.TextInput(
        label="المبلغ",
        placeholder="اكتب المبلغ الذي تريد إيداعه",
        required=True,
        min_length=1,
        max_length=15
    )

    async def on_submit(self, interaction):

        try:
            amount = int(
                self.amount.value
                .replace(",", "")
                .strip()
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ اكتب مبلغًا صحيحًا.",
                ephemeral=True
            )

            return

        if amount <= 0:

            await interaction.response.send_message(
                "❌ المبلغ يجب أن يكون أكبر من صفر.",
                ephemeral=True
            )

            return

        account = get_account(
            interaction.user.id
        )

        if account["cash"] < amount:

            await interaction.response.send_message(
                "روح يا فقير 😂",
                ephemeral=True
            )

            return

        cursor.execute(
            """
            UPDATE accounts
            SET cash = cash - ?,
                bank = bank + ?
            WHERE user_id = ?
            """,
            (
                amount,
                amount,
                interaction.user.id
            )
        )

        db.commit()

        add_transaction(
            interaction.user.id,
            "تم إيداع",
            amount
        )

        account = get_account(
            interaction.user.id
        )

        embed = discord.Embed(
            title="💵 إيداع",
            color=discord.Color.from_rgb(100, 0, 20)
        )

        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.description = (
            f"💵 **تم إيداع:** "
            f"{format_money(amount)}\n\n"
            f"💳 **الصرافة:** "
            f"{format_money(account['bank'])}\n"
            f"💵 **الكاش:** "
            f"{format_money(account['cash'])}"
        )

        embed.set_footer(
            text="بنك الطناطيح"
        )

        await interaction.response.send_message(
            embed=embed
        )


# =========================================================
# سحب
# =========================================================

class WithdrawModal(
    discord.ui.Modal,
    title="💸 سحب"
):

    amount = discord.ui.TextInput(
        label="المبلغ",
        placeholder="اكتب المبلغ الذي تريد سحبه",
        required=True,
        min_length=1,
        max_length=15
    )

    async def on_submit(self, interaction):

        try:
            amount = int(
                self.amount.value
                .replace(",", "")
                .strip()
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ اكتب مبلغًا صحيحًا.",
                ephemeral=True
            )

            return

        if amount <= 0:

            await interaction.response.send_message(
                "❌ المبلغ يجب أن يكون أكبر من صفر.",
                ephemeral=True
            )

            return

        account = get_account(
            interaction.user.id
        )

        if account["bank"] < amount:

            await interaction.response.send_message(
                "روح يا فقير 😂",
                ephemeral=True
            )

            return

        cursor.execute(
            """
            UPDATE accounts
            SET bank = bank - ?,
                cash = cash + ?
            WHERE user_id = ?
            """,
            (
                amount,
                amount,
                interaction.user.id
            )
        )

        db.commit()

        add_transaction(
            interaction.user.id,
            "تم سحب",
            amount
        )

        account = get_account(
            interaction.user.id
        )

        embed = discord.Embed(
            title="💸 سحب",
            color=discord.Color.from_rgb(100, 0, 20)
        )

        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.description = (
            f"💸 **تم سحب:** "
            f"{format_money(amount)}\n\n"
            f"💳 **الصرافة:** "
            f"{format_money(account['bank'])}\n"
            f"💵 **الكاش:** "
            f"{format_money(account['cash'])}"
        )

        embed.set_footer(
            text="بنك الطناطيح"
        )

        await interaction.response.send_message(
            embed=embed
        )


# =========================================================
# التحويل
# =========================================================

class Bank(commands.Cog):

    def __init__(self, bot):

        self.bot = bot

    @app_commands.command(
        name="تحويل",
        description="تحويل مبلغ إلى عضو آخر"
    )
    @app_commands.describe(
        المبلغ="المبلغ المراد تحويله",
        العضو="الشخص الذي تريد تحويل المبلغ له"
    )
    async def transfer(
        self,
        interaction: discord.Interaction,
        المبلغ: int,
        العضو: discord.Member
    ):

        if المبلغ <= 0:

            await interaction.response.send_message(
                "❌ المبلغ يجب أن يكون أكبر من صفر.",
                ephemeral=True
            )

            return

        if العضو.bot:

            await interaction.response.send_message(
                "❌ لا يمكنك التحويل إلى بوت.",
                ephemeral=True
            )

            return

        if العضو.id == interaction.user.id:

            await interaction.response.send_message(
                "❌ ما تقدر تحول لنفسك 😂",
                ephemeral=True
            )

            return

        sender = get_account(
            interaction.user.id
        )

        if sender["bank"] < المبلغ:

            await interaction.response.send_message(
                "روح يا فقير 😂",
                ephemeral=True
            )

            return

        get_account(العضو.id)

        cursor.execute(
            """
            UPDATE accounts
            SET bank = bank - ?
            WHERE user_id = ?
            """,
            (
                المبلغ,
                interaction.user.id
            )
        )

        cursor.execute(
            """
            UPDATE accounts
            SET bank = bank + ?
            WHERE user_id = ?
            """,
            (
                المبلغ,
                العضو.id
            )
        )

        db.commit()

        add_transaction(
            interaction.user.id,
            f"تحويل إلى {العضو.display_name}",
            المبلغ
        )

        add_transaction(
            العضو.id,
            f"تحويل من {interaction.user.display_name}",
            المبلغ
        )

        embed = discord.Embed(
            title="💸 تم التحويل",
            color=discord.Color.from_rgb(100, 0, 20)
        )

        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url
        )

        embed.description = (
            f"👤 **المستلم:** {العضو.mention}\n"
            f"💰 **المبلغ:** {format_money(المبلغ)}"
        )

        embed.set_footer(
            text="بنك الطناطيح"
        )

        await interaction.response.send_message(
            embed=embed
        )

    # =====================================================
    # لوحة البنك
    # =====================================================

    @app_commands.command(
        name="bank",
        description="فتح لوحة بنك الطناطيح"
    )
    async def bank(self, interaction):

        embed = discord.Embed(
            title="🏦 بنك الطناطيح",
            description=(
                "السلام عليكم في البنك 🏦\n\n"
                "نقدم مزايا غير عن باقي البنوك الكذابه.\n"
                "أزهلنا إذا ما جتك فلوسك مالنا دخل توكل 😂\n"
                "يمكن تلقاها في صدنايا."
            ),
            color=discord.Color.from_rgb(100, 0, 20)
        )

        embed.set_image(
            url=PANEL_IMAGE
        )

        embed.set_footer(
            text="بنك الطناطيح"
        )

        await interaction.response.send_message(
            embed=embed,
            view=BankView()
        )

    # =====================================================
    # المصروف الخاص
    # =====================================================

    @app_commands.command(
        name="تفضل_يا_طويل_العمر_مصروفك",
        description="تفضل يا طويل العمر مصروفك"
    )
    @app_commands.describe(
        المبلغ="المبلغ الذي تريد إضافته"
    )
    async def owner_money(
        self,
        interaction,
        المبلغ: int
    ):

        if interaction.user.id != OWNER_USER_ID:

            await interaction.response.send_message(
                "❌ هذا الأمر ليس لك.",
                ephemeral=True
            )

            return

        if المبلغ <= 0:

            await interaction.response.send_message(
                "❌ اكتب مبلغًا أكبر من صفر.",
                ephemeral=True
            )

            return

        get_account(
            interaction.user.id
        )

        cursor.execute(
            """
            UPDATE accounts
            SET cash = cash + ?
            WHERE user_id = ?
            """,
            (
                المبلغ,
                interaction.user.id
            )
        )

        db.commit()

        add_transaction(
            interaction.user.id,
            "تم استلام مصروف",
            المبلغ
        )

        account = get_account(
            interaction.user.id
        )

        embed = discord.Embed(
            title="👑 تفضل يا طويل العمر",
            color=discord.Color.from_rgb(100, 0, 20)
        )

        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.description = (
            f"💰 **مصروفك:** "
            f"{format_money(المبلغ)}\n\n"
            f"💵 **الكاش:** "
            f"{format_money(account['cash'])}\n"
            f"💳 **الصرافة:** "
            f"{format_money(account['bank'])}"
        )

        embed.set_footer(
            text="بنك الطناطيح"
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )


# =========================================================
# لوحة الأزرار الدائمة
# =========================================================

class BankView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    # -----------------------------------------------------
    # الراتب
    # -----------------------------------------------------

    @discord.ui.button(
        label="استلام راتب",
        emoji="💰",
        style=discord.ButtonStyle.danger,
        custom_id="bank_salary"
    )
    async def salary(
        self,
        interaction,
        button
    ):

        account = get_account(
            interaction.user.id
        )

        now = int(
            datetime.now().timestamp()
        )

        if account["last_salary"] > 0:

            next_salary = (
                account["last_salary"]
                + SALARY_COOLDOWN
            )

            if now < next_salary:

                remaining = (
                    next_salary - now
                )

                hours = remaining // 3600
                minutes = (
                    remaining % 3600
                ) // 60

                await interaction.response.send_message(
                    f"⏳ استلمت راتبك مسبقًا.\n"
                    f"تقدر تستلمه بعد "
                    f"**{hours} ساعة و {minutes} دقيقة**.",
                    ephemeral=True
                )

                return

        cursor.execute(
            """
            UPDATE accounts
            SET bank = bank + ?,
                last_salary = ?
            WHERE user_id = ?
            """,
            (
                SALARY_AMOUNT,
                now,
                interaction.user.id
            )
        )

        db.commit()

        add_transaction(
            interaction.user.id,
            "تم استلام راتب",
            SALARY_AMOUNT
        )

        embed = discord.Embed(
            title="💰 استلام راتب",
            color=discord.Color.from_rgb(100, 0, 20)
        )

        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        embed.description = (
            f"💰 **الراتب:** "
            f"{format_money(SALARY_AMOUNT)}"
        )

        embed.set_footer(
            text="بنك الطناطيح"
        )

        await interaction.response.send_message(
            embed=embed
        )

    # -----------------------------------------------------
    # الحساب
    # -----------------------------------------------------

    @discord.ui.button(
        label="حسابي البنكي",
        emoji="📊",
        style=discord.ButtonStyle.danger,
        custom_id="bank_account"
    )
    async def account_button(
        self,
        interaction,
        button
    ):

        await interaction.response.send_message(
            embed=account_embed(
                interaction.user
            )
        )

    # -----------------------------------------------------
    # إيداع
    # -----------------------------------------------------

    @discord.ui.button(
        label="إيداع",
        emoji="💵",
        style=discord.ButtonStyle.danger,
        custom_id="bank_deposit"
    )
    async def deposit_button(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            DepositModal()
        )

    # -----------------------------------------------------
    # سحب
    # -----------------------------------------------------

    @discord.ui.button(
        label="سحب",
        emoji="💸",
        style=discord.ButtonStyle.danger,
        custom_id="bank_withdraw"
    )
    async def withdraw_button(
        self,
        interaction,
        button
    ):

        await interaction.response.send_modal(
            WithdrawModal()
        )

    # -----------------------------------------------------
    # سجل العمليات
    # -----------------------------------------------------

    @discord.ui.button(
        label="سجل العمليات",
        emoji="📜",
        style=discord.ButtonStyle.danger,
        custom_id="bank_history"
    )
    async def history_button(
        self,
        interaction,
        button
    ):

        cursor.execute(
            """
            SELECT action, amount, created_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (interaction.user.id,)
        )

        rows = cursor.fetchall()

        embed = discord.Embed(
            title="📜 سجل العمليات",
            color=discord.Color.from_rgb(100, 0, 20)
        )

        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url
        )

        embed.set_thumbnail(
            url=interaction.user.display_avatar.url
        )

        if not rows:

            embed.description = (
                "لا توجد عمليات حتى الآن."
            )

        else:

            lines = []

            for row in rows:

                lines.append(
                    f"**{row['action']}** "
                    f"• `{format_money(row['amount'])}`\n"
                    f"└ {row['created_at']}"
                )

            embed.description = "\n\n".join(
                lines
            )

        embed.set_footer(
            text="آخر 10 عمليات • بنك الطناطيح"
        )

        await interaction.response.send_message(
            embed=embed
        )


# =========================================================
# Setup
# =========================================================

async def setup(bot):

    await bot.add_cog(
        Bank(bot)
    )

    # Persistent View
    bot.add_view(
        BankView()
    )
