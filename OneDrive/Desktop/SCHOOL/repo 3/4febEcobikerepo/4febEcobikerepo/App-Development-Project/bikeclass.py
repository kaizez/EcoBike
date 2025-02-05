import hashlib
import time


# Define the Order class
class Order:
    """Class to represent an order"""
    def __init__(self, order_id, items, total, customer_info, order_date, rental_dates=None):
        self.order_id = order_id
        self.items = items
        self.total = total
        self.customer_info = customer_info
        self.order_date = order_date
        self.rental_dates = rental_dates if rental_dates is not None else {}

    def get_order_id(self):
        return self.order_id

    def get_items(self):
        return self.items

    def get_total(self):
        return self.total

    def get_customer_info(self):
        return self.customer_info

    def get_order_date(self):
        return self.order_date
    
    def get_rental_dates(self):
        return self.rental_dates

    def get_bike_names(self):
        """Extract bike names from items"""
        return [item.get('bike', {}).get('bike_name', 'Unknown Bike') for item in self.items.values()]

    @property
    def customer_name(self):
        """Extract customer name from customer info"""
        return self.customer_info.get('full_name', 'Unknown Customer')
        
class BikeProduct:
    count_id = 0

    def __init__(self, bike_name, upload_bike_image, price, transmission_type, seating_capacity, engine_output, stock_quantity):
        BikeProduct.count_id += 1
        self.__bike_id = BikeProduct.count_id
        self.__bike_name = bike_name
        self.__upload_bike_image = upload_bike_image
        self.__price = price
        self.__transmission_type = transmission_type
        self.__seating_capacity = seating_capacity
        self.__engine_output = engine_output
        self.__stock_quantity = stock_quantity
        self.__rental = 0

    # Getter methods
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

    def get_rental(self):
        return self.__rental

    # Setter methods
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

    # Rental management methods
    def increase_rental(self):
        if self.__stock_quantity > 0:
            self.__stock_quantity -= 1
            self.__rental += 1
            return True
        return False

    def decrease_rental(self):
        if self.__rental > 0:
            self.__rental -= 1
            self.__stock_quantity += 1
            return True
        return False
            
carparks = {
    1: ["Orchard Central Carpark", 1.3016, 103.8396],
    2: ["ION Orchard Carpark", 1.3040, 103.8318],
    3: ["Marina Bay Sands Carpark", 1.2833, 103.8606],
    4: ["Gardens by the Bay Carpark", 1.2816, 103.8636],
    5: ["VivoCity Carpark", 1.2646, 103.8238],
    6: ["Yio Chu Kang MRT Carpark", 1.3812, 103.8444],
    7: ["Toa Payoh Central Carpark", 1.3324, 103.8484],
    8: ["Bishan Junction 8 Carpark", 1.3508, 103.8485],
    9: ["Yishun MRT Carpark", 1.4291, 103.8357],
    10: ["Khatib MRT Carpark", 1.4172, 103.8335],
    11: ["HDB Carpark Blk 570 Ang Mo Kio Ave 3", 1.3725, 103.8498],
    12: ["HDB Carpark Blk 562 Ang Mo Kio Ave 3", 1.3723, 103.8490],
    13: ["HDB Carpark Blk 550 Ang Mo Kio Ave 3", 1.3717, 103.8501],
    14: ["HDB Carpark Blk 547 Ang Mo Kio Ave 10", 1.3720, 103.8507],
    15: ["HDB Carpark Blk 501 Ang Mo Kio Ave 3", 1.3734, 103.8516],
    16: ["HDB Carpark Blk 556 Ang Mo Kio Ave 3", 1.3729, 103.8493],
    17: ["NYP Campus Carpark A", 1.3771, 103.8485],
    18: ["NYP Campus Carpark B", 1.3768, 103.8500],
    19: ["HDB Carpark Blk 511 Ang Mo Kio Ave 8", 1.3765, 103.8483],
    20: ["HDB Carpark Blk 544 Ang Mo Kio Ave 10", 1.3716, 103.8510],
    21: ["Plaza Singapura Carpark", 1.3009, 103.8451],
    22: ["Bugis Junction Carpark", 1.2990, 103.8550],
    23: ["Clarke Quay Central Carpark", 1.2885, 103.8486],
    24: ["East Coast Park Carpark", 1.3032, 103.9068],
    25: ["Tampines Mall Carpark", 1.3537, 103.9456],
    26: ["JCube Carpark", 1.3331, 103.7401],
    27: ["Bukit Panjang Plaza Carpark", 1.3782, 103.7642],
    28: ["IMM Building Carpark", 1.3342, 103.7463],
    29: ["City Square Mall Carpark", 1.3117, 103.8565],
    30: ["Paya Lebar Quarter Carpark", 1.3174, 103.8934]
}

class BikeDefect:
    count_id = 0

    def __init__(self, bike_id, defect_type, date_found, bike_location, severity, description):
        BikeDefect.count_id += 1
        self.__bike_id = bike_id
        self.__defect_type = defect_type
        self.__date_found = date_found
        self.__bike_location = bike_location
        self.__severity = severity
        self.__description = description
        self.__status = "Pending"  # Default status
        self.__report_id = BikeDefect.count_id

    # Add new getters
    def get_status(self):
        return self.__status

    def get_report_id(self):
        return self.__report_id

    # Add status setter
    def set_status(self, status):
        self.__status = status

    # Existing getters/setters remain the same
    def get_bike_id(self):
        return self.__bike_id

    def get_defect_type(self):
        return self.__defect_type

    def get_date_found(self):
        return self.__date_found

    def get_bike_location(self):
        return self.__bike_location

    def get_severity(self):
        return self.__severity

    def get_description(self):
        return self.__description

