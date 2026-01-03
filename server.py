import os
import secrets
import json
import requests
from flask import Flask, request, jsonify, session, render_template 
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
load_dotenv()

# --- DATABASE CONFIGURATION ---
DB_URI = os.getenv("DB_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent"

app = Flask(__name__)
app.secret_key = secrets.token_hex(24) 
CORS(app, supports_credentials=True)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- DATABASE MODELS -----------------------------------------------------------

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class BlogPost(db.Model):
    """Defines the structure of the blog_posts table."""
    __tablename__ = 'blog_posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=db.func.current_timestamp())
    likes = db.Column(db.Integer, default=0) 
    def to_dict(self):
        """Helper to serialize the blog post for JSON response."""
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "date": self.date.isoformat() if self.date else None,
            "likes": self.likes  # Include likes in dictionary
        }
    
class Place(db.Model):
    """Defines the structure of the places table."""
    __tablename__ = 'places'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True) # Corresponds to 'id' in your JS (e.g., 'taj')
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    rating = db.Column(db.Float)
    reviews = db.Column(db.Integer)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    img_url = db.Column(db.String(500))

    def to_dict(self):
        """Helper to convert DB object to JSON structure your frontend expects"""
        return {
            "id": self.slug,
            "name": self.name,
            "city": self.city,
            "rating": self.rating,
            "reviews": self.reviews,
            "coords": { "lat": self.lat, "lng": self.lng },
            "img": self.img_url
        }

# --- INITIALIZATION ------------------------------------------------------------

def init_db():
    print("INFO: Attempting database connection...")
    try:
        with app.app_context():
            db.create_all()
        print("SUCCESS: Database initialized.")
    except Exception as e:
        print(f"FATAL: Database error: {e}")

with app.app_context():
    init_db()

# --- PLACES ROUTES -------------------------------------------------------------

@app.route('/api/places', methods=['GET'])
def get_places():
    """Fetches all places from the database."""
    try:
        places = Place.query.all()
        # Convert list of DB objects to list of dictionaries
        return jsonify([p.to_dict() for p in places]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# In server.py (Add this new function)
@app.route('/api/blog/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    """Increments the like count for a specific blog post."""
    try:
        post = BlogPost.query.get(post_id)
        if not post:
            return jsonify({"success": False, "message": "Post not found."}), 404
        
        # Simple increment
        post.likes += 1
        db.session.commit()
        return jsonify({"success": True, "likes": post.likes}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error liking post: {e}")
        return jsonify({"success": False, "message": "Failed to like post."}), 500
# In server.py, near your other API routes

@app.route('/api/blogs', methods=['GET'])
def get_all_blogs():
    """Fetches all blog posts from the database."""
    try:
        # Order by date descending (newest first)
        posts = BlogPost.query.order_by(BlogPost.date.desc()).all()
        return jsonify([p.to_dict() for p in posts]), 200
    except Exception as e:
        print(f"Error fetching blogs: {e}")
        return jsonify({"success": False, "message": "Failed to retrieve blog posts."}), 500

@app.route('/api/blog/publish', methods=['POST'])
def publish_blog():
    """Receives blog post data and saves it to the database."""
    data = request.get_json()
    title = data.get('title')
    body = data.get('body')
    
    if not title or not body:
        return jsonify({"success": False, "message": "Title and body are required."}), 400

    new_post = BlogPost(title=title, body=body)
    
    try:
        db.session.add(new_post)
        db.session.commit()
        return jsonify({
            "success": True,
            "message": f"Blog post '{title}' published successfully!",
            "post": new_post.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error publishing blog: {e}")
        return jsonify({"success": False, "message": "Database error while saving post."}), 500

@app.route('/api/seed_places', methods=['GET'])
def seed_places():
    """One-time route to populate the database with your initial data."""
    
    # Your raw data converted to Python dictionaries
    initial_data = [
        { "slug": 'taj', "name": 'Taj Mahal', "city": 'Agra', "rating": 4.9, "reviews": 12451, "lat": 27.1751, "lng": 78.0421, "img": "https://dynamic-media-cdn.tripadvisor.com/media/photo-o/1a/62/a7/48/caption.jpg?w=1200&h=-1&s=1" },
        { "slug": 'hawa', "name": 'Hawa Mahal', "city": 'Jaipur', "rating": 4.6, "reviews": 5312, "lat": 26.9239, "lng": 75.8267, "img": 'https://miro.medium.com/v2/1*fYA-b-KA9UUqPL2OsDYkQw.png' },
        { "slug": 'varanasi', "name": 'Ganges Ghats', "city": 'Varanasi', "rating": 4.7, "reviews": 8200, "lat": 25.3176, "lng": 82.9739, "img": 'https://i0.wp.com/www.tusktravel.com/blog/wp-content/uploads/2019/09/Popular-Ghats-in-Varanasi.jpg?fit=1024%2C682&ssl=1' },
        { "slug": 'goa', "name": 'Baga Beach', "city": 'Goa', "rating": 4.5, "reviews": 4024, "lat": 15.5040, "lng": 73.8175, "img": 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=1400&auto=format&fit=crop' },
        { "slug": 'kerala', "name": 'Backwaters', "city": 'Alleppey', "rating": 4.8, "reviews": 6720, "lat": 9.4981, "lng": 76.3388, "img": 'https://dynamic-media-cdn.tripadvisor.com/media/photo-o/13/5e/59/d4/alleppey-backwater-tour.jpg?w=800&h=-1&s=1' },
        { "slug": 'goa2', "name": 'Palolem Beach', "city": 'Goa', "rating": 4.6, "reviews": 2481, "lat": 15.0066, "lng": 73.9865, "img": 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?q=80&w=1400&auto=format&fit=crop' },
        { "slug": 'mysore', "name": "Mysore Palace", "city": "Mysore", "rating": 4.7, "reviews": 2345, "lat": 12.3039, "lng": 76.6547, "img": "https://indiano.travel/wp-content/uploads/2022/04/Beautiful-View-of-Mysore-Palace-in-sunset.jpg" },
        { "slug": 'ayodhya', "name": "Ayodhya Ram Mandir", "city": "Ayodhya", "rating": 5, "reviews": 1234, "lat": 26.7956, "lng": 82.1944, "img": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/df/Ayodhya_Ram_Mandir_Inauguration_Day_Picture.jpg/1200px-Ayodhya_Ram_Mandir_Inauguration_Day_Picture.jpg" },
        { "slug": "madurai", "name": "Madurai Meenakshi Temple", "city": "Madurai", "rating": 4.5, "reviews": 3456, "lat": 9.9195, "lng": 78.1193, "img": "https://static.toiimg.com/photo/107052733.cms" },
        { "slug": "shiridi", "name": "Shiridi Sai Baba Temple", "city": "Shiridi", "rating": 4, "reviews": 3535, "lat": 19.7662, "lng": 74.4770, "img": "https://content.jdmagicbox.com/v2/comp/mumbai/z2/022pxx22.xx22.221117045316.t5z2/catalogue/shirdi-shri-sai-baba-temple-mumbai-temples-D4VGxNgL2D.jpg" },
        { "slug": "raipur", "name": "Tribal Museum", "city": "Raipur", "rating": 3.9, "reviews": 455, "lat": 21.164993, "lng": 81.775307, "img": "https://images.bhaskarassets.com/web2images/521/2025/05/16/whatsapp-image-2025-05-16-at-44019-pm-2_1747397006.jpeg" },
        { "slug": "kashi", "name": "Kashi Vishwanath Temple", "city": "Varanasi", "rating": 4.6, "reviews": 657, "lat": 25.3109, "lng": 83.0107, "img": "https://www.daiwikhotels.com/wp-content/uploads/2024/07/kashi-viswanath-temple-cvr-2.jpg" },
        { "slug": "lotus", "name": "Lotus Temple", "city": "New Delhi", "rating": 4, "reviews": 242, "lat": 28.5535, "lng": 77.2588, "img": "https://wanderon-images.gumlet.io/blogs/new/2024/04/lotus-temple.jpg" },
        { "slug": "kerala2", "name": "Padmanabhaswamy Temple", "city": "Thiruvananthapur", "rating": 4.3, "reviews": 4568, "lat": 8.4828, "lng": 76.9436, "img": "https://cf-img-a-in.tosshub.com/sites/visualstory/wp/2025/02/Padmanabhaswamy-Temple-1ITG-1739422643402.jpeg?size=*:900" },
        { "slug": "goa3", "name": "Basilica Of Bom Jeseus church", "city": "Goa", "rating": 4.6, "reviews": 4568, "lat": 15.5008, "lng": 73.9114, "img": "https://www.rvasia.org/sites/default/files/2024-06/basilica_of_bom_jesus.jpg" },
        { "slug": "chitrakote", "name": "Chitrakote Waterfalls", "city": "Bastar", "rating": 4.9, "reviews": 786, "lat": 19.2072, "lng": 81.7001, "img": "https://www.shutterstock.com/image-photo/chitrakoot-waterfall-jagdalpur-natural-widest-600nw-2294068255.jpg" },
        { "slug": "ramoji", "name": "Ramoji Film City", "city": "Hyderabad", "rating": 4.3, "reviews": 3456, "lat": 17.2641, "lng": 78.6818, "img": "https://www.paisawapas.com/scroll-time/wp-content/uploads/2023/12/Ramoji-Film-City-Hyderabad.jpg" },
        { "slug": "golconda", "name": "Golconda Fort", "city": "Hyderabad", "rating": 4.1, "reviews": 678, "lat": 17.3833, "lng": 78.4011, "img": "https://s7ap1.scene7.com/is/image/incredibleindia/golconda-fort-hyderabad-secunderabad-telangana-3-musthead-hero?qlt=82&ts=1742197014098" },
        { "slug": "puri", "name": "Jagganath Puri Temple", "city": "Puri", "rating": 4.7, "reviews": 2345, "lat": 19.8, "lng": 85.82, "img": "https://organiser.org/wp-content/uploads/2024/07/11-2-1-jpg.webp" },
        { "slug": "sikkim", "name": "Yumthang Valley Of Flowers", "city": "Sikkim", "rating": 4.5, "reviews": 986, "lat": 27.8268, "lng": 88.6958, "img": "https://static.toiimg.com/photo/msid-66679081,width-96,height-65.cms" },
        { "slug": "coorg", "name": "Coorg", "city": "Coorg", "rating": 5, "reviews": 6788, "lat": 12.4244, "lng": 75.7382, "img": "https://www.theindia.co.in/blog/wp-content/uploads/2025/06/Tourist-Places-to-Visit-in-Coorg-1.jpg" },
        { "slug": "kullu", "name": "Manikarnan Geothermal Spring", "city": "Kullu", "rating": 4.3, "reviews": 1234, "lat": 32.0306, "lng": 77.3528, "img": "https://static.toiimg.com/thumb/105307305/Manikaran-Himachal-Pradesh.jpg?width=1200&height=900" },
        { "slug": "jama", "name": "Jama Masijid", "city": "Delhi", "rating": 4.6, "reviews": 5678, "lat": 28.6507, "lng": 77.2334, "img": "https://lp-cms-production.imgix.net/2019-06/c6e8881b27f038f983b0ff40154abbfc-jama-masjid.jpg" },
        { "slug": "simhachalam", "name": "Simhachalam Temple", "city": "Vishakhapatnam", "rating": 4.7, "reviews": 9854, "lat": 17.7664, "lng": 83.2505, "img": "https://img.etimg.com/thumb/msid-116600255,width-640,height-480,imgsize-1860232,resizemode-4/simhachalam-temple.jpg" }
    ]

    try:
        # Check if DB is already empty to prevent duplicates
        if Place.query.first():
            return jsonify({"message": "Database already has data. Skipping seed."})

        for item in initial_data:
            p = Place(
                slug=item['slug'],
                name=item['name'],
                city=item['city'],
                rating=item['rating'],
                reviews=item['reviews'],
                lat=item['lat'],
                lng=item['lng'],
                img_url=item['img']
            )
            db.session.add(p)
        
        db.session.commit()
        return jsonify({"success": True, "message": f"Added {len(initial_data)} places to database."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# --- EXISTING ROUTES (Auth, Chat, etc.) ----------------------------------------
# ... (Paste your existing Register, Login, Logout, Status, Protected, and Chat routes here)
# ... (Include the User model logic from your previous code)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    username = email.split('@')[0] if email else None

    if not all([username, email, password]):
        return jsonify({"success": False, "message": "Missing fields"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email registered."}), 409

    password_hash = generate_password_hash(password)
    new_user = User(username=username, email=email, password_hash=password_hash)
    try:
        db.session.add(new_user)
        db.session.commit()
        session['user_id'] = new_user.id
        session['username'] = username
        return jsonify({"success": True, "message": "Registered & Logged in.", "email": email}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    if not all([email, password]): return jsonify({"success": False, "message": "Missing fields"}), 400
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({"success": True, "message": "Login successful.", "email": email}), 200
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out"}), 200

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '')
    if not user_message: return jsonify({"reply": "Please provide a message."}), 400
    
    system_prompt = "You are 'Soulful Journey', an expert travel guide for India."
    payload = {
        "contents": [{"parts": [{"text": user_message}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }
    try:
        response = requests.post(f"{GEMINI_API_URL}?key={GEMINI_API_KEY}", headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        if not response.ok: return jsonify({"reply": f"API Error: {response.status_code}"}), 500
        return jsonify({"reply": response.json()['candidates'][0]['content']['parts'][0]['text']}), 200
    except Exception as e:
        return jsonify({"reply": "Server Error."}), 500

@app.route('/')
def serve_index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)