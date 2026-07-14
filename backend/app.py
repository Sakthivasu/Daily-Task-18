import os
from flask import Flask, app, request, jsonify, session
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import mysql.connector
from werkzeug.utils import secure_filename, send_from_directory
from flask import send_from_directory

app = Flask(__name__)

app.secret_key = "change_this_secret_key"

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

bcrypt = Bcrypt(app)

CORS(
    app,
    origins=["http://localhost:5173"],
    supports_credentials=True
)
# Upload folder configuration
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# Route to serve uploaded images
@app.route("/static/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="12345", 
        database="ecommerce"
    )

# --- AUTH ROUTING MODULE ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('name') or not data.get('email') or not data.get('password'):
        return jsonify({"message": "All registration fields are required."}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT id FROM users WHERE email = %s", (data['email'],))
    if cursor.fetchone():
        return jsonify({"message": "Email is already registered."}), 400
        
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    role = data.get('role', 'customer') if data.get('role') in ['customer', 'admin'] else 'customer'
    
    cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
                   (data['name'], data['email'], hashed_password, role))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Account created successfully!"}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM users WHERE email=%s",
        (data["email"],)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user and bcrypt.check_password_hash(
        user["password"],
        data["password"]
    ):
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["role"] = user["role"]
        session.permanent = True

        return jsonify({
    "id": user["id"],
    "name": user["name"],
    "email": user["email"],
    "role": user["role"],
    "avatar_url": user["avatar_url"]
}), 200
    return jsonify({
        "message": "Invalid email or password"
    }), 401


@app.route("/api/logout", methods=["GET"])
def logout():
    session.clear()

    return jsonify({
        "message": "Logged out successfully"
    }), 200

@app.route("/api/me/password", methods=["PUT"])
def change_password():
    if "user_id" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.get_json()

    current_password = data.get("current_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    if not current_password or not new_password or not confirm_password:
        return jsonify({
            "message": "All fields are required"
        }), 400

    if new_password != confirm_password:
        return jsonify({
            "message": "New passwords do not match"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT password FROM users WHERE id=%s",
        (session["user_id"],)
    )

    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return jsonify({
            "message": "User not found"
        }), 404

    if not bcrypt.check_password_hash(
        user["password"],
        current_password
    ):
        cursor.close()
        conn.close()
        return jsonify({
            "message": "Current password is incorrect"
        }), 400

    hashed_password = bcrypt.generate_password_hash(
        new_password
    ).decode("utf-8")

    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET password=%s WHERE id=%s",
        (
            hashed_password,
            session["user_id"]
        )
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Password changed successfully"
    }), 200

@app.route("/api/me", methods=["GET"])
def get_current_user():

    if "user_id" not in session:
        return jsonify({
            "message": "Unauthorized"
        }), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        """
        SELECT id,name,email,role,avatar_url
        FROM users
        WHERE id=%s
        """,
        (session["user_id"],)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify(user), 200

@app.route("/api/me", methods=["PUT"])
def update_profile():
    if "user_id" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json

    # Add this validation here
    if not data.get("name") or not data.get("email"):
        return jsonify({
            "message": "Name and email are required"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET name=%s, email=%s WHERE id=%s",
        (
            data["name"],
            data["email"],
            session["user_id"]
        )
    )

    conn.commit()
    session["user_name"] = data["name"]
    cursor.close()
    conn.close()

    return jsonify({"message": "Profile Updated Successfully"}), 200

@app.route("/api/me/avatar", methods=["PUT"])
def upload_avatar():

    if "user_id" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    if "image" not in request.files:
        return jsonify({"message": "No image"}), 400

    image = request.files["image"]

    filename = secure_filename(image.filename)

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    image.save(filepath)

    avatar_url = f"/static/uploads/{filename}"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET avatar_url=%s WHERE id=%s",
        (avatar_url, session["user_id"])
    )

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        "message": "Avatar updated",
        "avatar_url": avatar_url
    })

# --- PRODUCTS ROUTING MODULE ---

@app.route('/api/products', methods=['GET'])
def get_all_products():
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    sort = request.args.get('sort', 'newest')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT p.*, c.name as category_name 
        FROM products p 
        LEFT JOIN categories c ON p.category_id = c.id 
        WHERE 1=1
    """
    params = []
    
    if category:
        query += " AND c.name = %s"
        params.append(category)
    if search:
        query += " AND (p.name LIKE %s OR p.description LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])
        
    if sort == 'price_asc':
        query += " ORDER BY p.price ASC"
    elif sort == 'price_desc':
        query += " ORDER BY p.price DESC"
    else:
        query += " ORDER BY p.created_at DESC"
        
    cursor.execute(query, params)
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(products), 200

@app.route('/api/products/<int:id>', methods=['GET'])
def get_product_by_id(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT p.*, c.name as category_name FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.id = %s", (id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    if not product:
        return jsonify({"message": "Product item entry matching target ID does not exist."}), 404
    return jsonify(product), 200

@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categories")
    cats = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(cats), 200


# --- ADMIN ONLY: PRODUCTS MODIFICATION CORE ---

@app.route("/api/products", methods=["POST"])
def create_product():
    if session.get("role") != "admin":
        return jsonify({"message": "Forbidden"}), 403

    data = request.json

    # Add this validation here
    required = [
        "name",
        "description",
        "price",
        "stock",
        "category_id",
        "image_url"
    ]

    for field in required:
        if field not in data:
            return jsonify({
                "message": f"{field} is required"
            }), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, description, price, stock, category_id, image_url) VALUES (%s, %s, %s, %s, %s, %s)",
        (
            data["name"],
            data["description"],
            data["price"],
            data["stock"],
            data["category_id"],
            data["image_url"]
        )
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Product created inside catalog database inventory entry."}), 201

@app.route('/api/products/<int:id>', methods=['PUT'])
def update_product(id):
    if session.get('role') != 'admin':
        return jsonify({"message": "Forbidden. Admin access level permissions required."}), 403
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE products SET name=%s, description=%s, price=%s, stock=%s, category_id=%s, image_url=%s WHERE id=%s",
        (data['name'], data['description'], data['price'], data['stock'], data['category_id'], data['image_url'], id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Catalog item metadata updated successfully."}), 200

@app.route('/api/products/<int:id>', methods=['DELETE'])
def delete_product(id):
    if session.get('role') != 'admin':
        return jsonify({"message": "Forbidden. Admin access level permissions required."}), 403
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Product purged from active catalog ledger."}), 200


# --- CUSTOMER ORDER FLOW ROUTING ---

@app.route('/api/orders', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return jsonify({"message": "Authentication state required."}), 401
    data = request.json
    items = data.get('items', [])
    address = data.get('address', '')
    
    if not items or not address:
        return jsonify({"message": "Missing required cart parameters or shipping address data."}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Step 1: Validate stock levels for all requested items
        total_amount = 0
        validated_items = []
        for entry in items:
            cursor.execute("SELECT * FROM products WHERE id = %s", (entry['product_id'],))
            prod = cursor.fetchone()
            if not prod:
                return jsonify({"message": f"Product key {entry['product_id']} not found."}), 400
            if prod['stock'] < entry['qty']:
                return jsonify({"message": f"Operation aborted. '{prod['name']}' is out of stock or requested quantities exceed available inventory storage limits."}), 400
            
            total_amount += float(prod['price']) * int(entry['qty'])
            validated_items.append({"prod": prod, "qty": entry['qty']})
            
        # Step 2: Atomic checkout action execution (Build database records + update inventory metrics)
        cursor.execute("INSERT INTO orders (user_id, total_amount, address, status) VALUES (%s, %s, %s, 'Pending')",
                       (session['user_id'], total_amount, address))
        order_id = cursor.lastrowid
        
        for entry in validated_items:
            # Reduce inventory stocks remaining
            new_stock = entry['prod']['stock'] - entry['qty']
            cursor.execute("UPDATE products SET stock = %s WHERE id = %s", (new_stock, entry['prod']['id']))
            # Insert tracking line items containing point-of-sale pricing capture freeze protections
            cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                           (order_id, entry['prod']['id'], entry['qty'], entry['prod']['price']))
            
        conn.commit()
        return jsonify({"message": "Order tracking transaction complete.", "order_id": order_id}), 201
        
    except Exception as err:
        conn.rollback()
        return jsonify({"message": f"Database processing exception occurred: {str(err)}"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/orders/my', methods=['GET'])
def get_user_orders():
    if 'user_id' not in session:
        return jsonify({"message": "Authentication context required."}), 401
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM orders WHERE user_id = %s ORDER BY ordered_at DESC", (session['user_id'],))
    orders = cursor.fetchall()
    
    for ord in orders:
        cursor.execute("""
            SELECT oi.*, p.name as product_name, p.image_url 
            FROM order_items oi 
            JOIN products p ON oi.product_id = p.id 
            WHERE oi.order_id = %s
        """, (ord['id'],))
        ord['items'] = cursor.fetchall()
        
    cursor.close()
    conn.close()
    return jsonify(orders), 200


# --- ADMIN ONLY: BULK SYSTEM ORDERS MANAGEMENT ---

@app.route('/api/orders', methods=['GET'])
def get_all_system_orders():
    if session.get('role') != 'admin':
        return jsonify({"message": "Forbidden. Admin access level permissions required."}), 403
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT o.*, u.name as customer_name 
        FROM orders o 
        JOIN users u ON o.user_id = u.id 
        ORDER BY o.ordered_at DESC
    """)
    orders = cursor.fetchall()
    
    for ord in orders:
        cursor.execute("""
            SELECT oi.*, p.name as product_name 
            FROM order_items oi 
            JOIN products p ON oi.product_id = p.id 
            WHERE oi.order_id = %s
        """, (ord['id'],))
        ord['items'] = cursor.fetchall()
        
    cursor.close()
    conn.close()
    return jsonify(orders), 200

@app.route('/api/orders/<int:id>/status', methods=['PUT'])
def update_order_status(id):
    if session.get('role') != 'admin':
        return jsonify({"message": "Forbidden. Admin access level permissions required."}), 403
    data = request.json
    new_status = data.get('status')
    if new_status not in ['Pending', 'Confirmed', 'Shipped', 'Delivered', 'Cancelled']:
        return jsonify({"message": "Invalid tracking classification type status syntax string option."}), 400
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, id))
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"message": "Order processing state flag updated globally."}), 200

if __name__ == '__main__':
    app.run(debug=True ,port=5000)