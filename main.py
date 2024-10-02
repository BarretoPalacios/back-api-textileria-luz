from fastapi import FastAPI, Depends, HTTPException, status
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
from create_admin import createAdmin

app = FastAPI()

Base.metadata.create_all(bind=engine)
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

@app.post("/token",tags=["Login"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=30))
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/products/", response_model=ProductResponse,tags=["productos"])
async def create_product(
    name: str,
    description: str,
    price: float,
    sizes: str,
    colors: str,
    category : str,
    stock:int,
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
@app.put("/products/{product_id}", response_model=ProductResponse,tags=["productos"])
async def update_product(product_id: int, product: ProductUpdate, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    username = verify_token(token)
    user = db.query(User).filter(User.username == username).first()
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in product.dict().items():
        setattr(db_product, key, value)
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


createAdmin()