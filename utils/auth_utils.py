import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
import re
import requests

# Load environment variables
load_dotenv()

google_credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
project_id = os.getenv("FIRESTORE_PROJECT_ID")

# Initialize Firebase Admin SDK if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(google_credentials_path)
    firebase_admin.initialize_app(cred, {"projectId": project_id})

# Firestore client
db = firestore.client()


def create_user_metadata(uid, email, username, role="user", league_id=None):
    """
    Store user metadata in Firestore under `users/{uid}` after Firebase Authentication signup.
    """
    try:
        # Prepare user metadata
        user_metadata = {
            "username": username,
            "email": email,
            "role": role,
            "league_id": league_id,
            "created_at": datetime.now(),
        }
        # Store metadata in Firestore using `uid` as the document ID
        db.collection("users").document(uid).set(user_metadata)
        return True
    except Exception as e:
        print(f"Error creating user metadata: {e}")
        return False



def is_username_or_email_taken(username, email):
    """
    Check if the given username or email is already taken in Firestore.
    """
    try:
        # Check for existing username
        username_ref = db.collection("users").document(username).get()
        if username_ref.exists:
            return True, "Username already exists."

        # Check for existing email
        email_query = db.collection("users").where("email", "==", email).stream()
        if any(email_query):
            return True, "Email already exists."

        return False, None
    except Exception as e:
        print(f"Error checking uniqueness: {e}")
        return True, "An error occurred while checking uniqueness."


def register_user(email, password, username, role="user", league_id=None):
    """
    Register a new user in Firebase Authentication and store metadata in Firestore.
    """
    # Check if username or email is already taken
    is_taken, message = is_username_or_email_taken(username, email)
    if is_taken:
        print(message)
        return False, message

    try:
        # Create user in Firebase Authentication
        user = auth.create_user(email=email, password=password, display_name=username)
        print(f"Firebase Auth user created: {user.uid}")

        # Set custom claims (roles and league association)
        custom_claims = {"role": role}
        if league_id:
            custom_claims["league_id"] = league_id
        auth.set_custom_user_claims(user.uid, custom_claims)

        # Store metadata in Firestore
        user_metadata = {
            "uid": user.uid,
            "email": email,
            "username": username,
            "role": role,
            "league_id": league_id,
            "created_at": datetime.now(),
        }
        db.collection("users").document(user.uid).set(user_metadata)

        return True, "User registered successfully."
    except Exception as e:
        print(f"Error registering user: {e}")
        return False, f"Error registering user: {e}"



def authenticate_user(identifier, password=None):
    """
    Authenticate a user by either email or username.

    Password verification is handled using Firebase's REST API.
    """
    try:
        # Fetch Firebase API key
        api_key = os.getenv("FIREBASE_API_KEY")
        if not api_key:
            raise ValueError("FIREBASE_API_KEY is not set in the environment variables.")

        # Determine if the identifier is an email
        is_email = re.match(r"[^@]+@[^@]+\.[^@]+", identifier)

        if is_email:
            # Authenticate by email
            firebase_user = auth.get_user_by_email(identifier)
            uid = firebase_user.uid
        else:
            # Authenticate by username
            user_ref = db.collection("users").where("username", "==", identifier).limit(1).get()
            if not user_ref:
                print("Username not found in Firestore.")
                return None
            user_data = user_ref[0].to_dict()
            uid = user_ref[0].id  # Firestore document ID corresponds to UID
            identifier = user_data.get("email")  # Retrieve the associated email for Firebase Authentication

            # Fetch Firebase user by email
            try:
                firebase_user = auth.get_user_by_email(identifier)
            except firebase_admin.auth.UserNotFoundError:
                print("Email associated with username not found in Firebase Authentication.")
                return None

        # Verify the password using Firebase REST API
        if password:
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
            response = requests.post(
                url,
                json={"email": identifier, "password": password, "returnSecureToken": True},
            )
            if response.status_code != 200:
                error_message = response.json().get("error", {}).get("message", "Unknown error.")
                print(f"Password verification failed: {error_message}")
                return None

        # Fetch user metadata from Firestore
        user_metadata = db.collection("users").document(uid).get().to_dict()
        if not user_metadata:
            print("User metadata not found in Firestore.")
            return None

        # Return user metadata
        return {
            "username": user_metadata.get("username"),
            "role": user_metadata.get("role"),
            "email": user_metadata.get("email"),
            "league_id": user_metadata.get("league_id"),
        }
    except Exception as e:
        print(f"Error authenticating user: {e}")
        return None


def get_user_metadata(username):
    """
    Retrieve user metadata from Firestore.
    """
    try:
        user_ref = db.collection("users").document(username).get()
        if user_ref.exists():
            return user_ref.to_dict()
        else:
            print(f"No metadata found for user '{username}'.")
            return None
    except Exception as e:
        print(f"Error fetching user metadata: {e}")
        return None


def get_tournaments_for_admin(username):
    """
    Retrieve tournaments for a given admin.
    """
    try:
        user_metadata = get_user_metadata(username)
        if not user_metadata:
            print("User not found.")
            return None

        if user_metadata.get("role") not in ["admin", "super_admin"]:
            print("User does not have admin privileges.")
            return None

        league_id = user_metadata.get("league_id")
        tournaments = db.collection("tournaments").where("league_id", "==", league_id).stream()
        return [tournament.to_dict() for tournament in tournaments]
    except Exception as e:
        print(f"Error retrieving tournaments: {e}")
        return None


def get_leagues_for_admin(username):
    """
    Retrieve leagues for a given admin.
    """
    try:
        user_metadata = get_user_metadata(username)
        if not user_metadata:
            print("User not found.")
            return None

        if user_metadata.get("role") not in ["admin", "super_admin"]:
            print("User does not have admin privileges.")
            return None

        leagues = db.collection("leagues").stream()
        return [league.to_dict() for league in leagues]
    except Exception as e:
        print(f"Error retrieving leagues: {e}")
        return None
