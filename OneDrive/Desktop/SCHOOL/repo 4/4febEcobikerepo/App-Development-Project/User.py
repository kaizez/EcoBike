import hashlib
import time
from werkzeug.security import generate_password_hash

class User:

    def __init__(self, email, username, password, user_id=None, last_login=None, status='active', is_admin=False, points=0, profile_picture="default.png"):
        self.__email = email
        self.__username = username
        self.__password = password
        self.__user_id = user_id or str(int(time.time()))
        self.__last_login = last_login or time.time()
        self.__status = status
        self.__is_admin = is_admin
        self.__points = points
        self.__profile_picture = profile_picture

    # Getters
    def get_email(self):
        return self.__email

    def get_username(self):
        return self.__username

    def get_password(self):
        return self.__password

    def get_user_id(self):
        return self.__user_id

    def get_last_login(self):
        return self.__last_login

    def get_status(self):
        return self.__status

    def is_admin(self):
        return self.__is_admin

    def get_points(self):
        return self.__points

    def get_profile_picture(self):
        return self.__profile_picture if self.__profile_picture else "helmet_pfp.jpg"

    # Setters
    def set_username(self, username):
        self.__username = username

    def set_status(self, status):
        self.__status = status

    def set_last_login(self, last_login):
        self.__last_login = last_login

    def set_admin(self, is_admin):
        self.__is_admin = is_admin

    def set_points(self, points):
        self.__points = points

    def set_profile_picture(self, filename):
        self.__profile_picture = filename


    # ✅ New method for updating passwords
    def set_password(self, password):
        """Hashes and updates the user's password securely."""
        self.__password = self.hash_password(password)  # ✅ Store securely hashed password

    # ✅ Modify check_password to compare hashes
    def check_password(self, input_password):
        return self.__password == self.hash_password(input_password)

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()


    def update_last_login(self):
        self.__last_login = time.time()

    def earn_points(self, amount):
        self.__points += amount

    def redeem_points(self, amount):
        if self.__points >= amount:
            self.__points -= amount
            return True
        return False

    def to_dict(self):
        return {
            'email': self.__email,
            'username': self.__username,
            'password': self.__password,
            'user_id': self.__user_id,
            'last_login': self.__last_login,
            'status': self.__status,
            'is_admin': self.__is_admin,
            'points': self.__points,
            'profile_picture': self.__profile_picture
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            email=data['email'],
            username=data['username'],
            password=data['password'],
            user_id=data['user_id'],
            last_login=data['last_login'],
            status=data['status'],
            is_admin=data.get('is_admin', False),  # Default to False for backward compatibility
            points = data.get('points', 0),
            profile_picture = data.get('profile_picture', "default.png")
        )

class Reward:
    def __init__(self, name, cost, stock=0):
        self.__name = name
        self.__cost = cost
        self.__stock = stock  # ✅ Private attribute

    # Getters
    def get_name(self):
        return self.__name

    def get_cost(self):
        return self.__cost

    def get_stock(self):
        return self.__stock

    # Setters
    def set_stock(self, stock):
        self.__stock = max(0, stock)  # ✅ Prevent negative stock values

    # Convert to dictionary for storage
    def to_dict(self):
        return {"name": self.__name, "cost": self.__cost, "stock": self.__stock}

    # Convert from dictionary
    @classmethod
    def from_dict(cls, data):
        return cls(data["name"], data["cost"], data.get("stock", 0))

