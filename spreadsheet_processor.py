import gspread
from google.oauth2.service_account import Credentials

from constants import CLAIM_SHEET_NAME, SECURITY_SHEET_NAME, \
    USERS_SHEET_NAME, TENANTS_SHEET_NAME

from gspread_formatting import get_data_validation_rule


class SpreadsheetManager:
    def __init__(self, spreadsheet_url, credentials_file):
        self.spreadsheet_url = spreadsheet_url
        self.credentials_file = credentials_file
        self.spreadsheet = None

    def authenticate(self):
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_file(self.credentials_file, scopes=scope)
        client = gspread.authorize(credentials)
        self.spreadsheet = client.open_by_url(self.spreadsheet_url)

    def get_data_from_worksheet(self, worksheet_name):
        worksheet = self.spreadsheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return data

    def get_worksheet(self, worksheet_name):
        return self.spreadsheet.worksheet(worksheet_name)

    def get_values_from_worksheet(self, worksheet_name):
        worksheet = self.spreadsheet.worksheet(worksheet_name)
        data_ = worksheet.get_all_values()
        return data_

    def add_row_to_worksheet(self, worksheet_name, row_data):
        worksheet = self.spreadsheet.worksheet(worksheet_name)
        worksheet.append_row(row_data)

    def delete_row_from_worksheet(self, worksheet_name, row_number):
        worksheet = self.spreadsheet.worksheet(worksheet_name)
        worksheet.delete_rows(row_number)

    def get_column_values(self, worksheet_name, column_index):
        worksheet = self.spreadsheet.worksheet(worksheet_name)
        column_values = [value for value in worksheet.col_values(column_index) if str(value).isdigit()]
        return column_values


# Usage example:
spreadsheet_manager = SpreadsheetManager(
    'https://docs.google.com/spreadsheets/d/1ZnkTI5xrR0vDh5QWMyNEz4PWofWhMv-nc4oUyeEbkzQ/edit?usp=sharing',
    'credentials.json')
spreadsheet_manager.authenticate()
tenants_values = spreadsheet_manager.get_values_from_worksheet(TENANTS_SHEET_NAME)


def get_claims_from_excel():
    return spreadsheet_manager.get_data_from_worksheet(CLAIM_SHEET_NAME)


def add_claim_to_excel(row_data):
    spreadsheet_manager.add_row_to_worksheet(CLAIM_SHEET_NAME, row_data)


def get_last_claim_number_cell() -> int:
    claim_numbers = spreadsheet_manager.get_column_values(CLAIM_SHEET_NAME, 1)
    claim_numbers_int = [int(number) for number in claim_numbers if str(number).isdigit()]
    if claim_numbers_int:
        return max(claim_numbers_int)
    else:
        return 0


def delete_claim(number):
    worksheet = spreadsheet_manager.get_worksheet(CLAIM_SHEET_NAME)
    cell = worksheet.find(number)
    worksheet.delete_rows(cell.row)
    cell = worksheet.find(number)
    return cell is None


def update_claim(number, processed_date, security_num, status):
    worksheet = spreadsheet_manager.get_worksheet(CLAIM_SHEET_NAME)
    cell = worksheet.find(number)
    worksheet.update_cell(cell.row, 10, processed_date)
    worksheet.update_cell(cell.row, 11, security_num)
    worksheet.update_cell(cell.row, 12, status)


def get_securities():
    security_data = spreadsheet_manager.get_data_from_worksheet(SECURITY_SHEET_NAME)
    return security_data


def get_tg_user_id_by_phone(phone):
    users_values = spreadsheet_manager.get_values_from_worksheet(USERS_SHEET_NAME)
    for row in users_values:
        if str(phone) == str(row[0]):
            return str(row[1])


def get_kpp_options_from_spreadsheet():
    kpp_data = spreadsheet_manager.get_worksheet('Авто на пропуск')
    rule = get_data_validation_rule(kpp_data, 'G2')

    if rule:
        return [value.userEnteredValue for value in rule.condition.values]

    return None


def get_debt_data_from_spreadsheet():
    debt_data = spreadsheet_manager.get_worksheet('debt')
    return debt_data


def get_admin_data_from_spreadsheet():
    staff_data = spreadsheet_manager.get_worksheet('admin_guard').get_all_records()
    admin_numbers = []

    for row in staff_data:
        if row['Role'] == 'admin':
            admin_numbers.append(row['Number'])

    return admin_numbers


def add_to_blacklist(number):
    worksheet = spreadsheet_manager.get_worksheet('blacklisted_numbers')
    worksheet.append_row([number])


def add_user_id(phone_number, user_id, name):
    worksheet = spreadsheet_manager.get_worksheet('telegram_users')
    if get_phone_num_by_user_id(user_id):
        return

    worksheet.append_row([phone_number, user_id, name])


def get_phone_num_by_user_id(user_id):
    worksheet = spreadsheet_manager.get_worksheet('telegram_users').get_all_values()
    for row in worksheet:
        if str(user_id) == str(row[1]):
            return row[0]


def get_name_by_user_id(user_id):
    worksheet = spreadsheet_manager.get_worksheet('telegram_users').get_all_values()
    for row in worksheet:
        if str(user_id) == str(row[1]):
            return row[2]


def add_admin(number, role, surname):
    worksheet = spreadsheet_manager.get_worksheet('admin_guard')
    worksheet.append_row([number, role, surname])


def get_data_from_spreadsheet():
    blacklisted_sheet = spreadsheet_manager.get_worksheet('blacklisted_numbers')
    blacklisted_data = blacklisted_sheet.get_all_records()

    admin_guard_sheet = spreadsheet_manager.get_worksheet('admin_guard')
    admin_guard_data = admin_guard_sheet.get_all_values()

    return blacklisted_data, tenants_values, admin_guard_data


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
            return row[0]


def check_debt(apartment_num):
    debt_data = get_debt_data_from_spreadsheet().get_all_values()

    for i, row in enumerate(debt_data):
        if apartment_num == row[0]:
            return int(debt_data[i][16])


def get_guards_data():
    admin_guard_sheet = spreadsheet_manager.get_worksheet('admin_guard')
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
    worksheet = spreadsheet_manager.get_worksheet('telegram_users').get_all_values()
    for row in worksheet:
        if str(phone).replace("+", '') == str(row[0]).replace("+", ''):
            return str(row[1])
    return None


def get_photo_by_number(number):
    worksheet = spreadsheet_manager.get_worksheet(CLAIM_SHEET_NAME)
    cell = worksheet.find(number)
    photo_cell = worksheet.cell(cell.row, 14)
    return photo_cell.value


def check_if_inhabitant(phone_number):
    phone_number = phone_number.strip().replace("+", '')
    for row in tenants_values:
        if phone_number in list(map(str, row[3:9])):
            return True

    return False


def check_if_security(phone_number, check_security):
    admin_guard_values = spreadsheet_manager.get_values_from_worksheet(SECURITY_SHEET_NAME)
    phone_number = phone_number.strip().replace("+", '')
    for i, row in enumerate(admin_guard_values):
        if str(row[0]) == phone_number:
            if check_security and str(admin_guard_values[i][1]) == "admin":
                return True
            if not check_security and str(admin_guard_values[i][1]) == "guard":
                return True
    return False
