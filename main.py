import os

import requests
from telebot import types

import spreadsheet_processor
from auth_file import token  # import token
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from Domain.claim import get_claims, to_process_claim, cancel_claim, ClaimStatuses, reject_claim, Claim, ClaimTypes, \
    save_claim
from Domain.user import User, get_user_id_by_phone
import gspread
from gspread_formatting import get_data_validation_rule
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from constants import SECURITY_ROLE, SECURITY_NUMBER, SECURITY_NAME, MENU_FULL_LIST_OF_CLAIMS, MENU_TODAY_CLAIMS, \
    MENU_STATUS_CLAIMS, MENU_SECURITY_CONTACTS, MENU_APPROVE, MENU_REJECT, MENU_CHAT, MENU_CANCEL

user = User()
new_claim_dict = {}


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

    rule = get_data_validation_rule(kpp_data, 'G2')

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
    worksheet = spreadsheet.worksheet('blacklisted_numbers')
    worksheet.append_row([number])


def add_user_id(phone_number, user_id):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet('telegram_users')
    if get_phone_num_by_user_id(user_id):
        return

    worksheet.append_row([phone_number, user_id])


def get_phone_num_by_user_id(user_id):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet('telegram_users').get_all_values()
    for row in worksheet:
        if str(user_id) == str(row[1]):
            return row[0]


def add_admin(number, role):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet('admin_guard')
    worksheet.append_row([number, role])


def get_user_role(phone_number):
    blacklisted_data, tenants_data, admin_guard_data = get_data_from_spreadsheet()

    user.number = phone_number

    for row in blacklisted_data:
        if str(row['number']) == user.number:
            user.is_blacklisted = True
            return "Blacklisted"

    for row in tenants_data:
        if user.number in list(map(str, row[3:9])):
            user.is_inhabitant = True
            return "tenant"

    for i, row in enumerate(admin_guard_data):
        if str(row[0]) == user.number:
            if admin_guard_data[i][1] == "guard":
                user.is_security = True
            else:
                user.is_admin = True
            return admin_guard_data[i][1]

    return None


def get_apart_num(phone_number):
    blacklisted_data, tenants_data, admin_guard_data = get_data_from_spreadsheet()

    for i, row in enumerate(tenants_data):
        if phone_number in row[3:9]:
            user.apartments.append(tenants_data[i][0])
            return row[0]


def check_debt(apartment_num):
    debt_data = get_debt_data_from_spreadsheet().get_all_values()

    for i, row in enumerate(debt_data):
        if apartment_num == row[0]:
            return int(debt_data[i][16])


def create_folder(service, name, parent_folder_id):
    file_metadata = {
        'name': str(name),
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_folder_id]
    }
    file = service.files().create(body=file_metadata, fields='id').execute()
    return file['id']


def upload_photo(file_info, apartment_number):
    credentials = Credentials.from_service_account_file('credentials.json')
    drive_service = build('drive', 'v3', credentials=credentials)
    folder_id = create_folder(drive_service, apartment_number, '1WMbP-CMpcsr8znKxMQzDz74UW95V0A4I')

    # Upload a file
    file = requests.get(f'https://api.telegram.org/file/bot{token}/{file_info.file_path}')

    dir_name = "photos/"
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    # Save file locally
    with open(file_info.file_path, 'wb') as f:
        f.write(file.content)

    # Determine the file's path and name
    file_name = file_info.file_path.split('/')[-1]
    file_path = file_info.file_path

    # upload file to Google Drive
    media = MediaFileUpload(file_path, mimetype='image/jpeg')
    request = drive_service.files().create(media_body=media,
                                           body={'name': file_name, 'parents': [folder_id]})
    request.execute()
    os.remove(file_path)


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
        message = f"Вітаємо, {user.tg_name}. Ви є охоронцем. Оберіть одну з доступних опцій: "
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_list_of_claims = types.KeyboardButton(text="Повний перелік заявок")
        button_list_of_today_claims = types.KeyboardButton(text="Заявки за сьогодні")
        keyboard.add(button_list_of_claims, button_list_of_today_claims)
        return message, keyboard
    if role == 'tenant':
        apartment_number = get_apart_num(user.number)
        message = f"Вітаємо, {user.tg_name}. Ви є мешканцем квартири {apartment_number}. Оберіть одну з доступних опцій: "
        keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
        button_new = types.KeyboardButton(text="Створити заявку")
        button_list_of_claims = types.KeyboardButton(text="Стан заявок")
        button_contacts = types.KeyboardButton(text="Контакти охорони")
        keyboard.add(button_new, button_list_of_claims, button_contacts)
        return message, keyboard

    return 'Ви не маєте доступу до чат бота', None


def telegram_bot(token_value):
    bot = telebot.TeleBot(token_value)  # create bot

    def simple_reply_markup(row_width: int, text_arr: list):
        markup = types.ReplyKeyboardMarkup(row_width=row_width, resize_keyboard=True)
        for element in text_arr:
            button = types.KeyboardButton(text=element)
            markup.add(button)
        return markup

    def generate_menu_checkpoint():
        markup = simple_reply_markup(3, get_kpp_options_from_spreadsheet())
        return markup

    # Code from Angela's github
    @bot.message_handler(commands=['new'])
    @bot.message_handler(func=lambda message: message.text == 'Створити заявку')
    def handle_new_request(message):
        keyboard = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        button1 = types.KeyboardButton(text="Пропуск таксі")
        button2 = types.KeyboardButton(text="Проблема парковки")
        button3 = types.KeyboardButton(text="Пропуск гостей")
        button4 = types.KeyboardButton(text="Пропуск кур'єра")
        button5 = types.KeyboardButton(text="Заявка на інше")
        button6 = types.KeyboardButton(text="Скасувати")
        keyboard.add(button1, button2, button3, button4, button5, button6)
        bot.send_message(message.chat.id, "Оберіть тип заявки:", reply_markup=keyboard)

    @bot.message_handler(func=lambda message: message.text == 'Скасувати')
    def cancel_creating_claim(message):
        result = initial_user_interface("tenant")
        bot.send_message(message.chat.id, "Оберіть одну з доступних опцій:", reply_markup=result[1])

    # Code from Angela's github
    @bot.message_handler(
        func=lambda message: message.text in ["Пропуск таксі", "Проблема парковки", "Пропуск гостей", "Пропуск кур'єра",
                                              "Заявка на інше"])
    def handle_request_type(message):
        request_type = message.text
        apartment_number = get_apart_num(user.number)
        new_claim = Claim.create_new(user.number, apartment_number)
        chat_id = message.chat.id

        match request_type:
            case "Пропуск таксі":
                new_claim.type = ClaimTypes.Taxi.value
                new_claim_dict[chat_id] = new_claim

                msg = bot.send_message(message.chat.id, "Введіть номер автомобіля таксі:")
                bot.register_next_step_handler(msg, process_number_step)

            case "Пропуск кур'єра":
                new_claim.type = ClaimTypes.Delivery.value
                new_claim_dict[chat_id] = new_claim

                markup = simple_reply_markup(1, ["Невідомий номер"])
                msg = bot.send_message(message.chat.id,
                                       "Введіть номер автомобіля кур'єра:",
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, process_number_step)

            case "Пропуск гостей":
                new_claim.type = ClaimTypes.Guests.value
                new_claim_dict[chat_id] = new_claim

                markup = simple_reply_markup(1, ["Гості без авто"])
                msg = bot.send_message(message.chat.id,
                                       "Введіть номер автомобіля або оберіть варіант 'гості без авто':",
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, process_number_step)

            case "Проблема парковки":
                new_claim.type = ClaimTypes.ProblemWithParking.value
                new_claim_dict[chat_id] = new_claim

                markup = simple_reply_markup(2, ["Моє авто заблоковано", "Автомобіль стоїть у недозволеному місці"])
                msg = bot.send_message(message.chat.id,
                                       "Уточніть характер проблеми:",
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, process_parking_step)

            case "Заявка на інше":
                new_claim.type = ClaimTypes.Other.value
                new_claim_dict[chat_id] = new_claim

                msg = bot.send_message(message.chat.id,
                                       "Напишіть текст заявки або прикріпіть фото, місцезнаходження або надішліть файл:")
                bot.register_next_step_handler(msg, process_description_step)

    def process_number_step(message):
        try:
            chat_id = message.chat.id
            claim = new_claim_dict[chat_id]
            answer = message.text

            match claim.type:
                case ClaimTypes.Taxi.value:
                    if len(answer) < 5:
                        msg = bot.reply_to(message, 'Ви повинні ввести номер автомобіля')
                        bot.register_next_step_handler(msg, process_number_step)
                        return

                    claim.vehicle_number = answer

                case ClaimTypes.Delivery.value:
                    if answer == "Невідомий номер":
                        claim.vehicle_number = ""
                        claim.description = answer
                    else:
                        if len(answer) < 5:
                            markup_unknown = simple_reply_markup(1, ["Невідомий номер"])

                            msg = bot.send_message(chat_id, 'Ви повинні ввести номер '
                                                            'автомобіля або обрати опцію "Невідомий номер"',
                                                   reply_markup=markup_unknown)
                            bot.register_next_step_handler(msg, process_number_step)
                            return

                        claim.vehicle_number = answer

                case ClaimTypes.Guests.value:
                    if answer == "Гості без авто":
                        msg = bot.send_message(chat_id, 'Введіть ПІБ гостей в одному повідомленні', reply_markup=None)
                        bot.register_next_step_handler(msg, process_guests_step)
                        return
                    else:
                        if len(answer) < 5:
                            markup_without_auto = simple_reply_markup(1, ["Гості без авто"])

                            msg = bot.send_message(chat_id, 'Ви повинні ввести номер '
                                                            'автомобіля або обрати опцію "Гості без авто"',
                                                   reply_markup=markup_without_auto)
                            bot.register_next_step_handler(msg, process_number_step)
                            return
                        claim.vehicle_number = answer

                case ClaimTypes.ProblemWithParking.value:
                    if len(answer) < 5:
                        msg = bot.reply_to(message, 'Введіть номер автомобіля порушника')
                        bot.register_next_step_handler(msg, process_number_step)
                        return
                    claim.vehicle_number = answer

            markup_without_comment = simple_reply_markup(1, ["Без коментарів"])
            msg = bot.send_message(chat_id,
                                   "Можете додати коментар до вашої заявки",
                                   reply_markup=markup_without_comment)

            bot.register_next_step_handler(msg, process_comment_step)

        except Exception as e:
            bot.reply_to(message, 'Sorry, service temporary unavailable')

    def process_guests_step(message):
        try:
            chat_id = message.chat.id
            guests = message.text
            claim = new_claim_dict[chat_id]

            if len(guests) == 0:
                msg = bot.send_message(chat_id, 'Введіть ПІБ гостей в одному повідомленні',
                                       reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, process_guests_step)
                return

            claim.visitors_data = guests

            markup_without_comment = simple_reply_markup(1, ["Без коментарів"])
            msg = bot.send_message(chat_id,
                                   "Можете додати коментар до вашої заявки", reply_markup=markup_without_comment)
            bot.register_next_step_handler(msg, process_comment_step)
        except Exception as e:
            bot.reply_to(message, 'Sorry, service temporary unavailable')

    def process_comment_step(message):
        try:
            chat_id = message.chat.id
            comment = message.text
            claim = new_claim_dict[chat_id]

            if comment != "Без коментарів":
                claim.description = comment

            if claim.type == ClaimTypes.Other.value or claim.type == ClaimTypes.ProblemWithParking.value:
                markup = simple_reply_markup(2, ["Так", "Ні"])

                msg = bot.send_message(chat_id,
                                       f"{claim}. Бажаєте зберегти заявку?",
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, process_save_claim_step)
            else:
                markup = generate_menu_checkpoint()
                msg = bot.send_message(chat_id,
                                       'Оберіть КПП',
                                       reply_markup=markup)
                bot.register_next_step_handler(msg, process_kpp_step)

        except Exception as e:
            bot.reply_to(message, 'Sorry, service temporary unavailable')

    def process_description_step(message):
        try:
            chat_id = message.chat.id
            description = message.text
            claim = new_claim_dict[chat_id]

            if len(description) == 0:
                msg = bot.send_message(chat_id, 'Напишіть текст заявки',
                                       reply_markup=ReplyKeyboardRemove())
                bot.register_next_step_handler(msg, process_description_step)
                return

            claim.description = description
            markup = simple_reply_markup(2, ["Так", "Ні"])

            msg = bot.send_message(chat_id,
                                   f"{claim}. Бажаєте зберегти заявку?",
                                   reply_markup=markup)
            bot.register_next_step_handler(msg, process_save_claim_step)
        except Exception as e:
            bot.reply_to(message, 'Sorry, service temporary unavailable')

    def process_kpp_step(message):
        try:
            chat_id = message.chat.id
            kpp = message.text
            claim = new_claim_dict[chat_id]
            claim.checkpoint = kpp

            markup = simple_reply_markup(2, ["Так", "Ні"])

            msg = bot.send_message(chat_id,
                                   f"{claim}. Бажаєте зберегти заявку?",
                                   reply_markup=markup)
            bot.register_next_step_handler(msg, process_save_claim_step)
        except Exception as e:
            bot.reply_to(message, 'Sorry, service temporary unavailable')

    def process_parking_step(message):
        try:
            chat_id = message.chat.id
            claim = new_claim_dict[chat_id]
            claim.description = message.text

            msg = bot.send_message(chat_id, 'Введіть номер авто порушника', reply_markup=ReplyKeyboardRemove())
            bot.register_next_step_handler(msg, process_number_step)

        except Exception as e:
            bot.reply_to(message, 'Sorry, service temporary unavailable')

    def process_save_claim_step(message):
        answer = message.text
        result = initial_user_interface("tenant")
        if answer == 'Так':
            chat_id = message.chat.id
            claim = new_claim_dict[chat_id]
            save_claim(claim)
            bot.send_message(message.chat.id, "Ваша заявка успішно збережена", reply_markup=result[1])
        else:
            bot.send_message(message.chat.id, "Збереження заявки скасовано", reply_markup=result[1])

    @bot.message_handler(func=lambda message: message.text == MENU_SECURITY_CONTACTS)
    def get_security_contact(message):
        security_list = ""
        data = spreadsheet_processor.get_securities()
        for row in data:
            if row[SECURITY_ROLE] == "guard":
                security_list += f"Номер телефону: {row[SECURITY_NUMBER]}, ПІБ: {row[SECURITY_NAME]}\n"

        bot.send_message(message.chat.id, security_list)

    @bot.callback_query_handler(func=lambda call: True)
    def processing_request(call):
        command, claim_id, number = str(call.data).split(',')
        claim_id = claim_id.strip()

        match command:
            case "approve":
                to_process_claim(claim_id, call.from_user.full_name)
                bot.send_message(call.message.chat.id,
                                 f"Заявкy № {claim_id} опрацьовано")
            case "reject":
                reject_claim(claim_id, call.from_user.full_name)
                bot.send_message(call.message.chat.id,
                                 f"Заявку № {claim_id} відхилено ")
            case "cancel":
                cancel_claim(claim_id)
                bot.send_message(call.message.chat.id,
                                 f"Ви успішно видалили заявку № {claim_id}")
            case "chat":
                user_id = get_user_id_by_phone(number)
                try:
                    bot.send_message(chat_id=user_id, text=f"Добрий день! Вас турбує охорона ЖК")
                except Exception as e:
                    bot.send_message(call.message.chat.id, f"Заявка № {claim_id}: Неможливо почати чат з мешканцем, "
                                                           f"спробуйте сконтактувати з ним по телефону: {number}",
                                     parse_mode="Markdown")

    @bot.message_handler(
        func=lambda message: message.text in [MENU_FULL_LIST_OF_CLAIMS, MENU_TODAY_CLAIMS, MENU_STATUS_CLAIMS])
    def get_list_of_claims(message):

        only_new = str(message.text) == MENU_TODAY_CLAIMS
        claims = get_claims(user.is_inhabitant,
                            user.number,
                            only_new=only_new)

        if len(claims) == 0:
            bot.send_message(message.chat.id,
                             f"За поданими критеріями заявок в системі не зареєстровано")

        # processing claims
        for claim in claims:
            # if user is security he would have more options to do with claim
            if user.is_security:
                if claim.status == ClaimStatuses.New.value:

                    markup_inline = InlineKeyboardMarkup()
                    item_approve = InlineKeyboardButton(
                        text=MENU_APPROVE,
                        callback_data=f"approve,{claim.number},")
                    item_reject = InlineKeyboardButton(
                        text=MENU_REJECT,
                        callback_data=f"reject,{claim.number},")
                    item_chat = InlineKeyboardButton(
                        text=MENU_CHAT,
                        callback_data=f"chat,{claim.number},{claim.phone_number}")

                    markup_inline.add(item_approve, item_reject, item_chat)
                    bot.send_message(message.chat.id,
                                     f"{claim}",
                                     reply_markup=markup_inline)
                else:
                    bot.send_message(message.chat.id,
                                     f"{claim}")

            # if user is inhabitant he could only cancel claim in case it in status New
            elif user.is_inhabitant:
                if claim.status == ClaimStatuses.New.value:

                    markup_inline = InlineKeyboardMarkup()
                    item_cancel = InlineKeyboardButton(
                        text=MENU_CANCEL,
                        callback_data=f"cancel, {claim.number}")
                    markup_inline.add(item_cancel)

                    bot.send_message(message.chat.id,
                                     f"{claim}",
                                     reply_markup=markup_inline)
                else:
                    bot.send_message(message.chat.id,
                                     f"{claim}")

    @bot.message_handler(commands=['start'])
    def start(message):
        user.tg_name = message.from_user.full_name
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

            if role is not None:
                add_user_id(contact.phone_number, contact.user_id)

            if role == 'tenant':
                apartment_number = get_apart_num(phone_number)
                debt = check_debt(apartment_number)

                if debt > 240:
                    bot.send_message(message.chat.id,
                                     f'У вас заборгованість {debt}, зверніться до адміністратора або завантажте квитанцію про оплату.')
                    return

            answer = initial_user_interface(role)
            bot.send_message(message.chat.id, answer[0], reply_markup=answer[1])

    @bot.message_handler(content_types=['contact'])
    def handle_contact(message):
        user.tg_name = message.from_user.full_name

        contact = message.contact
        phone_number = str(contact.phone_number)

        # phone_number = "380799761264" # - тест борг
        # phone_number = "380849784670"  # - тест мешканця
        # phone_number = "87654321"     # - тест охоронця

        role = get_user_role(phone_number)

        if role is not None:
            add_user_id(contact.phone_number, contact.user_id)

        if role == 'tenant':
            apartment_number = get_apart_num(phone_number)
            debt = check_debt(apartment_number)

            if debt > 240:
                bot.send_message(message.chat.id,
                                 f'У вас заборгованість {debt}, зверніться до адміністратора або завантажте квитанцію про оплату.')
                return

        answer = initial_user_interface(role)
        bot.send_message(message.chat.id, answer[0], reply_markup=answer[1])

    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        file_info = bot.get_file(message.photo[-1].file_id)
        phone_number = get_phone_num_by_user_id(message.from_user.id)
        print(phone_number)
        apartment_number = get_apart_num(phone_number)
        print(apartment_number)

        upload_photo(file_info, apartment_number)
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
            bot.send_message(message.chat.id,
                             "Некоректний формат. Будь ласка, введіть номер у форматі /blacklist [номер]")

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

    # Enable saving next step handlers to file "./.handlers-saves/step.save".
    # Delay=2 means that after any change in next step handlers (e.g. calling register_next_step_handler())
    # saving will hapen after delay 2 seconds.
    bot.enable_save_next_step_handlers(delay=2)

    # Load next_step_handlers from save file (default "./.handlers-saves/step.save")
    # WARNING It will work only if enable_save_next_step_handlers was called!
    bot.load_next_step_handlers()

    bot.infinity_polling()  # start endless loop of receiving new messages from Telegram


if __name__ == '__main__':
    telegram_bot(token)
