import discord
from discord.ext import commands
from discord import app_commands


class AdminPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="إدارة عضو",
        emoji="👤",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_member"
    )
    async def member_control(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "👤 **إدارة عضو**\n\nاختَر العضو اللي تبي تدير أموره.",
            ephemeral=True
        )

    @discord.ui.button(
        label="العقوبات",
        emoji="🔨",
        style=discord.ButtonStyle.danger,
        custom_id="admin_punishments"
    )
    async def punishments(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔨 **العقوبات**\n\nمن هنا تقدر تتعامل مع عقوبات الأعضاء.",
            ephemeral=True
        )

    @discord.ui.button(
        label="التحذيرات",
        emoji="⚠️",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_warnings"
    )
    async def warnings(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "⚠️ **التحذيرات**\n\nمن هنا تقدر تشوف وتدير تحذيرات الأعضاء.",
            ephemeral=True
        )

    @discord.ui.button(
        label="إدارة الرتب",
        emoji="🎭",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_roles"
    )
    async def roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🎭 **إدارة الرتب**\n\nمن هنا تقدر تدير رتب الأعضاء.",
            ephemeral=True
        )

    @discord.ui.button(
        label="قفل الروم",
        emoji="🔒",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_lock"
    )
    async def lock_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔒 **قفل الروم**\n\nبيتم هنا إضافة نظام قفل الرومات.",
            ephemeral=True
        )

    @discord.ui.button(
        label="حذف رسائل",
        emoji="🧹",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_clear"
    )
    async def clear_messages(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🧹 **حذف رسائل**\n\nمن هنا تقدر تحدد عدد الرسائل اللي تبي تحذفها.",
            ephemeral=True
        )

    @discord.ui.button(
        label="Slowmode",
        emoji="🐌",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_slowmode"
    )
    async def slowmode(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🐌 **Slowmode**\n\nمن هنا تقدر تتحكم بسرعة إرسال الرسائل في الروم.",
            ephemeral=True
        )

    @discord.ui.button(
        label="إعلان",
        emoji="📢",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_announce"
    )
    async def announcement(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "📢 **الإعلانات**\n\nمن هنا تقدر تجهيز وإرسال إعلان للسيرفر.",
            ephemeral=True
        )

    @discord.ui.button(
        label="سجل الإدارة",
        emoji="📜",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_logs"
    )
    async def logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "📜 **سجل الإدارة**\n\nهنا بتلقى كل العمليات الإدارية المسجلة.",
            ephemeral=True
        )

    @discord.ui.button(
        label="إحصائيات الإدارة",
        emoji="📊",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_stats"
    )
    async def statistics(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "📊 **إحصائيات الإدارة**\n\nهنا بتظهر إحصائيات عمليات الإدارة.",
            ephemeral=True
        )

    @discord.ui.button(
        label="البحث عن عملية",
        emoji="🔎",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_search"
    )
    async def search_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🔎 **البحث عن عملية**\n\nابحث عن أي عملية إدارية مسجلة.",
            ephemeral=True
        )

    @discord.ui.button(
        label="ملاحظات الإدارة",
        emoji="📝",
        style=discord.ButtonStyle.secondary,
        custom_id="admin_notes"
    )
    async def notes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "📝 **ملاحظات الإدارة**\n\nمن هنا تقدر تضيف ملاحظات خاصة بالإدارة.",
            ephemeral=True
        )

    @discord.ui.button(
        label="صلاحيات الإدارة",
        emoji="🛡️",
        style=discord.ButtonStyle.primary,
        custom_id="admin_permissions"
    )
    async def permissions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🛡️ **صلاحيات الإدارة**\n\nمن هنا بنحدد مين يقدر يستخدم كل ميزة.",
            ephemeral=True
        )

    @discord.ui.button(
        label="تحديث اللوحة",
        emoji="🔄",
        style=discord.ButtonStyle.success,
        custom_id="admin_refresh"
    )
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            embed=create_admin_embed(),
            view=AdminPanelView()
        )


def create_admin_embed():
    embed = discord.Embed(
        title="🛡️ لوحة الإدارة",
        description=(
            "هذي لوحة الإدارة، من هنا تقدر تدير أمور السيرفر كلها "
            "بمكان واحد، وتتابع شغل الإدارة والعمليات اللي تصير أول بأول."
        ),
        color=discord.Color.from_rgb(100, 0, 20)
    )

    embed.add_field(
        name="👥 الأعضاء",
        value="إدارة الأعضاء والعقوبات والتحذيرات والرتب.",
        inline=False
    )

    embed.add_field(
        name="🛠️ إدارة السيرفر",
        value="تحكم بالرومات والرسائل والإعلانات والـSlowmode.",
        inline=False
    )

    embed.add_field(
        name="📋 المتابعة",
        value="تابع سجل الإدارة والإحصائيات والعمليات.",
        inline=False
    )

    embed.add_field(
        name="⚙️ النظام",
        value="تحكم بصلاحيات الإدارة وإعدادات اللوحة.",
        inline=False
    )

    embed.set_footer(text="N9V・ADMIN CENTER")

    return embed


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="admin",
        description="فتح لوحة الإدارة"
    )
    @app_commands.default_permissions(administrator=True)
    async def admin(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ ما عندك صلاحية تستخدم لوحة الإدارة.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=create_admin_embed(),
            view=AdminPanelView()
        )


async def setup(bot: commands.Bot):
    bot.add_view(AdminPanelView())
    await bot.add_cog(Admin(bot))
