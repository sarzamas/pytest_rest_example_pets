"""session_data.py"""

from dataclasses import dataclass, field

from libs.api.airflow.helpers import get_local_time, parse_pytest_nodeid, get_debug_flag


@dataclass
class BaseTiming:
    """Базовый класс для работы с таймингами"""
    start_time: str | None = None
    start_timestamp: float | None = None
    end_time: str | None = None
    end_timestamp: float | None = None
    duration: float = 0.0

    def start(self) -> None:
        """Зафиксировать время начала"""
        now = get_local_time()
        self.start_time = now.strftime("%Y-%m-%d %H:%M:%S")
        self.start_timestamp = now.timestamp()

    def stop(self) -> None:
        """Зафиксировать время окончания и длительность"""
        now = get_local_time()
        self.end_time = now.strftime("%Y-%m-%d %H:%M:%S")
        self.end_timestamp = now.timestamp()
        if self.start_timestamp is not None:
            self.duration = round(self.end_timestamp - self.start_timestamp, 2)


@dataclass
class TestTiming(BaseTiming):
    """Тайминги выполнения теста"""


@dataclass
class SessionTiming(BaseTiming):
    """Тайминги выполнения тестовой сессии"""


@dataclass
class TestData:
    """Данные отдельного теста"""
    module: str
    class_name: str | None
    test_name: str
    timing: TestTiming = field(default_factory=TestTiming)
    _status: str | None = field(default=None, init=False)
    meta: dict[str, str] = field(default_factory=dict)
    steps: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @property
    def status(self) -> str | None:
        """Геттер для статуса"""
        return self._status

    @status.setter
    def status(self, value: str | None) -> None:
        """Сеттер с преобразованием в UPPERCASE"""
        self._status = value.upper() if value is not None and isinstance(value, str) else None


@dataclass
class SessionData:
    """Данные тестовой сессии"""
    session: SessionTiming = field(default_factory=SessionTiming)
    debug: bool = field(default_factory=get_debug_flag)
    pytest_debug: bool = False
    tests: dict[str, TestData] = field(default_factory=dict)

    def add_test(self, nodeid: str) -> TestData:
        """Добавляет тест с разбором nodeid"""
        module, class_name, test_name = parse_pytest_nodeid(nodeid)
        test_data = TestData(
            module=module,
            class_name=class_name,
            test_name=test_name
        )
        self.tests[nodeid] = test_data
        return test_data
