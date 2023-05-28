class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self.is_inhabitant = self._is_inhabitant()
        self.is_security = self._is_security()

    def get_user_number(self):
        return "380593539652"

    # need to implement
    def _is_inhabitant(self):
        return False

    # need to implement
    def _is_security(self):
        return True


# need to implement
def get_user_by_id(user_id: int) -> User:
    user = User(user_id)
    return user
