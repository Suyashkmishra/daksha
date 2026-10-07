from flask import Flask, render_template, request, redirect, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = "daksha_hackathon_secret"


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db():

    connection = sqlite3.connect("database.db")

    connection.row_factory = sqlite3.Row

    return connection


# ==========================================
# CREATE DATABASE TABLES
# ==========================================

def create_table():

    connection = get_db()

    # USERS TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            location TEXT
        )
    """)

    # BUSINESSES TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            business_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            location TEXT,
            FOREIGN KEY (owner_id)
            REFERENCES users(id)
        )
    """)

    # PRODUCTS TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            FOREIGN KEY (business_id)
            REFERENCES businesses(id)
        )
    """)
        # REVIEWS TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            review TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(business_id, customer_id),
            FOREIGN KEY (business_id)
            REFERENCES businesses(id),
            FOREIGN KEY (customer_id)
            REFERENCES users(id)
        )
    """)
        # CUSTOMER REQUESTS TABLE
    connection.execute("""
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (business_id)
            REFERENCES businesses(id),
            FOREIGN KEY (customer_id)
            REFERENCES users(id)
        )
    """)

    connection.commit()

    connection.close()


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():

    return render_template("index.html")


# ==========================================
# REGISTER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]

        email = request.form["email"]

        password = request.form["password"]

        role = request.form["role"]

        location = request.form["location"]


        # Encrypt password
        hashed_password = generate_password_hash(password)


        connection = get_db()


        try:

            connection.execute("""
                INSERT INTO users
                (
                    name,
                    email,
                    password,
                    role,
                    location
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                name,
                email,
                hashed_password,
                role,
                location
            ))

            connection.commit()


        except sqlite3.IntegrityError:

            connection.close()

            return "Email already registered!"


        connection.close()


        return redirect("/login")


    return render_template("register.html")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]


        connection = get_db()


        user = connection.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (
            email,
        )).fetchone()


        connection.close()


        # Check login
        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]

            session["name"] = user["name"]

            session["role"] = user["role"]


            # CUSTOMER
            if user["role"] == "customer":

                return redirect("/customer")


            # ENTREPRENEUR
            if user["role"] == "entrepreneur":

                return redirect("/entrepreneur")


        return "Invalid email or password"


    return render_template("login.html")


# ==========================================
# CUSTOMER DASHBOARD
# ==========================================

@app.route("/customer")
def customer():

    if "user_id" not in session:

        return redirect("/login")


    connection = get_db()


    # Get customer information
    customer = connection.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()


    # Get filters
    search = request.args.get(
        "search",
        ""
    ).strip()


    category = request.args.get(
        "category",
        ""
    ).strip()


    location = request.args.get(
        "location",
        ""
    ).strip()


    # Base query
    query = """
        SELECT *
        FROM businesses
        WHERE 1 = 1
    """


    parameters = []


    # SEARCH
    if search:

        query += """
            AND (
                LOWER(business_name) LIKE ?
                OR LOWER(category) LIKE ?
            )
        """


        search_value = "%" + search.lower() + "%"


        parameters.append(search_value)

        parameters.append(search_value)


    # CATEGORY
    if category:

        query += """
            AND category = ?
        """


        parameters.append(category)


    # LOCATION
    if location:

        query += """
            AND LOWER(location) LIKE ?
        """


        parameters.append(
            "%" + location.lower() + "%"
        )


    # Latest businesses first
    query += """
        ORDER BY id DESC
    """


    businesses = connection.execute(
        query,
        parameters
    ).fetchall()


    connection.close()


    return render_template(
        "customer.html",

        name=session["name"],

        businesses=businesses,

        customer_location=(
            customer["location"]
            if customer
            else ""
        )
    )


# ==========================================
# ENTREPRENEUR DASHBOARD
# ==========================================
# ==========================================
# ENTREPRENEUR DASHBOARD
# ==========================================

@app.route("/entrepreneur")
def entrepreneur():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "entrepreneur":
        return redirect("/")

    connection = get_db()

    # Get entrepreneur's business
    business = connection.execute("""
        SELECT *
        FROM businesses
        WHERE owner_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    products = []

    requests = []

    if business:

        # Get products
        products = connection.execute("""
            SELECT *
            FROM products
            WHERE business_id = ?
            ORDER BY id DESC
        """, (
            business["id"],
        )).fetchall()

        # Get customer requests
        requests = connection.execute("""
            SELECT
                requests.*,
                users.name AS customer_name,
                users.email AS customer_email
            FROM requests
            JOIN users
            ON requests.customer_id = users.id
            WHERE requests.business_id = ?
            ORDER BY requests.id DESC
        """, (
            business["id"],
        )).fetchall()

    connection.close()

    return render_template(
        "entrepreneur.html",
        name=session["name"],
        business=business,
        products=products,
        requests=requests
    )


# ==========================================
# DAKSHA GROW
# ==========================================

@app.route("/grow")
def grow():

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "entrepreneur":
        return redirect("/")

    connection = get_db()

    # Get entrepreneur's business
    business = connection.execute("""
        SELECT *
        FROM businesses
        WHERE owner_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    products = []

    if business:

        products = connection.execute("""
            SELECT *
            FROM products
            WHERE business_id = ?
        """, (
            business["id"],
        )).fetchall()

    connection.close()

    # --------------------------------
    # CALCULATE BUSINESS GROWTH SCORE
    # --------------------------------

    score = 0

    if business:

        # Business profile
        score += 30

        # Description
        if business["description"]:
            score += 15

        # Location
        if business["location"]:
            score += 15

        # Category
        if business["category"]:
            score += 10

        # At least one product
        if len(products) >= 1:
            score += 20

        # Three or more products
        if len(products) >= 3:
            score += 10

    # --------------------------------
    # GROWTH MESSAGE
    # --------------------------------

    if score >= 80:

        growth_message = "Excellent! Your business is ready to reach more customers."

    elif score >= 60:

        growth_message = "Good progress! A few improvements can help your business grow."

    elif score >= 30:

        growth_message = "You have started well. Complete your profile and add more products."

    else:

        growth_message = "Start by creating your business profile."


    return render_template(
        "grow.html",
        name=session["name"],
        business=business,
        products=products,
        score=score,
        growth_message=growth_message
    )

# ==========================================
# CREATE BUSINESS
# ==========================================

@app.route(
    "/create-business",
    methods=["GET", "POST"]
)
def create_business():

    if "user_id" not in session:

        return redirect("/login")


    if session.get("role") != "entrepreneur":

        return redirect("/")


    if request.method == "POST":

        business_name = request.form[
            "business_name"
        ]

        category = request.form[
            "category"
        ]

        description = request.form[
            "description"
        ]

        location = request.form[
            "location"
        ]


        connection = get_db()


        connection.execute("""
            INSERT INTO businesses
            (
                owner_id,
                business_name,
                category,
                description,
                location
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            business_name,
            category,
            description,
            location
        ))


        connection.commit()

        connection.close()


        return redirect("/entrepreneur")


    return render_template(
        "create_business.html"
    )


# ==========================================
# ADD PRODUCT
# ==========================================

@app.route(
    "/add-product",
    methods=["GET", "POST"]
)
def add_product():

    if "user_id" not in session:

        return redirect("/login")


    if session.get("role") != "entrepreneur":

        return redirect("/")


    connection = get_db()


    # Find entrepreneur's business
    business = connection.execute("""
        SELECT *
        FROM businesses
        WHERE owner_id = ?
    """, (
        session["user_id"],
    )).fetchone()


    # Business does not exist
    if not business:

        connection.close()

        return redirect("/create-business")


    # Add product
    if request.method == "POST":

        name = request.form["name"]

        description = request.form[
            "description"
        ]

        price = request.form["price"]


        connection.execute("""
            INSERT INTO products
            (
                business_id,
                name,
                description,
                price
            )
            VALUES (?, ?, ?, ?)
        """, (
            business["id"],
            name,
            description,
            price
        ))


        connection.commit()

        connection.close()


        return redirect("/entrepreneur")


    connection.close()


    return render_template(
        "add_product.html",

        business=business
    )


# ==========================================
# BUSINESS PROFILE
# ==========================================

# ==========================================
# BUSINESS PROFILE
# ==========================================

@app.route("/business/<int:business_id>")
def business_profile(business_id):

    if "user_id" not in session:
        return redirect("/login")

    connection = get_db()

    # Get business
    business = connection.execute("""
        SELECT *
        FROM businesses
        WHERE id = ?
    """, (
        business_id,
    )).fetchone()

    # Get products
    products = connection.execute("""
        SELECT *
        FROM products
        WHERE business_id = ?
        ORDER BY id DESC
    """, (
        business_id,
    )).fetchall()

    # Get reviews
    reviews = connection.execute("""
        SELECT
            reviews.*,
            users.name AS customer_name
        FROM reviews
        JOIN users
        ON reviews.customer_id = users.id
        WHERE reviews.business_id = ?
        ORDER BY reviews.id DESC
    """, (
        business_id,
    )).fetchall()

    # Calculate average rating
    rating_result = connection.execute("""
        SELECT
            AVG(rating) AS average_rating,
            COUNT(*) AS review_count
        FROM reviews
        WHERE business_id = ?
    """, (
        business_id,
    )).fetchone()

    connection.close()

    if not business:
        return "Business not found", 404

    average_rating = rating_result["average_rating"]

    if average_rating:
        average_rating = round(average_rating, 1)
    else:
        average_rating = 0

    return render_template(
        "business.html",
        business=business,
        products=products,
        reviews=reviews,
        average_rating=average_rating,
        review_count=rating_result["review_count"]
    )
    # ==========================================
# CUSTOMER REQUEST
# ==========================================

@app.route(
    "/business/<int:business_id>/request",
    methods=["POST"]
)
def customer_request(business_id):

    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "customer":
        return redirect(
            "/business/" + str(business_id)
        )

    message = request.form["message"].strip()

    if not message:
        return "Please enter a message."

    connection = get_db()

    business = connection.execute("""
        SELECT *
        FROM businesses
        WHERE id = ?
    """, (
        business_id,
    )).fetchone()

    if not business:
        connection.close()
        return "Business not found", 404

    connection.execute("""
        INSERT INTO requests
        (
            business_id,
            customer_id,
            message
        )
        VALUES (?, ?, ?)
    """, (
        business_id,
        session["user_id"],
        message
    ))

    connection.commit()

    connection.close()

    return redirect(
        "/business/" + str(business_id)
    )
    # ==========================================
# ADD REVIEW
# ==========================================

@app.route(
    "/business/<int:business_id>/review",
    methods=["POST"]
)
def add_review(business_id):

    if "user_id" not in session:
        return redirect("/login")

    # Only customers can review
    if session.get("role") != "customer":
        return redirect(
            "/business/" + str(business_id)
        )

    rating = request.form["rating"]

    review_text = request.form["review"].strip()

    # Make sure rating is valid
    try:
        rating = int(rating)
    except ValueError:
        return "Invalid rating", 400

    if rating < 1 or rating > 5:
        return "Rating must be between 1 and 5", 400

    connection = get_db()

    # Check that business exists
    business = connection.execute("""
        SELECT *
        FROM businesses
        WHERE id = ?
    """, (
        business_id,
    )).fetchone()

    if not business:
        connection.close()
        return "Business not found", 404

    # Prevent entrepreneur from reviewing own business
    if business["owner_id"] == session["user_id"]:
        connection.close()
        return "You cannot review your own business."

    # Check whether customer already reviewed
    existing_review = connection.execute("""
        SELECT *
        FROM reviews
        WHERE business_id = ?
        AND customer_id = ?
    """, (
        business_id,
        session["user_id"]
    )).fetchone()

    if existing_review:
        connection.close()
        return "You have already reviewed this business."

    # Save review
    connection.execute("""
        INSERT INTO reviews
        (
            business_id,
            customer_id,
            rating,
            review
        )
        VALUES (?, ?, ?, ?)
    """, (
        business_id,
        session["user_id"],
        rating,
        review_text
    ))

    connection.commit()

    connection.close()

    return redirect(
        "/business/" + str(business_id)
    )

# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":

    create_table()

    app.run(
        debug=True
    )