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

# Flask app
app = Flask(__name__)
app.config.from_object(config)
# Configure CORS with specific origins for production security
allowed_origins = [
    "https://nuestrasrecetas.club",
    "https://www.nuestrasrecetas.club"
]

if config.FLASK_ENV == 'development':
    allowed_origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

CORS(app, 
     origins=allowed_origins,
     supports_credentials=True,
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])

# Initialize Supabase client
supabase: Optional[Client] = None
if config.use_supabase:
    try:
        supabase = create_client(
            supabase_url=config.SUPABASE_URL,
            supabase_key=config.SUPABASE_KEY
        )
        print("✅ Supabase client initialized")
    except Exception as e:
        print(f"⚠️  Supabase initialization failed: {e}")
        supabase = None
else:
    print("❌ Supabase not configured - check .env file")

def get_current_user():
    """Get current user from Supabase session"""
    user_id = session.get('user_id')
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

@app.route("/health")
def health_check():
    """Health check endpoint"""
    try:
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
    if not supabase:
        return jsonify({"error": "Supabase no configurado"}), 500
        
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email y contraseña son requeridos"}), 400
    
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
@require_auth
def list_recipes():
    try:
        q = request.args.get("q", "").strip().lower()
        current_user = get_current_user()
        
        print(f"Current user: {current_user}")  # Debug log
        
        # Get recipes from Supabase using the current user's UUID
        try:
            response = supabase.table('recipes').select('*').eq('user_id', current_user['id']).execute()
            recipes = response.data or []
        except Exception as e:
            print(f"Error fetching recipes: {e}")
            # If there's a schema mismatch, return empty list for now
            recipes = []
        
        out = []
        for r in recipes:
            # Filter by search query
            searchable = " ".join([
                r.get('title', ''),
                r.get('category', ''),
                r.get('tags', '')
            ]).lower()
            
            if q and q not in searchable:
                continue
                
            out.append({
                "id": r['id'],
                "title": r['title'],
                "category": r.get('category', ''),
                "tags": r.get('tags', ''),
                "servings": r.get('servings', 2),
            })
        
        print(f"Returning {len(out)} recipes")  # Debug log
        return jsonify(out)
    except Exception as e:
        print(f"Error in list_recipes: {e}")  # Debug log
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipe/<int:rid>", methods=["GET"])
@require_auth
def get_recipe(rid):
    try:
        current_user = get_current_user()
        
        # Get recipe from Supabase
        response = supabase.table('recipes').select('*').eq('id', rid).eq('user_id', current_user['id']).execute()
        
        if not response.data or len(response.data) == 0:
            return jsonify({"error": "not found"}), 404
            
        recipe = response.data
        # Parse ingredients JSON
        try:
            recipe['ingredients'] = json.loads(recipe.get('ingredients_json', '[]'))
        except:
            recipe['ingredients'] = []
            
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
        
        # Check for existing title
        existing = supabase.table('recipes').select('id').eq('title', title).eq('user_id', current_user['id']).execute()
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
        
        response = supabase.table('recipes').insert(recipe_data).execute()
        
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
        # Get profile data from profiles table
        profile_response = supabase.table('profiles').select('*').eq('username', username).execute()
        if not profile_response.data or len(profile_response.data) == 0:
            return jsonify({"error": "Profile not found"}), 404
        
        profile = profile_response.data[0]
        
        # Check if current user is following this profile (if authenticated)
        current_user = get_current_user()
        is_following = False
        follows_back = False
        
        if current_user and current_user['id'] != profile['id']:
            # Check if current user follows this profile
            follow_check = supabase.table('user_follows').select('id').eq('follower_id', current_user['id']).eq('following_id', profile['id']).execute()
            is_following = bool(follow_check.data)
            
            # Check if this profile follows current user back
            follows_back_check = supabase.table('user_follows').select('id').eq('follower_id', profile['id']).eq('following_id', current_user['id']).execute()
            follows_back = bool(follows_back_check.data)
        
        # Add follow status to profile
        profile['is_following'] = is_following
        profile['follows_back'] = follows_back
        
        # Get user's public recipes (simplified for now)
        try:
            recipes_response = supabase.table('recipes').select('*').eq('user_id', profile['id']).eq('is_public', True).order('created_at', desc=True).limit(10).execute()
        except Exception as e:
            print(f"Error fetching recipes: {e}")
            recipes_response = {"data": []}
        
        # Get user's groups (temporarily empty until migration is applied)
        groups_response = {"data": []}
        
        return jsonify({
            "profile": profile,
            "recipes": recipes_response.data or [],
            "groups": groups_response.data or []
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
@require_auth
def get_feed():
    """Get user's feed (recipes from followed users)"""
    try:
        current_user = get_current_user()
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        offset = (page - 1) * limit
        
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
@require_auth
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
        
        # Get original recipe
        original_recipe = supabase.table('recipes').select('*').eq('id', recipe_id).single().execute()
        if not original_recipe.data:
            return jsonify({"error": "Recipe not found"}), 404
        
        original = original_recipe.data
        
        # Create forked recipe
        fork_data = {
            'user_id': current_user['id'],
            'title': f"{original['title']} (Fork)",
            'description': original['description'],
            'category': original['category'],
            'tags': original['tags'],
            'servings': original['servings'],
            'prep_time': original['prep_time'],
            'cook_time': original['cook_time'],
            'difficulty': original['difficulty'],
            'steps': original['steps'],
            'ingredients_json': original['ingredients_json'],
            'image_url': original['image_url'],
            'is_public': data.get('is_public', True),
            'original_recipe_id': recipe_id,
            'is_fork': True
        }
        
        # Create the forked recipe
        forked_recipe = supabase.table('recipes').insert(fork_data).execute()
        if not forked_recipe.data:
            return jsonify({"error": "Failed to create fork"}), 500
        
        forked_id = forked_recipe.data[0]['id']
        
        # Create fork relationship with enhanced data
        fork_relationship = {
            'original_recipe_id': recipe_id,
            'forked_recipe_id': forked_id,
            'forked_by_user_id': current_user['id'],
            'fork_reason': data.get('fork_reason', ''),
            'branch_name': data.get('branch_name', 'main')
        }
        
        supabase.table('recipe_forks').insert(fork_relationship).execute()
        
        # Create initial version (commit) for the forked recipe
        version_data = {
            'recipe_id': forked_id,
            'version_number': 1,
            'commit_message': f"Initial fork from recipe #{recipe_id}",
            'author_id': current_user['id'],
            'changes_json': {"action": "fork", "from_recipe_id": recipe_id},
            'snapshot_json': {
                'title': fork_data['title'],
                'description': fork_data['description'],
                'ingredients': json.loads(fork_data['ingredients_json']),
                'steps': fork_data['steps'],
                'servings': fork_data['servings'],
                'category': fork_data['category'],
                'tags': fork_data['tags']
            }
        }
        supabase.table('recipe_versions').insert(version_data).execute()
        
        # Create main branch for the forked recipe
        branch_data = {
            'recipe_id': forked_id,
            'branch_name': 'main',
            'description': 'Main branch',
            'created_by': current_user['id'],
            'is_default': True
        }
        branch_response = supabase.table('recipe_branches').insert(branch_data).execute()
        
        # Update recipe with branch reference
        if branch_response.data:
            supabase.table('recipes').update({
                'current_branch_id': branch_response.data[0]['id']
            }).eq('id', forked_id).execute()
        
        # Add creator as contributor
        contributor_data = {
            'recipe_id': forked_id,
            'contributor_id': current_user['id'],
            'contribution_type': 'forker',
            'commit_count': 1
        }
        supabase.table('recipe_contributors').insert(contributor_data).execute()
        
        return jsonify({
            "ok": True, 
            "message": "Recipe forked successfully! 🍴",
            "forked_recipe_id": forked_id
        })
    except Exception as e:
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
        
        # Check if groups table exists
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
        
        # Check if group exists and is public
        group_response = supabase.table('groups').select('*').eq('id', group_id).single().execute()
        if not group_response.data:
            return jsonify({"error": "Group not found"}), 404
        
        group = group_response.data
        if not group.get('is_public', True):
            return jsonify({"error": "Cannot join private group"}), 403
        
        # Check if already a member
        existing = supabase.table('group_members').select('*').eq('group_id', group_id).eq('user_id', current_user['id']).execute()
        if existing.data:
            return jsonify({"error": "Already a member of this group"}), 400
        
        # Join group
        member_data = {
            'group_id': group_id,
            'user_id': current_user['id'],
            'role': 'member'
        }
        response = supabase.table('group_members').insert(member_data).execute()
        
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
        
        if not query:
            return jsonify({"users": []})
        
        # Search users using simple SQL (since RPC might not work)
        current_user = get_current_user()
        
        response = supabase.table('profiles').select('''
            id, username, name, avatar_url, bio, followers_count, following_count, created_at
        ''').neq('id', current_user['id']).or_(f'username.ilike.%{query}%,name.ilike.%{query}%').limit(limit).execute()
        
        users = response.data or []
        
        # Add follow status for each user
        for user in users:
            # Check if current user follows this user
            follow_check = supabase.table('user_follows').select('id').eq('follower_id', current_user['id']).eq('following_id', user['id']).execute()
            user['is_following'] = bool(follow_check.data)
            
            # Check if this user follows current user back
            follows_back_check = supabase.table('user_follows').select('id').eq('follower_id', user['id']).eq('following_id', current_user['id']).execute()
            user['follows_back'] = bool(follows_back_check.data)
        
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

@app.route("/sentry-test")
def sentry_test():
    """Test endpoint to trigger a Sentry error for testing"""
    if not os.getenv('SENTRY_DSN'):
        return jsonify({"error": "Sentry not configured"}), 400
    
    # Trigger a test error
    division_by_zero = 1 / 0
    return jsonify({"message": "This should never be reached"})


if __name__ == "__main__":
    port = config.PORT
    debug = config.DEBUG
    app.run(host="0.0.0.0", port=port, debug=debug)