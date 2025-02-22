from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt

app = Flask(__name__)

# Database Configuration (Switch to PostgreSQL for production)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///farmers_marketplace.db'  
# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://username:password@localhost/farmers_marketplace'
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a secure key

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)
    is_farmer = db.Column(db.Boolean, default=False)  # Identifies farmers vs. consumers

# Stock Model (For Farmers)
class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Cart Model (For Businessmen)
class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    consumer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home Page
@app.route('/')
def index():
    stocks = Stock.query.all()  # Show all available stock
    return render_template('index.html', stocks=stocks)

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login Successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Credentials', 'danger')
            return redirect(url_for('register'))

    return render_template('login.html')

# Register Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        is_farmer = True if request.form.get('is_farmer') == 'on' else False

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'warning')
            return redirect(url_for('dashboard'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password, is_farmer=is_farmer)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration Successful! You can log in now.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Dashboard (Farmer or Consumer)
@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_farmer:
        stocks = Stock.query.filter_by(farmer_id=current_user.id).all()
        return render_template('dashboard_farmer.html', user=current_user, stocks=stocks)
    else:
        stocks = Stock.query.all()
        return render_template('dashboard_consumer.html', user=current_user, stocks=stocks)

# Add Stock (Only for Farmers)
@app.route('/add_stock', methods=['GET', 'POST'])
@login_required
def add_stock():
    if not current_user.is_farmer:
        flash("Only farmers can add stock!", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        product_name = request.form['product_name']
        quantity = request.form['quantity']
        price = request.form['price']

        new_stock = Stock(product_name=product_name, quantity=quantity, price=price, farmer_id=current_user.id)
        db.session.add(new_stock)
        db.session.commit()

        flash("Stock added successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('add_stock.html')

# 🛒 Purchase Page (For Businessmen)
@app.route('/purchase')
@login_required
def purchase():
    return render_template('business_purchases.html')
"""    if current_user.is_farmer:
        flash("Farmers cannot purchase products!", "danger")
        return redirect(url_for('purchase'))

    stocks = Stock.query.all()"""

# Add to Cart
@app.route('/add_to_cart/<int:stock_id>', methods=['POST'])
@login_required
def add_to_cart(stock_id):
    if current_user.is_farmer:
        flash("Farmers cannot add products to cart!", "danger")
        return redirect(url_for('dashboard'))

    stock = Stock.query.get_or_404(stock_id)
    quantity = int(request.form['quantity'])
    if quantity > stock.quantity:
        flash("Not enough stock available!", "danger")
        return redirect(url_for('purchase'))

    total_price = stock.price * quantity
    cart_item = Cart(consumer_id=current_user.id, stock_id=stock.id, quantity=quantity, total_price=total_price)
    db.session.add(cart_item)
    db.session.commit()

    flash("Product added to cart!", "success")
    return redirect(url_for('purchase'))

# Cart Page
@app.route('/cart')
@login_required
def cart():
    cart_items = Cart.query.filter_by(consumer_id=current_user.id).all()
    total_amount = sum(item.total_price for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total_amount=total_amount)

# Checkout Route
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(consumer_id=current_user.id).all()
    total_amount = sum(item.total_price for item in cart_items)

    if request.method == 'POST':
        # Confirm the order
        flash("Order placed successfully! Contact farmer for confirmation.", "success")

        # Reduce stock quantity
        for item in cart_items:
            stock = Stock.query.get(item.stock_id)
            stock.quantity -= item.quantity
            db.session.delete(item)

        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('checkout.html', cart_items=cart_items, total_amount=total_amount)

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

# Run the App
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Creates database tables if they don't exist
    app.run(debug=True)
