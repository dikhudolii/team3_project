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
        if self.number is not None:
            return get_apart_num(self.number)
        return None

    def is_inhabitant(self):
        if self.number is not None:
            return check_if_inhabitant(self.number)
        return False

    def is_security(self):
        if self.number is not None:
            return check_if_security(self.number, True)
        return False

    def is_admin(self):
        if self.number is not None:
            return check_if_security(self.number, False)
        return False

    def get_user_name(self):
        return get_name_by_user_id(self.id)

