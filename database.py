import sqlite3
import hashlib
import json
import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, 'tokyoh.db')

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Categories
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        name_fr TEXT NOT NULL,
        name_vi TEXT NOT NULL,
        name_en TEXT NOT NULL,
        name_es TEXT,
        kanji TEXT,
        sort_order INTEGER DEFAULT 0
    )
    ''')

    # 2. Dishes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS dishes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        name_fr TEXT NOT NULL,
        name_vi TEXT,
        name_en TEXT,
        name_es TEXT,
        kanji TEXT,
        description_fr TEXT,
        description_vi TEXT,
        description_en TEXT,
        description_es TEXT,
        price REAL NOT NULL,
        image_url TEXT,
        badge TEXT DEFAULT '',
        dietary_tags TEXT DEFAULT '',
        allergens TEXT DEFAULT '',
        protein_options TEXT DEFAULT '',
        is_available INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    ''')

    # 3. Restaurant Info
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS restaurant_info (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        slogan TEXT,
        tagline TEXT,
        address TEXT,
        location_detail TEXT,
        phone TEXT,
        email TEXT,
        opening_hours TEXT,
        ubereats_url TEXT,
        deliveroo_url TEXT,
        instagram_url TEXT,
        facebook_url TEXT,
        tiktok_url TEXT,
        story_fr TEXT,
        story_vi TEXT,
        story_en TEXT,
        story_es TEXT,
        hero_badge TEXT DEFAULT 'NOUVEAU À ANGLET • HALLES DES 5 CANTONS',
        hero_image_url TEXT DEFAULT '/static/images/dishes/hero_bento.jpg',
        hero_dish_name TEXT DEFAULT 'Lunch Katsu Bento',
        hero_dish_price TEXT DEFAULT '13,90 €',
        hero_dish_badge TEXT DEFAULT 'BEST SELLER',
        hero_mascot_url TEXT DEFAULT '/static/images/bento_box_art.jpg',
        allergen_badge TEXT DEFAULT 'TRANSPARENCE ALIMENTAIRE',
        allergen_title_fr TEXT DEFAULT 'Guide des Allergènes & Recettes Saines',
        allergen_title_vi TEXT DEFAULT 'Cẩm Nang Dị Ứng & Dinh Dưỡng Lành Mạnh',
        allergen_title_en TEXT DEFAULT 'Allergen Guide & Healthy Dining',
        allergen_title_es TEXT DEFAULT 'Guía de Alérgenos y Nutrición Saludable',
        allergen_desc_fr TEXT DEFAULT 'Conformément à la réglementation française et européenne, nous affichons avec la plus grande transparence l''ensemble des allergènes majeurs présents dans nos préparations.',
        allergen_desc_vi TEXT DEFAULT 'Tuân thủ nghiêm ngặt quy định an toàn thực phẩm của Pháp và EU, chúng tôi công khai minh bạch tất cả các nhóm dị ứng trong thực đơn.',
        allergen_desc_en TEXT DEFAULT 'In full compliance with French and EU food safety standards, we display all major allergens present in our dishes with total transparency.',
        allergen_desc_es TEXT DEFAULT 'Cumpliendo rigurosamente con la normativa europea de seguridad alimentaria, mostramos con total transparencia todos los alérgenos presentes en nuestras recetas.',
        allergen_note_fr TEXT DEFAULT 'Merci de signaler toute allergie ou intolérance à notre équipe lors de votre commande afin que nous adaptions votre plat với le plus grand soin.',
        allergen_note_vi TEXT DEFAULT 'Vui lòng thông báo cho nhân viên nếu bạn có bất kỳ dị ứng nào khi gọi món để đầu bếp chế biến phù hợp nhất.',
        allergen_note_en TEXT DEFAULT 'Please inform our team of any food allergies or intolerances when ordering so we can prepare your dish with extra care.',
        allergen_note_es TEXT DEFAULT 'Por favor, informe a nuestro equipo de cualquier alergia o intolerancia al realizar su pedido para que podamos adaptar su plato con el mayor cuidado.'
    )
    ''')

    # 4. Reservations
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        reservation_date TEXT NOT NULL,
        reservation_time TEXT NOT NULL,
        guests INTEGER NOT NULL,
        notes TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 5. Admin Users
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 6. Japanese Culinary Lexicon
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS lexicon (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        term TEXT NOT NULL,
        kanji TEXT,
        definition_fr TEXT,
        definition_vi TEXT,
        definition_en TEXT,
        definition_es TEXT,
        image_url TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0
    )
    ''')

    # 7. Allergens Guide
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS allergens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name_fr TEXT NOT NULL,
        name_vi TEXT,
        name_en TEXT,
        name_es TEXT,
        icon TEXT DEFAULT '⚠️',
        image_url TEXT DEFAULT '',
        example_dish_fr TEXT,
        example_dish_vi TEXT,
        example_dish_en TEXT,
        example_dish_es TEXT,
        sort_order INTEGER DEFAULT 0
    )
    ''')

    # Ensure Spanish columns exist in existing database tables
    for tbl, cols in [
        ('categories', [('name_es', 'TEXT')]),
        ('dishes', [('name_es', 'TEXT'), ('description_es', 'TEXT')]),
        ('restaurant_info', [('story_es', 'TEXT'), ('allergen_title_es', 'TEXT'), ('allergen_desc_es', 'TEXT'), ('allergen_note_es', 'TEXT')]),
        ('lexicon', [('definition_es', 'TEXT')]),
        ('allergens', [('name_es', 'TEXT'), ('example_dish_es', 'TEXT')])
    ]:
        for col, col_type in cols:
            try:
                cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    conn.commit()

    # Seed initial data if empty
    cursor.execute('SELECT COUNT(*) as cnt FROM categories')
    if cursor.fetchone()['cnt'] == 0:
        seed_data(cursor)
        conn.commit()

    conn.close()

def seed_data(cursor):
    # Categories
    categories_data = [
        ('entrees', 'Entrées', 'Món Khai Vị', 'Starters', '前菜', 1),
        ('bentos-classiques', 'Bentos Classiques', 'Bento Truyền Thống', 'Classic Bentos', 'クラシック弁当', 2),
        ('bento-gourmand', 'Formule Bento Gourmand', 'Set Bento Đại Tiệc', 'Gourmet Bento Set', 'グルマン弁当', 3),
        ('kids-supplements', 'Menu Enfant & Suppléments', 'Thực Đơn Trẻ Em & Topping Thêm', 'Kids Menu & Extras', 'お子さまメニュー・追加', 4),
        ('desserts', 'Desserts', 'Món Tráng Miệng', 'Desserts', 'デザート', 5),
        ('boissons', 'Boissons & Saké', 'Đồ Uống & Rượu Saké', 'Drinks & Sake', 'ドリンク', 6)
    ]
    cursor.executemany('''
    INSERT INTO categories (slug, name_fr, name_vi, name_en, kanji, sort_order)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', categories_data)

    cat_map = {
        'entrees': 1,
        'bentos-classiques': 2,
        'bento-gourmand': 3,
        'kids-supplements': 4,
        'desserts': 5,
        'boissons': 6
    }

    # Dishes from real menu
    dishes_data = [
        # --- Entrées ---
        (cat_map['entrees'], 'Soupe miso', 'Súp Miso truyền thống', 'Traditional Miso Soup', '味噌汁',
         'Soupe japonaise traditionnelle, végane, légère et réconfortante avec tofu soyeux, algues wakame et cébette fraîche.',
         'Súp miso đậu nành lên men truyền thống của Nhật Bản, thanh đạm, ấm lòng.',
         'Traditional Japanese soup, vegan, light and comforting with silken tofu, wakame seaweed and scallions.',
         3.90, '/static/images/dishes/soupe_miso.jpg', '', 'vegan', 'soja', '', 1, 1),

        (cat_map['entrees'], 'Salade japonaise', 'Salad Nhật Bản tươi giòn', 'Japanese Fresh Salad', '和風サラダ',
         'Salade fraîche et croquante d\'inspiration japonaise, assaisonnée avec une sauce légère au vinaigre de riz et à l\'huile de sésame.',
         'Salad bắp cải trộn edamame tươi giòn kiểu Nhật, hòa quyện dầu mè thơm lừng và giấm gạo.',
         'Fresh and crispy Japanese salad with rice vinegar dressing and sesame oil.',
         3.90, '/static/images/dishes/salade_japonaise.jpg', '', 'vegan,healthy', 'sesame', '', 1, 2),

        (cat_map['entrees'], 'Gyoza canard x4', 'Bánh há cảo vịt nướng (4 cái)', 'Duck Gyoza (4 pcs)', '鴨餃子',
         'Raviolis japonais grillés au canard, servis avec la sauce teriyaki douce.',
         'Bánh xếp Nhật Bản nhân thịt vịt thơm lừng áp chảo giòn đáy, sốt teriyaki đậm đà.',
         'Grilled Japanese duck dumplings served with savory teriyaki sauce.',
         4.90, '/static/images/dishes/gyoza_canard.jpg', 'POPULAIRE', '', 'gluten,soja', '', 1, 3),

        (cat_map['entrees'], 'Takoyaki x5', 'Bánh bạch tuộc Takoyaki (5 viên)', 'Octopus Takoyaki (5 pcs)', 'たこ焼き',
         'Fameuses boulettes japonaises au poulpe, servies avec une sauce teriyaki, de la mayonnaise japonaise et une touche d\'algue nori.',
         'Bánh viên nhân bạch tuộc nổi tiếng vùng Osaka, sốt teriyaki, sốt mayo Nhật và vụn rong biển.',
         'Famous Osaka octopus balls with teriyaki sauce, Japanese mayo and nori flakes.',
         5.90, '/static/images/dishes/takoyaki.jpg', 'COUP DE CŒUR', '', 'gluten,crustaces,poissons,oeufs,soja,moutarde', '', 1, 4),

        (cat_map['entrees'], 'Yakitori poulet x2', 'Thịt gà xiên nướng sốt Teriyaki (2 xiên)', 'Chicken Yakitori Skewers (2 pcs)', '焼き鳥',
         'Brochettes japonaises de poulet grillé, nappées d\'une sauce teriyaki douce et savoureuse.',
         'Xiên gà nướng than hoa mềm mọng, quét đẫm sốt teriyaki mật ong đặc trưng.',
         'Japanese grilled chicken skewers glazed with sweet teriyaki sauce.',
         4.90, '/static/images/dishes/yakitori_poulet.jpg', '', '', 'gluten,soja', '', 1, 5),

        (cat_map['entrees'], 'Beef cheese x2', 'Bò cuộn phô mai tan chảy (2 xiên)', 'Beef & Melted Cheese Skewers (2 pcs)', '牛チーズ',
         'Brochettes gourmandes au fromage fondant enrobé de bœuf, nappées d\'une sauce teriyaki.',
         'Thịt bò thượng hạng cuộn phô mai béo ngậy tan chảy khi nướng nóng hổi.',
         'Tender beef rolls stuffed with melted gooey cheese and glazed with teriyaki sauce.',
         4.90, '/static/images/dishes/beef_cheese.jpg', 'GOURMAND', '', 'lait,soja,gluten', '', 1, 6),

        # --- Bentos Classiques ---
        (cat_map['bentos-classiques'], 'Lunch Katsu', 'Cơm Bento Katsu Đặc Biệt', 'Signature Lunch Katsu Bento', 'ランチカツ弁当',
         'Le bento signature TokyOh! Riz japonais, salade japonaise, tomates cerises, cébette, sésame et panure japonaise croustillante.',
         'Hộp bento biểu tượng của TokyOh! Cơm dẻo Nhật Bản, salad giòn tươi, cà chua bi, hành hoa, mè rang cùng cốt lết chiên giòn rụm.',
         'The TokyOh! signature bento. Japanese rice, fresh salad, cherry tomatoes, scallions, sesame seeds and ultra-crispy Japanese cutlet.',
         13.90, '/static/images/dishes/bento_lunch_katsu.jpg', 'BEST SELLER', '', 'gluten,soja,sesame', 'Porc, Poulet, Crevettes, Tofu', 1, 1),

        (cat_map['bentos-classiques'], 'Katsu Curry', 'Bento Cà Ri Nhật Katsu', 'Japanese Katsu Curry Bento', 'カツカレー弁当',
         'Le grand classique japonais. Riz japonais, katsu croustillant, curry japonais maison aux légumes, cébette, pickles et takuan croquant.',
         'Món kinh điển xứ Phù Tang. Cơm trắng, katsu giòn rụm ngập sốt cà ri Nhật nấu rau củ đậm đà, củ cải muối takuan vàng óng.',
         'The great Japanese classic. Japanese rice, crispy cutlet, homemade vegetable Japanese curry, scallions, pickles and takuan radish.',
         13.90, '/static/images/dishes/bento_katsu_curry.jpg', 'INCONTOURNABLE', '', 'gluten,soja,moutarde', 'Porc, Poulet, Crevettes, Tofu', 1, 2),

        (cat_map['bentos-classiques'], 'Curry Katsu Udon', 'Mì Udon Cà Ri Katsu', 'Curry Katsu Udon Bento', 'カレーうどん',
         'Nouilles udon japonaises moelleuses, curry japonais maison savoureux, pickles et takuan croquant.',
         'Sợi mì udon tươi dai béo quyện cùng sốt cà ri nóng hổi, katsu giòn và củ cải chua ngọt.',
         'Thick soft udon noodles simmered in hearty Japanese curry sauce, pickles and takuan.',
         14.90, '/static/images/dishes/bento_curry_katsu_udon.jpg', '', '', 'gluten,soja,moutarde', 'Porc, Poulet, Crevettes, Tofu', 1, 3),

        (cat_map['bentos-classiques'], 'Teriyaki Udon Katsu', 'Mì Udon Xào Teriyaki Katsu', 'Stir-fried Teriyaki Udon Katsu Bento', '照り焼きうどん',
         'Nouilles udon sautées au wok, sauce teriyaki sucrée-salée, légumes croquants et salade japonaise rafraîchissante.',
         'Mì udon xào rau củ sốt teriyaki thơm lừng, ăn kèm thịt chiên katsu giòn tan.',
         'Wok-tossed udon noodles in rich teriyaki sauce, crunchy stir-fry vegetables and Japanese salad.',
         14.90, '/static/images/dishes/bento_teriyaki_udon.jpg', '', '', 'gluten,soja,sesame', 'Porc, Poulet, Crevettes, Tofu', 1, 4),

        (cat_map['bentos-classiques'], 'Tataki de Thon Rouge', 'Bento Cá Ngừ Đại Dương Áp Chảo', 'Red Tuna Tataki Bento', 'マグロのタタキ弁当',
         'Le plus frais et le plus léger. Riz vinaigré, tataki de thon rouge mi-cuit, salade mesclun, edamame, tomates cerises, takuan, wasabi, sauce ponzu et sésame.',
         'Món ăn tươi mát và thanh lịch nhất. Cơm trộn giấm sushi, thon rouge áp chảo tái hồng hào, hạt đậu nành edamame, sốt ponzu thanh mát.',
         'Light and exceptionally fresh. Seasoned sushi rice, seared red tuna tataki, mesclun, edamame, cherry tomatoes, takuan, wasabi and citrus ponzu.',
         15.90, '/static/images/dishes/bento_tataki_thon.jpg', 'HEALTHY', 'healthy', 'poissons,soja,sesame,celeri', '', 1, 5),

        # --- Bento Gourmand ---
        (cat_map['bento-gourmand'], 'Formule Bento Gourmand (+6 €)', 'Nâng Cấp Formule Gourmand (+6 €)', 'Gourmet Bento Upgrade (+6 €)', 'グルマン弁当セット',
         'Transformez votre bento classique en formule festin : riz à volonté, soupe miso offerte, salade mesclun aux tomates cerises et carotte râpée, aubergine miso fondante, sushi signature du chef, et tamagoyaki ou ajitsuke tamago.',
         'Nâng cấp hộp bento bất kỳ thành tiệc thịnh soạn: Thêm cơm thoải mái, súp miso, salad tươi, cà tím sốt tương miso, sushi cá tươi của bếp trưởng và trứng cuộn tamagoyaki.',
         'Upgrade any classic bento into a royal feast: unlimited rice, miso soup, mesclun salad, miso glazed eggplant, chef special sushi and tamagoyaki omelette.',
         6.00, '/static/images/dishes/bento_gourmand.jpg', 'OFFRE SPÉCIALE', 'gourmand', 'gluten,soja,poissons,oeufs', 'Disponible sur Katsu Curry, Lunch Katsu, Tataki Thon', 1, 1),

        # --- Kids & Suppléments ---
        (cat_map['kids-supplements'], 'TokyOh! Kids', 'Set Cơm Trẻ Em TokyOh! Kids', 'TokyOh! Kids Bento Box', 'お子さまセット',
         'Pour les petits ninjas : salade mesclun, tomates cerises, carottes râpées, riz japonais moulé en étoile, poulet karaage doré croustillant sauce teriyaki, cébette et 1 mochi douceur.',
         'Phần ăn dành riêng cho bé: Cơm Nhật tạo hình ngôi sao ngộ nghĩnh, gà karaage tẩm bột giòn ngọt sốt teriyaki, rau củ bổ dưỡng và 1 chiếc bánh mochi.',
         'For the little ninjas: star-shaped Japanese rice, crispy chicken karaage with sweet teriyaki, colorful fresh salad and a yummy mochi.',
         9.90, '/static/images/dishes/menu_enfant.jpg', 'POUR ENFANTS', '', 'gluten,soja,sesame', '', 1, 1),

        (cat_map['kids-supplements'], 'Supplément Protéines', 'Phần Topping Đạm Thêm', 'Extra Protein Portion', 'タンパク質追加',
         'Ajoutez votre protéine préférée : Karaage poulet, Porc tonkatsu, Ebi fry x4 (crevettes panées), Tofu frit x5 ou Tataki de thon x3.',
         'Thêm topping đạm cao cấp: Gà Karaage giòn rụm, Thịt heo Tonkatsu chiên xù, Tôm Tempura Ebi fry x4, Đậu hũ chiên x5 hoặc Cá ngừ Tataki x3 lát.',
         'Add extra protein: Crispy Chicken Karaage, Pork Tonkatsu, Panko Prawns Ebi Fry x4, Fried Tofu x5, or Tuna Tataki x3.',
         4.90, '/static/images/poster_bento.jpg', '', '', 'gluten,soja,poissons,crustaces', 'Karaage, Tonkatsu, Ebi fry x4, Tofu x5, Tataki x3', 1, 2),

        (cat_map['kids-supplements'], 'Supplément Accompagnements', 'Cơm & Mì Ăn Kèm Thêm', 'Extra Side Carbohydrates', '主食追加',
         'Portion supplémentaire de riz japonais parfumé, riz vinaigré sushi ou nouilles udon chaudes.',
         'Thêm cơm trắng Nhật Bản, cơm trộn giấm sushi dẻo thơm hoặc mì Udon.',
         'Extra portion of steaming Japanese rice, seasoned sushi rice or udon noodles.',
         2.90, '/static/images/bento_box_art.jpg', '', '', '', 'Riz japonais, Riz vinaigré, Udon', 1, 3),

        (cat_map['kids-supplements'], 'Extras (Légumes / Tamagoyaki / Ajitama)', 'Topping Rau Củ & Trứng Nhật', 'Extra Veggies & Japanese Eggs', 'トッピング',
         'Légumes croquants du jour, Tamagoyaki (omelette japonaise roulée) ou Ajitama (œuf mollet mariné coulant).',
         'Rau củ xào tươi, Trứng cuộn ngọt Tamagoyaki mềm mịn hoặc Trứng lòng đào ngâm tương Ajitama.',
         'Fresh seasonal vegetables, sliced sweet Tamagoyaki omelet, or marinated gooey soft-boiled Ajitama egg.',
         3.50, '/static/images/bento_mascot.jpg', '', '', 'oeufs,soja', 'Légumes, Tamagoyaki, Ajitama', 1, 4),

        # --- Desserts ---
        (cat_map['desserts'], 'Mochi x2', 'Bánh Mochi Nhật Dẻo Thơm (2 viên)', 'Artisanal Mochi (2 pcs)', '餅',
         'Mochi glacés rafraîchissants ou mochi pâtissiers traditionnels fondants au cœur gourmand.',
         'Bánh nếp mochi dẻo mềm nhân kem lạnh hoặc nhân ngọt truyền thống bùi thơm tan chảy.',
         'Refreshing ice cream mochi or traditional soft mochi pastries.',
         4.90, '/static/images/dishes/mochi.jpg', 'VÉGAN DISPONIBLE', 'vegan', 'sesame', 'Vanille, Matcha, Mangue, Chocolat', 1, 1),

        (cat_map['desserts'], 'Gyoza pomme caramel beurre salé x4', 'Gyoza nhân táo sốt caramel bơ mặn (4 cái)', 'Apple Gyoza with Salted Caramel (4 pcs)', 'りんご餃子',
         'Création fusion unique : raviolis japonais croustillants farcis à la compotée de pommes, nappés d\'un onctueux caramel au beurre salé.',
         'Sự kết hợp tuyệt đỉnh giữa ẩm thực Pháp và Nhật: Vỏ bánh gyoza chiên giòn rụm nhân táo nghiền thơm ngậy sốt caramel bơ mặn vùng Bretagne.',
         'Crispy sweet gyoza dumplings filled with tender stewed apples and drizzled with Brittany salted butter caramel.',
         5.90, '/static/images/dishes/gyoza_pomme.jpg', 'CRÉATION MAISON', '', 'gluten,lait', '', 1, 2),

        (cat_map['desserts'], 'Taiyaki anko + Chantilly', 'Bánh cá nướng Taiyaki đậu đỏ & kem tươi', 'Taiyaki Fish Waffle with Red Bean & Chantilly', 'たい焼き',
         'Gâteau traditionnel japonais en forme de poisson dorade, garni de pâte de haricots rouges sucrée (anko) et servi avec de la chantilly.',
         'Bánh quế hình cá tráp truyền thống biểu tượng may mắn của Nhật, nhân đậu đỏ anko ngọt dịu ăn kèm kem tươi chantilly.',
         'Traditional Japanese fish-shaped waffle cake filled with sweet azuki red bean paste, served with fluffy chantilly cream.',
         4.90, '/static/images/dishes/taiyaki.jpg', 'TRADITION', '', 'gluten,oeufs,lait', '', 1, 3),

        (cat_map['desserts'], 'Crème chocolat coco', 'Kem mousse sô-cô-la cốt dừa thuần chay', 'Vegan Coconut Chocolate Cream', 'チョコレートムース',
         'Chocolat noir intense 70%, lait de coco onctueux et copeaux croquants de noix de coco grillée. Recette 100% végane.',
         'Mousse sô-cô-la đen nguyên chất hòa quyện nước cốt dừa béo ngậy rắc dừa sấy giòn, thuần thực vật.',
         'Rich dark chocolate, smooth coconut cream and toasted crunchy coconut shavings. 100% vegan.',
         5.90, '/static/images/dishes/creme_chocolat.jpg', 'VÉGAN', 'vegan', '', '', 1, 4),

        (cat_map['desserts'], 'Glaces 2 boules', 'Kem Nhật 2 Viên (Matcha & Vừng Đen)', 'Japanese Ice Cream (2 scoops)', 'アイスクリーム',
         'Glace authentique au thé matcha d\'Uji et glace au sésame noir torréfié, saupoudrées de sésame croquant ou poudre de thé vert.',
         'Kem vị trà xanh Matcha Uji thượng hạng và kem mè đen rang béo thơm, rắc bột trà xanh tươi.',
         'Authentic Uji matcha green tea ice cream & roasted black sesame ice cream with roasted sesame topping.',
         4.90, '/static/images/dishes/glaces_matcha_sesame.jpg', 'REFRESHING', '', 'lait,sesame', '', 1, 5),

        # --- Boissons ---
        (cat_map['boissons'], 'Bière Asahi Super Dry (33cl)', 'Bia Nhật Bản Asahi Super Dry', 'Asahi Super Dry Beer (33cl)', 'アサヒビール',
         'La bière blonde numéro 1 au Japon, brassée selon la tradition du goût extra sec et désaltérant.',
         'Thương hiệu bia số 1 Nhật Bản, vị êm mượt, khô nhẹ sảng khoái tuyệt hảo khi dùng kèm Bento.',
         'Japan\'s #1 best-selling crisp dry lager beer.',
         4.90, '/static/images/dishes/boissons_all.jpg', 'JAPON', '', 'gluten', '', 1, 1),

        (cat_map['boissons'], 'Bière Kirin Ichiban (33cl)', 'Bia Nhật Bản Kirin Ichiban', 'Kirin Ichiban Beer (33cl)', '一番搾り',
         'Bière 100% pur malt, méthode de première pression pour une rondeur et un arôme floral incomparables.',
         'Bia Kirin Ichiban chiết xuất từ nước cốt hoa bia đầu tiên, hương thơm mạch nha thanh khiết.',
         '100% malt first press Japanese premium beer.',
         4.90, '/static/images/dishes/boissons_all.jpg', 'JAPON', '', 'gluten', '', 1, 2),

        (cat_map['boissons'], 'Saké Kaori Junmai (18cl - 14°)', 'Rượu Saké Nhật Bản Kaori', 'Kaori Japanese Sake (18cl - 14°)', '日本酒 香',
         'Saké japonais d\'exception, doux et floral, servi frais ou chambré dans sa coupelle traditionnelle.',
         'Rượu gạo sake truyền thống nhập khẩu nguyên chai từ Nhật Bản, hương hoa thanh nhã, êm ái.',
         'Refined aromatic Japanese sake, smooth and floral notes.',
         9.90, '/static/images/dishes/boissons_all.jpg', 'SÉLECTION', '', '', '', 1, 3),

        (cat_map['boissons'], 'Soju Raisin 7 Drops (36cl - 12°)', 'Rượu Soju Nho Xanh 7 Drops', 'Green Grape Soju (36cl - 12°)', 'マスカット焼酎',
         'Boisson douce et fruitée au raisin vert, idéale à partager entre amis.',
         'Rượu soju vị nho xanh chua ngọt thanh mát nồng độ 12°, cực kỳ dễ uống.',
         'Fruity and sweet green grape craft soju, perfect for sharing.',
         11.90, '/static/images/dishes/boissons_all.jpg', '', '', '', '', 1, 4),

        (cat_map['boissons'], 'Ramune Original / Yuzu (20cl)', 'Nước Ngọt Bật Bi Ramune Nhật', 'Japanese Ramune Marble Soda (20cl)', 'ラムネ',
         'Limonade pétillante culte du Japon avec sa fameuse bille de verre dans le goulot. Parfum Original ou Yuzu acidulé.',
         'Nước ngọt có ga truyền thống trứ danh của các lễ hội Nhật với viên bi thủy tinh độc đáo, vị nguyên bản hoặc quýt Yuzu thơm ngát.',
         'Famous nostalgic Japanese marble soda in Original or aromatic Yuzu citrus flavour.',
         4.90, '/static/images/dishes/boissons_all.jpg', 'TYPIQUE', '', '', 'Original, Yuzu', 1, 5),

        (cat_map['boissons'], 'Thé vert japonais Oishi (50cl)', 'Trà xanh thanh nhiệt Oishi', 'Oishi Japanese Green Tea (50cl)', 'お茶',
         'Thé vert japonais authentique infusé, désaltérant et riche en antioxydants naturels.',
         'Trà xanh đóng chai tươi mát của Nhật Bản, thanh lọc cơ thể và giải nhiệt.',
         'Authentic brewed Japanese green tea, refreshing and antioxidant-rich.',
         4.50, '/static/images/dishes/boissons_all.jpg', '', '', '', '', 1, 6),

        (cat_map['boissons'], 'Euskola Cola Basque (33cl)', 'Nước ngọt Cola xứ Basque Euskola', 'Basque Regional Cola (33cl)', '地元のコーラ',
         'Cola artisanal du Pays Basque, disponible en version classique ou sans sucres.',
         'Sản phẩm đặc sản nước ngọt có ga thủ công của vùng Basque (Anglet/Biarritz).',
         'Local artisan cola crafted in the Basque Country (Regular or Zero Sugar).',
         3.90, '/static/images/dishes/boissons_all.jpg', 'LOCAL', '', '', 'Classique, Zéro sucre', 1, 7),

        (cat_map['boissons'], 'Thé chaud vert Sencha / Jasmin', 'Trà Xanh Nóng Sencha / Trà Lài', 'Hot Japanese Sencha or Jasmine Tea', '温かいお茶',
         'Thé vert japonais sencha servi dans une théière avec ses arômes végétaux subtils.',
         'Trà xanh Sencha nóng pha ấm, ấm cúng và thơm ngát hương thảo mộc phương Đông.',
         'Traditional hot brewed sencha green tea or jasmine blossom tea.',
         3.20, '/static/images/dishes/boissons_all.jpg', '', '', '', 'Thé vert, Jasmin', 1, 8),

        (cat_map['boissons'], 'Café Espresso / Long', 'Cà phê Ý Espresso / Café Long', 'Espresso / Americano Coffee', 'コーヒー',
         'Café torréfié artisanal, court ou allongé.',
         'Cà phê rang xay đậm đà hảo hạng.',
         'Artisan roast espresso or lungo coffee.',
         2.20, '/static/images/dishes/boissons_all.jpg', '', '', '', 'Espresso, Déca, Café Long', 1, 9)
    ]

    cursor.executemany('''
    INSERT INTO dishes (
        category_id, name_fr, name_vi, name_en, kanji,
        description_fr, description_vi, description_en,
        price, image_url, badge, dietary_tags, allergens,
        protein_options, is_available, sort_order
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', dishes_data)

    # Restaurant info
    info_data = (
        1,
        'TokyOh! Anglet',
        "L'énergie de Tokyo dans votre assiette !",
        'Japanese Street Food & Bentos Authentiques',
        '999 allée du Cadran, 64600 Anglet, France',
        'À deux pas des Halles des 5 Cantons',
        '05 59 12 34 56',
        'contact@tokyoh-anglet.fr',
        'Ouvert tous les jours : 11h30 - 14h30 & 18h30 - 22h00',
        'https://www.ubereats.com',
        'https://deliveroo.fr',
        'https://www.instagram.com/tokyoh.anglet',
        'https://www.facebook.com/tokyoh.anglet',
        'https://www.tiktok.com/@tokyoh.anglet',
        "Bienvenue chez TokyOh! Anglet, votre escale gastronomique japonaise sur la côte basque. Situé à deux pas des Halles des 5 Cantons, nous préparons chaque jour des bentos savoureux, croustillants et équilibrés, inspirés de la cuisine de rue tokyoïte. 100% fait maison avec passion !",
        "Chào mừng bạn đến với TokyOh! Anglet, trạm dừng chân ẩm thực Nhật Bản chính gốc tại miền tây nam nước Pháp. Tọa lạc sát khu chợ ẩm thực nổi tiếng Halles des 5 Cantons, chúng tôi phục vụ các set bento tươi ngon, giòn rụm và cân bằng dinh dưỡng theo tinh thần ẩm thực đường phố Tokyo sôi động. 100% nguyên liệu tươi mới mỗi ngày!",
        "Welcome to TokyOh! Anglet, your authentic Japanese culinary stop in southwestern France. Located next to Halles des 5 Cantons, we handcraft hearty, crispy and well-balanced bento boxes every day, bringing the vibrant energy of Tokyo street food to your table. 100% homemade daily!"
    )

    cursor.execute('''
    INSERT INTO restaurant_info (
        id, name, slogan, tagline, address, location_detail, phone, email,
        opening_hours, ubereats_url, deliveroo_url, instagram_url, facebook_url,
        tiktok_url, story_fr, story_vi, story_en
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', info_data)

    # Default Admin User
    admin_pass_hash = hash_password('tokyoh2026')
    cursor.execute('''
    INSERT INTO admin_users (username, password_hash)
    VALUES (?, ?)
    ''', ('admin', admin_pass_hash))

    # Culinary Lexicon
    lexicon_items = [
        ('Bento', '弁当', 'Repas japonais complet et équilibré présenté avec élégance dans une boîte compartimentée.', 'Hộp cơm phần truyền thống đầy đủ dưỡng chất của người Nhật.', 'A balanced, wholesome Japanese meal served in a partitioned box.', 1),
        ('Katsu', 'カツ', 'Viande, crevettes ou tofu pané à la japonaise avec la fameuse chapelure panko extra croustillante.', 'Thịt, tôm hoặc đậu hũ tẩm bột chiên xù kiểu Nhật với bột panko giòn rụm.', 'Meat, prawns or tofu coated in crisp, flaky Japanese panko breadcrumbs and fried golden.', 2),
        ('Tonkatsu', '豚カツ', 'Côtelette de porc tendre panée et frite à la perfection, croustillante à l\'extérieur et juteuse à cœur.', 'Thịt heo cốt lết chiên xù giòn tan bên ngoài, mọng nước ngọt mềm bên trong.', 'Crisp deep-fried breaded pork cutlet.', 3),
        ('Karaage', '唐揚げ', 'Morceaux de poulet marinés au gingembre, ail et soja, puis frits pour un croustillant irrésistible.', 'Thịt gà ướp gừng tỏi sốt đậu nành rồi chiên vàng giòn tan quyến rũ.', 'Japanese style bite-sized ginger & soy marinated fried chicken.', 4),
        ('Ebi fry', 'エビフライ', 'Crevettes royales délicatement étirées, panées au panko et frites.', 'Tôm sú tẩm bột chiên xù vàng óng.', 'Jumbo prawns breaded with panko and deep fried.', 5),
        ('Udon', 'うどん', 'Grosses nouilles japonaises blanches à base de farine de blé, souples, épaisses et réconfortantes.', 'Mì sợi to màu trắng làm từ bột mì, dai mềm đặc trưng xứ Phù Tang.', 'Thick chewy Japanese wheat flour noodles.', 6),
        ('Gyoza', '餃子', 'Raviolis japonais en forme de demi-lune, grillés d\'un côté et moelleux à la vapeur de l\'autre.', 'Bánh há cảo Nhật chiên giòn một mặt và hấp mềm một mặt.', 'Pan-fried crescent dumplings, crispy bottom and steamed top.', 7),
        ('Yakitori', '焼き鳥', 'Brochettes de morceaux de poulet enfilés sur des piques de bambou et grillés au charbon avec sauce teriyaki.', 'Thịt gà xiên que tre nướng than hoa thơm lừng.', 'Charcoal-grilled skewered chicken glazed with tare sauce.', 8),
        ('Takoyaki', 'たこ焼き', 'Boulettes rondes moelleuses garnies de morceaux de poulpe frais, spécialité festive d\'Osaka.', 'Bánh viên nướng nhân bạch tuộc trứ danh của ẩm thực đường phố Osaka.', 'Crispy batter spheres stuffed with diced octopus, famous in Osaka.', 9),
        ('Tataki', 'タタキ', 'Technique culinaire consistant à saisir brièvement un poisson frais à feu vif, laissant le cœur cru et fondant.', 'Kỹ thuật áp chảo nhanh cá tươi bên ngoài chín tái, bên trong giữ nguyên độ tươi ngọt.', 'Fish lightly seared on the outside, leaving the core raw and tender.', 10),
        ('Takuan', '沢庵', 'Radis daikon mariné traditionnel de couleur jaune soleil, croquant et légèrement acidulé.', 'Củ cải trắng muối chua ngọt màu vàng óng giòn sần sật.', 'Crispy bright yellow pickled daikon radish.', 11),
        ('Ajitama', '味玉', 'Œuf mollet mariné dans une sauce au soja, mirin et dashi avec un jaune crémeux et coulant.', 'Trứng lòng đào ngâm tương béo ngậy mặn ngọt đậm đà.', 'Seasoned soft-boiled ramen egg with a jammy yolk.', 12),
        ('Tamagoyaki', '卵焼き', 'Omelette japonaise roulée en plusieurs couches fines, moelleuse et subtilement sucrée.', 'Trứng cuộn nhiều lớp mềm xốp thơm dịu vị dashi.', 'Rolled sweet and savory Japanese layered omelet.', 13),
        ('Mochi', '餅', 'Pâtisserie japonaise ancestrale faite d\'une pâte de riz gluant pilé, douce et élastique.', 'Bánh dẻo làm từ gạo nếp giã nhuyễn dẻo mịn thanh ngọt.', 'Traditional soft, chewy rice cake treat.', 14),
        ('Taiyaki', 'たい焼き', 'Gâteau gaufré doré en forme de dorade japonaise (symbole de chance), garni de pâte de haricots rouges.', 'Bánh quế nướng hình cá tráp may mắn nhân đậu đỏ thơm bùi.', 'Fish-shaped cake filled with sweet azuki paste.', 15),
        ('Ramune', 'ラムネ', 'Limonade rafraîchissante culte des matsuri (fêtes japonaises), fermée par une bille de verre que l\'on pousse pour ouvrir.', 'Nước ngọt có ga truyền thống có viên bi thủy tinh ở cổ chai độc đáo.', 'Classic Japanese carbonated beverage sealed with a glass marble.', 16)
    ]

    cursor.executemany('''
    INSERT INTO lexicon (term, kanji, definition_fr, definition_vi, definition_en, sort_order)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', lexicon_items)

    # Allergens Guide
    allergens_data = [
        ('Gluten', 'Gluten (Lúa mì)', 'Gluten (Wheat)', '🌾', '', 'Panure panko', 'Bột xù panko', 'Panko breadcrumbs', 1),
        ('Crustacés', 'Giáp xác (Tôm, Cua)', 'Crustaceans', '🦐', '', 'Ebi fry', 'Tôm chiên xù Ebi fry', 'Crispy ebi prawns', 2),
        ('Poissons', 'Cá biển', 'Fish', '🐟', '', 'Tataki thon', 'Cá ngừ áp chảo tataki', 'Tuna tataki', 3),
        ('Mollusques', 'Mực & Bạch tuộc', 'Molluscs (Squid)', '🐙', '', 'Takoyaki poulpe', 'Bánh mực & bạch tuộc Takoyaki', 'Octopus & squid', 4),
        ('Soja', 'Đậu nành & Tàu hũ', 'Soy & Tofu', '🫘', '', 'Miso, shoyu, tofu', 'Súp miso, tàu hũ, xì dầu', 'Miso broth, tofu, soy', 5),
        ('Œufs', 'Trứng', 'Eggs', '🥚', '', 'Tamago, mayo', 'Trứng cuộn tamago, sốt mayo', 'Tamago omelet, mayo', 6),
        ('Lait', 'Sữa & Phô mai', 'Milk & Dairy', '🥛', '', 'Beef cheese', 'Bò cuộn phô mai', 'Beef cheese skewers', 7),
        ('Moutarde', 'Mù tạt', 'Mustard', '🟡', '', 'Sauces curry', 'Sốt cà ri, mù tạt', 'Curry sauces', 8),
        ('Céleri', 'Rau cần tây & Nước hầm', 'Celery & Herbs', '🌿', '', 'Bouillons', 'Nước dùng rau củ hầm', 'Vegetable broths', 9),
        ('Sésame', 'Hạt mè & Dầu mè', 'Sesame', '🌰', '', 'Huile & graines', 'Dầu mè & hạt mè rang', 'Toasted sesame oil & seeds', 10)
    ]

    cursor.executemany('''
    INSERT INTO allergens (name_fr, name_vi, name_en, icon, image_url, example_dish_fr, example_dish_vi, example_dish_en, sort_order)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', allergens_data)

if __name__ == '__main__':
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    print('Database initialized successfully at:', DB_PATH)
