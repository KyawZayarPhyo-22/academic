from database import SessionLocal, User
from auth import hash_password

db = SessionLocal()

# Check existing users
users = db.query(User).all()
print(f"Total users: {len(users)}")
for user in users:
    print(f"ID: {user.id}, Email: {user.email}, Name: {user.name}")

# Create test user if none exist
if len(users) == 0:
    test_user = User(
        name="Test User",
        email="test@test.com",
        phone="1234567890",
        birth="2000-01-01",
        gender="Male",
        password=hash_password("test1234")
    )
    db.add(test_user)
    db.commit()
    print("\nCreated test user:")
    print("Email: test@test.com")
    print("Password: test1234")

db.close()
