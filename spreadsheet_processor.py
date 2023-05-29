import gspread
# from google.oauth2.service_account import Credentials
from oauth2client.service_account import ServiceAccountCredentials

from constants import CLAIM_SHEET_NAME, CLAIM_NUM, CLAIM_PROCESSED_DATE, CLAIM_SECURITY_NUM


def get_spreadsheet():
    # in case google.oauth2
    # scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    # credentials = Credentials.from_service_account_file('credentials.json', scopes=scopes)

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(credentials)

    spreadsheet_url = 'https://docs.google.com/spreadsheets/d/1ZnkTI5xrR0vDh5QWMyNEz4PWofWhMv-nc4oUyeEbkzQ/edit?usp=sharing'
    spreadsheet = client.open_by_url(spreadsheet_url)
    return spreadsheet


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


def get_rows_count(worksheet_name):
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(worksheet_name)
    return worksheet.row_count


def get_claims_from_excel():
    return get_data_from_worksheet(CLAIM_SHEET_NAME)


def add_claim_to_excel(row_data):
    add_row_to_worksheet(CLAIM_SHEET_NAME, row_data)


def get_last_claim_number_cell() -> int:
    spreadsheet = get_spreadsheet()
    worksheet = spreadsheet.worksheet(CLAIM_SHEET_NAME)
    return int(worksheet.cell(get_rows_count(), CLAIM_NUM))


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
    worksheet.update_cell(cell.row, 8, processed_date)
    worksheet.update_cell(cell.row, 9, security_num)
    worksheet.update_cell(cell.row, 10, status)