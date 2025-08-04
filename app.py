#!/usr/bin/env python3
"""
NuestrasRecetas.club - Git for Food Platform
Revolutionary recipe version control system with forking, branching, and collaboration
Flask app using Supabase directly without SQLAlchemy
"""

import html
import json
import re
import os
from collections import defaultdict
from typing import Optional, Dict, Any
from functools import wraps
from datetime import datetime, timezone

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from supabase import create_client, Client
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from config import Config

# Security helper functions
def sanitize_input(text: str, max_length: int = 500) -> str:
    """Sanitize user input by removing HTML tags and limiting length"""
    if not text:
        return ""
    # Remove HTML tags and decode HTML entities
    sanitized = html.escape(text.strip())
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    return sanitized

config = Config()

# Units for recipe calculations
UNIT_ALIASES = {
    "g": ["g", "gram", "grams"],
    "kg": ["kg", "kilogram", "kilograms"],
    "ml": ["ml", "milliliter", "milliliters"],
    "l": ["l", "liter", "liters"],
    "tbsp": ["tbsp", "tablespoon", "tablespoons"],
    "tsp": ["tsp", "teaspoon", "teaspoons"],
    "cup": ["cup", "cups"],
    "pc": ["pc", "piece", "pieces"],
}
CAN_AGGREGATE = {"g", "kg", "ml", "l", "tbsp", "tsp", "cup", "pc"}

def normalize_unit(u: str) -> str:
    u = (u or "").strip().lower()
    for base, aliases in UNIT_ALIASES.items():
        if u in aliases:
            return base
    return u

def convert_qty(qty: float, unit_from: str, unit_to: str) -> Optional[float]:
    unit_from = normalize_unit(unit_from)
    unit_to = normalize_unit(unit_to)
    if unit_from == unit_to:
        return qty
    if unit_from == "g" and unit_to == "kg":
        return qty / 1000.0
    if unit_from == "kg" and unit_to == "g":
        return qty * 1000.0
    if unit_from == "ml" and unit_to == "l":
        return qty / 1000.0
    if unit_from == "l" and unit_to == "ml":
        return qty * 1000.0
    spoon = {"tsp": 1.0, "tbsp": 3.0, "cup": 48.0}
    if unit_from in spoon and unit_to in spoon:
        tsp_qty = qty * spoon[unit_from]
        return tsp_qty / spoon[unit_to]
    return None

def try_aggregate(items):
    grouped = defaultdict(list)
    for name, qty, unit in items:
        name_key = name.strip().lower()
        unit_norm = normalize_unit(unit)
        grouped[(name_key, unit_norm)].append(qty)

    result = []
    for (name_key, unit_norm), qtys in grouped.items():
        if unit_norm in CAN_AGGREGATE:
            total = sum(qtys)
            if unit_norm in ("g", "ml") and total >= 1000:
                new_unit = "kg" if unit_norm == "g" else "l"
                conv = convert_qty(total, unit_norm, new_unit)
                if conv is not None:
                    total = conv
                    unit_norm = new_unit
            total = round(total, 2)
            result.append((name_key, total, unit_norm))
        else:
            for q in qtys:
                result.append((name_key, q, unit_norm))
    result.sort(key=lambda x: x[0])
    return result

# Initialize Sentry for error monitoring
sentry_dsn = os.getenv('SENTRY_DSN')
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration(transaction_style="endpoint")],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        profiles_sample_rate=0.1,  # 10% for profiling
        environment=os.getenv('ENVIRONMENT', 'production'),
        release=os.getenv('SENTRY_RELEASE', 'unknown'),
    )

# Development authentication bypass and test users
DEV_USERS = {
    'dev@test.com': {
        'id': '00000000-0000-0000-0000-000000000001',
        'email': 'dev@test.com',
        'password': 'dev123',
        'name': 'Dev User',
        'username': 'devuser',
        'avatar_url': '',
        'is_dev': True
    },
    'alice@test.com': {
        'id': '00000000-0000-0000-0000-000000000002', 
        'email': 'alice@test.com',
        'password': 'alice123',
        'name': 'Alice Chef',
        'username': 'alicechef',
        'avatar_url': '',
        'is_dev': True
    },
    'bob@test.com': {
        'id': '00000000-0000-0000-0000-000000000003',
        'email': 'bob@test.com', 
        'password': 'bob123',
        'name': 'Bob Cook',
        'username': 'bobcook',
        'avatar_url': '',
        'is_dev': True
    }
}

def is_development():
    """Check if we're running in development mode"""
    return (os.getenv('ENVIRONMENT') == 'development' or 
            os.getenv('FLASK_ENV') == 'development' or 
            os.getenv('PURE_DEV_MODE') == 'true')

def use_database():
    """Check if we should use the database (not mock data)"""
    return (os.getenv('USE_DATABASE') == 'true' or 
            os.getenv('ENVIRONMENT') == 'production' or
            os.getenv('FLASK_ENV') == 'production' or
            not is_development())

def get_supabase_client():
    """Get appropriate Supabase client (service client for dev users, regular for others)"""
    current_user = get_current_user()
    if current_user and current_user.get('is_dev') and supabase_service:
        return supabase_service
    return supabase

def is_dev_user(user):
    """Check if user is a development user"""
    return user and user.get('is_dev', False)

def ensure_dev_users_in_db():
    """Ensure development users exist in the profiles table"""
    if not supabase_service:
        return
    
    for email, user_data in DEV_USERS.items():
        try:
            # Check if user exists
            existing = supabase_service.table('profiles').select('*').eq('id', user_data['id']).execute()
            if not existing.data:
                # Create profile
                profile_data = {
                    'id': user_data['id'],
                    'username': user_data['username'],
                    'name': user_data['name'],
                    'bio': f'Development user - {user_data["name"]}',
                    'avatar_url': user_data['avatar_url'],
                    'is_public': True
                }
                result = supabase_service.table('profiles').insert(profile_data).execute()
                print(f"✅ Created dev user profile: {user_data['username']}")
        except Exception as e:
            print(f"⚠️  Error creating dev user {user_data['username']}: {e}")

# Load development data - kept for development authentication only
DEV_RECIPES = []
DEV_POSTS = []

# Flask app
app = Flask(__name__)
app.config.from_object(config)
# Configure CORS with specific origins for production security
allowed_origins = [
    "https://nuestrasrecetas.club",
    "https://www.nuestrasrecetas.club"
]

if config.FLASK_ENV == 'development':
    allowed_origins.extend(["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"])
    # Development session configuration for better persistence
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True

CORS(app, 
     origins=allowed_origins,
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Initialize Supabase client
supabase: Optional[Client] = None
supabase_service: Optional[Client] = None
if config.use_supabase:
    try:
        supabase = create_client(
            supabase_url=config.SUPABASE_URL,
            supabase_key=config.SUPABASE_KEY
        )
        print("✅ Supabase client initialized")
        
        # Initialize service client for bypassing RLS
        if config.SUPABASE_SERVICE_KEY:
            supabase_service = create_client(
                supabase_url=config.SUPABASE_URL,
                supabase_key=config.SUPABASE_SERVICE_KEY
            )
            print("✅ Supabase service client initialized")
        else:
            print("⚠️  Supabase service key not configured")
            
    except Exception as e:
        print(f"⚠️  Supabase initialization failed: {e}")
        supabase = None
        supabase_service = None
else:
    print("❌ Supabase not configured - check .env file")

# Ensure dev users exist in database for development mode
if is_development() and supabase_service:
    ensure_dev_users_in_db()

def get_current_user():
    """Get current user from Supabase session or development session"""
    user_id = session.get('user_id')
    
    # Debug logging
    print(f"🔧 get_current_user() called. is_development(): {is_development()}, user_id: {user_id}, is_dev_user: {session.get('is_dev_user')}")
    
    # Check for dev user session first (regardless of mode)
    if session.get('is_dev_user'):
        dev_user_data = session.get('dev_user_data')
        # TODO: Add input validation to prevent session manipulation in dev mode
        if dev_user_data and dev_user_data['id'] == user_id:
            # Debug log for development
            print(f"🔧 Dev auth success for: {dev_user_data.get('email')}")
            return dev_user_data
        else:
            # Clear invalid dev session
            print(f"🔧 Dev auth failed - clearing session. user_id: {user_id}, dev_data: {bool(dev_user_data)}")
            session.pop('user_id', None)
            session.pop('is_dev_user', None)
            session.pop('dev_user_data', None)
            return None
    
    # Production mode - use Supabase
    access_token = session.get('supabase_access_token')
    
    if not user_id or not access_token or not supabase:
        return None
    
    try:
        # Set the auth token for this request
        supabase.auth.set_session(access_token, session.get('supabase_refresh_token'))
        
        # Get current user from Supabase
        supabase_user = supabase.auth.get_user()
        if not supabase_user.user or supabase_user.user.id != user_id:
            # Token invalid or user mismatch, clear session
            session.pop('user_id', None)
            session.pop('supabase_access_token', None)
            session.pop('supabase_refresh_token', None)
            return None
            
        # Get user profile from Supabase profiles table
        profile_response = supabase.table('profiles').select('*').eq('id', user_id).execute()
        if profile_response.data and len(profile_response.data) > 0:
            return profile_response.data[0]
        else:
            return None
    except Exception as e:
        print(f"Auth error: {e}")
        # Token expired or invalid, clear session
        session.pop('user_id', None)
        session.pop('supabase_access_token', None)
        session.pop('supabase_refresh_token', None)
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In development mode, allow access if Supabase is not configured but dev user exists
        if is_development():
            current_user = get_current_user()
            if current_user:
                return f(*args, **kwargs)
            else:
                return jsonify({"error": "Authentication required"}), 401
        
        # Production mode - require Supabase
        if not supabase:
            return jsonify({"error": "Supabase not configured"}), 500
        if not get_current_user():
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route("/")
def landing():
    # If user is logged in, redirect to dashboard
    if get_current_user():
        return redirect(url_for('dashboard'))
    return render_template("landing.html")

@app.route("/dashboard")
def dashboard():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('landing'))
    return render_template("index.html", user=current_user)

@app.route("/profile")
def my_profile():
    """Redirect to current user's profile"""
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('landing'))
    
    username = current_user.get('username') or current_user.get('email', '').split('@')[0]
    return redirect(url_for('profile_page', username=username))

@app.route("/profile/<username>")
def profile_page(username):
    return render_template('profile.html')

@app.route("/community")
def community_page():
    return render_template('community.html')

@app.route("/groups")
def groups_page():
    return render_template('groups.html')

@app.route("/group/<group_id>")
def group_page(group_id):
    return render_template('group.html')

@app.route("/recipes")
def recipes_page():
    """Recipe browser page - shows all public recipes"""
    return render_template('recipes.html')

@app.route("/recipe/<int:recipe_id>")
def recipe_detail_page(recipe_id):
    """Recipe detail page - shows individual recipe"""
    # Create a recipe detail template that loads the specific recipe
    return render_template('recipe_detail.html', recipe_id=recipe_id)

@app.route("/activity")
@require_auth
def activity_page():
    """User activity feed page - personal activity feed"""
    return render_template('activity.html')

@app.route("/health")
def health_check():
    """Health check endpoint"""
    try:
        # Check Supabase connection
        if supabase:
            # Test Supabase connection
            response = supabase.table('profiles').select('count', count='exact').execute()
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "supabase": "enabled",
                "sentry": "enabled" if os.getenv('SENTRY_DSN') else "disabled",
                "profiles_count": response.count
            })
        else:
            return jsonify({
                "status": "unhealthy",
                "error": "Supabase not configured"
            }), 503
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

# Authentication Routes
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    # TODO: Implement rate limiting to prevent brute force attacks
    if not supabase:
        return jsonify({"error": "Supabase no configurado"}), 500
        
    data = request.json or {}
    
    # Validate required fields
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    
    if not all([name, username, email, password]):
        return jsonify({"error": "Todos los campos son requeridos"}), 400
        
    # Enhanced input validation
    if len(name.strip()) > 100:
        return jsonify({"error": "El nombre no puede exceder 100 caracteres"}), 400
        
    if len(username.strip()) > 50:
        return jsonify({"error": "El nombre de usuario no puede exceder 50 caracteres"}), 400
        
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({"error": "El nombre de usuario solo puede contener letras, números y guiones bajos"}), 400
        
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({"error": "Formato de email inválido"}), 400
        
    if len(password) < 8:
        return jsonify({"error": "La contraseña debe tener al menos 8 caracteres"}), 400
        
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        return jsonify({"error": "La contraseña debe contener al menos una letra y un número"}), 400
    
    try:
        # Check if username is already taken
        existing_user = supabase.table('profiles').select('username').eq('username', username).execute()
        if existing_user.data:
            return jsonify({"error": "Este nombre de usuario ya está en uso"}), 400
        
        # Create user with Supabase Auth
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "name": name,
                    "username": username
                }
            }
        })
        
        if response.user:
            return jsonify({
                "message": "Cuenta creada exitosamente. Revisa tu email para confirmar tu cuenta.",
                "user_id": response.user.id
            })
        else:
            return jsonify({"error": "Error al crear la cuenta"}), 400
    
    except Exception as e:
        error_msg = str(e)
        if "already been registered" in error_msg:
            return jsonify({"error": "Ya existe una cuenta con este email"}), 400
        return jsonify({"error": f"Error al crear la cuenta: {error_msg}"}), 500

@app.route("/api/auth/login", methods=["POST"])
def login():
    # TODO: Implement rate limiting for login attempts
    # TODO: Add monitoring/alerting for repeated failed login attempts
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email y contraseña son requeridos"}), 400
    
    # Development mode - check DEV_USERS first
    if is_development() and email in DEV_USERS:
        dev_user = DEV_USERS[email]
        if dev_user['password'] == password:
            # Create development session
            session['user_id'] = dev_user['id']
            session['is_dev_user'] = True
            session['dev_user_data'] = dev_user
            
            return jsonify({
                "message": "Inicio de sesión exitoso (desarrollo)",
                "user": {
                    "id": dev_user['id'],
                    "email": dev_user['email'],
                    "name": dev_user['name'],
                    "username": dev_user['username'],
                    "avatar_url": dev_user['avatar_url'],
                    "is_dev": True
                }
            })
        else:
            return jsonify({"error": "Credenciales inválidas"}), 401
    
    # Production mode or non-dev user - use Supabase
    if not supabase:
        return jsonify({"error": "Supabase no configurado"}), 500
    
    try:
        # Sign in with Supabase Auth
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user and response.session:
            # Store session in Flask session
            session['supabase_access_token'] = response.session.access_token
            session['supabase_refresh_token'] = response.session.refresh_token
            session['user_id'] = response.user.id
            
            # Get user profile from Supabase profiles table
            try:
                profile_response = supabase.table('profiles').select('*').eq('id', response.user.id).execute()
                
                if profile_response.data and len(profile_response.data) > 0:
                    # Update last active
                    supabase.table('profiles').update({
                        'last_active': 'now()'
                    }).eq('id', response.user.id).execute()
                    
                    user_profile = profile_response.data[0]
                else:
                    # Fallback to user metadata if profile doesn't exist yet
                    user_profile = {
                        "id": response.user.id,
                        "email": response.user.email,
                        "name": response.user.user_metadata.get("name", ""),
                        "username": response.user.user_metadata.get("username", "")
                    }
                
                return jsonify({
                    "message": "Inicio de sesión exitoso",
                    "user": user_profile
                })
            except Exception as e:
                print(f"Profile fetch error: {e}")
                return jsonify({
                    "message": "Inicio de sesión exitoso",
                    "user": {
                        "id": response.user.id,
                        "email": response.user.email,
                        "name": response.user.user_metadata.get("name", ""),
                        "username": response.user.user_metadata.get("username", "")
                    }
                })
        else:
            return jsonify({"error": "Credenciales inválidas"}), 401
    
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid login credentials" in error_msg:
            return jsonify({"error": "Credenciales inválidas"}), 401
        elif "email not confirmed" in error_msg:
            # For testing purposes, create a temporary workaround
            return jsonify({"error": "Por favor confirma tu email antes de iniciar sesión. Para testing, usa un email confirmado."}), 401
        print(f"Login error: {error_msg}")  # Debug log
        return jsonify({"error": f"Error al iniciar sesión: {error_msg}"}), 500

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    # Clear development session if exists
    if session.get('is_dev_user'):
        session.pop('is_dev_user', None)
        session.pop('dev_user_data', None)
    
    # Clear Supabase session if exists
    if supabase and session.get('supabase_access_token'):
        try:
            supabase.auth.sign_out()
        except:
            pass  # Continue even if Supabase signout fails
    
    # Clear Flask session
    session.pop('supabase_access_token', None)
    session.pop('supabase_refresh_token', None)
    session.pop('user_id', None)
    
    return jsonify({"message": "Sesión cerrada exitosamente"})

@app.route("/api/auth/me", methods=["GET"])
def get_current_user_info():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "No authenticated"}), 401
    
    return jsonify({"user": current_user})


# Recipe Routes
@app.route("/api/recipes", methods=["GET"])
def list_recipes():
    # TODO: Add pagination for better performance with large recipe collections
    try:
        q = request.args.get("q", "").strip().lower()
        current_user = get_current_user()
        
        print(f"Current user: {current_user}")  # Debug log
        
        # Get recipes from Supabase using optimized recipe_details view
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
            
        try:
            # Use recipe_details view for optimized queries with user info - show all public recipes
            query = supabase.table('recipe_details').select('*')
            
            # Apply search filter if provided
            if q:
                query = query.or_(f'title.ilike.%{q}%,category.ilike.%{q}%,tags.ilike.%{q}%')
            
            response = query.execute()
            recipes = response.data or []
        except Exception as e:
            print(f"Error fetching recipes: {e}")
            # If there's a schema mismatch, return empty list for now
            recipes = []
        
        out = []
        for r in recipes:
            out.append({
                "id": r['id'],
                "title": r['title'],
                "category": r.get('category', ''),
                "tags": r.get('tags', ''),
                "servings": r.get('servings', 2),
                # Include additional data from recipe_details view when available
                "username": r.get('username', ''),
                "user_name": r.get('user_name', ''),
                "like_count": r.get('like_count', 0),
                "comment_count": r.get('comment_count', 0),
                "created_at": r.get('created_at'),
                "updated_at": r.get('updated_at')
            })
        
        print(f"Returning {len(out)} recipes")  # Debug log
        return jsonify(out)
    except Exception as e:
        print(f"Error in list_recipes: {e}")  # Debug log
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipe/<int:rid>", methods=["GET"])
def get_recipe(rid):
    try:
        current_user = get_current_user()
        
        # Get public recipe from Supabase with author info
        response = supabase.table('recipes').select('''
            *,
            author:profiles!recipes_user_id_fkey(username, name, avatar_url)
        ''').eq('id', rid).eq('is_public', True).execute()
        
        if not response.data or len(response.data) == 0:
            return jsonify({"error": "Recipe not found or not public"}), 404
            
        recipe = response.data[0]
        # Parse ingredients JSON
        try:
            recipe['ingredients'] = json.loads(recipe.get('ingredients_json', '[]'))
        except:
            recipe['ingredients'] = []
        
        # Add user interaction data if logged in
        if current_user:
            # Check if user has starred this recipe
            star_response = supabase.table('recipe_stars').select('*').eq('recipe_id', rid).eq('user_id', current_user['id']).execute()
            recipe['is_starred'] = len(star_response.data) > 0
        else:
            recipe['is_starred'] = False
            
        return jsonify(recipe)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipe", methods=["POST"])
@require_auth
def create_recipe():
    try:
        data = request.json or {}
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "Title required"}), 400
        
        # Enhanced input validation for recipe creation
        if len(title) > 200:
            return jsonify({"error": "Title cannot exceed 200 characters"}), 400
            
        category = (data.get("category") or "").strip()
        if len(category) > 100:
            return jsonify({"error": "Category cannot exceed 100 characters"}), 400
            
        tags = (data.get("tags") or "").strip()
        if len(tags) > 500:
            return jsonify({"error": "Tags cannot exceed 500 characters"}), 400
            
        instructions = (data.get("instructions") or "").strip()
        if len(instructions) > 5000:
            return jsonify({"error": "Instructions cannot exceed 5000 characters"}), 400
            
        # Validate servings is reasonable
        servings = int(data.get("servings", 2))
        if servings < 1 or servings > 100:
            return jsonify({"error": "Servings must be between 1 and 100"}), 400
            
        # Validate ingredients
        ingredients = data.get("ingredients", [])
        if len(ingredients) > 50:
            return jsonify({"error": "Recipe cannot have more than 50 ingredients"}), 400
            
        for ingredient in ingredients:
            if isinstance(ingredient, dict):
                ingredient_name = str(ingredient.get('name', '')).strip()
                if len(ingredient_name) > 200:
                    return jsonify({"error": "Ingredient name cannot exceed 200 characters"}), 400
        
        current_user = get_current_user()
        
        # Mock mode - create mock recipe (only if database disabled)
        if not use_database():
            # Check for existing title in dev recipes
            for recipe in DEV_RECIPES:
                if recipe.get('title') == title and recipe.get('user_id') == current_user['id']:
                    return jsonify({"error": "Title already exists"}), 400
            
            # Create new recipe with mock ID
            new_recipe_id = len(DEV_RECIPES) + 1000  # Start dev IDs at 1000
            recipe_data = {
                'id': new_recipe_id,
                'user_id': current_user['id'],
                'title': title,
                'category': category,
                'tags': tags,
                'servings': servings,
                'ingredients_json': json.dumps(ingredients, ensure_ascii=False),
                'steps': data.get("steps", ""),
                'is_public': True,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'version_count': 1,
                'fork_count': 0,
                'star_count': 0
            }
            
            DEV_RECIPES.append(recipe_data)
            print(f"📝 Created dev recipe: {title} (ID: {new_recipe_id})")
            return jsonify({"ok": True, "id": new_recipe_id})
        
        # Database mode - check Supabase is available
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Database not available"}), 500
        
        # Check for existing title
        existing = client.table('recipes').select('id').eq('title', title).eq('user_id', current_user['id']).execute()
        if existing.data:
            return jsonify({"error": "Title already exists"}), 400
        
        # Create recipe with sanitized data
        recipe_data = {
            'user_id': current_user['id'],
            'title': sanitize_input(title, 200),
            'category': sanitize_input(category, 100),
            'tags': sanitize_input(tags, 500),
            'servings': servings,
            'ingredients_json': json.dumps(ingredients, ensure_ascii=False),
            'steps': data.get("steps", "")
        }
        
        response = client.table('recipes').insert(recipe_data).execute()
        
        if response.data:
            recipe_id = response.data[0]['id']
            
            # Create initial version (commit) for the new recipe
            try:
                version_data = {
                    'recipe_id': recipe_id,
                    'version_number': 1,
                    'commit_message': 'Initial recipe creation',
                    'author_id': current_user['id'],
                    'changes_json': {"action": "create"},
                    'snapshot_json': {
                        'title': sanitize_input(title, 200),
                        'description': '',
                        'ingredients': ingredients,
                        'steps': data.get("steps", ""),
                        'servings': servings,
                        'category': sanitize_input(category, 100),
                        'tags': sanitize_input(tags, 500)
                    }
                }
                supabase.table('recipe_versions').insert(version_data).execute()
                
                # Create main branch
                branch_data = {
                    'recipe_id': recipe_id,
                    'branch_name': 'main',
                    'description': 'Main recipe branch',
                    'created_by': current_user['id'],
                    'is_default': True
                }
                branch_response = supabase.table('recipe_branches').insert(branch_data).execute()
                
                # Update recipe with branch reference and version count
                if branch_response.data:
                    supabase.table('recipes').update({
                        'current_branch_id': branch_response.data[0]['id'],
                        'version_count': 1
                    }).eq('id', recipe_id).execute()
                
                # Add creator as contributor
                contributor_data = {
                    'recipe_id': recipe_id,
                    'contributor_id': current_user['id'],
                    'contribution_type': 'creator',
                    'commit_count': 1
                }
                supabase.table('recipe_contributors').insert(contributor_data).execute()
                
            except Exception as version_error:
                print(f"Failed to create initial version: {version_error}")
                # Don't fail recipe creation if version tracking fails
            
            return jsonify({"ok": True, "id": recipe_id})
        else:
            return jsonify({"error": "Failed to create recipe"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipe/<int:rid>", methods=["PUT"])
@require_auth
def update_recipe(rid):
    try:
        data = request.json or {}
        current_user = get_current_user()
        
        # Check if recipe exists and belongs to user
        existing = supabase.table('recipes').select('*').eq('id', rid).eq('user_id', current_user['id']).execute()
        if not existing.data or len(existing.data) == 0:
            return jsonify({"error": "not found"}), 404
        
        old_recipe = existing.data[0]
        
        new_title = (data.get("title") or "").strip()
        if not new_title:
            return jsonify({"error": "Title required"}), 400
        
        # Check for title conflicts (excluding current recipe)
        title_check = supabase.table('recipes').select('id').eq('title', new_title).eq('user_id', current_user['id']).neq('id', rid).execute()
        if title_check.data:
            return jsonify({"error": "Title already exists"}), 400
        
        # Calculate changes for version tracking
        changes = {}
        
        if old_recipe['title'] != new_title:
            changes['title'] = {'from': old_recipe['title'], 'to': new_title}
        
        old_category = old_recipe.get('category', '')
        new_category = data.get("category", "")
        if old_category != new_category:
            changes['category'] = {'from': old_category, 'to': new_category}
        
        old_tags = old_recipe.get('tags', '')
        new_tags = data.get("tags", "")
        if old_tags != new_tags:
            changes['tags'] = {'from': old_tags, 'to': new_tags}
        
        old_servings = old_recipe.get('servings', 2)
        new_servings = int(data.get("servings", 2))
        if old_servings != new_servings:
            changes['servings'] = {'from': old_servings, 'to': new_servings}
        
        old_steps = old_recipe.get('steps', '')
        new_steps = data.get("steps", "")
        if old_steps != new_steps:
            changes['steps'] = True  # Don't store full text diff for now
        
        old_ingredients = old_recipe.get('ingredients_json', '[]')
        new_ingredients_json = json.dumps(data.get("ingredients", []), ensure_ascii=False)
        if old_ingredients != new_ingredients_json:
            changes['ingredients'] = True  # Don't store full ingredient diff for now
        
        # Update recipe
        update_data = {
            'title': new_title,
            'category': new_category,
            'tags': new_tags,
            'servings': new_servings,
            'ingredients_json': new_ingredients_json,
            'steps': new_steps
        }
        
        response = supabase.table('recipes').update(update_data).eq('id', rid).eq('user_id', current_user['id']).execute()
        
        # Create a new version if there are changes and auto_commit is enabled
        if changes and data.get('auto_commit', True):
            try:
                # Create new version snapshot
                snapshot = {
                    'title': new_title,
                    'description': old_recipe.get('description', ''),
                    'ingredients': data.get("ingredients", []),
                    'steps': new_steps,
                    'servings': new_servings,
                    'category': new_category,
                    'tags': new_tags,
                    'prep_time': old_recipe.get('prep_time', 0),
                    'cook_time': old_recipe.get('cook_time', 0),
                    'difficulty': old_recipe.get('difficulty', 'Easy')
                }
                
                commit_message = data.get('commit_message', 'Update recipe')
                
                # Try to use the database function
                try:
                    supabase.rpc('create_recipe_version', {
                        'p_recipe_id': rid,
                        'p_author_id': current_user['id'],
                        'p_commit_message': commit_message,
                        'p_changes_json': changes,
                        'p_snapshot_json': snapshot
                    }).execute()
                except:
                    # Fallback to manual version creation
                    version_response = supabase.table('recipe_versions').select('version_number').eq('recipe_id', rid).order('version_number', desc=True).limit(1).execute()
                    next_version = 1
                    if version_response.data:
                        next_version = version_response.data[0]['version_number'] + 1
                    
                    version_data = {
                        'recipe_id': rid,
                        'version_number': next_version,
                        'commit_message': commit_message,
                        'author_id': current_user['id'],
                        'changes_json': changes,
                        'snapshot_json': snapshot
                    }
                    supabase.table('recipe_versions').insert(version_data).execute()
            except Exception as version_error:
                print(f"Failed to create version: {version_error}")
                # Don't fail the recipe update if version creation fails
        
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipe/<int:rid>", methods=["DELETE"])
@require_auth
def delete_recipe(rid):
    try:
        current_user = get_current_user()
        
        # Delete recipe
        response = supabase.table('recipes').delete().eq('id', rid).eq('user_id', current_user['id']).execute()
        
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Plan Routes
@app.route("/api/plan", methods=["GET"])
@require_auth
def get_plan():
    try:
        current_user = get_current_user()
        print(f"Getting plan for user: {current_user}")  # Debug log
        
        # Pure dev mode - return mock plan data
        if is_development():
            default_plan = {d: [] for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
            # Add some mock data for development
            default_plan["Mon"] = [{"id": 1, "title": "Spaghetti Carbonara", "type": "lunch"}]
            default_plan["Wed"] = [{"id": 2, "title": "Chicken Tacos", "type": "dinner"}]
            print(f"Returning dev plan data: {default_plan}")
            return jsonify(default_plan)
        
        # Production mode - check Supabase is available
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
        
        # Get plan from Supabase
        response = supabase.table('plans').select('*').eq('user_id', current_user['id']).execute()
        print(f"Plan response: {response}")  # Debug log
        
        if response.data:
            plan = response.data[0]
            try:
                plan_data = json.loads(plan.get('plan_json', '{}'))
            except Exception as e:
                print(f"Error parsing plan JSON: {e}")
                plan_data = {}
        else:
            # Create default plan
            default_plan = {d: [] for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
            plan_insert_data = {
                'user_id': current_user['id'],
                'name': 'Week Plan',
                'plan_json': json.dumps(default_plan)
            }
            
            print(f"Creating new plan: {plan_insert_data}")  # Debug log
            insert_response = supabase.table('plans').insert(plan_insert_data).execute()
            print(f"Plan insert response: {insert_response}")  # Debug log
            plan_data = default_plan
        
        print(f"Returning plan data: {plan_data}")  # Debug log
        return jsonify(plan_data)
    except Exception as e:
        print(f"Error in get_plan: {e}")  # Debug log
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/plan", methods=["PUT"])
@require_auth
def save_plan():
    try:
        current_user = get_current_user()
        data = request.json or {}
        
        # Check if plan exists
        existing = supabase.table('plans').select('*').eq('user_id', current_user['id']).execute()
        
        plan_json = json.dumps(data, ensure_ascii=False)
        
        if existing.data:
            # Update existing plan
            response = supabase.table('plans').update({
                'plan_json': plan_json
            }).eq('user_id', current_user['id']).execute()
        else:
            # Create new plan
            response = supabase.table('plans').insert({
                'user_id': current_user['id'],
                'name': 'Week Plan',
                'plan_json': plan_json
            }).execute()
        
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/groceries", methods=["POST"])
@require_auth
def build_groceries():
    try:
        current_user = get_current_user()
        payload = request.json or {}
        plan = payload.get("plan", {})
        
        # Get all recipes from Supabase
        recipes_response = supabase.table('recipes').select('*').eq('user_id', current_user['id']).execute()
        recipes_dict = {r['id']: r for r in recipes_response.data or []}
        
        items = []
        for day, entries in plan.items():
            for entry in entries:
                rid = entry.get("recipe_id")
                mult = int(entry.get("multiplier", 1))
                recipe = recipes_dict.get(rid)
                if not recipe:
                    continue
                
                try:
                    ingredients = json.loads(recipe.get('ingredients_json', '[]'))
                except:
                    ingredients = []
                    
                for ing in ingredients:
                    qty = float(ing.get("qty", 0) or 0) * mult
                    unit = ing.get("unit", "")
                    name = ing.get("name", "")
                    note = ing.get("note", "")
                    items.append({"name": name, "qty": qty, "unit": unit, "note": note})
        
        # Aggregate items
        flat = []
        notes_map = defaultdict(list)
        for it in items:
            name = it.get("name", "").strip()
            qty = float(it.get("qty", 0))
            unit = it.get("unit", "")
            note = it.get("note", "")
            flat.append((name, qty, unit))
            if note:
                notes_map[(name.strip().lower(), normalize_unit(unit))].append(note)
        
        aggregated = try_aggregate(flat)
        out = []
        for name, qty, unit in aggregated:
            notes = ", ".join(sorted(set(notes_map.get((name, normalize_unit(unit)), []))))
            out.append({"name": name, "qty": qty, "unit": unit, "note": notes})
        
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================================================
# Community and Profile API Routes
# ================================================

@app.route("/api/profile/<username>", methods=["GET"])
def get_profile(username):
    """Get public profile information"""
    try:
        # Get current user for follow status
        current_user = get_current_user()
        
        # Search for profile by username (usernames can contain @ symbols)
        response = supabase.table('profiles').select('*').eq('username', username).execute()
        
        if not response.data:
            return jsonify({"error": "Profile not found"}), 404
            
        profile = response.data[0]
        
        # Get recipe count for this user
        recipe_response = supabase.table('recipes').select('id').eq('user_id', profile['id']).eq('is_public', True).execute()
        recipe_count = len(recipe_response.data) if recipe_response.data else 0
        
        # Check if current user is following this profile
        is_following = False
        follows_back = False
        if current_user and current_user['id'] != profile['id']:
            follow_response = supabase.table('user_follows').select('*').eq('follower_id', current_user['id']).eq('following_id', profile['id']).execute()
            is_following = len(follow_response.data) > 0
            
            # Check if they follow back
            followback_response = supabase.table('user_follows').select('*').eq('follower_id', profile['id']).eq('following_id', current_user['id']).execute()
            follows_back = len(followback_response.data) > 0
        
        return jsonify({
            'id': profile['id'],
            'username': profile.get('username', ''),
            'name': profile.get('name', profile.get('username', '')),
            'email': profile.get('email', ''),
            'avatar_url': profile.get('avatar_url', ''),
            'bio': profile.get('bio', ''),
            'created_at': profile.get('created_at', ''),
            'followers_count': profile.get('followers_count', 0),
            'following_count': profile.get('following_count', 0),
            'recipes_count': recipe_count,
            'is_following': is_following,
            'follows_back': follows_back
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/profile", methods=["PUT"])
@require_auth
def update_profile():
    """Update current user's profile"""
    try:
        current_user = get_current_user()
        data = request.json or {}
        
        # Enhanced input validation for profile updates
        if 'username' in data and data['username']:
            username = str(data['username']).strip()
            if len(username) > 50:
                return jsonify({"error": "Username cannot exceed 50 characters"}), 400
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                return jsonify({"error": "Username can only contain letters, numbers, and underscores"}), 400
            # Check if username is already taken
            existing = supabase.table('profiles').select('id').eq('username', username).neq('id', current_user['id']).execute()
            if existing.data:
                return jsonify({"error": "Username already taken"}), 400
        
        if 'name' in data:
            name = str(data['name']).strip()
            if len(name) > 100:
                return jsonify({"error": "Name cannot exceed 100 characters"}), 400
        
        if 'bio' in data:
            bio = str(data['bio']).strip()
            if len(bio) > 500:
                return jsonify({"error": "Bio cannot exceed 500 characters"}), 400
        
        if 'avatar_url' in data:
            avatar_url = str(data['avatar_url']).strip()
            if len(avatar_url) > 500:
                return jsonify({"error": "Avatar URL cannot exceed 500 characters"}), 400
        
        # Update profile with sanitized data
        update_data = {}
        for field in ['username', 'name', 'bio', 'avatar_url', 'is_public']:
            if field in data:
                if field in ['username', 'name', 'bio', 'avatar_url']:
                    # Sanitize text fields
                    max_lengths = {'username': 50, 'name': 100, 'bio': 500, 'avatar_url': 500}
                    update_data[field] = sanitize_input(str(data[field]), max_lengths[field])
                else:
                    update_data[field] = data[field]
        
        if update_data:
            response = supabase.table('profiles').update(update_data).eq('id', current_user['id']).execute()
            return jsonify({"ok": True, "profile": response.data[0] if response.data else None})
        
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500





@app.route("/api/feed", methods=["GET"])  
def get_feed():
    """Get user's feed (recipes from followed users)"""
    try:
        current_user = get_current_user()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        
        # Pure dev mode - return dev recipes as feed
        if is_development():
            return jsonify({"recipes": DEV_RECIPES})
        
        # Production mode - use Supabase
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
            
        # Get feed using the database function
        response = supabase.rpc('get_user_feed', {
            'input_user_id': current_user['id'],
            'page_limit': limit,
            'page_offset': offset
        }).execute()
        
        return jsonify({"recipes": response.data or []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/community/feed", methods=["GET"])
def get_community_feed():
    """Get enhanced community feed with all activities"""
    try:
        current_user = get_current_user()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        
        # Get community feed using the new database function
        response = supabase.rpc('get_community_feed', {
            'input_user_id': current_user['id'],
            'page_limit': limit,
            'page_offset': offset
        }).execute()
        
        return jsonify({"activities": response.data or []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/activity", methods=["GET"])
@require_auth
def get_user_activity():
    """Get user's personal activity feed"""
    try:
        current_user = get_current_user()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        
        # Pure dev mode - return sample activity data
        if is_development():
            sample_activities = [
                {
                    "id": 1,
                    "type": "recipe_created",
                    "title": "Created recipe 'Pasta Carbonara'",
                    "created_at": "2025-08-04T10:30:00Z",
                    "recipe_id": 1,
                    "recipe_title": "Pasta Carbonara"
                },
                {
                    "id": 2,
                    "type": "recipe_forked",
                    "title": "Forked recipe 'Classic Pizza'",
                    "created_at": "2025-08-03T15:20:00Z",
                    "recipe_id": 2,
                    "recipe_title": "Classic Pizza"
                }
            ]
            return jsonify({"activities": sample_activities[offset:offset+limit]})
        
        # Production mode - get user's activities from database
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
            
        try:
            # Get user's personal activities
            activities_query = supabase.table('user_posts').select('''
                id, type, title, created_at, recipe_id,
                recipes!inner(title)
            ''').eq('user_id', current_user['id']).order('created_at', desc=True).range(offset, offset + limit - 1)
            
            activities_response = activities_query.execute()
            activities = []
            
            for activity in activities_response.data or []:
                activities.append({
                    "id": activity['id'],
                    "type": activity['type'],
                    "title": activity['title'],
                    "created_at": activity['created_at'],
                    "recipe_id": activity.get('recipe_id'),
                    "recipe_title": activity.get('recipes', {}).get('title') if activity.get('recipes') else None
                })
            
            return jsonify({"activities": activities})
        except Exception as e:
            print(f"Error fetching user activities: {e}")
            return jsonify({"activities": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================================================
# Recipe Forking System (GitHub-like)
# ================================================

@app.route("/api/recipes/<int:recipe_id>/fork", methods=["POST"])
@require_auth
def fork_recipe(recipe_id):
    """Fork a recipe (like GitHub fork)"""
    try:
        current_user = get_current_user()
        data = request.get_json() or {}
        
        # Get the original recipe from database
        original_response = supabase.table('recipes').select('*').eq('id', recipe_id).eq('is_public', True).execute()
        
        if not original_response.data:
            return jsonify({"error": "Recipe not found or not public"}), 404
        
        original = original_response.data[0]
        
        # Check if user already forked this recipe
        existing_fork = supabase.table('recipe_forks').select('forked_recipe_id').eq('original_recipe_id', recipe_id).eq('forked_by_user_id', current_user['id']).execute()
        
        if existing_fork.data:
            return jsonify({
                "error": "You have already forked this recipe", 
                "existing_fork_id": existing_fork.data[0]['forked_recipe_id']
            }), 400
        
        # Create forked recipe
        fork_data = {
            'user_id': current_user['id'],
            'title': f"{original['title']} (Fork)",
            'description': original.get('description', ''),
            'category': original.get('category', ''),
            'tags': original.get('tags', ''),
            'servings': original.get('servings', 2),
            'prep_time': original.get('prep_time'),
            'cook_time': original.get('cook_time'),
            'difficulty': original.get('difficulty', ''),
            'steps': original.get('steps', ''),
            'ingredients_json': original.get('ingredients_json', '[]'),
            'image_url': original.get('image_url', ''),
            'is_public': data.get('is_public', True),
            'original_recipe_id': recipe_id,
            'is_fork': True
        }
        
        # Create the forked recipe
        forked_recipe = supabase.table('recipes').insert(fork_data).execute()
        if not forked_recipe.data:
            return jsonify({"error": "Failed to create fork"}), 500
        
        forked_id = forked_recipe.data[0]['id']
        
        # Create fork relationship
        fork_relationship = {
            'original_recipe_id': recipe_id,
            'forked_recipe_id': forked_id,
            'forked_by_user_id': current_user['id'],
            'fork_reason': data.get('fork_reason', ''),
            'branch_name': data.get('branch_name', 'main')
        }
        
        supabase.table('recipe_forks').insert(fork_relationship).execute()
        
        return jsonify({
            "ok": True, 
            "message": "Recipe forked successfully! 🍴",
            "id": forked_id,
            "forked_recipe_id": forked_id
        })
        
    except Exception as e:
        print(f"Error forking recipe: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipes/<int:recipe_id>/forks", methods=["GET"])
def get_recipe_forks(recipe_id):
    """Get all forks of a recipe with full lineage"""
    try:
        # Use the database function to get fork tree
        response = supabase.rpc('get_recipe_fork_tree', {
            'p_recipe_id': recipe_id
        }).execute()
        
        forks = []
        for fork in response.data or []:
            forks.append({
                'id': fork['fork_id'],
                'recipe_id': fork['forked_recipe_id'],
                'title': fork['forked_recipe_title'],
                'forked_by': {
                    'id': fork['forked_by_id'],
                    'name': fork['forked_by_name'],
                    'username': fork['forked_by_username']
                },
                'fork_depth': fork['fork_depth'],
                'created_at': fork['created_at']
            })
        
        return jsonify({"forks": forks})
    except Exception as e:
        # Fallback to basic query if function doesn't exist
        response = supabase.table('recipe_forks').select('''
            *,
            forked_recipe:recipes!recipe_forks_forked_recipe_id_fkey(id, title, image_url, user_id),
            forked_by:profiles!recipe_forks_forked_by_user_id_fkey(username, name, avatar_url)
        ''').eq('original_recipe_id', recipe_id).execute()
        
        return jsonify({"forks": response.data or []})

# ================================================
# Recipe Version History (Git-like Commits)
# ================================================

@app.route("/api/recipes/<int:recipe_id>/history", methods=["GET"])
def get_recipe_history(recipe_id):
    """Get full commit history of a recipe"""
    try:
        page = int(request.args.get('page', 1))
        limit = min(int(request.args.get('limit', 20)), 50)
        offset = (page - 1) * limit
        
        # Use the database function to get history with author info
        response = supabase.rpc('get_recipe_history', {
            'p_recipe_id': recipe_id,
            'p_limit': limit,
            'p_offset': offset
        }).execute()
        
        commits = []
        for commit in response.data or []:
            commits.append({
                'version': f"v{commit['version_number']}",
                'version_id': commit['version_id'],
                'message': commit['commit_message'],
                'author': {
                    'id': commit['author_id'],
                    'name': commit['author_name'],
                    'username': commit['author_username'],
                    'avatar_url': commit['author_avatar']
                },
                'date': commit['created_at'],
                'changes': commit['changes_json']
            })
        
        return jsonify({"commits": commits})
    except Exception as e:
        # Fallback to basic query if function doesn't exist
        response = supabase.table('recipe_versions').select('''
            *,
            author:profiles!recipe_versions_author_id_fkey(username, name, avatar_url)
        ''').eq('recipe_id', recipe_id).order('version_number', desc=True).limit(limit).offset(offset).execute()
        
        commits = []
        for version in response.data or []:
            author = version.get('author', {}) or {}
            commits.append({
                'version': f"v{version['version_number']}",
                'version_id': version['id'],
                'message': version['commit_message'],
                'author': {
                    'name': author.get('name', 'Unknown'),
                    'username': author.get('username', 'unknown'),
                    'avatar_url': author.get('avatar_url', '')
                },
                'date': version['created_at'],
                'changes': version.get('changes_json', {})
            })
        
        return jsonify({"commits": commits})

@app.route("/api/recipes/<int:recipe_id>/commit", methods=["POST"])
@require_auth
def create_recipe_commit(recipe_id):
    """Create a new version (commit) for a recipe"""
    try:
        current_user = get_current_user()
        data = request.json or {}
        
        commit_message = (data.get('message') or '').strip()
        if not commit_message:
            return jsonify({"error": "Commit message is required"}), 400
        
        # Pure dev mode - mock commit creation
        if is_development():
            # Check if user owns the recipe in dev data
            recipe_found = False
            for recipe in DEV_RECIPES:
                if recipe.get('id') == recipe_id and recipe.get('user_id') == current_user['id']:
                    recipe_found = True
                    # Update version count
                    recipe['version_count'] = recipe.get('version_count', 1) + 1
                    recipe['updated_at'] = datetime.now().isoformat()
                    break
            
            if not recipe_found:
                return jsonify({"error": "Recipe not found or access denied"}), 404
            
            print(f"📝 Dev commit created for recipe {recipe_id}: {commit_message}")
            return jsonify({
                "ok": True, 
                "message": "Recipe version committed successfully! 📝",
                "version_number": recipe.get('version_count', 1)
            })
        
        # Production mode - check Supabase is available
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
        
        # Check if user owns the recipe
        recipe_check = supabase.table('recipes').select('*').eq('id', recipe_id).eq('user_id', current_user['id']).execute()
        if not recipe_check.data:
            return jsonify({"error": "Recipe not found or access denied"}), 404
        
        recipe = recipe_check.data[0]
        
        # Get current recipe state as snapshot
        try:
            ingredients = json.loads(recipe.get('ingredients_json', '[]'))
        except:
            ingredients = []
        
        snapshot = {
            'title': recipe['title'],
            'description': recipe.get('description', ''),
            'ingredients': ingredients,
            'steps': recipe.get('steps', ''),
            'servings': recipe.get('servings', 2),
            'category': recipe.get('category', ''),
            'tags': recipe.get('tags', ''),
            'prep_time': recipe.get('prep_time', 0),
            'cook_time': recipe.get('cook_time', 0),
            'difficulty': recipe.get('difficulty', 'Easy')
        }
        
        # Create version using database function
        try:
            response = supabase.rpc('create_recipe_version', {
                'p_recipe_id': recipe_id,
                'p_author_id': current_user['id'],
                'p_commit_message': commit_message,
                'p_changes_json': data.get('changes', {}),
                'p_snapshot_json': snapshot
            }).execute()
            
            version_id = response.data
            
            return jsonify({
                "ok": True,
                "message": "Changes committed successfully!",
                "version_id": version_id
            })
        except Exception as e:
            # Fallback to manual creation
            # Get next version number
            version_response = supabase.table('recipe_versions').select('version_number').eq('recipe_id', recipe_id).order('version_number', desc=True).limit(1).execute()
            next_version = 1
            if version_response.data:
                next_version = version_response.data[0]['version_number'] + 1
            
            # Create version
            version_data = {
                'recipe_id': recipe_id,
                'version_number': next_version,
                'commit_message': commit_message,
                'author_id': current_user['id'],
                'changes_json': data.get('changes', {}),
                'snapshot_json': snapshot
            }
            
            version_response = supabase.table('recipe_versions').insert(version_data).execute()
            
            if version_response.data:
                return jsonify({
                    "ok": True,
                    "message": "Changes committed successfully!",
                    "version_id": version_response.data[0]['id']
                })
            else:
                return jsonify({"error": "Failed to create version"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipes/<int:recipe_id>/branches", methods=["GET"])
def get_recipe_branches(recipe_id):
    """Get all branches for a recipe"""
    try:
        response = supabase.table('recipe_branches').select('''
            *,
            creator:profiles!recipe_branches_created_by_fkey(username, name, avatar_url)
        ''').eq('recipe_id', recipe_id).eq('is_active', True).order('created_at', desc=True).execute()
        
        branches = []
        for branch in response.data or []:
            creator = branch.get('creator', {}) or {}
            branches.append({
                'id': branch['id'],
                'name': branch['branch_name'],
                'description': branch.get('description', ''),
                'is_default': branch.get('is_default', False),
                'creator': {
                    'name': creator.get('name', 'Unknown'),
                    'username': creator.get('username', 'unknown'),
                    'avatar_url': creator.get('avatar_url', '')
                },
                'created_at': branch['created_at']
            })
        
        return jsonify({"branches": branches})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipes/<int:recipe_id>/branch", methods=["POST"])
@require_auth
def create_recipe_branch(recipe_id):
    """Create a new branch (variation) for a recipe"""
    try:
        current_user = get_current_user()
        data = request.json or {}
        
        branch_name = (data.get('name') or '').strip()
        if not branch_name:
            return jsonify({"error": "Branch name is required"}), 400
        
        # Validate branch name
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', branch_name):
            return jsonify({"error": "Branch name can only contain letters, numbers, hyphens and underscores"}), 400
        
        # Pure dev mode - mock branch creation
        if is_development():
            # Check if user owns the recipe in dev data
            recipe_found = False
            for recipe in DEV_RECIPES:
                if recipe.get('id') == recipe_id and recipe.get('user_id') == current_user['id']:
                    recipe_found = True
                    break
            
            if not recipe_found:
                return jsonify({"error": "Recipe not found or access denied"}), 404
            
            # In dev mode, just simulate success (no persistent branch storage)
            print(f"🌿 Dev branch created for recipe {recipe_id}: {branch_name}")
            return jsonify({
                "ok": True, 
                "message": f"Branch '{branch_name}' created successfully! 🌿",
                "branch": {
                    "id": f"dev-branch-{recipe_id}-{branch_name}",
                    "name": branch_name,
                    "description": data.get('description', ''),
                    "recipe_id": recipe_id,
                    "created_by": current_user['id'],
                    "is_default": False,
                    "created_at": datetime.now().isoformat()
                }
            })
        
        # Production mode - check Supabase is available
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
        
        # Check if user owns the recipe
        recipe_check = supabase.table('recipes').select('*').eq('id', recipe_id).eq('user_id', current_user['id']).execute()
        if not recipe_check.data:
            return jsonify({"error": "Recipe not found or access denied"}), 404
        
        # Check if branch name already exists
        existing_branch = supabase.table('recipe_branches').select('id').eq('recipe_id', recipe_id).eq('branch_name', branch_name).execute()
        if existing_branch.data:
            return jsonify({"error": "Branch name already exists"}), 400
        
        # Create branch
        branch_data = {
            'recipe_id': recipe_id,
            'branch_name': branch_name,
            'description': data.get('description', ''),
            'created_by': current_user['id'],
            'is_default': False
        }
        
        response = supabase.table('recipe_branches').insert(branch_data).execute()
        
        if response.data:
            return jsonify({
                "ok": True,
                "message": f"Branch '{branch_name}' created successfully!",
                "branch": response.data[0]
            })
        else:
            return jsonify({"error": "Failed to create branch"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipes/<int:recipe_id>/contributors", methods=["GET"])
def get_recipe_contributors(recipe_id):
    """Get all contributors to a recipe"""
    try:
        response = supabase.table('recipe_contributors').select('''
            *,
            contributor:profiles!recipe_contributors_contributor_id_fkey(username, name, avatar_url)
        ''').eq('recipe_id', recipe_id).order('commit_count', desc=True).execute()
        
        contributors = []
        for contrib in response.data or []:
            contributor = contrib.get('contributor', {}) or {}
            contributors.append({
                'id': contrib['contributor_id'],
                'name': contributor.get('name', 'Unknown'),
                'username': contributor.get('username', 'unknown'),
                'avatar_url': contributor.get('avatar_url', ''),
                'contribution_type': contrib['contribution_type'],
                'commit_count': contrib['commit_count'],
                'first_contributed_at': contrib['first_contributed_at'],
                'last_contributed_at': contrib['last_contributed_at']
            })
        
        return jsonify({"contributors": contributors})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================================================
# User Posts & Updates
# ================================================

# Duplicate function removed - using the more complete version below

@app.route("/api/users/<user_id>/posts", methods=["GET"])
def get_user_posts(user_id):
    """Get posts by a specific user"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        
        response = supabase.table('user_posts').select('''
            *,
            user:profiles!user_posts_user_id_fkey(username, name, avatar_url),
            recipe:recipes(id, title, image_url)
        ''').eq('user_id', user_id).eq('is_public', True).order('created_at', desc=True).limit(limit).offset(offset).execute()
        
        return jsonify({"posts": response.data or []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================================================
# Following/Followers Management
# ================================================

@app.route("/api/users/<user_id>/followers", methods=["GET"])
def get_user_followers(user_id):
    """Get users following this user"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        
        response = supabase.table('user_follows').select('''
            follower_id,
            created_at,
            follower:profiles!user_follows_follower_id_fkey(id, username, name, avatar_url, followers_count, following_count)
        ''').eq('following_id', user_id).order('created_at', desc=True).limit(limit).offset(offset).execute()
        
        followers = [
            {
                **follow['follower'],
                'followed_at': follow['created_at']
            }
            for follow in (response.data or [])
        ]
        
        return jsonify({"followers": followers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/users/<user_id>/following", methods=["GET"])
def get_user_following(user_id):
    """Get users this user is following"""
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        
        response = supabase.table('user_follows').select('''
            following_id,
            created_at,
            following:profiles!user_follows_following_id_fkey(id, username, name, avatar_url, followers_count, following_count)
        ''').eq('follower_id', user_id).order('created_at', desc=True).limit(limit).offset(offset).execute()
        
        following = [
            {
                **follow['following'],
                'followed_at': follow['created_at']
            }
            for follow in (response.data or [])
        ]
        
        return jsonify({"following": following})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/me/followers", methods=["GET"])
@require_auth
def get_my_followers():
    """Get current user's followers"""
    current_user = get_current_user()
    return get_user_followers(current_user['id'])

@app.route("/api/me/following", methods=["GET"])
@require_auth
def get_my_following():
    """Get users current user is following"""
    current_user = get_current_user()
    return get_user_following(current_user['id'])

# ================================================
# Groups API Routes
# ================================================

@app.route("/api/groups", methods=["GET"])
def list_groups():
    """List public groups"""
    try:
        # Check if user is authenticated (optional for public groups)
        current_user = None
        if 'user_id' in session:
            try:
                current_user = get_current_user()
            except:
                pass  # Continue without authentication
        
        # Mock mode - return mock groups (only if database disabled)
        if not use_database():
            mock_groups = [
                {
                    'id': 'group-1',
                    'name': 'Recipe Lovers',
                    'description': 'A community for sharing amazing recipes',
                    'avatar_url': '',
                    'is_public': True,
                    'member_count': 15,
                    'is_member': False,
                    'owner_name': 'Alice Cook',
                    'created_at': '2025-01-01T00:00:00Z'
                },
                {
                    'id': 'group-2', 
                    'name': 'BBQ Masters',
                    'description': 'Perfect your grilling and BBQ skills',
                    'avatar_url': '',
                    'is_public': True,
                    'member_count': 8,
                    'is_member': False,
                    'owner_name': 'Bob Chef',
                    'created_at': '2025-01-01T00:00:00Z'
                }
            ]
            return jsonify({"groups": mock_groups})
        
        # Production mode - check if groups table exists
        try:
            if supabase:
                # Try using the group_details view first
                try:
                    response = supabase.table('group_details').select('*').eq('is_public', True).limit(20).execute()
                    groups = []
                    for group in response.data or []:
                        group_data = {
                            **group,
                            'is_member': False  # Will be checked below
                        }
                        
                        # Check if current user is a member
                        if current_user:
                            member_check = supabase.table('group_members').select('*').eq('group_id', group['id']).eq('user_id', current_user['id']).execute()
                            group_data['is_member'] = len(member_check.data or []) > 0
                        
                        groups.append(group_data)
                except Exception as view_error:
                    print(f"group_details view not available, falling back to basic query: {view_error}")
                    # Fallback to basic groups table query
                    response = supabase.table('groups').select('''
                        *,
                        profiles!groups_owner_id_fkey(username, name, avatar_url)
                    ''').eq('is_public', True).limit(20).execute()
                    
                    groups = []
                    for group in response.data or []:
                        # Add owner information
                        owner = group.get('profiles', {}) or {}
                        group_data = {
                            **group,
                            'owner_name': owner.get('name', 'Unknown'),
                            'owner_username': owner.get('username', 'unknown'),
                            'owner_avatar': owner.get('avatar_url', ''),
                            'post_count': 0,  # Default post count
                            'is_member': False
                        }
                        
                        # Check if current user is a member
                        if current_user:
                            member_check = supabase.table('group_members').select('*').eq('group_id', group['id']).eq('user_id', current_user['id']).execute()
                            group_data['is_member'] = len(member_check.data or []) > 0
                        
                        groups.append(group_data)
            else:
                groups = []
        except Exception as e:
            # Groups table doesn't exist yet, return empty list
            print(f"Groups table not available: {e}")
            groups = []
        
        return jsonify({"groups": groups})
    except Exception as e:
        print(f"Error in list_groups: {e}")
        return jsonify({"groups": []})  # Return empty list instead of error

@app.route("/api/groups", methods=["POST"])
@require_auth
def create_group():
    """Create a new group"""
    try:
        current_user = get_current_user()
        data = request.json or {}
        
        # Validate required fields
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "Group name is required"}), 400
        
        # Create group
        group_data = {
            'name': name,
            'description': data.get("description", ""),
            'owner_id': current_user['id'],
            'is_public': data.get("is_public", True)
        }
        
        response = supabase.table('groups').insert(group_data).execute()
        if response.data:
            group = response.data[0]
            
            # Add owner as member
            member_data = {
                'group_id': group['id'],
                'user_id': current_user['id'],
                'role': 'owner'
            }
            supabase.table('group_members').insert(member_data).execute()
            
            return jsonify({"ok": True, "group": group})
        else:
            return jsonify({"error": "Failed to create group"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/groups/<group_id>", methods=["GET"])
def get_group(group_id):
    """Get group details"""
    try:
        # Pure dev mode - return mock group data
        if is_development():
            mock_groups = {
                "1": {
                    "id": "1", 
                    "name": "Recipe Developers", 
                    "description": "A group for recipe developers",
                    "is_public": True,
                    "owner_id": "00000000-0000-0000-0000-000000000001",
                    "owner_name": "Dev User",
                    "owner_username": "dev_user",
                    "owner_avatar": "",
                    "created_at": datetime.now().isoformat()
                },
                "2": {
                    "id": "2", 
                    "name": "Home Cooks", 
                    "description": "Share your home cooking experiences",
                    "is_public": True,
                    "owner_id": "00000000-0000-0000-0000-000000000002",
                    "owner_name": "Home Chef",
                    "owner_username": "home_chef",
                    "owner_avatar": "",
                    "created_at": datetime.now().isoformat()
                },
                "3": {
                    "id": "3", 
                    "name": "Professional Chefs", 
                    "description": "For professional chefs only",
                    "is_public": False,
                    "owner_id": "00000000-0000-0000-0000-000000000003",
                    "owner_name": "Chef Master",
                    "owner_username": "chef_master",
                    "owner_avatar": "",
                    "created_at": datetime.now().isoformat()
                }
            }
            
            if group_id not in mock_groups:
                return jsonify({"error": "Group not found"}), 404
            
            group = mock_groups[group_id]
            
            # Mock members data
            members = [
                {
                    "id": "1",
                    "user_id": group["owner_id"],
                    "role": "owner",
                    "profiles": {
                        "username": group["owner_username"],
                        "name": group["owner_name"],
                        "avatar_url": group["owner_avatar"]
                    }
                }
            ]
            
            # Mock posts data
            posts = [
                {
                    "id": "1",
                    "group_id": group_id,
                    "user_id": group["owner_id"],
                    "title": "Welcome to the group!",
                    "content": "Let's share some amazing recipes together.",
                    "created_at": datetime.now().isoformat(),
                    "user_name": group["owner_name"],
                    "username": group["owner_username"],
                    "user_avatar": group["owner_avatar"]
                }
            ]
            
            return jsonify({
                "group": group,
                "members": members,
                "posts": posts
            })
        
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
            
        # Get group details (try with owner info first)
        try:
            response = supabase.table('groups').select('''
                *,
                profiles!groups_owner_id_fkey(username, name, avatar_url)
            ''').eq('id', group_id).single().execute()
            
            if not response.data:
                return jsonify({"error": "Group not found"}), 404
            
            group = response.data
            # Add owner information
            owner = group.get('profiles', {}) or {}
            group.update({
                'owner_name': owner.get('name', 'Unknown'),
                'owner_username': owner.get('username', 'unknown'),
                'owner_avatar': owner.get('avatar_url', '')
            })
        except Exception as e:
            print(f"Error getting group with owner info: {e}")
            # Fallback to basic group query
            response = supabase.table('groups').select('*').eq('id', group_id).single().execute()
            if not response.data:
                return jsonify({"error": "Group not found"}), 404
            group = response.data
        
        # Get group members
        try:
            members_response = supabase.table('group_members').select('*, profiles(username, name, avatar_url)').eq('group_id', group_id).execute()
            members = members_response.data or []
        except Exception as e:
            print(f"Error getting group members: {e}")
            members = []
        
        # Get recent posts
        try:
            posts_response = supabase.table('group_posts').select('*, profiles!group_posts_user_id_fkey(username, name, avatar_url)').eq('group_id', group_id).order('created_at', desc=True).limit(10).execute()
            posts = []
            for post in posts_response.data or []:
                user_info = post.get('profiles', {}) or {}
                post.update({
                    'user_name': user_info.get('name', 'Unknown User'),
                    'username': user_info.get('username', 'unknown'),
                    'user_avatar': user_info.get('avatar_url', '')
                })
                posts.append(post)
        except Exception as e:
            print(f"Error getting group posts: {e}")
            posts = []
        
        return jsonify({
            "group": group,
            "members": members,
            "posts": posts
        })
    except Exception as e:
        print(f"Error in get_group: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/groups/<group_id>/join", methods=["POST"])
@require_auth
def join_group(group_id):
    """Join a group"""
    try:
        current_user = get_current_user()
        
        # Mock mode - mock group joining (only if database disabled)
        if not use_database():
            # Create mock groups if they don't exist
            mock_groups = {
                "group-1": {"id": "group-1", "name": "Recipe Lovers", "is_public": True, "description": "A community for sharing amazing recipes"},
                "group-2": {"id": "group-2", "name": "BBQ Masters", "is_public": True, "description": "Perfect your grilling and BBQ skills"},
                "group-3": {"id": "group-3", "name": "Professional Chefs", "is_public": False, "description": "For professional chefs only"}
            }
            
            if group_id not in mock_groups:
                return jsonify({"error": "Group not found"}), 404
            
            group = mock_groups[group_id]
            if not group.get('is_public', True):
                return jsonify({"error": "Cannot join private group"}), 403
            
            # In dev mode, we'll just assume success without persistent storage
            print(f"👥 Dev user {current_user['username']} joined group: {group['name']}")
            return jsonify({"ok": True, "message": f"Successfully joined {group['name']}!"})
        
        # Database mode - check Supabase is available
        client = get_supabase_client()
        if not client:
            return jsonify({"error": "Database not available"}), 500
        
        # Check if group exists and is public
        group_response = client.table('groups').select('*').eq('id', group_id).single().execute()
        if not group_response.data:
            return jsonify({"error": "Group not found"}), 404
        
        group = group_response.data
        if not group.get('is_public', True):
            return jsonify({"error": "Cannot join private group"}), 403
        
        # Check if already a member
        existing = client.table('group_members').select('*').eq('group_id', group_id).eq('user_id', current_user['id']).execute()
        if existing.data:
            return jsonify({"error": "Already a member of this group"}), 400
        
        # Join group
        member_data = {
            'group_id': group_id,
            'user_id': current_user['id'],
            'role': 'member'
        }
        response = client.table('group_members').insert(member_data).execute()
        
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/groups/<group_id>/leave", methods=["POST"])
@require_auth
def leave_group(group_id):
    """Leave a group"""
    try:
        current_user = get_current_user()
        
        # Leave group
        response = supabase.table('group_members').delete().eq('group_id', group_id).eq('user_id', current_user['id']).execute()
        
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/groups/<group_id>/posts", methods=["POST"])
@require_auth
def create_group_post(group_id):
    """Create a post in a group"""
    try:
        current_user = get_current_user()
        data = request.json or {}
        
        # Validate required fields
        if not data.get('title') or not data.get('content'):
            return jsonify({"error": "Title and content are required"}), 400
        
        # Check if user is a member
        membership = supabase.table('group_members').select('*').eq('group_id', group_id).eq('user_id', current_user['id']).execute()
        if not membership.data:
            return jsonify({"error": "Must be a member to post"}), 403
        
        # Create post
        post_data = {
            'group_id': group_id,
            'user_id': current_user['id'],
            'title': data['title'],
            'content': data['content'],
            'post_type': data.get('post_type', 'discussion'),
            'recipe_id': data.get('recipe_id')
        }
        
        response = supabase.table('group_posts').insert(post_data).execute()
        post = response.data[0] if response.data else None
        
        return jsonify({"ok": True, "post": post})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/posts/<post_id>/comments", methods=["POST"])
@require_auth
def create_post_comment(post_id):
    """Create a comment on a group post"""
    try:
        current_user = get_current_user()
        data = request.json or {}
        
        # Validate required fields
        if not data.get('content'):
            return jsonify({"error": "Content is required"}), 400
        
        # Check if user can access the post (member of the group)
        post_response = supabase.table('group_posts').select('group_id').eq('id', post_id).execute()
        if not post_response.data:
            return jsonify({"error": "Post not found"}), 404
        
        group_id = post_response.data[0]['group_id']
        membership = supabase.table('group_members').select('*').eq('group_id', group_id).eq('user_id', current_user['id']).execute()
        if not membership.data:
            return jsonify({"error": "Must be a member to comment"}), 403
        
        # Create comment
        comment_data = {
            'post_id': post_id,
            'user_id': current_user['id'],
            'content': data['content']
        }
        
        response = supabase.table('group_post_comments').insert(comment_data).execute()
        comment = response.data[0] if response.data else None
        
        return jsonify({"ok": True, "comment": comment})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================================================
# User Search and Follow ("Cook") System
# ================================================

@app.route("/api/users/search", methods=["GET"])
@require_auth
def search_users():
    """Search for users"""
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 20)), 50)  # Max 50 results
        current_user = get_current_user()
        
        if not query:
            return jsonify({"users": []})
        
        # Pure dev mode - search dev users
        if is_development():
            matching_users = []
            for email, user_data in DEV_USERS.items():
                if (query.lower() in user_data['name'].lower() or 
                    query.lower() in user_data['username'].lower() or 
                    query.lower() in user_data['email'].lower()):
                    if user_data['id'] != current_user['id']:  # Don't include self
                        matching_users.append({
                            'id': user_data['id'],
                            'username': user_data['username'],
                            'name': user_data['name'],
                            'avatar_url': user_data['avatar_url'],
                            'bio': f"Development user - {user_data['name']}",
                            'followers_count': 5,
                            'following_count': 3,
                            'is_following': False,
                            'follows_back': False,
                            'created_at': '2025-01-01T00:00:00Z'
                        })
            return jsonify({"users": matching_users[:limit]})
        
        # Production mode - use Supabase optimized search function
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
        
        # Use the optimized search_users RPC function
        response = supabase.rpc('search_users', {
            'search_query': query,
            'current_user_id': current_user['id'],
            'limit_count': limit
        }).execute()
        
        users = response.data or []
        
        # The RPC function already includes all needed fields:
        # id, username, name, avatar_url, bio, followers_count, following_count,
        # recipe_count, is_following, follows_back, created_at
        
        return jsonify({"users": users})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route("/api/users/<user_id>/follow", methods=["POST"])
@require_auth
def follow_user(user_id):
    """Follow a user"""
    try:
        current_user = get_current_user()
        
        # Prevent self-follows
        if user_id == current_user['id']:
            return jsonify({"error": "Cannot follow yourself"}), 400
        
        # Check if already following
        existing = supabase.table('user_follows').select('id').eq('follower_id', current_user['id']).eq('following_id', user_id).execute()
        if existing.data:
            return jsonify({"error": "Already following this user"}), 400
        
        # Create follow relationship
        follow_data = {
            'follower_id': current_user['id'],
            'following_id': user_id
        }
        
        response = supabase.table('user_follows').insert(follow_data).execute()
        
        if response.data:
            return jsonify({"ok": True, "message": "Now cooking together! 👨‍🍳"})
        else:
            return jsonify({"error": "Failed to follow user"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/users/<user_id>/unfollow", methods=["POST"])
@require_auth
def unfollow_user(user_id):
    """Unfollow a user"""
    try:
        current_user = get_current_user()
        
        # Find and delete the follow relationship
        response = supabase.table('user_follows').delete().eq('follower_id', current_user['id']).eq('following_id', user_id).execute()
        
        return jsonify({"ok": True, "message": "Unfollowed successfully"})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================================================
# User Posts and Activity Feed System
# ================================================

@app.route("/api/posts", methods=["POST"])
@require_auth
def create_user_post():
    """Create a new user post for activity feed"""
    try:
        current_user = get_current_user()
        data = request.json or {}
        
        content = sanitize_input(data.get('content', ''), 1000)
        if not content:
            return jsonify({"error": "Content is required"}), 400
        
        post_data = {
            'user_id': current_user['id'],
            'content': content,
            'post_type': data.get('post_type', 'general'),
            'recipe_id': data.get('recipe_id'),
            'group_id': data.get('group_id'),
            'metadata': data.get('metadata', {}),
            'is_public': data.get('is_public', True)
        }
        
        response = supabase.table('user_posts').insert(post_data).execute()
        
        if response.data:
            return jsonify({"ok": True, "post": response.data[0]})
        else:
            return jsonify({"error": "Failed to create post"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/posts/feed", methods=["GET"])
@require_auth
def get_activity_feed():
    """Get activity feed for current user"""
    try:
        current_user = get_current_user()
        feed_type = request.args.get('type', 'following')  # following, public, trending
        limit = min(int(request.args.get('limit', 20)), 50)
        
        if feed_type == 'following':
            # Get posts from users the current user follows
            following_response = supabase.table('user_follows').select('following_id').eq('follower_id', current_user['id']).execute()
            following_ids = [f['following_id'] for f in following_response.data] if following_response.data else []
            following_ids.append(current_user['id'])  # Include own posts
            
            if following_ids:
                posts_response = supabase.table('user_posts')\
                    .select('*, profiles!user_id(username, name, avatar_url), recipes(id, title)')\
                    .in_('user_id', following_ids)\
                    .eq('is_public', True)\
                    .order('created_at', desc=True)\
                    .limit(limit)\
                    .execute()
            else:
                posts_response = type('obj', (object,), {'data': []})()
        
        elif feed_type == 'public':
            # Get all public posts
            posts_response = supabase.table('user_posts')\
                .select('*, profiles!user_id(username, name, avatar_url), recipes(id, title)')\
                .eq('is_public', True)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
        
        else:  # trending, latest, etc.
            posts_response = supabase.table('user_posts')\
                .select('*, profiles!user_id(username, name, avatar_url), recipes(id, title)')\
                .eq('is_public', True)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
        
        return jsonify({"ok": True, "posts": posts_response.data or []})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================================================
# Git-Style Repository Interface
# ================================================

@app.route("/api/recipes/<int:recipe_id>/stats", methods=["GET"])
def get_recipe_stats(recipe_id):
    """Get Git-style statistics for a recipe"""
    try:
        # Get recipe basic info
        recipe_response = supabase.table('recipes').select('*').eq('id', recipe_id).execute()
        if not recipe_response.data:
            return jsonify({"error": "Recipe not found"}), 404
        
        recipe = recipe_response.data[0]
        
        # Get fork count (direct from recipe or calculate)
        fork_count = recipe.get('fork_count', 0)
        if fork_count == 0:
            fork_response = supabase.table('recipe_forks').select('id', count='exact').eq('original_recipe_id', recipe_id).execute()
            fork_count = fork_response.count or 0
        
        # Get version count
        version_count = recipe.get('version_count', 0)
        if version_count == 0:
            version_response = supabase.table('recipe_versions').select('id', count='exact').eq('recipe_id', recipe_id).execute()
            version_count = version_response.count or 0
        
        # Get contributor count
        contributor_response = supabase.table('recipe_contributors').select('id', count='exact').eq('recipe_id', recipe_id).execute()
        contributor_count = contributor_response.count or 0
        
        # Get branch count
        branch_response = supabase.table('recipe_branches').select('id', count='exact').eq('recipe_id', recipe_id).eq('is_active', True).execute()
        branch_count = branch_response.count or 0
        
        # Get stars (likes)
        star_count = recipe.get('star_count', 0)
        if star_count == 0:
            star_response = supabase.table('recipe_likes').select('id', count='exact').eq('recipe_id', recipe_id).execute()
            star_count = star_response.count or 0
        
        # Get latest commit info
        latest_commit = None
        version_response = supabase.table('recipe_versions').select('''
            *,
            author:profiles!recipe_versions_author_id_fkey(username, name, avatar_url)
        ''').eq('recipe_id', recipe_id).order('version_number', desc=True).limit(1).execute()
        
        if version_response.data:
            version = version_response.data[0]
            author = version.get('author', {}) or {}
            latest_commit = {
                'version': f"v{version['version_number']}",
                'message': version['commit_message'],
                'author': {
                    'name': author.get('name', 'Unknown'),
                    'username': author.get('username', 'unknown'),
                    'avatar_url': author.get('avatar_url', '')
                },
                'date': version['created_at']
            }
        
        return jsonify({
            "recipe_id": recipe_id,
            "title": recipe['title'],
            "is_fork": recipe.get('is_fork', False),
            "original_recipe_id": recipe.get('original_recipe_id'),
            "stats": {
                "forks": fork_count,
                "stars": star_count,
                "versions": version_count,
                "contributors": contributor_count,
                "branches": branch_count
            },
            "latest_commit": latest_commit,
            "created_at": recipe['created_at'],
            "updated_at": recipe['updated_at']
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipes/<int:recipe_id>/network", methods=["GET"])
def get_recipe_network(recipe_id):
    """Get the fork network graph for a recipe"""
    try:
        # Find the root recipe (original)
        recipe_response = supabase.table('recipes').select('*').eq('id', recipe_id).execute()
        if not recipe_response.data:
            return jsonify({"error": "Recipe not found"}), 404
        
        recipe = recipe_response.data[0]
        root_recipe_id = recipe.get('original_recipe_id') or recipe_id
        
        # Get the complete fork tree starting from root
        try:
            network_response = supabase.rpc('get_recipe_fork_tree', {
                'p_recipe_id': root_recipe_id
            }).execute()
        except:
            # Fallback if function doesn't exist
            network_response = supabase.table('recipe_forks').select('''
                *,
                forked_recipe:recipes!recipe_forks_forked_recipe_id_fkey(id, title),
                forked_by:profiles!recipe_forks_forked_by_user_id_fkey(username, name)
            ''').eq('original_recipe_id', root_recipe_id).execute()
        
        # Build network structure
        network = {
            "root": {
                "id": root_recipe_id,
                "title": recipe['title'] if recipe_id == root_recipe_id else "Original Recipe",
                "owner": "system"  # Would need to fetch actual owner
            },
            "nodes": [],
            "edges": []
        }
        
        if hasattr(network_response, 'data') and network_response.data:
            for fork in network_response.data:
                if 'forked_recipe_id' in fork:  # New format
                    network["nodes"].append({
                        "id": fork['forked_recipe_id'],
                        "title": fork.get('forked_recipe_title', 'Fork'),
                        "owner": fork.get('forked_by_username', 'unknown'),
                        "depth": fork.get('fork_depth', 1),
                        "created_at": fork['created_at']
                    })
                else:  # Fallback format
                    forked_recipe = fork.get('forked_recipe', {}) or {}
                    forked_by = fork.get('forked_by', {}) or {}
                    network["nodes"].append({
                        "id": fork['forked_recipe_id'],
                        "title": forked_recipe.get('title', 'Fork'),
                        "owner": forked_by.get('username', 'unknown'),
                        "depth": 1,
                        "created_at": fork['created_at']
                    })
                
                # Add edge from parent to this fork
                network["edges"].append({
                    "from": root_recipe_id,
                    "to": fork['forked_recipe_id'],
                    "type": "fork"
                })
        
        return jsonify(network)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipes/<int:recipe_id>/compare/<int:other_recipe_id>", methods=["GET"])
def compare_recipes(recipe_id, other_recipe_id):
    """Compare two recipes (like GitHub compare)"""
    try:
        # Get both recipes
        recipe1_response = supabase.table('recipes').select('*').eq('id', recipe_id).execute()
        recipe2_response = supabase.table('recipes').select('*').eq('id', other_recipe_id).execute()
        
        if not recipe1_response.data or not recipe2_response.data:
            return jsonify({"error": "One or both recipes not found"}), 404
        
        recipe1 = recipe1_response.data[0]
        recipe2 = recipe2_response.data[0]
        
        # Calculate differences
        differences = {}
        
        # Title difference
        if recipe1['title'] != recipe2['title']:
            differences['title'] = {
                'base': recipe1['title'],
                'compare': recipe2['title']
            }
        
        # Ingredients difference
        try:
            ingredients1 = json.loads(recipe1.get('ingredients_json', '[]'))
            ingredients2 = json.loads(recipe2.get('ingredients_json', '[]'))
            
            if ingredients1 != ingredients2:
                differences['ingredients'] = {
                    'base_count': len(ingredients1),
                    'compare_count': len(ingredients2),
                    'added': [],
                    'removed': [],
                    'modified': []
                }
                # Simple comparison - could be enhanced with proper diff algorithm
        except:
            # TODO: Add specific exception handling for JSON parsing and comparison errors
            # TODO: Implement proper diff algorithm using difflib or similar library
            pass
        
        # Steps difference
        if recipe1.get('steps', '') != recipe2.get('steps', ''):
            differences['steps'] = {
                'base_length': len(recipe1.get('steps', '')),
                'compare_length': len(recipe2.get('steps', '')),
                'changed': True
            }
        
        # Other field differences
        for field in ['category', 'tags', 'servings', 'prep_time', 'cook_time', 'difficulty']:
            if recipe1.get(field) != recipe2.get(field):
                differences[field] = {
                    'base': recipe1.get(field),
                    'compare': recipe2.get(field)
                }
        
        return jsonify({
            "base_recipe": {
                "id": recipe_id,
                "title": recipe1['title']
            },
            "compare_recipe": {
                "id": other_recipe_id,
                "title": recipe2['title']
            },
            "differences": differences,
            "has_changes": len(differences) > 0
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipes/<int:recipe_id>/star", methods=["POST"])
@require_auth
def star_recipe(recipe_id):
    """Star (like) a recipe"""
    try:
        current_user = get_current_user()
        
        # Pure dev mode - mock starring
        if is_development():
            # Check if recipe exists in dev data
            recipe_exists = False
            for recipe in DEV_RECIPES:
                if recipe.get('id') == recipe_id:
                    recipe_exists = True
                    # Update star count
                    recipe['star_count'] = recipe.get('star_count', 0) + 1
                    break
            
            if not recipe_exists:
                return jsonify({"error": "Recipe not found"}), 404
            
            print(f"⭐ Dev user {current_user['username']} starred recipe ID: {recipe_id}")
            return jsonify({"ok": True, "message": "Recipe starred! ⭐"})
        
        # Production mode - check Supabase is available
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
        
        # Check if recipe exists
        recipe_response = supabase.table('recipes').select('*').eq('id', recipe_id).execute()
        if not recipe_response.data:
            return jsonify({"error": "Recipe not found"}), 404
        
        # Check if already starred
        existing = supabase.table('recipe_likes').select('id').eq('recipe_id', recipe_id).eq('user_id', current_user['id']).execute()
        if existing.data:
            return jsonify({"error": "Recipe already starred"}), 400
        
        # Create star
        star_data = {
            'recipe_id': recipe_id,
            'user_id': current_user['id']
        }
        
        response = supabase.table('recipe_likes').insert(star_data).execute()
        
        if response.data:
            return jsonify({"ok": True, "message": "Recipe starred! ⭐"})
        else:
            return jsonify({"error": "Failed to star recipe"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipes/<int:recipe_id>/unstar", methods=["POST"])
@require_auth
def unstar_recipe(recipe_id):
    """Unstar (unlike) a recipe"""
    try:
        current_user = get_current_user()
        
        # Pure dev mode - mock unstarring
        if is_development():
            # Check if recipe exists and decrease star count
            for recipe in DEV_RECIPES:
                if recipe.get('id') == recipe_id:
                    if recipe.get('star_count', 0) > 0:
                        recipe['star_count'] = recipe['star_count'] - 1
                    break
            
            print(f"⭐ Dev user {current_user['username']} unstarred recipe ID: {recipe_id}")
            return jsonify({"ok": True, "message": "Recipe unstarred"})
        
        # Production mode - check Supabase is available
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
        
        # Remove star
        response = supabase.table('recipe_likes').delete().eq('recipe_id', recipe_id).eq('user_id', current_user['id']).execute()
        
        return jsonify({"ok": True, "message": "Recipe unstarred"})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard/stats", methods=["GET"])
def get_dashboard_stats():
    """Get real-time dashboard statistics"""
    try:
        # Pure dev mode - use mock data
        if is_development():
            return jsonify({
                "total_recipes": len(DEV_RECIPES),
                "total_forks": 12,  # Mock data
                "active_cooks": len(DEV_USERS),
                "recipes_today": 1
            })
        
        # Production mode - use Supabase
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
            
        # Get total recipes count
        recipes_response = supabase.table('recipes').select('id', count='exact').execute()
        total_recipes = recipes_response.count or 0
        
        # Get total forks count
        forks_response = supabase.table('recipe_forks').select('id', count='exact').execute()
        total_forks = forks_response.count or 0
        
        # Get active users (users who have created recipes or posted recently)
        active_users_response = supabase.table('profiles').select('id', count='exact').execute()
        active_cooks = active_users_response.count or 0
        
        # Get recipes created today
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        today_recipes_response = supabase.table('recipes').select('id', count='exact').gte('created_at', today).execute()
        recipes_today = today_recipes_response.count or 0
        
        return jsonify({
            "total_recipes": total_recipes,
            "total_forks": total_forks,
            "active_cooks": active_cooks,
            "recipes_today": recipes_today
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================================================
# User Suggestions System
# ================================================

@app.route("/api/users/suggestions", methods=["GET"])
@require_auth
def get_user_suggestions():
    """Get intelligent user suggestions for the current user"""
    try:
        current_user = get_current_user()
        limit = min(int(request.args.get('limit', 10)), 20)  # Max 20 suggestions
        
        # Pure dev mode - return mock suggestions
        if is_development():
            mock_suggestions = []
            for email, user_data in list(DEV_USERS.items())[:limit]:
                if user_data['id'] != current_user['id']:
                    mock_suggestions.append({
                        'id': user_data['id'],
                        'username': user_data['username'],
                        'name': user_data['name'],
                        'avatar_url': user_data['avatar_url'],
                        'bio': f"Development user - {user_data['name']}",
                        'followers_count': 5,
                        'following_count': 3,
                        'recipe_count': 2,
                        'suggestion_reason': 'Development suggestion',
                        'relevance_score': 5.0,
                        'mutual_connections': 0,
                        'activity_score': 2.0,
                        'is_new_user': False,
                        'created_at': '2025-01-01T00:00:00Z'
                    })
            return jsonify({"suggestions": mock_suggestions})
        
        # Production mode - use Supabase function
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
        
        response = supabase.rpc('get_suggested_users', {
            'input_user_id': current_user['id'],
            'limit_count': limit
        }).execute()
        
        suggestions = response.data or []
        return jsonify({"suggestions": suggestions})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/users/suggestions/stats", methods=["GET"])
@require_auth
def get_user_suggestion_stats():
    """Get analytics for user suggestions"""
    try:
        current_user = get_current_user()
        
        # Pure dev mode - return mock stats
        if is_development():
            return jsonify({
                "total_available_users": len(DEV_USERS) - 1,
                "mutual_connection_suggestions": 1,
                "similar_interest_suggestions": 2,
                "active_user_suggestions": 2,
                "popular_user_suggestions": 1,
                "new_user_suggestions": 0,
                "already_following_count": 0
            })
        
        # Production mode - use Supabase function
        if not supabase:
            return jsonify({"error": "Database not available"}), 500
        
        response = supabase.rpc('get_user_suggestion_stats', {
            'input_user_id': current_user['id']
        }).execute()
        
        stats = response.data[0] if response.data else {}
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/sentry-test")
def sentry_test():
    """Test endpoint to trigger a Sentry error for testing"""
    if not os.getenv('SENTRY_DSN'):
        return jsonify({"error": "Sentry not configured"}), 400
    
    # Trigger a test error
    division_by_zero = 1 / 0
    return jsonify({"message": "This should never be reached"})

@app.route("/api/user/preferences", methods=["GET", "PUT"])
@require_auth
def user_preferences():
    """Get or update user preferences"""
    try:
        current_user = get_current_user()
        
        if request.method == "GET":
            # Pure dev mode - return default preferences
            if is_development():
                default_preferences = {
                    "notifications": {
                        "email_on_follow": True,
                        "email_on_recipe_fork": True,
                        "email_on_comment": True,
                        "push_notifications": True
                    },
                    "privacy": {
                        "profile_public": True,
                        "recipes_public": True,
                        "show_activity": True
                    },
                    "display": {
                        "theme": "dark",
                        "language": "en",
                        "measurement_units": "metric"
                    }
                }
                return jsonify({"preferences": default_preferences})
            
            # Production mode - get preferences from database
            if not supabase:
                return jsonify({"error": "Database not available"}), 500
                
            try:
                # Get user preferences from database
                response = supabase.table('user_preferences').select('*').eq('user_id', current_user['id']).execute()
                
                if response.data and len(response.data) > 0:
                    preferences = response.data[0].get('preferences', {})
                else:
                    # Return default preferences if none exist
                    preferences = {
                        "notifications": {
                            "email_on_follow": True,
                            "email_on_recipe_fork": True,
                            "email_on_comment": True,
                            "push_notifications": True
                        },
                        "privacy": {
                            "profile_public": True,
                            "recipes_public": True,
                            "show_activity": True
                        },
                        "display": {
                            "theme": "dark",
                            "language": "en",
                            "measurement_units": "metric"
                        }
                    }
                
                return jsonify({"preferences": preferences})
            except Exception as e:
                print(f"Error fetching user preferences: {e}")
                # Return default preferences on error
                default_preferences = {
                    "notifications": {
                        "email_on_follow": True,
                        "email_on_recipe_fork": True,
                        "email_on_comment": True,
                        "push_notifications": True
                    },
                    "privacy": {
                        "profile_public": True,
                        "recipes_public": True,
                        "show_activity": True
                    },
                    "display": {
                        "theme": "dark",
                        "language": "en",
                        "measurement_units": "metric"
                    }
                }
                return jsonify({"preferences": default_preferences})
        
        elif request.method == "PUT":
            # Update user preferences
            data = request.get_json() or {}
            preferences = data.get('preferences', {})
            
            # Pure dev mode - just return success
            if is_development():
                return jsonify({"ok": True, "preferences": preferences})
            
            # Production mode - update preferences in database
            if not supabase:
                return jsonify({"error": "Database not available"}), 500
                
            try:
                # Upsert user preferences
                upsert_data = {
                    'user_id': current_user['id'],
                    'preferences': preferences,
                    'updated_at': 'now()'
                }
                
                response = supabase.table('user_preferences').upsert(upsert_data).execute()
                return jsonify({"ok": True, "preferences": preferences})
            except Exception as e:
                print(f"Error updating user preferences: {e}")
                return jsonify({"error": "Failed to update preferences"}), 500
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = config.PORT
    debug = config.DEBUG
    app.run(host="0.0.0.0", port=port, debug=debug)