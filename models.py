from extensions import db
from flask_login import UserMixin
from datetime import datetime
import numpy as np
from sqlalchemy import LargeBinary

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    surname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    customer_code = db.Column(db.String(50), unique=True, nullable=False)
    profile_picture = db.Column(db.String(120), nullable=True)
    face_encoding = db.Column(LargeBinary, nullable=True)  # New field for facial recognition
    selected_gift_id = db.Column(db.Integer, db.ForeignKey('gifts.id'))
    bonus_points = db.Column(db.Integer, default=0)
    
    # ... (keep all your existing methods)
    
    def set_face_encoding(self, encoding):
        """Store face encoding as binary"""
        self.face_encoding = encoding.tobytes() if encoding is not None else None
    
    def get_face_encoding(self):
        """Retrieve face encoding from binary"""
        return np.frombuffer(self.face_encoding, dtype=np.float64) if self.face_encoding else None
