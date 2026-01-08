document.addEventListener('DOMContentLoaded', function() {
    const map = L.map('map').setView([55.7558, 37.6173], 10);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    // Группа кластеров для маркеров станций
    const markers = L.markerClusterGroup();
    map.addLayer(markers);

    let stations = [];
    let userMarker = null;

    // Геолокация пользователя
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;

            // Установка вида карты на позицию пользователя
            map.setView([lat, lon], 12);

            // Добавление маркера пользователя
            userMarker = L.marker([lat, lon], {
                icon: L.icon({
                    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
                    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                })
            }).addTo(map).bindPopup('Ваше местоположение');

            // Автоматическая загрузка станций вокруг пользователя
            loadStations(lat, lon, 10);

            // Заполнение полей поиска
            document.getElementById('lat').value = lat.toFixed(4);
            document.getElementById('lon').value = lon.toFixed(4);
        }, function(error) {
            console.warn('Geolocation error:', error);
            loadStations(); // Загрузка по умолчанию
        });
    } else {
        loadStations(); // Загрузка по умолчанию
    }

    // Загрузка станций по координатам
    async function loadStations(lat = 55.7558, lon = 37.6173, radius = 10) {
        try {
            const response = await fetch(`/api/v1/stations?latitude=${lat}&longitude=${lon}&radius_km=${radius}`);
            stations = await response.json();
            displayStations(stations);
        } catch (error) {
            console.error('Ошибка загрузки станций:', error);
        }
    }

    // Отображение станций на карте
    function displayStations(stations) {
        // Очистка предыдущих маркеров
        markers.clearLayers();

        stations.forEach(station => {
            const marker = L.marker([station.latitude, station.longitude])
                .bindPopup(`
                    <div class="station-info">
                        <h3>${station.title}</h3>
                        <p><strong>Адрес:</strong> ${station.address}</p>
                        <p><strong>Разъем:</strong> ${station.connector_type}</p>
                        <p><strong>Мощность:</strong> ${station.power_kw} kW</p>
                        <p><strong>Статус:</strong> ${station.status}</p>
                        ${station.price ? `<p><strong>Цена:</strong> ${station.price} руб/кВт</p>` : ''}
                        ${station.hours ? `<p><strong>Часы работы:</strong> ${station.hours}</p>` : ''}
                        <button onclick="toggleFavorite(${station.id})" class="favorite-btn" id="fav-${station.id}">
                            ★ Избранное
                        </button>
                    </div>
                `);
            markers.addLayer(marker);
        });

        // Проверка избранных станций
        checkFavorites(stations);
    }

    // Поиск по местоположению
    document.getElementById('search-btn').addEventListener('click', function() {
        const lat = parseFloat(document.getElementById('lat').value) || 55.7558;
        const lon = parseFloat(document.getElementById('lon').value) || 37.6173;
        const radius = parseFloat(document.getElementById('radius').value) || 10;
        map.setView([lat, lon], 10);
        loadStations(lat, lon, radius);
    });

    // Фильтр по типу разъема
    document.getElementById('connector-filter').addEventListener('change', function() {
        const selectedType = this.value;
        if (selectedType === 'all') {
            displayStations(stations);
        } else {
            const filtered = stations.filter(s => s.connector_type.toLowerCase().includes(selectedType.toLowerCase()));
            displayStations(filtered);
        }
    });

    // Обновление кэша
    document.getElementById('update-cache-btn').addEventListener('click', async function() {
        const statusEl = document.getElementById('status');
        statusEl.textContent = 'Обновление данных...';

        try {
            const lat = parseFloat(document.getElementById('lat').value) || 55.7558;
            const lon = parseFloat(document.getElementById('lon').value) || 37.6173;
            const radius = parseFloat(document.getElementById('radius').value) || 10;

            const response = await fetch(`/api/v1/stations/update_cache?latitude=${lat}&longitude=${lon}&radius=${radius}`, {
                method: 'POST'
            });

            if (response.ok) {
                statusEl.textContent = 'Данные обновляются в фоне...';
                setTimeout(() => {
                    loadStations(lat, lon, radius);
                    statusEl.textContent = '';
                }, 2000);
            } else {
                statusEl.textContent = 'Ошибка обновления';
            }
        } catch (error) {
            console.error('Error updating cache:', error);
            statusEl.textContent = 'Ошибка обновления';
        }
    });

    // Функции для работы с избранными станциями
    window.toggleFavorite = async function(stationId) {
        const btn = document.getElementById(`fav-${stationId}`);
        
        try {
            // Проверяем текущий статус
            const checkResponse = await fetch(`/api/v1/favorites/check/${stationId}`);
            const checkData = await checkResponse.json();
            
            if (checkData.is_favorite) {
                // Удалить из избранного
                const response = await fetch(`/api/v1/favorites/${stationId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    btn.textContent = '☆ В избранное';
                    btn.style.background = '#f0f0f0';
                    btn.style.color = '#666';
                }
            } else {
                // Добавить в избранное
                const response = await fetch(`/api/v1/favorites/${stationId}`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    btn.textContent = '★ В избранном';
                    btn.style.background = '#ffd700';
                    btn.style.color = '#000';
                }
            }
        } catch (error) {
            console.error('Ошибка при работе с избранным:', error);
        }
    };

    async function checkFavorites(stations) {
        for (const station of stations) {
            try {
                const response = await fetch(`/api/v1/favorites/check/${station.id}`);
                const data = await response.json();
                
                const btn = document.getElementById(`fav-${station.id}`);
                if (btn) {
                    if (data.is_favorite) {
                        btn.textContent = '★ В избранном';
                        btn.style.background = '#ffd700';
                        btn.style.color = '#000';
                    } else {
                        btn.textContent = '☆ В избранное';
                        btn.style.background = '#f0f0f0';
                        btn.style.color = '#666';
                    }
                }
            } catch (error) {
                console.error('Ошибка проверки избранного:', error);
            }
        }
    }
});