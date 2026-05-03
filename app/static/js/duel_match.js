// ===========================
// Инициализация
// ===========================
const socket = io();
const duelId = parseInt(sessionStorage.getItem('duel_id'));
const opponentName = sessionStorage.getItem('opponent_name') || 'Соперник';
const myUserId = parseInt(sessionStorage.getItem('my_user_id'));

console.log('Duels: duelId=' + duelId + ', myUserId=' + myUserId + ', opponent=' + opponentName);

if (!duelId || !myUserId) {
    alert('Ошибка: данные дуэли не найдены. Вернитесь в меню.');
    window.location.href = '/duel';
}

let myMap = null;
let myPlacemark = null;
let panoramaPlayer = null;
let currentRound = 0;
let timerInterval = null;
let timeLeft = 60;
let guessLat = null;
let guessLon = null;
let roundActive = false;
let myTotalScore = 0;
let opponentTotalScore = 0;
let startCoords = null;
let panoramaAttempts = 0;
const MAX_PANORAMA_ATTEMPTS = 10;
let panoramaNotFoundSent = false;
let guessSubmitted = false;
let roundFinished = false;

// ★ Токен отмены для асинхронных операций загрузки панорам
let currentLoadToken = null;

socket.emit('join_duel_from_queue', { duel_id: duelId });
console.log('Sent join_duel_from_queue, duel_id=' + duelId);

// ===========================
// Безопасное уничтожение плеера
// ===========================
function destroyPanoramaPlayer() {
    if (panoramaPlayer) {
        try {
            panoramaPlayer.destroy();
        } catch(e) {
            console.warn('[PANORAMA] Error destroying player:', e);
        }
        panoramaPlayer = null;
    }
}

// ===========================
// Сброс всех состояний загрузки панорам
// ===========================
function resetPanoramaState() {
    currentLoadToken = null;
    panoramaAttempts = 0;
    panoramaNotFoundSent = false;
    destroyPanoramaPlayer();
}

// ===========================
// Яндекс.Карты
// ===========================
ymaps.ready(function() {
    myMap = new ymaps.Map('map', {
        center: [55.751244, 37.618423],
        zoom: 9,
        controls: []
    });

    if (typeof setUIMap === 'function') {
        setUIMap(myMap);
    }

    myMap.events.add('click', function(e) {
        if (!roundActive || guessSubmitted || roundFinished) return;
        const coords = e.get('coords');
        guessLat = coords[0];
        guessLon = coords[1];

        if (myPlacemark) {
            myPlacemark.geometry.setCoordinates(coords);
        } else {
            myPlacemark = new ymaps.Placemark(coords, {}, {
                draggable: true,
                preset: 'islands#redIcon',
                iconColor: '#e05a2b'
            });
            myMap.geoObjects.add(myPlacemark);
            myPlacemark.events.add('dragend', function() {
                const newCoords = myPlacemark.geometry.getCoordinates();
                guessLat = newCoords[0];
                guessLon = newCoords[1];
            });
        }
        document.getElementById('guessBtn').disabled = false;

        if (typeof hideMapHint === 'function') {
            hideMapHint();
        }
    });
});

// ===========================
// Загрузка панорамы (с токеном отмены)
// ===========================
async function loadPanorama(lat, lon, cityName) {
    const myToken = {};
    currentLoadToken = myToken;

    console.log(`[PANORAMA] Loading: ${cityName} at ${lat.toFixed(6)}, ${lon.toFixed(6)} [token: ${JSON.stringify(myToken)}]`);

    destroyPanoramaPlayer();

    const panoDiv = document.getElementById('pano');
    if (!panoDiv) {
        console.warn('[PANORAMA] Container #pano not found in DOM');
        return;
    }

    panoDiv.innerHTML = '';
    panoDiv.style.display = 'block';

    await new Promise(resolve => requestAnimationFrame(resolve));
    await new Promise(resolve => setTimeout(resolve, 50));

    if (currentLoadToken !== myToken) {
        console.log(`[PANORAMA] Token expired before locate for ${cityName} at ${lat.toFixed(6)}, ${lon.toFixed(6)}`);
        return;
    }

    if (!document.getElementById('pano')) {
        console.warn('[PANORAMA] Container #pano removed from DOM');
        return;
    }

    if (panoDiv.offsetWidth === 0 || panoDiv.offsetHeight === 0) {
        console.error('[PANORAMA] Container has zero size');
        return;
    }

    try {
        const panoramas = await ymaps.panorama.locate([lat, lon]);

        if (currentLoadToken !== myToken) {
            console.log(`[PANORAMA] Token expired after locate for ${cityName} at ${lat.toFixed(6)}, ${lon.toFixed(6)} — discarding result`);
            return;
        }

        if (!panoramas || panoramas.length === 0) {
            throw new Error('No panorama');
        }

        if (!document.getElementById('pano')) {
            console.warn('[PANORAMA] Container #pano removed from DOM after locate');
            return;
        }

        panoramaAttempts = 0;
        panoramaNotFoundSent = false;
        startCoords = [lat, lon];

        panoramaPlayer = new ymaps.panorama.Player('pano', panoramas[0], {
            controls: [],
            suppressMapOpenBlock: true
        });

        console.log(`[PANORAMA] ✓ Loaded: ${cityName} at ${lat.toFixed(6)}, ${lon.toFixed(6)}`);

    } catch (error) {
        if (currentLoadToken !== myToken) {
            console.log(`[PANORAMA] Token expired in catch for ${cityName} at ${lat.toFixed(6)}, ${lon.toFixed(6)} — discarding error`);
            return;
        }

        console.log(`[PANORAMA] ✗ Not found: ${cityName} at ${lat.toFixed(6)}, ${lon.toFixed(6)}`);
        panoramaAttempts++;

        if (!document.getElementById('pano')) {
            console.warn('[PANORAMA] Container #pano removed from DOM');
            return;
        }

        if (guessSubmitted || roundFinished) {
            console.log('[PANORAMA] Guess already submitted or round finished, not requesting regeneration');
            return;
        }

        if (panoramaAttempts < MAX_PANORAMA_ATTEMPTS && !panoramaNotFoundSent) {
            panoramaNotFoundSent = true;
            console.log(`[PANORAMA] Requesting regeneration (attempt ${panoramaAttempts}/${MAX_PANORAMA_ATTEMPTS})`);
            socket.emit('panorama_not_found', { duel_id: duelId });
        }
        else if (panoramaAttempts >= MAX_PANORAMA_ATTEMPTS) {
            console.log(`[PANORAMA] Max attempts reached (${MAX_PANORAMA_ATTEMPTS}), showing placeholder`);
            panoDiv.innerHTML = `
                <div style="display:flex;align-items:center;justify-content:center;
                            height:100%;color:var(--muted);text-align:center;">
                    <div>
                        <div style="font-size:48px;">🗺️</div>
                        <div>Панорама недоступна</div>
                        <div style="font-size:12px;">${cityName}</div>
                    </div>
                </div>`;
        }
    }
}

// ===========================
// Сокет-события
// ===========================

// ★ ИСПРАВЛЕНИЕ: duel_found теперь приходит и при переподключении
socket.on('duel_found', function(data) {
    console.log('duel_found received (reconnect):', data);
    
    // Сохраняем данные в sessionStorage для VS-экрана
    if (data.opponent_name) {
        sessionStorage.setItem('opponent_name', data.opponent_name);
    }
    if (data.opponent_id) {
        sessionStorage.setItem('opponent_id', data.opponent_id);
    }
    
    document.getElementById('opponentStatus').textContent = data.opponent_name + ' думает...';
    
    // ★ Триггерим событие для VS-экрана
    window.dispatchEvent(new CustomEvent('duel_data_ready', {
        detail: {
            opponent_id: data.opponent_id,
            opponent_name: data.opponent_name,
            my_user_id: data.my_user_id
        }
    }));
});

socket.on('start_round', function(data) {
    console.log('start_round received:', data);

    const isNewRound = (data.round_number !== currentRound);

    if (!isNewRound && (guessSubmitted || roundFinished)) {
        console.log('[DUEL] Ignoring start_round, round already handled');
        return;
    }

    resetPanoramaState();

    currentRound = data.round_number;
    roundActive = true;
    guessSubmitted = false;
    roundFinished = false;

    document.getElementById('roundPill').textContent = 'Раунд ' + currentRound + '/5';
    document.getElementById('guessBtn').disabled = true;
    document.getElementById('guessBtn').style.display = 'block';
    document.getElementById('opponentStatus').textContent = opponentName + ' думает...';
    document.getElementById('opponentStatus').className = 'opponent-status thinking';

    if (isNewRound) {
        guessLat = null;
        guessLon = null;
        if (myPlacemark && myMap) {
            myMap.geoObjects.remove(myPlacemark);
            myPlacemark = null;
        }
        stopTimer();
        startTimer();
    }

    document.getElementById('roundModal').classList.remove('visible');
    document.getElementById('finishModal').classList.remove('visible');

    loadPanorama(data.search_lat, data.search_lon, data.city);

    console.log(`[DUEL] Round ${currentRound} started (newRound=${isNewRound})`);
});

socket.on('player_moved', function(data) {
    if (data.user_id != myUserId) {
        document.getElementById('opponentStatus').textContent = data.user_name + ' сделал ход';
        document.getElementById('opponentStatus').className = 'opponent-status answered';
    }
});

socket.on('round_result', function(data) {
    roundActive = false;
    roundFinished = true;
    stopTimer();
    resetPanoramaState();

    document.getElementById('guessBtn').disabled = true;

    if (data.total_scores[myUserId] !== undefined) {
        myTotalScore = data.total_scores[myUserId];
    }
    const oppId = Object.keys(data.total_scores).find(id => id != myUserId);
    if (oppId) {
        opponentTotalScore = data.total_scores[oppId] || 0;
    }

    document.getElementById('myScore').textContent = myTotalScore;
    document.getElementById('opponentScore').textContent = opponentTotalScore;

    showRoundResults(data);
});

socket.on('player_ready_next', function(data) {
    if (data.user_id != myUserId) {
        document.getElementById('opponentStatus').textContent = opponentName + ' готов';
        document.getElementById('opponentStatus').className = 'opponent-status answered';
    }
});

socket.on('duel_finished', function(data) {
    stopTimer();
    resetPanoramaState();
    showDuelFinished(data);
});

socket.on('opponent_disconnected', function() {
    stopTimer();
    resetPanoramaState();
    alert('Соперник отключился. Дуэль завершена.');
    window.location.href = '/duel';
});

socket.on('error', function(data) {
    if (data.message === 'Время истекло') {
        document.getElementById('guessBtn').disabled = true;
    }
});

// ===========================
// Таймер
// ===========================
function startTimer() {
    timeLeft = 60;
    updateTimerDisplay();
    clearInterval(timerInterval);
    timerInterval = setInterval(function() {
        timeLeft--;
        updateTimerDisplay();
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            document.getElementById('guessBtn').disabled = true;
            document.getElementById('opponentStatus').textContent = 'Время вышло!';
            document.getElementById('opponentStatus').className = 'opponent-status thinking';
        }
    }, 1000);
}

function stopTimer() { 
    clearInterval(timerInterval); 
}

function updateTimerDisplay() {
    const pill = document.getElementById('timerPill');
    if (!pill) return;
    pill.textContent = timeLeft;
    pill.classList.remove('safe', 'warn', 'danger');
    if (timeLeft <= 10) pill.classList.add('danger');
    else if (timeLeft <= 30) pill.classList.add('warn');
    else pill.classList.add('safe');
}

// ===========================
// Отправка догадки
// ===========================
document.getElementById('guessBtn').addEventListener('click', function() {
    if (!roundActive || guessLat === null || guessSubmitted || roundFinished) return;

    guessSubmitted = true;
    document.getElementById('guessBtn').disabled = true;
    document.getElementById('opponentStatus').textContent = 'Ожидание соперника...';
    document.getElementById('opponentStatus').className = 'opponent-status waiting';

    console.log('Submitting guess:', guessLat, guessLon);
    socket.emit('submit_duel_guess', {
        duel_id: duelId,
        guess_lat: guessLat,
        guess_lon: guessLon
    });
});

// ===========================
// Результаты раунда
// ===========================
function showRoundResults(data) {
    const roundModal = document.getElementById('roundModal');
    if (!roundModal) return;
    roundModal.classList.add('visible');

    setTimeout(function() {
        const resultMapEl = document.getElementById('resultMap');
        if (!resultMapEl) return;
        resultMapEl.innerHTML = '';

        const resultMap = new ymaps.Map('resultMap', {
            center: [data.correct_lat, data.correct_lon],
            zoom: 12,
            controls: ['zoomControl']
        });

        resultMap.geoObjects.add(new ymaps.Placemark(
            [data.correct_lat, data.correct_lon],
            { balloonContent: '📍 ' + data.city, hintContent: 'Правильное место' },
            { preset: 'islands#greenIcon', iconColor: '#3fb950' }
        ));

        const colors = ['#e05a2b', '#f0a500'];
        let allPoints = [[data.correct_lat, data.correct_lon]];

        data.players.forEach(function(player, i) {
            if (player.guess_lat && player.guess_lon) {
                const pc = [player.guess_lat, player.guess_lon];
                allPoints.push(pc);
                resultMap.geoObjects.add(new ymaps.Placemark(pc,
                    { balloonContent: player.name + ': ' + player.score + ' очков', hintContent: player.name },
                    { preset: 'islands#redIcon', iconColor: colors[i] }
                ));
                resultMap.geoObjects.add(new ymaps.Polyline(
                    [pc, [data.correct_lat, data.correct_lon]], {},
                    { strokeColor: colors[i], strokeWidth: 2, strokeOpacity: 0.7, strokeDasharray: '8 4' }
                ));
            }
        });

        if (allPoints.length > 1) {
            try { 
                resultMap.setBounds(resultMap.geoObjects.getBounds(), { 
                    zoomMargin: 50, 
                    checkZoomRange: true 
                }); 
            } catch(e) {
                console.warn('Failed to set map bounds:', e);
            }
        }
    }, 300);

    let html = '<table class="scores-table"><thead><tr><th>Игрок</th><th>Очки</th><th>Всего</th><th>Время</th></tr></thead><tbody>';
    data.players.forEach(function(p) {
        html += `<tr>
            <td>${p.name || 'Игрок'}${p.guess_lat ? '' : ' ⏰'}</td>
            <td class="${p.score >= 4000 ? 'score-high' : p.score >= 2000 ? 'score-med' : ''}">${p.score || 0}</td>
            <td>${data.total_scores[p.user_id] || 0}</td>
            <td>${p.time_taken ? p.time_taken.toFixed(1) + 'с' : '—'}</td>
        </tr>`;
    });
    html += '</tbody></table>';
    
    const scoresContainer = document.getElementById('scoresTableContainer');
    if (scoresContainer) {
        scoresContainer.innerHTML = html;
    }

    const nextBtn = document.getElementById('nextRoundBtn');
    const roundModalTitle = document.getElementById('roundModalTitle');
    
    if (roundModalTitle) {
        roundModalTitle.textContent = data.is_last_round ? '🏁 Финальный раунд' : '📍 Раунд ' + data.round_number;
    }
    if (nextBtn) {
        nextBtn.textContent = data.is_last_round ? 'Завершить дуэль' : 'Следующий раунд →';
        nextBtn.className = data.is_last_round ? 'btn-finish' : 'btn-next';
        nextBtn.disabled = false;
    }
}

function goNextRound() {
    socket.emit('next_round', { duel_id: duelId });
    const nextBtn = document.getElementById('nextRoundBtn');
    if (nextBtn) {
        nextBtn.disabled = true;
        nextBtn.textContent = 'Ожидание соперника...';
    }
    document.getElementById('opponentStatus').textContent = 'Ожидание соперника...';
    document.getElementById('opponentStatus').className = 'opponent-status waiting';
}

function showDuelFinished(data) {
    document.getElementById('roundModal').classList.remove('visible');
    
    const myScore = data.total_scores[myUserId] || myTotalScore;
    const oppId = Object.keys(data.total_scores).find(id => id != myUserId);
    const oppScore = oppId ? (data.total_scores[oppId] || 0) : opponentTotalScore;

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

    document.getElementById('finishTitle').textContent = title;
    document.getElementById('finishContent').innerHTML = content;
    document.getElementById('finishModal').classList.add('visible');
    
    // 🆕 Меняем кнопки в финишном модальном окне
    const finishModal = document.getElementById('finishModal');
    const modalCard = finishModal.querySelector('.modal-card');
    
    // Убираем старые кнопки
    const oldLinks = modalCard.querySelectorAll('a');
    oldLinks.forEach(link => link.remove());
    
    // Добавляем кнопку возврата в лобби (если есть lobby_id)
    if (data.lobby_id) {
        const lobbyBtn = document.createElement('a');
        lobbyBtn.href = '/duel/lobby/' + data.lobby_id;
        lobbyBtn.className = 'btn-finish';
        lobbyBtn.style.cssText = 'display:block;text-align:center;text-decoration:none;';
        lobbyBtn.textContent = '🔄 Вернуться в лобби';
        modalCard.appendChild(lobbyBtn);
    }
    
    // Кнопка в меню дуэлей
    const menuBtn = document.createElement('a');
    menuBtn.href = '/duel';
    menuBtn.className = 'btn-menu';
    menuBtn.style.cssText = 'display:block;text-align:center;text-decoration:none;margin-top:8px;';
    menuBtn.textContent = '📋 В меню дуэлей';
    modalCard.appendChild(menuBtn);
}