### Блок схема платформы E2E

```
                       [Параметризация] 
                  Фикстуры передают данные в тест,
              Тест может требовать специфичные фикстуры
    ┌───────────────────┐           ┌───────────────────┐
    │ Тестовые фикстуры │           │ Тестовые сценарии:│
    │ (Подготовка:      │──────────>│(Сценарии из шагов,│         [Вызов шагов сценария переходы состояний] 
    │  - Данные         │◄──────────│ Проверки шагов,   │<────────────────────────────────────────────────┐
    │  - Клиенты        │           │ Отчет по шагам)   │                                                 │
    │  - Конфигурация)  │           └─────────▲─────────┘                                                 │
    └─────────────┬───┬─┘                     │                                                           │
                  │   │                       │       [Set-Up Session TearDown]                           │
          [Set-Up │   └───────────────────────│───────────────────────────────┐                           │
          Session │     [Вызов шагов сценария │                               │                           │
        TearDown] │       переходы состояний] │                               │                           │
    ┌─────────────│───────────────────────────│──────────┐      ┌─────────────│───────────────────────────│──────────┐
    │ Stateless   ▼  API-клиент (AirFlowAPI)  ▼          │      │ Stateless   ▼   Storage-клиент (HDFS)   ▼          │
    │  ┌───────────────────┐        ┌─────────────────┐  │      │  ┌───────────────────┐        ┌─────────────────┐  │
    │  │      Client       │───────>│      Steps      │  │      │  │      Client       │───────>│      Steps      │  │
    │  │ (HTTP-логика)     │<───────┤ (Методы-шаги)   │  │      │  │ (Mixin-логика)    │<───────┤ (Методы-шаги)   │  │
    │  └──────┬───▲────────┘        └─────────▲───────┘  │ ...  │  └──────┬───▲────────┘        └─────────▲───────┘  │
    │         │   │                           │          │      │         │   │                           │          │
    └─────────┬───│───────────────────────────│──────────┘      └─────────┬───│───────────────────────────│──────────┘
              │   │                           │                           │   │                           │           
     [Методы] │   │           [Чтение/запись] │                 [Методы]  │   │           [Чтение/запись] │           
              ▼   │                           │                           ▼   │                           │           
    ┌───────────────────┐                     │                   ┌───────────────────┐                   │
    │ Внешние API SUT.  │                     │                   │ Внешние API SUT.  │                   │
    │   (Request /      │                     │                   │   (Request /      │                   │
    │   Response)       │                     │                   │   Response)       │                   │
    └───────────────────┘                     │                   └───────────────────┘                   │
                                              │                                                           │
                                              │                                                           │
                                              │              ┌──────────────────────┐                     │
                                              │              │    Data Collector    │                     │
                                              └─────────────>│  (Statefull Schema)  │<────────────────────┘
                                                             │                      │
                                                             └──────────▲───────────┘
                                                                        │
                                                                        ▼
                                                          ┌─────────────────────────────┐
                                                          │  Schema:   Session Data     │
                                                          │ (fields: states, timestamps,│
                                                          │      user_id, tokens)       │
                                                          └─────────────────────────────┘

```

### Структура файлов:

```
project/
├── libs/
│   ├── core/                  # Новый модуль для общих компонентов
│   │   ├── data_collector.py  # Data Collector (методы: хранение состояния)
│   │   └── session_data.py    # Session Data (dataclass_singleton: конфигурация, параметры сессии)
│   │
│   ├── api/
│   │   ├── airflow/
│   │   │   ├── client.py    # Класс APIClient (методы: Stateless-логика)
│   │   │   └── steps.py     # Класс BusinessSteps (шаги: dag_control, start_task, check_task, ...)
│   │   ├── nifi/
│   │   │   ├── client.py    # Класс APIClient (методы: Stateless-логика)
│   │   │   └── steps.py     # Класс BusinessSteps (шаги: processor_control, start_processor, check_processor, ...)
│   │   └── ...
:   :
:   :
│   ├── db/
│   │   ├── client.py        # Класс DBClient
│   │   └── steps.py         # Класс BusinessSteps
│   │
│   └── drivers/
│       ├── client.py        # Класс StorageClient
│       └── steps.py         # Класс BusinessSteps
:
:
├── tests/
├── conftest.py          # Фикстуры для создания окружения и подготовки данных
├── test_flow_1.py       # Тесты, использующие BusinessSteps
:                          - шаг можно экспортировать в TestIt/Allure через @decorator или контекстный менеждер
├── test_flow_n.py       # Тесты, использующие BusinessSteps
└── ...
```

#### steps.py

- Зачем:
-
    - Тесты состоят из последовательности шагов которые удобно оборачивать для репортинга в TMS (через декоратор или
      контекстный менеджер)
    - Тесты инициируют переходы между состояниями систем(ы) через выполнение шагов (частей сценария)
    - Шаги реализуют бизнес логику перехода между состояниями и оценки состояния систем(ы)
    - Шаги могут быть Stateless (без использования контекста сессии) и Stateful (использующие контекст)
    - По окончании шага производится (либо самим шагом либо тестом) transition-проверка, валидирующая корректность
      перехода состояния

- Использование:
-
    - нужны фикстурам и тестам
    - методы шагов расширяемы по мере необходимости
- Размещение:
-
    - У каждого клиента участвующего в E2E сценарии реализуется свой класс Steps в его папке

#### data_collector.py:

- Зачем:
-
    - Класс DataCollector - экземпляр-Синглтон, содержащий методы реализации хранения сессионных данных
-
    - менеджер параметров Stateful состояний сессии  (states, timestamps, polling_results, ...)
-
    - Mockk/Stub нереализованной бизнес логики компонентом клиента (замещение и подстановка в Steps)
- Использование - нужен в шагах (Steps) и в тестах, фикстурах
- Размещение: в libs/core/ делает его доступным для всех модулей без циклических зависимостей

#### session_data.py:

- Зачем:
-
    - Data-Класс SessionData - схема реализующая структуру хранения данных
- Использование - нужен для DataCollector для адресации при хранении данных
- Размещение: libs/core/ рядом с DataCollector

### Преимущества такого подхода:

#### Модульность:

- Тесты, Клиенты, Steps и DataCollector разделены, но легко интегрируются
- Комбинация Stateless и Stateful подходов в рамках одного сценария
- Переходы между этапами и их валидация централизованы, что снижает риск ошибок в сложной бизнес-логике

#### Доступность:

- DataCollector - Singleton - доступен в единственном экземпляре на всех уровнях (шаги, тесты, фикстуры)
-
    - изоляция тестов при использовании синглтона обеспечивается адресацией предоставляемой Pytest через nodeid
  - для большей защиты состояний использовать UpdatableSingleton (имеет метод _validate())

- SessionData - расширяемая структура dataclass - схема для хранения данных

- Размещение: libs/core не зависит от tests - обработка данных отделена от тестов, что соответствует чистой архитектуре

#### Масштабируемость:

- Добавление новых клиентов не требует изменений в DataCollector (только расширение в схеме SessionData)
- Переиспользование Steps в различных тестовых сценариях

### Список терминов:

1. Пошаговый сценарий — последовательность шагов, инкапсулирующих бизнес-логику (data-flow) через *Клиентов* (
   инструменты взаимодействия с внешними системами) и *Шаги*
2. Stateless-клиенты реализуют методы получая параметры от Steps (и ?Фикстур?)
3. Stateless-шаги выполняются изолированно от контекста
4. Stateful-шаги сохраняют контекст между состояниями (используют данные из DataCollector)
5. DataCollector — централизованное хранилище, фиксирующее результаты шагов для обеспечения согласованности состояний
6. Transition-проверка — валидации корректности перехода между состояниями системы тестом после выполнения шага
