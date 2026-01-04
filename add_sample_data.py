from app.database import SessionLocal
from app.models import Station

def add_sample_stations():
    db = SessionLocal()
    try:
        # Примерные станции в Москве
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
        print("Тестовые станции добавлены")
    except Exception as e:
        print(f"Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_sample_stations()