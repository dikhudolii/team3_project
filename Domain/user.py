from spreadsheet_processor import get_tg_user_id_by_phone, get_tg_phone_by_user_id


class User:
    def __init__(self):
        self.id = None
        self.number = None
        self.flats = []
        self.is_inhabitant = False
        self.is_security = False
        self.is_blacklisted = False
        self.tg_name = ""
        self.apartments = []

    def set_id(self, _id):
        self.id = _id

    def set_number(self, number):
        self.number = number


def get_phone_by_id(user_id):
    return get_tg_phone_by_user_id(user_id)


def get_user_id_by_phone(number):
    return get_tg_user_id_by_phone(number)
