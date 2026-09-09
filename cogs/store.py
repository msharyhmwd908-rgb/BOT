import discord
from discord.ext import commands

# قسيمة الرتب الـ 13 مع نقاطها (30 نقطة بدون مدة محددة)
ROLES_DATA = [
    {"name": "جنون العظمة", "cost": 30},
    {"name": "محنك", "cost": 30},
    {"name": "ساطي", "cost": 30},
    {"name": "سامج", "cost": 30},
    {"name": "فراشه", "cost": 30},
    {"name": "نسونجي", "cost": 30},
    {"name": "نرجسي", "cost": 30},
    {"name": "Meow", "cost": 30},
    {"name": "ذيب جداوي", "cost": 30},
    {"name": "قصيمي", "cost": 30},
    {"name": "Catfish", "cost": 30},
    {"name": "وزير الدفاع", "cost": 30},
]

class RolePurchaseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # أزرار دائمة بدون انتهاء
        
        # إنشاء الأزرار تلقائياً للرتب الـ 13
        for index, role in enumerate(ROLES_DATA):
            button = discord.ui.Button(
                label=f"{role['name']} ({role['cost']} نقطة)",
                style=discord.ButtonStyle.success,
                custom_id=f"buy_role_{index}"
            )
            button.callback = self.create_callback(role['name'], role['cost'])
            self.add_item(button)

    def create_callback(self, role_name, cost):
        async def button_callback(interaction: discord.Interaction):
            # هنا يمكنك ربط نظام نقاطك الخاص (مثلاً خصم 30 نقطة وإعطائه الرتبة)
            # كمثال توضيحي:
            await interaction.response.send_message(
                f"✅ تم شراء رتبة **{role['name']}** بنجاح مقابل {cost} نقطة وبدون مدة محددة!", 
                ephemeral=True
            )
        return button_callback

class StoreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # أزرار دائمة

    @discord.ui.button(label="دخول المتجر", style=discord.ButtonStyle.secondary, emoji="🛍️", custom_id="persistent_store_enter")
    async def enter_store(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user

        # إعدادات الصلاحيات للروم الخاص (لا يراه إلا العضو والبوت والإدارة إن أردت)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }

        # إنشاء روم خاص باسم العضو
        category = interaction.channel.category  # ينشئه في نفس الفئة إن وجدت، أو عشوائي
        channel_name = f"store-{member.name}"
        
        private_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            topic=f"متجر خاص بالعضو {member.display_name}"
        )

        # إرسال رسالة المتجر الداخلية التي تحتوي على الـ 13 زر للرتب
        embed = discord.Embed(
            title="🛒 قسم شراء الرتب الخاصة",
            description="أهلاً بك في متجرك الخاص! اختر الرتبة التي تناسبك واضغط على زر الشراء أدناه:",
            color=discord.Color.gold()
        )
        embed.set_image(url="https://h.top4top.io/p_39044coda0.png")

        await private_channel.send(
            content=f"مرحباً بك {member.mention} في روم المتجر الخاص بك!",
            embed=embed,
            view=RolePurchaseView()
        )

        # الرد على المستخدم برابط الروم الخاص به
        await interaction.response.send_message(f" تم إنشاء روم المتجر الخاص بك هنا: {private_channel.mention}", ephemeral=True)

    @discord.ui.button(label="توجه إلى الإدارة", style=discord.ButtonStyle.danger, emoji="🛠️", custom_id="persistent_store_admin")
    async def contact_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("إذا واجهتك أي مشكلة أثناء الشراء، يرجى التوجه فوراً إلى روم التكت الخاص بالإدارة هنا: <#1542935432445165689>", ephemeral=True)

    @discord.ui.button(label="معلومات المتجر", style=discord.ButtonStyle.primary, emoji="ℹ️", custom_id="persistent_store_info")
    async def store_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        private_message = (
            "🌟 **مرحباً بك في تفاصيل متجرنا المتواضع!**\n\n"
            "نحن سعيدون جداً بزيارتك ونحرص على تقديم أفضل تجربة ممكنة لك:\n\n"
            "• 🛍️ **ماذا نقدم؟** نوفر لك رتب مميزة ودائمة وبأفضل الأسعار.\n"
            "• ⚡ **سرعة التنفيذ:** يتم تسليم الرتب بشكل آلي فور الضغط على زر الشراء.\n"
            "• 🛡️ **الأمان والثقة:** جميع تعاملاتنا محمية وفريق الإدارة جاهز لخدمتك.\n\n"
            "شكراً لاختيارك لنا! ❤️"
        )
        try:
            await interaction.user.send(private_message)
            await interaction.response.send_message("تم إرسال معلومات المتجر في رسالة خاصة (تأكد من فتح الخاص ✅).", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("عذراً، لم أستطع إرسال رسالة خاصة لأن رسائلك مغلقة. إليك المعلومات هنا:\n\n" + private_message, ephemeral=True)

class Store(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # تسجيل جميع الأطراف الدائمة لكي لا تعطل بعد إعادة التشغيل
        self.bot.add_view(StoreView())
        self.bot.add_view(RolePurchaseView())

    @discord.app_commands.command(name="store", description="إرسال لوحة المتجر الرئيسية")
    async def store_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✨ يا هلا يا هلا في متجرنا المتواضع ✨",
            description="تصفح الأقسام المتاحة، وقم باختيار ما يناسبك من الرتب المميزة.\n\n"
                        "⚠️ **تنبيه هام:** إذا واجهتك مشكلة أثناء الشراء، اضغط على زر الإدارة أدناه للمساعدة الفورية.",
            color=discord.Color.from_rgb(0, 150, 255)
        )
        embed.set_image(url="https://h.top4top.io/p_39044coda0.png")
        
        await interaction.response.send_message(embed=embed, view=StoreView())

async def setup(bot):
    await bot.add_cog(Store(bot))
