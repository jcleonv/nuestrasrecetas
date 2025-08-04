#!/usr/bin/env python3
"""
Development Seed Data Script
Creates sample recipes and data for local development testing
"""

import json
import uuid
from datetime import datetime, timedelta
import random

# Sample recipe data for development
DEV_RECIPES = [
    {
        "id": 1,
        "title": "Abuela's Secret Paella",
        "description": "Traditional Spanish paella passed down through generations",
        "created_by": "00000000-0000-0000-0000-000000000001",  # dev@test.com
        "created_at": (datetime.now() - timedelta(days=7)).isoformat(),
        "is_public": True,
        "recipe_data": {
            "ingredients": [
                {"name": "Rice", "amount": "2", "unit": "cups"},
                {"name": "Saffron", "amount": "1", "unit": "pinch"},
                {"name": "Chicken", "amount": "500", "unit": "g"},
                {"name": "Shrimp", "amount": "300", "unit": "g"},
                {"name": "Green beans", "amount": "200", "unit": "g"}
            ],
            "instructions": [
                "Heat olive oil in a large paella pan",
                "Add chicken and brown on all sides",
                "Add vegetables and sauté until tender",
                "Add rice and stir to coat with oil",
                "Add hot broth with saffron",
                "Simmer for 18-20 minutes without stirring",
                "Add seafood in final 5 minutes",
                "Let rest for 5 minutes before serving"
            ],
            "prep_time": 30,
            "cook_time": 45,
            "servings": 6
        }
    },
    {
        "id": 2,
        "title": "Mom's Chocolate Chip Cookies",
        "description": "The perfect chewy chocolate chip cookies with a secret ingredient",
        "created_by": "00000000-0000-0000-0000-000000000002",  # alice@test.com
        "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
        "is_public": True,
        "recipe_data": {
            "ingredients": [
                {"name": "Flour", "amount": "2.25", "unit": "cups"},
                {"name": "Butter", "amount": "1", "unit": "cup"},
                {"name": "Brown sugar", "amount": "0.75", "unit": "cup"},
                {"name": "White sugar", "amount": "0.75", "unit": "cup"},
                {"name": "Eggs", "amount": "2", "unit": "pc"},
                {"name": "Vanilla", "amount": "2", "unit": "tsp"},
                {"name": "Chocolate chips", "amount": "2", "unit": "cups"}
            ],
            "instructions": [
                "Preheat oven to 375°F (190°C)",
                "Cream butter and sugars until light and fluffy",
                "Beat in eggs one at a time, then vanilla",
                "Gradually blend in flour",
                "Stir in chocolate chips",
                "Drop rounded tablespoons onto ungreased cookie sheets",
                "Bake 9-11 minutes until golden brown",
                "Cool on baking sheet for 2 minutes before removing"
            ],
            "prep_time": 15,
            "cook_time": 11,
            "servings": 48
        }
    },
    {
        "id": 3,
        "title": "Bob's Famous BBQ Ribs",
        "description": "Fall-off-the-bone ribs with homemade dry rub and sauce",
        "created_by": "00000000-0000-0000-0000-000000000003",  # bob@test.com
        "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
        "is_public": True,
        "recipe_data": {
            "ingredients": [
                {"name": "Baby back ribs", "amount": "2", "unit": "racks"},
                {"name": "Brown sugar", "amount": "0.5", "unit": "cup"},
                {"name": "Paprika", "amount": "2", "unit": "tbsp"},
                {"name": "Garlic powder", "amount": "1", "unit": "tbsp"},
                {"name": "Onion powder", "amount": "1", "unit": "tbsp"},
                {"name": "Chili powder", "amount": "1", "unit": "tbsp"},
                {"name": "Salt", "amount": "1", "unit": "tbsp"},
                {"name": "Black pepper", "amount": "1", "unit": "tsp"}
            ],
            "instructions": [
                "Remove membrane from back of ribs",
                "Mix all dry rub ingredients together",
                "Coat ribs generously with dry rub",
                "Wrap in plastic and refrigerate overnight",
                "Preheat oven to 275°F (135°C)",
                "Bake ribs wrapped in foil for 2.5 hours",
                "Remove foil and bake 30 minutes more",
                "Brush with BBQ sauce and broil 2-3 minutes"
            ],
            "prep_time": 20,
            "cook_time": 180,
            "servings": 4
        }
    }
]

# Sample user posts for activity feed
DEV_POSTS = [
    {
        "id": str(uuid.uuid4()),
        "user_id": "00000000-0000-0000-0000-000000000001",
        "content": "Just shared my family's secret paella recipe! Been perfecting this for years 🥘",
        "post_type": "recipe_share",
        "recipe_id": 1,
        "is_public": True,
        "created_at": (datetime.now() - timedelta(days=7)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "user_id": "00000000-0000-0000-0000-000000000002",
        "content": "Cookies are in the oven! Can't wait to share the results 🍪",
        "post_type": "recipe_share",
        "recipe_id": 2,
        "is_public": True,
        "created_at": (datetime.now() - timedelta(days=3)).isoformat()
    },
    {
        "id": str(uuid.uuid4()),
        "user_id": "00000000-0000-0000-0000-000000000003",
        "content": "Weekend BBQ prep starts now! These ribs are going to be amazing 🔥",
        "post_type": "recipe_share",
        "recipe_id": 3,
        "is_public": True,
        "created_at": (datetime.now() - timedelta(days=1)).isoformat()
    }
]

def create_seed_data():
    """Create development seed data"""
    print("🌱 Creating development seed data...")
    
    # Create recipes JSON file
    with open('dev_recipes.json', 'w') as f:
        json.dump(DEV_RECIPES, f, indent=2)
    print(f"✅ Created {len(DEV_RECIPES)} sample recipes in dev_recipes.json")
    
    # Create posts JSON file  
    with open('dev_posts.json', 'w') as f:
        json.dump(DEV_POSTS, f, indent=2)
    print(f"✅ Created {len(DEV_POSTS)} sample posts in dev_posts.json")
    
    print("\n📊 Development Data Summary:")
    print(f"- Users: 3 (dev@test.com, alice@test.com, bob@test.com)")
    print(f"- Recipes: {len(DEV_RECIPES)}")
    print(f"- Posts: {len(DEV_POSTS)}")
    print("\n🔑 Development Login Credentials:")
    print("- dev@test.com / dev123")
    print("- alice@test.com / alice123") 
    print("- bob@test.com / bob123")
    print("\n🚀 Start the dev server with: docker compose -f docker-compose.dev.yml up --build")

if __name__ == "__main__":
    create_seed_data()