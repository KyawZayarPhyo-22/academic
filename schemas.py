from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class RegisterStep1(BaseModel):
    name: str
    email: EmailStr
    phone: str
    birth: str
    gender: str

class RegisterStep2(BaseModel):
    temp_register_id: int
    password: str
    confirm_password: str

class Login(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class BotCreate(BaseModel):
    bot_type: str
    custom_name: str

class BotResponse(BaseModel):
    id: int
    bot_type: str
    custom_name: str
    created_at: datetime

class MessageSend(BaseModel):
    message_text: str
    user_language: str

class MessageResponse(BaseModel):
    id: int
    sender: str
    content: str
    timestamp: datetime

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    birth: Optional[str] = None
    gender: Optional[str] = None

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str

class SettingsUpdate(BaseModel):
    language: Optional[str] = None
    dark_mode: Optional[bool] = None
