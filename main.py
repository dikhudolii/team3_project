from telebot import types
from auth_file import token  # import token
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def get_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(credentials)

    spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1ZnkTI5xrR0vDh5QWMyNEz4PWofWhMv-nc4oUyeEbkzQ/edit?usp=sharing'
    spreadsheet = client.open_by_url(spreadsheet_url)
    return spreadsheet


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


def get_user_role(phone_number):
    blacklisted_data, tenants_data, admin_guard_data = get_data_from_spreadsheet()

    for row in blacklisted_data:
        if str(row['number']) == phone_number:
            return "Blacklisted"

    for row in tenants_data:
        if phone_number in row[1:6]:
            return "tenant"

    for i, row in enumerate(admin_guard_data):
        if row[0] == phone_number:
            return admin_guard_data[i][1]

    return None


def get_apart_num(phone_number):
    blacklisted_data, tenants_data, admin_guard_data = get_data_from_spreadsheet()

    for i, row in enumerate(tenants_data):
        if phone_number in row[1:6]:
            return tenants_data[i][0]


def check_debt(apartment_num):
    debt_data = get_debt_data_from_spreadsheet()

    for i, row in enumerate(debt_data):
        if apartment_num == row[0]:
            return int(debt_data[i][14])


def initial_user_interface(role):
    if role == 'admin':
        pass
    if role == 'guard':
        pass
    if role == 'tenant':
        pass


def telegram_bot(token_value):
    bot = telebot.TeleBot(token_value)  # create bot

    @bot.message_handler(commands=['claims'])  # handler for command for getting list of claims
    def get_list_of_claims(message):
        bot.send_message(message.chat.id, "Here you can see all your claims")

    @bot.message_handler(commands=['start'])
    def start(message):
        contact = message.contact
        phone_number = contact.phone_number

        if phone_number is None:

            keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
            button = types.KeyboardButton(text="Відправити свій контакт", request_contact=True)
            keyboard.add(button)

            bot.send_message(message.chat.id,
                             "Натисніть кнопку 'Відправити контакт' для передачі свого особистого контакту.",
                             reply_markup=keyboard)

        else:
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
        phone_number = contact.phone_number

        role = get_user_role(phone_number)
        answer = initial_user_interface(role)
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

        bot.infinity_polling()  # start endless loop of receiving new messages from Telegram


if __name__ == '__main__':
    telegram_bot(token)


