import discord
from discord.ext import commands
import asyncio
import os                        # Добавили это
from dotenv import load_dotenv    # Добавили это

# Загружаем переменные из файла .env
load_dotenv()

# Теперь достаем токен из окружения
TOKEN = os.getenv('BOT_TOKEN')

GUILD_ID = 1484940293236195390  # ID твоего сервера
CATEGORY_ID = 1484944897000607917  # ID категории, где будут создаваться тикеты
ADMIN_ROLE_ID = 1484961565332471859  # ID роли админа (кто видит все тикеты)
PLAYER_ROLE_ID = 1484973955810070769  # ID роли, которая выдается после принятия

WELCOME_DM = "# Твоя заявка на SKVIPTIK одобрена.\n\nВот айпи сервера: **skviptik.sosal.today**\n**Версия:**  1.19.4 ForgeOptiFine\n**Моды:** https://drive.google.com/drive/folders/102lidbdtWsIfZ2Awx-kJPqIscBayRKrb?usp=sharing\n\nЖдем тебя в игре! 🐲"


class TicketBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(PersistentApplyView())
        print(f"✅ Бот запущен как {self.user}")


bot = TicketBot()


# --- КНОПКИ ВНУТРИ ТИКЕТА (ИСПРАВЛЕНО: ДОБАВЛЕН DEFER) ---
class TicketControlView(discord.ui.View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success, custom_id="accept_user")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1. Проверка прав (Админ или роль)
        if not interaction.user.guild_permissions.administrator and not any(
                role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ У тебя нет прав для управления заявками!", ephemeral=True)
            return

        # 2. ПРЕДОТВРАЩАЕМ ОШИБКУ 10062 (Unknown Interaction)
        await interaction.response.defer()

        # 3. Выдача роли
        role = interaction.guild.get_role(PLAYER_ROLE_ID)
        if role:
            try:
                await self.user.add_roles(role)
            except Exception as e:
                print(f"Ошибка при выдаче роли: {e}")

        # 4. Сообщение в ЛС
        try:
            await self.user.send(WELCOME_DM)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ У игрока закрыты ЛС, но роль выдана.", ephemeral=True)

        # 5. Финальный ответ в канал (через followup)
        await interaction.followup.send(
            f"✅ Заявка одобрена админом {interaction.user.mention}. Канал удалится через 5 секунд...")

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except:
            pass

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger, custom_id="reject_user")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator and not any(
                role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message("❌ У тебя нет прав для управления заявками!", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            await self.user.send("❌ К сожалению, твоя заявка на SKVIPTIK была отклонена.")
        except:
            pass

        await interaction.followup.send(f"❌ Отклонено админом {interaction.user.mention}. Удаляю канал...")

        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except:
            pass


# --- МОДАЛЬНОЕ ОКНО ---
class AppModal(discord.ui.Modal, title='Анкета на SKVIPTIK'):
    nickname = discord.ui.TextInput(label='Ник в Minecraft', placeholder='Твой ник...')
    age = discord.ui.TextInput(label='Сколько тебе лет?', placeholder='17', min_length=1, max_length=2)
    about = discord.ui.TextInput(label='Почему хочешь к нам?', style=discord.TextStyle.long,
                                 placeholder='Расскажи немного о себе...')

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        admin_role = guild.get_role(ADMIN_ROLE_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True,
                                                          read_message_history=True),
            admin_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=f"анкета-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(title="Новая заявка!", color=discord.Color.blue())
        embed.add_field(name="Кандидат", value=interaction.user.mention)
        embed.add_field(name="Ник", value=self.nickname.value)
        embed.add_field(name="Возраст", value=self.age.value)
        embed.add_field(name="О себе", value=self.about.value, inline=False)

        await channel.send(f"Привет {interaction.user.mention}! Ожидай ответа администрации.", embed=embed,
                           view=TicketControlView(interaction.user))
        await interaction.response.send_message(f"Тикет создан: {channel.mention}", ephemeral=True)


# --- ГЛАВНАЯ КНОПКА ---
class PersistentApplyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Подать заявку", style=discord.ButtonStyle.primary, custom_id="main_apply_btn", emoji="✉️")
    async def apply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AppModal())


# --- КОМАНДА ЗАПУСКА ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    embed = discord.Embed(
        title="🌿 SKVIPTIK | Набор на сервер",
        description="Нажми на кнопку ниже, чтобы заполнить анкету. Будет создан приватный тикет.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=PersistentApplyView())


bot.run(TOKEN)