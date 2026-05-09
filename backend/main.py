import json
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import create_engine, Column, Integer, String, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from geoalchemy2 import Geometry, WKTElement
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt


DATABASE_URL = "postgresql://postgres:12345@localhost:5432/sig_123140143"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


SECRET_KEY = "itera_super_secret_key" 
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Facility(Base):
    __tablename__ = "public_facilities"
    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String)
    geom = Column(Geometry('POINT', srid=4326))

Base.metadata.create_all(bind=engine)


class UserCreate(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class FacilityCreate(BaseModel):
    nama: str
    lat: float
    lon: float


def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None: raise HTTPException(status_code=401)
    except JWTError: raise HTTPException(status_code=401)
    user = db.query(User).filter(User.username == username).first()
    if user is None: raise HTTPException(status_code=401)
    return user


app = FastAPI(title="WebGIS Fullstack ITERA")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user: raise HTTPException(status_code=400, detail="User already exists")
    new_user = User(username=user.username, hashed_password=pwd_context.hash(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid login credentials")
    return {"access_token": create_access_token({"sub": user.username}), "token_type": "bearer"}


@app.get("/facilities/geojson")
def get_geojson(db: Session = Depends(get_db)):
    results = db.query(Facility.id, Facility.nama, func.ST_AsGeoJSON(Facility.geom)).all()
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": r[0],
                "properties": {"id": r[0], "nama": r[1]},
                "geometry": json.loads(r[2])
            } for r in results
        ]
    }

@app.post("/facilities")
def create_facility(item: FacilityCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    point = f'POINT({item.lon} {item.lat})'
    new_f = Facility(nama=item.nama, geom=WKTElement(point, srid=4326))
    db.add(new_f)
    db.commit()
    return {"message": "Data added successfully"}

@app.put("/facilities/{id}")
def update_facility(id: int, item: FacilityCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_f = db.query(Facility).filter(Facility.id == id).first()
    if not db_f: raise HTTPException(status_code=404)
    db_f.nama = item.nama
    db_f.geom = WKTElement(f'POINT({item.lon} {item.lat})', srid=4326)
    db.commit()
    return {"message": "Data updated"}

@app.delete("/facilities/{id}")
def delete_facility(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_f = db.query(Facility).filter(Facility.id == id).first()
    if not db_f: raise HTTPException(status_code=404)
    db.delete(db_f)
    db.commit()
    return {"message": "Data deleted"}

@app.get("/detection/geojson")
def get_detection_geojson():
    file_path = "hasil_deteksi.json"
    if not os.path.exists(file_path):
        return {"type": "FeatureCollection", "features": []}
    
    with open(file_path, "r") as f:
        return json.load(f)