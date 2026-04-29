import asyncio
import logging
import os
import tempfile
import zipfile
import io
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.methods import DeleteWebhook
from aiogram.types import FSInputFile
from PyPDF2 import PdfReader
from docx import Document
from PIL import Image
import pandas as pd

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ Необходимо установить переменную окружения BOT_TOKEN")

# ID администратора
ADMIN_IDS = [7973988177]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временная папка для конвертации
TEMP_DIR = Path("temp_conversions")
TEMP_DIR.mkdir(exist_ok=True)


# Функции конвертации
async def convert_pdf_to_txt(pdf_path: str) -> str:
    """Конвертирует PDF в TXT"""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    
    txt_path = pdf_path.replace('.pdf', '_converted.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    return txt_path


async def convert_pdf_to_docx(pdf_path: str) -> str:
    """Конвертирует PDF в DOCX"""
    reader = PdfReader(pdf_path)
    doc = Document()
    
    for page in reader.pages:
        doc.add_paragraph(page.extract_text())
    
    docx_path = pdf_path.replace('.pdf', '_converted.docx')
    doc.save(docx_path)
    return docx_path


async def convert_txt_to_pdf(txt_path: str) -> str:
    """Конвертирует TXT в PDF"""
    from reportlab.pdfgen import canvas
    
    pdf_path = txt_path.replace('.txt', '_converted.pdf')
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    c = canvas.Canvas(pdf_path)
    y = 800
    for line in text.split('\n'):
        if y < 50:
            c.showPage()
            y = 800
        c.drawString(50, y, line[:100])
        y -= 15
    
    c.save()
    return pdf_path


async def extract_zip_to_files(zip_path: str) -> list:
    """Извлекает ZIP архив и возвращает список файлов"""
    extract_dir = zip_path.replace('.zip', '_extracted')
    os.makedirs(extract_dir, exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    files = []
    for root, dirs, filenames in os.walk(extract_dir):
        for filename in filenames:
            files.append(os.path.join(root, filename))
    
    return files


async def create_zip_from_files(file_paths: list, output_path: str) -> str:
    """Создает ZIP архив из списка файлов"""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in file_paths:
            zipf.write(file_path, os.path.basename(file_path))
    return output_path


async def convert_image_to_pdf(image_path: str) -> str:
    """Конвертирует изображение в PDF"""
    pdf_path = image_path.rsplit('.', 1)[0] + '_converted.pdf'
    
    image = Image.open(image_path)
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    
    image.save(pdf_path, 'PDF')
    return pdf_path


async def convert_excel_to_csv(excel_path: str) -> str:
    """Конвертирует Excel в CSV"""
    df = pd.read_excel(excel_path)
    csv_path = excel_path.rsplit('.', 1)[0] + '_converted.csv'
    df.to_csv(csv_path, index=False, encoding='utf-8')
    return csv_path


# Клавиатуры
def get_main_menu():
    """Главное меню с премиум эмодзи через icon"""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(
                    text="PDF → TXT",
                    icon_custom_emoji_id="5870528606328852614"
                ),
                types.KeyboardButton(
                    text="PDF → DOCX",
                    icon_custom_emoji_id="5870528606328852614"
                )
            ],
            [
                types.KeyboardButton(
                    text="TXT → PDF",
                    icon_custom_emoji_id="5870528606328852614"
                ),
                types.KeyboardButton(
                    text="ZIP → Извлечь",
                    icon_custom_emoji_id="5884479287171485878"
                )
            ],
            [
                types.KeyboardButton(
                    text="Создать ZIP",
                    icon_custom_emoji_id="5884479287171485878"
                ),
                types.KeyboardButton(
                    text="Изображение → PDF",
                    icon_custom_emoji_id="6035128606563241721"
                )
            ],
            [
                types.KeyboardButton(
                    text="Excel → CSV",
                    icon_custom_emoji_id="5870930636742595124"
                ),
                types.KeyboardButton(
                    text="О боте",
                    icon_custom_emoji_id="6028435952299413210"
                )
            ]
        ],
        resize_keyboard=True
    )


def get_back_button():
    """Кнопка назад"""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(
                    text="◁ Назад",
                    icon_custom_emoji_id="5345906554510012647"
                )
            ]
        ],
        resize_keyboard=True
    )


def get_inline_menu():
    """Инлайн меню с цветными кнопками"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='6028435952299413210'>ℹ</tg-emoji> Информация",
            callback_data="info",
            style="primary",
            icon_custom_emoji_id="6028435952299413210"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='6030400221232501136'>🤖</tg-emoji> Поддержка",
            callback_data="support",
            style="success",
            icon_custom_emoji_id="6030400221232501136"
        ),
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870875489362513438'>🗑</tg-emoji> Очистить",
            callback_data="clear",
            style="danger",
            icon_custom_emoji_id="5870875489362513438"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Настройки",
            callback_data="settings",
            style="default",
            icon_custom_emoji_id="5870982283724328568"
        ),
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='6041731551845159060'>🎉</tg-emoji> Премиум",
            callback_data="premium",
            style="primary",
            icon_custom_emoji_id="6041731551845159060"
        )
    )
    
    return builder.as_markup()


# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    welcome_text = (
        "<b><tg-emoji emoji-id='6041731551845159060'>🎉</tg-emoji> Добро пожаловать в File Converter Bot!</b>\n\n"
        "<tg-emoji emoji-id='6030400221232501136'>🤖</tg-emoji> Я могу конвертировать файлы различных форматов:\n"
        "<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> PDF → TXT\n"
        "<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> PDF → DOCX\n"
        "<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> TXT → PDF\n"
        "<tg-emoji emoji-id='5884479287171485878'>📦</tg-emoji> ZIP → Извлечь\n"
        "<tg-emoji emoji-id='5884479287171485878'>📦</tg-emoji> Создать ZIP\n"
        "<tg-emoji emoji-id='6035128606563241721'>🖼</tg-emoji> Изображение → PDF\n"
        "<tg-emoji emoji-id='5870930636742595124'>📊</tg-emoji> Excel → CSV\n\n"
        "<tg-emoji emoji-id='6028435952299413210'>ℹ</tg-emoji> Выберите действие из меню ниже или отправьте файл для конвертации!"
    )
    
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )


@dp.message(F.text == "О боте")
@dp.message(Command("about"))
async def cmd_about(message: types.Message):
    """Информация о боте"""
    about_text = (
        "<b><tg-emoji emoji-id='6030400221232501136'>🤖</tg-emoji> File Converter Bot</b>\n\n"
        "<tg-emoji emoji-id='6028435952299413210'>ℹ</tg-emoji> <b>Версия:</b> 1.0.0\n"
        "<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> <b>Функции:</b>\n"
        "<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> Конвертация PDF в TXT/DOCX\n"
        "<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> Конвертация TXT в PDF\n"
        "<tg-emoji emoji-id='5884479287171485878'>📦</tg-emoji> Работа с ZIP архивами\n"
        "<tg-emoji emoji-id='6035128606563241721'>🖼</tg-emoji> Конвертация изображений в PDF\n"
        "<tg-emoji emoji-id='5870930636742595124'>📊</tg-emoji> Экспорт Excel в CSV\n\n"
        "<tg-emoji emoji-id='5963103826075456248'>⬆</tg-emoji> Просто отправьте файл и выберите формат конвертации!"
    )
    
    await message.answer(
        about_text,
        parse_mode="HTML",
        reply_markup=get_inline_menu()
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Помощь"""
    help_text = (
        "<b><tg-emoji emoji-id='6028435952299413210'>ℹ</tg-emoji> Как использовать бота:</b>\n\n"
        "<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> <b>Конвертация PDF:</b>\n"
        "1. Отправьте PDF файл\n"
        "2. Выберите в меню PDF → TXT или PDF → DOCX\n"
        "3. Получите конвертированный файл\n\n"
        "<tg-emoji emoji-id='5884479287171485878'>📦</tg-emoji> <b>Работа с ZIP:</b>\n"
        "1. Для извлечения: отправьте ZIP файл и выберите ZIP → Извлечь\n"
        "2. Для создания: отправьте несколько файлов и выберите Создать ZIP\n\n"
        "<tg-emoji emoji-id='6035128606563241721'>🖼</tg-emoji> <b>Изображение → PDF:</b>\n"
        "1. Отправьте изображение (PNG, JPG)\n"
        "2. Выберите Изображение → PDF\n\n"
        "<tg-emoji emoji-id='5870930636742595124'>📊</tg-emoji> <b>Excel → CSV:</b>\n"
        "1. Отправьте Excel файл\n"
        "2. Выберите Excel → CSV"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Главное меню",
            callback_data="main_menu",
            style="primary",
            icon_custom_emoji_id="5870982283724328568"
        )
    )
    
    await message.answer(
        help_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


@dp.message(F.text == "◁ Назад")
@dp.message(Command("menu"))
async def cmd_main_menu(message: types.Message):
    """Возврат в главное меню"""
    await message.answer(
        "<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> <b>Главное меню</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )


# Обработчики файлов
@dp.message(F.document)
async def handle_file(message: types.Message):
    """Обработчик входящих документов"""
    document = message.document
    file_name = document.file_name
    
    # Определяем тип файла
    if file_name.lower().endswith('.pdf'):
        await handle_pdf(message)
    elif file_name.lower().endswith('.txt'):
        await handle_txt(message)
    elif file_name.lower().endswith('.zip'):
        await handle_zip(message)
    elif file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
        await handle_image(message)
    elif file_name.lower().endswith(('.xlsx', '.xls')):
        await handle_excel(message)
    else:
        await message.answer(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> <b>Неподдерживаемый формат файла</b>\n\n"
            "<tg-emoji emoji-id='6028435952299413210'>ℹ</tg-emoji> Поддерживаемые форматы: PDF, TXT, ZIP, изображения, Excel",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )


async def handle_pdf(message: types.Message):
    """Обработка PDF файлов"""
    processing_msg = await message.answer(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Обработка PDF файла...</b>",
        parse_mode="HTML"
    )
    
    # Скачиваем файл
    file = await bot.get_file(message.document.file_id)
    file_path = TEMP_DIR / message.document.file_name
    await bot.download_file(file.file_path, file_path)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> Конвертировать в TXT",
            callback_data=f"convert_pdf_txt_{message.document.file_name}",
            style="success",
            icon_custom_emoji_id="5870528606328852614"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> Конвертировать в DOCX",
            callback_data=f"convert_pdf_docx_{message.document.file_name}",
            style="primary",
            icon_custom_emoji_id="5870528606328852614"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Отмена",
            callback_data="cancel",
            style="danger",
            icon_custom_emoji_id="5870657884844462243"
        )
    )
    
    await processing_msg.edit_text(
        "<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> <b>PDF файл загружен!</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Выберите формат конвертации:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


async def handle_txt(message: types.Message):
    """Обработка TXT файлов"""
    processing_msg = await message.answer(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Обработка TXT файла...</b>",
        parse_mode="HTML"
    )
    
    file = await bot.get_file(message.document.file_id)
    file_path = TEMP_DIR / message.document.file_name
    await bot.download_file(file.file_path, file_path)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> Конвертировать в PDF",
            callback_data=f"convert_txt_pdf_{message.document.file_name}",
            style="success",
            icon_custom_emoji_id="5870528606328852614"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Отмена",
            callback_data="cancel",
            style="danger",
            icon_custom_emoji_id="5870657884844462243"
        )
    )
    
    await processing_msg.edit_text(
        "<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> <b>TXT файл загружен!</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Выберите формат конвертации:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


async def handle_zip(message: types.Message):
    """Обработка ZIP файлов"""
    processing_msg = await message.answer(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Обработка ZIP файла...</b>",
        parse_mode="HTML"
    )
    
    file = await bot.get_file(message.document.file_id)
    file_path = TEMP_DIR / message.document.file_name
    await bot.download_file(file.file_path, file_path)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5884479287171485878'>📦</tg-emoji> Извлечь все файлы",
            callback_data=f"extract_zip_{message.document.file_name}",
            style="success",
            icon_custom_emoji_id="5884479287171485878"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Отмена",
            callback_data="cancel",
            style="danger",
            icon_custom_emoji_id="5870657884844462243"
        )
    )
    
    await processing_msg.edit_text(
        "<tg-emoji emoji-id='5884479287171485878'>📦</tg-emoji> <b>ZIP файл загружен!</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Выберите действие:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


async def handle_image(message: types.Message):
    """Обработка изображений"""
    processing_msg = await message.answer(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Обработка изображения...</b>",
        parse_mode="HTML"
    )
    
    file = await bot.get_file(message.document.file_id)
    file_path = TEMP_DIR / message.document.file_name
    await bot.download_file(file.file_path, file_path)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='6035128606563241721'>🖼</tg-emoji> Конвертировать в PDF",
            callback_data=f"convert_img_pdf_{message.document.file_name}",
            style="success",
            icon_custom_emoji_id="6035128606563241721"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Отмена",
            callback_data="cancel",
            style="danger",
            icon_custom_emoji_id="5870657884844462243"
        )
    )
    
    await processing_msg.edit_text(
        "<tg-emoji emoji-id='6035128606563241721'>🖼</tg-emoji> <b>Изображение загружено!</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Выберите действие:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


async def handle_excel(message: types.Message):
    """Обработка Excel файлов"""
    processing_msg = await message.answer(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Обработка Excel файла...</b>",
        parse_mode="HTML"
    )
    
    file = await bot.get_file(message.document.file_id)
    file_path = TEMP_DIR / message.document.file_name
    await bot.download_file(file.file_path, file_path)
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870930636742595124'>📊</tg-emoji> Конвертировать в CSV",
            callback_data=f"convert_excel_csv_{message.document.file_name}",
            style="success",
            icon_custom_emoji_id="5870930636742595124"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Отмена",
            callback_data="cancel",
            style="danger",
            icon_custom_emoji_id="5870657884844462243"
        )
    )
    
    await processing_msg.edit_text(
        "<tg-emoji emoji-id='5870930636742595124'>📊</tg-emoji> <b>Excel файл загружен!</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Выберите действие:",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )


# Callback обработчики
@dp.callback_query(F.data == "cancel")
async def cancel_callback(callback: types.CallbackQuery):
    """Отмена действия"""
    await callback.message.edit_text(
        "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> <b>Действие отменено</b>",
        parse_mode="HTML"
    )
    await callback.answer(
        "<tg-emoji emoji-id='5870875489362513438'>🗑</tg-emoji> Отменено",
        show_alert=False
    )


@dp.callback_query(F.data.startswith("convert_pdf_txt_"))
async def convert_pdf_to_txt_callback(callback: types.CallbackQuery):
    """Конвертация PDF в TXT"""
    file_name = callback.data.replace("convert_pdf_txt_", "")
    file_path = TEMP_DIR / file_name
    
    await callback.message.edit_text(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Конвертирую PDF в TXT...</b>",
        parse_mode="HTML"
    )
    
    try:
        converted_path = await convert_pdf_to_txt(str(file_path))
        input_file = FSInputFile(converted_path)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(
                text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Главное меню",
                callback_data="main_menu",
                style="primary",
                icon_custom_emoji_id="5870982283724328568"
            )
        )
        
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> <b>Конвертация завершена!</b>\n"
            "<tg-emoji emoji-id='6039802767931871481'>⬇</tg-emoji> Ваш TXT файл готов:",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
        await callback.message.answer_document(
            document=input_file,
            caption="<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> Конвертированный файл",
            parse_mode="HTML"
        )
        
        await callback.answer(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> Готово!",
            show_alert=False
        )
        
        # Очистка временных файлов
        os.remove(file_path)
        os.remove(converted_path)
        
    except Exception as e:
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> <b>Ошибка конвертации:</b>\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )
        await callback.answer(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Ошибка!",
            show_alert=True
        )


@dp.callback_query(F.data.startswith("convert_pdf_docx_"))
async def convert_pdf_to_docx_callback(callback: types.CallbackQuery):
    """Конвертация PDF в DOCX"""
    file_name = callback.data.replace("convert_pdf_docx_", "")
    file_path = TEMP_DIR / file_name
    
    await callback.message.edit_text(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Конвертирую PDF в DOCX...</b>",
        parse_mode="HTML"
    )
    
    try:
        converted_path = await convert_pdf_to_docx(str(file_path))
        input_file = FSInputFile(converted_path)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(
                text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Главное меню",
                callback_data="main_menu",
                style="primary",
                icon_custom_emoji_id="5870982283724328568"
            )
        )
        
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> <b>Конвертация завершена!</b>\n"
            "<tg-emoji emoji-id='6039802767931871481'>⬇</tg-emoji> Ваш DOCX файл готов:",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
        await callback.message.answer_document(
            document=input_file,
            caption="<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> Конвертированный файл",
            parse_mode="HTML"
        )
        
        await callback.answer(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> Готово!",
            show_alert=False
        )
        
        # Очистка временных файлов
        os.remove(file_path)
        os.remove(converted_path)
        
    except Exception as e:
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> <b>Ошибка конвертации:</b>\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )
        await callback.answer(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Ошибка!",
            show_alert=True
        )


@dp.callback_query(F.data.startswith("convert_txt_pdf_"))
async def convert_txt_to_pdf_callback(callback: types.CallbackQuery):
    """Конвертация TXT в PDF"""
    file_name = callback.data.replace("convert_txt_pdf_", "")
    file_path = TEMP_DIR / file_name
    
    await callback.message.edit_text(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Конвертирую TXT в PDF...</b>",
        parse_mode="HTML"
    )
    
    try:
        converted_path = await convert_txt_to_pdf(str(file_path))
        input_file = FSInputFile(converted_path)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(
                text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Главное меню",
                callback_data="main_menu",
                style="primary",
                icon_custom_emoji_id="5870982283724328568"
            )
        )
        
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> <b>Конвертация завершена!</b>\n"
            "<tg-emoji emoji-id='6039802767931871481'>⬇</tg-emoji> Ваш PDF файл готов:",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
        await callback.message.answer_document(
            document=input_file,
            caption="<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> Конвертированный файл",
            parse_mode="HTML"
        )
        
        await callback.answer(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> Готово!",
            show_alert=False
        )
        
        # Очистка временных файлов
        os.remove(file_path)
        os.remove(converted_path)
        
    except Exception as e:
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> <b>Ошибка конвертации:</b>\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )
        await callback.answer(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Ошибка!",
            show_alert=True
        )


@dp.callback_query(F.data.startswith("extract_zip_"))
async def extract_zip_callback(callback: types.CallbackQuery):
    """Извлечение ZIP архива"""
    file_name = callback.data.replace("extract_zip_", "")
    file_path = TEMP_DIR / file_name
    
    await callback.message.edit_text(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Извлекаю файлы из ZIP...</b>",
        parse_mode="HTML"
    )
    
    try:
        extracted_files = await extract_zip_to_files(str(file_path))
        
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(
                text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Главное меню",
                callback_data="main_menu",
                style="primary",
                icon_custom_emoji_id="5870982283724328568"
            )
        )
        
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> <b>Архив извлечен!</b>\n"
            f"<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> Количество файлов: {len(extracted_files)}\n"
            "<tg-emoji emoji-id='6039802767931871481'>⬇</tg-emoji> Файлы отправляются...",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
        # Отправляем извлеченные файлы
        for file_path in extracted_files:
            if os.path.getsize(file_path) < 50 * 1024 * 1024:  # Лимит 50MB
                input_file = FSInputFile(file_path)
                await callback.message.answer_document(
                    document=input_file,
                    caption=f"<tg-emoji emoji-id='5870528606328852614'>📁</tg-emoji> {os.path.basename(file_path)}",
                    parse_mode="HTML"
                )
        
        await callback.answer(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> Файлы извлечены!",
            show_alert=False
        )
        
        # Очистка временных файлов
        os.remove(file_path)
        
    except Exception as e:
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> <b>Ошибка извлечения:</b>\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )
        await callback.answer(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Ошибка!",
            show_alert=True
        )


@dp.callback_query(F.data.startswith("convert_img_pdf_"))
async def convert_image_to_pdf_callback(callback: types.CallbackQuery):
    """Конвертация изображения в PDF"""
    file_name = callback.data.replace("convert_img_pdf_", "")
    file_path = TEMP_DIR / file_name
    
    await callback.message.edit_text(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Конвертирую изображение в PDF...</b>",
        parse_mode="HTML"
    )
    
    try:
        converted_path = await convert_image_to_pdf(str(file_path))
        input_file = FSInputFile(converted_path)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(
                text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Главное меню",
                callback_data="main_menu",
                style="primary",
                icon_custom_emoji_id="5870982283724328568"
            )
        )
        
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> <b>Конвертация завершена!</b>\n"
            "<tg-emoji emoji-id='6039802767931871481'>⬇</tg-emoji> Ваш PDF файл готов:",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
        await callback.message.answer_document(
            document=input_file,
            caption="<tg-emoji emoji-id='6035128606563241721'>🖼</tg-emoji> Изображение в PDF",
            parse_mode="HTML"
        )
        
        await callback.answer(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> Готово!",
            show_alert=False
        )
        
        # Очистка временных файлов
        os.remove(file_path)
        os.remove(converted_path)
        
    except Exception as e:
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> <b>Ошибка конвертации:</b>\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )
        await callback.answer(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Ошибка!",
            show_alert=True
        )


@dp.callback_query(F.data.startswith("convert_excel_csv_"))
async def convert_excel_to_csv_callback(callback: types.CallbackQuery):
    """Конвертация Excel в CSV"""
    file_name = callback.data.replace("convert_excel_csv_", "")
    file_path = TEMP_DIR / file_name
    
    await callback.message.edit_text(
        "<tg-emoji emoji-id='5345906554510012647'>🔄</tg-emoji> <b>Конвертирую Excel в CSV...</b>",
        parse_mode="HTML"
    )
    
    try:
        converted_path = await convert_excel_to_csv(str(file_path))
        input_file = FSInputFile(converted_path)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(
                text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Главное меню",
                callback_data="main_menu",
                style="primary",
                icon_custom_emoji_id="5870982283724328568"
            )
        )
        
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> <b>Конвертация завершена!</b>\n"
            "<tg-emoji emoji-id='6039802767931871481'>⬇</tg-emoji> Ваш CSV файл готов:",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
        
        await callback.message.answer_document(
            document=input_file,
            caption="<tg-emoji emoji-id='5870930636742595124'>📊</tg-emoji> Данные в CSV формате",
            parse_mode="HTML"
        )
        
        await callback.answer(
            "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> Готово!",
            show_alert=False
        )
        
        # Очистка временных файлов
        os.remove(file_path)
        os.remove(converted_path)
        
    except Exception as e:
        await callback.message.edit_text(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> <b>Ошибка конвертации:</b>\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )
        await callback.answer(
            "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Ошибка!",
            show_alert=True
        )


@dp.callback_query(F.data == "info")
async def info_callback(callback: types.CallbackQuery):
    """Информация о боте"""
    info_text = (
        "<b><tg-emoji emoji-id='6030400221232501136'>🤖</tg-emoji> File Converter Bot v1.0.0</b>\n\n"
        "<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> <b>Разработчик:</b> @admin\n"
        "<tg-emoji emoji-id='6028435952299413210'>ℹ</tg-emoji> <b>Возможности:</b>\n"
        "- Конвертация PDF ↔ TXT/DOCX\n"
        "- Работа с ZIP архивами\n"
        "- Конвертация изображений в PDF\n"
        "- Экспорт Excel в CSV\n"
        "- Поддержка drag & drop файлов\n"
        "- Временные файлы автоматически удаляются\n\n"
        "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> <b>Премиум эмодзи</b> используются во всех сообщениях"
    )
    
    await callback.message.edit_text(
        info_text,
        parse_mode="HTML",
        reply_markup=get_inline_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "support")
async def support_callback(callback: types.CallbackQuery):
    """Поддержка"""
    support_text = (
        "<tg-emoji emoji-id='6030400221232501136'>🤖</tg-emoji> <b>Поддержка</b>\n\n"
        "<tg-emoji emoji-id='5870657884844462243'>❌</tg-emoji> Возникли проблемы?\n"
        "<tg-emoji emoji-id='6028435952299413210'>ℹ</tg-emoji> Напишите администратору\n\n"
        "<tg-emoji emoji-id='5940433880585605708'>🔨</tg-emoji> Бот всегда обновляется и улучшается!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Назад в меню",
            callback_data="main_menu",
            style="primary",
            icon_custom_emoji_id="5870982283724328568"
        )
    )
    
    await callback.message.edit_text(
        support_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data == "clear")
async def clear_callback(callback: types.CallbackQuery):
    """Очистка сообщения"""
    await callback.message.delete()
    await callback.answer(
        "<tg-emoji emoji-id='5870875489362513438'>🗑</tg-emoji> Очищено",
        show_alert=False
    )


@dp.callback_query(F.data == "settings")
async def settings_callback(callback: types.CallbackQuery):
    """Настройки"""
    settings_text = (
        "<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> <b>Настройки</b>\n\n"
        "<tg-emoji emoji-id='6028435952299413210'>ℹ</tg-emoji> Версия бота: 1.0.0\n"
        "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> Статус: Активен"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Назад в меню",
            callback_data="main_menu",
            style="primary",
            icon_custom_emoji_id="5870982283724328568"
        )
    )
    
    await callback.message.edit_text(
        settings_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data == "premium")
async def premium_callback(callback: types.CallbackQuery):
    """Премиум возможности"""
    premium_text = (
        "<tg-emoji emoji-id='6041731551845159060'>🎉</tg-emoji> <b>Премиум возможности</b>\n\n"
        "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> Все функции уже доступны бесплатно!\n"
        "<tg-emoji emoji-id='6030400221232501136'>🤖</tg-emoji> Бот использует премиум эмодзи\n"
        "<tg-emoji emoji-id='5963103826075456248'>⬆</tg-emoji> Максимальное качество конвертации"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Назад в меню",
            callback_data="main_menu",
            style="primary",
            icon_custom_emoji_id="5870982283724328568"
        )
    )
    
    await callback.message.edit_text(
        premium_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.delete()
    await callback.message.answer(
        "<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> <b>Главное меню</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
    await callback.answer(
        "<tg-emoji emoji-id='5870633910337015697'>✅</tg-emoji> Меню обновлено",
        show_alert=False
    )


# Обработчик текстовых команд из меню
@dp.message(F.text == "PDF → TXT")
async def menu_convert_pdf_txt(message: types.Message):
    """Меню: PDF в TXT"""
    await message.answer(
        "<tg-emoji emoji-id='5963103826075456248'>⬆</tg-emoji> <b>Отправьте PDF файл</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Я конвертирую его в TXT формат",
        parse_mode="HTML"
    )


@dp.message(F.text == "PDF → DOCX")
async def menu_convert_pdf_docx(message: types.Message):
    """Меню: PDF в DOCX"""
    await message.answer(
        "<tg-emoji emoji-id='5963103826075456248'>⬆</tg-emoji> <b>Отправьте PDF файл</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Я конвертирую его в DOCX формат",
        parse_mode="HTML"
    )


@dp.message(F.text == "TXT → PDF")
async def menu_convert_txt_pdf(message: types.Message):
    """Меню: TXT в PDF"""
    await message.answer(
        "<tg-emoji emoji-id='5963103826075456248'>⬆</tg-emoji> <b>Отправьте TXT файл</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Я конвертирую его в PDF формат",
        parse_mode="HTML"
    )


@dp.message(F.text == "ZIP → Извлечь")
async def menu_unzip(message: types.Message):
    """Меню: Извлечь ZIP"""
    await message.answer(
        "<tg-emoji emoji-id='5963103826075456248'>⬆</tg-emoji> <b>Отправьте ZIP архив</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Я извлеку все файлы из архива",
        parse_mode="HTML"
    )


@dp.message(F.text == "Создать ZIP")
async def menu_create_zip(message: types.Message):
    """Меню: Создать ZIP"""
    await message.answer(
        "<tg-emoji emoji-id='5963103826075456248'>⬆</tg-emoji> <b>Отправьте несколько файлов</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Я создам ZIP архив (в разработке)",
        parse_mode="HTML"
    )


@dp.message(F.text == "Изображение → PDF")
async def menu_image_pdf(message: types.Message):
    """Меню: Изображение в PDF"""
    await message.answer(
        "<tg-emoji emoji-id='5963103826075456248'>⬆</tg-emoji> <b>Отправьте изображение</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Я конвертирую его в PDF формат",
        parse_mode="HTML"
    )


@dp.message(F.text == "Excel → CSV")
async def menu_excel_csv(message: types.Message):
    """Меню: Excel в CSV"""
    await message.answer(
        "<tg-emoji emoji-id='5963103826075456248'>⬆</tg-emoji> <b>Отправьте Excel файл</b>\n"
        "<tg-emoji emoji-id='5893057118545646106'>📰</tg-emoji> Я конвертирую его в CSV формат",
        parse_mode="HTML"
    )


# Requirements check
async def check_requirements():
    """Проверка установленных пакетов"""
    required_packages = [
        'PyPDF2',
        'python-docx',
        'Pillow',
        'openpyxl',
        'pandas',
        'reportlab'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print("Установка необходимых пакетов...")
        import subprocess
        for package in missing:
            subprocess.check_call(['pip', 'install', package])


# Запуск бота
async def main():
    await check_requirements()
    
    print("<tg-emoji emoji-id='6030400221232501136'>🤖</tg-emoji> File Converter Bot запущен!")
    print(f"<tg-emoji emoji-id='6028435952299413210'>ℹ</tg-emoji> Токен из переменной BOT_TOKEN")
    print(f"<tg-emoji emoji-id='5870982283724328568'>⚙</tg-emoji> Администратор ID: {ADMIN_IDS}")
    
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
