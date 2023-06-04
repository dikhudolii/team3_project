from datetime import datetime
from enum import Enum
from constants import CLAIM_DESCRIPTION, CLAIM_NUM, CLAIM_PHONE_NUMBER, CLAIM_TYPE, CLAIM_VEHICLE_NUM, \
    CLAIM_CHECKPOINT, CLAIM_CREATED_DATE, CLAIM_PROCESSED_DATE, CLAIM_SECURITY_NUM, CLAIM_STATUS, FORMAT_STRING, \
    CLAIM_APARTMENT_NUMBER
from Domain.user import get_user_by_id
from spreadsheet_processor import get_claims_from_excel, add_claim_to_excel, get_last_claim_number_cell, delete_claim, \
    update_claim


class ClaimTypes(Enum):
    Taxi = "Таксі"
    Delivery = "Кур’єр"
    Guests = "Гості"
    ProblemWithParking = "Проблеми з парковкою"
    Other = "Інше"


class ClaimStatuses(Enum):
    New = "В процесі опрацювання"
    Rejected = "Відхилено"
    Done = "Виконано"


class CheckpointTypes(Enum):
    Main = "перший КПП-головний"
    Second = "другий КПП-боковий"
    Unknown = "Невідомий варіант"


class Claim:

    def __init__(self, number, phone_number, apartment_number, claim_type, vehicle_number, checkpoint,
                 description, created_date, status):
        '''
            number - generate number of claim
            phone_number - phone number of user
            claim_type -one of allowed claim types
            vehicle_number - not necessary field in case claim type guests without car or other
            checkpoint - one of the type of checkpoint
            description - description of main goal of this claim
            created_date - date of claim creation
            status - one of the possible value from claim statuses
        '''

        self.number = number
        self.phone_number = phone_number
        self.apartment_number = apartment_number
        self.type = claim_type
        self.vehicle_number = vehicle_number
        self.checkpoint = checkpoint
        self.description = description
        self.status = status
        self.created_date = created_date

        self.security_number = None
        self.processed_date = None
        self.geolocation = None
        self.photos = None
        self.documents = None

    @classmethod
    def init_empty(cls, user_number, apartment_number):
        return cls("", user_number, apartment_number, None, None, None, "", None, ClaimStatuses.New.value)

    def __str__(self):
        info = f"Тип: {self.type}"
        if self.vehicle_number is not None:
            info += f", Номер авто: {self.vehicle_number}"
        if self.description is not None and len(self.description) > 0:
            info += f", {self.description} "
        if self.checkpoint is not None:
            info += f", КПП: {self.checkpoint} "
        return info


def get_claims(is_inhabitant: bool, number: str, only_new: bool):
    claims_data = get_claims_from_excel()
    claims = []

    for row in claims_data:
        claims.append(
            convert_row_data_into_claim(row)
        )

    if only_new:
        current_date = datetime.now().date()
        claims = [claim for claim in claims if claim.created_date.date() == current_date]
    if is_inhabitant:
        claims = [claim for claim in claims if claim.phone_number == number]

    return claims


def get_next_claim_number():
    return get_last_claim_number_cell() + 1


def save_claim(claim: Claim):
    claim.number = get_next_claim_number()
    claim.created_date = datetime.now().strftime(FORMAT_STRING)
    row_data = convert_claim_into_row_data(claim)
    add_claim_to_excel(row_data)


def convert_claim_into_row_data(claim: Claim):
    row = [claim.number,
           claim.phone_number,
           claim.apartment_number,
           claim.type,
           claim.vehicle_number,
           claim.checkpoint,
           claim.description,
           claim.created_date,
           claim.processed_date,
           claim.security_number,
           claim.status]
    return row


def convert_row_data_into_claim(row) -> Claim:
    return Claim(int(row[CLAIM_NUM]),
                 str(row[CLAIM_PHONE_NUMBER]),
                 str(row[CLAIM_APARTMENT_NUMBER]),
                 str(row[CLAIM_TYPE]),
                 str(row[CLAIM_VEHICLE_NUM]),
                 str(row[CLAIM_CHECKPOINT]),
                 str(row[CLAIM_DESCRIPTION]),
                 datetime.strptime(str(row[CLAIM_CREATED_DATE]), FORMAT_STRING),
                 str(row[CLAIM_STATUS]))


# delete row
def cancel_claim(number):
    delete_claim(number)


def reject_claim(number, security_name):
    now = datetime.now()
    update_claim(number, now.strftime(FORMAT_STRING), security_name, ClaimStatuses.Rejected.value)


def to_process_claim(number, security_name):
    now = datetime.now()
    update_claim(number, now.strftime(FORMAT_STRING), security_name, ClaimStatuses.Done.value)
