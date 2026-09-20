"""
Leo Carter Poster Vault - Online Database Backend
Python Flask + SQL (SQLite) - Permanent Storage
Deploy this FREE on Render.com or Railway.app
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import base64

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Database Config - SQLite (permanent file)
# On Render, this will be stored in persistent disk
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'leocarter.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Poster Model - Table structure
class Poster(db.Model):
    id = db.Column(db.String(100), primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    short_title = db.Column(db.String(100))
    description = db.Column(db.Text)
    category = db.Column(db.String(100), nullable=False)  # Food, Abstract, Nature, etc.
    type = db.Column(db.String(20), default='free')  # free or premium
    price = db.Column(db.Float, default=0)
    image_url = db.Column(db.Text, nullable=False)  # Base64 or URL
    tags = db.Column(db.Text)  # comma separated
    downloads = db.Column(db.Integer, default=0)
    featured = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.String(100), default='user')  # user or admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'short_title': self.short_title,
            'description': self.description,
            'category': self.category,
            'type': self.type,
            'price': self.price,
            'image_url': self.image_url,
            'image': self.image_url,  # for frontend compatibility
            'tags': self.tags.split(',') if self.tags else [],
            'downloads': self.downloads,
            'featured': self.featured,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat()
        }

# Create tables
with app.app_context():
    db.create_all()
    # Add default burger poster if not exists
    if not Poster.query.get('burger-fresh-best'):
        burger = Poster(
            id='burger-fresh-best',
            title='Fresh & Best Burger - Gourmet Cheeseburger Poster',
            short_title='Fresh Best Burger',
            description='Fresh and best Burger! Crispy Garlic Butter Shrimp style cheeseburger poster. Juicy beef patty with melted cheese, fresh lettuce, tomatoes, red onion and pickles. Perfect for cafe, restaurant menu, food delivery.',
            category='Food & Restaurant',
            type='free',
            image_url='',  # Will be filled by frontend with base64
            tags='burger,food,restaurant,cafe,fast food',
            downloads=127,
            featured=True,
            created_by='admin'
        )
        db.session.add(burger)
        db.session.commit()
        print("Default burger poster created")

# API Routes

@app.route('/')
def home():
    return jsonify({
        'message': 'Leo Carter Poster Vault API - Online Database Active',
        'endpoints': {
            'GET /api/posters': 'Get all posters',
            'POST /api/posters': 'Add new poster (anyone can post)',
            'DELETE /api/posters/<id>': 'Delete poster (admin only - needs admin_key)',
            'POST /api/posters/<id>/download': 'Increment download count',
            'GET /api/categories': 'Get all categories'
        }
    })

@app.route('/api/posters', methods=['GET'])
def get_posters():
    """Get all posters - for everyone"""
    category = request.args.get('category')
    search = request.args.get('search')
    query = Poster.query
    
    if category and category != 'All':
        query = query.filter_by(category=category)
    
    if search:
        query = query.filter(Poster.title.contains(search) | Poster.description.contains(search))
    
    posters = query.order_by(Poster.created_at.desc()).all()
    return jsonify([p.to_dict() for p in posters])

@app.route('/api/posters', methods=['POST'])
def add_poster():
    """Add new poster - anyone can add, saves permanently"""
    data = request.json
    
    # Required fields
    if not data.get('title') or not data.get('image_url'):
        return jsonify({'error': 'Title and image_url required'}), 400
    
    # Generate ID from title
    import re
    poster_id = re.sub(r'[^a-z0-9]+', '-', data['title'].lower()).strip('-') + '-' + datetime.now().strftime('%Y%m%d%H%M%S')
    
    new_poster = Poster(
        id=poster_id,
        title=data['title'],
        short_title=data.get('short_title', data['title'][:30]),
        description=data.get('description', ''),
        category=data.get('category', 'General'),
        type=data.get('type', 'free'),
        price=data.get('price', 0),
        image_url=data['image_url'],
        tags=','.join(data.get('tags', [])) if isinstance(data.get('tags'), list) else data.get('tags', ''),
        created_by=data.get('created_by', 'user'),
        featured=data.get('featured', False)
    )
    
    db.session.add(new_poster)
    db.session.commit()
    
    return jsonify(new_poster.to_dict()), 201

@app.route('/api/posters/<poster_id>', methods=['DELETE'])
def delete_poster(poster_id):
    """Delete poster - only admin with key"""
    admin_key = request.headers.get('X-Admin-Key') or request.args.get('admin_key')
    
    # Simple admin protection - set your own key in environment
    # Default key: leocarter_admin_2024 - CHANGE IT!
    expected_key = os.environ.get('ADMIN_KEY', 'leocarter_admin_2024')
    
    if admin_key != expected_key:
        return jsonify({'error': 'Unauthorized - Admin key required'}), 403
    
    poster = Poster.query.get(poster_id)
    if not poster:
        return jsonify({'error': 'Poster not found'}), 404
    
    db.session.delete(poster)
    db.session.commit()
    
    return jsonify({'message': 'Poster deleted', 'id': poster_id})

@app.route('/api/posters/<poster_id>/download', methods=['POST'])
def increment_download(poster_id):
    """Increment download count when someone downloads"""
    poster = Poster.query.get(poster_id)
    if not poster:
        return jsonify({'error': 'Poster not found'}), 404
    
    poster.downloads += 1
    db.session.commit()
    
    return jsonify({'downloads': poster.downloads})

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories"""
    categories = db.session.query(Poster.category).distinct().all()
    return jsonify([c[0] for c in categories])

@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    """Admin stats - only you can see"""
    admin_key = request.headers.get('X-Admin-Key') or request.args.get('admin_key')
    expected_key = os.environ.get('ADMIN_KEY', 'leocarter_admin_2024')
    
    if admin_key != expected_key:
        return jsonify({'error': 'Unauthorized'}), 403
    
    total_posters = Poster.query.count()
    total_downloads = db.session.query(db.func.sum(Poster.downloads)).scalar() or 0
    categories = Poster.query.with_entities(Poster.category, db.func.count(Poster.id)).group_by(Poster.category).all()
    
    return jsonify({
        'total_posters': total_posters,
        'total_downloads': total_downloads,
        'by_category': {cat: count for cat, count in categories},
        'recent_posters': [p.to_dict() for p in Poster.query.order_by(Poster.created_at.desc()).limit(5).all()]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
