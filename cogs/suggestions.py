import discord
from discord.ext import commands
from discord import app_commands
import json
import os

DATA_FILE = "suggestions_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {"count": 0, "suggestions": {}}
    return {"count": 0, "suggestions": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

COLORS = {
    "أصفر": 0xF1C40F,
    "أحمر": 0xE74C3C,
    "أزرق": 0x3498DB,
    "أخضر": 0x2ECC71,
    "بنفسجي": 0x9B59B6,
    "برتقالي": 0xE67E22,
    "وردي": 0xFF69B4,
    "تركوازي": 0x1ABC9C,
    "ذهبي": 0xD4AF37,
    "رمادي": 0x95A5A6,
    "أبيض": 0xFFFFFF,
    "بني": 0x8B4513,
    "كحلي": 0x1B4F72
}

class SuggestionModal(discord.ui.Modal, title="شاركنا فكرتك للتطوير"):
    def __init__(self, color_name: str):
        super().__init__(timeout=None)
        self.color_name = color_name

    idea_input = discord.ui.TextInput(
        label="اكتب فكرتك (لا تحط أمثلة)",
        style=discord.TextStyle.paragraph,
        placeholder="اكتب تفاصيل فكرتك هنا بوضوح...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        data["count"] += 1
        s_id = str(data["count"])
        
        data["suggestions"][s_id] = {
            "author_id": interaction.user.id,
            "text": self.idea_input.value,
            "color_name": self.color_name,
            "streak": 0,
            "voters": [],
            "ratings": [],
            "rejections": 0,
            "dm_sent": False
        }
        save_data(data)

        embed = discord.Embed(
            title=f"💡 فكرة رقم #{s_id}",
            description=f"**{self.idea_input.value}**",
            color=COLORS.get(self.color_name, 0xFFFFFF)
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="صاحب الفكرة", value=interaction.user.mention, inline=False)
        embed.add_field(name="التقييم والستريك", value="🕯️ الستريك: 0 | ⭐ التقييم: 0.0 (0) | ❌ رفض: 0", inline=False)
        
        view = SuggestionView(s_id)
        
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ تم إرسال فكرتك بنجاح وتوثيقها!", ephemeral=True)

class ColorSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        options = [discord.SelectOption(label=name, value=name) for name in COLORS.keys()]
        
        self.select_menu = discord.ui.Select(
            placeholder="اختر لون الفكرة...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="color_select_menu_persistent"
        )
        self.select_menu.callback = self.select_callback
        self.add_item(self.select_menu)

    async def select_callback(self, interaction: discord.Interaction):
        selected_color = self.select_menu.values[0]
        modal = SuggestionModal(color_name=selected_color)
        await interaction.response.send_modal(modal)

class SuggestionView(discord.ui.View):
    def __init__(self, s_id: str):
        super().__init__(timeout=None)
        self.s_id = s_id

    @discord.ui.button(label="تصويت / سحب", style=discord.ButtonStyle.green, custom_id="vote_btn_action")
    async def vote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        data = load_data()
        if self.s_id not in data["suggestions"]:
            await interaction.response.send_message("❌ هذه الفكرة غير موجودة.", ephemeral=True)
            return

        s_data = data["suggestions"][self.s_id]
        user_id_str = str(interaction.user.id)

        if user_id_str in s_data["voters"]:
            s_data["voters"].remove(user_id_str)
            s_data["streak"] = max(0, s_data["streak"] - 1)
            action_msg = "تم سحب تصويتك بنجاح."
        else:
            s_data["voters"].append(user_id_str)
            s_data["streak"] += 1
            action_msg = "تم تسجيل صوتك بنجاح!"

        streak = s_data["streak"]
        if streak >= 20:
            streak_icon = "🕯️🔥 [اللون النهائي 20+]"
            if not s_data.get("dm_sent", False):
                s_data["dm_sent"] = True
                try:
                    author = await interaction.client.fetch_user(s_data["author_id"])
                    await author.send("الله يجزاك خير على الفكرة الي تبيض الوجه امواححح يا شيخ .")
                except:
                    pass
        elif streak >= 11:
            streak_icon = f"🕯️💜 (الستريك: {streak})"
        elif streak >= 7:
            streak_icon = f"🕯️💙 (الستريك: {streak})"
        elif streak >= 3:
            streak_icon = f"🕯️💖 (الستريك: {streak})"
        else:
            streak_icon = f"🕯️ (الستريك: {streak})"

        save_data(data)

        embed = interaction.message.embeds[0]
        ratings = s_data["ratings"]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
        
        embed.set_field_at(
            1,
            name="التقييم والستريك",
            value=f"{streak_icon} | ⭐ التقييم: {avg_rating} ({len(ratings)}) | ❌ رفض: {s_data['rejections']}",
            inline=False
        )
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message(action_msg, ephemeral=True)

    @discord.ui.button(label="تقييم الفكرة", style=discord.ButtonStyle.blurple, custom_id="rate_btn_action")
    async def rate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RateModal(self.s_id))

class RateModal(discord.ui.Modal, title="تقييم الفكرة"):
    def __init__(self, s_id: str):
        super().__init__(timeout=None)
        self.s_id = s_id

    rating_input = discord.ui.TextInput(
        label="اكتب تقييمك من 0 إلى 6 (0 يعني رفض)",
        placeholder="اكتب رقم من 0 إلى 6...",
        min_length=1,
        max_length=1,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        val = self.rating_input.value
        if not val.isdigit() or not (0 <= int(val) <= 6):
            await interaction.response.send_message("❌ خطأ: يجب أن يكون التقييم رقماً صحيحاً بين 0 و 6 حصراً.", ephemeral=True)
            return

        score = int(val)
        data = load_data()
        if self.s_id not in data["suggestions"]:
            await interaction.response.send_message("❌ الفكرة غير موجودة.", ephemeral=True)
            return

        s_data = data["suggestions"][self.s_id]
        
        if score == 0:
            s_data["rejections"] += 1
        else:
            s_data["ratings"].append(score)

        save_data(data)

        msg = interaction.message
        embed = msg.embeds[0]
        streak = s_data["streak"]
        
        if streak >= 20:
            streak_icon = "🕯️🔥 [اللون النهائي 20+]"
        elif streak >= 11:
            streak_icon = f"🕯️💜 (الستريك: {streak})"
        elif streak >= 7:
            streak_icon = f"🕯️💙 (الستريك: {streak})"
        elif streak >= 3:
            streak_icon = f"🕯️💖 (الستريك: {streak})"
        else:
            streak_icon = f"🕯️ (الستريك: {streak})"

        ratings = s_data["ratings"]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

        embed.set_field_at(
            1,
            name="التقييم والستريك",
            value=f"{streak_icon} | ⭐ التقييم: {avg_rating} ({len(ratings)}) | ❌ رفض: {s_data['rejections']}",
            inline=False
        )
        
        view = SuggestionView(self.s_id)
        await msg.edit(embed=embed, view=view)
        await interaction.response.send_message(f"✅ تم تسجيل تقييمك ({score}) بنجاح!", ephemeral=True)

class MainPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="انتقل للإدارة (شارك فكرتك)", style=discord.ButtonStyle.primary, custom_id="open_suggestion_menu_persistent_btn")
    async def open_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ColorSelectView()
        await interaction.response.send_message("اختر لون الفكرة المناسب لتظهر رسالتك به:", view=view, ephemeral=True)

class SuggestionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_suggestions", description="إرسال لوحة شارك أفكارك لتطوير السيرفر")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_suggestions(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="✨ شارك أفكارك معنا لتطوير السيرفر",
            description="نحن نرحب بكافة آرائك واقترحاتك البناءة لتطوير السيرفر وجعله أفضل دائماً.\nاضغط على الزر أدناه للبدء في كتابة فكرتك واختيار لونها الخاص!",
            color=0x2B2D31
        )
        embed.set_image(url="https://f.top4top.io/p_3909ea6fn0.png")
        
        view = MainPanelView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ تمت إرسال لوحة الأفكار بنجاح!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SuggestionsCog(bot))
