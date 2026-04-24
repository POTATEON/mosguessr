self.addEventListener('install', (event) => {
    console.log('[SW] Установлен');
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('[SW] Активирован');
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Перехватываем все запросы к API панорам
    if (url.hostname.includes('api-maps.yandex.ru') &&
        url.pathname.includes('/panoramas/')) {

        console.log('[SW] Перехвачен запрос:', url.searchParams.toString().substring(0, 80));

        event.respondWith(
            fetch(event.request)
                .then(response => {
                    if (!response.ok) {
                        console.log('[SW] Пропущен (статус ошибки):', response.status);
                        return response;
                    }

                    const clonedResponse = response.clone();

                    return clonedResponse.text().then(text => {
                        // Определяем тип ответа
                        const isJSONP = text.startsWith('/**/') || text.trim().startsWith('id_');
                        const isJSON = text.trim().startsWith('{');

                        console.log('[SW] Тип ответа:', isJSONP ? 'JSONP' : isJSON ? 'JSON' : 'другой');

                        // Модифицируем только JSON-ответы (не JSONP)
                        if (isJSON) {
                            let modified = text;

                            // Удаляем маркеры
                            if (/"Markers"\s*:\s*\[.*?\]/gs.test(modified)) {
                                modified = modified.replace(/"Markers"\s*:\s*\[.*?\]/gs, '"Markers":[]');
                                console.log('[SW] Маркеры удалены');
                            }

                            // Удаляем компании
                            if (/"Companies"\s*:\s*\[.*?\]/gs.test(modified)) {
                                modified = modified.replace(/"Companies"\s*:\s*\[.*?\]/gs, '"Companies":[]');
                                console.log('[SW] Компании удалены');
                            }

                            return new Response(modified, {
                                status: response.status,
                                statusText: response.statusText,
                                headers: response.headers
                            });
                        }

                        // Пропускаем JSONP без изменений
                        console.log('[SW] JSONP пропущен без изменений');
                        return response;
                    });
                })
                .catch(error => {
                    console.error('[SW] Ошибка:', error);
                    return fetch(event.request);
                })
        );
    }
});