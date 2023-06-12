import gspread
from google.oauth2.service_account import Credentials

from constants import CLAIM_SHEET_NAME, SECURITY_SHEET_NAME, \
    USERS_SHEET_NAME

from gspread_formatting import get_data_validation_rule


def get_data_from_worksheet(worksheet_name):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return data


def add_row_to_worksheet(worksheet_name, row_data):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(worksheet_name)
    worksheet.append_row(row_data)


def delete_row_from_worksheet(worksheet_name, row_number):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(worksheet_name)
    worksheet.delete_rows(row_number)


def get_column_values(worksheet_name, column_index):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(worksheet_name)
    column_values = [value for value in worksheet.col_values(column_index) if str(value).isdigit()]
    return column_values


def get_claims_from_excel():
    return get_data_from_worksheet(CLAIM_SHEET_NAME)


def add_claim_to_excel(row_data):
    add_row_to_worksheet(CLAIM_SHEET_NAME, row_data)


def get_last_claim_number_cell() -> int:
    claim_numbers = get_column_values(CLAIM_SHEET_NAME, 1)
    claim_numbers_int = [int(number) for number in claim_numbers if str(number).isdigit()]
    if claim_numbers_int:
        return max(claim_numbers_int)
    else:
        return 0


def delete_claim(number):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(CLAIM_SHEET_NAME)
    cell = worksheet.find(number)
    worksheet.delete_rows(cell.row)
    cell = worksheet.find(number)
    return cell is None


def update_claim(number, processed_date, security_num, status):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(CLAIM_SHEET_NAME)
    cell = worksheet.find(number)
    worksheet.update_cell(cell.row, 10, processed_date)
    worksheet.update_cell(cell.row, 11, security_num)
    worksheet.update_cell(cell.row, 12, status)


def get_securities():
    return get_data_from_worksheet(SECURITY_SHEET_NAME)


def get_tg_phone_by_user_id(user_id):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(USERS_SHEET_NAME).get_all_values()
    for row in worksheet:
        if str(user_id) == str(row[1]):
            return str(row[0])


def get_tg_user_id_by_phone(phone):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(USERS_SHEET_NAME).get_all_values()
    for row in worksheet:
        if str(phone) == str(row[0]):
            return str(row[1])


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


def get_admin_data_from_spreadsheet():
    spreadsheet = get_spreadsheet()
    staff_data = spreadsheet.worksheet('admin_guard').get_all_records()
    admin_numbers = []

    for row in staff_data:
        if row['Role'] == 'admin':
            admin_numbers.append(row['Number'])

    return admin_numbers


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


def add_admin(number, role, surname):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet('admin_guard')
    worksheet.append_row([number, role, surname])


def get_user_role(phone_number, user):
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


def get_apart_num(phone_number, user):
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


def get_guards_data():
    spreadsheet = get_spreadsheet()

    admin_guard_sheet = spreadsheet.worksheet('admin_guard')
    admin_guard_data = admin_guard_sheet.get_all_values()
    guards_numbers = []

    for i, row in enumerate(admin_guard_data):
        if admin_guard_data[i][1] == "guard":
            guards_numbers.append(admin_guard_data[i][0])

    return guards_numbers


def get_guard_user_ids():
    data = get_guards_data()
    guard_ids = []
    for item in data:
        user_id = get_user_id_by_phone_num(item)
        if user_id is not None:
            guard_ids.append(user_id)
    return guard_ids


def get_user_id_by_phone_num(phone):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet('telegram_users').get_all_values()
    for row in worksheet:
        if str(phone).replace("+", '') == str(row[0]).replace("+", ''):
            return str(row[1])
    return None


def get_photo_by_number(number):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(CLAIM_SHEET_NAME)
    cell = worksheet.find(number)
    photo_cell = worksheet.cell(cell.row, 14)
    return photo_cell.value
