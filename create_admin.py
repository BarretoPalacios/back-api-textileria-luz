from sqlalchemy.orm import Session
from models import User, Base
from auth import get_password_hash
from database import engine, SessionLocal

# Crear la base de datos si no existe
Base.metadata.create_all(bind=engine)

# Crear sesión
db: Session = SessionLocal()

def create_admin():
    # Verificar si ya existe un usuario administrador
    existing_admin = db.query(User).filter(User.username == "admin").first()
    
    if existing_admin:
        print("Admin user already exists.")
        return
    
    # Crear un usuario administrador manualmente si no existe
    hashed_password = get_password_hash("123")  # Cambia "123" por la contraseña deseada
    admin_user = User(
        username="admin",
        email="admin@example.com",
        hashed_password=hashed_password,
        role="admin"  # El rol para este usuario
    )

    # Guardar en la base de datos
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    print(f"Admin user created: {admin_user.username}")
