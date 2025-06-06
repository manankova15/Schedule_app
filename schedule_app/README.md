# Расписание Областной Больницы

Система автоматизации процесса составления оптимального расписания для работников областной больницы Воронежа с визуализацией в веб-приложении.

## Описание проекта

Курсовая работа: автоматизация процесса составления оптимального расписания для работников областной больницы Воронежа с визуализацией в веб-приложении.

### Факторы, влияющие на составление расписания

1. Индивидуальные особенности сотрудников:
   - квалификация и специализация (кто на каких аппаратах может работать);
   - количество ставок (полная, неполная занятость);
   - предпочтения по сменам (желание работать в определённые дни или время суток);
   - личные запросы (дни, когда сотрудник хочет не работать, с указанием причины и важности события).

2. Производственные требования:
   - необходимое количество сотрудников в смену для обеспечения бесперебойной работы отделений;
   - распределение нагрузки между сотрудниками для предотвращения перегрузок;
   - учёт работы оборудования (когда какие аппараты доступны для использования).

3. Ограничения по времени работы:
   - максимальное количество рабочих часов в смену и в месяц;
   - перерывы между сменами;
   - учёт отпусков, больничных и других периодов отсутствия сотрудников.

## Технологии

- **Backend**: Django, Django REST Framework
- **Database**: PostgreSQL
- **Frontend**: Django Templates, Bootstrap 5, JavaScript

## Установка и запуск

### С использованием Docker или Podman

1. Установите Docker или Podman и Podman Compose
2. Клонируйте репозиторий
3. Создайте `.env` файл по аналогии с .env.example

Далее при использовании Docker вместо Podman прописывайте стандартные команды (например, docker-compose up -d --build)

4. Остановите существующие контейнеры, если они запущены:

```bash
podman-compose down
```
Если podman-compose недоступен, установите его:

```bash
pip install podman-compose
```

или

```bash
brew install podman-compose
```

5. Запустите приложение:

```bash
podman-compose up -d --build
```

6. Проверьте статус контейнеров:

```bash
podman-compose ps
```

7. Если контейнер backend не запущен, проверьте логи:

```bash
podman-compose logs backend
```

8. Приложение будет доступно по адресу: http://localhost:8000 или http://localhost

### Локальная установка

1. Клонируйте репозиторий
2. Создайте и активируйте виртуальное окружение:

```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
venv\Scripts\activate     # для Windows
```

3. Установите зависимости:

```bash
pip install -r backend/requirements.txt
```

4. Создайте файл `.env` на основе `.env.example`
5. Примените миграции:

```bash
cd backend
python manage.py migrate
```

6. Создайте суперпользователя:

```bash
python manage.py createsuperuser
```

7. Запустите сервер разработки:

```bash
python manage.py runserver
```

8. Приложение будет доступно по адресу: http://localhost:8000

## Функциональность

### Для сотрудников
1. Просмотр текущего графика работ:
   - календарь с отображением смен, в которые сотрудник работает (в разрезе по месяцам и по неделям).
   - старый календарь за прошедшие месяца.

2. Указание дней, когда сотрудник хочет не работать:
   - форма для ввода дат с причинами и важностью события (например, отпуск, больничный, важное личное событие);
   - возможность сохранения и отправки запроса на согласование старшей.
   - просмотр согласований от старшей

3. Личный кабинет:
   - просмотр и редактирование личной информации;
   - изменение пароля;
   - восстановление пароля при необходимости.

### Для старшей
1. Согласование отпусков и личных запросов сотрудников:
   - список запросов от сотрудников с возможностью просмотра причин и важности;
   - кнопки для одобрения или отклонения запросов.
   - изменение важности события, указанного сотрудником (можно как повысить, так и понизить) (всего есть 3 категории - низкая, средняя, высокая)

2. Генерация расписания на новый месяц:
   - кнопка для запуска алгоритма генерации расписания;
   - отображение сгенерированного расписания в виде календаря или таблицы.

3. Изменение уже сгенерированного расписания:
   - возможность ручного редактирования расписания (добавление и удаление смен);
   - инструменты для перегенерации графика на оставшийся период месяца при необходимости.

4. Дополнительные функции:
   - управление сотрудниками (добавление, редактирование, удаление);
   - управление оборудованием (добавление, редактирование, удаление);
   - управление доступностью сотрудников по сменам (только утренняя, только дневные, любые).

## Алгоритм генерации расписания

Для генерации оптимального расписания используется алгоритм на основе теории графов:

1. Создается двудольный граф, где одна часть - сотрудники, другая - смены.
2. Ребра между сотрудниками и сменами создаются с учетом:
   - квалификации сотрудника (может ли работать на данном оборудовании);
   - доступности сотрудника (нет ли одобренных запросов на отгул);
   - необходимого отдыха между сменами (минимум 3 дня);
   - количества уже назначенных смен (для соблюдения ставки);
   - доступности сотрудника по сменам (только утренняя, только дневные, любые).
3. Веса ребер устанавливаются в зависимости от уровня навыка (основной или дополнительный).
4. Применяется алгоритм поиска минимального стоимостного потока для оптимального назначения сотрудников на смены.

## Смены и их времена

В системе предусмотрены следующие типы смен:
- Утренняя смена: 8:00-14:00
- Вечерняя смена: 14:00-20:00
- Ночная смена: 20:00-8:00 (следующего дня)

## Аутентификация

В системе используется аутентификация по email вместо имени пользователя. Пароли хранятся в зашифрованном виде. Предусмотрена возможность восстановления пароля через email.