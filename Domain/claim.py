from datetime import datetime
from enum import Enum
from constants import CLAIM_DESCRIPTION, CLAIM_NUM, CLAIM_PHONE_NUMBER, CLAIM_TYPE, CLAIM_VEHICLE_NUM, \
    CLAIM_CHECKPOINT, CLAIM_CREATED_DATE, CLAIM_PROCESSED_DATE, CLAIM_SECURITY_NUM, CLAIM_STATUS, FORMAT_STRING, \
    CLAIM_APARTMENT_NUMBER, CLAIM_VISITORS_DATA, CLAIM_LOCATION, CLAIM_PHOTOIDS
from spreadsheet_processor import get_claims_from_excel, add_claim_to_excel, get_last_claim_number_cell, delete_claim, \
    update_claim, get_photo_by_number


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

    def __init__(self, **kwargs):
        '''
            number - generate number of claim
            phone_number - phone number of user
            claim_type -one of allowed claim types
            vehicle_number - not necessary field in case claim type guests without car or other
            visitors_data - guest's full name
            checkpoint - one of the type of checkpoint
            description - description of main goal of this claim
            created_date - date of claim creation
            status - one of the possible value from claim statuses
        '''
        self.number = kwargs.pop('number', None)
        self.phone_number = kwargs.pop('phone_number', None)
        self.apartment_number = kwargs.pop('apartment_number', None)
        self.type = kwargs.pop('type', ClaimTypes.Other.value)
        self.vehicle_number = kwargs.pop('vehicle_number', None)
        self.visitors_data = kwargs.pop('visitors_data', None)
        self.checkpoint = kwargs.pop('checkpoint', CheckpointTypes.Unknown.value)
        self.description = kwargs.pop('description', None)
        self.status = kwargs.pop('status', ClaimStatuses.New.value)
        self.created_date = kwargs.pop('created_date', None)
        self.security_number = kwargs.pop('security_number', None)
        self.processed_date = kwargs.pop('processed_date', None)
        self.geolocation = kwargs.pop('geolocation', None)

        self.photos = None
        self.photo_ids = kwargs.pop('photo_ids', "")
        if len(self.photo_ids):
            self.photos = str(self.photo_ids).split(";")
        else:
            self.photos = None

        self.documents = None

    def get_photo_to_str(self):
        if self.photos is not None and len(self.photos) > 0:
            return ';'.join(self.photos)
        return ''

    @classmethod
    def create_new(cls, number, apartment_number):
        return cls(phone_number=number, apartment_number=apartment_number)

    def __str__(self):
        info = f"Тип: {self.type}"
        if self.number is not None:
            info += f" Заявка №: {self.number}"
        if self.vehicle_number is not None and len(str(self.vehicle_number)) > 0:
            info += f", Номер авто: {self.vehicle_number}"
        if self.visitors_data is not None and len(str(self.visitors_data)) > 0:
            info += f", ПІБ відвідувача: {self.visitors_data}"
        if self.description is not None and len(self.description) > 0:
            info += f", Коментар: {self.description} "
        if self.checkpoint is not None and len(str(self.checkpoint)) > 0:
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
    return claim.number


def convert_claim_into_row_data(claim: Claim):
    row = [claim.number,
           claim.phone_number,
           claim.apartment_number,
           claim.type,
           claim.vehicle_number,
           claim.visitors_data,
           claim.checkpoint,
           claim.description,
           claim.created_date,
           claim.processed_date,
           claim.security_number,
           claim.status,
           claim.geolocation,
           claim.get_photo_to_str()]
    return row


def convert_row_data_into_claim(row) -> Claim:
    return Claim(number=int(row[CLAIM_NUM]),
                 phone_number=str(row[CLAIM_PHONE_NUMBER]),
                 apartment_number=str(row[CLAIM_APARTMENT_NUMBER]),
                 type=str(row[CLAIM_TYPE]),
                 vehicle_number=str(row[CLAIM_VEHICLE_NUM]),
                 visitors_data=str(row[CLAIM_VISITORS_DATA]),
                 checkpoint=str(row[CLAIM_CHECKPOINT]),
                 description=str(row[CLAIM_DESCRIPTION]),
                 created_date=datetime.strptime(str(row[CLAIM_CREATED_DATE]), FORMAT_STRING),
                 processed_date=datetime.strptime(str(row[CLAIM_PROCESSED_DATE]), FORMAT_STRING),
                 status=str(row[CLAIM_STATUS]),
                 geolocation=str(row[CLAIM_LOCATION]),
                 photo_ids=str(row[CLAIM_PHOTOIDS]))


# delete row
def cancel_claim(number):
    delete_claim(number)


def reject_claim(number, security_name):
    now = datetime.now()
    update_claim(number, now.strftime(FORMAT_STRING), security_name, ClaimStatuses.Rejected.value)


def to_process_claim(number, security_name):
    now = datetime.now()
    update_claim(number, now.strftime(FORMAT_STRING), security_name, ClaimStatuses.Done.value)


def get_claims_photo(number):
    return get_photo_by_number(number)
