import discord
from discord import app_commands
from discord.ext import commands
import json
import os

DATA_FILE = "suggestions_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"streak": 0, "suggestions": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"streak": 0, "suggestions": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# مودال كتابة الفكرة
class SuggestionModal(discord.ui.Modal, title="شاركنا فكرتك للتطوير"):
    def __init__(self, color_name: str, color_hex: int):
        super().__init__()
        self.color_name = color_name
        self.color_hex = color_hex

    suggestion_input = discord.ui.TextInput(
        label="اكتب فكرتك (لا تحط أمثلة)",
        style=discord.TextStyle.paragraph,
        placeholder="اكتب اقتراحك هنا...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        
        data = load_data()
        data["streak"] = min(20, data.get("streak", 0) + 1)
        
        # حفظ بيانات الفكرة أو إرسالها للقناة
        embed = discord.Embed(
            title=f"💡 اقتراح جديد من {interaction.user.name}",
            description=self.suggestion_input.value,
            color=self.color_hex
        )
        embed.set_footer(text=f"التصنيف: {self.color_name} | Streak: {data['streak']}")
        
        # إرسال الاقتراح في نفس القناة أو قناة مخصصة
        await interaction.channel.send(embed=embed, view=SuggestionActionView())
        save_data(data)
        
        await interaction.followup.send("✅ تم إرسال فكرتك بنجاح!", ephemeral=True)

# قائمة اختيار الألوان الـ 13
class ColorSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="اختر لون الفئة الخاصة باقتراحك...",
        min_values=1,
        max_values=1,
        custom_id="suggestion_color_select",
        options=[
            discord.SelectOption(label="أحمر", value="Red", description="اقتراحات عامة أو عاجلة", emoji="🔴"),
            discord.SelectOption(label="أزرق", value="Blue", description="تطويرات برمجية أو بوتات", emoji="🔵"),
            discord.SelectOption(label="أخضر", value="Green", description="إضافات ومميزات جديدة", emoji="🟢"),
            discord.SelectOption(label="أصفر", value="Yellow", description="تعديلات وتحسينات", emoji="🟡"),
            discord.SelectOption(label="برتقالي", value="Orange", description="فعاليات وأحداث", emoji="🟠"),
            discord.SelectOption(label="بنفسجي", value="Purple", description="تصاميم وواجهات", emoji="🟣"),
            discord.SelectOption(label="وردي", value="Pink", description="أفكار مميزة", emoji="🩷"),
            discord.SelectOption(label="أسود", value="Black", description="إلغاء أو تعديل نظام", emoji="⬛"),
            discord.SelectOption(label="أبيض", value="White", description="أفكار عامة", emoji="⬜"),
            discord.SelectOption(label="بني", value="Brown", description="قسم الرتب والأقسام", emoji="🟫"),
            discord.SelectOption(label="رمادي", value="Gray", description="أرشيف وصيانة", emoji="🩶"),
            discord.SelectOption(label="سماوي", value="Cyan", description="أوامر صوتية وتفاعلية", emoji="🌐"),
            discord.SelectOption(label="ذهبي", value="Gold", description="اقتراحات VIP خاصة", emoji="⭐"),
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        colors_map = {
            "Red": 0xFF0000, "Blue": 0x0000FF, "Green": 0x00FF00,
            "Yellow": 0xFFFF00, "Orange": 0xFFA500, "Purple": 0x800080,
            "Pink": 0xFFC0CB, "Black": 0x000000, "White": 0xFFFFFF,
            "Brown": 0xA52A2A, "Gray": 0x808080, "Cyan": 0x00FFFF,
            "Gold": 0xFFD700
        }
        selected_label = select.values[0]
        color_hex = colors_map.get(selected_label, 0x3498DB)
        await interaction.response.send_modal(SuggestionModal(color_name=selected_label, color_hex=color_hex))

# اللوحة الرئيسية (زر شارك فكرتك يفتح الألوان مباشرة)
class MainPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="شارك فكرتك", style=discord.ButtonStyle.primary, custom_id="main_share_idea_btn", emoji="💡")
    async def share_idea_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # يفتح قائمة الألوان المنسدلة مباشرة
        view = ColorSelectView()
        await interaction.response.send_message("اختر تصنيف لون فكرتك من القناة أدناه:", view=view, ephemeral=True)

# أزرار التفاعل على الاقتراح نفسه (تصويت وغيرها)
class SuggestionActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="👍 تأييد", style=discord.ButtonStyle.success, custom_id="sug_upvote_btn")
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ تم تسجيل صوتك بنجاح!", ephemeral=True)

    @discord.ui.button(label="👎 معارضة", style=discord.ButtonStyle.danger, custom_id="sug_downvote_btn")
    async def downvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ تم تسجيل صوتك بنجاح!", ephemeral=True)

class SuggestionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_suggestions", description="إرسال لوحة نظام الاقتراحات")
    async def setup_suggestions(self, interaction: discord.Interaction):
        # استجابة فورية لمنع خطأ الـ Timeout
        await interaction.response.send_message("✅ جاري إرسال لوحة الاقتراحات...", ephemeral=True)
        
        embed = discord.Embed(
            title="💡 • أفكار • IDEAS",
            description="نحن نرحب بكافة آرائك واقتراحاتك البناءة لتطوير السيرفر وجعله أفضل دائماً.\nاضغط على الزر أدناه للبدء في كتابة فكرتك واختيار لونها الخاص!",
            color=0x9B59B6
        )
        embed.set_image(url="https://cdn.phototourl.com/free/2026-09-12-34690126-831d-4c61-a227-cb0a9dde78bf.png")
        
        view = MainPanelView()
        await interaction.channel.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(SuggestionsCog(bot))
