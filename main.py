from auth_file import token  # import token
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def get_data_from_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(credentials)

    spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1ZnkTI5xrR0vDh5QWMyNEz4PWofWhMv-nc4oUyeEbkzQ/edit?usp=sharing'
    spreadsheet = client.open_by_url(spreadsheet_url)

    blacklisted_sheet = spreadsheet.worksheet('blacklisted_numbers')
    blacklisted_data = blacklisted_sheet.get_all_records()

    tenants_sheet = spreadsheet.worksheet('tenants')
    tenants_data = tenants_sheet.get_all_values()

    admin_guard_sheet = spreadsheet.worksheet('admin_guard')
    admin_guard_data = admin_guard_sheet.get_all_values()

    return blacklisted_data, tenants_data, admin_guard_data


def get_user_role(phone_number):
    blacklisted_data, tenants_data, admin_guard_data = get_data_from_spreadsheet()

    for row in blacklisted_data:
        if str(row['number']) == phone_number:
            return "Blacklisted"

    for row in tenants_data:
        if phone_number in row[1:6]:
            return "Tenant"

    for i, row in enumerate(admin_guard_data):
        if row[0] == phone_number:
            return admin_guard_data[i][1]

    return None


def initial_user_interface(role):
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
            #  Ask for phone number
            pass

        role = get_user_role(phone_number)
        answer = initial_user_interface(role)

    @bot.message_handler(commands=['help'])
    def help_(message):
        help_message = '''
        ВСТАВИТЬ ТЕКСТ СЮДА
        '''
        bot.send_message(message.chat.id, help_message)

    bot.infinity_polling()  # start endless loop of receiving new messages from Telegram


if __name__ == '__main__':
    # telegram_bot(token)
    # print(get_data_from_spreadsheet())

    phone_number = '87654321'
    user_role = get_user_role(phone_number)
    if user_role is not None:
        print(f"User role for phone number {phone_number}: {user_role}")
    else:
        print(f"User role not found for phone number {phone_number}")
