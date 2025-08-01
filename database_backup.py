import json
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Table
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.sql import func
from config import Config

Base = declarative_base()
config = Config()

# Association tables for many-to-many relationships
user_follows = Table('user_follows', Base.metadata,
    Column('follower_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('followed_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
)

recipe_likes = Table('recipe_likes', Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True),
    Column('recipe_id', Integer, ForeignKey('recipes.id'), primary_key=True)
)

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True)  # Use Supabase UUID
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    password_hash = Column(String, default="")  # Not required with Supabase auth
    bio = Column(Text, default="")
    avatar_url = Column(String, default="")
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    last_active = Column(DateTime, default=func.now())
    
    # Relationships
    recipes = relationship("Recipe", back_populates="user", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    
    # Social relationships
    following = relationship(
        "User", secondary=user_follows,
        primaryjoin=id == user_follows.c.follower_id,
        secondaryjoin=id == user_follows.c.followed_id,
        backref="followers"
    )
    
    liked_recipes = relationship(
        "Recipe", secondary=recipe_likes,
        back_populates="liked_by"
    )
    
    def to_dict(self, include_private=False):
        data = {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "follower_count": len(self.followers),
            "following_count": len(self.following),
            "recipe_count": len([r for r in self.recipes if r.is_public or include_private])
        }
        if include_private:
            data["email"] = self.email
            data["last_active"] = self.last_active.isoformat() if self.last_active else None
        return data

class Recipe(Base):
    __tablename__ = "recipes"
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Allow null for guest mode
    title = Column(String, nullable=False)
    description = Column(Text, default="")
    category = Column(String, default="")
    tags = Column(String, default="")
    servings = Column(Integer, default=2)
    prep_time = Column(Integer, default=0)  # minutes
    cook_time = Column(Integer, default=0)  # minutes
    difficulty = Column(String, default="Easy")  # Easy, Medium, Hard
    steps = Column(Text, default="")
    ingredients_json = Column(Text, default="[]")
    image_url = Column(String, default="")
    is_public = Column(Boolean, default=True)
    rating_avg = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="recipes")
    comments = relationship("Comment", back_populates="recipe", cascade="all, delete-orphan")
    liked_by = relationship("User", secondary=recipe_likes, back_populates="liked_recipes")

    def ingredients(self):
        try:
            return json.loads(self.ingredients_json)
        except Exception:
            return []

    def set_ingredients(self, ing_list):
        self.ingredients_json = json.dumps(ing_list, ensure_ascii=False)

    def to_dict(self, include_user=True):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "category": self.category or "",
            "tags": self.tags or "",
            "servings": self.servings or 2,
            "prep_time": self.prep_time or 0,
            "cook_time": self.cook_time or 0,
            "difficulty": self.difficulty or "Easy",
            "steps": self.steps or "",
            "ingredients": self.ingredients(),
            "image_url": self.image_url or "",
            "is_public": self.is_public,
            "rating_avg": self.rating_avg or 0.0,
            "rating_count": self.rating_count or 0,
            "like_count": len(self.liked_by),
            "comment_count": len(self.comments),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_user and self.user:
            data["user"] = {
                "id": self.user.id,
                "username": self.user.username,
                "name": self.user.name,
                "avatar_url": self.user.avatar_url
            }
        return data

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="comments")
    recipe = relationship("Recipe", back_populates="comments")
    
    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user": {
                "id": self.user.id,
                "username": self.user.username,
                "name": self.user.name,
                "avatar_url": self.user.avatar_url
            } if self.user else None
        }

class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # Not nullable in Supabase
    name = Column(String, default="Week Plan")
    plan_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="plans")
    
    def data(self):
        try:
            return json.loads(self.plan_json)
        except Exception:
            return {}
    
    def set_data(self, d):
        self.plan_json = json.dumps(d, ensure_ascii=False)

# Database connection
def get_database_url():
    # Always use DATABASE_URL from environment
    # This allows users to configure Supabase connection string manually
    return config.DATABASE_URL

def get_session(db_url: Optional[str] = None):
    if db_url is None:
        db_url = get_database_url()
    
    engine = create_engine(db_url, echo=config.DEBUG, future=True)
    
    # Create tables if they don't exist
    Base.metadata.create_all(engine)
    
    return sessionmaker(bind=engine)()

def init_db():
    """Initialize database with tables"""
    engine = create_engine(get_database_url(), echo=config.DEBUG, future=True)
    Base.metadata.create_all(engine)
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()