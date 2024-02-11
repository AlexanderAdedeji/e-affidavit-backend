from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from  app.core.settings.configurations import settings





url = settings.POSTGRES_DB_URL
engine = create_engine(url,pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)






