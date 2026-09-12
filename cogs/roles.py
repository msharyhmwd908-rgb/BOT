import discord
from discord.ext import commands

# ----------------- الإعدادات والآدات المطلوبة -----------------
GENDER_ROLES = {
    "boy": 1548367554295369819,
    "girl": 1548367744414515241
}

COLOR_ROLES = {
    "red": 1548368687487258694,
    "orange": 1548368909734908065,
    "yellow": 1548369074403418254,
    "green": 1548369206406283325,
    "skyblue": 1548369363923505373,
    "pink": 1548369523952980048,
    "brown": 1548369817210458142,
    "silver": 1548369993501245440,
    "white": 1548370130529157270,
    "black": 1548370270610260060
}

# رابط صورتك الجديدة المعتمدة
HAND_IMAGE_URL = "https://cdn.phototourl.com/free/2026-09-12-34690126-831d-4c61-a227-cb0a9dde78bf.png"

# ----------------- خطوة الألوان (السؤال الثاني) -----------------
class ColorSelectView(discord.ui.View):
    def __init__(self, chosen_gender_role_id: int):
        super().__init__(timeout=None) # دائم لا ينتهي
        self.chosen_gender_role_id = chosen_gender_role_id
        self.add_item(ColorSelectDropdown(chosen_gender_role_id))

class ColorSelectDropdown(discord.ui.Select):
    def __init__(self, chosen_gender_role_id: int):
        self.chosen_gender_role_id = chosen_gender_role_id
        options = [
            discord.SelectOption(label="أحمر", emoji="🔴", value="red"),
            discord.SelectOption(label="برتقالي", emoji="🟠", value="orange"),
            discord.SelectOption(label="أصفر", emoji="🟡", value="yellow"),
            discord.SelectOption(label="أخضر", emoji="🟢", value="green"),
            discord.SelectOption(label="أزرق سماوي", emoji="🩵", value="skyblue"),
            discord.SelectOption(label="وردي", emoji="🩷", value="pink"),
            discord.SelectOption(label="بني", emoji="🤎", value="brown"),
            discord.SelectOption(label="فضي", emoji="🩶", value="silver"),
            discord.SelectOption(label="أبيض", emoji="🤍", value="white"),
            discord.SelectOption(label="أسود", emoji="🖤", value="black"),
        ]
        super().__init__(placeholder="🎨 | اختر اللون الذي تحبه...", min_values=1, max_values=1, options=options, custom_id="persistent_color_select")

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        selected_color_key = self.values[0]
        new_color_role_id = COLOR_ROLES[selected_color_key]

        # 1. إعطاء رتبة الجنس المختارة (مع إزالة باقي رتب الجنس الأخرى إن وجدت)
        for g_key, g_id in GENDER_ROLES.items():
            r = guild.get_role(g_id)
            if r:
                if g_id == self.chosen_gender_role_id:
                    if r not in member.roles:
                        await member.add_roles(r)
                else:
                    if r in member.roles:
                        await member.remove_roles(r)

        # 2. إعطاء رتبة اللون الجديدة وإزالة أي رتبة لون قديمة أخرى
        for c_key, c_id in COLOR_ROLES.items():
            r = guild.get_role(c_id)
            if r:
                if c_id == new_color_role_id:
                    if r not in member.roles:
                        await member.add_roles(r)
                else:
                    if r in member.roles:
                        await member.remove_roles(r)

        # 3. إرسال رسالة النجاح النهائية
        await interaction.response.edit_message(
            content="✅ **تم اختيار رتبك بنجاح!**\nشكراً لك، تم تطبيق رتبة الجنس واللون المطلوبة.",
            embed=None,
            view=None
        )


# ----------------- خطوة الجنس (السؤال الأول) -----------------
class GenderSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # دائم لا ينتهي

    @discord.ui.button(label="ولد", style=discord.ButtonStyle.primary, emoji="👦", custom_id="persistent_gender_boy")
    async def select_boy(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id = GENDER_ROLES["boy"]
        await self.proceed_to_color(interaction, role_id)

    @discord.ui.button(label="بنت", style=discord.ButtonStyle.danger, emoji="👧", custom_id="persistent_gender_girl")
    async def select_girl(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_id = GENDER_ROLES["girl"]
        await self.proceed_to_color(interaction, role_id)

    async def proceed_to_color(self, interaction: discord.Interaction, gender_role_id: int):
        embed = discord.Embed(
            title="🎨 اختيار اللون المفضّل",
            description="حنا نخيرك، ما نغصبك\n\n**اي لون تحبـ/ـين؟**\nاختر لونك المفضل من القائمة أدناه:",
            color=discord.Color.from_rgb(0, 150, 255)
        )
        embed.set_image(url=HAND_IMAGE_URL)
        
        await interaction.response.edit_message(
            embed=embed,
            view=ColorSelectView(gender_role_id)
        )


# ----------------- اللوحة الرئيسية لاختيار الرتب -----------------
class MainRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # دائم لا ينتهي

    @discord.ui.button(label="بدء اختيار الرتب", style=discord.ButtonStyle.success, emoji="✨", custom_id="persistent_start_roles_btn")
    async def start_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="👤 اختيار الجنس",
            description="حنا نخيرك، ما نغصبك\n\n**ما هو جنسكـ/ـي؟**\nاختر من الأزرار أدناه:",
            color=discord.Color.from_rgb(0, 150, 255)
        )
        embed.set_image(url=HAND_IMAGE_URL)
        
        await interaction.response.send_message(
            embed=embed,
            view=GenderSelectView(),
            ephemeral=True
        )

    @discord.ui.button(label="انتقل للدعم", style=discord.ButtonStyle.secondary, emoji="🛠️", custom_id="persistent_goto_support_btn")
    async def goto_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🛠️ يمكنك التوجه إلى قسم الدعم الفني عبر فتح تذكرة من الروم المخصص للدعم.",
            ephemeral=True
        )


# ----------------- ملف الـ Cog الرئيسي -----------------
class RolesSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(MainRolesView())
        self.bot.add_view(GenderSelectView())

    @discord.app_commands.command(name="roles-setup", description="إرسال لوحة اختيار الرتب الفخمة")
    @commands.has_permissions(administrator=True)
    async def roles_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="اختر رتبك",
            description="حنا نخيرك، ما نغصبك\n\nاضغط على الزر أدناه لبدء عملية تخصيص واختيار رتبك الخاصة بكل مرونة واحترافية.",
            color=discord.Color.from_rgb(0, 150, 255)
        )
        embed.set_image(url=HAND_IMAGE_URL)
        
        await interaction.response.send_message(embed=embed, view=MainRolesView())

async def setup(bot):
    await bot.add_cog(RolesSetup(bot))
