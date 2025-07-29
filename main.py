import logging as logs
import uvicorn

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import Body, FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

import app.schemas.calculation as calcs
from app.auth.dependencies import get_current_active_user
from app.database_client import DatabaseClient
from app.models.user import User
from app.models.calculation import Calculation
from app.schemas.user import AuthToken, UserRecord
from app.schemas.user_form import UserCreate, UserLoginForm

# ----------------------------------------
# Setup
# ----------------------------------------

logs.basicConfig(level=logs.INFO)
logger = logs.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Tables")
    client = DatabaseClient()
    client.model_base.metadata.create_all(bind=client.engine)
    logger.info("Initialization Successful")
    yield

app = FastAPI(
    title="Calculations API",
    description="API for managing calculations",
    version="1.0.0",
    lifespan=lifespan
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ----------------------------------------
# Page Endpoints
# ----------------------------------------
@app.get("/", response_class=HTMLResponse, tags=["web"])
def get_homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse, tags=["web"])
def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register", response_class=HTMLResponse, tags=["web"])
def get_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse, tags=["web"])
def get_dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ----------------------------------------
# Health Endpoint
# ----------------------------------------
@app.get("/health", tags=["health"])
def read_health():
    return {"status": "ok"}

# ----------------------------------------
# User Registration Endpoint
# ----------------------------------------
@app.post(
    "/auth/register",
    response_model=UserRecord,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"]
)
def register(
        user_create: UserCreate,
        db: Session = Depends(DatabaseClient().get_session)):
    user_data = user_create.dict() #.dict(exclude={"confirm_password"})
    try:
        user = User.register(db, user_data)
        db.commit()
        db.refresh(user)
        return user
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ----------------------------------------
# User Login Endpoints
# ----------------------------------------
@app.post("/auth/login", response_model=AuthToken, tags=["auth"])
def login_json(
        user_login: UserLoginForm,
        db: Session = Depends(DatabaseClient().get_session)):
    """Login with JSON data, ex. from a login screen"""
    auth_result = User.authenticate(db, user_login.username, user_login.password)
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    db.commit()
    return auth_result

@app.post("/auth/token", tags=["auth"])
def login_form(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(DatabaseClient().get_session)):
    """Login with form data, ex. from Swagger UI"""
    auth_result = User.authenticate(db, form_data.username, form_data.password)
    if not auth_result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": auth_result["access_token"],
        "token_type": "bearer"
    }

# ----------------------------------------
# Calculation Endpoints
# ----------------------------------------
# CREATE
@app.post(
    "/calculations",
    response_model=calcs.CalculationRecord,
    status_code=status.HTTP_201_CREATED,
    tags=['calculations'],
)
def create_calculation(
        calc_data: calcs.CalculationForm,
        current_user = Depends(get_current_active_user),
        db: Session = Depends(DatabaseClient().get_session)):
    """Creates and inserts a Calculation record"""
    try:
        new_calculation = Calculation.create(
            calc_type=calc_data.type,
            user_id=current_user.id,
            inputs=calc_data.inputs,
        )
        
        db.add(new_calculation)
        db.commit()
        db.refresh(new_calculation)
        return new_calculation
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# READ ALL
@app.get(
    "/calculations",
    response_model=List[calcs.CalculationRecord],
    tags=["calculations"],
)
def list_calculations(
        current_user = Depends(get_current_active_user),
        db: Session = Depends(DatabaseClient().get_session)):
    calculations = db.query(Calculation).filter(
        Calculation.user_id == current_user.id).all()
    return calculations

# READ ONE
@app.get(
    "/calculations/{calc_id}",
    response_model=calcs.CalculationRecord,
    tags=["calculations"]
)
def get_calculation(
        calc_id: str,
        current_user = Depends(get_current_active_user),
        db: Session = Depends(DatabaseClient().get_session)):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid calculation id format"
        )
    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user_id
    ).first()
    if not calculation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculation not found."
        )
    return calculation

# UPDATE
@app.put(
    "/calculations/{calc_id}",
    response_model=calcs.CalculationRecord,
    tags=["calculations"]
)
def update_calculation(
        calc_id: str,
        calculation_update: calcs.CalculationUpdate,
        current_user = Depends(get_current_active_user),
        db: Session = Depends(DatabaseClient().get_session)):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid calculation id format"
        )
    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculation not found"
        )
    if calculation_update.inputs:
        calculation.inputs = calculation_update.inputs
    calculation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(calculation)
    return calculation

# DELETE
@app.delete(
    "/calculations/{calc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["calculations"]
)
def delete_calculation(
        calc_id: str,
        current_user = Depends(get_current_active_user),
        db: Session = Depends(DatabaseClient().get_session)):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid calculation id format"
        )
    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculation not found"
        )
    db.delete(calculation)
    db.commit()

# ----------------------------------------
# Launch Script
# ----------------------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
