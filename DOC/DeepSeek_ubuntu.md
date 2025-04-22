# Инструкция для Ubuntu 24.04: Запуск DeepSeek-R1 1.5B через Page Assist

---

### 1. Установка системных зависимостей

```bash
sudo apt update && sudo apt upgrade -y  
sudo apt install -y python3 python3-venv python3-pip git git-lfs curl  
git lfs install  # Для загрузки моделей через Git LFS
```

---

### 2. Скачивание модели

- Получите токен доступа [Hugging Face](https://huggingface.co)
    - Перейдите → Hugging Face → User Profile → Access Tokens
    - Создайте токен с правами read (требуется для git clone).

DeepSeek-R1 — **бесплатная модель, токены для работы не требуются**:

Получить ссылки для клонирования
нужной [версии](https://huggingface.co/collections/deepseek-ai/deepseek-r1-678e1e131c0169c0bc89728d)

```bash
mkdir -p ~/models && cd ~/models  
git clone https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B # заменить на ссылку нужной версии
# или с login:
git clone https://ВАШ_USERNAME:ВАШ_ТОКЕН@huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
# или c progress-bar:
GIT_TRACE=2 GIT_CURL_VERBOSE=1 GIT_LFS_PROGRESS=1 \
git -c http.version=HTTP/2 clone -v --progress \
https://ВАШ_USERNAME:ВАШ_ТОКЕНhuggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
```

Модель сохранена в git в формате .safetensors

Архитектура должна быть указана в config.json: "Qwen2ForCausalLM"

```bash
cat ~/models/DeepSeek-R1-Distill-Qwen-1.5B/config.json | grep -A 5 architectures
```

Если поле architectures отсутствует в config.json:

Создайте в репе файл `model_index.json` вручную:

```bash
echo '{"architectures": ["Qwen2ForCausalLM"], "model_type": "qwen2"}' > ~/models/DeepSeek-R1-Distill-Qwen-1.5B/model_index.json
```

```json
{
  "architectures": ["Qwen2ForCausalLM"], 
  "model_type": "qwen2"
}
```

---

### 3. Настройка окружения

```bash
cd ~  
python3 -m venv deepseek-env  
source ~/deepseek-env/bin/activate
# для выключения venv:
deactivate
```

---

### 4. Установка Python-пакетов

```bash
pip install --upgrade transformers accelerate sentencepiece uvicorn python-multipart bitsandbytes huggingface_hub
pip install --upgrade fastapi starlette[standard]
pip install --upgrade torch torchvision torchaudio
```

---

### 5. Переменные окружения

- **Для локального использования** (опционально):


- **Для серверов** (если модель не в ~/models и есть GPU с поддержкой CUDA):

  ```bash
  export MODEL_PATH="/полный/путь/к/DeepSeek-R1-Distill-Qwen-1.5B" # НЕ задавать при локальном запуске (будет определено в `api.py` по умолчанию)

  export USE_8BIT=1  # Активировать 8-битную оптимизацию памяти ТОЛЬКО при наличии GPU с поддержкой CUDA
  ```

- **Примечание**: `HUGGINGFACE_TOKEN` **не требуется** для DeepSeek-R1 (только для приватных моделей).

---

### 6. Создание API

Создайте файл `api.py`:

```bash
nano ~/api.py
```

Вставьте следующий код:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from safetensors import safe_open
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoConfig
import torch
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = os.getenv("MODEL_PATH", os.path.expanduser("~/models/DeepSeek-R1-Distill-Qwen-1.5B"))

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

config = AutoConfig.from_pretrained(MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",  # Автовыбор GPU/CPU
    torch_dtype=torch.float16,
    config=config,
    # load_in_8bit=bool(os.getenv("USE_8BIT", False))  # Активировать при нехватке ОЗУ¹ при наличии GPU с поддержкой CUDA
)


class Query(BaseModel):
    text: str


@app.post("/generate")
async def generate(query: Query):
    inputs = tokenizer(query.text, return_tensors="pt").to(model.device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=200,
        do_sample=True,
        temperature=0.9,
        top_p=0.9
    )

    return {"response": tokenizer.decode(outputs[0], skip_special_tokens=True)}
```

---

### 7. Запуск сервера

```bash
cd ~  
uvicorn api:app --reload --port 8000 --host 0.0.0.0
```

- **На сервере** (фоновый режим):

  ```bash
  nohup uvicorn api:app --port 8000 --host 0.0.0.0 > server.log 2>&1 &
  ```

---

### 8. Пример кода клиента

```python
import requests
from typing import Optional


def generate_text(
        prompt: str,
        api_url: str = "http://localhost:8000/generate",
        timeout: Optional[float] = 30.0
) -> str:
    """
    Отправляет текстовый запрос на сервер генерации текста и возвращает ответ.

    Параметры:
    ----------
    prompt : str
        Входной текст/промпт для генерации. Модель будет пытаться продолжить
        или ответить на этот текст. Максимальная длина ограничена конфигурацией
        сервера.
        
    api_url : str, optional
        URL endpoint API сервера. По умолчанию:
        'http://localhost:8000/generate'
        
    timeout : float, optional
        Максимальное время ожидания ответа от сервера в секундах.
        По умолчанию 30.0

    Возвращает:
    -------
    str
        Сгенерированный текст ответа. Сервер автоматически обрезает специальные
        токены и возвращает только содержательную часть ответа.

    Исключения:
    ----------
    RuntimeError
        В случае проблем с подключением, таймаута или невалидного ответа

    Пример:
    ------
    >>> generate_text("Как работает гравитация?")
    'Гравитация — это фундаментальное взаимодействие...'
    
    Примечания:
    ----------
    Параметры генерации (max_new_tokens=200, temperature=0.9, top_p=0.9)
    фиксированы на стороне сервера. Для их изменения требуется модификация
    API сервера.
    """
    try:
        response = requests.post(
            url=api_url,
            json={"text": prompt},
            timeout=timeout
        )
        response.raise_for_status()

        if "response" not in response.json():
            raise ValueError("Некорректный формат ответа от сервера")

        return response.json()["response"]

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ошибка соединения с API: {str(e)}") from e
    except (KeyError, ValueError) as e:
        raise RuntimeError(f"Ошибка обработки ответа: {str(e)}") from e


# Пример использования
if __name__ == "__main__":
    try:
        response = generate_text("Объясни теорию относительности простыми словами")
        print("Ответ сервера:", response)
    except RuntimeError as e:
        print(f"Ошибка: {str(e)}")
```

---

### 9. Интеграция с Page Assist для взаимодействия через браузер

1. Установите расширение **[Page Assist](https://chrome.google.com/webstore/detail/page-assist)** из Chrome Web Store.
2. Настройки расширения:

- **API URL**:
    - Локально: `http://localhost:8000/generate`
    - Удаленно: `https://ВАШ_СУБДОМЕН.ngrok-free.app/generate`
- **HTTP Method**: `POST`
- **Request Body**: `{"text": "{query}"}`
- **Headers**: `{"Content-Type": "application/json"}`

---

### 10. Удаленный доступ через Ngrok

1. **Получите токен Ngrok** (не связан с моделью):
    - Зарегистрируйтесь на [ngrok.com](https://ngrok.com).
    - В [Dashboard](https://dashboard.ngrok.com/) скопируйте **Your Authtoken**.

2. **Настройка туннеля**:

```bash
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null  
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list  
sudo apt update && sudo apt install -y ngrok  
ngrok config add-authtoken ВАШ_ТОКЕН  # Замените на токен из шага 1  
ngrok http 8000  # Скопируйте HTTPS-ссылку (например, https://a1b2.ngrok-free.app)
```

3. В Page Assist укажите URL: `https://ВАШ_СУБДОМЕН.ngrok-free.app/generate`.

---

### Сноски

¹ **Оптимизация памяти**:

- `load_in_8bit=True` уменьшает потребление ОЗУ, но может не работать на некоторых GPU.
    - **Как отключить**: Удалите параметр из кода `api.py` или выполните:
      ```bash
      export USE_8BIT=0 && uvicorn api:app --reload
      ```
- Для CPU: замените `device_map="auto"` → `device_map="cpu"`.

---

**Готово!** Модель доступна через браузер. Для DeepSeek-R1 **токены Hugging Face не требуются**.
