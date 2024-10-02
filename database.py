from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql://db_textileria_luz_user:YGuCl8dNJMJkyobegrLybfbOPQzPEhRa@dpg-cru8obdumphs73ejht3g-a.oregon-postgres.render.com/db_textileria_luz"  # Cambiar por el URI de tu base de datos

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
