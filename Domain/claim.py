from Domain.user import User, get_user_by_id


class Claim:
    def __init__(self, phone_number, type_id, vehicle_number, checkpoint,
                 description):
        self.id = 1
        self.phone_number = phone_number
        self.type = type_id
        self.vehicle_number = vehicle_number
        self.checkpoint = checkpoint
        self.description = description
        self.status = "New"


def get_claims(user_id: int):
    user = get_user_by_id(user_id)
    claims = []
    if user.is_inhabitant:
        # get claims by user_id only in Status New ? or all claims by today's date
        claims = [Claim("+380666669796", "delivery", "AA3453BB", "КПП1", "makeup"),
                  Claim("+380666669796", "taxi", "AA1111BB", "КПП1", "taxi"),
                  Claim("+380666669796", "guest", "AA0001", "КПП1", "guest")]
    elif user.is_security:
        # get claims by gate number??? and only in status New ???
        claims = [Claim("+380666669796", "delivery", "AA3453BB", "КПП1", "makeup"),
                  Claim("+380666669796", "taxi", "AA1111BB", "КПП1", "taxi"),
                  Claim("+380666669796", "guest", "AA0001", "КПП1", "guest"),
                  Claim("+380509555555", "taxi", "AA1111BB", "КПП1", "taxi"),
                  Claim("+380635555589", "guest", "", "КПП1", "taxi"),
                  Claim("+380686598989", "guest", "", "КПП1", "taxi"),
                  ]

    return claims
