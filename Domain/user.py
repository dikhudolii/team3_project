

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


# need to implement
def get_user_by_id(user_id: int) -> User:
    user = User(user_id)
    return user
