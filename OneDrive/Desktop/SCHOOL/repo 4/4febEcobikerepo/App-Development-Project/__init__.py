from flask import Flask, render_template, request, session, redirect, url_for, flash, Response, stream_with_context
from forms import LoginForm, RegisterForm, EditUsernameForm, NumberOnlyValidator, FutureDateValidator, CreateDefectForm, UpdateDefectForm, DateSelectionForm, PaymentForm, BikeIDManagementForm, LockUnlockForm,  CreateBikeForm, CreateFAQForm, UpdateFAQForm
from google.auth import exceptions
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
import google.auth.transport.requests
from googleapiclient.discovery import build
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
import random
import shelve
import requests
import json
import re
import gpxpy
import os
import logging
from datetime import datetime
from bikeclass import BikeProduct, Order, carparks
from bikeclass import BikeDefect as createDefect
from User import User, Reward
from math import radians, sin, cos, sqrt, atan2
import os
import time
from faq import FAQ

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # ✅ Allow HTTP in Development Mode

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/uploads'
UPLOAD_FOLDER_PROFILE = 'static/profile_pics'

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Load Gmail API Credentials (Replace with your downloaded JSON file)
GOOGLE_CLIENT_SECRET_FILE = "client_secret.json"
GOOGLE_LOGIN_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]


GOOGLE_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
GOOGLE_REDIRECT_URI = "http://127.0.0.1:5000/google/callback"

ADMIN_EMAIL = 'bryceang2007@gmail.com'
ADMIN_PASSWORD = 'ecobike'
#App password for google: "eesm lpxo pgzm hfcb"

HEADERS = {
    "Authorization": f"Bearer ",
    "Content-Type": "application/json"
}

def clean_ai_response(text):
    """Cleans up AI response by removing unwanted formatting and spaces"""
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    text = re.sub(r'(```[\s\S]*?```)', '', text)  # Remove triple backtick code blocks
    text = re.sub(r'[\*_#]', '', text)  # Remove Markdown symbols
    return text.strip()

def generate_response(user_prompt):
    """Handles AI response streaming from external API with NO context memory"""
    data = {
    "model": AI_MODEL_NAME,
    "prompt": f"This website is ecobike. I will NOT remember previous responses. Answer the following question independently: {user_prompt}",
    "stream": True
    }


    try:
        response = requests.post(AI_API_URL, headers=HEADERS, json=data, stream=True)

        if response.status_code != 200:
            yield "Error: AI server returned an invalid response."
            return

        buffer = ""
        for line in response.iter_lines():
            if request.environ.get('werkzeug.server.shutdown'):  # Detect if request was aborted
                return

            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    chunk_response = data.get('response', '')

                    if chunk_response:
                        buffer += chunk_response

                        words = buffer.split()
                        buffer = words.pop() if words and chunk_response[-1] != ' ' else ""

                        for word in words:
                            yield clean_ai_response(word) + " "

                    if data.get('done'):
                        if buffer:
                            yield clean_ai_response(buffer)
                        return

                except json.JSONDecodeError:
                    yield "Error: Failed to decode AI response."
                    return

    except requests.exceptions.RequestException as e:
        yield f"Error: Could not reach AI API. {str(e)}"

@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_message = request.json.get("message", "").strip()
    
    if not user_message:
        return Response("Please enter a message.", content_type="text/plain")

    return Response(stream_with_context(generate_response(user_message)), content_type="text/plain")

def load_env(file_path=".env"):
    try:
        import os
        full_path = os.path.abspath(file_path)
        print(f"Attempting to load .env from: {full_path}")
        print(f"File exists: {os.path.exists(full_path)}")

        with open(full_path, "r") as env_file:
            for line in env_file:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    print(f"Loading: {key}={value}")
                    os.environ[key.strip()] = value.strip()

        # Verify keys are loaded
        print(f"Loaded Google Maps API Key: {os.getenv('GOOGLE_MAPS_API_KEY')}")
        print(f"Loaded AI API URL: {os.getenv('AI_API_URL')}")
        print(f"Loaded AI Model Name: {os.getenv('AI_MODEL_NAME')}")

    except Exception as e:
        print(f"Detailed Error: {e}")
        print(f"Error Type: {type(e)}")

# Load the .env variables
load_env()

# Access the variables
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
AI_API_URL = os.getenv("AI_API_URL")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME")

def initialize_bike_products():
    """Initialize the bike products database if it doesn't exist."""
    try:
        with shelve.open('bike.db', 'c') as db:
            if 'Bikes' not in db:  # Check if the key exists
                sample_bikes = {
                    1: {
                        "bike_id": 1,
                        "bike_name": "Activa-E",
                        "upload_bike_image": "activa-e.jpg",
                        "price": 30.00,
                        "transmission_type": "Manual",
                        "seating_capacity": 1,
                        "engine_output": "700W",
                        "stock_quantity": 15,
                    },
                    2: {
                        "bike_id": 2,
                        "bike_name": "Ecima",
                        "upload_bike_image": "ecima.jpg",
                        "price": 45.00,
                        "transmission_type": "Manual",
                        "seating_capacity": 1,
                        "engine_output": "900W",
                        "stock_quantity": 17,
                    },
                    3: {
                        "bike_id": 3,
                        "bike_name": "EV Urban",
                        "upload_bike_image": "ev-urban.jpg",
                        "price": 65.00,
                        "transmission_type": "Manual",
                        "seating_capacity": 1,
                        "engine_output": "1200W",
                        "stock_quantity": 10,
                    },
                    4: {
                        "bike_id": 4,
                        "bike_name": "EV Fun",
                        "upload_bike_image": "ev-fun.jpg",
                        "price": 75.00,
                        "transmission_type": "Manual",
                        "seating_capacity": 1,
                        "engine_output": "1500W",
                        "stock_quantity": 5,
                    },
                    5: {
                        "bike_id": 5,
                        "bike_name": "Energica Eva Ribelle",
                        "upload_bike_image": "energica-eva-ribelle.jpg",
                        "price": 65.00,
                        "transmission_type": "Manual",
                        "seating_capacity": 1,
                        "engine_output": "1250W",
                        "stock_quantity": 15,
                    },
                    6: {
                        "bike_id": 6,
                        "bike_name": "Energica Ego+ RS",
                        "upload_bike_image": "energica-ego-rs.jpg",
                        "price": 65.00,
                        "transmission_type": "Manual",
                        "seating_capacity": 1,
                        "engine_output": "1380W",
                        "stock_quantity": 10,
                    },
                    7: {
                        "bike_id": 7,
                        "bike_name": "Energica Experia",
                        "upload_bike_image": "energica-experia.jpg",
                        "price": 80.00,
                        "transmission_type": "Manual",
                        "seating_capacity": 1,
                        "engine_output": "1500W",
                        "stock_quantity": 10,
                    },
                    8: {
                        "bike_id": 8,
                        "bike_name": "Energica Esse Esse",
                        "upload_bike_image": "energica-esse-esse.jpg",
                        "price": 85.00,
                        "transmission_type": "Manual",
                        "seating_capacity": 1,
                        "engine_output": "1500W",
                        "stock_quantity": 10,
                    },
                }
                db['Bikes'] = sample_bikes  # Initialize with sample data
                logging.info("Bike products database created and initialized.")
            else:
                logging.info("Bike products already exist in the database.")
    except Exception as e:
        logging.error(f"Error initializing bike products: {e}")


def get_bike_data():
    """Retrieve bike data, reinitialize if missing."""
    try:
        with shelve.open('bike.db', 'c') as db:
            if 'Bikes' not in db:
                initialize_bike_products()  # Reinitialize
            return db.get('Bikes', {})
    except Exception as e:
        logging.error(f"Error accessing bike database: {e}")
        return {}


def extract_gpx_details(gpx_file_path):
    try:
        with open(gpx_file_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)

        total_distance = 0
        start_time = None
        end_time = None
        carbon_emission_factor = 0.1  # kg CO2 per km

        for track in gpx.tracks:
            for segment in track.segments:
                for i in range(len(segment.points) - 1):
                    point1 = segment.points[i]
                    point2 = segment.points[i + 1]

                    # Calculate distance between points
                    total_distance += point1.distance_3d(point2)

                # Capture start and end time
                if segment.points:
                    if not start_time:
                        start_time = segment.points[0].time
                    end_time = segment.points[-1].time

        # Calculate total duration in hours
        if start_time and end_time and start_time < end_time:
            total_time = (end_time - start_time).total_seconds() / 3600  # Hours
        else:
            total_time = 0

        # Calculate average speed (safe check for zero time)
        # Only consider the first `speed` or `extensions` entry for speed, if available.
        avg_speed = sum([point.speed for point in segment.points if point.speed]) / len(segment.points) if segment.points else 0

        # Convert distance to kilometers
        total_distance_km = total_distance / 1000

        # Calculate total carbon emissions
        total_carbon_emissions = total_distance_km * carbon_emission_factor

        print(f"Total distance: {total_distance_km} km, Total time: {total_time} hours, Average speed: {avg_speed} km/h")

        return {
            "total_distance": round(total_distance_km, 2),
            "avg_speed": round(avg_speed, 2),
            "duration": f"{int(total_time)} hours {int((total_time % 1) * 60)} mins" if total_time > 0 else "N/A",
            "carbon_emissions": round(total_carbon_emissions, 2)
        }
    except Exception as e:
        print(f"Error processing GPX file: {e}")
        return {"total_distance": 0, "avg_speed": 0, "duration": "N/A", "carbon_emissions": 0}

def generate_svg_points(gpx_file_path):
    try:
        with open(gpx_file_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)

        # Debugging: Print parsed GPX structure
        print(f"GPX Tracks: {len(gpx.tracks)}")
        for track in gpx.tracks:
            print(f"Track: {track.name}, Segments: {len(track.segments)}")
            for segment in track.segments:
                print(f"Segment Points: {len(segment.points)}")

        # Extract route coordinates
        route_coordinates = [
            (point.latitude, point.longitude)
            for track in gpx.tracks
            for segment in track.segments
            for point in segment.points
        ]

        # Debugging: Print extracted coordinates
        print(f"Route Coordinates: {route_coordinates}")

        if not route_coordinates:
            print("No route coordinates found in the GPX file.")
            return ""

        # Calculate bounding box
        min_lat = min(coord[0] for coord in route_coordinates)
        max_lat = max(coord[0] for coord in route_coordinates)
        min_lon = min(coord[1] for coord in route_coordinates)
        max_lon = max(coord[1] for coord in route_coordinates)

        # Debugging: Print bounding box details
        print(f"Bounds: min_lat={min_lat}, max_lat={max_lat}, min_lon={min_lon}, max_lon={max_lon}")

        if min_lat == max_lat or min_lon == max_lon:
            print("Invalid bounding box for route.")
            return ""

        # Generate SVG points
        width_scale = 200  # Scaling factors
        height_scale = 150

        svg_points = " ".join([
            f"{((lon - min_lon) / (max_lon - min_lon) * width_scale)},{(max_lat - lat) / (max_lat - min_lat) * height_scale}"
            for lat, lon in route_coordinates
        ])

        # Debugging: Print SVG points
        print(f"Generated SVG Points: {svg_points}")
        return svg_points

    except Exception as e:
        print(f"Error generating SVG points: {e}")
        return ""


@app.route('/createBike', methods=['GET', 'POST'])
def create_bike():
    create_bike_form = CreateBikeForm(request.form)

    if request.method == 'POST' and create_bike_form.validate():
        db = shelve.open('bike.db', 'c')
        bikes_dict = db.get('Bikes', {})

        file = request.files.get('upload_bike_image')
        filename = ''
        if file and file.filename != '':
            from werkzeug.utils import secure_filename
            filename = secure_filename(file.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        bike_id = len(bikes_dict) + 1
        bike_data = {
            "bike_id": bike_id,
            "bike_name": create_bike_form.bike_name.data,
            "upload_bike_image": filename,
            "price": float(create_bike_form.price.data),
            "transmission_type": create_bike_form.transmission_type.data,
            "seating_capacity": create_bike_form.seating_capacity.data,
            "engine_output": create_bike_form.engine_output.data,
            "stock_quantity": int(create_bike_form.stock_quantity.data),
        }

        bikes_dict[bike_id] = bike_data
        db['Bikes'] = bikes_dict
        db.close()

        flash("Bike created successfully!", "success")
        return redirect(url_for('retrieve_bikes'))
    return render_template('createBike.html', form=create_bike_form)



@app.route('/retrieveBikes')
def retrieve_bikes():
    bikes_dict = get_bike_data()
    return render_template(
        'retrieveBikes.html',
        count=len(bikes_dict),
        bikes=bikes_dict
    )


@app.route('/updateBike/<int:id>/', methods=['GET', 'POST'])
def update_bike(id):
    update_bike_form = CreateBikeForm(request.form)

    # Open the database
    with shelve.open('bike.db', 'c') as db:
        bikes_dict = db.get('Bikes', {})
        bike = bikes_dict.get(id)

        if not bike:
            flash("Bike not found.", "error")
            return redirect(url_for('retrieve_bikes'))

        if request.method == 'POST' and update_bike_form.validate():
            # Update bike details
            bike["bike_name"] = update_bike_form.bike_name.data
            bike["price"] = float(update_bike_form.price.data)
            bike["transmission_type"] = update_bike_form.transmission_type.data
            bike["seating_capacity"] = update_bike_form.seating_capacity.data
            bike["engine_output"] = update_bike_form.engine_output.data
            bike["stock_quantity"] = int(update_bike_form.stock_quantity.data)

            # Handle image upload
            file = request.files.get('upload_bike_image')
            if file and file.filename != '':
                # Remove old image if it exists
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], bike.get("upload_bike_image", ""))
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)

                # Save new image
                from werkzeug.utils import secure_filename
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                bike["upload_bike_image"] = filename

            # Save updated bike to the database
            bikes_dict[id] = bike
            db['Bikes'] = bikes_dict

            flash("Bike updated successfully!", "success")
            return redirect(url_for('retrieve_bikes'))

        # Pre-fill the form with existing bike details
        update_bike_form.bike_name.data = bike["bike_name"]
        update_bike_form.price.data = bike["price"]
        update_bike_form.transmission_type.data = bike["transmission_type"]
        update_bike_form.seating_capacity.data = bike["seating_capacity"]
        update_bike_form.engine_output.data = bike["engine_output"]
        update_bike_form.stock_quantity.data = bike["stock_quantity"]

    return render_template('updateBikes.html', form=update_bike_form, bike=bike)


@app.route('/viewBikes')
def view_bikes():
    try:
        # Initialize the database if missing
        initialize_bike_products()

        # Open the database to retrieve bikes
        with shelve.open('bike.db', 'r') as db:
            bikes = db.get('Bikes', {})
        return render_template('viewBikes.html', count=len(bikes), bikes=bikes)
    except Exception as e:
        logging.error(f"Error in view_bikes: {e}")
        flash("Error retrieving bikes", "error")
        return redirect(url_for('home'))


@app.route('/deleteBike/<int:id>/', methods=['POST'])
def delete_bike(id):
    db = shelve.open('bike.db', 'c')
    bikes_dict = db.get('Bikes', {})

    if id in bikes_dict:
        del bikes_dict[id]
        db['Bikes'] = bikes_dict
        flash("Bike deleted successfully!", "success")
    else:
        flash("Bike not found.", "error")

    db.close()
    return redirect(url_for('retrieve_bikes'))

@app.route('/dashboard', methods=['GET'])
def user_dashboard():
    user_email = session.get('user_id')  # Ensure session holds email

    print(f"Dashboard accessed by user: {user_email}")

    with shelve.open('dashboard_data.db') as db:
        user_data = db.get('user_data', {}).get(user_email, {
            "files": [],
            "gpx_details": {
                "total_distance": 0,
                "avg_speed": 0,
                "carbon_emissions": 0,
                "duration": "N/A"
            }
        })

    svg_points = ""
    if user_data["files"]:
        last_uploaded_file = user_data["files"][-1]["file_path"]
        svg_points = generate_svg_points(last_uploaded_file)

    carbon_emissions = user_data["gpx_details"].get("carbon_emissions", 0)

        # Fetch leaderboard
    with shelve.open('leaderboard_data.db') as leaderboard_db:
        leaderboard = leaderboard_db.get('leaderboard', [])

    # Safely access values, ensure all keys exist
    total_miles = user_data["gpx_details"].get("total_distance", 0)
    avg_speed = user_data["gpx_details"].get("avg_speed", 0)
    carbon_emissions = carbon_emissions,
    carbon_emissions = user_data["gpx_details"].get("carbon_emissions", 0)  # Ensure this is always defined
    duration = user_data["gpx_details"].get("duration", "N/A")

    # Pass data to the template
    return render_template(
        'dashboard.html',
        leaderboard=leaderboard,  # Pass leaderboard to template
        svg_points=svg_points,
        total_miles=total_miles,
        avg_speed=avg_speed,
        carbon_emissions=carbon_emissions,
        duration=duration,
        uploaded_files=user_data["files"]
    )

@app.route('/dashBoardAdmin', methods=['GET'])
def dashboard_admin():
    default_gpx_details = {
        "total_distance": 0,
        "avg_speed": 0,
        "carbon_emissions": 0,
        "duration": "N/A"
    }
    bike_count = 0

    with shelve.open('dashboard_data.db') as db:
        gpx_details = db.get('gpx_details', default_gpx_details)
        bike_count = db.get('bike_count', 0)

    return render_template(
        'dashBoardAdmin.html',
        gpx_details=gpx_details,
        bike_count=bike_count
    )



@app.route('/resetDashboard', methods=['POST'])
def reset_dashboard():
    # Path to the shelve database
    shelve_path = 'dashboard_data.db'

    # Reset the shelve database
    with shelve.open(shelve_path, writeback=True) as db:
        db.clear()  # Clear all existing data
        db['gpx_details'] = {
            "total_distance": 0,
            "avg_speed": 0,
            "carbon_emissions": 0,
            "duration": 0.0
        }
        db['bike_count'] = 0

    flash("Dashboard has been reset to default values.", "success")
    return redirect('/dashBoardAdmin')


#wk
@app.route('/add_to_cart/<int:bike_id>', methods=['POST'])
def add_to_cart(bike_id):
    try:
        with shelve.open('bike.db', 'c') as db:
            if 'Bikes' not in db:  # If database is empty
                initialize_bike_products()  # Reinitialize
            bikes = db.get('Bikes', {})
            bike = bikes.get(bike_id)

        if not bike:
            flash("Bike not found", "error")
            return redirect(url_for('view_bikes'))

        with shelve.open('cart.db', 'c') as db:
            cart = db.get('cart', {})
            if bike_id in cart:
                cart[bike_id]['quantity'] += 1
            else:
                cart[bike_id] = {'bike': bike, 'quantity': 1}
            db['cart'] = cart

        flash("Bike added to cart successfully!", "success")
        return redirect(url_for('checkout'))

    except Exception as e:
        logging.error(f"Error in add_to_cart: {e}")
        flash("Error adding bike to cart", "error")
        return redirect(url_for('view_bikes'))
    
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    form = DateSelectionForm()
    try:
        with shelve.open('bike.db', 'r') as db:
            bikes = db.get('Bikes', {})
        
        with shelve.open('cart.db', 'r') as db:
            cart = db.get('cart', {})
            
            if not cart:
                flash("No item in cart", "error")
                return redirect(url_for('view_bikes'))
            
            # Get the first (and only) item in the cart
            bike_id = list(cart.keys())[0]
            bike = bikes[bike_id]
            base_price = bike['price']
            
            if form.validate_on_submit():
                days = (form.end_date.data - form.start_date.data).days + 1
                total = base_price * days
                
                session['rental_info'] = {
                    'start_date': form.start_date.data.strftime('%Y-%m-%d'),
                    'end_date': form.end_date.data.strftime('%Y-%m-%d'),
                    'days': days,
                    'total': total
                }
                
                return redirect(url_for('payment'))
            
            return render_template('checkout.html', 
                                 form=form, 
                                 cart_items=[bike], 
                                 total=base_price)
    except Exception as e:
        logging.error(f"Error in checkout: {str(e)}", exc_info=True)
        flash("Error processing checkout", "error")
        return redirect(url_for('view_bikes'))
    
@app.route('/payment', methods=['GET', 'POST'])
def payment():
    form = PaymentForm()
    rental_info = session.get('rental_info')
    
    if not rental_info:
        flash("Please select rental dates first", "error")
        return redirect(url_for('checkout'))
    
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                with shelve.open('cart.db', 'r') as db:
                    cart = db.get('cart', {})
                    if not cart:
                        flash("Cart is empty", "error")
                        return redirect(url_for('view_bikes'))
                    
                # Generate order ID
                order_id = datetime.now().strftime('%Y%m%d%H%M%S')
                
                # Get rental dates from session
                rental_dates = {
                    'start_date': rental_info['start_date'],
                    'end_date': rental_info['end_date'],
                    'days': rental_info['days']
                }
                
                # Store user email in session
                session['user_email'] = form.email.data
                
                # Find nearest carpark if coordinates are provided
                nearest_carpark = None
                if form.latitude.data and form.longitude.data:
                    try:
                        nearest_carpark = find_nearest_carpark(
                            float(form.latitude.data),
                            float(form.longitude.data)
                        )
                    except ValueError as e:
                        logging.error(f"Error finding nearest carpark: {e}")
                        flash("Error processing location data", "error")
                        return render_template('payment.html', form=form, google_maps_api_key=GOOGLE_MAPS_API_KEY)
                
                # Compile customer information
                customer_info = {
                    'full_name': form.full_name.data,
                    'email': form.email.data,
                    'address': form.address.data,
                    'city': form.city.data,
                    'postal_code': form.postal_code.data,
                    'payment_info': {
                        'card_last_4': form.card_no.data[-4:],
                        'exp_date': form.exp_date.data
                    }
                }
                
                # Add carpark information if available
                if nearest_carpark:
                    customer_info['assigned_carpark'] = nearest_carpark
                
                # Create new order
                # In the payment route, modify the order creation section
                order = Order(
                    order_id=order_id,
                    items=dict(cart),  # Keep the entire cart dictionary
                    total=rental_info['total'],
                    customer_info=customer_info,
                    order_date=datetime.now(),
                    rental_dates=rental_dates
                )
                
                # Save order to database
                try:
                    with shelve.open('orders.db', 'c') as db:
                        orders = db.get('orders', {})
                        orders[order_id] = order
                        db['orders'] = orders
                except Exception as e:
                    logging.error(f"Error saving order to database: {e}")
                    flash("Error saving order", "error")
                    return render_template('payment.html', form=form, google_maps_api_key=GOOGLE_MAPS_API_KEY)
                
                # Clear session data
                session.pop('rental_info', None)
                
                # Clean up cart
                try:
                    with shelve.open('cart.db', 'c') as db:
                        if 'cart' in db:
                            del db['cart']
                except Exception as e:
                    logging.error(f"Error clearing cart: {e}")
                
                flash("Order placed successfully!", "success")
                return redirect(url_for('order_confirmation', order_id=order_id))
                
            except Exception as e:
                logging.error(f"Error processing payment: {e}", exc_info=True)
                flash("Error processing payment", "error")
                return render_template('payment.html', form=form, google_maps_api_key=GOOGLE_MAPS_API_KEY)
        else:
            logging.warning(f"Form validation failed: {form.errors}")
            return render_template('payment.html', form=form, google_maps_api_key=GOOGLE_MAPS_API_KEY)

    # GET request - render empty form
    return render_template('payment.html', form=form, google_maps_api_key=GOOGLE_MAPS_API_KEY)
@app.route('/orders')
def view_orders():
    """View all orders"""
    try:
        with shelve.open('orders.db', 'r') as db:
            orders = db.get('orders', {})
            logging.debug(f"Retrieved orders: {orders}")
            if orders:
                # Verify the first order has the required methods for debugging
                first_order = next(iter(orders.values()))
                logging.debug(f"First order attributes: {dir(first_order)}")
            return render_template('orders.html', orders=orders.values()) #renders order page with all orders
    except Exception as e:
        logging.error(f"Error in view_orders: {str(e)}")
        flash("Error viewing orders", "error")
        return redirect(url_for('home'))
                        
@app.route('/order/<order_id>')
def view_order(order_id):
    """View a specific order"""
    try:
        with shelve.open('orders.db', 'r') as db:
            orders = db.get('orders', {}) # Get all orders
            order = orders.get(order_id) # Find specific order
            if order:
                return render_template('order_details.html', order=order, google_maps_api_key=GOOGLE_MAPS_API_KEY)
            flash("Order not found", "error")
    except Exception as e:
        logging.error(f"Error in view_order: {str(e)}", exc_info=True)
        flash("Error retrieving order", "error")
    return redirect(url_for('view_orders'))

@app.route('/order_confirmation/<order_id>') ## just display order dates, duration and ID
def order_confirmation(order_id):
    """Order confirmation page"""
    try:
        with shelve.open('orders.db', 'r') as db:
            orders = db.get('orders', {})
            order = orders.get(order_id)
            if order:
                return render_template('order_confirmation.html', order_id=order_id, order=order, google_maps_api_key=GOOGLE_MAPS_API_KEY)
            flash("Order not found", "error")
    except Exception as e:
        logging.error(f"Error in order_confirmation: {str(e)}", exc_info=True)
        flash("Error retrieving order details", "error")
    return redirect(url_for('home'))

@app.route('/order/<order_id>/edit', methods=['GET', 'POST'])
def edit_order(order_id):
    try:
        with shelve.open('orders.db', 'c') as db:  # Open orders database in write mode
            orders = db.get('orders', {})
            order = orders.get(order_id)
            
            if not order:
                flash("Order not found", "error")
                return redirect(url_for('view_orders'))
            
            if request.method == 'POST':
                try:
                    # Convert string dates to datetime objects
                    start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
                    end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d')
                    
                    # Validate date range
                    if start_date > end_date:
                        flash("Start date must be before end date", "error")
                        return render_template('edit_order.html', order=order)
                    
                    # Calculate new duration
                    days = (end_date - start_date).days + 1
                    
                    # Update order details
                    order.rental_dates['start_date'] = request.form['start_date']
                    order.rental_dates['end_date'] = request.form['end_date']
                    order.rental_dates['days'] = days
                    
                    # Get base price - handle both product and bike scenarios
                    first_item = list(order.items.values())[0]
                    if 'product' in first_item:
                        base_price = first_item['product'].get_price()
                    elif 'bike' in first_item:
                        base_price = first_item['bike'].get('price', 0)
                    else:
                        base_price = 0
                    
                    # Update total based on new duration
                    order.total = base_price * days
                    
                    # Save edited order
                    orders[order_id] = order
                    db['orders'] = orders
                    
                    flash("Order updated successfully!", "success")
                    return redirect(url_for('view_order', order_id=order_id))
                
                except Exception as e:
                    logging.error(f"Error processing order edit: {e}")
                    flash("Error updating order details", "error")
                    return render_template('edit_order.html', order=order)
                
            return render_template('edit_order.html', order=order)
    
    except Exception as e:
        logging.error(f"Error accessing orders database for edit: {e}")
        flash("System error occurred", "error")
        return redirect(url_for('view_orders'))
        
@app.route('/order/<order_id>/delete', methods=['POST'])
def delete_order(order_id):
    try:
        with shelve.open('orders.db', 'c') as db:  # write mode
            orders = db.get('orders', {})  # get all orders
            
            if order_id in orders:
                # Optional: Implement soft delete or archiving if needed
                deleted_order = orders.pop(order_id)  # delete order
                db['orders'] = orders
                
                # Optional logging of deleted order
                logging.info(f"Order {order_id} deleted. Original order details: {deleted_order.get_order_id()}")
                
                flash("Order deleted successfully!", "success")
            else:
                flash("Order not found", "error")
            
            return redirect(url_for('view_orders'))
    
    except Exception as e:
        logging.error(f"Error deleting order {order_id}: {e}")
        flash("Error deleting order", "error")
        return redirect(url_for('view_orders'))    

def find_nearest_carpark(latitude, longitude):
    """
    Find the nearest carpark to the given coordinates using a simple distance calculation.
    """
    if not latitude or not longitude:
        return None
        
    def calculate_distance(lat1, lng1, lat2, lng2):
        # Simple Euclidean distance - for more accuracy, you might want to use haversine formula
        return ((lat1 - lat2) ** 2 + (lng1 - lng2) ** 2) ** 0.5
    
    nearest_carpark = None
    min_distance = float('inf')
    
    for carpark_id, carpark_data in carparks.items():
        # Since your carpark data is in [name, lat, lng] format
        name = carpark_data[0]
        carpark_lat = carpark_data[1]
        carpark_lng = carpark_data[2]
        
        distance = calculate_distance(
            float(latitude),
            float(longitude),
            carpark_lat,
            carpark_lng
        )
        
        if distance < min_distance:
            min_distance = distance
            nearest_carpark = {
                'id': carpark_id,
                'name': name,
                'distance': distance,
                'coordinates': {'lat': carpark_lat, 'lng': carpark_lng}
            }
    
    return nearest_carpark
@app.route('/initializeBikeIDs', methods=['GET'])
def initialize_bike_ids():
    try:
        # Open bike.db to get products
        with shelve.open('bike.db', 'r') as bike_db:
            bikes = bike_db.get('Bikes', {})
            if not bikes:
                flash("No bikes found in bike.db to initialize IDs.", "error")
                return redirect(url_for('manage_ids'))

        # Open or create bike_ids.db
        with shelve.open('bike_ids.db', 'c') as bike_id_db:
            bike_ids = bike_id_db.get('bike_ids', {})

            # Initialize bike IDs if not already present
            for bike_id, bike in bikes.items():
                bike_name = bike['bike_name']
                stock_quantity = bike['stock_quantity']

                # Generate a unique Bike ID (e.g., first 3 letters of the name + an ID)
                unique_id = f"{bike_name[:3].upper()}-{bike_id:03d}"

                if unique_id not in bike_ids:
                    bike_ids[unique_id] = {
                        'name': bike_name,
                        'stock': stock_quantity,
                        'rental': 0,
                    }
                    print(f"Added new bike: {unique_id} with stock {stock_quantity}")

            # Save back to the database
            bike_id_db['bike_ids'] = bike_ids

        flash("Bike IDs initialized or updated successfully!", "success")
    except Exception as e:
        logging.error(f"Error initializing bike IDs: {e}")
        flash("Error initializing bike IDs", "error")

    return redirect(url_for('manage_ids'))

@app.route('/debugBikeDB', methods=['GET'])
def debug_bike_db():
    with shelve.open('bike.db', 'r') as bike_db:
        bikes = bike_db.get('Bikes', {})
        return f"<pre>{bikes}</pre>"

@app.route('/manageBikeIDs', methods=['GET', 'POST'])
def manage_ids():
    form = BikeIDManagementForm()
    try:
        # Ensure bike_ids.db exists and initialize if needed
        with shelve.open('bike_ids.db', 'c') as bike_id_db:
            if 'bike_ids' not in bike_id_db or not bike_id_db['bike_ids']:
                initialize_bike_ids()  # Initialize bike IDs from bike.db

            # Get the bike_ids
            bike_ids = bike_id_db['bike_ids']

        # Prepare bike_inventory for rendering
        bike_inventory = []
        for id_string, data in bike_ids.items():
            bike_inventory.append({
                'id': id_string,
                'name': data['name'],
                'stock': data['stock'],
                'rental': data['rental'],
            })

    except Exception as e:
        logging.error(f"Error in manage_ids route: {e}")
        flash("Error retrieving or saving bike IDs", "error")
        bike_inventory = []

    return render_template('manage_ids.html', form=form, bike_inventory=bike_inventory)


@app.route('/editBikeID/<id_string>', methods=['GET', 'POST'])
def edit_bike_id(id_string):
    form = BikeIDManagementForm()

    try:
        with shelve.open('bike_ids.db', 'c') as bike_id_db:
            bike_ids = bike_id_db.get('bike_ids', {})
            bike_id_data = bike_ids.get(id_string)

            if not bike_id_data:
                flash("Bike ID not found.", "error")
                return redirect(url_for('manage_ids'))

            if request.method == 'POST' and form.validate_on_submit():
                new_id = form.id_string.data
                bike_name = form.bike_name.data
                stock_quantity = form.stock_quantity.data

                # Remove the old ID if it has been changed
                if new_id != id_string:
                    del bike_ids[id_string]

                # Update the bike ID data
                bike_ids[new_id] = {
                    'name': bike_name,
                    'stock': stock_quantity,
                    'rental': bike_id_data['rental'],  # Preserve rental count
                }
                bike_id_db['bike_ids'] = bike_ids  # Save changes

                flash("Bike ID updated successfully!", "success")
                return redirect(url_for('manage_ids'))

            # Pre-fill the form with the existing data
            form.id_string.data = id_string
            form.bike_name.data = bike_id_data['name']
            form.stock_quantity.data = bike_id_data['stock']

    except Exception as e:
        logging.error(f"Error editing bike ID: {e}")
        flash("Error editing bike ID.", "error")

    return render_template('edit_bike_id.html', form=form)



@app.route('/deleteBikeID/<id_string>', methods=['POST'])
def delete_bike_id(id_string):
    try:
        with shelve.open('bike_ids.db', 'c') as bike_id_db:
            bike_ids = bike_id_db.get('bike_ids', {})
            if id_string in bike_ids:
                del bike_ids[id_string]  # Remove the bike ID
                bike_id_db['bike_ids'] = bike_ids
                flash("Bike ID deleted successfully!", "success")
            else:
                flash("Bike ID not found.", "error")

    except Exception as e:
        logging.error(f"Error deleting bike ID: {e}")
        flash("Error deleting bike ID.", "error")

    return redirect(url_for('manage_ids'))

@app.route('/unlock', methods=['GET', 'POST'])
def unlock_bike():
    form = LockUnlockForm()
    if form.validate_on_submit():
        try:
            bike_id = form.bike_id.data.upper()
            user_email = session.get('user_email')

            if not user_email:
                flash('Please create an order first', 'error')
                return render_template('unlock.html', form=form)

            # Get bike ID data
            with shelve.open('bike_ids.db', 'c') as db:
                bike_ids = db.get('bike_ids', {})
                if bike_id not in bike_ids:
                    flash('Invalid bike ID', 'error')
                    return render_template('unlock.html', form=form)

                bike_info = bike_ids[bike_id]
                bike_name = bike_info['name']

            # Get product data and check stock
            with shelve.open('bike.db', 'c') as db:
                bikes = db.get('Bikes', {})
                product = None
                for bike in bikes.values():
                    if bike['bike_name'] == bike_name:
                        product = bike
                        break

                if not product:
                    flash('Product not found', 'error')
                    return render_template('unlock.html', form=form)

                if product['stock_quantity'] <= 0:
                    flash('No bikes available for this model', 'error')
                    return render_template('unlock.html', form=form)

            # Verify rental status
            with shelve.open('orders.db', 'r') as db:
                orders = db.get('orders', {})
                has_valid_rental = False
                for order in orders.values():
                    if (order.get_customer_info()['email'] == user_email and
                        any(item['bike']['bike_name'] == bike_name for item in order.get_items().values())):
                        has_valid_rental = True
                        break

                if not has_valid_rental:
                    flash('No active rental found for this bike', 'error')
                    return render_template('unlock.html', form=form)

            # Process unlock
            if bike_info.get('status') == 'unlocked':
                flash('Bike is already unlocked', 'error')
                return render_template('unlock.html', form=form)

            # Update bike attributes
            update_bike_attributes_in_both_dbs(bike_name, -1, 1)  # Decrease stock, increase rental

            # Update bike status
            with shelve.open('bike_ids.db', 'c') as db:
                bike_ids = db.get('bike_ids', {})
                bike_ids[bike_id]['status'] = 'unlocked'
                bike_ids[bike_id]['current_user'] = user_email
                db['bike_ids'] = bike_ids

            flash('Bike unlocked successfully!', 'success')
            return redirect(url_for('lock_success'))


            # Update product stock and rental count
            with shelve.open('bike.db', 'c') as db:
                bikes = db.get('Bikes', {})
                for bike_id, bike in bikes.items():
                    if bike['bike_name'] == bike_name:
                        bike['stock_quantity'] -= 1
                        bike['rental'] = bike.get('rental', 0) + 1  # Ensure 'rental' exists and increment it
                        break
                db['Bikes'] = bikes

            flash('Bike unlocked successfully!', 'success')
            return redirect(url_for('lock_success'))

        except Exception as e:
            logging.error(f"Error in unlock_bike: {str(e)}")
            flash('Error processing request', 'error')

    return render_template('unlock.html', form=form)


@app.route('/lock', methods=['GET', 'POST'])
def lock_bike():
    form = LockUnlockForm()
    if form.validate_on_submit():
        try:
            bike_id = form.bike_id.data.upper()
            user_email = session.get('user_email')

            # Get bike ID data
            with shelve.open('bike_ids.db', 'c') as db:
                bike_ids = db.get('bike_ids', {})
                if bike_id not in bike_ids:
                    flash('Invalid bike ID', 'error')
                    return render_template('lock.html', form=form)

                bike_info = bike_ids[bike_id]
                bike_name = bike_info['name']

            # Get product data
            with shelve.open('bike.db', 'c') as db:
                bikes = db.get('Bikes', {})
                product = None
                for bike in bikes.values():
                    if bike['bike_name'] == bike_name:
                        product = bike
                        break

                if not product:
                    flash('Product not found', 'error')
                    return render_template('lock.html', form=form)

                # Verify current user
                if bike_info.get('current_user') != user_email:
                    flash('You are not the current user of this bike', 'error')
                    return render_template('lock.html', form=form)

                # Update bike attributes
                update_bike_attributes_in_both_dbs(bike_name, 1, -1)  # Increase stock, decrease rental

                # Update bike status
                with shelve.open('bike_ids.db', 'c') as db:
                    bike_ids = db.get('bike_ids', {})
                    bike_ids[bike_id]['status'] = 'locked'
                    bike_ids[bike_id]['current_user'] = None
                    db['bike_ids'] = bike_ids

                flash('Bike locked successfully!', 'success')
                return redirect(url_for('lock_success'))

            # Update product stock
            with shelve.open('bike.db', 'c') as db:
                bikes = db.get('Bikes', {})
                for bike_id, bike in bikes.items():
                    if bike['bike_name'] == bike_name:
                        bike['stock_quantity'] += 1
                        bike['rental'] = max(bike.get('rental', 0) - 1, 0)  # Ensure rental count does not go below 0
                        break
                db['Bikes'] = bikes

            flash('Bike locked successfully!', 'success')
            return redirect(url_for('lock_success'))

        except Exception as e:
            logging.error(f"Error in lock_bike: {str(e)}")
            flash('Error processing request', 'error')

    return render_template('lock.html', form=form)

def update_bike_attributes_in_both_dbs(bike_name, stock_change, rental_change):
    """Update stock and rental attributes in both bike.db and bike_ids.db."""
    # Update attributes in bike.db
    with shelve.open('bike.db', 'c') as db:
        bikes = db.get('Bikes', {})
        for bike_id, bike in bikes.items():
            if bike['bike_name'] == bike_name:
                bike['stock_quantity'] += stock_change
                bike['rental'] = bike.get('rental', 0) + rental_change
                bikes[bike_id] = bike
                break
        db['Bikes'] = bikes

    # Update attributes in bike_ids.db
    with shelve.open('bike_ids.db', 'c') as db:
        bike_ids = db.get('bike_ids', {})
        for id_string, data in bike_ids.items():
            if data['name'] == bike_name:
                data['stock'] += stock_change
                data['rental'] += rental_change
                bike_ids[id_string] = data
                break
        db['bike_ids'] = bike_ids


@app.route('/lock-success')
def lock_success():
    return render_template('lock_success.html')


#bryce
#User-management

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

db_path = os.path.join(os.getcwd(), 'users_db')

rewards_db_path = 'rewards.db'

# Ensure the credentials JSON file exists
if not os.path.exists(GOOGLE_CLIENT_SECRET_FILE):
    raise FileNotFoundError("Google Client Secret file not found!")

def get_google_login_flow():
    return Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRET_FILE,
        scopes=GOOGLE_LOGIN_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI
    )

def get_gmail_flow():
    return Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRET_FILE,
        scopes=GOOGLE_GMAIL_SCOPES,
        redirect_uri="http://127.0.0.1:5000/gmail/callback"
    )


# ✅ Google Login Route
@app.route("/login/google")
def google_login():
    """Redirects the user to Google's OAuth consent screen for login."""
    flow = get_google_login_flow()  # ✅ Initialize flow correctly
    authorization_url, state = flow.authorization_url()
    session["state"] = state  # ✅ Store state for security
    return redirect(authorization_url)


# ✅ Google Login Callback Route
@app.route("/google/callback")
def google_callback():
    try:
        # ✅ Ensure a new OAuth flow instance is created
        flow = get_google_login_flow()

        # ✅ Fetch token correctly
        flow.fetch_token(authorization_response=request.url)

        # ✅ Retrieve token credentials
        credentials = flow.credentials
        request_session = google.auth.transport.requests.Request()

        # ✅ Adjust for clock skew to prevent timing errors
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            request_session,
            flow.client_config["client_id"],
            clock_skew_in_seconds=10  # ✅ Allow up to 10 seconds time difference
        )

        # ✅ Extract user information from Google token
        google_email = id_info["email"]
        google_name = id_info["name"]
        google_picture = id_info.get("picture", "default.jpg")

        # ✅ Store user information in session
        session["user_id"] = google_email
        session["username"] = google_name
        session["profile_picture"] = google_picture
        session["is_admin"] = False  # Default role

        # ✅ Store user in database if they don’t exist
        with shelve.open("users_db", writeback=True) as db:
            if google_email not in db:
                db[google_email] = {
                    "email": google_email,
                    "username": google_name,
                    "profile_picture": google_picture,
                    "is_admin": False
                }

        flash("Successfully logged in with Google!", "success")
        return redirect(url_for("user_dashboard"))

    except google.auth.exceptions.InvalidValue as e:
        flash(f"Google login failed: {e}", "danger")
        return redirect(url_for("login"))

    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
        return redirect(url_for("login"))



# ✅ Google Gmail API Callback Route
@app.route("/authorize_gmail")
def authorize_gmail():
    """Redirects the user to Google's OAuth consent screen for Gmail API authorization."""
    flow = get_gmail_flow()
    authorization_url, state = flow.authorization_url()
    session["state"] = state  # ✅ Store state for security
    return redirect(authorization_url)

@app.route("/gmail/callback")
def gmail_callback():
    """Handles Gmail API authentication and stores credentials."""
    try:
        flow = get_gmail_flow()
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        # ✅ Ensure credentials are not None before saving
        if not credentials or not credentials.token:
            flash("Failed to retrieve credentials. Try again.", "danger")
            return redirect(url_for("authorize_gmail"))

        session["gmail_credentials"] = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }

        # ✅ Save Gmail API credentials
        with shelve.open("users_db", writeback=True) as db:
            user_data = db.get(session.get("user_id"), {})
            user_data["gmail_credentials"] = session["gmail_credentials"]
            db[session.get("user_id")] = user_data

        flash("Google Gmail API Access Granted!", "success")
        return redirect(url_for("forgot_password"))

    except Exception as e:
        flash(f"Gmail API authorization failed: {e}", "danger")
        return redirect(url_for("forgot_password"))




def datenow():
    return str(int(time.time()))

def init_admin():
    try:
        with shelve.open(db_path, flag='c') as db:
            if ADMIN_EMAIL not in db:
                admin_password_hash = User.hash_password(ADMIN_PASSWORD)
                # Set is_admin=True when creating admin user
                admin_user = User(ADMIN_EMAIL, 'admin', admin_password_hash, is_admin=True)
                db[ADMIN_EMAIL] = admin_user.to_dict()
    except Exception as e:
        print(f"Error initializing admin: {str(e)}")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    try:
        init_admin()  # Ensure admin initialization
        if 'user_id' in session:
            if session.get('is_admin'):
                return redirect(url_for('admin'))
            return render_template('home.html')
        return render_template('home.html')
    except Exception as e:
        logging.error(f"Unexpected error in home route: {e}")
        flash("An unexpected error occurred.", "danger")
        return redirect(url_for('home'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with shelve.open('users_db', writeback=True) as db:
        user_data = db.get(session['user_id'])

        if not user_data:
            flash("User not found. Please log in again.", "danger")
            return redirect(url_for('login'))

        user = User.from_dict(user_data)

        if request.method == 'POST':
            if 'profile_picture' not in request.files:
                flash('No file selected.', 'danger')
                return redirect(url_for('settings'))

            file = request.files['profile_picture']
            if file.filename == '':
                flash('No file selected.', 'danger')
                return redirect(url_for('settings'))

            if file and allowed_file(file.filename):
                # ✅ Delete old profile picture if it exists
                old_picture = user.get_profile_picture()
                old_picture_path = os.path.join('static/profile_pics', old_picture)
                if os.path.exists(old_picture_path) and old_picture != "helmet_pfp.jpg":
                    os.remove(old_picture_path)

                # ✅ Save new profile picture using user_id instead of email
                file_extension = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"{session['user_id']}.{file_extension}")
                file_path = os.path.join('static/profile_pics', filename)
                file.save(file_path)

                # ✅ Update user profile picture in database
                user.set_profile_picture(filename)
                db[session['user_id']] = user.to_dict()

                # ✅ Refresh session with the new profile picture
                session['profile_picture'] = filename

                flash('Profile picture updated successfully!', 'success')
                return redirect(url_for('settings'))

    return render_template('settings.html', user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']

            with shelve.open(db_path) as db:
                user_data = db.get(email)
                if not user_data:
                    flash('Email not found.', 'danger')
                    return redirect(url_for('login'))

                user = User.from_dict(user_data)
                if not user.check_password(password):
                    flash('Incorrect password.', 'danger')
                    return redirect(url_for('login'))

                # ✅ Store profile picture in session
                session['user_id'] = email
                session['is_admin'] = user.is_admin()
                session['profile_picture'] = user.get_profile_picture()  # ✅ Ensure profile picture persists

                return redirect(url_for('admin' if user.is_admin() else 'user_dashboard'))

        return render_template('login.html')

    except IOError as e:
        logging.error(f"Database read error: {e}")
        flash("An error occurred while accessing user data.", "danger")
    except Exception as e:
        logging.error(f"Unexpected error in login route: {e}")
        flash("An unexpected error occurred.", "danger")

    return redirect(url_for('login'))


def authenticate_gmail():
    """Authenticate using OAuth 2.0 and return a Gmail API service."""
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)  # Opens a browser for authentication
    return build('gmail', 'v1', credentials=creds)


# ✅ Send Email Using Gmail API
def send_email_gmail(to_email, subject, body):
    """Send an email using the Gmail API."""
    credentials_data = session.get("gmail_credentials")
    if not credentials_data:
        flash("Please authorize Gmail API first!", "warning")
        return False

    try:
        credentials = google.oauth2.credentials.Credentials(**credentials_data)
        service = build("gmail", "v1", credentials=credentials)

        message = MIMEMultipart()
        message["to"] = to_email
        message["subject"] = subject
        message.attach(MIMEText(body, "plain"))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw_message}).execute()

        flash("OTP has been sent successfully!", "success")
        return True

    except Exception as e:
        flash(f"Failed to send OTP: {e}", "danger")
        return False



@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]

        # ✅ Ensure Gmail API is authorized before sending OTP
        if "gmail_credentials" not in session:
            flash("Please authorize Gmail API first!", "warning")
            return redirect(url_for("authorize_gmail"))

        if send_otp(email):
            return redirect(url_for("verify_otp"))

    return render_template("forgot_password.html")


def send_otp(email):
    """Sends OTP via Gmail API if authorized and stores it in session."""
    if "gmail_credentials" not in session:
        flash("Please authorize Gmail API first!", "warning")
        return False

    try:
        credentials = google.oauth2.credentials.Credentials(**session["gmail_credentials"])
        service = build("gmail", "v1", credentials=credentials)

        otp = str(random.randint(100000, 999999))  # ✅ Generate OTP
        session["otp"] = otp
        session["otp_email"] = email
        session["otp_expiry"] = time.time() + 300  # ✅ OTP expires in 5 minutes

        # ✅ Construct email message
        message = MIMEMultipart()
        message["to"] = email
        message["subject"] = "Your Ecobike OTP"
        body = f"Your OTP for password reset is: {otp}\nThis OTP will expire in 5 minutes."
        message.attach(MIMEText(body, "plain"))

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": encoded_message}).execute()

        flash("OTP sent successfully! Check your email.", "success")
        return True

    except Exception as e:
        flash(f"Failed to send OTP: {e}", "danger")
        return False



@app.route("/verify_otp", methods=["GET", "POST"])  # ✅ Ensure GET & POST are allowed
def verify_otp():
    """Verifies the OTP entered by the user."""
    if request.method == "GET":
        return render_template("verify_otp.html")  # ✅ Render OTP form for GET requests

    entered_otp = request.form.get("otp")  # ✅ Retrieve entered OTP

    # ✅ Ensure OTP exists in session
    if "otp" not in session or "otp_email" not in session or "otp_expiry" not in session:
        flash("OTP expired or not found. Please request a new one.", "danger")
        return redirect(url_for("forgot_password"))

    # ✅ Ensure OTP has not expired
    if time.time() > session["otp_expiry"]:
        flash("OTP has expired. Please request a new one.", "danger")
        session.pop("otp", None)  # Remove expired OTP
        session.pop("otp_email", None)
        session.pop("otp_expiry", None)
        return redirect(url_for("forgot_password"))

    # ✅ Verify OTP
    if entered_otp != session["otp"]:
        flash("Invalid OTP. Please try again.", "danger")
        return redirect(url_for("verify_otp"))

    # ✅ OTP is correct, proceed to reset password
    flash("OTP verified successfully! You may now reset your password.", "success")
    return redirect(url_for("reset_password"))




@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    """Allows users to reset their password after OTP verification."""
    if "otp_email" not in session:
        flash("Session expired. Please request a new OTP.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # ✅ Ensure passwords match
        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("reset_password"))

        # ✅ Retrieve user from the database
        with shelve.open("users_db", writeback=True) as db:
            if session["otp_email"] not in db:
                flash("User not found.", "danger")
                return redirect(url_for("forgot_password"))

            user_data = db[session["otp_email"]]
            user = User.from_dict(user_data)

            # ✅ Use the new `set_password` method
            user.set_password(new_password)

            # ✅ Save updated user data
            db[session["otp_email"]] = user.to_dict()

        # ✅ Clear OTP session data
        session.pop("otp", None)
        session.pop("otp_email", None)
        session.pop("otp_expiry", None)

        flash("Password reset successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html")




# ✅ Logout Route (Clears Session)
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        with shelve.open(db_path) as db:
            if email in db:
                flash('Email already registered.', 'danger')
                return redirect(url_for('register'))

            # Create a new user and save to the database
            user = User(
                email=email,
                username=username,
                password=User.hash_password(password),
                user_id=datenow(),
                is_admin=False
            )
            db[email] = user.to_dict()

        # Add new user to leaderboard (if applicable)
        with shelve.open('leaderboard_data.db', writeback=True) as leaderboard_db:
            if 'leaderboard' not in leaderboard_db:
                leaderboard_db['leaderboard'] = []

            leaderboard = leaderboard_db['leaderboard']
            leaderboard.append({
                "name": username,
                "avatar": username[0].upper(),
                "color": "#FF5733",  # Assign a default color
                "change": "new"  # Mark as a new entry
            })
            leaderboard_db['leaderboard'] = leaderboard

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    try:
        with shelve.open(db_path) as db:
            current_time = time.time()
            users = []
            regular_users_count = 0
            active_users_count = 0
            thirty_days_ago = current_time - (30 * 24 * 3600)
            past_regular_count = 0
            past_active_count = 0

            for email, user_data in db.items():
                user = User.from_dict(user_data)
                is_active = (current_time - user.get_last_login()) <= (30 * 24 * 3600)
                users.append((
                    user.get_username(),
                    user.get_user_id(),
                    email,
                    'active' if is_active else 'inactive',
                    user.is_admin(),
                    user.get_points()
                ))

                if not user.is_admin():
                    regular_users_count += 1
                    if is_active:
                        active_users_count += 1
                    if user.get_last_login() < thirty_days_ago:
                        past_regular_count += 1
                        if current_time - user.get_last_login() <= (60 * 24 * 3600):
                            past_active_count += 1

            try:
                total_growth = int(((regular_users_count - past_regular_count) / max(past_regular_count, 1)) * 100)
                active_growth = int(((active_users_count - past_active_count) / max(past_active_count, 1)) * 100)
                current_month_rides = 680  # Placeholder value
                last_month_rides = 354  # Placeholder value
                rides_growth = int(((current_month_rides - last_month_rides) / max(last_month_rides, 1)) * 100)
            except ZeroDivisionError:
                flash("Insufficient data to calculate growth percentages.", "warning")
                total_growth = active_growth = rides_growth = 0

            stats = {
                'totalUsers': regular_users_count,
                'activeUsers': active_users_count,
                'monthlyRides': current_month_rides,
                'activePercentage': int(
                    (active_users_count / regular_users_count * 100) if regular_users_count > 0 else 0),
                'totalGrowth': total_growth,
                'activeGrowth': active_growth,
                'ridesGrowth': rides_growth
            }
        return render_template('admin.html', users=users, stats=stats)
    except IOError as e:
        logging.error(f"Database access error in admin: {e}")
        flash("Error accessing the database.", "danger")
    except Exception as e:
        logging.error(f"Unexpected error in admin route: {e}")
        flash("An unexpected error occurred.", "danger")
    return redirect(url_for('home'))

@app.route('/view_users')
def view_users():
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Unauthorized access!", "danger")
        return redirect(url_for('login'))

    users_list = []
    with shelve.open(db_path) as db:
        for email, user_data in db.items():
            user = User.from_dict(user_data)
            users_list.append(user)

    return render_template('view_users.html', users=users_list)


@app.route('/edit_points/<user_id>', methods=['POST'])
def edit_points(user_id):
    """Admin updates user points."""
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    try:
        with shelve.open(db_path) as db:
            for email, user_data in db.items():
                user = User.from_dict(user_data)
                if user.get_user_id() == user_id:
                    try:
                        new_points = int(request.form['new_points'])
                        user.set_points(new_points)
                        db[email] = user.to_dict()

                        # ✅ Flash message now includes username
                        flash(f'User "{user.get_username()}" points updated to {new_points}.', "success")

                    except ValueError:
                        flash("Invalid point value. Please enter a valid number.", "danger")
                    break

    except IOError as e:
        logging.error(f"Database access error in edit_points: {e}")
        flash("Error accessing the database.", "danger")

    except Exception as e:
        logging.error(f"Unexpected error in edit_points: {e}")
        flash("An unexpected error occurred.", "danger")

    return redirect(url_for('admin'))



@app.route('/rewards', methods=['GET', 'POST'])
def rewards():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with shelve.open(db_path) as db:
        user_data = db[session['user_id']]
        user = User.from_dict(user_data)
        points = user.get_points()

    with shelve.open(rewards_db_path, writeback=True) as db:
        rewards_dict = db.get('rewards', {})
        rewards = {key: Reward.from_dict(data) for key, data in rewards_dict.items()}

        # ✅ Reverse history to show the most recent first
        history = list(reversed(db.get(session['user_id'], [])))



        # ✅ Define reward images dictionary
        reward_images = {
            'voucher': 'images/voucher.png',
            'tree_donation': 'images/plant-tree.png',
            'reusable_bag': 'images/tote-bag.png',
            'eco_plush': 'images/motorbike-plush.png',
            'keychain': 'images/helmet-keychain.png'
        }

    return render_template('rewards.html', points=points, rewards=rewards, history=history, is_admin=session.get('is_admin'), reward_images=reward_images)


def initialize_rewards():
    """Initialize the rewards database if not already set."""
    with shelve.open(rewards_db_path, 'c') as db:
        if 'rewards' not in db:  # Only initialize if missing
            default_rewards = {
                'voucher': Reward('$1 Voucher', 100),
                'reusable_bag': Reward('Reusable Bag', 300),
                'eco_plush': Reward('Eco-friendly Plush', 500),
                'keychain': Reward('Keychain', 150),
                'tree_donation': Reward('Tree Donation', 100),
            }
            db['rewards'] = {key: reward.to_dict() for key, reward in default_rewards.items()}

@app.route('/redeem/<reward_type>', methods=['POST'])
def redeem_reward(reward_type):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with shelve.open(rewards_db_path, writeback=True) as db:
        rewards_dict = db.get('rewards', {})
        if reward_type not in rewards_dict:
            flash('Invalid reward selection.', 'danger')
            return redirect(url_for('rewards'))

        reward = Reward.from_dict(rewards_dict[reward_type])
        cost = reward.get_cost()

        # ✅ Check if the reward is in stock
        if reward.get_stock() <= 0:
            flash("This reward is out of stock!", "danger")
            return redirect(url_for('rewards'))

    with shelve.open(db_path, writeback=True) as db:
        user_data = db[session['user_id']]
        user = User.from_dict(user_data)

        # ✅ Ensure user has enough points
        if user.get_points() < cost:
            flash("Insufficient points.", "danger")
            return redirect(url_for('rewards'))

        # ✅ Deduct points and decrease stock
        user.redeem_points(cost)
        reward.set_stock(reward.get_stock() - 1)  # ✅ Reduce stock by 1

        # ✅ Update database
        db[session['user_id']] = user.to_dict()
        with shelve.open(rewards_db_path, writeback=True) as db_rewards:
            db_rewards['rewards'][reward_type] = reward.to_dict()

    # ✅ Log the reward redemption in history
    with shelve.open(rewards_db_path, writeback=True) as db:
        if session['user_id'] not in db:
            db[session['user_id']] = []
        db[session['user_id']].append({
            'reward': reward.get_name(),
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'points_used': cost
        })

    flash(f"Successfully redeemed {reward.get_name()}!", "success")
    return redirect(url_for('rewards'))

@app.route('/update_reward_stock', methods=['POST'])
def update_reward_stock():
    """Admin updates reward stock."""
    if 'user_id' not in session or not session.get('is_admin'):
        flash("Unauthorized access!", "danger")
        return redirect(url_for('rewards'))

    reward_id = request.form.get("reward_id")
    new_stock = request.form.get("stock")

    if not reward_id or new_stock is None:
        flash("Invalid reward update request.", "danger")
        return redirect(url_for("rewards"))

    try:
        new_stock = int(new_stock)
        if new_stock < 0:
            flash("Stock cannot be negative.", "danger")
            return redirect(url_for("rewards"))

        with shelve.open(rewards_db_path, writeback=True) as db:
            rewards_dict = db.get("rewards", {})

            if reward_id not in rewards_dict:
                flash("Invalid reward selection.", "danger")
                return redirect(url_for("rewards"))

            reward = Reward.from_dict(rewards_dict[reward_id])
            reward.set_stock(new_stock)
            rewards_dict[reward_id] = reward.to_dict()
            db["rewards"] = rewards_dict

        # ✅ Flash message now includes reward name
        flash(f'Stock for "{reward.get_name()}" updated to {new_stock}.', "success")

    except ValueError:
        flash("Invalid stock value. Please enter a valid number.", "danger")

    return redirect(url_for("rewards"))



@app.route('/rewards/history')
def rewards_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    with shelve.open(rewards_db_path) as db:
        history = db.get(session['user_id'], [])

    return render_template('history.html', history=history)
@app.route('/edit/<user_id>', methods=['GET', 'POST'])
def edit(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    with shelve.open(db_path) as db:

        target_email = None
        for email, user_data in db.items():
            user = User.from_dict(user_data)
            if user.get_user_id() == user_id:
                target_email = email
                break
        else:
            flash('User not found.')
            return redirect(url_for('admin'))

        if request.method == 'POST':
            new_username = request.form['username']

            #
            if any(User.from_dict(u_data).get_username() == new_username
                   and User.from_dict(u_data).get_user_id() != user_id
                   for u_data in db.values()):
                flash('Username already taken.')
                return redirect(url_for('edit', user_id=user_id))

            user.set_username(new_username)
            db[target_email] = user.to_dict()
            flash('Username updated successfully.')
            return redirect(url_for('admin'))

        return render_template('edit.html', user_id=user_id, username=user.get_username())


@app.route('/delete/<user_id>', methods=['POST'])
def delete(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    with shelve.open(db_path) as db:
        for email, user_data in list(db.items()):
            user = User.from_dict(user_data)
            if user.get_user_id() == user_id:
                del db[email]
                flash(f'User "{user.get_username()}" deleted successfully.', "danger")
                break

    return redirect(url_for('admin'))


@app.route('/add_admin', methods=['POST'])
def add_admin():
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    email = request.form['email']
    username = request.form['username']
    password = request.form['password']
    confirm_password = request.form['confirm_password']

    if password != confirm_password:
        flash('Passwords do not match.', "danger")
        return redirect(url_for('admin'))

    with shelve.open(db_path) as db:
        if email in db:
            flash('Email already registered.', "danger")
            return redirect(url_for('admin'))

        if any(User.from_dict(user_data).get_username() == username
               for user_data in db.values()):
            flash('Username already taken.', "danger")
            return redirect(url_for('admin'))

        user = User(
            email=email,
            username=username,
            password=User.hash_password(password),
            user_id=datenow(),
            is_admin=True
        )
        db[email] = user.to_dict()
        flash(f'Admin user "{username}" created successfully.', "success")
        return redirect(url_for('admin'))



@app.route("/toggle_admin/<user_id>", methods=["POST"])
def toggle_admin(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    with shelve.open(db_path) as db:
        for email, user_data in db.items():
            user = User.from_dict(user_data)
            if user.get_user_id() == user_id:
                # Prevent self-demotion
                if email == session['user_id']:
                    flash('You cannot change your own admin status.', "danger")
                    return redirect(url_for('admin'))

                user.set_admin(not user.is_admin())
                db[email] = user.to_dict()

                # ✅ Flash message now includes username
                if user.is_admin():
                    flash(f'User "{user.get_username()}" promoted to admin.', "success")
                else:
                    flash(f'User "{user.get_username()}" demoted from admin.', "warning")

                break

    return redirect(url_for('admin'))


#Rais
@app.route('/createDefect', methods=['GET', 'POST'])
def create_defect():
    create_defect_form = CreateDefectForm(request.form)
    if request.method == 'POST' and create_defect_form.validate():
        try:
            with shelve.open('defect.db', 'c') as db:
                defects_dict = db.get('Defects', {})
                defect = createDefect(
                    create_defect_form.bike_id.data.upper(),
                    create_defect_form.defect_type.data,
                    create_defect_form.date_found.data,
                    create_defect_form.bike_location.data,
                    create_defect_form.severity.data,
                    create_defect_form.description.data
                )
                defects_dict[defect.get_report_id()] = defect
                db['Defects'] = defects_dict

            bike_id = create_defect_form.bike_id.data.upper()

            # Reduce stock when defect is reported
            with shelve.open('bike.db', 'c') as db:
                bikes = db.get('Bikes', {})
                for key, bike in bikes.items():
                    if bike['bike_name'].upper() == bike_id:
                        bike['stock_quantity'] -= 1
                        break
                db['Bikes'] = bikes

            with shelve.open('bike_ids.db', 'c') as db:
                bike_ids = db.get('bike_ids', {})
                if bike_id in bike_ids and bike_ids[bike_id]['stock'] > 0:
                    bike_ids[bike_id]['stock'] -= 1
                    db['bike_ids'] = bike_ids

            flash("Defect reported successfully! Stock updated in all views.", "success")
            return redirect(url_for('success'))
        except Exception as e:
            logging.error(f"Error reporting defect: {e}")
            flash("An error occurred while reporting the defect.", "error")
    return render_template('createDefect.html', form=create_defect_form)


def load_env(file_path=".env"):
    try:
        with open(file_path, "r") as env_file:
            for line in env_file:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
        app.config['GOOGLE_MAPS_API_KEY'] = os.getenv("GOOGLE_MAPS_API_KEY")  # Add API key to app config
    except Exception as e:
        print(f"Error loading environment variables: {e}")



@app.route('/success')
def success():
    return render_template('success.html')


@app.route('/updateDefect/<int:id>', methods=['GET', 'POST'])
def update_defect(id):
    update_defect_form = UpdateDefectForm(request.form)
    defects_dict = {}

    with shelve.open('defect.db', 'c') as db:
        defects_dict = db.get('Defects', {})
        defect = defects_dict.get(id)

    if not defect:
        flash("Defect not found.", "error")
        return redirect(url_for('retrieve_defect'))

    if request.method == 'POST' and update_defect_form.validate():
        try:
            new_status = update_defect_form.status.data
            old_status = defect.get_status()

            defect.set_status(new_status)
            defects_dict[id] = defect
            with shelve.open('defect.db', 'c') as db:
                db['Defects'] = defects_dict

            bike_id = defect.get_bike_id().upper()

            if old_status != "Repaired" and new_status == "Repaired":
                # Increase stock when defect is marked as repaired
                with shelve.open('bike.db', 'c') as db:
                    bikes = db.get('Bikes', {})
                    for key, bike in bikes.items():
                        if bike['bike_name'].upper() == bike_id:
                            bike['stock_quantity'] += 1
                            break
                    db['Bikes'] = bikes

                with shelve.open('bike_ids.db', 'c') as db:
                    bike_ids = db.get('bike_ids', {})
                    if bike_id in bike_ids:
                        bike_ids[bike_id]['stock'] += 1
                        db['bike_ids'] = bike_ids

            flash("Defect status updated successfully! Stock adjusted in all views.", "success")
            return redirect(url_for('retrieve_defect'))
        except Exception as e:
            logging.error(f"Error updating defect status: {e}")
            flash("An error occurred while updating the defect status.", "error")

    update_defect_form.status.data = defect.get_status()
    return render_template('updateDefect.html', form=update_defect_form, defect=defect)


@app.route('/retrieveDefect', methods=['GET', 'POST'])
def retrieve_defect():
    defects_dict = {}
    search_bike_id = request.form.get('search_bike_id', '').strip().upper()

    with shelve.open('defect.db', 'c') as db:
        defects_dict = db.get('Defects', {})

    defects_list = list(defects_dict.values())

    if search_bike_id:
        try:
            filtered_defects = [defect for defect in defects_list if defect.get_bike_id().upper() == search_bike_id]
            if not filtered_defects:
                flash("No defects found for the entered Bike ID.", "error")
            return render_template('retrieveDefect.html', defects_list=filtered_defects, count=len(filtered_defects))
        except Exception as e:
            logging.error(f"Error searching for Bike ID: {e}")
            flash("An error occurred while searching.", "error")

    return render_template('retrieveDefect.html', defects_list=defects_list, count=len(defects_list))


@app.route('/deleteDefect/<int:id>', methods=['POST'])
def delete_defect(id):
    with shelve.open('defect.db', 'c') as db:
        defects_dict = db.get('Defects', {})
        defect = defects_dict.get(id)

        if defect:
            if defect.get_status() in ["Repaired", "Closed"]:
                del defects_dict[id]
                db['Defects'] = defects_dict
                flash("Defect report deleted successfully.", "success")
            else:
                flash("Not allowed to delete while status is Pending.", "error")
        else:
            flash("Defect report not found.", "error")

    return redirect(url_for('retrieve_defect'))


@app.route('/searchUser', methods=['POST'])
def search_user():
    # Ensure the admin is logged in
    if not session.get('is_admin'):
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('home'))

    search_query = request.form.get('search_query', '').lower().strip()
    if not search_query:
        flash('Please enter a valid search query.', 'warning')
        return redirect(url_for('dashboard_admin'))

    # Fetch users from the shelve database
    matching_users = []
    try:
        with shelve.open(db_path) as db:
            for email, user_data in db.items():
                user = User.from_dict(user_data)
                # Check if the user matches the search query
                if search_query in user.get_username().lower() or search_query in email.lower():
                    if not user.is_admin():  # Only show non-admin users
                        matching_users.append({
                            "user_id": user.get_user_id(),
                            "name": user.get_username(),
                            "email": email
                        })

        if not matching_users:
            flash('No users found matching your search query.', 'warning')
            return redirect(url_for('dashboard_admin'))

    except Exception as e:
        flash(f"Error searching for users: {str(e)}", 'danger')
        return redirect(url_for('dashboard_admin'))

    # Render the admin dashboard with search results
    return render_template(
        'dashBoardAdmin.html',
        gpx_details={},  # Keep existing data
        bike_count=0,  # Replace with actual value
        search_results=matching_users
    )

@app.route('/uploadForUser', methods=['POST'])
def upload_for_user():
    user_email = request.form.get('user_id')
    gpx_file = request.files.get('gpx_file')

    if not user_email or not gpx_file:
        flash('Invalid user or file. Please select a user and upload a valid GPX file.', 'danger')
        return redirect(url_for('dashboard_admin'))

    # Save the file
    filename = gpx_file.filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    gpx_file.save(file_path)

    print(f"File uploaded for user {user_email}: {file_path}")  # Debugging

    # Extract GPX details
    gpx_details = extract_gpx_details(file_path)
    svg_points = generate_svg_points(file_path)  # Generate points right after upload

    print(f"SVG Points Generated: {svg_points}")  # Debugging

    if not svg_points:
        flash('No valid route found in the uploaded GPX file.', 'danger')
        return redirect(url_for('dashboard_admin'))

    # Update database
    with shelve.open('dashboard_data.db', writeback=True) as db:
        if 'user_data' not in db:
            db['user_data'] = {}

        if user_email not in db['user_data']:
            db['user_data'][user_email] = {
                "files": [],
                "gpx_details": {
                    "total_distance": 0,
                    "avg_speed": 0,
                    "carbon_emissions": 0,
                    "duration": "N/A"
                }
            }
            if 'gpx_details' not in db:
                db['gpx_details'] = {
                    "total_distance": 0,
                    "avg_speed": 0,
                    "carbon_emissions": 0,
                    "duration": "N/A"
                }

            db['gpx_details']['total_distance'] += gpx_details.get("total_distance", 0)
            db['gpx_details']['avg_speed'] = (
                (db['gpx_details']['avg_speed'] + gpx_details.get("avg_speed", 0)) / 2
                if db['gpx_details']['avg_speed']
                else gpx_details.get("avg_speed", 0)
            )
            db['gpx_details']['carbon_emissions'] += gpx_details.get("carbon_emissions", 0)
            db['gpx_details']['duration'] = gpx_details.get("duration", "N/A")

            # Increment the bike count if applicable
            db['bike_count'] = db.get('bike_count', 0) + 1

        user_data = db['user_data'][user_email]
        user_data["files"].append({
            "file_name": filename,
            "file_path": file_path,
            "svg_points": svg_points,
            "total_distance": gpx_details["total_distance"],
            "avg_speed": gpx_details["avg_speed"],
            "carbon_emissions": gpx_details["carbon_emissions"],
            "duration": gpx_details["duration"]
        })
        user_data["gpx_details"]["total_distance"] += gpx_details["total_distance"]
        user_data["gpx_details"]["avg_speed"] = (
            user_data["gpx_details"]["avg_speed"] + gpx_details["avg_speed"]
        ) / 2
        user_data["gpx_details"]["carbon_emissions"] += gpx_details["carbon_emissions"]
        user_data["gpx_details"]["duration"] = gpx_details["duration"]

        db['user_data'][user_email] = user_data
        print(f"Updated user data for {user_email}: {user_data}")

    flash(f"GPX file uploaded successfully for user {user_email}.", 'success')
    return redirect(url_for('dashboard_admin'))


@app.route('/initialize_user', methods=['POST'])
def initialize_user():
    user_id = session.get('user_id')  # Ensure a valid session exists

    with shelve.open('dashboard_data.db', writeback=True) as db:
        if 'user_data' not in db:
            db['user_data'] = {}

        if user_id not in db['user_data']:
            db['user_data'][user_id] = {
                "files": [],
                "gpx_details": {
                    "total_distance": 0,
                    "avg_speed": 0,
                    "carbon_emissions": 0,
                    "duration": "N/A"
                }
            }
    return redirect(url_for('user_dashboard'))

@app.route('/createFAQ', methods=['GET', 'POST'])
def create_faq():
    create_faq_form = CreateFAQForm(request.form)
    if request.method == 'POST' and create_faq_form.validate():
        faqs_dict = {}
        db = shelve.open('faq.db', 'c')

        try:
            faqs_dict = db['FAQs']
        except:
            print("Error in retrieving FAQs from faq.db.")

        question = create_faq_form.question.data
        answer = create_faq_form.answer.data
        faq = FAQ(question, answer)

        # Set FAQ ID
        faq.set_faq_id(max(faqs_dict.keys(), default=0) + 1)
        faqs_dict[faq.get_faq_id()] = faq
        db['FAQs'] = faqs_dict
        db.close()

        return redirect(url_for('retrieve_faqs'))
    return render_template('createFAQ.html', form=create_faq_form)

@app.route('/faq')
def faq():
    faqs_dict = {}
    try:
        db = shelve.open('faq.db', 'r')
        faqs_dict = db['FAQs']
        db.close()
    except:
        print("Error in retrieving FAQs from faq.db.")

    faqs_list = [faqs_dict[key] for key in faqs_dict]
    return render_template('faq.html', faqs_list=faqs_list)

@app.route('/retrieveFAQ')
def retrieve_faqs():
    faqs_dict = {}
    try:
        db = shelve.open('faq.db', 'r')
        faqs_dict = db['FAQs']
        db.close()
    except:
        print("Error in retrieving FAQs from faq.db.")

    faqs_list = [faqs_dict[key] for key in faqs_dict]
    return render_template('retrieveFAQ.html', faqs_list=faqs_list)

@app.route('/updateFAQ/<int:id>', methods=['GET', 'POST'])
def update_faq(id):
    update_faq_form = UpdateFAQForm(request.form)
    if request.method == 'POST' and update_faq_form.validate():
        db = shelve.open('faq.db', 'w')
        faqs_dict = db['FAQs']
        faq = faqs_dict[id]
        faq.set_question(update_faq_form.question.data)
        faq.set_answer(update_faq_form.answer.data)
        db['FAQs'] = faqs_dict
        db.close()
        return redirect(url_for('retrieve_faqs'))

    db = shelve.open('faq.db', 'r')
    faqs_dict = db['FAQs']
    faq = faqs_dict[id]
    update_faq_form.question.data = faq.get_question()
    update_faq_form.answer.data = faq.get_answer()
    db.close()
    return render_template('updateFAQ.html', form=update_faq_form)

@app.route('/deleteFAQ/<int:id>', methods=['POST'])
def delete_faq(id):
    db = shelve.open('faq.db', 'w')
    faqs_dict = db['FAQs']
    faqs_dict.pop(id, None)
    db['FAQs'] = faqs_dict
    db.close()
    return redirect(url_for('retrieve_faqs'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    initialize_rewards()
    initialize_bike_products()
    app.run(debug=True)