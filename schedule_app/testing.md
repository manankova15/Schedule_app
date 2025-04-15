# Тестирование проекта "Система составления расписания для Областной больницы Воронежа"

## Инструкция по запуску проекта через Docker

1. Клонируйте репозиторий:
   ```bash
   git clone <url-репозитория>
   cd schedule_app
   ```

2. Создайте файл .env на основе .env.example:
   ```bash
   cp .env.example .env
   ```

3. Запустите проект с помощью Docker Compose:
   ```bash
   docker-compose up -d
   ```

4. Если возникают проблемы при сборке, попробуйте пересобрать контейнеры:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

5. Приложение будет доступно по адресу:
   - Frontend: http://localhost
   - Backend API: http://localhost/api/
   - Django Admin: http://localhost/admin/

## Временная инструкция для тестирования без постоянного перезапуска Docker

Поскольку перезапуск Docker Compose занимает много времени, для быстрого тестирования и разработки рекомендуется использовать локальное окружение:

### Запуск Backend (Django)

1. Установите PostgreSQL локально и создайте базу данных:
   ```bash
   # Для Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   sudo -u postgres createdb hospital_db
   
   # Для macOS (с использованием Homebrew)
   brew install postgresql
   createdb hospital_db
   ```

2. Создайте и активируйте виртуальное окружение Python:
   ```bash
   cd backend
   python -m venv venv
   
   # Для Linux/macOS
   source venv/bin/activate
   
   # Для Windows
   venv\Scripts\activate
   ```

3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

4. Создайте файл .env в директории backend/ со следующим содержимым:
   ```
   DEBUG=True
   SECRET_KEY=your-secret-key-here
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   POSTGRES_DB=hospital_db
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=password
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   ```

5. Примените миграции и создайте суперпользователя:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. Запустите сервер разработки:
   ```bash
   python manage.py runserver
   ```

7. Django API будет доступен по адресу http://localhost:8000/api/

### Запуск Frontend (React)

1. Откройте новый терминал и перейдите в директорию frontend:
   ```bash
   cd frontend
   ```

2. Установите зависимости:
   ```bash
   npm install
   ```

3. Создайте файл .env в директории frontend/ со следующим содержимым:
   ```
   REACT_APP_API_URL=http://localhost:8000/api/
   ```

4. Запустите сервер разработки:
   ```bash
   npm start
   ```

5. React приложение будет доступно по адресу http://localhost:3000

### Преимущества локального запуска для разработки и тестирования

1. **Быстрая перезагрузка**: Изменения в коде автоматически применяются без необходимости перезапуска контейнеров.
2. **Отладка**: Легче отлаживать код с использованием инструментов разработчика.
3. **Производительность**: Локальный запуск обычно быстрее, чем запуск в контейнерах.
4. **Независимость**: Можно работать над фронтендом и бэкендом независимо.

### Переключение между локальной разработкой и Docker

Когда вы закончите тестирование и разработку в локальном окружении, вы можете запустить полное приложение в Docker для проверки интеграции всех компонентов:

```bash
# Остановите локальные серверы (Ctrl+C в терминалах)
# Запустите Docker Compose
docker-compose up -d
```

Это позволит вам быстро разрабатывать и тестировать отдельные компоненты локально, а затем проверять полную интеграцию в Docker.