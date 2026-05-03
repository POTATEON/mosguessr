// ===========================
// ИГРОВАЯ ЛОГИКА РЕЖИМА "СОЗДАТЕЛЬ"
// ===========================

;(function() {
    'use strict';

    // Получаем визуальные функции из глобальной области
    const visualAPI = window.visualAPI;
    if (!visualAPI) {
        console.error('[GAME] visualAPI not found!');
        return;
    }

    // Используем функции через объект visualAPI, чтобы избежать конфликтов имен
    const showNotification = visualAPI.showNotification;
    const updateTimerDisplay = visualAPI.updateTimerDisplay;
    const updateOpponentStatus = visualAPI.updateOpponentStatus;
    const updatePhase = visualAPI.updatePhase;

    // Получаем данные дуэли
    const duelData = visualAPI.getDuelData();
    const duelId = duelData.duelId;
    const myUserId = duelData.myUserId;
    const opponentName = duelData.opponentName;

    // Проверяем, что данные получены
    if (!duelId || !myUserId) {
        console.error('[GAME] Duel data not found');
        return;
    }

    console.log('[GAME] Initializing game logic...');

    // Socket соединение
    const socket = io();

    // Состояния игры
    let phase = 'creating';
    let selectMap = null;
    let guessMap = null;
    let selectedCoords = null;
    let selectPlacemark = null;
    let guessPlacemark = null;
    let panoramaPlayer = null;
    let previewPlayer = null;
    let timerInterval = null;
    let timeLeft = 60;
    let roundNumber = 1;
    let startCoords = null;

    // Присоединяемся к дуэли
    socket.emit('join_creator_duel', { duel_id: duelId });

    // ===== ИНИЦИАЛИЗАЦИЯ КАРТ =====
    ymaps.ready(() => {
        console.log('[GAME] Yandex Maps API ready');

        // Карта для выбора точки
        selectMap = new ymaps.Map('selectMap', {
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

            document.getElementById('confirmBtn').disabled = false;
            document.getElementById('selectMapHint').style.opacity = '0';
            checkPanorama(coords);
        });

        // Карта для угадывания
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

            document.getElementById('guessBtn').disabled = false;
            document.getElementById('guessMapHint').style.opacity = '0';
        });

        window.selectMap = selectMap;
        window.guessMap = guessMap;
    });

    // ===== ПРОВЕРКА ПАНОРАМЫ =====
    async function checkPanorama(coords) {
        try {
            const panoramas = await ymaps.panorama.locate(coords);

            if (panoramas && panoramas.length > 0) {
                showPanoPreview(panoramas[0]);
                document.getElementById('confirmBtn').disabled = false;
            } else {
                hidePanoPreview();
                document.getElementById('confirmBtn').disabled = true;
                showNotification('Нет панорамы в этой точке', 'error');
            }
        } catch (e) {
            console.error('Panorama check error:', e);
            hidePanoPreview();
            document.getElementById('confirmBtn').disabled = true;
        }
    }

    function showPanoPreview(panorama) {
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

    // Глобальные функции для вызова из HTML
    window.closePanoPreview = hidePanoPreview;

    // ===== ПОДТВЕРЖДЕНИЕ ЛОКАЦИИ =====
    window.confirmLocation = function() {
        console.log('[GAME] Confirming location');

        if (!selectedCoords) {
            socket.emit('creator_location_selected', {
                duel_id: duelId,
                lat: null,
                lon: null
            });
        } else {
            socket.emit('creator_location_selected', {
                duel_id: duelId,
                lat: selectedCoords[0],
                lon: selectedCoords[1]
            });
        }

        document.getElementById('confirmBtn').disabled = true;
        document.getElementById('confirmBtn').textContent = 'Ожидание соперника...';
        updateOpponentStatus('waiting', 'Ожидание соперника...');
        phase = 'waiting';

        if (selectMap) {
            selectMap.behaviors.disable('drag');
            selectMap.behaviors.disable('scrollZoom');
        }
    };

    // ===== ФАЗА УГАДЫВАНИЯ =====
    socket.on('start_guessing_phase', (data) => {
        console.log('[GAME] Starting guessing phase');

        stopTimer();
        phase = 'guessing';
        roundNumber = data.round_number;

        document.getElementById('mainMap').style.display = 'none';
        document.getElementById('gamePano').style.display = 'block';
        document.getElementById('selectMapFloat').classList.remove('visible');
        document.getElementById('guessMapFloat').classList.add('visible');
        document.getElementById('goToStart').style.display = 'block';
        document.getElementById('confirmBtn').classList.add('hidden');

        updatePhase('Угадайте');
        updateOpponentStatus('thinking', opponentName + ' тоже угадывает...');
        hidePanoPreview();

        loadOpponentPanorama(data.lat, data.lon);

        const timeLimit = data.time_limit || 120;
        startTimer(timeLimit);
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
            console.error('[GAME] Failed to load opponent panorama:', e);
        }
    }

    window.returnToStart = function() {
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
    };

    // ===== ОТПРАВКА ДОГАДКИ =====
    window.submitGuess = function() {
        console.log('[GAME] Submitting guess');

        const coords = guessPlacemark ? guessPlacemark.geometry.getCoordinates() : null;

        socket.emit('submit_creator_guess', {
            duel_id: duelId,
            guess_lat: coords ? coords[0] : null,
            guess_lon: coords ? coords[1] : null
        });

        document.getElementById('guessBtn').disabled = true;
        document.getElementById('guessBtn').textContent = 'Ожидание...';
        updateOpponentStatus('waiting', 'Ожидание соперника...');
    };

    // ===== РЕЗУЛЬТАТЫ РАУНДА =====
    socket.on('creator_round_result', (data) => {
        console.log('[GAME] Round results received');

        stopTimer();
        phase = 'results';

        document.getElementById('resultsMapsRow').style.display = 'flex';
        document.getElementById('resultModal').classList.add('visible');
        document.getElementById('resultTitle').textContent = 'Результаты раунда';

        setTimeout(() => {
            document.getElementById('enemyResultMap').innerHTML = '';
            document.getElementById('myResultMap').innerHTML = '';

            const myLoc = data.my_location;
            const enemyGuess = data.enemy_guess;

            const map1 = new ymaps.Map('enemyResultMap', {
                center: myLoc?.lat ? [myLoc.lat, myLoc.lon] : [55.75, 37.62],
                zoom: 12,
                controls: []
            });

            if (myLoc?.lat) {
                map1.geoObjects.add(new ymaps.Placemark(
                    [myLoc.lat, myLoc.lon],
                    { hintContent: 'Твоя локация' },
                    { preset: 'islands#greenIcon', iconColor: '#3fb950' }
                ));

                if (enemyGuess?.lat) {
                    map1.geoObjects.add(new ymaps.Placemark(
                        [enemyGuess.lat, enemyGuess.lon],
                        { hintContent: 'Догадка соперника' },
                        { preset: 'islands#redIcon', iconColor: '#f85149' }
                    ));
                    map1.geoObjects.add(new ymaps.Polyline(
                        [[enemyGuess.lat, enemyGuess.lon], [myLoc.lat, myLoc.lon]],
                        {},
                        { strokeColor: '#f0a500', strokeWidth: 3, strokeOpacity: 1, strokeStyle: 'dash' }
                    ));
                    map1.setBounds(map1.geoObjects.getBounds(), { zoomMargin: 40, checkZoomRange: true });
                }
            }

            const oppLoc = { lat: data.opponent_lat, lon: data.opponent_lon };
            const myGuess = data.my_guess;

            const map2 = new ymaps.Map('myResultMap', {
                center: oppLoc.lat ? [oppLoc.lat, oppLoc.lon] : [55.75, 37.62],
                zoom: 12,
                controls: []
            });

            if (oppLoc.lat) {
                map2.geoObjects.add(new ymaps.Placemark(
                    [oppLoc.lat, oppLoc.lon],
                    { hintContent: 'Локация соперника' },
                    { preset: 'islands#greenIcon', iconColor: '#3fb950' }
                ));

                if (myGuess?.lat) {
                    map2.geoObjects.add(new ymaps.Placemark(
                        [myGuess.lat, myGuess.lon],
                        { hintContent: 'Твоя догадка' },
                        { preset: 'islands#redIcon', iconColor: '#f85149' }
                    ));
                    map2.geoObjects.add(new ymaps.Polyline(
                        [[myGuess.lat, myGuess.lon], [oppLoc.lat, oppLoc.lon]],
                        {},
                        { strokeColor: '#f0a500', strokeWidth: 3, strokeOpacity: 1, strokeStyle: 'dash' }
                    ));
                    map2.setBounds(map2.geoObjects.getBounds(), { zoomMargin: 40, checkZoomRange: true });
                }
            }

            let html = '<table class="scores-table"><thead><tr><th>Игрок</th><th>Дистанция</th><th>Очки</th></tr></thead><tbody>';
            data.players.forEach(p => {
                const cls = p.score >= 4000 ? 'score-high' : p.score >= 2000 ? 'score-med' : '';
                html += `<tr><td>${p.name} ${p.user_id === myUserId ? '(Вы)' : ''}</td><td>${p.distance ? p.distance.toFixed(2) + ' км' : '—'}</td><td class="${cls}">${p.score || 0}</td></tr>`;
            });
            html += '</tbody></table>';
            document.getElementById('scoresTableContainer').innerHTML = html;

            const btn = document.getElementById('nextRoundBtn');
            btn.textContent = data.is_last_round ? 'Завершить' : 'Следующий раунд →';
            btn.style.display = 'block';
            btn.disabled = false;
        }, 300);
    });

    // ===== СЛЕДУЮЩИЙ РАУНД =====
    window.goNextRound = function() {
        console.log('[GAME] Next round');

        socket.emit('next_creator_round', { duel_id: duelId });
        document.getElementById('resultModal').classList.remove('visible');
        document.getElementById('nextRoundBtn').disabled = true;
        resetForNextRound();
    };

    function resetForNextRound() {
        phase = 'creating';

        document.getElementById('mainMap').style.display = 'block';
        document.getElementById('gamePano').style.display = 'none';
        document.getElementById('gamePano').innerHTML = '';
        document.getElementById('selectMapFloat').classList.add('visible');
        document.getElementById('guessMapFloat').classList.remove('visible');
        document.getElementById('goToStart').style.display = 'none';
        document.getElementById('confirmBtn').classList.remove('hidden');

        document.getElementById('confirmBtn').disabled = true;
        document.getElementById('confirmBtn').textContent = '✅ Подтвердить точку';
        document.getElementById('guessBtn').disabled = true;
        document.getElementById('guessBtn').textContent = '🎯 Угадать';

        updatePhase('Выберите точку');
        updateOpponentStatus('thinking', 'Соперник выбирает...');

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

        if (selectMap) {
            selectMap.behaviors.enable('drag');
            selectMap.behaviors.enable('scrollZoom');
        }

        startTimer(60);
    }

    // ===== ЗАВЕРШЕНИЕ ДУЭЛИ =====
    socket.on('duel_finished', (data) => {
        console.log('[GAME] Duel finished');

        stopTimer();

        const myScore = data.total_scores[myUserId] || 0;
        const oppId = Object.keys(data.total_scores).find(id => id != myUserId);
        const oppScore = oppId ? (data.total_scores[oppId] || 0) : 0;

        let title;
        if (myScore > oppScore) title = '🏆 Вы победили!';
        else if (oppScore > myScore) title = '😞 Вы проиграли';
        else title = '🤝 Ничья!';

        document.getElementById('resultsMapsRow').style.display = 'none';
        document.getElementById('resultModal').classList.add('visible');
        document.getElementById('resultTitle').textContent = title;

        let buttonsHtml = `
            <p style="font-size:64px;font-family:'Bebas Neue',sans-serif;text-align:center;margin:20px 0;">
                ${myScore} : ${oppScore}
            </p>
            <button class="btn-next" onclick="window.location.href='/duel'">
                📋 В меню дуэлей
            </button>
        `;

        if (data.lobby_id) {
            buttonsHtml += `
                <button class="btn-next" style="background: var(--green); margin-top: 8px;"
                        onclick="window.location.href='/duel/lobby/${data.lobby_id}'">
                    🔄 Вернуться в лобби
                </button>
            `;
        }

        document.getElementById('scoresTableContainer').innerHTML = buttonsHtml;
        document.getElementById('nextRoundBtn').style.display = 'none';
    });

    // ===== ТАЙМЕР =====
    function startTimer(seconds) {
        stopTimer();
        timeLeft = seconds;
        updateTimerDisplay(timeLeft);

        console.log(`[GAME] Timer started: ${seconds}s`);

        timerInterval = setInterval(() => {
            timeLeft--;
            updateTimerDisplay(timeLeft);

            if (timeLeft <= 0) {
                stopTimer();
                console.log(`[GAME] Timer expired in phase: ${phase}`);

                if (phase === 'creating') {
                    window.confirmLocation();
                } else if (phase === 'guessing') {
                    window.submitGuess();
                }
            }
        }, 1000);
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
            console.log('[GAME] Timer stopped');
        }
    }

    // ===== СЛУЖЕБНЫЕ СОБЫТИЯ =====
    socket.on('opponent_selected_location', () => {
        updateOpponentStatus('answered', opponentName + ' выбрал точку');
    });

    socket.on('opponent_guessed', () => {
        updateOpponentStatus('answered', opponentName + ' сделал догадку');
    });

    socket.on('time_expired', (data) => {
        stopTimer();
        showNotification(data.message || 'Время истекло', 'warning');

        if (data.phase === 'selection' && phase === 'creating') {
            window.confirmLocation();
        } else if (data.phase === 'guessing' && phase === 'guessing') {
            window.submitGuess();
        }
    });

    socket.on('error', (data) => {
        alert(data.message);
    });

    socket.on('opponent_disconnected', () => {
        stopTimer();
        alert('Соперник отключился');
        window.location.href = '/duel';
    });

    // ===== ЗАПУСК ИГРЫ =====
    console.log('[GAME] Starting game with 60s timer');
    startTimer(60);

})(); // Заворачиваем в IIFE для изоляции области видимости