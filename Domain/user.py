from spreadsheet_processor import check_if_security, check_if_inhabitant, get_apart_num, get_phone_num_by_user_id, \
    get_name_by_user_id


class User:
    def __init__(self, user_id):
        self.id = user_id
        self.number = get_phone_num_by_user_id(self.id)
        self.is_inhabitant = self.is_inhabitant()
        self.is_security = self.is_security()
        self.is_blacklisted = None
        self.tg_name = self.get_user_name()
        self.apartments = self.get_user_apart()

    def get_user_apart(self):
        return get_apart_num(self.number)

    def is_inhabitant(self):
        return check_if_inhabitant(self.number)

    def is_security(self):
        return check_if_security(self.number, True)

    def is_admin(self):
        return check_if_security(self.number, False)

    def get_user_name(self):
        return get_name_by_user_id(self.id)

