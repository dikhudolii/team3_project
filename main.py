from telebot import types
from auth_file import token  # import token
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from Domain.claim import get_claims, to_process_claim, cancel_claim, ClaimStatuses
from Domain.user import User, get_user_by_id
import gspread
from gspread_formatting import get_data_validation_rule
from google.oauth2.service_account import Credentials


def get_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_file('credentials.json', scopes=scope)
    client = gspread.authorize(credentials)

    spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1ZnkTI5xrR0vDh5QWMyNEz4PWofWhMv-nc4oUyeEbkzQ/edit?usp=sharing'
    spreadsheet = client.open_by_url(spreadsheet_url)
    return spreadsheet


def get_kpp_options_from_spreadsheet():
    spreadsheet = get_spreadsheet()
    kpp_data = spreadsheet.worksheet('Авто на пропуск')

    rule = get_data_validation_rule(kpp_data, 'E2')

    if rule:
        return [value.userEnteredValue for value in rule.condition.values]

    return None


def get_data_from_spreadsheet():
    spreadsheet = get_spreadsheet()

    blacklisted_sheet = spreadsheet.worksheet('blacklisted_numbers')
    blacklisted_data = blacklisted_sheet.get_all_records()

    tenants_sheet = spreadsheet.worksheet('tenants')
    tenants_data = tenants_sheet.get_all_values()

    admin_guard_sheet = spreadsheet.worksheet('admin_guard')
    admin_guard_data = admin_guard_sheet.get_all_values()

    return blacklisted_data, tenants_data, admin_guard_data


def get_debt_data_from_spreadsheet():
    spreadsheet = get_spreadsheet()

    debt_data = spreadsheet.worksheet('debt')
    return debt_data


def add_to_blacklist(number):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.get_worksheet('blacklisted_numbers')
    worksheet.append_row([number])


def add_admin(number, role):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.get_worksheet('admin_guard')
    worksheet.append_row([number, role])


def get_user_role(phone_number):
    blacklisted_data, tenants_data, admin_guard_data = get_data_from_spreadsheet()

    for row in blacklisted_data:
        if str(row['number']) == phone_number:
            return "Blacklisted"

    for row in tenants_data:
        if phone_number in list(map(str, row[3:9])):
            return "tenant"

    for i, row in enumerate(admin_guard_data):
        if str(row[0]) == phone_number:
            return admin_guard_data[i][1]

    return None


def get_apart_num(phone_number):
    blacklisted_data, tenants_data, admin_guard_data = get_data_from_spreadsheet()

    for i, row in enumerate(tenants_data):
        if phone_number in row[3:9]:
            return tenants_data[i][0]


def check_debt(apartment_num):
    debt_data = get_debt_data_from_spreadsheet()

    for i, row in enumerate(debt_data):
        if apartment_num == row[0]:
            return int(debt_data[i][14])


def initial_user_interface(role):
    if role == 'admin':
        message = 'Виберіть дію з нижчеподаних опцій:'
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_add_blacklisted = types.KeyboardButton(text="Додати номер у blacklist")
        button_add_admin = types.KeyboardButton(text="Додати нового адміна/охоронця")
        keyboard.add(button_add_admin)
        keyboard.add(button_add_blacklisted)
        return message, keyboard
    if role == 'guard':
        pass
    if role == 'tenant':
        return 'Ви мешканець дому, (Замість цього повідомлення має бути меню для мешканця)'

    return 'Ви не маєте доступу до чат бота', None


def telegram_bot(token_value):
    bot = telebot.TeleBot(token_value)  # create bot

    @bot.callback_query_handler(func=lambda call: True)
    def processing_request(call):
        command, claim_id = str(call.data).split(',')
        claim_id = claim_id.strip()

        match command:
            case "approve":
                to_process_claim(claim_id)
                bot.send_message(call.message.chat.id,
                                 f"Заявка успішно опрацьована {claim_id}")
            case "cancel":
                cancel_claim(claim_id)
                bot.send_message(call.message.chat.id,
                                 f"Ви успішно видалили заявку {claim_id}")
            case "chat":
                bot.send_message(call.message.chat.id, f"Start chat with inhabitant")

    @bot.message_handler(commands=['allclaims', 'todayclaims'])  # handler for getting list of claims
    def get_list_of_claims(message):
        command = str(message.text).find("todayclaims") < 0
        claims = get_claims(message.from_user.id,
                            only_new=(str(message.text).find("todayclaims") > -1))  # get list of claims from db ???
        user = get_user_by_id(message.from_user.id)  # get user info to deside is security or inhabitant from db?

        if len(claims) == 0:
            bot.send_message(message.chat.id,
                             f"За поданими критеріями заявок в системі не зареєстровано")

        # processing claims
        for claim in claims:
            # if user is security he would have more options to do with claim
            if user.is_security:
                if claim.status == ClaimStatuses.New.value:
                    markup_inline = InlineKeyboardMarkup()
                    item_approve = InlineKeyboardButton(text='Підтвердити',
                                                        callback_data=f"approve, {claim.number}")
                    item_chat = InlineKeyboardButton(text='Чат з мешканцем',
                                                     callback_data=f"chat, {claim.number, claim.phone_number}")
                    markup_inline.add(item_approve, item_chat)
                    bot.send_message(message.chat.id,
                                     f"Заявка від {claim.phone_number}, {claim.type}",
                                     reply_markup=markup_inline)
                else:
                    bot.send_message(message.chat.id,
                                     f"Заявка від {claim.phone_number}, {claim.type}")

            # if user is inhabitant he could only cancel claim in case it in status New
            elif user.is_inhabitant:
                if claim.status == ClaimStatuses.New.value:
                    markup_inline = InlineKeyboardMarkup()
                    item_cancel = InlineKeyboardButton(text='Скасувати', callback_data=f"cancel, {claim.number}")
                    markup_inline.add(item_cancel)
                    bot.send_message(message.chat.id,
                                     f"Заявка {claim.type} {claim.vehicle_number} статус: {claim.status}",
                                     reply_markup=markup_inline)
                else:
                    bot.send_message(message.chat.id,
                                     f"Заявка {claim.type} {claim.vehicle_number} статус: {claim.status}")

    @bot.message_handler(commands=['start'])
    def start(message):
        if message.contact is None or message.contact.phone_number is None:
            keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            button = types.KeyboardButton(text="Відправити свій контакт", request_contact=True)
            keyboard.add(button)

            bot.send_message(message.chat.id,
                             "Натисніть кнопку 'Відправити контакт' для передачі свого особистого контакту.",
                             reply_markup=keyboard)
        else:
            contact = message.contact
            phone_number = str(contact.phone_number)
            role = get_user_role(phone_number)

            if role == 'tenant':
                apartment_number = get_apart_num(phone_number)
                debt = check_debt(apartment_number)

                if debt > 240:
                    bot.send_message(message.chat.id, f'У вас заборгованість {debt}, зверніться до адміністратора або завантажте квитанцію про оплату.')

            answer = initial_user_interface(role)
            bot.send_message(message.chat.id, answer)


    @bot.message_handler(content_types=['contact'])
    def handle_contact(message):
        contact = message.contact
        phone_number = str(contact.phone_number)

        role = get_user_role(phone_number)
        answer = initial_user_interface(role)

        if role == 'tenant':
            apartment_number = get_apart_num(phone_number)
            debt = check_debt(apartment_number)

            if debt > 240:
                bot.send_message(message.chat.id,
                                 f'У вас заборгованість {debt}, зверніться до адміністратора або завантажте квитанцію про оплату.')

        bot.send_message(message.chat.id, answer)


    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        bot.reply_to(message, "Дякуємо! Ваша квитанція на розгляді в адміністратора.")


    @bot.message_handler(commands=['help'])
    def help_(message):
        help_message = '''
        Ось декілька корисних команд, які ви можете використовувати:
        /start - Початок роботи з ботом
        /help - Вивести це повідомлення з інструкціями
        /newrequest - Створити нову заявку
        /stop - Припинити використання бота

        Якщо у вас виникли додаткові питання або проблеми, будь ласка, зверніться до адміністратора.

        Дякуємо за використання цього бота!
        '''

        bot.send_message(message.chat.id, help_message)


    @bot.message_handler(func=lambda message: message.text == 'Додати номер у blacklist')
    def handle_blacklist_add(message):
        msg = 'Будь ласка, введіть номер, який потрібно додати до blacklist у форматі: /blacklist [номер]'
        bot.send_message(message.chat.id, msg)


    @bot.message_handler(func=lambda message: message.text == 'Додати нового адміна/охоронця')
    def handle_admin_add(message):
        msg = 'Будь ласка, введіть номер та роль нового користувача у форматі: /admin [номер] [роль]'
        bot.send_message(message.chat.id, msg)

    @bot.message_handler(commands=['blacklist'])
    def handle_blacklist_add_command(message):
        try:
            parts = message.text.split()
            if len(parts) != 2:
                raise ValueError
            number = parts[1]
            # Перевіряємо, чи є number коректним номером телефону.
            # Якщо все в порядку, додаємо номер до blacklist
            add_to_blacklist(number)
            bot.send_message(message.chat.id, "Номер успішно додано до blacklist!")
        except ValueError:
            bot.send_message(message.chat.id, "Некоректний формат. Будь ласка, введіть номер у форматі /blacklist [номер]")

    @bot.message_handler(commands=['admin'])
    def handle_admin_add_command(message):
        try:
            parts = message.text.split()
            if len(parts) != 3:
                raise ValueError
            number = parts[1]
            role = parts[2]
            # Перевіряємо, чи є number коректним номером телефону, і чи є role валідною роллю.
            # Якщо все в порядку, додаємо номер і роль до  листа admin_guard
            add_admin(number, role)
            bot.send_message(message.chat.id, "Новий адмін/охоронець успішно доданий!")
        except ValueError:
            bot.send_message(message.chat.id,
                             "Некоректний формат. Будь ласка, введіть дані у форматі /admin [номер] [роль]")

    bot.infinity_polling()  # start endless loop of receiving new messages from Telegram


if __name__ == '__main__':
    # telegram_bot(token)
    rules = get_kpp_options_from_spreadsheet()
    print(rules)
