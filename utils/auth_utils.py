import hashlib
from firebase_admin import auth, firestore
import firebase_admin
from firebase_admin.credentials import Certificate

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = Certificate("path/to/serviceAccount.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def authenticate_user(email, password):
    """Authenticate a user using email and password."""
    try:
        user = auth.get_user_by_email(email)
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user_data = db.collection("users").document(user.uid).get().to_dict()
        if user_data and user_data["password"] == hashed_password:
            return {"email": email, "uid": user.uid, "role": user_data.get("role", "user")}
    except Exception:
        return None

def create_user(email, password, league_id=None):
    """Create a new user account."""
    try:
        user = auth.create_user(email=email)
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        db.collection("users").document(user.uid).set({
            "email": email,
            "password": hashed_password,
            "role": "admin" if league_id else "user",
            "league_id": league_id,
        })
        return True
    except Exception:
        return False
