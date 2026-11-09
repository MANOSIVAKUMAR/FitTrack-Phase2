from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, create_engine, or_
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./fittrack.db"
SECRET_KEY = "fittrack-development-secret-change-this"
ALGORITHM = "HS256"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()

app = FastAPI(title="FitTrack Fitness & Workout Management API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- DATABASE MODELS --------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    workout_name = Column(String(120), nullable=False)
    category = Column(String(30), nullable=False)
    duration = Column(Integer, nullable=False)
    calories_burned = Column(Float, nullable=False)
    workout_date = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Progress(Base):
    __tablename__ = "progress"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_workouts = Column(Integer, default=0)
    total_calories = Column(Float, default=0)
    date = Column(String(20), nullable=False)

class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_type = Column(String(40), nullable=False)
    target_value = Column(Float, nullable=False)
    current_value = Column(Float, default=0)
    deadline = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(120), nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Phase 2
class WorkoutPlan(Base):
    __tablename__ = "workout_plans"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(120), nullable=False)
    description = Column(String(500), default="")
    scheduled_date = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Exercise(Base):
    __tablename__ = "exercises"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    category = Column(String(30), nullable=False)
    description = Column(String(500), default="")
    duration = Column(Integer, nullable=False)

class Streak(Base):
    __tablename__ = "streaks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_workout_date = Column(String(20), nullable=True)

class Badge(Base):
    __tablename__ = "badges"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), unique=True, nullable=False)
    description = Column(String(500), nullable=False)
    icon = Column(String(20), default="🏆")

class UserBadge(Base):
    __tablename__ = "user_badges"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# -------------------- SCHEMAS --------------------
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

class WorkoutRequest(BaseModel):
    workout_name: str = Field(min_length=2, max_length=120)
    category: str
    duration: int = Field(gt=0, le=600)
    calories_burned: float = Field(ge=0, le=10000)
    workout_date: str

class GoalRequest(BaseModel):
    goal_type: str
    target_value: float = Field(gt=0)
    current_value: float = Field(ge=0)
    deadline: str

class WorkoutPlanRequest(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    scheduled_date: str

class ExerciseRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str
    description: str = Field(default="", max_length=500)
    duration: int = Field(gt=0, le=600)

class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime
    class Config:
        from_attributes = True

# -------------------- HELPERS --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_token(user: User) -> str:
    return jwt.encode({"sub": str(user.id), "username": user.username}, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    err = HTTPException(401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("sub")
        if not uid:
            raise err
    except (JWTError, ValueError):
        raise err
    user = db.get(User, int(uid))
    if not user:
        raise err
    return user

def valid_category(category: str):
    if category not in {"Cardio", "Strength", "Yoga"}:
        raise HTTPException(400, "Category must be Cardio, Strength, or Yoga")

def parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(400, "Date must use YYYY-MM-DD format")

def get_streak_data(user_id: int, db: Session):
    rows = db.query(Workout.workout_date).filter(Workout.user_id == user_id).all()
    days = sorted({parse_day(r[0]) for r in rows})
    if not days:
        return 0, 0, None
    longest = current = 1
    for i in range(1, len(days)):
        if days[i] == days[i - 1] + timedelta(days=1):
            current += 1
        else:
            current = 1
        longest = max(longest, current)
    today = date.today()
    if days[-1] == today:
        current_streak = 1
        for i in range(len(days) - 2, -1, -1):
            if days[i + 1] == days[i] + timedelta(days=1):
                current_streak += 1
            else:
                break
    elif days[-1] == today - timedelta(days=1):
        current_streak = 1
        for i in range(len(days) - 2, -1, -1):
            if days[i + 1] == days[i] + timedelta(days=1):
                current_streak += 1
            else:
                break
    else:
        current_streak = 0
    return current_streak, longest, days[-1].isoformat()

def sync_streak(user_id: int, db: Session):
    current, longest, last = get_streak_data(user_id, db)
    s = db.query(Streak).filter(Streak.user_id == user_id).first()
    if not s:
        s = Streak(user_id=user_id)
        db.add(s)
    s.current_streak, s.longest_streak, s.last_workout_date = current, longest, last
    db.commit()
    db.refresh(s)
    return s

def seed_badges(db: Session):
    defaults = [
        ("First Workout", "Complete your first workout", "🥇"),
        ("Workout Hero", "Complete 10 workouts", "💪"),
        ("Consistency Star", "Maintain a 7-day streak", "🔥"),
        ("Goal Crusher", "Reach 100% of a goal", "🎯"),
    ]
    for name, desc, icon in defaults:
        if not db.query(Badge).filter(Badge.name == name).first():
            db.add(Badge(name=name, description=desc, icon=icon))
    db.commit()

seed_db = SessionLocal()
seed_badges(seed_db)
seed_db.close()

# -------------------- PHASE 1 --------------------
@app.get("/")
def root():
    return {"message": "FitTrack API is running", "phase": "Phase 2"}

@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already exists")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(username=data.username, email=data.email, hashed_password=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    return user

@app.post("/auth/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token(user), "token_type": "bearer"}

@app.get("/auth/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user

@app.post("/workouts")
def add_workout(data: WorkoutRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    valid_category(data.category); parse_day(data.workout_date)
    workout = Workout(user_id=user.id, **data.model_dump())
    db.add(workout); db.commit(); db.refresh(workout)
    sync_streak(user.id, db); award_badges(user.id, db)
    return {"message": "Workout added", "id": workout.id}

@app.get("/workouts")
def get_workouts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Workout).filter(Workout.user_id == user.id).order_by(Workout.workout_date.desc()).all()

@app.put("/workouts/{workout_id}")
def edit_workout(workout_id: int, data: WorkoutRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workout = db.get(Workout, workout_id)
    if not workout or workout.user_id != user.id: raise HTTPException(404, "Workout not found")
    valid_category(data.category); parse_day(data.workout_date)
    for k, v in data.model_dump().items(): setattr(workout, k, v)
    db.commit(); sync_streak(user.id, db); award_badges(user.id, db)
    return {"message": "Workout updated"}

@app.delete("/workouts/{workout_id}")
def delete_workout(workout_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    workout = db.get(Workout, workout_id)
    if not workout or workout.user_id != user.id: raise HTTPException(404, "Workout not found")
    db.delete(workout); db.commit(); sync_streak(user.id, db)
    return {"message": "Workout deleted"}

@app.get("/progress/daily")
def daily_progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today().isoformat()
    ws = db.query(Workout).filter(Workout.user_id == user.id, Workout.workout_date == today).all()
    return {"date": today, "total_workouts": len(ws), "total_calories": sum(w.calories_burned for w in ws)}

@app.get("/progress/history")
def progress_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ws = db.query(Workout).filter(Workout.user_id == user.id).all(); grouped = {}
    for w in ws:
        grouped.setdefault(w.workout_date, {"total_workouts": 0, "total_calories": 0})
        grouped[w.workout_date]["total_workouts"] += 1
        grouped[w.workout_date]["total_calories"] += w.calories_burned
    return [{"date": k, **v} for k, v in sorted(grouped.items(), reverse=True)]

@app.post("/goals")
def create_goal(data: GoalRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.goal_type not in {"Weight Loss", "Muscle Gain", "Steps"}: raise HTTPException(400, "Invalid goal type")
    goal = Goal(user_id=user.id, **data.model_dump()); db.add(goal); db.commit(); db.refresh(goal)
    return {"message": "Goal created", "id": goal.id}

@app.get("/goals")
def get_goals(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.created_at.desc()).all()

@app.put("/goals/{goal_id}")
def update_goal(goal_id: int, data: GoalRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = db.get(Goal, goal_id)
    if not goal or goal.user_id != user.id: raise HTTPException(404, "Goal not found")
    if data.goal_type not in {"Weight Loss", "Muscle Gain", "Steps"}: raise HTTPException(400, "Invalid goal type")
    for k, v in data.model_dump().items(): setattr(goal, k, v)
    db.commit(); award_badges(user.id, db)
    return {"message": "Goal updated"}

@app.get("/goals/{goal_id}/progress")
def goal_progress(goal_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = db.get(Goal, goal_id)
    if not goal or goal.user_id != user.id: raise HTTPException(404, "Goal not found")
    pct = round(min(goal.current_value / goal.target_value * 100, 100), 2)
    return {"goal_id": goal.id, "goal_type": goal.goal_type, "target_value": goal.target_value, "current_value": goal.current_value, "progress_percent": pct, "deadline": goal.deadline}

@app.get("/reports/weekly")
def weekly_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start = date.today() - timedelta(days=6)
    ws = [w for w in db.query(Workout).filter(Workout.user_id == user.id).all() if parse_day(w.workout_date) >= start]
    return {"period": "weekly", "total_workouts": len(ws), "total_calories": sum(w.calories_burned for w in ws)}

@app.get("/reports/monthly")
def monthly_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    start = date.today() - timedelta(days=29)
    ws = [w for w in db.query(Workout).filter(Workout.user_id == user.id).all() if parse_day(w.workout_date) >= start]
    return {"period": "monthly", "total_workouts": len(ws), "total_calories": sum(w.calories_burned for w in ws)}

@app.get("/notifications", response_model=list[NotificationResponse])
def get_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).all()

@app.put("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id: raise HTTPException(404, "Notification not found")
    n.is_read = True; db.commit(); return {"message": "Notification marked as read"}

# -------------------- MODULE 7: WORKOUT PLANS --------------------
@app.post("/workout-plans")
def create_workout_plan(data: WorkoutPlanRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    parse_day(data.scheduled_date)
    plan = WorkoutPlan(user_id=user.id, **data.model_dump())
    db.add(plan); db.commit(); db.refresh(plan)
    return {"message": "Workout plan created", "id": plan.id}

@app.get("/workout-plans")
def get_workout_plans(upcoming_only: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id)
    if upcoming_only:
        query = query.filter(WorkoutPlan.scheduled_date >= date.today().isoformat())
    return query.order_by(WorkoutPlan.scheduled_date.asc()).all()

@app.put("/workout-plans/{plan_id}")
def update_workout_plan(plan_id: int, data: WorkoutPlanRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.get(WorkoutPlan, plan_id)
    if not plan or plan.user_id != user.id: raise HTTPException(404, "Workout plan not found")
    parse_day(data.scheduled_date)
    for k, v in data.model_dump().items(): setattr(plan, k, v)
    db.commit(); return {"message": "Workout plan updated"}

@app.delete("/workout-plans/{plan_id}")
def delete_workout_plan(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.get(WorkoutPlan, plan_id)
    if not plan or plan.user_id != user.id: raise HTTPException(404, "Workout plan not found")
    db.delete(plan); db.commit(); return {"message": "Workout plan deleted"}

# -------------------- MODULE 8: EXERCISE LIBRARY --------------------
@app.get("/exercises")
def list_exercises(search: Optional[str] = None, category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Exercise)
    if search:
        query = query.filter(or_(Exercise.name.ilike(f"%{search}%"), Exercise.description.ilike(f"%{search}%")))
    if category:
        valid_category(category); query = query.filter(Exercise.category == category)
    return query.order_by(Exercise.name.asc()).all()

@app.post("/exercises")
def add_exercise(data: ExerciseRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    valid_category(data.category)
    if db.query(Exercise).filter(Exercise.name.ilike(data.name)).first(): raise HTTPException(400, "Exercise already exists")
    exercise = Exercise(**data.model_dump()); db.add(exercise); db.commit(); db.refresh(exercise)
    return exercise

@app.post("/workouts/from-exercise/{exercise_id}")
def add_exercise_to_workout(exercise_id: int, workout_date: str = Query(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exercise = db.get(Exercise, exercise_id)
    if not exercise: raise HTTPException(404, "Exercise not found")
    parse_day(workout_date)
    workout = Workout(user_id=user.id, workout_name=exercise.name, category=exercise.category, duration=exercise.duration, calories_burned=float(exercise.duration * 5), workout_date=workout_date)
    db.add(workout); db.commit(); db.refresh(workout); sync_streak(user.id, db); award_badges(user.id, db)
    return {"message": "Exercise added to workouts", "id": workout.id}

# -------------------- MODULE 9: COMPARISON --------------------
@app.get("/comparison/weekly")
def weekly_comparison(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today(); current_start = today - timedelta(days=6); previous_start = today - timedelta(days=13)
    ws = db.query(Workout).filter(Workout.user_id == user.id).all()
    current = [w for w in ws if current_start <= parse_day(w.workout_date) <= today]
    previous = [w for w in ws if previous_start <= parse_day(w.workout_date) < current_start]
    return comparison_payload(current, previous, "current_week", "previous_week")

@app.get("/comparison/monthly")
def monthly_comparison(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today(); current_start = today - timedelta(days=29); previous_start = today - timedelta(days=59)
    ws = db.query(Workout).filter(Workout.user_id == user.id).all()
    current = [w for w in ws if current_start <= parse_day(w.workout_date) <= today]
    previous = [w for w in ws if previous_start <= parse_day(w.workout_date) < current_start]
    return comparison_payload(current, previous, "current_month", "previous_month")

def comparison_payload(current, previous, current_label, previous_label):
    cw, cc = len(current), sum(w.calories_burned for w in current)
    pw, pc = len(previous), sum(w.calories_burned for w in previous)
    return {
        "current": {"period": current_label, "workouts": cw, "calories": cc},
        "previous": {"period": previous_label, "workouts": pw, "calories": pc},
        "improvement": {"workouts": cw - pw, "calories": round(cc - pc, 2)},
    }

# -------------------- MODULE 10: STREAK --------------------
@app.get("/streak")
def get_streak(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = sync_streak(user.id, db)
    return {"id": s.id, "current_streak": s.current_streak, "longest_streak": s.longest_streak, "last_workout_date": s.last_workout_date}

# -------------------- MODULE 11: BADGES --------------------
def award_badges(user_id: int, db: Session):
    workout_count = db.query(Workout).filter(Workout.user_id == user_id).count()
    goals = db.query(Goal).filter(Goal.user_id == user_id).all()
    streak = db.query(Streak).filter(Streak.user_id == user_id).first()
    rules = []
    if workout_count >= 1: rules.append("First Workout")
    if workout_count >= 10: rules.append("Workout Hero")
    if streak and streak.longest_streak >= 7: rules.append("Consistency Star")
    if any(g.current_value >= g.target_value for g in goals): rules.append("Goal Crusher")
    for name in rules:
        badge = db.query(Badge).filter(Badge.name == name).first()
        if badge and not db.query(UserBadge).filter(UserBadge.user_id == user_id, UserBadge.badge_id == badge.id).first():
            db.add(UserBadge(user_id=user_id, badge_id=badge.id))
    db.commit()

@app.get("/badges")
def list_badges(db: Session = Depends(get_db)):
    return db.query(Badge).order_by(Badge.id.asc()).all()

@app.get("/badges/my")
def my_badges(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    award_badges(user.id, db)
    rows = db.query(UserBadge, Badge).join(Badge, UserBadge.badge_id == Badge.id).filter(UserBadge.user_id == user.id).order_by(UserBadge.earned_at.desc()).all()
    return [{"id": ub.id, "name": b.name, "description": b.description, "icon": b.icon, "earned_at": ub.earned_at} for ub, b in rows]

# -------------------- MODULE 12: PERSONALIZED DASHBOARD --------------------
@app.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today().isoformat()
    today_workouts = db.query(Workout).filter(Workout.user_id == user.id, Workout.workout_date == today).all()
    upcoming = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user.id, WorkoutPlan.scheduled_date >= today).order_by(WorkoutPlan.scheduled_date.asc()).limit(5).all()
    goals = db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.created_at.desc()).limit(5).all()
    streak = sync_streak(user.id, db)
    award_badges(user.id, db)
    badges = my_badges(user, db)
    return {
        "user": {"id": user.id, "username": user.username},
        "daily_summary": {"date": today, "workouts": len(today_workouts), "calories": sum(w.calories_burned for w in today_workouts)},
        "upcoming_workouts": [{"id": p.id, "title": p.title, "description": p.description, "scheduled_date": p.scheduled_date} for p in upcoming],
        "goals": [{"id": g.id, "goal_type": g.goal_type, "target_value": g.target_value, "current_value": g.current_value, "deadline": g.deadline, "progress_percent": round(min(g.current_value / g.target_value * 100, 100), 2)} for g in goals],
        "streak": {"current_streak": streak.current_streak, "longest_streak": streak.longest_streak, "last_workout_date": streak.last_workout_date},
        "badges": badges,
    }
