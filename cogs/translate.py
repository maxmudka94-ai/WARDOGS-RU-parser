import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

import config
from translator import async_translate_text

log = logging.getLogger("translate")
DISCORD_LIMIT = 1900


def _split_for_discord(text: str, limit: int = DISCORD_LIMIT) -> list[str]:
    """Split a translation into sendable chunks without splitting words."""
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit + 1)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit + 1)
        if cut < limit // 2:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        chunks.append(text)
    return chunks


def _message_text(message: discord.Message) -> str:
    parts: list[str] = []
    if message.content and message.content.strip():
        parts.append(message.content.strip())
    for emb in message.embeds:
        emb_parts: list[str] = []
        if emb.title:
            emb_parts.append(f"**{emb.title}**")
        if emb.description:
            emb_parts.append(emb.description.strip())
        for field in emb.fields:
            if field.name or field.value:
                emb_parts.append(f"**{field.name}**: {field.value}".strip())
        if emb_parts:
            parts.append("\n\n".join(emb_parts))
    return "\n\n".join(parts).strip()


def _attachment_files(message: discord.Message) -> list[discord.Attachment]:
    return list(message.attachments)[:10]


@app_commands.context_menu(name="Перевести")
async def translate_context(interaction: discord.Interaction, message: discord.Message):
    text = _message_text(message)
    if not text:
        await interaction.response.send_message("❌ Сообщение без текста.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    translated = await async_translate_text(text, config.TRANSLATE_TARGET)
    if not translated:
        await interaction.followup.send(
            "❌ Не удалось перевести. Проверь GEMINI_API_KEY и GEMINI_MODEL в .env.",
            ephemeral=True,
        )
        return

    files = _attachment_files(message)
    try:
        for index, chunk in enumerate(_split_for_discord(translated)):
            kwargs = {"ephemeral": True}
            if index == 0 and files:
                kwargs["files"] = files
            prefix = "**Перевод:**\n" if index == 0 else ""
            await interaction.followup.send(f"{prefix}{chunk}", **kwargs)
    except discord.HTTPException:
        log.exception("Не удалось отправить ручной перевод")


class TranslateCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._sent_ids: set[int] = set()
        self._sent_ts: dict[int, float] = {}
        self._processed_ids: set[int] = set()
        self._processed_ts: dict[int, float] = {}
        self._processing: set[int] = set()

    def _remember(self, msg_id: int):
        self._sent_ids.add(msg_id)
        self._sent_ts[msg_id] = time.monotonic()
        now = time.monotonic()
        stale = [mid for mid, ts in self._sent_ts.items() if now - ts > 3600]
        for mid in stale:
            self._sent_ids.discard(mid)
            self._sent_ts.pop(mid, None)

    def _remember_processed(self, msg_id: int):
        self._processed_ids.add(msg_id)
        self._processed_ts[msg_id] = time.monotonic()
        now = time.monotonic()
        stale = [mid for mid, ts in self._processed_ts.items() if now - ts > 3600]
        for mid in stale:
            self._processed_ids.discard(mid)
            self._processed_ts.pop(mid, None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Do not translate bot/webhook messages: this prevents translation loops.
        if message.author.bot:
            return
        if message.channel.id not in config.TRANSLATE_CHANNELS:
            return
        if message.id in self._sent_ids:
            return
        if message.id in self._processed_ids or message.id in self._processing:
            return

        self._processing.add(message.id)
        try:
            text = _message_text(message)
            if not text:
                return
            translated = await async_translate_text(text, config.TRANSLATE_TARGET)
            if not translated or translated.strip().lower() == text.strip().lower():
                return

            files = _attachment_files(message)
            for index, chunk in enumerate(_split_for_discord(translated)):
                kwargs = {"files": files} if index == 0 and files else {}
                sent = await message.channel.send(chunk, **kwargs)
                if sent:
                    self._remember(sent.id)
            self._remember_processed(message.id)
        except discord.HTTPException:
            log.exception("Не удалось отправить автоматический перевод")
        finally:
            self._processing.discard(message.id)


async def setup(bot: commands.Bot):
    bot.tree.add_command(translate_context)
    await bot.add_cog(TranslateCog(bot))
