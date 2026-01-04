from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.api import stations
from app.api import auth
from app.core.config import settings
from app.database import engine
from app.models import Base
from app.utils import logging

# Setup logging
logging.setup_logging()

# Создание таблиц
Base.metadata.create_all(bind=engine)

# Добавление тестовых данных
def add_sample_data():
    import logging as logger_module  # Avoid naming conflict
    logger = logger_module.getLogger(__name__)
    from app.database import SessionLocal
    from app.models.station import Station
    db = SessionLocal()
    try:
        if db.query(Station).count() == 0:  # Только если нет данных
            stations = [
                {
                    "title": "Зарядная станция ТЦ Атриум",
                    "address": "Москва, ул. Земляной Вал, 33",
                    "latitude": 55.7568,
                    "longitude": 37.6591,
                    "connector_type": "CCS",
                    "power_kw": 50.0,
                    "status": "available",
                    "price": 15.0,
                    "hours": "24/7"
                },
                {
                    "title": "EV зарядка у метро Тверская",
                    "address": "Москва, Тверская ул., 12",
                    "latitude": 55.7642,
                    "longitude": 37.6008,
                    "connector_type": "CHAdeMO",
                    "power_kw": 62.5,
                    "status": "occupied",
                    "price": 12.0,
                    "hours": "06:00-22:00"
                },
                {
                    "title": "Быстрая зарядка Сити",
                    "address": "Москва, Пресненская наб., 12",
                    "latitude": 55.7494,
                    "longitude": 37.5379,
                    "connector_type": "Type 2",
                    "power_kw": 22.0,
                    "status": "available",
                    "price": 10.0,
                    "hours": "24/7"
                }
            ]
            for station_data in stations:
                station = Station(**station_data)
                db.add(station)
            db.commit()
            logger.info("Тестовые станции добавлены")
    except Exception as e:
        logger.error(f"Ошибка добавления данных: {e}")
        db.rollback()
    finally:
        db.close()

add_sample_data()

app = FastAPI(
    title="VoltWay",
    description="Интерактивная карта зарядных станций для электромобилей",
    version="1.0.0",
)
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Монтирование статических файлов
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Шаблоны
templates = Jinja2Templates(directory="app/templates")

# Роутеры
app.include_router(stations.router, prefix="/api/v1", tags=["stations"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])

# Create tables after all models are imported
Base.metadata.create_all(bind=engine)

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/v1/")
async def root():
    return {"message": "Welcome to VoltWay API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)