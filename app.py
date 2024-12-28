from flask import Flask, render_template, redirect, url_for, flash, request, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'Martyshka'
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect('auth.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            image_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    conn.commit()
    conn.close()


init_db()

def update_db_schema():
    conn = sqlite3.connect('auth.db')
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE wishlist ADD COLUMN image_path TEXT')
        conn.commit()
        print("Database schema updated successfully.")
    except sqlite3.OperationalError:
        print("Column 'image_path' already exists.")
    conn.close()

update_db_schema()


@app.route('/')
def home():
    return render_template('base.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            conn = sqlite3.connect('auth.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            conn.close()
            flash('Signup successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Try a different one.', 'danger')
    
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('auth.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and user[1] == password:
            session['user_id'] = user[0]
            flash('Login successful!', 'success')
            return redirect(url_for('wishlist')) 
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/wishlist', methods=['GET', 'POST'])
def wishlist():
    if 'user_id' not in session:
        flash('You need to log in to access your wishlist.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']

    conn = sqlite3.connect('auth.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        product_name = request.form.get('product_name', '').strip()
        image = request.files.get('image')
        image_path = None

        if image and image.filename:
            if image.mimetype.startswith('image/'):
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = filename 
            else:
                flash('Only image files are allowed!', 'danger')
                return redirect(url_for('wishlist'))

        if product_name:
            cursor.execute('INSERT INTO wishlist (user_id, product_name, image_path) VALUES (?, ?, ?)', 
                           (user_id, product_name, image_path))
            conn.commit()
            flash('Product added to wishlist!', 'success')
        else:
            flash('Product name cannot be empty.', 'danger')

    cursor.execute('SELECT id, product_name, image_path FROM wishlist WHERE user_id = ?', (user_id,))
    wishlist_items = cursor.fetchall()
    conn.close()

    return render_template('wishlist.html', wishlist_items=wishlist_items)

@app.route('/wishlist/delete/<int:item_id>', methods=['POST'])
def delete_wishlist_item(item_id):
    if 'user_id' not in session:
        flash('You need to log in to access your wishlist.', 'danger')
        return redirect(url_for('login'))
    
    user_id = session['user_id']

    conn = sqlite3.connect('auth.db')
    cursor = conn.cursor()

    cursor.execute('SELECT image_path FROM wishlist WHERE id = ? AND user_id = ?', (item_id, user_id))
    item = cursor.fetchone()
    if item and item[0]: 
        try:
            os.remove(item[0])
        except FileNotFoundError:
            pass

    cursor.execute('DELETE FROM wishlist WHERE id = ? AND user_id = ?', (item_id, user_id))
    conn.commit()
    conn.close()

    flash('Product removed from wishlist.', 'success')
    return redirect(url_for('wishlist'))

if __name__ == '__main__':
    app.run(debug=True)
