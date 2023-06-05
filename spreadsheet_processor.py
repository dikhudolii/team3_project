import gspread
from google.oauth2.service_account import Credentials

from constants import CLAIM_SHEET_NAME, CLAIM_NUM, CLAIM_PROCESSED_DATE, CLAIM_SECURITY_NUM, SECURITY_SHEET_NAME


def get_spreadsheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = Credentials.from_service_account_file('credentials.json', scopes=scope)
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


