import discord
from discord.ext import commands
import asyncio
import datetime

# ----------------- إعدادات الـ IDs -----------------
ADMIN_ROLES = [
    1542934967711957002,
    1542934992424931378,
    1542236415469817897,
    1542236006093426698
]
TICKET_IMAGE_URL = "https://f.top4top.io/p_3904xofep0.png"

# نظام حفظ رقم التكت التسلسلي ليبقى محفوظاً حتى لو أعيد تشغيل البوت
TICKET_COUNTER_FILE = "ticket_counter.txt"

def get_next_ticket_number():
    try:
        with open(TICKET_COUNTER_FILE, "r") as f:
            num = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        num = 0
    num += 1
    with open(TICKET_COUNTER_FILE, "w") as f:
        f.write(str(num))
    return num

# ----------------- نموذج تعبئة بيانات الدعم الفني (Modal) -----------------
class SupportModal(discord.ui.Modal, title="استمارة الدعم الفني"):
    problem_title = discord.ui.TextInput(
        label="ما هي مشكلتك باختصار؟",
        placeholder="اكتب عنوان المشكلة هنا...",
        style=discord.TextStyle.short,
        required=True
    )
    problem_desc = discord.ui.TextInput(
        label="وصف المشكلة بالتفصيل",
        placeholder="اشرح مشكلتك هنا بشكل واضح...",
        style=discord.TextStyle.paragraph,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_channel(
            interaction, 
            ticket_type="دعم فني", 
            reason=f"**العنوان:** {self.problem_title.value}\n**الوصف:** {self.problem_desc.value}"
        )

# ----------------- نموذج شكوى على عضو/إداري -----------------
class ReportModal(discord.ui.Modal):
    def __init__(self, report_type: str):
        super().__init__(title=f"استمارة {report_type}")
        self.report_type = report_type
        
        self.target_user = discord.ui.TextInput(
            label="يوزر الشخص (العضو أو الإداري)",
            placeholder="مثال: user#0000 أو آيدي الشخص",
            style=discord.TextStyle.short,
            required=True
        )
        self.reason = discord.ui.TextInput(
            label="السبب والدليل",
            placeholder="اكتب السبب هنا.. (الأدلة والقرائن يتم إرسالها داخل التكت)",
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.target_user)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        reason_text = f"**المشتكى عليه:** {self.target_user.value}\n**السبب:** {self.reason.value}\n*(ملاحظة: الأدلة تُرسل داخل التكت)*"
        await create_ticket_channel(interaction, ticket_type=self.report_type, reason=reason_text)

# ----------------- قائمة منسدلة لاختيار نوع التكت (Select Menu) -----------------
class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="🛠️ دعم فني", description="لحل المشاكل العامة والاستفسارات التقنية", value="support"),
            discord.SelectOption(label="💬 استفسار", description="للاستفسارات العامة حول السيرفر أو القوانين", value="inquiry"),
            discord.SelectOption(label="⚠️ شكوى على عضو", description="الإبلاغ عن تجاوزات أو مشاكل من أعضاء", value="report_member"),
            discord.SelectOption(label="🛡️ شكوى على إداري", description="الإبلاغ عن إساءة استخدام صلاحيات من إداري", value="report_admin"),
            discord.SelectOption(label="🗺️ دعم الماب", description="المشاكل المتعلقة بماب السيرفر والدخول", value="map_support"),
        ]
        super().__init__(placeholder="📂 | اضغط هنا لاختيار نوع التكت المناسب لك...", min_values=1, max_values=1, options=options, custom_id="persistent_ticket_select")

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        if val == "support":
            await interaction.response.send_modal(SupportModal())
        elif val == "inquiry":
            await create_ticket_channel(interaction, ticket_type="استفسار", reason="استفسار عام")
        elif val == "report_member":
            await interaction.response.send_modal(ReportModal("شكوى على عضو"))
        elif val == "report_admin":
            await interaction.response.send_modal(ReportModal("شكوى على إداري"))
        elif val == "map_support":
            await create_ticket_channel(interaction, ticket_type="دعم الماب", reason="مشكلة أو استفسار بخصوص الماب")

class TicketSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # دائم لا ينتهي
        self.add_item(TicketSelect())


# ----------------- قائمة خيارات الإدارة الأخرى (Select Menu داخل التكت) -----------------
class AdminOptionsSelect(discord.ui.Select):
    def __init__(self, ticket_owner_id: int):
        self.ticket_owner_id = ticket_owner_id
        options = [
            discord.SelectOption(label="➕ إضافة شخص للتكت", description="إضافة عضو آخر للمحادثة", value="add_user"),
            discord.SelectOption(label="👑 منشن الأونر والكونر", description="منشن الإدارة العليا", value="ping_owners"),
            discord.SelectOption(label="👤 منشن صاحب التكت", description="تنبيه صاحب التذكرة", value="ping_owner"),
            discord.SelectOption(label="⭐ إرسال تقييم إداري", description="تقييم أداء الإداري المستلم", value="rate_admin"),
        ]
        super().__init__(placeholder="⚙️ | خيارات الإدارة المتقدمة...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # التحقق من صلاحيات الإدارة للخيارات المتقدمة
        if not any(r.id in ADMIN_ROLES for r in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ أنت لست مخولاً لذلك، هذا مخصص للإدارة فقط!", ephemeral=True)
            return

        val = self.values[0]
        if val == "add_user":
            await interaction.response.send_message("📌 يرجى عمل منشن للشخص الذي تريد إضافته (أو استخدام أمر السيرفر للإضافة).", ephemeral=True)
        elif val == "ping_owners":
            await interaction.response.send_message("👑 **[منشن الأونر والكونر]** - يرجى الانتباه لهذا التكت الهام!", ephemeral=False)
        elif val == "ping_owner":
            await interaction.response.send_message(f"👤 تنبيه لصاحب التكت: <@{self.ticket_owner_id}>", ephemeral=False)
        elif val == "rate_admin":
            await interaction.response.send_message("⭐ **تقييم الأداء الإداري:**\nيرجى تقييم الإداري المستلم من 1 إلى 5 نجوم وكتابة الملاحظات.", ephemeral=False)

class AdminOptionsView(discord.ui.View):
    def __init__(self, ticket_owner_id: int):
        super().__init__(timeout=None)
        self.add_item(AdminOptionsSelect(ticket_owner_id))


# ----------------- أزرار التحكم داخل التكت -----------------
class TicketControlView(discord.ui.View):
    def __init__(self, ticket_owner_id: int):
        super().__init__(timeout=None)  # دائم لا ينتهي
        self.ticket_owner_id = ticket_owner_id
        self.claimed_by = None
        self.claimed_time = "غير مستلم"
        self.closed_by = "لم يُغلق بعد"
        self.close_time = "غير مغلق"
        self.ticket_num = get_next_ticket_number()
        self.created_at_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.created_at_time = datetime.datetime.now().strftime("%H:%M:%S")

    @discord.ui.button(label="🛡️ | استلام التكت", style=discord.ButtonStyle.success, custom_id="persistent_claim_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # التحقق من أن الضاغظ إداري
        if not any(r.id in ADMIN_ROLES for r in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ أنت لست مخولاً لذلك، هذا مخصص للإدارة فقط!", ephemeral=True)
            return

        if self.claimed_by is not None:
            await interaction.response.send_message(f"⚠️ هذا التكت مستلم بالفعل بواسطة: {self.claimed_by.mention}", ephemeral=True)
            return

        self.claimed_by = interaction.user
        self.claimed_time = datetime.datetime.now().strftime("%H:%M:%S")
        button.label = "مستلم ✅"
        button.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message(f"🛡️ تم استلام التكت بنجاح بواسطة الإداري: {interaction.user.mention}", ephemeral=False)

    @discord.ui.button(label="🔒 | إغلاق التكت", style=discord.ButtonStyle.danger, custom_id="persistent_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # متاح للإدارة أو صاحب التكت
        is_admin = any(r.id in ADMIN_ROLES for r in interaction.user.roles) or interaction.user.guild_permissions.administrator
        if not is_admin and interaction.user.id != self.ticket_owner_id:
            await interaction.response.send_message("❌ أنت لست مخولاً لإغلاق هذا التكت!", ephemeral=True)
            return

        self.closed_by = interaction.user.mention
        self.close_time = datetime.datetime.now().strftime("%H:%M:%S")
        
        await interaction.response.send_message("🔒 **جاري إغلاق التكت وحفظ السجل وإرسال نسخة العضو...**", ephemeral=False)
        
        # تجهيز السجل النهائي
        summary_text = (
            "╭━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "🎫 سجل بيانات التكت\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            f"«🔖 رقم التكت:\n{self.ticket_num}»\n\n"
            f"«👤 فاتح التكت:\n<@{self.ticket_owner_id}>»\n\n"
            f"«📅 تاريخ الفتح:\n{self.created_at_date}»\n\n"
            f"«🕐 وقت الفتح:\n{self.created_at_time}»\n\n"
            f"«🛡️ الإداري المستلم:\n{self.claimed_by.mention if self.claimed_by else 'لم يتم الاستلام'}»\n\n"
            f"«⏱️ وقت الاستلام:\n{self.claimed_time}»\n\n"
            f"«🔒 حالة التكت:\nمغلق»\n\n"
            f"«🕐 وقت الإغلاق:\n{self.close_time}»\n\n"
            f"«👑 الإداري الذي أغلق التكت:\n{self.closed_by}»\n\n"
            "╭━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "📋 نهاية السجل\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━━━╯"
        )

        # إرسال نسخة للعضو في الخاص للتأمين
        try:
            owner_user = interaction.guild.get_member(self.ticket_owner_id)
            if not owner_user:
                owner_user = await self.bot.fetch_user(self.ticket_owner_id)
            
            if owner_user:
                warning_dm = (
                    "📄 **هذه نسخة أرشيفية من تكت الخاص بك الذي تم إغلاقه.**\n"
                    "لا عليك لو احد الإداريين اهانك أو سبك، في نسخة هذه معك ارسلها لكونر أو أونر ليحاسب الإداري.\n\n"
                    f"{summary_text}"
                )
                await owner_user.send(warning_dm)
        except Exception:
            pass

        await asyncio.sleep(3)
        try:
            await interaction.channel.delete()
        except:
            pass

    @discord.ui.button(label="🔔 | منشن الإدارة", style=discord.ButtonStyle.primary, custom_id="persistent_ping_admin_btn")
    async def ping_management(self, interaction: discord.Interaction, button: discord.ui.Button):
        # متاح للجميع ولكن بحد أقصى مرة لكل دقيقتين (Cooldown محلي بسيط أو عبر الذاكرة)
        current_time = datetime.datetime.now().timestamp()
        if not hasattr(self, "_last_ping"):
            self._last_ping = 0
        
        if current_time - self._last_ping < 120:
            remaining = int(120 - (current_time - self._last_ping))
            await interaction.response.send_message(f"⏳ يجب عليك الانتظار {remaining} ثانية قبل استخدام منشن الإدارة مرة أخرى.", ephemeral=True)
            return

        self._last_ping = current_time
        roles_mention = " ".join([f"<@&{r_id}>" for r_id in ADMIN_ROLES])
        await interaction.response.send_message(f"📢 **تنبيه للإدارة:** {roles_mention}\nطلب العضو انتباهكم في هذا التكت!", ephemeral=False)

    @discord.ui.button(label="⚙️ | خيارات أخرى", style=discord.ButtonStyle.secondary, custom_id="persistent_other_options_btn")
    async def other_options(self, interaction: discord.Interaction, button: discord.ui.Button):
        # مخصص للإدارة فقط
        if not any(r.id in ADMIN_ROLES for r in interaction.user.roles) and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ أنت لست مخولاً لذلك، هذا مخصص للإدارة فقط!", ephemeral=True)
            return

        # إرسال رسالة مؤقتة فيها قائمة الخيارات الإدارية المتقدمة
        await interaction.response.send_message(
            "⚙️ **قائمة خيارات الإدارة المتقدمة:**\nاختر الإجراء المناسب من القائمة أدناه:",
            view=AdminOptionsView(self.ticket_owner_id),
            ephemeral=True
        )


# ----------------- دالة إنشاء الروم البرمجية الموحدة -----------------
async def create_ticket_channel(interaction: discord.Interaction, ticket_type: str, reason: str):
    guild = interaction.guild
    member = interaction.user

    # التحقق من وجود تكت مفتوح سابقاً للعضو منعاً للتلاعب
    existing_channel = discord.utils.get(guild.text_channels, name=f"ticket-{member.name.lower()}")
    if existing_channel:
        await interaction.response.send_message(f"❌ لديك تكت مفتوح بالفعل هنا: {existing_channel.mention}", ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }

    # إضافة صلاحيات رؤية الروم لرتب الإدارة تلقائياً
    for r_id in ADMIN_ROLES:
        role_obj = guild.get_role(r_id)
        if role_obj:
            overwrites[role_obj] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

    category = interaction.channel.category
    ticket_channel = await guild.create_text_channel(
        name=f"ticket-{member.name}",
        overwrites=overwrites,
        category=category,
        topic=f"تكت {ticket_type} - صاحب التكت: {member.display_name}"
    )

    control_view = TicketControlView(ticket_owner_id=member.id)

    # السجل المزخرف داخل التكت
    summary_embed_text = (
        "╭━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "🎫 سجل بيانات التكت\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        f"«🔖 رقم التكت:\n{control_view.ticket_num}»\n\n"
        f"«📁 نوع التكت:\n{ticket_type}»\n\n"
        f"«📝 سبب فتح التكت:\n{reason}»\n\n"
        f"«👤 فاتح التكت:\n{member.mention}»\n\n"
        f"«📅 تاريخ الفتح:\n{control_view.created_at_date}»\n\n"
        f"«🕐 وقت الفتح:\n{control_view.created_at_time}»\n\n"
        f"«🛡️ الإداري المستلم:\nلم يتم الاستلام»\n\n"
        f"«⏱️ وقت الاستلام:\nغير مستلم»\n\n"
        f"«🔒 حالة التكت:\nمفتوح»\n\n"
        f"«🕐 وقت الإغلاق:\nغير مغلق»\n\n"
        f"«👑 الإداري الذي أغلق التكت:\nلم يُغلق بعد»\n\n"
        "╭━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        "📋 نهاية السجل\n"
        "╰━━━━━━━━━━━━━━━━━━━━━━━━╯"
    )

    embed = discord.Embed(
        title="🎫 تفاصيل ومعلومات التكت",
        description=summary_embed_text,
        color=discord.Color.blurple()
    )

    await ticket_channel.send(
        content=f"{member.mention} أهلاً بك في تكت الخاص بك! طاقم الإدارة سيحضر قريباً.",
        embed=embed,
        view=control_view
    )

    await interaction.response.send_message(f"✅ تم فتح تكت الخاص بك بنجاح: {ticket_channel.mention}", ephemeral=True)


# ----------------- الكوج الأساسي للتكتات -----------------
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # تسجيل الفيو الدائم لكي لا تتوقف الأزرار بعد إعادة تشغيل البوت
        self.bot.add_view(TicketSetupView())

    @discord.app_commands.command(name="ticket-setup", description="إرسال لوحة فتح التكتات الفخمة والمزخرفة")
    @commands.has_permissions(administrator=True)
    async def ticket_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎟️ مركز الدعم الفني والتذاكر",
            description=(
                "أفتح تكت لسبب المشكله حقتك بالضبط\n"
                "⚠️ **تنبيه هام:** أي استهبال = تايم أوت، الرجاء الأدب في التكت واحترام المتواجدين.\n\n"
                "اختر نوع التكت المناسب لك من القائمة المنسدلة أدناه لفتح تذكرة خاصة بك."
            ),
            color=discord.Color.from_rgb(0, 150, 255)
        )
        embed.set_image(url=TICKET_IMAGE_URL)
        
        await interaction.response.send_message(embed=embed, view=TicketSetupView())

async def setup(bot):
    await bot.add_cog(Tickets(bot))
