class BikeUser:
    count_id = 0

    def __init__(self, bike_name, upload_bike_image, price, transmission_type, seating_capacity, engine_output, stock_quantity):
        BikeUser.count_id += 1
        self.__bike_id = BikeUser.count_id
        self.__bike_name = bike_name
        self.__upload_bike_image = upload_bike_image
        self.__price = price
        self.__transmission_type = transmission_type
        self.__seating_capacity = seating_capacity
        self.__engine_output = engine_output
        self.__stock_quantity = stock_quantity

    def get_bike_id(self):
        return self.__bike_id

    def get_bike_name(self):
        return self.__bike_name

    def get_upload_bike_image(self):
        return self.__upload_bike_image

    def get_price(self):
        return self.__price

    def get_transmission_type(self):
        return self.__transmission_type

    def get_seating_capacity(self):
        return self.__seating_capacity

    def get_engine_output(self):
        return self.__engine_output

    def get_stock_quantity(self):
        return self.__stock_quantity

    def set_bike_id(self, bike_id):
        self.__bike_id = bike_id

    def set_bike_name(self, bike_name):
        self.__bike_name = bike_name

    def set_upload_bike_image(self, upload_bike_image):
        self.__upload_bike_image = upload_bike_image

    def set_price(self, price):
        self.__price = price

    def set_transmission_type(self, transmission_type):
        self.__transmission_type = transmission_type

    def set_seating_capacity(self, seating_capacity):
        self.__seating_capacity = seating_capacity

    def set_engine_output(self, engine_output):
        self.__engine_output = engine_output

    def set_stock_quantity(self, stock_quantity):
        self.__stock_quantity = stock_quantity