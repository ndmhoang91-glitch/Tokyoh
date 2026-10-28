from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image
import os
import sys
import uuid
import datetime
import database

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'static'),
    template_folder=os.path.join(BASE_DIR, 'templates')
)
app.secret_key = os.environ.get('SECRET_KEY', 'tokyoh-secret-salt-key-2026')
CORS(app)

# Ensure database tables and initial data are ready on startup (important for Gunicorn/Render)
database.init_db()

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_admin():
    return session.get('is_admin', False)

# ----------------- PAGE ROUTES -----------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    if not is_admin():
        return redirect('/admin/login')
    return render_template('admin.html')

@app.route('/admin/login')
def login_page():
    if is_admin():
        return redirect('/admin')
    return render_template('login.html')

@app.route('/3D81CB48-6895-423D-8C39-367D4A3A69E0.png')
@app.route('/3D81CB48-6895-423D-8C39-367D4A3A69E0.PNG')
def serve_custom_logo():
    return send_from_directory(os.path.join(BASE_DIR, 'static', 'images'), '3D81CB48-6895-423D-8C39-367D4A3A69E0.png')

# ----------------- PUBLIC API -----------------

@app.route('/api/info', methods=['GET'])
def get_info():
    conn = database.get_db()
    c = conn.cursor()
    row = c.execute('SELECT * FROM restaurant_info WHERE id = 1').fetchone()
    conn.close()
    if row:
        return jsonify(dict(row))
    return jsonify({}), 404

@app.route('/api/menu', methods=['GET'])
def get_menu():
    conn = database.get_db()
    c = conn.cursor()
    categories = [dict(row) for row in c.execute('SELECT * FROM categories ORDER BY sort_order ASC, id ASC').fetchall()]
    dishes = [dict(row) for row in c.execute('SELECT * FROM dishes ORDER BY sort_order ASC, id ASC').fetchall()]
    conn.close()

    # Group dishes by category
    category_map = {}
    for cat in categories:
        cat['dishes'] = []
        category_map[cat['id']] = cat

    for dish in dishes:
        cat_id = dish['category_id']
        if cat_id in category_map:
            category_map[cat_id]['dishes'].append(dish)

    return jsonify({
        'categories': categories,
        'all_dishes': dishes
    })

# ----------------- LEXICON API -----------------

@app.route('/api/lexicon', methods=['GET', 'POST'])
def manage_lexicon():
    conn = database.get_db()
    c = conn.cursor()
    if request.method == 'GET':
        items = [dict(row) for row in c.execute('SELECT * FROM lexicon ORDER BY sort_order ASC, id ASC').fetchall()]
        conn.close()
        return jsonify(items)

    if not is_admin():
        conn.close()
        return jsonify({'error': 'Non autorisé.'}), 403

    data = request.get_json() or {}
    term = (data.get('term') or '').strip()
    if not term:
        conn.close()
        return jsonify({'error': 'Le terme est requis.'}), 400

    c.execute('''
    INSERT INTO lexicon (term, kanji, definition_fr, definition_vi, definition_en, definition_es, image_url, sort_order)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        term,
        (data.get('kanji') or '').strip(),
        (data.get('definition_fr') or '').strip(),
        (data.get('definition_vi') or '').strip(),
        (data.get('definition_en') or '').strip(),
        (data.get('definition_es') or data.get('definition_vi') or '').strip(),
        (data.get('image_url') or '').strip(),
        int(data.get('sort_order', 0))
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': new_id, 'message': 'Terme ajouté avec succès.'})

@app.route('/api/lexicon/<int:item_id>', methods=['PUT', 'DELETE'])
def update_delete_lexicon(item_id):
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    conn = database.get_db()
    c = conn.cursor()
    if request.method == 'DELETE':
        c.execute('DELETE FROM lexicon WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Terme supprimé.'})

    data = request.get_json() or {}
    term = (data.get('term') or '').strip()
    if not term:
        conn.close()
        return jsonify({'error': 'Le terme est requis.'}), 400

    c.execute('''
    UPDATE lexicon SET
        term = ?,
        kanji = ?,
        definition_fr = ?,
        definition_vi = ?,
        definition_en = ?,
        definition_es = ?,
        image_url = ?,
        sort_order = ?
    WHERE id = ?
    ''', (
        term,
        (data.get('kanji') or '').strip(),
        (data.get('definition_fr') or '').strip(),
        (data.get('definition_vi') or '').strip(),
        (data.get('definition_en') or '').strip(),
        (data.get('definition_es') or data.get('definition_vi') or '').strip(),
        (data.get('image_url') or '').strip(),
        int(data.get('sort_order', 0)),
        item_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Terme mis à jour avec succès.'})

# ----------------- ALLERGENS API -----------------

@app.route('/api/allergens', methods=['GET', 'POST'])
def manage_allergens():
    conn = database.get_db()
    c = conn.cursor()
    if request.method == 'GET':
        items = [dict(row) for row in c.execute('SELECT * FROM allergens ORDER BY sort_order ASC, id ASC').fetchall()]
        conn.close()
        return jsonify(items)

    if not is_admin():
        conn.close()
        return jsonify({'error': 'Non autorisé.'}), 403

    data = request.get_json() or {}
    name_fr = (data.get('name_fr') or '').strip()
    if not name_fr:
        conn.close()
        return jsonify({'error': 'Le nom de l\'allergène est requis.'}), 400

    c.execute('''
    INSERT INTO allergens (name_fr, name_vi, name_en, name_es, icon, image_url, example_dish_fr, example_dish_vi, example_dish_en, example_dish_es, sort_order)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        name_fr,
        (data.get('name_vi') or name_fr).strip(),
        (data.get('name_en') or name_fr).strip(),
        (data.get('name_es') or data.get('name_vi') or name_fr).strip(),
        (data.get('icon') or '⚠️').strip(),
        (data.get('image_url') or '').strip(),
        (data.get('example_dish_fr') or '').strip(),
        (data.get('example_dish_vi') or '').strip(),
        (data.get('example_dish_en') or '').strip(),
        (data.get('example_dish_es') or data.get('example_dish_vi') or '').strip(),
        int(data.get('sort_order', 0))
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': new_id, 'message': 'Allergène ajouté avec succès.'})

@app.route('/api/allergens/<int:item_id>', methods=['PUT', 'DELETE'])
def update_delete_allergen(item_id):
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    conn = database.get_db()
    c = conn.cursor()
    if request.method == 'DELETE':
        c.execute('DELETE FROM allergens WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Allergène supprimé.'})

    data = request.get_json() or {}
    name_fr = (data.get('name_fr') or '').strip()
    if not name_fr:
        conn.close()
        return jsonify({'error': 'Le nom de l\'allergène est requis.'}), 400

    c.execute('''
    UPDATE allergens SET
        name_fr = ?,
        name_vi = ?,
        name_en = ?,
        name_es = ?,
        icon = ?,
        image_url = ?,
        example_dish_fr = ?,
        example_dish_vi = ?,
        example_dish_en = ?,
        example_dish_es = ?,
        sort_order = ?
    WHERE id = ?
    ''', (
        name_fr,
        (data.get('name_vi') or name_fr).strip(),
        (data.get('name_en') or name_fr).strip(),
        (data.get('name_es') or data.get('name_vi') or name_fr).strip(),
        (data.get('icon') or '⚠️').strip(),
        (data.get('image_url') or '').strip(),
        (data.get('example_dish_fr') or '').strip(),
        (data.get('example_dish_vi') or '').strip(),
        (data.get('example_dish_en') or '').strip(),
        (data.get('example_dish_es') or data.get('example_dish_vi') or '').strip(),
        int(data.get('sort_order', 0)),
        item_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Allergène mis à jour avec succès.'})

@app.route('/api/reserve', methods=['POST'])
def create_reservation():
    conn = database.get_db()
    c = conn.cursor()

    # Check if online reservations are active
    info = c.execute('SELECT is_reservation_enabled FROM restaurant_info WHERE id = 1').fetchone()
    if info and info['is_reservation_enabled'] == 0:
        conn.close()
        return jsonify({'error': 'Les réservations en ligne sont actuellement fermées. Veuillez nous contacter directement par téléphone.'}), 400

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    email = (data.get('email') or '').strip()
    date = (data.get('date') or '').strip()
    time = (data.get('time') or '').strip()
    guests = data.get('guests', 2)
    notes = (data.get('notes') or '').strip()

    if not name or not phone or not date or not time:
        conn.close()
        return jsonify({'error': 'Veuillez renseigner votre nom, téléphone, date et heure.'}), 400

    c.execute('''
    INSERT INTO reservations (customer_name, phone, email, reservation_date, reservation_time, guests, notes, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
    ''', (name, phone, email, date, time, int(guests), notes))
    res_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'id': res_id, 'message': 'Réservation enregistrée avec succès.'})

@app.route('/api/reservations/toggle', methods=['POST'])
def toggle_reservations():
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    conn = database.get_db()
    c = conn.cursor()
    row = c.execute('SELECT is_reservation_enabled FROM restaurant_info WHERE id = 1').fetchone()
    current_status = row['is_reservation_enabled'] if row and row['is_reservation_enabled'] is not None else 1
    new_status = 0 if current_status == 1 else 1

    c.execute('UPDATE restaurant_info SET is_reservation_enabled = ? WHERE id = 1', (new_status,))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'is_reservation_enabled': new_status,
        'message': 'Les réservations en ligne sont désormais ouvertes.' if new_status == 1 else 'Les réservations en ligne sont désormais fermées.'
    })

# ----------------- ADMIN AUTH API -----------------

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()

    if not username or not password:
        return jsonify({'error': 'Nom d\'utilisateur et mot de passe requis.'}), 400

    pw_hash = database.hash_password(password)
    conn = database.get_db()
    c = conn.cursor()
    user = c.execute('SELECT * FROM admin_users WHERE username = ? AND password_hash = ?', (username, pw_hash)).fetchone()
    conn.close()

    if user:
        session['is_admin'] = True
        session['username'] = user['username']
        return jsonify({'success': True, 'username': user['username']})
    else:
        return jsonify({'error': 'Identifiants invalides.'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/admin/check', methods=['GET'])
def check_auth():
    return jsonify({
        'authenticated': is_admin(),
        'username': session.get('username', '')
    })

@app.route('/api/admin/change-password', methods=['POST'])
def change_password():
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    data = request.get_json() or {}
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')

    if not old_pw or not new_pw or len(new_pw) < 6:
        return jsonify({'error': 'Le mot de passe doit comporter au moins 6 caractères.'}), 400

    conn = database.get_db()
    c = conn.cursor()
    user = c.execute('SELECT * FROM admin_users WHERE username = ?', (session['username'],)).fetchone()
    if not user or user['password_hash'] != database.hash_password(old_pw):
        conn.close()
        return jsonify({'error': 'Ancien mot de passe incorrect.'}), 400

    c.execute('UPDATE admin_users SET password_hash = ? WHERE username = ?',
              (database.hash_password(new_pw), session['username']))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Mot de passe modifié avec succès.'})

# ----------------- ADMIN DISHES API -----------------

@app.route('/api/dishes', methods=['GET', 'POST'])
def manage_dishes():
    if request.method == 'GET':
        conn = database.get_db()
        c = conn.cursor()
        dishes = [dict(row) for row in c.execute('SELECT d.*, c.name_fr as category_name FROM dishes d LEFT JOIN categories c ON d.category_id = c.id ORDER BY d.sort_order ASC, d.id ASC').fetchall()]
        conn.close()
        return jsonify(dishes)

    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    data = request.get_json() or {}
    name_fr = (data.get('name_fr') or '').strip()
    category_id = data.get('category_id')
    price = data.get('price')

    if not name_fr or not category_id or price is None:
        return jsonify({'error': 'Champs obligatoires manquants.'}), 400

    conn = database.get_db()
    c = conn.cursor()
    c.execute('''
    INSERT INTO dishes (
        category_id, name_fr, name_vi, name_en, name_es, kanji,
        description_fr, description_vi, description_en, description_es,
        price, image_url, badge, dietary_tags, allergens,
        protein_options, is_available, sort_order
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        int(category_id),
        name_fr,
        data.get('name_vi', ''),
        data.get('name_en', ''),
        data.get('name_es', data.get('name_vi', '')),
        data.get('kanji', ''),
        data.get('description_fr', ''),
        data.get('description_vi', ''),
        data.get('description_en', ''),
        data.get('description_es', data.get('description_vi', '')),
        float(price),
        data.get('image_url', '/static/images/dishes/hero_bento.jpg'),
        data.get('badge', ''),
        data.get('dietary_tags', ''),
        data.get('allergens', ''),
        data.get('protein_options', ''),
        1 if data.get('is_available', True) else 0,
        int(data.get('sort_order', 0))
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'id': new_id, 'message': 'Plat ajouté avec succès.'})

@app.route('/api/dishes/<int:dish_id>', methods=['PUT', 'DELETE'])
def update_delete_dish(dish_id):
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    conn = database.get_db()
    c = conn.cursor()

    if request.method == 'DELETE':
        c.execute('DELETE FROM dishes WHERE id = ?', (dish_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Plat supprimé.'})

    data = request.get_json() or {}
    c.execute('''
    UPDATE dishes SET
        category_id = ?,
        name_fr = ?,
        name_vi = ?,
        name_en = ?,
        name_es = ?,
        kanji = ?,
        description_fr = ?,
        description_vi = ?,
        description_en = ?,
        description_es = ?,
        price = ?,
        image_url = ?,
        badge = ?,
        dietary_tags = ?,
        allergens = ?,
        protein_options = ?,
        is_available = ?,
        sort_order = ?
    WHERE id = ?
    ''', (
        int(data.get('category_id')),
        data.get('name_fr', '').strip(),
        data.get('name_vi', ''),
        data.get('name_en', ''),
        data.get('name_es', data.get('name_vi', '')),
        data.get('kanji', ''),
        data.get('description_fr', ''),
        data.get('description_vi', ''),
        data.get('description_en', ''),
        data.get('description_es', data.get('description_vi', '')),
        float(data.get('price', 0)),
        data.get('image_url', ''),
        data.get('badge', ''),
        data.get('dietary_tags', ''),
        data.get('allergens', ''),
        data.get('protein_options', ''),
        1 if data.get('is_available', True) else 0,
        int(data.get('sort_order', 0)),
        dish_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Plat mis à jour avec succès.'})

@app.route('/api/dishes/<int:dish_id>/availability', methods=['PATCH'])
def toggle_dish_availability(dish_id):
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    conn = database.get_db()
    c = conn.cursor()
    dish = c.execute('SELECT is_available FROM dishes WHERE id = ?', (dish_id,)).fetchone()
    if not dish:
        conn.close()
        return jsonify({'error': 'Plat non trouvé.'}), 404

    new_status = 0 if dish['is_available'] == 1 else 1
    c.execute('UPDATE dishes SET is_available = ? WHERE id = ?', (new_status, dish_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'is_available': new_status})

# ----------------- ADMIN CATEGORIES API -----------------

@app.route('/api/categories', methods=['GET', 'POST'])
def manage_categories():
    conn = database.get_db()
    c = conn.cursor()

    if request.method == 'GET':
        categories = [dict(row) for row in c.execute('SELECT * FROM categories ORDER BY sort_order ASC, id ASC').fetchall()]
        conn.close()
        return jsonify(categories)

    if not is_admin():
        conn.close()
        return jsonify({'error': 'Non autorisé.'}), 403

    data = request.get_json() or {}
    slug = (data.get('slug') or '').strip().lower()
    name_fr = (data.get('name_fr') or '').strip()
    name_vi = (data.get('name_vi') or name_fr).strip()
    name_en = (data.get('name_en') or name_fr).strip()
    name_es = (data.get('name_es') or data.get('name_vi') or name_fr).strip()
    kanji = data.get('kanji', '')
    sort_order = int(data.get('sort_order', 0))

    if not slug or not name_fr:
        conn.close()
        return jsonify({'error': 'Slug et nom requis.'}), 400

    c.execute('''
    INSERT INTO categories (slug, name_fr, name_vi, name_en, name_es, kanji, sort_order)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (slug, name_fr, name_vi, name_en, name_es, kanji, sort_order))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': new_id})

@app.route('/api/categories/<int:cat_id>', methods=['PUT', 'DELETE'])
def update_delete_category(cat_id):
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    conn = database.get_db()
    c = conn.cursor()

    if request.method == 'DELETE':
        # Check if dishes exist
        cnt = c.execute('SELECT COUNT(*) as count FROM dishes WHERE category_id = ?', (cat_id,)).fetchone()['count']
        if cnt > 0:
            conn.close()
            return jsonify({'error': f'Impossible de supprimer : cette catégorie contient {cnt} plats.'}), 400
        c.execute('DELETE FROM categories WHERE id = ?', (cat_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    data = request.get_json() or {}
    c.execute('''
    UPDATE categories SET
        slug = ?,
        name_fr = ?,
        name_vi = ?,
        name_en = ?,
        name_es = ?,
        kanji = ?,
        sort_order = ?
    WHERE id = ?
    ''', (
        data.get('slug', '').strip(),
        data.get('name_fr', '').strip(),
        data.get('name_vi', '').strip(),
        data.get('name_en', '').strip(),
        (data.get('name_es') or data.get('name_vi') or '').strip(),
        data.get('kanji', '').strip(),
        int(data.get('sort_order', 0)),
        cat_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ----------------- ADMIN SETTINGS API -----------------

@app.route('/api/info', methods=['PUT'])
def update_info():
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    data = request.get_json() or {}
    conn = database.get_db()
    c = conn.cursor()
    current_row = c.execute('SELECT * FROM restaurant_info WHERE id = 1').fetchone()
    current = dict(current_row) if current_row else {}

    def val(key, default=''):
        if key in data:
            return data[key]
        return current.get(key, default)

    c.execute('''
    UPDATE restaurant_info SET
        name = ?,
        slogan = ?,
        tagline = ?,
        address = ?,
        location_detail = ?,
        phone = ?,
        email = ?,
        opening_hours = ?,
        ubereats_url = ?,
        deliveroo_url = ?,
        instagram_url = ?,
        facebook_url = ?,
        tiktok_url = ?,
        story_fr = ?,
        story_vi = ?,
        story_en = ?,
        story_es = ?,
        hero_badge = ?,
        hero_image_url = ?,
        hero_dish_name = ?,
        hero_dish_price = ?,
        hero_dish_badge = ?,
        hero_mascot_url = ?,
        allergen_badge = ?,
        allergen_title_fr = ?,
        allergen_title_vi = ?,
        allergen_title_en = ?,
        allergen_title_es = ?,
        allergen_desc_fr = ?,
        allergen_desc_vi = ?,
        allergen_desc_en = ?,
        allergen_desc_es = ?,
        allergen_note_fr = ?,
        allergen_note_vi = ?,
        allergen_note_en = ?,
        allergen_note_es = ?,
        is_reservation_enabled = ?
    WHERE id = 1
    ''', (
        val('name', 'TokyOh! Anglet'),
        val('slogan', "L'énergie de Tokyo dans votre assiette !"),
        val('tagline', 'Cuisine Japonaise Moderne & Bentos Gourmands'),
        val('address', 'Halles des 5 Cantons, 64600 Anglet, France'),
        val('location_detail', 'Aux Halles des 5 Cantons - Emplacement Cœur Gourmand'),
        val('phone', '+33 5 59 00 00 00'),
        val('email', 'contact@tokyoh-anglet.fr'),
        val('opening_hours', 'Mardi - Dimanche : 10h30 - 14h30 & 18h30 - 22h00'),
        val('ubereats_url', 'https://www.ubereats.com'),
        val('deliveroo_url', 'https://deliveroo.fr'),
        val('instagram_url', 'https://instagram.com/tokyoh.anglet'),
        val('facebook_url', 'https://facebook.com/tokyoh.anglet'),
        val('tiktok_url', 'https://tiktok.com/@tokyoh.anglet'),
        val('story_fr', ''),
        val('story_vi', ''),
        val('story_en', ''),
        val('story_es', ''),
        val('hero_badge', 'NOUVEAU À ANGLET • HALLES DES 5 CANTONS'),
        val('hero_image_url', '/static/images/dishes/hero_bento.jpg'),
        val('hero_dish_name', 'Lunch Katsu Bento'),
        val('hero_dish_price', '13,90 €'),
        val('hero_dish_badge', 'BEST SELLER'),
        val('hero_mascot_url', '/static/images/bento_box_art.jpg'),
        val('allergen_badge', 'TRANSPARENCE ALIMENTAIRE'),
        val('allergen_title_fr', 'Guide des Allergènes & Recettes Saines'),
        val('allergen_title_vi', 'Cẩm Nang Dị Ứng & Dinh Dưỡng Lành Mạnh'),
        val('allergen_title_en', 'Allergen Guide & Healthy Dining'),
        val('allergen_title_es', 'Guía de Alérgenos y Nutrición Saludable'),
        val('allergen_desc_fr', 'Conformément à la réglementation française et européenne, nous affichons avec la plus grande transparence l''ensemble des allergènes majeurs présents dans nos préparations.'),
        val('allergen_desc_vi', 'Tuân thủ nghiêm ngặt quy định an toàn thực phẩm của Pháp và EU, chúng tôi công khai minh bạch tất cả các nhóm dị ứng trong thực đơn.'),
        val('allergen_desc_en', 'In full compliance with French and EU food safety standards, we display all major allergens present in our dishes with total transparency.'),
        val('allergen_desc_es', 'Cumpliendo rigurosamente con la normativa europea de seguridad alimentaria, mostramos con total transparencia todos los alérgenos presentes en nuestras recetas.'),
        val('allergen_note_fr', 'Merci de signaler toute allergie ou intolérance à notre équipe lors de votre commande afin que nous adaptions votre plat avec le plus grand soin.'),
        val('allergen_note_vi', 'Vui lòng thông báo cho nhân viên nếu bạn có bất kỳ dị ứng nào khi gọi món để đầu bếp chế biến phù hợp nhất.'),
        val('allergen_note_en', 'Please inform our team of any food allergies or intolerances when ordering so we can prepare your dish with extra care.'),
        val('allergen_note_es', 'Por favor, informe a nuestro equipo de cualquier alergia o intolerancia al realizar su pedido para que podamos adaptar su plato con el mayor cuidado.'),
        int(val('is_reservation_enabled', 1))
    ))
    conn.commit()
    updated_row = c.execute('SELECT * FROM restaurant_info WHERE id = 1').fetchone()
    conn.close()
    return jsonify({'success': True, 'message': 'Informations enregistrées avec succès.', 'data': dict(updated_row) if updated_row else {}})

# ----------------- ADMIN RESERVATIONS API -----------------

@app.route('/api/admin/reservations', methods=['GET'])
def get_reservations():
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    conn = database.get_db()
    c = conn.cursor()
    reservations = [dict(row) for row in c.execute('SELECT * FROM reservations ORDER BY reservation_date DESC, reservation_time DESC, id DESC').fetchall()]
    conn.close()
    return jsonify(reservations)

@app.route('/api/admin/reservations/<int:res_id>', methods=['PUT', 'DELETE'])
def update_reservation(res_id):
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    conn = database.get_db()
    c = conn.cursor()

    if request.method == 'DELETE':
        c.execute('DELETE FROM reservations WHERE id = ?', (res_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    data = request.get_json() or {}
    status = data.get('status', 'pending')
    c.execute('UPDATE reservations SET status = ? WHERE id = ?', (status, res_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'status': status})

# ----------------- FILE UPLOAD API -----------------

@app.route('/api/upload', methods=['POST'])
def upload_image():
    if not is_admin():
        return jsonify({'error': 'Non autorisé.'}), 403

    if 'image' not in request.files:
        return jsonify({'error': 'Aucun fichier envoyé.'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'Nom de fichier vide.'}), 400

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f'dish_{uuid.uuid4().hex[:12]}.{ext}'
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)

        # Optimize image with Pillow
        try:
            img = Image.open(file.stream)
            if img.mode in ('RGBA', 'P') and ext in ('jpg', 'jpeg'):
                img = img.convert('RGB')
            # Resize if very large
            if img.width > 1200 or img.height > 1200:
                img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            img.save(save_path, quality=90, optimize=True)
        except Exception as e:
            file.save(save_path)

        url = f'/static/uploads/{unique_name}'
        return jsonify({'success': True, 'url': url})

    return jsonify({'error': 'Format de fichier non supporté.'}), 400

import threading
import webbrowser

def open_browser():
    import time
    time.sleep(1.5)
    try:
        webbrowser.open('http://localhost:5000')
    except Exception:
        pass

if __name__ == '__main__':
    database.init_db()
    is_frozen = getattr(sys, 'frozen', False)
    print('======================================================================')
    print('              TOKYOH! ANGLET - RESTAURANT JAPONAIS')
    print('                 HE THONG WEBSITE VA QUAN TRI')
    print('======================================================================')
    print('  - Website khach hang:     http://localhost:5000')
    print('  - Trang quan tri Admin:   http://localhost:5000/admin')
    print('    (Tai khoan: admin  |  Mat khau: tokyoh2026)')
    print('======================================================================')
    port = int(os.environ.get('PORT', 5000))
    if not os.environ.get('RENDER'):
        threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='0.0.0.0', port=port, debug=not is_frozen)
