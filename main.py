#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import io
import uuid
import tempfile
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import SquareModuleDrawer, CircleModuleDrawer, RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================
# ВНИМАНИЕ: Получите НОВЫЙ токен в @BotFather и вставьте сюда!
# Текущий токен 8024802229:AAHEknWnyIkcCRVBufuyKvZK68n0MUvJKtQ больше НЕ РАБОТАЕТ
# и был скомпрометирован. Получите новый!

BOT_TOKEN = "8024802229:AAHvG8NHvI431Nrdh9iR6PAUdwUC-pUGh7o"

if BOT_TOKEN == "8024802229:AAHvG8NHvI431Nrdh9iR6PAUdwUC-pUGh7o":
    logger.error("ТОКЕН НЕ УСТАНОВЛЕН! Получите новый токен в @BotFather")
    raise ValueError("Токен бота не установлен!")

# Эмодзи для интерфейса
EMOJIS = {
    'qr': '🔳', 'link': '🔗', 'text': '📝', 'wifi': '📶', 'email': '📧',
    'phone': '📱', 'sms': '💬', 'vcard': '📇', 'event': '📅', 'location': '📍',
    'crypto': '₿', 'settings': '⚙️', 'color': '🎨', 'design': '✨',
    'stats': '📊', 'back': '🔙', 'success': '✅', 'error': '❌',
    'wait': '⏳', 'info': 'ℹ️', 'download': '📥', 'history': '📜',
    'heart': '❤️', 'star': '⭐', 'crown': '👑', 'fire': '🔥', 'rocket': '🚀',
    'magic': '🪄', 'gift': '🎁', 'tada': '🎉', 'rainbow': '🌈'
}

# Цветовые схемы
COLOR_SCHEMES = {
    'classic': ('black', 'white'),
    'neon': ('#00ff00', '#000000'),
    'gold': ('#ffd700', '#1a1a1a'),
    'ocean': ('#0066cc', '#e6f3ff'),
    'sunset': ('#ff4500', '#fff0e6'),
    'berry': ('#990066', '#ffe6f3'),
    'forest': ('#006400', '#e6ffe6'),
    'royal': ('#4b0082', '#f0e6ff'),
    'blood': ('#8b0000', '#ffe6e6'),
    'rosa': ('#ff69b4', '#fff0f5'),
    'cosmic': ('#9400d3', '#f0e6ff'),
    'aqua': ('#00ffff', '#000033'),
    'lava': ('#ff4500', '#2b1b0e'),
    'mint': ('#98ff98', '#004d00'),
    'rainbow': ('rainbow', 'white')
}

# Стили модулей
MODULE_STYLES = {
    'square': SquareModuleDrawer(),
    'circle': CircleModuleDrawer(),
    'rounded': RoundedModuleDrawer(radius_ratio=0.5)
}

# Временная директория
TEMP_DIR = "temp_files"
os.makedirs(TEMP_DIR, exist_ok=True)

# ==================== СОСТОЯНИЯ ====================
MAIN_MENU, WAITING_FOR_TEXT, WAITING_FOR_URL, WAITING_FOR_WIFI_SSID, WAITING_FOR_WIFI_PASSWORD, \
WAITING_FOR_WIFI_ENCRYPTION, WAITING_FOR_VCARD_NAME, WAITING_FOR_VCARD_PHONE, WAITING_FOR_VCARD_EMAIL, \
WAITING_FOR_VCARD_ORG, WAITING_FOR_EMAIL_ADDRESS, WAITING_FOR_EMAIL_SUBJECT, WAITING_FOR_EMAIL_BODY, \
WAITING_FOR_SMS_PHONE, WAITING_FOR_SMS_TEXT, WAITING_FOR_PHONE, WAITING_FOR_GEO_LAT, WAITING_FOR_GEO_LON, \
WAITING_FOR_CRYPTO_CURRENCY, WAITING_FOR_CRYPTO_ADDRESS, WAITING_FOR_CRYPTO_AMOUNT, \
WAITING_FOR_EVENT_NAME, WAITING_FOR_EVENT_START, WAITING_FOR_EVENT_END, WAITING_FOR_EVENT_LOCATION, \
WAITING_FOR_EVENT_DESCRIPTION, CUSTOMIZING_COLORS, CUSTOMIZING_STYLE, CUSTOMIZING_LOGO, \
HISTORY_VIEW, SETTINGS_MENU = range(31)

# ==================== ХРАНИЛИЩЕ ДАННЫХ ====================
user_sessions: Dict[int, Dict[str, Any]] = {}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Конвертация HEX в RGB"""
    if hex_color.startswith('#'):
        hex_color = hex_color[1:]
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_gradient(size: Tuple[int, int], colors: list) -> Image:
    """Создание градиентного фона"""
    img = Image.new('RGB', size, color=0)
    draw = ImageDraw.Draw(img)
    
    for i in range(size[0]):
        ratio = i / size[0]
        if len(colors) == 2:
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * ratio)
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * ratio)
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * ratio)
            draw.line([(i, 0), (i, size[1])], fill=(r, g, b))
    
    return img

def create_text_logo(text: str, size: int = 100) -> Image:
    """Создание текстового логотипа"""
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", size // 2)
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    draw.text((x, y), text, fill='black', font=font)
    return img

def validate_url(url: str) -> Tuple[bool, str]:
    """Проверка URL"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    pattern = re.compile(
        r'^(https?://)?'  # http:// or https://
        r'([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'  # domain
        r'(/[a-zA-Z0-9\-\._\?\,\'/\\\+&%\$#\=~]*)?$'  # path
    )
    return bool(pattern.match(url)), url

def validate_email(email: str) -> bool:
    """Проверка email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """Проверка телефона"""
    pattern = r'^[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}$'
    return bool(re.match(pattern, phone))

# ==================== ГЕНЕРАЦИЯ QR-КОДА ====================
def generate_qr_code(data: str, user_id: int, **kwargs) -> Tuple[bytes, str]:
    """Генерация QR-кода с настройками"""
    try:
        # Получаем настройки пользователя
        settings = user_sessions.get(user_id, {}).get('settings', {})
        
        # Параметры
        box_size = kwargs.get('box_size', settings.get('box_size', 10))
        border = kwargs.get('border', settings.get('border', 4))
        fill_color = kwargs.get('fill_color', settings.get('fill_color', 'black'))
        back_color = kwargs.get('back_color', settings.get('back_color', 'white'))
        module_style = kwargs.get('module_style', settings.get('module_style', 'square'))
        error_correction = kwargs.get('error_correction', settings.get('error_correction', 'M'))
        
        # Создание QR-кода
        qr = qrcode.QRCode(
            version=1,
            error_correction={
                'L': qrcode.constants.ERROR_CORRECT_L,
                'M': qrcode.constants.ERROR_CORRECT_M,
                'Q': qrcode.constants.ERROR_CORRECT_Q,
                'H': qrcode.constants.ERROR_CORRECT_H
            }.get(error_correction, qrcode.constants.ERROR_CORRECT_M),
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Создание изображения
        if module_style == 'gradient' and fill_color == 'rainbow':
            # Особый случай - радужный градиент
            img = qr.make_image(fill_color="black", back_color="white")
            img = img.convert('RGB')
            
            # Создаем радужный градиент
            rainbow_colors = [
                (255, 0, 0), (255, 127, 0), (255, 255, 0),
                (0, 255, 0), (0, 0, 255), (75, 0, 130), (148, 0, 211)
            ]
            gradient = create_gradient(img.size, rainbow_colors)
            
            # Накладываем QR на градиент
            img_array = np.array(img)
            gradient_array = np.array(gradient)
            mask = img_array[:, :, 0] < 128
            for i in range(3):
                img_array[:, :, i] = np.where(mask, gradient_array[:, :, i], 255)
            img = Image.fromarray(img_array)
        else:
            # Обычный QR со стилем
            drawer = MODULE_STYLES.get(module_style, SquareModuleDrawer())
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=drawer,
                color_mask=SolidFillColorMask(
                    back_color=back_color,
                    front_color=fill_color
                )
            )
        
        # Добавление логотипа если нужно
        if kwargs.get('add_logo'):
            logo_text = kwargs.get('logo_text', 'QR')
            logo_size = kwargs.get('logo_size', 30)
            logo = create_text_logo(logo_text, logo_size)
            
            # Вставляем логотип в центр
            img_width, img_height = img.size
            x = (img_width - logo_size) // 2
            y = (img_height - logo_size) // 2
            
            # Белый фон для логотипа
            img.paste((255, 255, 255), (x-2, y-2, x+logo_size+2, y+logo_size+2))
            
            if logo.mode == 'RGBA':
                img.paste(logo, (x, y), logo)
            else:
                img.paste(logo, (x, y))
        
        # Сохранение в байты
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        filename = f"qr_{uuid.uuid4().hex[:8]}.png"
        return img_bytes.getvalue(), filename
        
    except Exception as e:
        logger.error(f"Error generating QR: {e}")
        raise

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Инициализация сессии пользователя
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'history': [],
            'settings': {
                'box_size': 10,
                'border': 4,
                'fill_color': 'black',
                'back_color': 'white',
                'module_style': 'square',
                'error_correction': 'M'
            },
            'temp_data': {}
        }
    
    welcome_text = (
        f"🎯 **Привет, {user.first_name}!**\n\n"
        f"Я **QR Magic Bot** — твой персональный генератор QR-кодов с крутыми фишками!\n\n"
        f"✨ **Что я умею:**\n"
        f"• URL и текст\n"
        f"• Wi-Fi для быстрого подключения\n"
        f"• Визитки (vCard)\n"
        f"• Email, SMS, телефон\n"
        f"• События и геолокация\n"
        f"• Криптовалюты\n"
        f"• Кастомизация цветов и стилей\n"
        f"• Градиенты и логотипы\n\n"
        f"📱 **Выбери тип данных:**"
    )
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['link']} URL / Ссылка", callback_data="type_url")],
        [InlineKeyboardButton(f"{EMOJIS['text']} Текст", callback_data="type_text")],
        [InlineKeyboardButton(f"{EMOJIS['wifi']} Wi-Fi сеть", callback_data="type_wifi")],
        [InlineKeyboardButton(f"{EMOJIS['vcard']} Визитка (vCard)", callback_data="type_vcard")],
        [InlineKeyboardButton(f"{EMOJIS['email']} Email", callback_data="type_email")],
        [InlineKeyboardButton(f"{EMOJIS['phone']} Телефон", callback_data="type_phone")],
        [InlineKeyboardButton(f"{EMOJIS['sms']} SMS", callback_data="type_sms")],
        [InlineKeyboardButton(f"{EMOJIS['event']} Событие", callback_data="type_event")],
        [InlineKeyboardButton(f"{EMOJIS['location']} Геолокация", callback_data="type_geo")],
        [InlineKeyboardButton(f"{EMOJIS['crypto']} Криптовалюта", callback_data="type_crypto")],
        [InlineKeyboardButton(f"{EMOJIS['color']} Кастомизация", callback_data="customize")],
        [InlineKeyboardButton(f"{EMOJIS['settings']} Настройки", callback_data="settings")],
        [InlineKeyboardButton(f"{EMOJIS['history']} История", callback_data="history")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    return MAIN_MENU

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = (
        f"{EMOJIS['info']} **Как пользоваться ботом:**\n\n"
        f"1. Выберите тип данных из меню\n"
        f"2. Введите необходимую информацию\n"
        f"3. Настройте внешний вид (по желанию)\n"
        f"4. Получите готовый QR-код\n\n"
        f"{EMOJIS['magic']} **Фишки:**\n"
        f"• Разные стили модулей (круги, квадраты, скругленные)\n"
        f"• 15+ цветовых схем\n"
        f"• Градиенты и радужные QR\n"
        f"• Добавление логотипов\n"
        f"• История созданных QR\n\n"
        f"{EMOJIS['rocket']} **Команды:**\n"
        f"/start - Главное меню\n"
        f"/help - Эта справка\n"
        f"/settings - Настройки\n"
        f"/history - История\n"
        f"/cancel - Отмена"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия"""
    await update.message.reply_text(
        f"{EMOJIS['back']} Действие отменено. Возвращаюсь в главное меню.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(f"{EMOJIS['qr']} Главное меню", callback_data="main_menu")
        ]])
    )
    return MAIN_MENU

# ==================== ОБРАБОТЧИКИ КНОПОК ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "main_menu":
        return await show_main_menu(query)
    
    elif data == "type_url":
        await query.edit_message_text(
            f"{EMOJIS['link']} **Введите URL**\n\n"
            f"Пример: https://example.com или example.com\n\n"
            f"{EMOJIS['back']} /cancel - отмена",
            parse_mode='Markdown'
        )
        return WAITING_FOR_URL
    
    elif data == "type_text":
        await query.edit_message_text(
            f"{EMOJIS['text']} **Введите текст**\n\n"
            f"Максимум 1000 символов\n\n"
            f"{EMOJIS['back']} /cancel - отмена",
            parse_mode='Markdown'
        )
        return WAITING_FOR_TEXT
    
    elif data == "type_wifi":
        await query.edit_message_text(
            f"{EMOJIS['wifi']} **Введите название Wi-Fi сети (SSID)**\n\n"
            f"{EMOJIS['back']} /cancel - отмена",
            parse_mode='Markdown'
        )
        return WAITING_FOR_WIFI_SSID
    
    elif data == "customize":
        keyboard = [
            [InlineKeyboardButton(f"{EMOJIS['color']} Цветовая схема", callback_data="customize_colors")],
            [InlineKeyboardButton(f"{EMOJIS['design']} Стиль модулей", callback_data="customize_style")],
            [InlineKeyboardButton(f"{EMOJIS['star']} Добавить логотип", callback_data="customize_logo")],
            [InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="main_menu")]
        ]
        await query.edit_message_text(
            f"{EMOJIS['magic']} **Кастомизация QR-кода**\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return MAIN_MENU
    
    elif data == "customize_colors":
        keyboard = []
        for name in COLOR_SCHEMES.keys():
            keyboard.append([InlineKeyboardButton(
                f"{EMOJIS['heart']} {name.capitalize()}",
                callback_data=f"color_{name}"
            )])
        keyboard.append([InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="customize")])
        
        await query.edit_message_text(
            f"{EMOJIS['rainbow']} **Выберите цветовую схему:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return CUSTOMIZING_COLORS
    
    elif data.startswith("color_"):
        scheme_name = data[6:]
        scheme = COLOR_SCHEMES.get(scheme_name, COLOR_SCHEMES['classic'])
        
        user_sessions[user_id]['settings']['fill_color'] = scheme[0]
        user_sessions[user_id]['settings']['back_color'] = scheme[1]
        
        await query.edit_message_text(
            f"{EMOJIS['success']} Цветовая схема **{scheme_name}** установлена!\n\n"
            f"Теперь создайте QR-код через главное меню.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"{EMOJIS['qr']} В меню", callback_data="main_menu")
            ]]),
            parse_mode='Markdown'
        )
        return MAIN_MENU
    
    elif data == "customize_style":
        keyboard = [
            [InlineKeyboardButton("🔲 Квадраты", callback_data="style_square")],
            [InlineKeyboardButton("⚪ Круги", callback_data="style_circle")],
            [InlineKeyboardButton("🟩 Скругленные", callback_data="style_rounded")],
            [InlineKeyboardButton("🌈 Радужный", callback_data="style_rainbow")],
            [InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="customize")]
        ]
        await query.edit_message_text(
            f"{EMOJIS['design']} **Выберите стиль модулей:**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return CUSTOMIZING_STYLE
    
    elif data.startswith("style_"):
        style = data[6:]
        user_sessions[user_id]['settings']['module_style'] = style
        
        await query.edit_message_text(
            f"{EMOJIS['success']} Стиль **{style}** установлен!\n\n"
            f"Теперь создайте QR-код через главное меню.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"{EMOJIS['qr']} В меню", callback_data="main_menu")
            ]]),
            parse_mode='Markdown'
        )
        return MAIN_MENU
    
    elif data == "settings":
        settings = user_sessions[user_id]['settings']
        text = (
            f"{EMOJIS['settings']} **Текущие настройки:**\n\n"
            f"• Размер: {settings['box_size']}\n"
            f"• Граница: {settings['border']}\n"
            f"• Цвет: {settings['fill_color']}\n"
            f"• Фон: {settings['back_color']}\n"
            f"• Стиль: {settings['module_style']}\n"
            f"• Коррекция: {settings['error_correction']}\n\n"
            f"Изменить настройки можно в процессе создания QR."
        )
        keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MAIN_MENU
    
    elif data == "history":
        history = user_sessions[user_id].get('history', [])[-10:]  # Последние 10
        if not history:
            text = f"{EMOJIS['history']} **История пуста**\n\nСоздайте свой первый QR-код!"
        else:
            text = f"{EMOJIS['history']} **Последние QR-коды:**\n\n"
            for i, item in enumerate(history, 1):
                text += f"{i}. {item['type']}: {item['data'][:30]}...\n"
        
        keyboard = [[InlineKeyboardButton(f"{EMOJIS['back']} Назад", callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MAIN_MENU
    
    return MAIN_MENU

async def show_main_menu(query):
    """Показать главное меню"""
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['link']} URL / Ссылка", callback_data="type_url")],
        [InlineKeyboardButton(f"{EMOJIS['text']} Текст", callback_data="type_text")],
        [InlineKeyboardButton(f"{EMOJIS['wifi']} Wi-Fi сеть", callback_data="type_wifi")],
        [InlineKeyboardButton(f"{EMOJIS['vcard']} Визитка (vCard)", callback_data="type_vcard")],
        [InlineKeyboardButton(f"{EMOJIS['email']} Email", callback_data="type_email")],
        [InlineKeyboardButton(f"{EMOJIS['phone']} Телефон", callback_data="type_phone")],
        [InlineKeyboardButton(f"{EMOJIS['sms']} SMS", callback_data="type_sms")],
        [InlineKeyboardButton(f"{EMOJIS['event']} Событие", callback_data="type_event")],
        [InlineKeyboardButton(f"{EMOJIS['location']} Геолокация", callback_data="type_geo")],
        [InlineKeyboardButton(f"{EMOJIS['crypto']} Криптовалюта", callback_data="type_crypto")],
        [InlineKeyboardButton(f"{EMOJIS['color']} Кастомизация", callback_data="customize")],
        [InlineKeyboardButton(f"{EMOJIS['settings']} Настройки", callback_data="settings")],
        [InlineKeyboardButton(f"{EMOJIS['history']} История", callback_data="history")]
    ]
    
    await query.edit_message_text(
        f"{EMOJIS['qr']} **Главное меню**\n\nВыберите тип данных для QR-кода:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return MAIN_MENU

# ==================== ОБРАБОТЧИКИ СООБЩЕНИЙ ====================
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка URL"""
    user_id = update.effective_user.id
    url = update.message.text.strip()
    
    is_valid, processed_url = validate_url(url)
    if not is_valid:
        await update.message.reply_text(
            f"{EMOJIS['error']} Неверный формат URL. Попробуйте снова:\n\n"
            f"Пример: https://example.com или google.com\n\n"
            f"{EMOJIS['back']} /cancel - отмена"
        )
        return WAITING_FOR_URL
    
    try:
        status_msg = await update.message.reply_text(f"{EMOJIS['wait']} Генерирую QR-код...")
        
        # Генерация QR
        img_bytes, filename = generate_qr_code(processed_url, user_id)
        
        # Сохраняем в историю
        user_sessions[user_id]['history'].append({
            'type': 'URL',
            'data': processed_url,
            'time': datetime.now().isoformat()
        })
        
        # Отправка фото
        await update.message.reply_photo(
            photo=img_bytes,
            filename=filename,
            caption=f"{EMOJIS['success']} QR-код для URL:\n{processed_url}"
        )
        
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} Ошибка при генерации QR-кода")
    
    # Возвращаемся в главное меню
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['qr']} В меню", callback_data="main_menu")]]
    await update.message.reply_text(
        "Что делаем дальше?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MAIN_MENU

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка текста"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if len(text) > 1000:
        await update.message.reply_text(
            f"{EMOJIS['error']} Текст слишком длинный! Максимум 1000 символов.\n"
            f"Сейчас: {len(text)} символов\n\n"
            f"Попробуйте снова или /cancel"
        )
        return WAITING_FOR_TEXT
    
    try:
        status_msg = await update.message.reply_text(f"{EMOJIS['wait']} Генерирую QR-код...")
        
        img_bytes, filename = generate_qr_code(text, user_id)
        
        user_sessions[user_id]['history'].append({
            'type': 'Text',
            'data': text[:50] + ('...' if len(text) > 50 else ''),
            'time': datetime.now().isoformat()
        })
        
        await update.message.reply_photo(
            photo=img_bytes,
            filename=filename,
            caption=f"{EMOJIS['success']} QR-код с текстом готов!"
        )
        
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} Ошибка при генерации QR-кода")
    
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['qr']} В меню", callback_data="main_menu")]]
    await update.message.reply_text(
        "Что делаем дальше?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MAIN_MENU

async def handle_wifi_ssid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка названия Wi-Fi сети"""
    user_id = update.effective_user.id
    ssid = update.message.text.strip()
    
    if not ssid:
        await update.message.reply_text(
            f"{EMOJIS['error']} Название сети не может быть пустым. Попробуйте снова:"
        )
        return WAITING_FOR_WIFI_SSID
    
    user_sessions[user_id]['temp_data']['wifi_ssid'] = ssid
    
    # Выбор типа шифрования
    keyboard = [
        [InlineKeyboardButton("WPA/WPA2 (рекомендуется)", callback_data="wifi_enc_wpa")],
        [InlineKeyboardButton("WEP", callback_data="wifi_enc_wep")],
        [InlineKeyboardButton("Без пароля", callback_data="wifi_enc_nopass")],
        [InlineKeyboardButton(f"{EMOJIS['back']} Отмена", callback_data="main_menu")]
    ]
    
    await update.message.reply_text(
        f"{EMOJIS['wifi']} Сеть: **{ssid}**\n\n"
        f"Выберите тип шифрования:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return WAITING_FOR_WIFI_ENCRYPTION

async def wifi_encryption_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора шифрования"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    enc_type = query.data.replace("wifi_enc_", "")
    
    user_sessions[user_id]['temp_data']['wifi_enc'] = enc_type
    
    if enc_type == 'nopass':
        # Без пароля - сразу генерируем
        return await generate_wifi_qr(query, user_id)
    else:
        await query.edit_message_text(
            f"{EMOJIS['wifi']} Введите пароль для сети "
            f"**{user_sessions[user_id]['temp_data']['wifi_ssid']}**:\n\n"
            f"{EMOJIS['back']} /cancel - отмена",
            parse_mode='Markdown'
        )
        return WAITING_FOR_WIFI_PASSWORD

async def handle_wifi_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка пароля Wi-Fi"""
    user_id = update.effective_user.id
    password = update.message.text.strip()
    
    user_sessions[user_id]['temp_data']['wifi_password'] = password
    
    # Генерируем QR
    query = type('obj', (), {'from_user': update.effective_user, 'message': update.message})()
    return await generate_wifi_qr(query, user_id)

async def generate_wifi_qr(query, user_id):
    """Генерация Wi-Fi QR кода"""
    temp_data = user_sessions[user_id]['temp_data']
    ssid = temp_data['wifi_ssid']
    enc = temp_data.get('wifi_enc', 'nopass')
    password = temp_data.get('wifi_password', '')
    
    # Формат: WIFI:S:<SSID>;T:<WPA|WEP|>;P:<password>;;
    wifi_data = f"WIFI:S:{ssid};T:{enc.upper()};P:{password};;"
    
    try:
        if hasattr(query, 'edit_message_text'):
            await query.edit_message_text(f"{EMOJIS['wait']} Генерирую QR-код...")
        else:
            status = await query.message.reply_text(f"{EMOJIS['wait']} Генерирую QR-код...")
        
        img_bytes, filename = generate_qr_code(wifi_data, user_id, fill_color='#0066cc')
        
        user_sessions[user_id]['history'].append({
            'type': 'Wi-Fi',
            'data': ssid,
            'time': datetime.now().isoformat()
        })
        
        caption = f"{EMOJIS['success']} QR-код для Wi-Fi сети **{ssid}**"
        if enc != 'nopass':
            caption += f"\n🔐 Тип: {enc.upper()}"
        
        if hasattr(query, 'message'):
            await query.message.reply_photo(photo=img_bytes, filename=filename, caption=caption, parse_mode='Markdown')
        else:
            await query.reply_photo(photo=img_bytes, filename=filename, caption=caption, parse_mode='Markdown')
        
        if 'status' in locals():
            await status.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        error_msg = f"{EMOJIS['error']} Ошибка при генерации QR-кода"
        if hasattr(query, 'edit_message_text'):
            await query.edit_message_text(error_msg)
        else:
            await query.message.reply_text(error_msg)
    
    # Очищаем временные данные
    user_sessions[user_id]['temp_data'] = {}
    
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['qr']} В меню", callback_data="main_menu")]]
    if hasattr(query, 'message'):
        await query.message.reply_text(
            "Что делаем дальше?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.reply_text(
            "Что делаем дальше?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return MAIN_MENU

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка email"""
    user_id = update.effective_user.id
    email = update.message.text.strip()
    
    if not validate_email(email):
        await update.message.reply_text(
            f"{EMOJIS['error']} Неверный формат email. Попробуйте снова:\n\n"
            f"Пример: name@example.com\n\n"
            f"{EMOJIS['back']} /cancel - отмена"
        )
        return WAITING_FOR_EMAIL_ADDRESS
    
    # Простой email QR (mailto:)
    email_data = f"mailto:{email}"
    
    try:
        status_msg = await update.message.reply_text(f"{EMOJIS['wait']} Генерирую QR-код...")
        
        img_bytes, filename = generate_qr_code(email_data, user_id)
        
        user_sessions[user_id]['history'].append({
            'type': 'Email',
            'data': email,
            'time': datetime.now().isoformat()
        })
        
        await update.message.reply_photo(
            photo=img_bytes,
            filename=filename,
            caption=f"{EMOJIS['success']} QR-код для email:\n{email}"
        )
        
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} Ошибка при генерации QR-кода")
    
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['qr']} В меню", callback_data="main_menu")]]
    await update.message.reply_text(
        "Что делаем дальше?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MAIN_MENU

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка телефона"""
    user_id = update.effective_user.id
    phone = update.message.text.strip()
    
    if not validate_phone(phone):
        await update.message.reply_text(
            f"{EMOJIS['error']} Неверный формат телефона. Попробуйте снова:\n\n"
            f"Пример: +79123456789 или 89123456789\n\n"
            f"{EMOJIS['back']} /cancel - отмена"
        )
        return WAITING_FOR_PHONE
    
    phone_data = f"tel:{phone}"
    
    try:
        status_msg = await update.message.reply_text(f"{EMOJIS['wait']} Генерирую QR-код...")
        
        img_bytes, filename = generate_qr_code(phone_data, user_id)
        
        user_sessions[user_id]['history'].append({
            'type': 'Phone',
            'data': phone,
            'time': datetime.now().isoformat()
        })
        
        await update.message.reply_photo(
            photo=img_bytes,
            filename=filename,
            caption=f"{EMOJIS['success']} QR-код для телефона:\n{phone}"
        )
        
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} Ошибка при генерации QR-кода")
    
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['qr']} В меню", callback_data="main_menu")]]
    await update.message.reply_text(
        "Что делаем дальше?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MAIN_MENU

async def handle_sms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка SMS"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if len(text) > 160:
        await update.message.reply_text(
            f"{EMOJIS['error']} Текст SMS слишком длинный! Максимум 160 символов.\n"
            f"Сейчас: {len(text)} символов\n\n"
            f"Попробуйте снова или /cancel"
        )
        return WAITING_FOR_SMS_TEXT
    
    # Здесь должен быть номер телефона, но для простоты используем текст
    sms_data = f"smsto:1234567890:{text}"
    
    try:
        status_msg = await update.message.reply_text(f"{EMOJIS['wait']} Генерирую QR-код...")
        
        img_bytes, filename = generate_qr_code(sms_data, user_id)
        
        user_sessions[user_id]['history'].append({
            'type': 'SMS',
            'data': text[:30] + '...',
            'time': datetime.now().isoformat()
        })
        
        await update.message.reply_photo(
            photo=img_bytes,
            filename=filename,
            caption=f"{EMOJIS['success']} QR-код для SMS готов!"
        )
        
        await status_msg.delete()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} Ошибка при генерации QR-кода")
    
    keyboard = [[InlineKeyboardButton(f"{EMOJIS['qr']} В меню", callback_data="main_menu")]]
    await update.message.reply_text(
        "Что делаем дальше?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MAIN_MENU

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================
def main() -> None:
    """Запуск бота"""
    if BOT_TOKEN == "ВСТАВЬТЕ_СЮДА_НОВЫЙ_ТОКЕН_ОТ_BOTFATHER":
        logger.error("Токен не установлен! Получите новый токен в @BotFather")
        print("\n" + "="*50)
        print("❌ ОШИБКА: Токен не установлен!")
        print("="*50)
        print("1. Откройте Telegram")
        print("2. Найдите @BotFather")
        print("3. Отправьте команду /newbot")
        print("4. Получите новый токен")
        print("5. Вставьте его в файл main.py в строку BOT_TOKEN")
        print("="*50 + "\n")
        return
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Регистрация ConversationHandler для основного меню
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(button_handler)
        ],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(button_handler)
            ],
            WAITING_FOR_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url)
            ],
            WAITING_FOR_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
            ],
            WAITING_FOR_WIFI_SSID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wifi_ssid)
            ],
            WAITING_FOR_WIFI_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wifi_password)
            ],
            WAITING_FOR_WIFI_ENCRYPTION: [
                CallbackQueryHandler(wifi_encryption_handler, pattern="^wifi_enc_")
            ],
            WAITING_FOR_EMAIL_ADDRESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)
            ],
            WAITING_FOR_PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)
            ],
            WAITING_FOR_SMS_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sms)
            ],
            CUSTOMIZING_COLORS: [
                CallbackQueryHandler(button_handler, pattern="^color_")
            ],
            CUSTOMIZING_STYLE: [
                CallbackQueryHandler(button_handler, pattern="^style_")
            ],
            SETTINGS_MENU: [
                CallbackQueryHandler(button_handler)
            ],
            HISTORY_VIEW: [
                CallbackQueryHandler(button_handler)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(button_handler, pattern="^main_menu$")
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    # Запуск бота
    logger.info("Бот запущен и готов к работе!")
    print(f"\n{EMOJIS['rocket']} Бот успешно запущен! Нажмите Ctrl+C для остановки.\n")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
