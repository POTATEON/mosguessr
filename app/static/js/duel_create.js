// ===========================
// Инициализация
// ===========================
const socket = io();

console.log('[CREATE] Script loaded');
console.log('[CREATE] Socket connected:', socket.connected);
console.log('[CREATE] duelId:', duelId);
console.log('[CREATE] myUserId:', myUserId);

// 🔥 Получаем данные из sessionStorage
const duelId = parseInt(sessionStorage.getItem('duel_id'));
const opponentName = sessionStorage.getItem('opponent_name') || 'Соперник';
const myUserId = parseInt(sessionStorage.getItem('my_user_id'));

console.log(`[CREATE] Duel ${duelId}, User ${myUserId}`);

if (!duelId || !myUserId) {
    alert('Ошибка: данные дуэли не найдены. Вернитесь в меню.');
    window.location.href = '/duel';
}

// Присоединяемся к дуэли
socket.emit('join_creator_duel', { duel_id: duelId });

// Состояния
let phase = 'creating'; // 'creating' | 'guessing' | 'results'
let selectMap = null;
let guessMap = null;
let selectedCoords = null;
let selectPlacemark = null;
let guessPlacemark = null;
let panoramaPlayer = null;
let previewPlayer = null;
let timerInterval = null;
let timeLeft = 45;
let roundNumber = 1;
let startCoords = null;

// Элементы
const selectMapFloat = document.getElementById('selectMapFloat');
const guessMapFloat = document.getElementById('guessMapFloat');
const confirmBtn = document.getElementById('confirmBtn');
const guessBtn = document.getElementById('guessBtn');
const selectMapHint = document.getElementById('selectMapHint');
const guessMapHint = document.getElementById('guessMapHint');
const goToStartBtn = document.getElementById('goToStart');

// Состояния карт
let selectMapExpanded = false;
let selectMapCollapsed = false;
let guessMapExpanded = false;
let guessMapCollapsed = false;

// ===========================
// Карты
// ===========================
ymaps.ready(() => {
    // Карта для выбора точки
    selectMap = new ymaps.Map('map', {
        center: [55.751244, 37.618423],
        zoom: 10,
        controls: []
    });

    selectMap.events.add('click', (e) => {
        if (phase !== 'creating') return;

        const coords = e.get('coords');
        selectedCoords = coords;

        if (selectPlacemark) {
            selectPlacemark.geometry.setCoordinates(coords);
        } else {
            selectPlacemark = new ymaps.Placemark(coords, {
                hintContent: 'Выбранное место',
                balloonContent: '📍 Ваша точка'
            }, {
                draggable: true,
                preset: 'islands#redIcon',
                iconColor: '#e05a2b'
            });
            selectMap.geoObjects.add(selectPlacemark);

            selectPlacemark.events.add('dragend', () => {
                selectedCoords = selectPlacemark.geometry.getCoordinates();
                checkPanorama(selectedCoords);
            });
        }

        confirmBtn.disabled = false;
        selectMapHint.style.opacity = '0';
        checkPanorama(coords);
    });

    // Карта для угадывания (инициализируем позже)
    guessMap = new ymaps.Map('guessMap', {
        center: [55.751244, 37.618423],
        zoom: 10,
        controls: []
    });

    guessMap.events.add('click', (e) => {
        if (phase !== 'guessing') return;

        const coords = e.get('coords');

        if (guessPlacemark) {
            guessPlacemark.geometry.setCoordinates(coords);
        } else {
            guessPlacemark = new ymaps.Placemark(coords, {
                hintContent: 'Ваша догадка',
                balloonContent: '🎯 Ваша догадка'
            }, {
                preset: 'islands#redIcon',
                iconColor: '#f85149'
            });
            guessMap.geoObjects.add(guessPlacemark);
        }

        guessBtn.disabled = false;
        guessMapHint.style.opacity = '0';
    });
});

// ===========================
// Кнопки сворачивания/разворачивания
// ===========================

// Карта выбора
document.getElementById('selectExpandBtn').addEventListener('click', (e) => {
    e.stopPropagation();
    if (selectMapCollapsed) {
        selectMapCollapsed = false;
        selectMapFloat.classList.remove('collapsed');
        updateSelectCollapseIcon();
    }
    selectMapExpanded = !selectMapExpanded;
    selectMapFloat.classList.toggle('expanded', selectMapExpanded);
    updateSelectExpandIcon();
    setTimeout(() => { if (selectMap) selectMap.container.fitToViewport(); }, 370);
});

document.getElementById('selectCollapseBtn').addEventListener('click', (e) => {
    e.stopPropagation();
    selectMapCollapsed = !selectMapCollapsed;
    selectMapFloat.classList.toggle('collapsed', selectMapCollapsed);
    if (selectMapCollapsed) {
        selectMapExpanded = false;
        selectMapFloat.classList.remove('expanded');
        updateSelectExpandIcon();
    }
    updateSelectCollapseIcon();
    if (!selectMapCollapsed) {
        setTimeout(() => { if (selectMap) selectMap.container.fitToViewport(); }, 370);
    }
});

// Карта угадывания
document.getElementById('guessExpandBtn').addEventListener('click', (e) => {
    e.stopPropagation();
    if (guessMapCollapsed) {
        guessMapCollapsed = false;
        guessMapFloat.classList.remove('collapsed');
        updateGuessCollapseIcon();
    }
    guessMapExpanded = !guessMapExpanded;
    guessMapFloat.classList.toggle('expanded', guessMapExpanded);
    updateGuessExpandIcon();
    setTimeout(() => { if (guessMap) guessMap.container.fitToViewport(); }, 370);
});

document.getElementById('guessCollapseBtn').addEventListener('click', (e) => {
    e.stopPropagation();
    guessMapCollapsed = !guessMapCollapsed;
    guessMapFloat.classList.toggle('collapsed', guessMapCollapsed);
    if (guessMapCollapsed) {
        guessMapExpanded = false;
        guessMapFloat.classList.remove('expanded');
        updateGuessExpandIcon();
    }
    updateGuessCollapseIcon();
    if (!guessMapCollapsed) {
        setTimeout(() => { if (guessMap) guessMap.container.fitToViewport(); }, 370);
    }
});

function updateSelectExpandIcon() {
    const btn = document.getElementById('selectExpandBtn');
    btn.innerHTML = selectMapExpanded
        ? `<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
               <path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3"/>
           </svg>`
        : `<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
               <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
           </svg>`;
}

function updateSelectCollapseIcon() {
    const btn = document.getElementById('selectCollapseBtn');
    btn.innerHTML = selectMapCollapsed
        ? `<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
               <path d="M12 5v14M5 12h14"/>
           </svg>`
        : `<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
               <path d="M5 12h14"/>
           </svg>`;
    btn.title = selectMapCollapsed ? 'Развернуть' : 'Свернуть';
}

function updateGuessExpandIcon() {
    const btn = document.getElementById('guessExpandBtn');
    btn.innerHTML = guessMapExpanded
        ? `<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
               <path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3"/>
           </svg>`
        : `<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
               <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>
           </svg>`;
}

function updateGuessCollapseIcon() {
    const btn = document.getElementById('guessCollapseBtn');
    btn.innerHTML = guessMapCollapsed
        ? `<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
               <path d="M12 5v14M5 12h14"/>
           </svg>`
        : `<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
               <path d="M5 12h14"/>
           </svg>`;
    btn.title = guessMapCollapsed ? 'Развернуть' : 'Свернуть';
}

// ===========================
// Проверка панорамы
// ===========================
async function checkPanorama(coords) {
    try {
        const panoramas = await ymaps.panorama.locate(coords);

        if (panoramas && panoramas.length > 0) {
            showPanoPreview(panoramas[0], coords);
            confirmBtn.disabled = false;
        } else {
            hidePanoPreview();
            confirmBtn.disabled = true;
            showNotification('Нет панорамы в этой точке', 'error');
        }
    } catch (e) {
        console.error('Panorama check error:', e);
        hidePanoPreview();
        confirmBtn.disabled = true;
    }
}

function showPanoPreview(panorama, coords) {
    const box = document.getElementById('panoPreviewBox');
    box.classList.add('visible');

    if (previewPlayer) {
        try { previewPlayer.destroy(); } catch(e) {}
    }

    document.getElementById('panoPreview').innerHTML = '';

    previewPlayer = new ymaps.panorama.Player('panoPreview', panorama, {
        controls: [],
        suppressMapOpenBlock: true
    });

    showNotification('Панорама найдена! ✅', 'success');
}

function hidePanoPreview() {
    document.getElementById('panoPreviewBox').classList.remove('visible');
    if (previewPlayer) {
        try { previewPlayer.destroy(); } catch(e) {}
        previewPlayer = null;
    }
}

function closePanoPreview() {
    hidePanoPreview();
}

function showNotification(text, type) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        background: ${type === 'success' ? 'rgba(63,185,80,0.9)' : 'rgba(248,81,73,0.9)'};
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 600;
        z-index: 9999;
    `;
    notification.textContent = text;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.3s';
        setTimeout(() => notification.remove(), 300);
    }, 2000);
}

// ===========================
// Подтверждение локации
// ===========================
function confirmLocation() {
    if (!selectedCoords) return;

    console.log('[CREATE] Confirming location:', selectedCoords);

    socket.emit('creator_location_selected', {
        duel_id: duelId,
        lat: selectedCoords[0],
        lon: selectedCoords[1]
    });

    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Ожидание соперника...';
    document.getElementById('opponentStatus').textContent = 'Ожидание соперника...';
    document.getElementById('opponentStatus').className = 'opponent-status waiting';

    phase = 'waiting';
    selectMap.behaviors.disable('drag');
    selectMap.behaviors.disable('scrollZoom');
}

// ===========================
// Фаза угадывания
// ===========================
socket.on('start_guessing_phase', (data) => {
    console.log('[CREATE] Starting guessing phase:', data);

    phase = 'guessing';
    roundNumber = data.round_number;

    // Меняем видимость элементов
    document.getElementById('mainMap').style.display = 'none';
    document.getElementById('gamePano').style.display = 'block';
    selectMapFloat.classList.add('hidden');
    selectMapFloat.classList.remove('visible');
    guessMapFloat.classList.add('visible');
    guessMapFloat.classList.remove('hidden');

    goToStartBtn.classList.add('visible');

    document.getElementById('phasePill').textContent = 'Угадайте';
    document.getElementById('opponentStatus').textContent = opponentName + ' тоже угадывает...';
    document.getElementById('opponentStatus').className = 'opponent-status thinking';

    hidePanoPreview();

    // Загружаем панораму соперника
    loadOpponentPanorama(data.lat, data.lon);

    // Запускаем таймер
    startTimer(60);
});

async function loadOpponentPanorama(lat, lon) {
    startCoords = [lat, lon];

    try {
        const panoramas = await ymaps.panorama.locate([lat, lon]);

        if (panoramas && panoramas.length > 0) {
            panoramaPlayer = new ymaps.panorama.Player('gamePano', panoramas[0], {
                controls: [],
                suppressMapOpenBlock: true
            });
        } else {
            document.getElementById('gamePano').innerHTML = `
                <div style="display:flex;align-items:center;justify-content:center;height:100%;color:var(--muted);">
                    <div style="text-align:center;">
                        <div style="font-size:48px;">🗺️</div>
                        <div>Панорама недоступна</div>
                        <div style="font-size:12px;">Угадайте приблизительно</div>
                    </div>
                </div>
            `;
        }
    } catch (e) {
        console.error('Failed to load opponent panorama:', e);
    }
}

// Кнопка возврата к начальной точке
goToStartBtn.addEventListener('click', () => {
    if (startCoords && phase === 'guessing') {
        document.getElementById('gamePano').innerHTML = '';

        ymaps.panorama.locate(startCoords).then(panoramas => {
            if (panoramas.length) {
                if (panoramaPlayer) {
                    try { panoramaPlayer.destroy(); } catch(e) {}
                }
                panoramaPlayer = new ymaps.panorama.Player('gamePano', panoramas[0], {
                    controls: [],
                    suppressMapOpenBlock: true
                });
            }
        });
    }
});

// ===========================
// Отправка догадки
// ===========================
function submitGuess() {
    if (!guessPlacemark) return;

    const coords = guessPlacemark.geometry.getCoordinates();

    console.log('[CREATE] Submitting guess:', coords);

    socket.emit('submit_creator_guess', {
        duel_id: duelId,
        guess_lat: coords[0],
        guess_lon: coords[1]
    });

    guessBtn.disabled = true;
    guessBtn.textContent = 'Ожидание...';
    document.getElementById('opponentStatus').textContent = 'Ожидание соперника...';
    document.getElementById('opponentStatus').className = 'opponent-status waiting';
}

socket.on('creator_round_result', (data) => {
    // ВЫВОДИМ ВСЁ В КОНСОЛЬ
    console.log('=== ВСЕ ДАННЫЕ ===');
    console.log(JSON.stringify(data, null, 2));
    console.log('opponent_lat:', data.opponent_lat, 'opponent_lon:', data.opponent_lon);
    console.log('my_guess существует?:', !!data.my_guess);
    console.log('my_guess содержимое:', data.my_guess);
    console.log('my_location существует?:', !!data.my_location);
    console.log('my_location содержимое:', data.my_location);
    console.log('enemy_guess существует?:', !!data.enemy_guess);
    console.log('enemy_guess содержимое:', data.enemy_guess);

    stopTimer();
    phase = 'results';
    document.getElementById('resultModal').classList.add('visible');

    setTimeout(() => {
        // Очищаем обе карты
        document.getElementById('enemyResultMap').innerHTML = '';
        document.getElementById('myResultMap').innerHTML = '';

        // ========================================
        // КАРТА 1 (ЛЕВАЯ): Локация соперника + ТВОЯ догадка
        // ========================================
        const map1 = new ymaps.Map('enemyResultMap', {
            center: [data.opponent_lat, data.opponent_lon],
            zoom: 12,
            controls: []
        });

        // Зеленая метка — локация соперника
        map1.geoObjects.add(new ymaps.Placemark(
            [data.opponent_lat, data.opponent_lon],
            { hintContent: 'Локация соперника' },
            { preset: 'islands#greenIcon', iconColor: '#3fb950' }
        ));

        // Если есть твоя догадка
        if (data.my_guess && data.my_guess.lat && data.my_guess.lon) {
            map1.geoObjects.add(new ymaps.Placemark(
                [data.my_guess.lat, data.my_guess.lon],
                { hintContent: 'Твоя догадка' },
                { preset: 'islands#redIcon', iconColor: '#f85149' }
            ));
            map1.geoObjects.add(new ymaps.Polyline(
                [[data.my_guess.lat, data.my_guess.lon], [data.opponent_lat, data.opponent_lon]],
                {},
                { strokeColor: '#f0a500', strokeWidth: 3, strokeOpacity: 1, strokeStyle: 'dash' }
            ));
            map1.setBounds(map1.geoObjects.getBounds(), { zoomMargin: 40, checkZoomRange: true });
        }

        // ========================================
        // КАРТА 2 (ПРАВАЯ): ТВОЯ локация + ДОГАДКА СОПЕРНИКА
        // ========================================
        const myLoc = data.my_location;
        const enemyGuess = data.enemy_guess;

        const center2 = (myLoc?.lat && myLoc?.lon)
            ? [myLoc.lat, myLoc.lon]
            : [55.75, 37.62];

        const map2 = new ymaps.Map('myResultMap', {
            center: center2,
            zoom: 12,
            controls: []
        });

        if (myLoc?.lat && myLoc?.lon) {
            // Зеленая метка — твоя локация
            map2.geoObjects.add(new ymaps.Placemark(
                [myLoc.lat, myLoc.lon],
                { hintContent: 'Твоя локация' },
                { preset: 'islands#greenIcon', iconColor: '#3fb950' }
            ));

            // Если есть догадка соперника
            if (enemyGuess?.lat && enemyGuess?.lon) {
                map2.geoObjects.add(new ymaps.Placemark(
                    [enemyGuess.lat, enemyGuess.lon],
                    { hintContent: 'Догадка соперника' },
                    { preset: 'islands#redIcon', iconColor: '#f85149' }
                ));
                map2.geoObjects.add(new ymaps.Polyline(
                    [[enemyGuess.lat, enemyGuess.lon], [myLoc.lat, myLoc.lon]],
                    {},
                    { strokeColor: '#f0a500', strokeWidth: 3, strokeOpacity: 1, strokeStyle: 'dash' }
                ));
                map2.setBounds(map2.geoObjects.getBounds(), { zoomMargin: 40, checkZoomRange: true });
            }
        }

        // Таблица
        let html = '<table class="scores-table"><thead><tr><th>Игрок</th><th>Дистанция</th><th>Очки</th></tr></thead><tbody>';
        data.players.forEach(p => {
            const cls = p.score >= 4000 ? 'score-high' : p.score >= 2000 ? 'score-med' : '';
            html += `<tr><td>${p.name} ${p.user_id === myUserId ? '(Вы)' : ''}</td><td>${p.distance ? p.distance.toFixed(2) + ' км' : '—'}</td><td class="${cls}">${p.score || 0}</td></tr>`;
        });
        html += '</tbody></table>';
        document.getElementById('scoresTableContainer').innerHTML = html;

        const btn = document.getElementById('nextRoundBtn');
        btn.textContent = data.is_last_round ? 'Завершить' : 'Следующий раунд →';
        btn.disabled = false;
    }, 300);
});

function goNextRound() {
    socket.emit('next_creator_round', { duel_id: duelId });
    document.getElementById('resultModal').classList.remove('visible');
    document.getElementById('nextRoundBtn').disabled = true;
    resetForNextRound();
}

function resetForNextRound() {
    phase = 'creating';

    document.getElementById('mainMap').style.display = 'block';
    document.getElementById('gamePano').style.display = 'none';
    document.getElementById('gamePano').innerHTML = '';
    selectMapFloat.classList.add('visible');
    selectMapFloat.classList.remove('hidden');
    guessMapFloat.classList.add('hidden');
    guessMapFloat.classList.remove('visible');
    goToStartBtn.classList.remove('visible');

    confirmBtn.disabled = true;
    confirmBtn.textContent = '✅ Подтвердить точку';
    guessBtn.disabled = true;
    guessBtn.textContent = '🎯 Угадать';

    document.getElementById('phasePill').textContent = 'Выберите точку';
    document.getElementById('opponentStatus').textContent = 'Соперник выбирает...';
    document.getElementById('opponentStatus').className = 'opponent-status thinking';
    document.getElementById('selectMapHint').style.opacity = '1';
    document.getElementById('guessMapHint').style.opacity = '1';

    if (selectPlacemark) {
        selectMap.geoObjects.remove(selectPlacemark);
        selectPlacemark = null;
    }

    if (guessPlacemark && guessMap) {
        guessMap.geoObjects.remove(guessPlacemark);
        guessPlacemark = null;
    }

    if (panoramaPlayer) {
        try { panoramaPlayer.destroy(); } catch(e) {}
        panoramaPlayer = null;
    }

    selectedCoords = null;
    startCoords = null;

    selectMap.behaviors.enable('drag');
    selectMap.behaviors.enable('scrollZoom');

    startTimer(45);
}

// ===========================
// Завершение дуэли
// ===========================
socket.on('duel_finished', (data) => {
    stopTimer();

    const myScore = data.total_scores[myUserId] || 0;
    const oppId = Object.keys(data.total_scores).find(id => id != myUserId);
    const oppScore = oppId ? (data.total_scores[oppId] || 0) : 0;

    let title, content;
    if (myScore > oppScore) {
        title = '🏆 Вы победили!';
        content = `<p style="font-size:64px;color:var(--green);font-family:'Bebas Neue',sans-serif;">${myScore} : ${oppScore}</p>`;
    } else if (oppScore > myScore) {
        title = '😞 Вы проиграли';
        content = `<p style="font-size:64px;color:var(--red);font-family:'Bebas Neue',sans-serif;">${myScore} : ${oppScore}</p>`;
    } else {
        title = '🤝 Ничья!';
        content = `<p style="font-size:64px;color:var(--accent);font-family:'Bebas Neue',sans-serif;">${myScore} : ${oppScore}</p>`;
    }

    document.getElementById('resultModal').classList.add('visible');
    document.getElementById('resultTitle').textContent = title;
    document.getElementById('scoresTableContainer').innerHTML = content;

    const nextBtn = document.getElementById('nextRoundBtn');
    nextBtn.textContent = 'В меню дуэлей';
    nextBtn.onclick = () => window.location.href = '/duel';
});

// ===========================
// Таймер
// ===========================
function startTimer(seconds) {
    timeLeft = seconds;
    updateTimerDisplay();
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        timeLeft--;
        updateTimerDisplay();
        if (timeLeft <= 0) {
            stopTimer();
            if (phase === 'creating' && selectedCoords) {
                confirmLocation();
            } else if (phase === 'guessing') {
                // 🔥 Всегда отправляем при истечении времени
                if (guessPlacemark) {
                    submitGuess();
                } else {
                    // Если даже не выбрал точку - отправляем пустые координаты
                    socket.emit('submit_creator_guess', {
                        duel_id: duelId,
                        guess_lat: null,
                        guess_lon: null
                    });
                    guessBtn.disabled = true;
                    guessBtn.textContent = 'Время вышло';
                    document.getElementById('opponentStatus').textContent = 'Время истекло';
                    document.getElementById('opponentStatus').className = 'opponent-status waiting';
                }
            } else if (phase === 'waiting') {
                // Ничего не делаем, ждем соперника
            }
        }
    }, 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
}

function updateTimerDisplay() {
    const pill = document.getElementById('timerPill');
    pill.textContent = timeLeft;

    pill.classList.remove('safe', 'warn', 'danger');
    if (timeLeft <= 10) {
        pill.classList.add('danger');
    } else if (timeLeft <= 20) {
        pill.classList.add('warn');
    } else {
        pill.classList.add('safe');
    }
}

// ===========================
// Socket события
// ===========================
socket.on('opponent_selected_location', (data) => {
    document.getElementById('opponentStatus').textContent = opponentName + ' выбрал точку';
    document.getElementById('opponentStatus').className = 'opponent-status answered';
});

socket.on('opponent_guessed', (data) => {
    document.getElementById('opponentStatus').textContent = opponentName + ' сделал догадку';
    document.getElementById('opponentStatus').className = 'opponent-status answered';
});

socket.on('error', (data) => {
    alert(data.message);
});

socket.on('opponent_disconnected', () => {
    alert('Соперник отключился');
    window.location.href = '/duel';
});

// Запускаем таймер
startTimer(45);