from fastapi import FastAPI, Depends, HTTPException, status,Form
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from auth import verify_password, get_password_hash, create_access_token, oauth2_scheme, verify_token
from models import User, Product, Base
from database import SessionLocal, engine
from pydantic import BaseModel
from typing import List,Optional
from datetime import timedelta
import shutil
import os
from fastapi import File, UploadFile
from fastapi.staticfiles import StaticFiles
from create_admin import create_admin
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

Base.metadata.create_all(bind=engine)

origins = [
    "http://localhost:5173",
    "*",# Permitir acceso desde cualquier dominio (usarlo con precaución)
]

# Añadir el middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Permitir estos orígenes
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],   # Permitir todos los encabezados
)

UPLOAD_FOLDER = "./uploads/"
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Crear la carpeta de imágenes si no existe
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# Esquemas de Pydantic
class ProductUpdate(BaseModel):
    name: str
    description: str
    price: float
    sizes: str  # 'S,M,L' formato
    colors: str  
    category : str
    stock : int

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    sizes: str  # 'S,M,L' formato
    colors: str  # 'red,blue,green'
    category :str
    stock : int
    image_url: str  # URL de la imagen

class ProductResponse(ProductCreate):
    id: int


class UserCreate(BaseModel):
    username: str
    email: str
    password: str

# Dependencia para obtener la sesión
def get_db():
    db = SessionLocal()
    try:
        yield db
        
    finally:
        db.close()

@app.get("/userme", tags=["usuarios"])
async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Verifica el token y obtiene el nombre de usuario
    username = verify_token(token)  
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found"
        )

    # Devuelve información relevante del usuario (como su rol y correo)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }

@app.post("/token",tags=["Login"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=30))
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/products/", response_model=ProductResponse,tags=["productos"])
async def create_product(
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    sizes: str = Form(...),
    colors: str = Form(...),
    category : str = Form(...),
    stock:int = Form(...),
    image: UploadFile = File(...),  # Recibir el archivo de imagen
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    username = verify_token(token)
    user = db.query(User).filter(User.username == username).first()
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    # Guardar la imagen en el servidor
    file_location = f"{UPLOAD_FOLDER}{image.filename}"
    with open(file_location, "wb") as file:
        shutil.copyfileobj(image.file, file)

    db_product = Product(
        name=name,
        description=description,
        price=price,
        sizes=sizes,
        colors=colors,
        category=category,
        stock=stock,
        image_url=file_location  # Guardar la ruta de la imagen
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

# Obtener lista de productos
@app.get("/products/", tags=["productos"])
async def read_products(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    products = db.query(Product).offset(skip).limit(limit).all()
 
    return {"count":len(products),"data":products}

@app.get("/products/{id}", response_model=ProductResponse,tags=["productos"])
async def product_id(id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    return product

@app.get("/search/",response_model=List[ProductResponse],tags=["filtros"])
async def search_products(skip: int = 0, limit: int = 10,
                          name: Optional[str] = None,
                          description: Optional[str] = None,
                          category: Optional[str] = None,
                          db: Session = Depends(get_db),):
    products_query = db.query(Product)
    if name:
        products_query = products_query.filter(Product.name.ilike(f"%{name}%")).offset(skip).limit(limit)
    if description:
        products_query = products_query.filter(Product.description.ilike(f"%{description}%")).offset(skip).limit(limit)
    if category:
        products_query = products_query.filter(Product.category.ilike(f"%{category}%")).offset(skip).limit(limit)
    
    return products_query.all()

# Actualizar un producto
import shutil
from fastapi import UploadFile, File, HTTPException, Depends, status, Form
from sqlalchemy.orm import Session

UPLOAD_FOLDER = "./uploads/"  # Ruta donde se guardarán las imágenes

# Actualizar un producto y su imagen
@app.put("/products/{product_id}", response_model=ProductResponse, tags=["productos"])
async def update_product(
    product_id: int,
    name: str = Form(None),
    description: str = Form(None),
    price: float = Form(None),
    sizes: str = Form(None),
    colors: str = Form(None),
    category: str = Form(None),
    stock: int = Form(None),
    image: UploadFile = File(None),  # Imagen opcional para actualizar
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    # Verificar el token y el rol del usuario
    username = verify_token(token)
    user = db.query(User).filter(User.username == username).first()
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    # Buscar el producto por ID
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Actualizar los campos del producto si se proporcionan
    update_data = {
        "name": name,
        "description": description,
        "price": price,
        "sizes": sizes,
        "colors": colors,
        "category": category,
        "stock": stock,
    }
    for key, value in update_data.items():
        if value is not None:
            setattr(db_product, key, value)

    # Manejar la actualización de la imagen si se proporciona
    if image:
        # Guardar la nueva imagen en el servidor
        file_location = f"{UPLOAD_FOLDER}{image.filename}"
        with open(file_location, "wb") as file:
            shutil.copyfileobj(image.file, file)

        # Actualizar la URL de la imagen en la base de datos
        db_product.image_url = file_location

    # Confirmar los cambios en la base de datos
    db.commit()
    db.refresh(db_product)

    return db_product

# Eliminar un producto
@app.delete("/products/{product_id}",tags=["productos"])
async def delete_product(product_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = verify_token(token)
    user = db.query(User).filter(User.username == username).first()
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}


create_admin()