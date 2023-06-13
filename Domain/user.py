from spreadsheet_processor import get_tg_user_id_by_phone, get_tg_phone_by_user_id


class User:
    def __init__(self):
        self.id = None
        self.number = None
        self.is_inhabitant = False
        self.is_security = False
        self.is_blacklisted = False
        self.tg_name = ""
        self.apartments = []

