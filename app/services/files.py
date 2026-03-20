from aiogram import Bot


async def send_file_by_type(bot: Bot, chat_id: int, file_id: str, file_type: str, caption: str | None = None) -> None:
    if file_type == "document":
        await bot.send_document(chat_id=chat_id, document=file_id, caption=caption)
        return

    await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption)


async def send_submission_files(bot: Bot, chat_id: int, submission, submission_files) -> None:
    if submission_files:
        for file_item in submission_files:
            await send_file_by_type(
                bot=bot,
                chat_id=chat_id,
                file_id=file_item["file_id"],
                file_type=file_item["file_type"],
            )
        return

    await send_file_by_type(
        bot=bot,
        chat_id=chat_id,
        file_id=submission["file_id"],
        file_type=submission["file_type"],
    )

