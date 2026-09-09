import discord
from discord.ext import commands

class StoreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # أزرار دائمة بدون انتهاء

    @discord.ui.button(label="دخول المتجر", style=discord.ButtonStyle.secondary, emoji="🛍️", custom_id="persistent_store_enter")
    async def enter_store(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("أهلاً بك في المتجر! تصفح الأقسام المتاحة وابدأ التسوق الآن.", ephemeral=True)

    @discord.ui.button(label="توجه إلى الإدارة", style=discord.ButtonStyle.danger, emoji="🛠️", custom_id="persistent_store_admin")
    async def contact_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("إذا واجهتك أي مشكلة أثناء الشراء، يرجى التوجه فوراً إلى روم التكت الخاص والإدارة هنا: <#1542935432445165689>", ephemeral=True)

    @discord.ui.button(label="معلومات المتجر", style=discord.ButtonStyle.primary, emoji="ℹ️", custom_id="persistent_store_info")
    async def store_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        private_message = (
            "🌟 **مرحباً بك في تفاصيل متجرنا المتواضع!**\n\n"
            "نحن سعيدون جداً بزيارتك ونحرص على تقديم أفضل تجربة ممكنة لك:\n\n"
            "• 🛍️ **ماذا نقدم؟** نوفر لك منتجات وخدمات مميزة وبأفضل الأسعار المنافسة.\n"
            "• ⚡ **سرعة التنفيذ:** يتم تسليم الطلبات والخدمات بشكل آلي أو سريع جداً بعد إتمام الدفع.\n"
            "• 🛡️ **الأمان والثقة:** جميع تعاملاتنا محمية وفريق الإدارة جاهز لخدمتك على مدار الساعة.\n"
            "• 💬 **الدعم الفني:** لو واجهتك أي عقبة، زر الإدارة في السيرفر موجود دائماً لمساعدتك.\n\n"
            "شكراً لاختيارك لنا، ونتمنى لك رحلة تسوق سعيدة معنا! ❤️"
        )
        try:
            await interaction.user.send(private_message)
            await interaction.response.send_message("تم إرسال معلومات المتجر في رسالة خاصة (تأكد من فتح الخاص ✅).", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("عذراً، لم أستطع إرسال رسالة خاصة لأن رسائلك مغلقة. إليك المعلومات هنا:\n\n" + private_message, ephemeral=True)

class Store(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(StoreView())

    @discord.app_commands.command(name="store", description="إرسال لوحة المتجر الرئيسية")
    async def store_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(color=discord.Color.from_rgb(0, 150, 255))
        embed.set_image(url="https://h.top4top.io/p_39044coda0.png")
        await interaction.response.send_message(embed=embed, view=StoreView())

async def setup(bot):
    await bot.add_cog(Store(bot))
