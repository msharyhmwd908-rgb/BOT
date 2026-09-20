import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import time


# =========================================================
# الإعدادات
# =========================================================

PANEL_IMAGE = "https://e.top4top.io/p_39154nnr40.png"

OWNER_USER_ID = 1495450684731162664

# إذا عندك كاتجوري محدد حط ID هنا
# إذا تبي الرومات بدون كاتجوري خلها 0
SHOP_CATEGORY_ID = 0

# قاعدة بيانات البنك نفسها
DB_FILE = "bank.db"

# الأسعار
NORMAL_ROLE_PRICE = 67
ROLE_COLOR_PRICE = 5
CUSTOM_ROLE_PRICE = 1500
CUSTOM_COLOR_PRICE = 9


# =========================================================
# أسماء الرتب العادية
# =========================================================

SHOP_ROLES = [
    "شاروخان",
    "مترجم إيطالي",
    "دزازه",
    "مسويه",
    "عمو",
    "محمااااا",
    "فلحلح",
    "دادح",
    "كنق",
    "كوين",
    "امير",
    "اميرة",
    "باتمان",
    "امير الشات",
]


# =========================================================
# ألوان الرتب
# =========================================================

ROLE_COLORS = {
    "🔴 أحمر": 0xFF0000,
    "🍷 عنابي": 0x800020,
    "🩷 وردي": 0xFF69B4,
    "🩵 سماوي": 0x87CEEB,
    "💎 كرستالي": 0xE0FFFF,
    "🟣 بنفسجي": 0x8000FF,
    "💗 فوشي": 0xFF1493,
    "🔵 أزرق": 0x3498DB,
    "🟢 أخضر": 0x2ECC71,
    "🖤 أسود": 0x111111,
    "⚪ أبيض": 0xFFFFFF,
    "🟡 ذهبي": 0xFFD700,
}


# =========================================================
# ألوان إنشاء الرتبة الخاصة
# =========================================================

CUSTOM_COLORS = {
    "🔴 أحمر": 0xFF0000,
    "🍷 عنابي": 0x800020,
    "🩷 وردي": 0xFF69B4,
    "🩵 سماوي": 0x87CEEB,
    "💎 كرستالي": 0xE0FFFF,
    "🟣 بنفسجي": 0x8000FF,
    "💗 فوشي": 0xFF1493,
    "🔵 أزرق ملكي": 0x4169E1,
    "🟢 زمردي": 0x50C878,
    "🟡 ذهبي": 0xFFD700,
    "🌌 كحلي": 0x191970,
    "🌸 وردي فاتح": 0xFFB6C1,
}


# =========================================================
# الإيموجيات
# =========================================================

ROLE_EMOJIS = [
    "👑",
    "💎",
    "🔥",
    "⚡",
    "🌙",
    "☀️",
    "🪽",
    "🦋",
    "🐉",
    "🖤",
    "❤️",
    "💜",
]


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_account(user_id: int):
    conn = get_db()

    row = conn.execute(
        "SELECT * FROM accounts WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    if row is None:
        conn.execute(
            """
            INSERT INTO accounts
            (user_id, cash, bank, last_salary)
            VALUES (?, 0, 0, 0)
            """,
            (user_id,)
        )
        conn.commit()

    row = conn.execute(
        "SELECT * FROM accounts WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    conn.close()
    return row


def change_balance(user_id: int, balance_type: str, amount: int):
    if balance_type not in ("cash", "bank"):
        return

    conn = get_db()

    conn.execute(
        f"""
        UPDATE accounts
        SET {balance_type} = {balance_type} + ?
        WHERE user_id = ?
        """,
        (amount, user_id)
    )

    conn.commit()
    conn.close()


def add_transaction(user_id: int, action: str, amount: int):
    conn = get_db()

    conn.execute(
        """
        INSERT INTO transactions
        (user_id, action, amount, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            action,
            amount,
            int(time.time())
        )
    )

    conn.commit()
    conn.close()


# =========================================================
# توليد أرقام الرومات
# =========================================================

def get_next_number(guild: discord.Guild, prefix: str):
    numbers = []

    for channel in guild.text_channels:
        if channel.name.startswith(prefix + " "):
            try:
                number = int(
                    channel.name.replace(prefix + " ", "", 1)
                )
                numbers.append(number)
            except ValueError:
                continue

    return max(numbers, default=0) + 1


# =========================================================
# إنشاء روم خاص
# =========================================================

async def create_private_room(
    guild: discord.Guild,
    member: discord.Member,
    name: str
):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False
        ),

        member: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
    }

    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_roles=True
        )

    category = None

    if SHOP_CATEGORY_ID:
        category = guild.get_channel(SHOP_CATEGORY_ID)

    channel = await guild.create_text_channel(
        name=name,
        overwrites=overwrites,
        category=category
    )

    return channel


async def close_room(channel: discord.TextChannel):
    try:
        await channel.delete(
            reason="محل أبوي - انتهاء الطلب"
        )
    except discord.HTTPException:
        pass


# =========================================================
# الدفع
# =========================================================

class PaymentView(discord.ui.View):

    def __init__(
        self,
        member_id: int,
        role_id: int
    ):
        super().__init__(timeout=None)

        self.member_id = member_id
        self.role_id = role_id

        self.cash_button.custom_id = (
            f"shop_cash_{member_id}_{role_id}"
        )

        self.bank_button.custom_id = (
            f"shop_bank_{member_id}_{role_id}"
        )

    async def pay(
        self,
        interaction: discord.Interaction,
        balance_type: str
    ):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "هذا الروم مو لك.",
                ephemeral=True
            )
            return

        account = ensure_account(
            self.member_id
        )

        balance = account[balance_type]

        if balance < NORMAL_ROLE_PRICE:
            await interaction.response.send_message(
                "هش برا يا فقير 😂",
                ephemeral=True
            )

            try:
                await interaction.user.send(
                    "محل أبوي\n"
                    "اطرد الي ابيه واخلي الي ابيه"
                )
            except discord.HTTPException:
                pass

            await close_room(
                interaction.channel
            )
            return

        role = interaction.guild.get_role(
            self.role_id
        )

        if role is None:
            await interaction.response.send_message(
                "الرتبة غير موجودة بالسيرفر.",
                ephemeral=True
            )
            return

        # خصم سعر الرتبة
        change_balance(
            self.member_id,
            balance_type,
            -NORMAL_ROLE_PRICE
        )

        payment_name = (
            "كاش"
            if balance_type == "cash"
            else "شبكة"
        )

        add_transaction(
            self.member_id,
            f"شراء رتبة {role.name} - {payment_name}",
            NORMAL_ROLE_PRICE
        )

        await interaction.response.send_message(
            f"تم شراء رتبة **{role.name}** بنجاح.\n"
            f"طريقة الدفع: **{payment_name}**\n\n"
            f"🎨 اختر لون الرتبة — **{ROLE_COLOR_PRICE}**"
        )

        await interaction.channel.send(
            "اختر اللون الذي تريده:",
            view=RoleColorView(
                self.member_id,
                role.id
            )
        )

    @discord.ui.button(
        label="كاش",
        emoji="💵",
        style=discord.ButtonStyle.green
    )
    async def cash_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.pay(
            interaction,
            "cash"
        )

    @discord.ui.button(
        label="شبكة",
        emoji="💳",
        style=discord.ButtonStyle.blurple
    )
    async def bank_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.pay(
            interaction,
            "bank"
        )


# =========================================================
# اختيار لون رتبة عادية
# =========================================================

class RoleColorView(discord.ui.View):

    def __init__(
        self,
        member_id: int,
        role_id: int
    ):
        super().__init__(timeout=None)

        self.member_id = member_id
        self.role_id = role_id

        for color_name, color_value in ROLE_COLORS.items():
            self.add_item(
                RoleColorButton(
                    member_id,
                    role_id,
                    color_name,
                    color_value
                )
            )

        self.add_item(
            CancelColorButton(
                member_id,
                role_id
            )
        )


class RoleColorButton(discord.ui.Button):

    def __init__(
        self,
        member_id,
        role_id,
        color_name,
        color_value
    ):
        super().__init__(
            label=color_name,
            style=discord.ButtonStyle.secondary
        )

        self.member_id = member_id
        self.role_id = role_id
        self.color_name = color_name
        self.color_value = color_value

    async def callback(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "هذا الاختيار مو لك.",
                ephemeral=True
            )
            return

        account = ensure_account(
            self.member_id
        )

        # اللون يدفع من الكاش أولاً
        if account["cash"] >= ROLE_COLOR_PRICE:
            payment_type = "cash"
        elif account["bank"] >= ROLE_COLOR_PRICE:
            payment_type = "bank"
        else:
            await interaction.response.send_message(
                "هش برا يا فقير 😂\n"
                f"سعر اللون {ROLE_COLOR_PRICE}.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            self.role_id
        )

        if role is None:
            await interaction.response.send_message(
                "الرتبة غير موجودة.",
                ephemeral=True
            )
            return

        change_balance(
            self.member_id,
            payment_type,
            -ROLE_COLOR_PRICE
        )

        await role.edit(
            color=discord.Color(
                self.color_value
            )
        )

        try:
            await interaction.user.add_roles(
                role,
                reason="محل أبوي - شراء رتبة"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "ما قدرت أعطيك الرتبة. تأكد أن رتبة البوت أعلى منها.",
                ephemeral=True
            )
            return

        add_transaction(
            self.member_id,
            f"شراء لون {self.color_name} لرتبة {role.name}",
            ROLE_COLOR_PRICE
        )

        await interaction.response.send_message(
            f"تم إعطاؤك رتبة **{role.name}** "
            f"باللون **{self.color_name}** ✅"
        )

        await close_room(
            interaction.channel
        )


class CancelColorButton(discord.ui.Button):

    def __init__(
        self,
        member_id,
        role_id
    ):
        super().__init__(
            label="إلغاء اختيار اللون",
            emoji="❌",
            style=discord.ButtonStyle.red
        )

        self.member_id = member_id
        self.role_id = role_id

    async def callback(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "هذا الاختيار مو لك.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(
            self.role_id
        )

        if role is None:
            await interaction.response.send_message(
                "الرتبة غير موجودة.",
                ephemeral=True
            )
            return

        try:
            await interaction.user.add_roles(
                role,
                reason="محل أبوي - شراء رتبة"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "ما قدرت أعطيك الرتبة. تأكد أن رتبة البوت أعلى منها.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"تم إعطاؤك رتبة **{role.name}** بدون تغيير اللون ✅"
        )

        await close_room(
            interaction.channel
        )


# =========================================================
# قائمة الرتب
# =========================================================

class ShopRoleSelect(discord.ui.Select):

    def __init__(
        self,
        member_id: int
    ):
        self.member_id = member_id

        options = []

        for role_name in SHOP_ROLES:
            options.append(
                discord.SelectOption(
                    label=role_name,
                    description=f"السعر: {NORMAL_ROLE_PRICE}"
                )
            )

        super().__init__(
            placeholder="اختر الرتبة التي تريد شراءها",
            options=options,
            custom_id=f"shop_roles_{member_id}"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "القائمة مو لك.",
                ephemeral=True
            )
            return

        role_name = self.values[0]

        role = discord.utils.get(
            interaction.guild.roles,
            name=role_name
        )

        if role is None:
            await interaction.response.send_message(
                f"رتبة **{role_name}** غير موجودة بالسيرفر.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🛒 شراء رتبة",
            description=(
                f"**الرتبة:** {role.name}\n"
                f"**السعر:** {NORMAL_ROLE_PRICE}\n\n"
                "اختر طريقة الدفع:"
            )
        )

        await interaction.response.send_message(
            embed=embed,
            view=PaymentView(
                self.member_id,
                role.id
            )
        )


class ShopRoleView(discord.ui.View):

    def __init__(
        self,
        member_id: int
    ):
        super().__init__(timeout=None)

        self.add_item(
            ShopRoleSelect(
                member_id
            )
        )


# =========================================================
# إنشاء رتبة خاصة - حفظ بيانات الطلب
# =========================================================

custom_orders = {}


# =========================================================
# مودال اسم الرتبة
# =========================================================

class RoleNameModal(discord.ui.Modal):

    def __init__(
        self,
        member_id: int
    ):
        super().__init__(
            title="اسم الرتبة"
        )

        self.member_id = member_id

        self.role_name = discord.ui.TextInput(
            label="اسم الرتبة",
            placeholder="اكتب اسم الرتبة",
            required=True,
            max_length=100
        )

        self.add_item(
            self.role_name
        )

    async def on_submit(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "هذا الروم مو لك.",
                ephemeral=True
            )
            return

        custom_orders[self.member_id] = {
            "name": self.role_name.value,
            "emoji": None,
            "color": None,
            "color_name": None
        }

        await interaction.response.send_message(
            f"تم حفظ اسم الرتبة: **{self.role_name.value}**\n"
            "الحين اختر الإيموجي واللون."
        )

        await interaction.channel.send(
            "⚙️ إعداد الرتبة",
            view=CustomRoleOptionsView(
                self.member_id
            )
        )


# =========================================================
# زر اسم الرتبة
# =========================================================

class CustomRoleStartView(discord.ui.View):

    def __init__(
        self,
        member_id: int
    ):
        super().__init__(timeout=None)

        self.member_id = member_id

    @discord.ui.button(
        label="اسم الرتبة",
        emoji="📝",
        style=discord.ButtonStyle.blurple
    )
    async def role_name(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "هذا الروم مو لك.",
                ephemeral=True
            )
            return

        await interaction.response.send_modal(
            RoleNameModal(
                self.member_id
            )
        )


# =========================================================
# اختيار الإيموجي
# =========================================================

class EmojiSelect(discord.ui.Select):

    def __init__(
        self,
        member_id: int
    ):
        self.member_id = member_id

        options = []

        for emoji in ROLE_EMOJIS:
            options.append(
                discord.SelectOption(
                    label=emoji,
                    value=emoji
                )
            )

        super().__init__(
            placeholder="اختر إيموجي الرتبة",
            options=options,
            custom_id=f"custom_emoji_{member_id}"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "هذا الاختيار مو لك.",
                ephemeral=True
            )
            return

        if self.member_id not in custom_orders:
            await interaction.response.send_message(
                "ابدأ أولاً باختيار اسم الرتبة.",
                ephemeral=True
            )
            return

        custom_orders[
            self.member_id
        ]["emoji"] = self.values[0]

        await interaction.response.send_message(
            f"تم اختيار الإيموجي {self.values[0]} ✅",
            ephemeral=True
        )


# =========================================================
# اختيار لون الرتبة الخاصة
# =========================================================

class CustomColorSelect(discord.ui.Select):

    def __init__(
        self,
        member_id: int
    ):
        self.member_id = member_id

        options = []

        for color_name, color_value in CUSTOM_COLORS.items():
            options.append(
                discord.SelectOption(
                    label=color_name,
                    description=f"السعر: {CUSTOM_COLOR_PRICE}",
                    value=str(color_value)
                )
            )

        super().__init__(
            placeholder="اختر لون الرتبة",
            options=options,
            custom_id=f"custom_color_{member_id}"
        )

    async def callback(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "هذا الاختيار مو لك.",
                ephemeral=True
            )
            return

        if self.member_id not in custom_orders:
            await interaction.response.send_message(
                "ابدأ أولاً باختيار اسم الرتبة.",
                ephemeral=True
            )
            return

        color_value = int(
            self.values[0]
        )

        color_name = next(
            (
                name
                for name, value in CUSTOM_COLORS.items()
                if value == color_value
            ),
            "غير معروف"
        )

        custom_orders[
            self.member_id
        ]["color"] = color_value

        custom_orders[
            self.member_id
        ]["color_name"] = color_name

        await interaction.response.send_message(
            f"تم اختيار اللون **{color_name}** "
            f"بسعر **{CUSTOM_COLOR_PRICE}**.",
            ephemeral=True
        )


# =========================================================
# خيارات الرتبة الخاصة
# =========================================================

class CustomRoleOptionsView(discord.ui.View):

    def __init__(
        self,
        member_id: int
    ):
        super().__init__(timeout=None)

        self.add_item(
            EmojiSelect(
                member_id
            )
        )

        self.add_item(
            CustomColorSelect(
                member_id
            )
        )

        self.add_item(
            ConfirmCustomRoleButton(
                member_id
            )
        )


# =========================================================
# تأكيد إنشاء الرتبة
# =========================================================

class ConfirmCustomRoleButton(discord.ui.Button):

    def __init__(
        self,
        member_id: int
    ):
        super().__init__(
            label="تأكيد",
            emoji="✅",
            style=discord.ButtonStyle.green
        )

        self.member_id = member_id

    async def callback(
        self,
        interaction: discord.Interaction
    ):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "هذا الروم مو لك.",
                ephemeral=True
            )
            return

        order = custom_orders.get(
            self.member_id
        )

        if not order:
            await interaction.response.send_message(
                "ابدأ أولاً باختيار اسم الرتبة.",
                ephemeral=True
            )
            return

        if not order["name"]:
            await interaction.response.send_message(
                "اختر اسم الرتبة أولاً.",
                ephemeral=True
            )
            return

        if not order["emoji"]:
            await interaction.response.send_message(
                "اختر إيموجي الرتبة أولاً.",
                ephemeral=True
            )
            return

        if order["color"] is None:
            await interaction.response.send_message(
                "اختر لون الرتبة أولاً.",
                ephemeral=True
            )
            return

        account = ensure_account(
            self.member_id
        )

        # سعر اللون 9
        if account["cash"] >= CUSTOM_COLOR_PRICE:
            payment_type = "cash"
        elif account["bank"] >= CUSTOM_COLOR_PRICE:
            payment_type = "bank"
        else:
            await interaction.response.send_message(
                "هش برا يا فقير 😂\n"
                f"سعر اللون {CUSTOM_COLOR_PRICE}.",
                ephemeral=True
            )
            return

        # خصم سعر اللون
        change_balance(
            self.member_id,
            payment_type,
            -CUSTOM_COLOR_PRICE
        )

        add_transaction(
            self.member_id,
            f"لون رتبة خاصة {order['name']}",
            CUSTOM_COLOR_PRICE
        )

        # إنشاء الرتبة
        try:
            role = await interaction.guild.create_role(
                name=(
                    f"{order['emoji']} "
                    f"{order['name']}"
                ),
                color=discord.Color(
                    order["color"]
                ),
                reason="محل أبوي - إنشاء رتبة خاصة"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "ما قدرت أنشئ الرتبة.\n"
                "تأكد أن رتبة البوت عندها Manage Roles.",
                ephemeral=True
            )
            return

        # إعطاء الرتبة لصاحبها فقط
        try:
            await interaction.user.add_roles(
                role,
                reason="محل أبوي - رتبة خاصة"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "تم إنشاء الرتبة لكن ما قدرت أعطيها لك.\n"
                "ارفع رتبة البوت فوق الرتبة التي ينشئها.",
                ephemeral=True
            )
            return

        # رسالة للمالك
        owner = interaction.guild.get_member(
            OWNER_USER_ID
        )

        owner_message = (
            "🏪 **محل أبوي — إنشاء رتبة**\n\n"
            f"**العضو:** {interaction.user} "
            f"({interaction.user.id})\n"
            f"**اسم الرتبة:** {order['name']}\n"
            f"**الإيموجي:** {order['emoji']}\n"
            f"**اللون:** {order['color_name']}"
        )

        if owner:
            try:
                await owner.send(
                    owner_message
                )
            except discord.HTTPException:
                pass

        await interaction.response.send_message(
            f"تم إنشاء رتبتك **{role.name}** وإعطاؤك إياها 👑"
        )

        custom_orders.pop(
            self.member_id,
            None
        )

        await close_room(
            interaction.channel
        )


# =========================================================
# سجل الرتب
# =========================================================

class MyRolesView(discord.ui.View):

    def __init__(
        self,
        member_id: int
    ):
        super().__init__(timeout=None)

        self.member_id = member_id

    @discord.ui.button(
        label="إغلاق",
        emoji="🔒",
        style=discord.ButtonStyle.red
    )
    async def close(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user.id != self.member_id:
            await interaction.response.send_message(
                "هذا الروم مو لك.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "تم إغلاق السجل."
        )

        await close_room(
            interaction.channel
        )


# =========================================================
# لوحة المحل
# =========================================================

class ShopView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # -----------------------------------------------------
    # شراء رتب
    # -----------------------------------------------------

    @discord.ui.button(
        label="شراء رتب",
        emoji="🛒",
        style=discord.ButtonStyle.green,
        custom_id="shop_buy_roles"
    )
    async def buy_roles(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        number = get_next_number(
            interaction.guild,
            "شوب"
        )

        channel = await create_private_room(
            interaction.guild,
            interaction.user,
            f"شوب {number}"
        )

        embed = discord.Embed(
            title="🛒 محل أبوي",
            description=(
                "اختر الرتبة التي تريد شراءها.\n\n"
                f"💰 سعر جميع الرتب: **{NORMAL_ROLE_PRICE}**"
            )
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=ShopRoleView(
                interaction.user.id
            )
        )

        await interaction.response.send_message(
            f"تم فتح روم الشراء {channel.mention}",
            ephemeral=True
        )

    # -----------------------------------------------------
    # إنشاء رتبة خاصة
    # -----------------------------------------------------

    @discord.ui.button(
        label="شراء 1500",
        emoji="👑",
        style=discord.ButtonStyle.red,
        custom_id="shop_custom_role"
    )
    async def custom_role(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        account = ensure_account(
            interaction.user.id
        )

        total = (
            account["cash"] +
            account["bank"]
        )

        if total < CUSTOM_ROLE_PRICE:
            await interaction.response.send_message(
                "هش برا يا فقير 😂",
                ephemeral=True
            )

            try:
                await interaction.user.send(
                    "محل أبوي\n"
                    "اطرد الي ابيه واخلي الي ابيه"
                )
            except discord.HTTPException:
                pass

            return

        # دفع 1500
        if account["cash"] >= CUSTOM_ROLE_PRICE:
            payment_type = "cash"
        else:
            payment_type = "bank"

        change_balance(
            interaction.user.id,
            payment_type,
            -CUSTOM_ROLE_PRICE
        )

        add_transaction(
            interaction.user.id,
            "شراء إنشاء رتبة خاصة",
            CUSTOM_ROLE_PRICE
        )

        # بعد الشراء يظهر الروم
        number = get_next_number(
            interaction.guild,
            "إنشاء"
        )

        channel = await create_private_room(
            interaction.guild,
            interaction.user,
            f"إنشاء {number}"
        )

        embed = discord.Embed(
            title="👑 إنشاء رتبة خاصة",
            description=(
                f"تم دفع **{CUSTOM_ROLE_PRICE}** بنجاح.\n\n"
                "ابدأ بالضغط على **اسم الرتبة**.\n"
                "بعدها اختر الإيموجي واللون.\n\n"
                f"🎨 سعر اللون: **{CUSTOM_COLOR_PRICE}**"
            )
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=CustomRoleStartView(
                interaction.user.id
            )
        )

        await interaction.response.send_message(
            f"تم فتح روم إنشاء الرتبة: {channel.mention}",
            ephemeral=True
        )

    # -----------------------------------------------------
    # رتبي وإنشائي
    # -----------------------------------------------------

    @discord.ui.button(
        label="رتبي وإنشائي",
        emoji="📋",
        style=discord.ButtonStyle.blurple,
        custom_id="shop_my_roles"
    )
    async def my_roles(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        number = get_next_number(
            interaction.guild,
            "سجلي"
        )

        channel = await create_private_room(
            interaction.guild,
            interaction.user,
            f"سجلي {number}"
        )

        # الرتب التي عند العضو
        member_roles = [
            role
            for role in interaction.user.roles
            if role != interaction.guild.default_role
        ]

        if member_roles:
            roles_text = "\n".join(
                f"• {role.mention}"
                for role in member_roles
            )
        else:
            roles_text = "ما عندك رتب."

        embed = discord.Embed(
            title="📋 رتبي وإنشائي",
            description=(
                "### الرتب عندك\n"
                f"{roles_text}\n\n"
                "### الرتب الخاصة\n"
                "أي رتبة خاصة أنشأتها من محل أبوي تظهر هنا "
                "إذا كانت موجودة عندك."
            )
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=MyRolesView(
                interaction.user.id
            )
        )

        await interaction.response.send_message(
            f"تم فتح سجلك: {channel.mention}",
            ephemeral=True
        )


# =========================================================
# الـ COG
# =========================================================

class Shop(commands.Cog):

    def __init__(
        self,
        bot: commands.Bot
    ):
        self.bot = bot

    @app_commands.command(
        name="المحل",
        description="فتح محل أبوي"
    )
    async def shop(
        self,
        interaction: discord.Interaction
    ):
        embed = discord.Embed(
            title="🏪 محل أبوي",
            description="محل أبوي بإسم ابوي احد عنده مانع ؟",
            color=discord.Color.from_rgb(
                100,
                0,
                20
            )
        )

        embed.set_image(
            url=PANEL_IMAGE
        )

        await interaction.response.send_message(
            embed=embed,
            view=ShopView()
        )


async def setup(bot):
    await bot.add_cog(
        Shop(bot)
    )

    # الأزرار الرئيسية لا تنتهي بعد إعادة تشغيل البوت
    bot.add_view(
        ShopView()
    )
