# CLAUDE.md — Инструкция для AI-агентов

## Что это за проект

Инвест Dashboard — статический HTML-дашборд для отслеживания ETF-портфеля (SWRD, EIMI, USSC).
Хостится на **GitHub Pages**: https://nawka.github.io/invest-dashboard/

## Структура файлов

```
index.html              ← ГЛАВНЫЙ файл дашборда (GitHub Pages отдаёт его)
dashboard/index.html    ← Копия для локальной разработки (пути к data/ отличаются: ../data/)
data/
  prices.js             ← Текущие цены ETF (auto-generated, обновляется GitHub Actions)
  prices.json           ← То же в JSON-формате
  portfolio.json        ← Портфель: холдинги, транзакции, DCA-план, метаданные
docs/
  investment-plan-v3.md ← Инвестиционный план v3.0
scripts/
  server.py             ← Локальный сервер (опционален, для разработки)
  buy_calculator.py     ← CLI-калькулятор покупок
.github/workflows/
  update-prices.yml     ← GitHub Actions: автообновление цен ежедневно в 17:00 UTC
```

## Как работают цены

1. **При загрузке страницы**: загружаются из `data/prices.js` + автоматически запрашиваются свежие с Yahoo Finance через CORS-прокси
2. **Кнопка "Обновить цены"**: клиентский fetch через CORS-прокси (allorigins, corsproxy.io), НЕ требует сервера
3. **GitHub Actions**: каждый рабочий день в 17:00 UTC обновляет `prices.js`, `prices.json`, `portfolio.json` и пушит

**ВАЖНО**: НЕ откатывай клиентский fetch (функция `refreshPrices` с `fetchYahooPrice`) обратно на серверный `/api/prices`. Кнопка должна работать без сервера.

## Git и деплой

- **Репозиторий**: https://github.com/naWka/invest-dashboard
- **Ветка**: `main`
- **GitHub Pages**: автодеплой из `main`, корень `/`
- После каждого пуша в `main` GitHub Pages автоматически обновляется (~1-2 мин)

### Как пушить изменения

**Токен хранится в файле `.github-token`** (он в `.gitignore`, в репо НЕ попадает).

Перед первым пушем в новой сессии настрой remote:
```bash
TOKEN=$(cat .github-token | tr -d '[:space:]')
git remote set-url origin https://x-access-token:${TOKEN}@github.com/naWka/invest-dashboard.git
# Или если remote ещё нет:
# git remote add origin https://x-access-token:${TOKEN}@github.com/naWka/invest-dashboard.git
```

Затем пуш как обычно:
```bash
git add -A
git commit -m "описание изменений"
git push
```

**ВАЖНО**: Никогда не коммить `.github-token` — он в `.gitignore`. Не выводи содержимое токена в чат.

## При внесении изменений в index.html

1. Редактируй **корневой** `index.html` (НЕ `dashboard/index.html`)
2. После изменений скопируй его в dashboard:
   ```bash
   cp index.html dashboard/index.html
   sed -i 's|src="data/prices.js"|src="../data/prices.js"|' dashboard/index.html
   ```
3. Коммить и пуш

## Ключевые архитектурные решения (не ломай!)

- `index.html` в корне проекта — для GitHub Pages
- Клиентский fetch цен через CORS-прокси — для работы без сервера
- `refreshPrices()` вызывается автоматически при загрузке страницы
- Два варианта `index.html`: корневой (пути `data/...`) и dashboard/ (пути `../data/...`)
- GitHub Actions обновляет `data/prices.js` автоматически каждый рабочий день
