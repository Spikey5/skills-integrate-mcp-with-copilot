"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import re
import secrets
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

ROLES = {
    "student": "Student",
    "organizer": "Club Organizer",
    "faculty": "Faculty",
    "administrator": "Administrator",
}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
users = {}
sessions = {}
bearer_scheme = HTTPBearer(auto_error=False)


class AuthRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(AuthRequest):
    role: str


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 120_000
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    salt, expected_digest = stored_hash.split("$", 1)
    actual_digest = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(actual_digest, expected_digest)


def validate_email(email: str) -> str:
    normalized_email = email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized_email):
        raise HTTPException(status_code=400, detail="Enter a valid email address")
    return normalized_email


def user_response(email: str) -> dict:
    role = users[email]["role"]
    return {"email": email, "role": role, "role_label": ROLES[role]}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None or credentials.credentials not in sessions:
        raise HTTPException(status_code=401, detail="Please sign in to continue")
    email = sessions[credentials.credentials]
    return {"email": email, **users[email]}


def require_roles(*allowed_roles: str):
    def role_dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="This action is not available for your role")
        return user

    return role_dependency

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/register")
def register(request: RegisterRequest):
    email = validate_email(request.email)
    role = request.role.strip().lower()
    if role not in ROLES:
        raise HTTPException(status_code=400, detail="Select a valid role")
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if email in users:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    users[email] = {"password_hash": hash_password(request.password), "role": role}
    token = secrets.token_urlsafe(32)
    sessions[token] = email
    return {"token": token, "user": user_response(email)}


@app.post("/auth/login")
def login(request: AuthRequest):
    email = validate_email(request.email)
    user = users.get(email)
    if user is None or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")

    token = secrets.token_urlsafe(32)
    sessions[token] = email
    return {"token": token, "user": user_response(email)}


@app.get("/auth/me")
def get_me(user: dict = Depends(get_current_user)):
    return user_response(user["email"])


@app.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    if credentials is not None:
        sessions.pop(credentials.credentials, None)
    return {"message": "Signed out successfully"}


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, user: dict = Depends(require_roles("student"))):
    """Sign up a student for an activity"""
    email = user["email"]
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, user: dict = Depends(get_current_user)):
    """Unregister a student from an activity"""
    email = user["email"]
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
