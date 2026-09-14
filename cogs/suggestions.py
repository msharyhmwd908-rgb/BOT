import discord
from discord import app_commands
from discord.ext import commands
import json
import os

DATA_FILE = "suggestions_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"suggestions": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"suggestions": []}

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
        
        # إنشاء اليمبد مع منشن العضو والصورة المطلوبة وبدون ستريك
        embed = discord.Embed(
            title="💡 • اقتراح جديد",
            description=f"**صاحب الاقتراح:** {interaction.user.mention}\n**الفكرة:**\n{self.suggestion_input.value}",
        color=self.color_hex
        )
        embed.add_field(name="👍 المؤيدون (0)", value="لا يوجد حالياً", inline=False)
        embed.add_field(name="👎 المعارضون (0)", value="لا يوجد حالياً", inline=False)
        embed.set_footer(text=f"التصنيف: {self.color_name}")
        embed.set_image(url="https://b.top4top.io/p_3909j0hu80.png")
        
        # إرسال الاقتراح للقناة مع أزرار التفاعل
        await interaction.channel.send(embed=embed, view=SuggestionActionView())
        
        # إرسال رسالة تأكيد مؤقتة ثم حذفها أو إخفاؤها
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
        
        # فتح المودال وحذف رسالة اختيار اللون فوراً لتبقى الشاشة نظيفة
        await interaction.response.send_modal(SuggestionModal(color_name=selected_label, color_hex=color_hex))

# اللوحة الرئيسية
class MainPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="شارك فكرتك", style=discord.ButtonStyle.primary, custom_id="main_share_idea_btn", emoji="💡")
    async def share_idea_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ColorSelectView()
        await interaction.response.send_message("اختر تصنيف لون فكرتك من القائمة أدناه:", view=view, ephemeral=True)

# أزرار التفاعل (تأييد / معارضة) مع تحديث القوائم والمنشنات
class SuggestionActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="👍 تأييد", style=discord.ButtonStyle.success, custom_id="sug_upvote_btn")
    async def upvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        message = interaction.message
        embed = message.embeds[0]
        
        # تحديث حقل المؤيدين
        upvote_field_index = 0
        current_field = embed.fields[upvote_field_index]
        current_value = current_field.value
        
        user_mention = interaction.user.mention
        
        if "لا يوجد حالياً" in current_value:
            supporters = [user_mention]
        else:
            supporters = current_value.split("\n")
            if user_mention not in supporters:
                supporters.append(user_mention)
            else:
                supporters.remove(user_mention) # إلغاء التأييد لو ضغط مرة ثانية
                
        new_value = "\n".join(supporters) if supporters else "لا يوجد حالياً"
        embed.set_field_at(
            index=upvote_field_index,
            name=f"👍 المؤيدون ({len(supporters) if supporters and supporters[0] != 'لا يوجد حالياً' else 0})",
            value=new_value,
            inline=False
        )
        
        await message.edit(embed=embed)
        await interaction.followup.send("✅ تم تحديث تصويتك بنجاح!", ephemeral=True)

    @discord.ui.button(label="👎 معارضة", style=discord.ButtonStyle.danger, custom_id="sug_downvote_btn")
    async def downvote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        message = interaction.message
        embed = message.embeds[0]
        
        downvote_field_index = 1
        current_field = embed.fields[downvote_field_index]
        current_value = current_field.value
        
        user_mention = interaction.user.mention
        
        if "لا يوجد حالياً" in current_value:
            opposers = [user_mention]
        else:
            opposers = current_value.split("\n")
            if user_mention not in opposers:
                opposers.append(user_mention)
            else:
                opposers.remove(user_mention)
                
        new_value = "\n".join(opposers) if opposers else "لا يوجد حالياً"
        embed.set_field_at(
            index=downvote_field_index,
            name=f"👎 المعارضون ({len(opposers) if opposers and opposers[0] != 'لا يوجد حالياً' else 0})",
            value=new_value,
            inline=False
        )
        
        await message.edit(embed=embed)
        await interaction.followup.send("❌ تم تحديث تصويتك بنجاح!", ephemeral=True)

class SuggestionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_suggestions", description="إرسال لوحة نظام الاقتراحات")
    async def setup_suggestions(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ جاري إرسال لوحة الاقتراحات...", ephemeral=True)
        
        embed = discord.Embed(
            title="💡 • أفكار • IDEAS",
            description="نحن نرحب بكافة آرائك واقتراحاتك البناءة لتطوير السيرفر وجعله أفضل دائماً.\nاضغط على الزر أدناه للبدء في كتابة فكرتك واختيار لونها الخاص!",
            color=0x9B59B6
        )
        embed.set_image(url="https://b.top4top.io/p_3909j0hu80.png")
        
        view = MainPanelView()
        await interaction.channel.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(SuggestionsCog(bot))
