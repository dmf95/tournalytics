import os
import json
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, auth, initialize_app
from dotenv import load_dotenv
import re
import requests
import random
from utils.general_utils import generate_unique_id 
import streamlit as st

#--------
# PROD
#--------
# Access credentials and Firebase details from Streamlit secrets
firebase_credentials = st.secrets["GOOGLE_APPLICATION_CREDENTIALS"]
# Access Firebase secrets
project_id = st.secrets["FIREBASE"]["project_id"]
database_url = st.secrets["FIREBASE"]["database_url"]
api_key = st.secrets["FIREBASE"]["api_key"]

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_credentials)
    initialize_app(cred, {"projectId": firebase_credentials["project_id"]})

# Firestore client
db = firestore.client()

def create_user_metadata(email, password, username, role="user", league_id=None):
    """
    Create a new user in Firebase Authentication and store additional metadata in Firestore.
    Ensures no duplicate UIDs are stored in Firestore.
    """
    try:
        # Check if the email is already registered
        existing_user = None
        try:
            existing_user = auth.get_user_by_email(email)
        except Exception:
            # No user found, this is fine
            pass

        if existing_user:
            print(f"User with email {email} already exists. UID: {existing_user.uid}")
            return False

        # Create user in Firebase Authentication
        user_record = auth.create_user(email=email, password=password, display_name=username)

        # Check for duplicate UID in Firestore
        if db.collection("users").document(user_record.uid).get().exists:
            print(f"Duplicate UID detected for {user_record.uid}. Rolling back user creation.")
            auth.delete_user(user_record.uid)  # Rollback user creation in Firebase Auth
            return False

        # Store additional metadata in Firestore
        user_doc = {
            "uid": user_record.uid,  # Link Firestore metadata to Firebase Auth UID
            "username": username,
            "email": email,
            "role": role,
            "league_id": league_id,
            "created_at": firestore.SERVER_TIMESTAMP,
        }
        db.collection("users").document(user_record.uid).set(user_doc)

        print(f"User {username} created successfully.")
        return True
    except Exception as e:
        print(f"Error creating user metadata: {e}")
        return False



def create_league_metadata(league_name, league_type="private", created_by=None):
    """
    Create a new league and store metadata in Firestore.

    Parameters:
        league_name (str): The name of the league.
        league_type (str): The type of the league ('Private' or 'Public'). Defaults to 'Private'.
        created_by (str, optional): The UID of the user who created the league.

    Returns:
        dict: A dictionary containing the result status and message.
              Example: {"success": True, "message": "League created successfully.", "league_id": "123456789"}
    """
    try:
        # Validate inputs
        if not league_name or not isinstance(league_name, str):
            raise ValueError("Invalid league_name. It must be a non-empty string.")
        
        if league_type.lower() not in ["private", "public"]:
            raise ValueError("Invalid league_type. Allowed values are 'private' or 'public'.")

        # Generate a unique league ID
        existing_league_ids = {doc.id for doc in db.collection("leagues").stream()}  # Use set for efficiency
        league_id = generate_unique_id(existing_league_ids, id_length=9, id_type="numeric")

        # League metadata
        league_doc = {
            "league_id": league_id,
            "league_name": league_name.strip(),
            "league_type": league_type.lower(),
            "created_by": created_by,  # UID of the user who created the league
            "created_at": firestore.SERVER_TIMESTAMP,
        }

        # Store league metadata in Firestore
        db.collection("leagues").document(league_id).set(league_doc)

        print(f"League '{league_name}' created successfully with ID: {league_id}")
        return {
            "success": True,
            "message": f"League '{league_name}' created successfully.",
            "league_id": league_id,
        }
    except ValueError as ve:
        # Handle validation errors
        print(f"Validation error: {ve}")
        return {
            "success": False,
            "message": str(ve),
        }
    except Exception as e:
        # Handle general exceptions
        print(f"Error creating league metadata: {e}")
        return {
            "success": False,
            "message": f"Error creating league metadata: {e}",
        }


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
    Ensures the user is created in Firebase Auth and Firestore without duplicates.

    Args:
        email (str): User's email address.
        password (str): User's chosen password.
        username (str): User's chosen username.
        role (str): User's role (default: "user").
        league_id (str or None): Associated league ID (default: None).

    Returns:
        tuple: (bool, str) indicating success and a message.
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
            "league_id": league_id if league_id else [],  # Initialize with empty list if None
            "created_at": datetime.now(),
        }
        db.collection("users").document(user.uid).set(user_metadata)

        return True, "User registered successfully."
    except Exception as e:
        print(f"Error registering user: {e}")
        return False, f"Error registering user: {e}"




def authenticate_user(identifier, FIREBASE_API_KEY, password=None):
    """
    Authenticate a user by either email or username.

    Password verification is handled using Firebase's REST API.
    """
    try:
        # Fetch Firebase API key
        if not FIREBASE_API_KEY:
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
