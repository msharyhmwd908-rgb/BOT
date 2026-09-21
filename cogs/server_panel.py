import discord
from discord.ext import commands
from discord import app_commands


# =========================
# إعدادات
# =========================

PANEL_COLOR = discord.Color.from_rgb(100, 0, 20)


# =========================
# التحقق من صلاحيات الإدارة
# =========================

def is_admin(interaction: discord.Interaction):
    return interaction.user.guild_permissions.manage_guild


# =========================
# Modal حذف الرسائل
# =========================

class ClearMessagesModal(discord.ui.Modal, title="🧹 حذف رسائل"):

    amount = discord.ui.TextInput(
        label="عدد الرسائل",
        placeholder="مثال: 50",
        required=True,
        min_length=1,
        max_length=4
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ ما عندك صلاحية استخدام هذا النظام.",
                ephemeral=True
            )

        try:
            amount = int(self.amount.value)

            if amount < 1 or amount > 100:
                return await interaction.response.send_message(
                    "❌ اختر رقم بين 1 و 100.",
                    ephemeral=True
                )

        except ValueError:
            return await interaction.response.send_message(
                "❌ اكتب رقم صحيح.",
                ephemeral=True
            )

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ هذا الأمر يعمل داخل الرومات الكتابية فقط.",
                ephemeral=True
            )

        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await channel.purge(limit=amount)

            await interaction.followup.send(
                f"✅ تم حذف **{len(deleted)}** رسالة.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.followup.send(
                "❌ البوت ما عنده صلاحية حذف الرسائل.",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ حدث خطأ: `{e}`",
                ephemeral=True
            )


# =========================
# Modal السلو مود
# =========================

class SlowmodeModal(discord.ui.Modal, title="🐌 السلو مود"):

    seconds = discord.ui.TextInput(
        label="المدة بالثواني",
        placeholder="0 = إيقاف | مثال: 10",
        required=True,
        min_length=1,
        max_length=5
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ ما عندك صلاحية استخدام هذا النظام.",
                ephemeral=True
            )

        try:
            seconds = int(self.seconds.value)

            if seconds < 0 or seconds > 21600:
                return await interaction.response.send_message(
                    "❌ المدة لازم تكون بين 0 و 21600 ثانية.",
                    ephemeral=True
                )

        except ValueError:
            return await interaction.response.send_message(
                "❌ اكتب رقم صحيح.",
                ephemeral=True
            )

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ هذا النظام يعمل داخل الرومات الكتابية فقط.",
                ephemeral=True
            )

        try:
            await channel.edit(slowmode_delay=seconds)

            if seconds == 0:
                message = "🐌 تم **إيقاف السلو مود**."
            else:
                message = f"🐌 تم تشغيل السلو مود لمدة **{seconds} ثانية**."

            await interaction.response.send_message(
                f"✅ {message}",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ البوت ما عنده صلاحية تعديل الروم.",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ حدث خطأ: `{e}`",
                ephemeral=True
            )


# =========================
# Modal الإعلان
# =========================

class AnnouncementModal(discord.ui.Modal, title="📢 إرسال إعلان"):

    title_input = discord.ui.TextInput(
        label="عنوان الإعلان",
        placeholder="اكتب عنوان الإعلان",
        required=True,
        max_length=100
    )

    content = discord.ui.TextInput(
        label="محتوى الإعلان",
        placeholder="اكتب محتوى الإعلان هنا...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=2000
    )

    mention = discord.ui.TextInput(
        label="منشن الجميع؟",
        placeholder="نعم أو لا",
        required=True,
        max_length=3
    )

    async def on_submit(self, interaction: discord.Interaction):

        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ ما عندك صلاحية استخدام هذا النظام.",
                ephemeral=True
            )

        mention_text = self.mention.value.strip().lower()

        if mention_text not in ["نعم", "لا", "yes", "no"]:
            return await interaction.response.send_message(
                "❌ اكتب **نعم** أو **لا** في خانة المنشن.",
                ephemeral=True
            )

        use_mention = mention_text in ["نعم", "yes"]

        embed = discord.Embed(
            title=f"📢 {self.title_input.value}",
            description=self.content.value,
            color=PANEL_COLOR,
            timestamp=discord.utils.utcnow()
        )

        embed.set_footer(
            text=f"N9V・ANNOUNCEMENT • بواسطة {interaction.user.display_name}"
        )

        view = AnnouncementConfirmView(
            author_id=interaction.user.id,
            embed=embed,
            use_mention=use_mention
        )

        await interaction.response.send_message(
            "📋 **معاينة الإعلان**\n\nهل تريد إرسال الإعلان؟",
            embed=embed,
            view=view,
            ephemeral=True
        )


# =========================
# تأكيد الإعلان
# =========================

class AnnouncementConfirmView(discord.ui.View):

    def __init__(self, author_id, embed, use_mention):
        super().__init__(timeout=120)

        self.author_id = author_id
        self.embed = embed
        self.use_mention = use_mention

    @discord.ui.button(
        label="إرسال",
        emoji="📢",
        style=discord.ButtonStyle.success
    )
    async def send_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(
                "❌ هذه المعاينة ليست لك.",
                ephemeral=True
            )

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ لا يمكن إرسال الإعلان هنا.",
                ephemeral=True
            )

        try:
            await channel.send(
                content="@everyone" if self.use_mention else None,
                embed=self.embed,
                allowed_mentions=discord.AllowedMentions(
                    everyone=self.use_mention
                )
            )

            await interaction.response.edit_message(
                content="✅ تم إرسال الإعلان بنجاح.",
                embed=None,
                view=None
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ البوت ما عنده صلاحية إرسال الإعلان.",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"❌ حدث خطأ: `{e}`",
                ephemeral=True
            )

    @discord.ui.button(
        label="إلغاء",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.author_id:
            return await interaction.response.send_message(
                "❌ هذه المعاينة ليست لك.",
                ephemeral=True
            )

        await interaction.response.edit_message(
            content="❌ تم إلغاء الإعلان.",
            embed=None,
            view=None
        )


# =========================
# لوحة إدارة السيرفر
# =========================

class ServerPanelView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    # -------------------------
    # قفل الروم
    # -------------------------

    @discord.ui.button(
        label="قفل الروم",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="server_panel:lock"
    )
    async def lock_channel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ ما عندك صلاحية استخدام هذا النظام.",
                ephemeral=True
            )

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ هذا الزر يعمل داخل الرومات الكتابية فقط.",
                ephemeral=True
            )

        try:
            await channel.set_permissions(
                interaction.guild.default_role,
                send_messages=False
            )

            await interaction.response.send_message(
                "🔒 تم **قفل الروم** بنجاح.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ البوت ما عنده صلاحية تعديل صلاحيات الروم.",
                ephemeral=True
            )

    # -------------------------
    # فتح الروم
    # -------------------------

    @discord.ui.button(
        label="فتح الروم",
        emoji="🔓",
        style=discord.ButtonStyle.success,
        custom_id="server_panel:unlock"
    )
    async def unlock_channel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ ما عندك صلاحية استخدام هذا النظام.",
                ephemeral=True
            )

        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ هذا الزر يعمل داخل الرومات الكتابية فقط.",
                ephemeral=True
            )

        try:
            await channel.set_permissions(
                interaction.guild.default_role,
                send_messages=None
            )

            await interaction.response.send_message(
                "🔓 تم **فتح الروم** بنجاح.",
                ephemeral=True
            )

        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ البوت ما عنده صلاحية تعديل صلاحيات الروم.",
                ephemeral=True
            )

    # -------------------------
    # حذف رسائل
    # -------------------------

    @discord.ui.button(
        label="حذف رسائل",
        emoji="🧹",
        style=discord.ButtonStyle.secondary,
        custom_id="server_panel:clear"
    )
    async def clear_messages(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ ما عندك صلاحية استخدام هذا النظام.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            ClearMessagesModal()
        )

    # -------------------------
    # سلو مود
    # -------------------------

    @discord.ui.button(
        label="سلو مود",
        emoji="🐌",
        style=discord.ButtonStyle.secondary,
        custom_id="server_panel:slowmode"
    )
    async def slowmode(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ ما عندك صلاحية استخدام هذا النظام.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            SlowmodeModal()
        )

    # -------------------------
    # إرسال إعلان
    # -------------------------

    @discord.ui.button(
        label="إرسال إعلان",
        emoji="📢",
        style=discord.ButtonStyle.primary,
        custom_id="server_panel:announcement"
    )
    async def announcement(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ ما عندك صلاحية استخدام هذا النظام.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            AnnouncementModal()
        )


# =========================
# Cog
# =========================

class ServerPanel(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="server",
        description="فتح لوحة إدارة السيرفر"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def server_panel(
        self,
        interaction: discord.Interaction
    ):

        if not is_admin(interaction):
            return await interaction.response.send_message(
                "❌ ما عندك صلاحية استخدام لوحة إدارة السيرفر.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="🛠️ لوحة إدارة السيرفر",
            description=(
                "من هنا تقدر تتحكم بالسيرفر وتدير الرومات والرسائل "
                "بكل سهولة، كل الأدوات الأساسية للإدارة بمكان واحد."
            ),
            color=PANEL_COLOR
        )

        embed.set_footer(
            text="N9V・SERVER MANAGEMENT"
        )

        await interaction.response.send_message(
            embed=embed,
            view=ServerPanelView()
        )


# =========================
# Setup
# =========================

async def setup(bot):
    bot.add_view(ServerPanelView())
    await bot.add_cog(ServerPanel(bot))
