import discord
from discord.ext import commands

class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # أزرار دائمة لا تنتهي

    @discord.ui.button(label="📜 عرض القوانين", style=discord.ButtonStyle.primary, emoji="⚖️", custom_id="persistent_rules_btn")
    async def show_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="⚖️ قوانين سيرفر سوالف الرسمية",
            description=(
                "مرحباً بك في سيرفرنا! لضمان بيئة ممتعة وآمنة للجميع، نرجو الالتزام بالآتي:\n\n"
                "1️⃣ **الاحترام المتبادل:** يمنع منعاً باتاً السب، الشتم، أو الاستهزاء بأي عضو.\n"
                "2️⃣ **مواضيع النقاش:** يمنع التحدث في المواضيع السياسية، الطائفية، أو الحساسة.\n"
                "3️⃣ **الإزعاج والسبام:** يمنع تكرار الرسائل المزعجة (Spam) أو استخدام المايك بشكل مزعج في الرومات الصوتية.\n"
                "4️⃣ **المنشن العشوائي:** يمنع عمل منشن للإدارة بدون سبب حقيقي أو طارئ.\n"
                "5️⃣ **الصور والروابط:** يمنع نشر محتوى غير ملق وكريه أو روابط مشبوهة وإعلانات خارجية.\n"
                "6️⃣ **الأدب العام:** أي استهبال زائد أو مخالفة للأدب ستعرضك للعقوبة الفورية (تايم أوت / طرد).\n\n"
                "⚠️ *جهلك بالقوانين لا يعفيك من المسؤولية!*"
            ),
            color=discord.Color.from_rgb(0, 150, 255)
        )
        embed.set_footer(text="شكراً لتعاونكم معنا في جعل السيرفر أفضل مكان للجميع ❤️")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(RulesView())

    @discord.app_commands.command(name="rules-setup", description="إرسال لوحة قوانين السيرفر الرسمية")
    @commands.has_permissions(administrator=True)
    async def rules_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📜 قوانين السيرفر الأساسية",
            description="حرصاً على راحت الجميع وتنظيم السيرفر، يرجى قراءة القوانين بعناية عبر الضغط على الزر أدناه.",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, view=RulesView())

async def setup(bot):
    await bot.add_cog(Rules(bot))
