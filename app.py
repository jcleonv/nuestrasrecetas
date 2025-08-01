#!/usr/bin/env python3
"""
NuestrasRecetas.club - Pure Supabase Implementation
Flask app using Supabase directly without SQLAlchemy
"""

import json
import os
from collections import defaultdict
from typing import Optional, Dict, Any
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from supabase import create_client, Client

from config import Config

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

# Flask app
app = Flask(__name__)
app.config.from_object(config)
CORS(app)

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
        # Handle test sessions
        if access_token == 'test-token':
            # For testing - directly get user profile
            profile_response = supabase.table('profiles').select('*').eq('id', user_id).execute()
            if profile_response.data and len(profile_response.data) > 0:
                return profile_response.data[0]
            else:
                return None
        
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
    
    if len(password) < 6:
        return jsonify({"error": "La contraseña debe tener al menos 6 caracteres"}), 400
    
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

# Temporary testing endpoint - REMOVE IN PRODUCTION
@app.route("/api/auth/test-login", methods=["POST"])
def test_login():
    """Temporary endpoint for testing - bypasses email confirmation"""
    if not supabase:
        return jsonify({"error": "Supabase no configurado"}), 500
    
    # Use the existing confirmed user for testing
    user_id = "81c61a80-4e61-4cf6-b699-040db00b5e96"  # jcleonvil user
    
    try:
        # Get user profile from Supabase profiles table
        print(f"Debug: Looking for user with ID: {user_id}")
        profile_response = supabase.table('profiles').select('*').eq('id', user_id).execute()
        print(f"Debug: Profile response: {profile_response}")
        
        if profile_response.data and len(profile_response.data) > 0:
            # Create a mock session for testing
            session['user_id'] = user_id
            session['supabase_access_token'] = 'test-token'
            session['supabase_refresh_token'] = 'test-refresh'
            
            return jsonify({
                "message": "Test login successful",
                "user": profile_response.data[0]
            })
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        
        current_user = get_current_user()
        
        # Check for existing title
        existing = supabase.table('recipes').select('id').eq('title', title).eq('user_id', current_user['id']).execute()
        if existing.data:
            return jsonify({"error": "Title already exists"}), 400
        
        # Create recipe
        recipe_data = {
            'user_id': current_user['id'],
            'title': title,
            'category': data.get("category", ""),
            'tags': data.get("tags", ""),
            'servings': int(data.get("servings", 2)),
            'ingredients_json': json.dumps(data.get("ingredients", []), ensure_ascii=False),
            'steps': data.get("steps", "")
        }
        
        response = supabase.table('recipes').insert(recipe_data).execute()
        
        if response.data:
            return jsonify({"ok": True, "id": response.data[0]['id']})
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
        
        new_title = (data.get("title") or "").strip()
        if not new_title:
            return jsonify({"error": "Title required"}), 400
        
        # Check for title conflicts (excluding current recipe)
        title_check = supabase.table('recipes').select('id').eq('title', new_title).eq('user_id', current_user['id']).neq('id', rid).execute()
        if title_check.data:
            return jsonify({"error": "Title already exists"}), 400
        
        # Update recipe
        update_data = {
            'title': new_title,
            'category': data.get("category", ""),
            'tags': data.get("tags", ""),
            'servings': int(data.get("servings", 2)),
            'ingredients_json': json.dumps(data.get("ingredients", []), ensure_ascii=False),
            'steps': data.get("steps", "")
        }
        
        response = supabase.table('recipes').update(update_data).eq('id', rid).eq('user_id', current_user['id']).execute()
        
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
        
        # Validate required fields
        if 'username' in data and data['username']:
            # Check if username is already taken
            existing = supabase.table('profiles').select('id').eq('username', data['username']).neq('id', current_user['id']).execute()
            if existing.data:
                return jsonify({"error": "Username already taken"}), 400
        
        # Update profile
        update_data = {}
        for field in ['username', 'name', 'bio', 'avatar_url', 'is_public']:
            if field in data:
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
            'user_id': current_user['id'],
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
            'original_recipe_id': recipe_id
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
            'fork_reason': data.get('fork_reason', '')
        }
        
        supabase.table('recipe_forks').insert(fork_relationship).execute()
        
        return jsonify({
            "ok": True, 
            "message": "Recipe forked successfully! 🍴",
            "forked_recipe_id": forked_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/recipes/<int:recipe_id>/forks", methods=["GET"])
def get_recipe_forks(recipe_id):
    """Get all forks of a recipe"""
    try:
        response = supabase.table('recipe_forks').select('''
            *,
            forked_recipe:recipes!recipe_forks_forked_recipe_id_fkey(id, title, image_url, user_id),
            forked_by:profiles!recipe_forks_forked_by_user_id_fkey(username, name, avatar_url)
        ''').eq('original_recipe_id', recipe_id).execute()
        
        return jsonify({"forks": response.data or []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ================================================
# User Posts & Updates
# ================================================

@app.route("/api/posts", methods=["POST"])
@require_auth
def create_user_post():
    """Create a user post/update"""
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        if not data or not data.get('content'):
            return jsonify({"error": "Content is required"}), 400
        
        post_data = {
            'user_id': current_user['id'],
            'content': data['content'],
            'post_type': data.get('post_type', 'update'),
            'recipe_id': data.get('recipe_id'),
            'is_public': data.get('is_public', True)
        }
        
        response = supabase.table('user_posts').insert(post_data).execute()
        
        if response.data:
            return jsonify({"ok": True, "message": "Post created! 📝", "post": response.data[0]})
        else:
            return jsonify({"error": "Failed to create post"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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



if __name__ == "__main__":
    port = config.PORT
    debug = config.DEBUG
    app.run(host="0.0.0.0", port=port, debug=debug)