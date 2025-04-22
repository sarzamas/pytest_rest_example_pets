# Модели с Ollama:

https://github.com/ollama/ollama

- установить ollama:
  https://ollama.com/
- выбрать и скачать образ модели:
  https://ollama.com/search
- запустить локально сервер ollama:

```bash
ollama run deepseek-r1:1.5b
```

- установить расширение **[Page Assist](https://chrome.google.com/webstore/detail/page-assist)** из Chrome Web Store.

### Инструкция по установке DeepSeek-R1 1.5B на MacBook

===============================================================

#### 1. **Системные требования**

- macOS 12.3 (Monterey) или новее (рекомендуется для поддержки MPS).
- MacBook с чипом Apple Silicon (M1/M2/M3) для ускорения через Metal.
- Не менее 16 ГБ ОЗУ (для работы с моделью 1.5B в CPU-режиме).
- 5–10 ГБ свободного места на диске.
- Python 3.8 или новее.
- Интернет-соединение для загрузки модели.

---

#### 2. **Установка Homebrew (если не установлен)**

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

#### 3. **Установка Python и создание виртуального окружения**

```bash
# Установка Python (если не установлен)
brew install python

# Создание виртуального окружения
python -m venv deepseek-env
source deepseek-env/bin/activate
```

---

#### 4. **Установка PyTorch с поддержкой MPS**

Установите PyTorch с поддержкой Metal Performance Shaders (MPS) для ускорения на GPU Apple Silicon:

```bash
pip3 install torch torchvision torchaudio
```

---

#### 5. **Установка зависимостей**

```bash
pip install transformers accelerate huggingface_hub sentencepiece
```

- `transformers`: Для работы с моделями Hugging Face.
- `accelerate`: Для оптимизации загрузки больших моделей.
- `huggingface_hub`: Для загрузки моделей.
- `sentencepiece`: Токенизатор (если требуется).

---

#### 6. **Загрузка модели DeepSeek-R1 1.5B**

Проверьте наличие модели в Hugging Face Hub:

- Если модель доступна публично (например, `deepseek-ai/deepseek-r1-1.5b`), используйте:
  ```python
  from transformers import AutoModelForCausalLM, AutoTokenizer

  model_name = "deepseek-ai/deepseek-r1-1.5b"
  tokenizer = AutoTokenizer.from_pretrained(model_name)
  model = AutoModelForCausalLM.from_pretrained(model_name)
  ```

- Если модель требует авторизации:
    1. Зарегистрируйтесь на [Hugging Face](https://huggingface.co).
    2. Запросите доступ к модели.
    3. Выполните вход в терминале:
       ```bash
       huggingface-cli login
       ```
    4. Введите ваш токен API.

---

#### 7. **Пример использования модели**

Создайте файл `run.py`:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "deepseek-ai/deepseek-r1-1.5b"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto")  # auto выбирает GPU (MPS) или CPU

prompt = "Как установить DeepSeek-R1 на MacBook?"
inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_length=200)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

---

#### 8. **Запуск**

```bash
python run.py
```

---

#### 9. **Советы и устранение ошибок**

- **Нехватка памяти**:
    - Используйте `device_map="cpu"` для принудительной загрузки на CPU.
    - Добавьте аргумент `load_in_8bit=True` или `load_in_4bit=True` (требуется `bitsandbytes`):
      ```bash
      pip install bitsandbytes
      ```
      ```python
      model = AutoModelForCausalLM.from_pretrained(model_name, load_in_8bit=True)
      ```

- **Ошибки токенизатора**: Убедитесь, что установлены `sentencepiece` или `tiktoken`.

- **Совместимость MPS**: Если возникают ошибки с MPS, перезагрузите модель на CPU:
  ```python
  model = AutoModelForCausalLM.from_pretrained(model_name, device_map="cpu")
  ```

---

#### 10. **Дополнительная оптимизация**

- Используйте `float16` для экономии памяти:
  ```python
  model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16)
  ```

---

Готово! Модель должна работать на вашем MacBook.
Для уточнений по конкретной реализации DeepSeek-R1 1.5B проверьте официальную документацию модели.

Для запуска интерактивного веб-интерфейса (WEB UI) для DeepSeek-R1 1.5B на MacBook можно использовать несколько
подходов.
Вот инструкция для двух популярных вариантов:

---

### **Вариант 1: Использование Gradio (простой UI)**

Gradio — библиотека для быстрого создания веб-интерфейсов для ML-моделей.

#### 1. Установите Gradio:

```bash
pip install gradio
```

#### 2. Создайте файл `web_ui.py`:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import gradio as gr
import torch

model_name = "deepseek-ai/deepseek-r1-1.5b"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto", torch_dtype=torch.float16)


def generate_text(prompt):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_length=200, temperature=0.7)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)


# Создание интерфейса
interface = gr.Interface(
    fn=generate_text,
    inputs=gr.Textbox(lines=3, placeholder="Введите запрос..."),
    outputs="text",
    title="DeepSeek-R1 1.5B Chat",
    theme="soft"
)

# Запуск сервера
interface.launch(server_name="0.0.0.0", server_port=7860, share=False)
```

#### 3. Запустите UI:

```bash
python web_ui.py
```

После запуска откройте в браузере:  
`http://localhost:7860`

---

### **Вариант 2: Использование текстового веб-интерфейса (oobabooga/text-generation-webui)**

Продвинутый интерфейс с поддержкой плагинов и расширений.

#### 1. Установите репозиторий:

```bash
git clone https://github.com/oobabooga/text-generation-webui
cd text-generation-webui
```

#### 2. Установите зависимости:

```bash
pip install -r requirements.txt
```

#### 3. Подготовьте модель:

- Поместите модель DeepSeek-R1 1.5B в папку `models`.
- Или создайте символическую ссылку:
  ```bash
  ln -s /путь/к/deepseek-r1-1.5b models/
  ```

#### 4. Запустите интерфейс:

```bash
python server.py --model deepseek-ai/deepseek-r1-1.5b --load-in-8bit --chat
```

- Откройте в браузере: `http://localhost:7860`

---

### **Вариант 3: Интеграция с браузером (через API)**

Для использования через расширение (например, как Page Assist) нужно создать локальный API.

#### 1. Установите FastAPI:

```bash
pip install fastapi uvicorn python-multipart
```

#### 2. Создайте файл `api.py`:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

app = FastAPI()

model_name = "deepseek-ai/deepseek-r1-1.5b"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto", torch_dtype=torch.float16)


class Query(BaseModel):
    text: str


@app.post("/generate")
async def generate(query: Query):
    inputs = tokenizer(query.text, return_tensors="pt").to(model.device)
    outputs = model.generate(**inputs, max_length=200)
    return {"response": tokenizer.decode(outputs[0], skip_special_tokens=True)}
```

#### 3. Запустите API:

```bash
uvicorn api:app --reload --port 8000
```

#### 4. Интеграция с расширением браузера:

1. Создайте расширение (manifest.json + popup.js) с запросом к `http://localhost:8000/generate`.
2. Убедитесь, что браузер разрешает CORS (или используйте плагин для обхода CORS).

---

### **Советы:**

1. **Оптимизация памяти**:
    - Используйте квантование: `--load-in-4bit` или `--load-in-8bit`.
   ```bash
   pip install bitsandbytes
   ```

2. **Ускорение на Apple Silicon**:
    - Для M1/M2 используйте `device_map="mps"`:
      ```python
      model = AutoModelForCausalLM.from_pretrained(model_name, device_map="mps")
      ```

3. **Готовые решения**:
    - [LM Studio](https://lmstudio.ai/) — GUI для локальных LLM (поддерживает модели GGUF).
    - [Faraday.dev](https://faraday.dev/) — кроссплатформенный клиент с веб-интерфейсом.

---

Готово! Теперь вы можете взаимодействовать с моделью через браузер или расширение.
Для расширений типа **Page Assist** потребуется настроить CORS и HTTPS (используйте `ngrok` для туннелирования,
если нужен внешний доступ).
