
### File: app.py
### --------------------------------
import json
import os
from collections import defaultdict
from typing import Optional
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from supabase import create_client, Client

from config import Config
from database import get_session, Recipe, Plan, Comment

config = Config()

# Units
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

# Supabase client (if configured)
supabase: Optional[Client] = None
if config.use_supabase:
    try:
        # Initialize with minimal options to avoid proxy error
        supabase = create_client(
            supabase_url=config.SUPABASE_URL,
            supabase_key=config.SUPABASE_KEY
        )
        print("✅ Supabase client initialized")
    except Exception as e:
        print(f"⚠️  Supabase initialization failed: {e}")
        print("   Continuing with SQLite...")
        supabase = None

# Authentication helpers
def get_current_user():
    """Get current user from Supabase session or return None for guest mode"""
    user_id = session.get('user_id')
    access_token = session.get('supabase_access_token')
    
    if not user_id or not access_token:
        return None
    
    # Verify token is still valid with Supabase
    if supabase:
        try:
            # Set the auth token for this request
            supabase.auth.set_session(access_token, session.get('supabase_refresh_token'))
            
            # Try to get current user from Supabase
            supabase_user = supabase.auth.get_user()
            if not supabase_user.user or supabase_user.user.id != user_id:
                # Token invalid or user mismatch, clear session
                session.pop('user_id', None)
                session.pop('supabase_access_token', None)
                session.pop('supabase_refresh_token', None)
                return None
                
            # Get user profile from Supabase profiles table
            profile_response = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
            if profile_response.data:
                return profile_response.data
            else:
                return None
        except Exception as e:
            # Token expired or invalid, clear session
            session.pop('user_id', None)
            session.pop('supabase_access_token', None)
            session.pop('supabase_refresh_token', None)
            return None
    
    return None

def require_auth(f):
    """Decorator to require authentication (optional - allows guest mode)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If using Supabase, require authentication for multi-user features
        if supabase and not get_current_user():
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def bootstrap_plan(sess, user_id):
    """Bootstrap plan for authenticated user"""
    if not user_id:
        raise ValueError("User ID is required for plans")
    
    plan = sess.query(Plan).filter(Plan.user_id == user_id).first()
    
    if not plan:
        plan = Plan(name="Week Plan", user_id=user_id)
        plan.set_data({d: [] for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]})
        sess.add(plan)
        sess.commit()
    return plan

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

# Temporary test route to check dashboard styling
@app.route("/test-dashboard")
def test_dashboard():
    return render_template("index.html", user={"id": "test", "username": "testuser", "name": "Test User"})

@app.route("/health")
def health_check():
    """Health check endpoint for Docker/monitoring"""
    try:
        from sqlalchemy import text
        # Test database connection
        sess = get_session()
        sess.execute(text("SELECT 1"))
        sess.close()
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "supabase": "enabled" if config.use_supabase else "disabled"
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503

# Supabase Authentication Routes
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
            # Profile will be automatically created by the trigger
            # Just check if username is available in Supabase
            try:
                existing_user = supabase.table('profiles').select('username').eq('username', username).execute()
                if existing_user.data:
                    return jsonify({"error": "Este nombre de usuario ya está en uso"}), 400
                
                return jsonify({
                    "message": "Cuenta creada exitosamente. Revisa tu email para confirmar tu cuenta.",
                    "user_id": response.user.id
                })
            except Exception as e:
                print(f"Username check error: {e}")
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
        return jsonify({"error": "Error al crear la cuenta"}), 500

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
                profile_response = supabase.table('profiles').select('*').eq('id', response.user.id).single().execute()
                
                if profile_response.data:
                    # Update last active
                    supabase.table('profiles').update({
                        'last_active': 'now()'
                    }).eq('id', response.user.id).execute()
                    
                    user_profile = profile_response.data
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
            return jsonify({"error": "Por favor confirma tu email antes de iniciar sesión"}), 401
        return jsonify({"error": "Error al iniciar sesión"}), 500

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

@app.route("/api/recipes", methods=["GET"])
@require_auth
def list_recipes():
    sess = get_session()
    try:
        q = request.args.get("q", "").strip().lower()
        current_user = get_current_user()
        
        # Query recipes for current user or guest mode
        if current_user:
            recipes = sess.query(Recipe).filter(Recipe.user_id == current_user.get('id')).order_by(Recipe.title.asc()).all()
        else:
            # Guest mode - get recipes with no user_id
            recipes = sess.query(Recipe).filter(Recipe.user_id.is_(None)).order_by(Recipe.title.asc()).all()
        
        out = []
        for r in recipes:
            hay = " ".join([r.title or "", r.category or "", r.tags or ""]).lower()
            if q and q not in hay:
                continue
            out.append({
                "id": r.id,
                "title": r.title,
                "category": r.category or "",
                "tags": r.tags or "",
                "servings": r.servings or 2,
            })
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        sess.close()

@app.route("/api/recipe/<int:rid>", methods=["GET"])
@require_auth
def get_recipe(rid):
    sess = get_session()
    try:
        current_user = get_current_user()
        
        # Query recipe for current user or guest mode
        if current_user:
            r = sess.query(Recipe).filter(Recipe.id == rid, Recipe.user_id == current_user.get('id')).first()
        else:
            r = sess.query(Recipe).filter(Recipe.id == rid, Recipe.user_id.is_(None)).first()
        
        if not r:
            return jsonify({"error": "not found"}), 404
        return jsonify(r.to_dict())
    finally:
        sess.close()

@app.route("/api/recipe", methods=["POST"])
@require_auth
def create_recipe():
    data = request.json or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Title required"}), 400
    
    sess = get_session()
    try:
        current_user = get_current_user()
        user_id = current_user.get('id') if current_user else None
        
        # Check for existing title within user's recipes
        if current_user:
            existing = sess.query(Recipe).filter(Recipe.title == title, Recipe.user_id == current_user.get('id')).first()
        else:
            existing = sess.query(Recipe).filter(Recipe.title == title, Recipe.user_id.is_(None)).first()
        
        if existing:
            return jsonify({"error": "Title already exists"}), 400
        
        r = Recipe()
        r.user_id = user_id
        r.title = title
        r.category = data.get("category", "")
        r.tags = data.get("tags", "")
        r.servings = int(data.get("servings", 2))
        r.set_ingredients(data.get("ingredients", []))
        r.steps = data.get("steps", "")
        sess.add(r)
        sess.commit()
        return jsonify({"ok": True, "id": r.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        sess.close()

@app.route("/api/recipe/<int:rid>", methods=["PUT"])
def update_recipe(rid):
    data = request.json or {}
    sess = get_session()
    r = sess.query(Recipe).filter(Recipe.id == rid).first()
    if not r:
        return jsonify({"error": "not found"}), 404
    new_title = (data.get("title") or "").strip()
    if not new_title:
        return jsonify({"error": "Title required"}), 400
    existing = sess.query(Recipe).filter(Recipe.title == new_title).first()
    if existing and existing.id != r.id:
        return jsonify({"error": "Title already exists"}), 400
    r.title = new_title
    r.category = data.get("category", "")
    r.tags = data.get("tags", "")
    r.servings = int(data.get("servings", 2))
    r.set_ingredients(data.get("ingredients", []))
    r.steps = data.get("steps", "")
    sess.commit()
    return jsonify({"ok": True})

@app.route("/api/recipe/<int:rid>", methods=["DELETE"])
def delete_recipe(rid):
    sess = get_session()
    r = sess.query(Recipe).filter(Recipe.id == rid).first()
    if not r:
        return jsonify({"error": "not found"}), 404
    sess.delete(r)
    sess.commit()
    return jsonify({"ok": True})

@app.route("/api/plan", methods=["GET"])
@require_auth
def get_plan():
    sess = get_session()
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "Authentication required"}), 401
        user_id = current_user.get('id')
        plan = bootstrap_plan(sess, user_id)
        return jsonify(plan.data())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        sess.close()

@app.route("/api/plan", methods=["PUT"])
@require_auth
def save_plan():
    sess = get_session()
    try:
        current_user = get_current_user()
        if not current_user:
            return jsonify({"error": "Authentication required"}), 401
        user_id = current_user.get('id')
        plan = bootstrap_plan(sess, user_id)
        data = request.json or {}
        plan.set_data(data)
        sess.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        sess.close()

@app.route("/api/groceries", methods=["POST"])
def build_groceries():
    # body: { plan: {...} }
    sess = get_session()
    payload = request.json or {}
    plan = payload.get("plan", {})
    # id->recipe
    recipes = {r.id: r for r in sess.query(Recipe).all()}
    items = []
    for day, entries in plan.items():
        for entry in entries:
            rid = entry.get("recipe_id")
            mult = int(entry.get("multiplier", 1))
            r = recipes.get(rid)
            if not r:
                continue
            for ing in r.ingredients():
                qty = float(ing.get("qty", 0) or 0) * mult
                unit = ing.get("unit", "")
                name = ing.get("name", "")
                note = ing.get("note", "")
                items.append({"name": name, "qty": qty, "unit": unit, "note": note})
    # aggregate
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

@app.route("/api/import", methods=["POST"])
def import_recipes():
    sess = get_session()
    try:
        data = request.json or []
        count = 0
        for item in data:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            r = sess.query(Recipe).filter(Recipe.title == title).first()
            if not r:
                r = Recipe()
                sess.add(r)
            r.title = title
            r.category = item.get("category", "")
            r.tags = item.get("tags", "")
            r.servings = int(item.get("servings", 2))
            r.set_ingredients(item.get("ingredients", []))
            r.steps = item.get("steps", "")
            count += 1
        sess.commit()
        return jsonify({"ok": True, "count": count})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/export", methods=["GET"])
def export_recipes():
    sess = get_session()
    recipes = sess.query(Recipe).all()
    data = []
    for r in recipes:
        data.append({
            "title": r.title,
            "category": r.category,
            "tags": r.tags,
            "servings": r.servings,
            "ingredients": r.ingredients(),
            "steps": r.steps,
        })
    return jsonify(data)

if __name__ == "__main__":
    port = config.PORT
    debug = config.DEBUG
    app.run(host="0.0.0.0", port=port, debug=debug)



