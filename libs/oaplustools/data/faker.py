import random
from dataclasses import dataclass


@dataclass
class Identity:
    name: str = ""
    last_name: str = ""
    email: str = ""
    password: str = ""
    phone_number: str = ""
    address: str = ""
    birth_data: str = ""


class TestDataGenerator:
    MAIL_FIRST_PARTS = ["sharon", "richard", "justin", "ella", "jung", "hashimin", "bulsheesh", "scandalors", "melody",
                        "acker", "jhony", "lexie", "khalifa", "stephen", "dorota", "georgeta", "krystiana", "gerbold",
                        "iona", "lore", "surprize", "dog", "admin", "cat", "shermin"]
    MAIL_SECOND_PARTS = ["communication", "help", "gaming", "assistant", "trinity", "sponsor", "love_you", "nicelife",
                         "sun", "mukbangs", "assistant", "support", "info", "work", "school", "help", "care", "random",
                         "admin", "moderator", "adm", "mod"]
    MAIL_THIRD_PARTS = ["gmail", "outlook", "me", "yahoo", "github", "microsoft", "youtube", "gunser", "coolmail",
                        "google", "hotmail", "insta", "facebook", "msn", "gone", "braces"]
    MAIL_PART_CONNECTORS = ["-", "_", ".", ""]
    MAIL_FOURTH_PARTS = ["net", "de", "com", "you", "me", "online", "here"]

    PASSWORD_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789,;.:-_#'+*<>´`=)(/&%$§!"

    NAMES = ["sharon", "richard", "justin", "ella", "hashimin", "melody", "jhony", "lexie", "khalifa", "stephen",
             "dorota", "georgeta", "krystiana", "gerbold", "iona", "shermin"]
    LAST_NAMES = ["smith", "jones", "williams", "taylor", "brown", "davies"]

    NUMS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

    STREETS = ["Main", "Oak"]

    CENTURIES = ["19", "20"]

    DECADES = {"19": NUMS, "20": NUMS[:2]}

    YEARS = {"19": NUMS, "20": NUMS}

    MONTHS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

    DAYS = ["0" + str(x) if len(str(x)) < 2 else str(x) for x in range(31) if x != 0]  # Could be dict too, but no need

    def __init__(self):
        pass

    def generate_random_name(self):
        return f"{random.choice(self.NAMES).title()} {random.choice(self.LAST_NAMES).title()}"

    def generate_random_email(self):
        return f"{random.choice(self.MAIL_FIRST_PARTS)}{random.choice(self.MAIL_PART_CONNECTORS)}{random.choice(self.MAIL_SECOND_PARTS)}@{random.choice(self.MAIL_THIRD_PARTS)}.{random.choice(self.MAIL_FOURTH_PARTS)}"

    def generate_random_password(self, length=10):
        return ''.join(random.choices(list(self.PASSWORD_CHARS), k=length))

    def generate_random_phone_number(self):
        return f"{''.join(random.choices(self.NUMS, k=3))}-{''.join(random.choices(self.NUMS, k=3))}-{''.join(random.choices(self.NUMS, k=4))}"

    def generate_random_address(self):
        return f"{''.join(random.choices(self.NUMS, k=3))} {random.choice(self.STREETS)} St"

    def generate_random_birth_date(self):
        century = random.choice(self.CENTURIES)
        decade = random.choice(self.DECADES[century])
        year = random.choice(self.YEARS[century])
        return f"{century + decade + year}-{''.join(random.choices(self.MONTHS, k=1))}-{''.join(random.choices(self.DAYS, k=1))}"

    def generate_random_identity(self):
        name, last_name = self.generate_random_name().split(maxsplit=1)
        email = self.generate_random_email()
        password = self.generate_random_password()
        phone_number = self.generate_random_phone_number()
        address = self.generate_random_address()
        birth_date = self.generate_random_birth_date()
        return Identity(name, last_name, email, password, phone_number, address, birth_date)


def local_test():
    try:
        test_data = TestDataGenerator()
        lst_string = ', \n'.join([str(test_data.generate_random_identity()) for _ in range(9000)])
        print(lst_string)  # 900000 takes ~5 sec
        print("\n", end="")
        print(test_data.generate_random_name())
        print(test_data.generate_random_email())
        print(test_data.generate_random_password())
        print(test_data.generate_random_phone_number())
        print(test_data.generate_random_address())
        print(test_data.generate_random_birth_date())
    except Exception as e:
        print(f"Exception occurred {e}.")
        return False
    print("Test completed successfully.")
    return True


if __name__ == "__main__":
    local_test()
