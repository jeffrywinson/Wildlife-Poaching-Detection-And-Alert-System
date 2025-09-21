document.addEventListener('DOMContentLoaded', () => {
    // --- Custom Map Icons ---
    const createIcon = (color) => L.divIcon({
        className: 'custom-map-icon',
        html: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}" width="24px" height="24px"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/><circle cx="12" cy="9.5" r="2.5" fill="white"/></svg>`,
        iconSize: [24, 24],
        iconAnchor: [12, 24],
        popupAnchor: [0, -24]
    });
    const greenIcon = createIcon('#28a745'); // Normal
    const redIcon = createIcon('#dc3545');   // Threat

    // --- Map Initialization ---
    const map = L.map('map').setView([12.9716, 77.5946], 11);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    }).addTo(map);

    const cameraMarkers = {};
    const zoneCircles = {};

    const alertsContainer = document.getElementById('alerts-container');
    const eventsLog = document.getElementById('events-log');

    // --- State Update Function ---
    const updateDashboard = async () => {
        try {
            const response = await fetch('/api/get_state');
            if (!response.ok) return;
            const state = await response.json();

            // 1. Update Camera Markers and Popups
            for (const camId in state.cameras) {
                const cam = state.cameras[camId];
                const isThreat = cam.last_detection?.type === 'human' || cam.last_detection?.type === 'vehicle';
                const icon = isThreat ? redIcon : greenIcon;
                
                let popupContent = `<b>${cam.name}</b><br>${camId}<br>Status: OK`;
                if(cam.last_detection) {
                    const detectionTime = new Date(cam.last_detection.timestamp).toLocaleTimeString();
                    popupContent = `<b>${cam.name}</b><br>${camId}<br>Last seen: ${cam.last_detection.type} at ${detectionTime}`;
                }

                if (!cameraMarkers[camId]) {
                    cameraMarkers[camId] = L.marker([cam.lat, cam.lon], { icon }).addTo(map);
                }
                cameraMarkers[camId].setIcon(icon).bindPopup(popupContent);
            }

            // 2. Update Active Zones
            const activeZoneIds = Object.keys(state.active_zones);
            Object.keys(zoneCircles).forEach(camId => {
                if (!activeZoneIds.includes(camId)) {
                    map.removeLayer(zoneCircles[camId]);
                    delete zoneCircles[camId];
                }
            });
            activeZoneIds.forEach(camId => {
                const zone = state.active_zones[camId];
                if (!zoneCircles[camId]) {
                    zoneCircles[camId] = L.circle([zone.lat, zone.lon], {
                        color: '#f0ad4e', weight: 2, fillOpacity: 0.2, radius: 2000
                    }).addTo(map).bindPopup(`Active Zone around ${state.cameras[camId].name}`);
                }
            });
            
            // 3. Update High-Priority Alerts
            alertsContainer.innerHTML = state.alerts.length === 0 
                ? '<p class="no-alerts">No high-priority alerts at the moment.</p>'
                : state.alerts.map(alert => {
                    const alertDate = new Date(alert.timestamp);
                    return `<div class="alert-item">
                                <p>${alert.message}</p>
                                <span>${alertDate.toLocaleTimeString()} - ${alertDate.toLocaleDateString()}</span>
                            </div>`;
                }).join('');

            // 4. Update Recent Events Log
            eventsLog.innerHTML = state.events.map(event => {
                const eventDate = new Date(event.timestamp);
                const threatClass = event.is_threat ? 'event-threat' : '';
                return `<li class="${threatClass}"><span>${eventDate.toLocaleTimeString()}:</span> ${event.message}</li>`;
            }).join('');

        } catch (error) {
            console.error('Error updating dashboard:', error);
        }
    };

    updateDashboard();
    setInterval(updateDashboard, 3000); // Refresh every 3 seconds
});