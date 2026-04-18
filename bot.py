import asyncio
import logging
import os
import zipfile
import io
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Список расширений файлов, которые считаются текстовыми/кодовыми
TEXT_EXTENSIONS = {
    '.py', '.txt', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.yml',
    '.md', '.rst', '.c', '.cpp', '.h', '.hpp', '.java', '.kt', '.kts',
    '.swift', '.go', '.rs', '.rb', '.php', '.ts', '.jsx', '.tsx', '.vue',
    '.sql', '.sh', '.bat', '.ps1', '.dockerfile', '.gitignore', '.env',
    '.ini', '.cfg', '.conf', '.toml', '.lock', '.gradle', '.properties'
}

# Приветственное сообщение с премиум-эмодзи
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем клавиатуру с премиум-эмодзи (ReplyKeyboardMarkup)
    builder = ReplyKeyboardBuilder()
    builder.button(text="📁 Отправить ZIP", icon_custom_emoji_id="5870528606328852614")
    builder.button(text="ℹ Помощь", icon_custom_emoji_id="6028435952299413210")
    builder.adjust(2)
    
    welcome_text = (
        f"<b><tg-emoji emoji-id=\"6030400221232501136\">🤖</tg-emoji> ZIP to TXT Converter</b>\n\n"
        f"<tg-emoji emoji-id=\"5870982283724328568\">⚙</tg-emoji> <b>Как это работает:</b>\n"
        f"1. Отправь мне ZIP-файл с кодом\n"
        f"2. Я извлеку все текстовые файлы\n"
        f"3. Объединю их в один TXT-файл\n"
        f"4. Сохраню структуру папок\n\n"
        f"<tg-emoji emoji-id=\"5884479287171485878\">📦</tg-emoji> <i>Просто пришли архив!</i>"
    )
    await message.answer(welcome_text, reply_markup=builder.as_markup(resize_keyboard=True))

# Обработчик кнопки "Помощь" и команды /help
@dp.message(F.text == "ℹ Помощь")
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        f"<b><tg-emoji emoji-id=\"6028435952299413210\">ℹ</tg-emoji> Справка</b>\n\n"
        f"<tg-emoji emoji-id=\"5870528606328852614\">📁</tg-emoji> Отправь ZIP-архив с любыми файлами кода.\n\n"
        f"<b>Поддерживаемые форматы:</b>\n"
        f"Python, JavaScript, HTML, CSS, JSON, XML, YAML, Markdown, C/C++, Java, Kotlin, "
        f"Swift, Go, Rust, Ruby, PHP, TypeScript, SQL, Shell и другие.\n\n"
        f"<tg-emoji emoji-id=\"5940433880585605708\">🔨</tg-emoji> Бот извлечёт текст из всех файлов "
        f"и создаст единый TXT-документ с сохранением путей.\n\n"
        f"<tg-emoji emoji-id=\"5870930636742595124\">📊</tg-emoji> <i>Максимальный размер архива: 20 МБ</i>"
    )
    
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📁 Отправить архив",
            callback_data="send_zip_hint",
            icon_custom_emoji_id="5870528606328852614"
        )]
    ])
    await message.answer(help_text, reply_markup=inline_kb)

@dp.callback_query(F.data == "send_zip_hint")
async def hint_callback(callback: types.CallbackQuery):
    await callback.answer()
    await callback.message.answer(
        f"<tg-emoji emoji-id=\"5870528606328852614\">📁</tg-emoji> <b>Жду ZIP-файл!</b>\n"
        f"<i>Просто прикрепи и отправь архив в этот чат.</i>"
    )

# Обработчик получения ZIP-файла
@dp.message(F.document)
async def handle_zip(message: types.Message):
    document = message.document
    
    # Проверяем, что это ZIP-файл
    if not document.file_name or not document.file_name.lower().endswith('.zip'):
        await message.answer(
            f"<tg-emoji emoji-id=\"5870657884844462243\">❌</tg-emoji> "
            f"Пожалуйста, отправь файл с расширением <b>.zip</b>",
        )
        return
    
    # Проверка размера (20 МБ ограничение для ботов)
    if document.file_size > 20 * 1024 * 1024:
        await message.answer(
            f"<tg-emoji emoji-id=\"5870657884844462243\">❌</tg-emoji> "
            f"Файл слишком большой! Максимальный размер: 20 МБ.",
        )
        return
    
    # Отправляем сообщение о начале обработки
    processing_msg = await message.answer(
        f"<tg-emoji emoji-id=\"5345906554510012647\">🔄</tg-emoji> "
        f"<b>Обрабатываю архив...</b>\n"
        f"<tg-emoji emoji-id=\"5870528606328852614\">📁</tg-emoji> {document.file_name}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Отменить",
                callback_data="cancel_processing",
                icon_custom_emoji_id="5870657884844462243"
            )]
        ])
    )
    
    try:
        # Скачиваем файл в память
        file_in_io = io.BytesIO()
        await bot.download(document, destination=file_in_io)
        file_in_io.seek(0)
        
        # Создаем выходной буфер для TXT
        output_buffer = io.StringIO()
        
        # Счетчики
        processed_files = 0
        skipped_files = 0
        
        # Обрабатываем ZIP-архив
        with zipfile.ZipFile(file_in_io, 'r') as zip_ref:
            # Получаем список всех файлов в архиве
            file_list = [f for f in zip_ref.namelist() if not f.endswith('/')]
            
            output_buffer.write(f"# Содержимое архива: {document.file_name}\n")
            output_buffer.write(f"# Всего файлов в архиве: {len(file_list)}\n")
            output_buffer.write(f"# Дата обработки: {message.date.strftime('%Y-%m-%d %H:%M:%S')}\n")
            output_buffer.write("# " + "="*60 + "\n\n")
            
            for file_path in file_list:
                # Пропускаем скрытые файлы и системные папки
                if any(part.startswith('.') or part.startswith('__') and part.endswith('__') 
                       for part in Path(file_path).parts):
                    skipped_files += 1
                    continue
                
                # Проверяем расширение файла
                ext = Path(file_path).suffix.lower()
                if ext not in TEXT_EXTENSIONS:
                    skipped_files += 1
                    continue
                
                try:
                    # Читаем содержимое файла
                    with zip_ref.open(file_path) as f:
                        content = f.read()
                        
                        # Пробуем декодировать как UTF-8
                        try:
                            text_content = content.decode('utf-8')
                        except UnicodeDecodeError:
                            # Пробуем другие кодировки
                            try:
                                text_content = content.decode('cp1251')
                            except:
                                text_content = content.decode('latin-1', errors='replace')
                        
                        # Добавляем разделитель и содержимое файла
                        output_buffer.write(f"\n{'='*80}\n")
                        output_buffer.write(f"ФАЙЛ: {file_path}\n")
                        output_buffer.write(f"{'='*80}\n\n")
                        output_buffer.write(text_content)
                        output_buffer.write("\n\n")
                        
                        processed_files += 1
                        
                except Exception as e:
                    logging.warning(f"Не удалось прочитать файл {file_path}: {e}")
                    skipped_files += 1
                    continue
            
            # Добавляем итоговую информацию
            output_buffer.write(f"\n{'='*80}\n")
            output_buffer.write(f"# ИТОГИ ОБРАБОТКИ:\n")
            output_buffer.write(f"# Обработано файлов: {processed_files}\n")
            output_buffer.write(f"# Пропущено файлов: {skipped_files}\n")
            output_buffer.write(f"{'='*80}\n")
        
        # Создаем итоговый TXT-файл
        output_buffer.seek(0)
        txt_content = output_buffer.getvalue()
        
        # Создаем имя выходного файла
        base_name = Path(document.file_name).stem
        output_filename = f"{base_name}_extracted.txt"
        
        # Отправляем результат
        txt_file = io.BytesIO(txt_content.encode('utf-8'))
        txt_file.name = output_filename
        
        # Удаляем сообщение о обработке
        await processing_msg.delete()
        
        # Создаем инлайн клавиатуру для результата
        result_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📊 Статистика",
                callback_data=f"stats_{processed_files}_{skipped_files}",
                icon_custom_emoji_id="5870921681735781843"
            )],
            [InlineKeyboardButton(
                text="📁 Новый архив",
                callback_data="send_zip_hint",
                icon_custom_emoji_id="5870528606328852614"
            )]
        ])
        
        # Отправляем файл
        await message.answer_document(
            document=types.BufferedInputFile(
                file=txt_file.getvalue(),
                filename=output_filename
            ),
            caption=(
                f"<b><tg-emoji emoji-id=\"5870633910337015697\">✅</tg-emoji> Архив обработан!</b>\n\n"
                f"<tg-emoji emoji-id=\"5884479287171485878\">📦</tg-emoji> Файл: {document.file_name}\n"
                f"<tg-emoji emoji-id=\"5940433880585605708\">🔨</tg-emoji> Обработано: {processed_files} файлов\n"
                f"<tg-emoji emoji-id=\"5870657884844462243\">❌</tg-emoji> Пропущено: {skipped_files}"
            ),
            reply_markup=result_kb
        )
        
    except zipfile.BadZipFile:
        await processing_msg.delete()
        await message.answer(
            f"<tg-emoji emoji-id=\"5870657884844462243\">❌</tg-emoji> "
            f"<b>Ошибка!</b> Файл повреждён или не является ZIP-архивом.",
        )
    except Exception as e:
        logging.error(f"Ошибка при обработке архива: {e}")
        await processing_msg.delete()
        await message.answer(
            f"<tg-emoji emoji-id=\"5870657884844462243\">❌</tg-emoji> "
            f"<b>Произошла ошибка при обработке!</b>\n"
            f"<code>{str(e)[:200]}</code>",
        )

@dp.callback_query(F.data.startswith("stats_"))
async def stats_callback(callback: types.CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    processed = parts[1]
    skipped = parts[2]
    
    await callback.message.answer(
        f"<tg-emoji emoji-id=\"5870921681735781843\">📊</tg-emoji> <b>Детальная статистика:</b>\n\n"
        f"<tg-emoji emoji-id=\"5870633910337015697\">✅</tg-emoji> Обработано: {processed}\n"
        f"<tg-emoji emoji-id=\"5870657884844462243\">❌</tg-emoji> Пропущено: {skipped}\n\n"
        f"<i>Пропускаются: бинарные файлы, скрытые файлы и неподдерживаемые форматы.</i>"
    )

@dp.callback_query(F.data == "cancel_processing")
async def cancel_processing(callback: types.CallbackQuery):
    await callback.answer("Обработка прервана", show_alert=True)
    await callback.message.delete()

# Обработчик текстовых сообщений с "Отправить ZIP"
@dp.message(F.text == "📁 Отправить ZIP")
async def send_zip_hint(message: types.Message):
    await message.answer(
        f"<tg-emoji emoji-id=\"5870528606328852614\">📁</tg-emoji> <b>Отправь ZIP-файл прямо сюда!</b>\n\n"
        f"<tg-emoji emoji-id=\"6028435952299413210\">ℹ</tg-emoji> Просто прикрепи архив и отправь его в чат.\n"
        f"<i>Бот извлечёт все текстовые файлы и создаст единый TXT-документ.</i>"
    )

# Обработчик любых других сообщений
@dp.message()
async def handle_other(message: types.Message):
    await message.answer(
        f"<tg-emoji emoji-id=\"5870657884844462243\">❌</tg-emoji> "
        f"Пожалуйста, отправь <b>ZIP-файл</b> с кодом.\n\n"
        f"<tg-emoji emoji-id=\"6028435952299413210\">ℹ</tg-emoji> Используй /start или кнопку ниже:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="📁 Отправить ZIP",
                callback_data="send_zip_hint",
                icon_custom_emoji_id="5870528606328852614"
            )]
        ])
    )

async def main():
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
