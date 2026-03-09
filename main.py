from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, User, Bot, Message, Settings, TempRegister
from schemas import *
from auth import hash_password, verify_password, create_access_token, get_current_user
from bot_logic import get_bot_response
from nltk_tokenize import router as tokenize_router
import shutil
import os

app = FastAPI(title="Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth Endpoints
@app.post("/api/auth/register-step1")
def register_step1(data: RegisterStep1, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    temp = TempRegister(**data.model_dump())
    db.add(temp)
    db.commit()
    db.refresh(temp)
    return {"temp_register_id": temp.id}

@app.post("/api/auth/register-step2")
def register_step2(data: RegisterStep2, db: Session = Depends(get_db)):
    if data.password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    temp = db.query(TempRegister).filter(TempRegister.id == data.temp_register_id).first()
    if not temp:
        raise HTTPException(status_code=404, detail="Registration session not found")
    
    user = User(
        name=temp.name,
        email=temp.email,
        phone=temp.phone,
        birth=temp.birth,
        gender=temp.gender,
        password=hash_password(data.password)
    )
    db.add(user)
    settings = Settings(user=user)
    db.add(settings)
    db.delete(temp)
    db.commit()
    return {"message": "Successful Done"}

@app.post("/api/auth/login", response_model=Token)
def login(data: Login, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "email": user.email}
    }

@app.post("/api/auth/logout")
def logout():
    return {"message": "Logged out successfully"}

# Bot Endpoints
@app.get("/api/bots/types")
def get_bot_types():
    return [
        {"type": "Personal", "name": "Personal Bot"},
        {"type": "Educational", "name": "Educational Assistant Bot"},
        {"type": "Lover", "name": "Lover Bot"}
    ]

@app.post("/api/bots", response_model=BotResponse)
def create_bot(data: BotCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot_count = db.query(Bot).filter(Bot.user_id == current_user.id).count()
    if bot_count >= 2:
        raise HTTPException(status_code=400, detail="Maximum 2 bots allowed")
    
    bot = Bot(user_id=current_user.id, bot_type=data.bot_type, custom_name=data.custom_name)
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot

@app.get("/api/bots", response_model=List[BotResponse])
def get_user_bots(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Bot).filter(Bot.user_id == current_user.id).all()

@app.patch("/api/bots/{bot_id}", response_model=BotResponse)
def update_bot(bot_id: int, data: BotCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot.custom_name = data.custom_name
    db.commit()
    db.refresh(bot)
    return bot

@app.delete("/api/bots/{bot_id}")
def delete_bot(bot_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    db.delete(bot)
    db.commit()
    return {"message": "Bot deleted"}

# Chat Endpoints
@app.post("/api/chat/{bot_id}/message")
def send_message(bot_id: int, data: MessageSend, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    user_msg = Message(bot_id=bot_id, sender="user", content=data.message_text)
    db.add(user_msg)
    db.commit()
    
    # Pass user context to bot
    user_context = {
        "name": current_user.name,
        "gender": current_user.gender,
        "birth": current_user.birth
    }
    
    bot_reply = get_bot_response(bot.bot_type, data.message_text, data.user_language, user_context)
    bot_msg = Message(bot_id=bot_id, sender="bot", content=bot_reply)
    db.add(bot_msg)
    db.commit()
    db.refresh(bot_msg)
    
    return {"bot_reply": bot_reply, "message_id": bot_msg.id, "timestamp": bot_msg.timestamp}

@app.get("/api/chat/{bot_id}/history", response_model=List[MessageResponse])
def get_chat_history(bot_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    return db.query(Message).filter(Message.bot_id == bot_id).order_by(Message.timestamp).all()

@app.delete("/api/chat/{bot_id}/history")
def delete_chat_history(bot_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bot = db.query(Bot).filter(Bot.id == bot_id, Bot.user_id == current_user.id).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    db.query(Message).filter(Message.bot_id == bot_id).delete()
    db.commit()
    return {"message": "Chat history deleted"}

# Profile Endpoints
@app.get("/api/profile")
def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone": current_user.phone,
        "birth": current_user.birth,
        "gender": current_user.gender,
        "photo": current_user.photo
    }

@app.patch("/api/profile")
def update_profile(data: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.name:
        current_user.name = data.name
    if data.phone:
        current_user.phone = data.phone
    if data.birth:
        current_user.birth = data.birth
    if data.gender:
        current_user.gender = data.gender
    db.commit()
    return {"message": "Profile updated"}

@app.patch("/api/profile/password")
def update_password(data: PasswordUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.old_password, current_user.password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    current_user.password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated"}

@app.post("/api/profile/photo")
async def upload_photo(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{current_user.id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    current_user.photo = file_path
    db.commit()
    return {"photo_url": file_path}

# Settings Endpoints
@app.get("/api/settings")
def get_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = db.query(Settings).filter(Settings.user_id == current_user.id).first()
    if not settings:
        settings = Settings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return {"language": settings.language, "dark_mode": settings.dark_mode}

@app.patch("/api/settings")
def update_settings(data: SettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = db.query(Settings).filter(Settings.user_id == current_user.id).first()
    if data.language:
        settings.language = data.language
    if data.dark_mode is not None:
        settings.dark_mode = data.dark_mode
    db.commit()
    return {"message": "Settings updated"}

# Service Endpoints
@app.get("/api/service/faqs")
def get_faqs():
    return [
        {"question": "How do I change my bot?", "answer": "Go to Settings and select a new bot."},
        {"question": "Can I have more than 2 bots?", "answer": "No, maximum 2 bots per user."}
    ]

@app.get("/api/service/privacy")
def get_privacy():
    return {"content": "Your privacy is important to us. We do not share your data with third parties."}

@app.get("/api/service/premium")
def get_premium():
    return {"status": "free", "features": ["Unlimited messages", "2 bots", "5 languages"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
