from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# ===== DATABASE =====

DATABASE_URL = "sqlite:///./database.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ===== DATABASE MODELS =====

class EventDB(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    date = Column(String)
    time = Column(String)
    place = Column(String)
    description = Column(String)
    image_url = Column(String)


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    login = Column(String, unique=True)
    password = Column(String)

    calendar = relationship("CalendarDB", back_populates="user")


class CalendarDB(Base):
    __tablename__ = "calendar"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    event_id = Column(Integer, ForeignKey("events.id"))

    user = relationship("UserDB", back_populates="calendar")


Base.metadata.create_all(bind=engine)

# ===== FASTAPI =====

app = FastAPI(title="Sxodim Backend")

# ===== SCHEMAS =====

class Event(BaseModel):
    id: Optional[int]
    name: str
    date: str
    time: str
    place: str
    description: str
    image_url: str

    class Config:
        from_attributes = True


class User(BaseModel):
    id: int
    login: str

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    login: str
    password: str


class LoginRequest(RegisterRequest):
    pass


class CalendarItem(BaseModel):
    user_id: int
    event_id: int


class UserSettings(BaseModel):
    theme: Optional[str] = "light"
    notifications: Optional[bool] = True


# ===== DEPENDENCY =====

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== AUTH =====

@app.post("/api/register", response_model=User)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(UserDB).filter(UserDB.login == data.login).first():
        raise HTTPException(status_code=400, detail="User already exists")

    user = UserDB(login=data.login, password=data.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/login", response_model=User)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(
        UserDB.login == data.login,
        UserDB.password == data.password
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid login or password")

    return user

# ===== EVENTS CRUD =====

@app.get("/api/events", response_model=List[Event])
def get_events(db: Session = Depends(get_db)):
    return db.query(EventDB).all()


@app.post("/api/events", response_model=Event)
def create_event(event: Event, db: Session = Depends(get_db)):
    new_event = EventDB(**event.dict(exclude={"id"}))
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


@app.put("/api/events/{event_id}", response_model=Event)
def update_event(event_id: int, event: Event, db: Session = Depends(get_db)):
    db_event = db.query(EventDB).filter(EventDB.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")

    for key, value in event.dict(exclude={"id"}).items():
        setattr(db_event, key, value)

    db.commit()
    return db_event


@app.delete("/api/events/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(EventDB).filter(EventDB.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()
    return {"message": "Event deleted"}

# ===== CALENDAR =====

@app.post("/api/calendar")
def add_to_calendar(data: CalendarItem, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == data.user_id).first()
    event = db.query(EventDB).filter(EventDB.id == data.event_id).first()

    if not user or not event:
        raise HTTPException(status_code=404, detail="User or Event not found")

    item = CalendarDB(user_id=data.user_id, event_id=data.event_id)
    db.add(item)
    db.commit()
    return {"message": "Added to calendar"}


@app.get("/api/calendar/{user_id}", response_model=List[Event])
def get_calendar(user_id: int, db: Session = Depends(get_db)):
    items = db.query(CalendarDB).filter(CalendarDB.user_id == user_id).all()
    events = [
        db.query(EventDB).filter(EventDB.id == item.event_id).first()
        for item in items
    ]
    return events

# ===== USER SETTINGS (ЗАГЛУШКА) =====

@app.get("/api/users/{user_id}/settings", response_model=UserSettings)
def get_settings(user_id: int):
    return UserSettings()


@app.put("/api/users/{user_id}/settings", response_model=UserSettings)
def update_settings(user_id: int, settings: UserSettings):
    return settings
