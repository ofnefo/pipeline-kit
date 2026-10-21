# NameNode и доска задач

Для агента, работающего с проектами в одной локальной среде. NameNode хранит карту проектов, владельцев работы, журнал и сообщения; доска хранит отдельные задачи и историю их выполнения.

## Подготовьте карточку

Создайте проект в панели или карточку через `namenode put_card`. Используйте [card.example.json](../config/card.example.json): укажите фактический путь, репозиторий при наличии, правила, место изменений, запуск, риски и критерии готовности. Заголовки разделов оставляйте как в примере — их использует редактор панели. `meta.rules` можно дополнить путём к правилам проекта.

Карточка сама по себе не создаёт проектные файлы и не устанавливает сервисы. Путь и команды в ней должны соответствовать проверенной среде. Файлы внутреннего хранилища NameNode вручную не редактируйте.

## Пример полного цикла через CLI

Следующий Python-код запускайте из корня Kit Python-интерпретатором его виртуального окружения. Он создаёт демонстрационную карточку в отдельном соседнем `pipeline-test-workspace`, проверяет занятость и почту, затем освобождает карточку. Данные сохраняются. Не назначайте этот каталог рабочим хранилищем. Для повторного запуска задайте новое `CARD`; существующая карточка не перезаписывается.

<!-- runnable-example: namenode -->
```python
import json
import os
from pathlib import Path
import subprocess
import sys

KIT = Path.cwd()
WORKSPACE = (KIT.parent / "pipeline-test-workspace").resolve()
AGENT = "codex:onboarding-demo"
CARD = "project-onboarding-demo"

def nn(action, args, expect_ok=True):
    result = subprocess.run(
        [sys.executable, str(KIT / "pipeline_kit.py"), "--workspace",
         str(WORKSPACE), "namenode", action, json.dumps(args)],
        cwd=KIT, capture_output=True, text=True, encoding="utf-8",
        creationflags=0x08000000 if os.name == "nt" else 0, check=True,
    )
    data = json.loads(result.stdout)
    if expect_ok and ("error" in data or data.get("ok") is False):
        raise RuntimeError(data)
    return data

sample = json.loads((KIT / "config/card.example.json").read_text("utf-8"))
sample["meta"].update(id=CARD, title="Onboarding demo",
                      canonical=str(WORKSPACE / "projects" / "demo"))
sample["agent"] = AGENT
nn("put_card", sample)
assert nn("search", {"query": "Onboarding"})["hits"]
nn("card", {"id": CARD})
nn("inbox", {"agent": AGENT, "peek": True})
nn("claim", {"id": CARD, "agent": AGENT, "what": "Check local coordination", "hours": 1})
try:
    busy = nn("claim", {"id": CARD, "agent": "claude:onboarding-demo",
                       "what": "Conflict probe"}, expect_ok=False)
    assert busy.get("ok") is False and busy.get("busy"), busy
    nn("send", {"agent": AGENT, "to": "claude:onboarding-demo",
                "id": CARD, "text": "Local coordination sample"})
    assert nn("inbox", {"agent": "claude:onboarding-demo", "peek": True})["messages"]
    nn("log", {"agent": AGENT, "id": CARD,
               "text": "Claim conflict and local mailbox checked."})
    assert nn("journal", {"id": CARD})["entries"]
finally:
    nn("release", {"agent": AGENT, "id": CARD, "summary": "Coordination example finished"})
print("NameNode coordination example passed")
```

Передача JSON как отдельного аргумента `subprocess` избавляет от различий экранирования PowerShell/cmd/bash. Проверяйте и код завершения процесса, и JSON: ошибки CLI могут завершить процесс с ненулевым кодом, а конфликт claim возвращает `ok: false` и `busy` при коде 0.

## Действия в обычной работе

| Действие | Поля JSON | Когда использовать |
| --- | --- | --- |
| `search` | `query`, необязательно `limit` | Найти нужную карточку |
| `card` | `id`, необязательно `sections` | Прочитать пути, правила и состояние |
| `work` | `{}` | Проверить действующие claims |
| `claim` | `id`, `agent`, `what`, необязательно `hours` | Занять карточку; по истечении срока claim перестаёт защищать работу |
| `log` | `id`, `agent`, `text` | Записать изменение и доказательство |
| `set_section` | `id`, `agent`, `section`, `text`, необязательно `expect_updated` | Обновить раздел, передав `meta.updated` из прочитанной карточки |
| `send` | `agent`, `to`, `text`, необязательно `id` | Передать локальное сообщение конкретному агенту или `card:<id>` |
| `inbox` | `agent`, необязательно `peek` | Прочитать сообщения; `peek: true` не помечает их прочитанными |
| `release` | `id`, `agent`, `summary` | Завершить владение и оставить краткий итог |

При долгой работе обновляйте свой claim до истечения срока. Перед каждым новым этапом проверяйте владельца. Claim — договорённость агентов, а не файловая блокировка всех программ. `expect_updated` — дополнительная проверка прочитанной версии; не заменяйте ею владение карточкой. Чужую работу не перехватывайте через `force` без согласованной передачи.

## Доска задач

Создайте задачу в панели: название, проект, ожидаемый результат, критерии проверки, исполнитель и при необходимости модель. Получите текст передачи задачи из панели. Запуск внешней сессии выполняется отдельно.

Агенту доступны команды из корня Kit. Ниже `python` означает интерпретатор виртуального окружения Kit; `TASK_ID`, `VERSION`, `SESSION_REF` и `MODEL_ID` заменяются фактическими значениями:

```text
python apps/tools/workboard/board.py list
python apps/tools/workboard/board.py get TASK_ID
python apps/tools/workboard/board.py start TASK_ID --actor codex:demo --version VERSION --session-ref SESSION_REF --actual-model MODEL_ID
python apps/tools/workboard/board.py heartbeat TASK_ID --actor codex:demo --version VERSION
python apps/tools/workboard/board.py submit TASK_ID --actor codex:demo --version VERSION --evidence /absolute/path/to/receipt.json
```

До запуска задайте `PIPELINE_KIT_WORKSPACE`. Получайте свежую `version` через `get` перед каждой изменяющей командой: после действия она увеличивается. Если есть блокер, используйте `block` с `--reason` вместо `submit`. Подробные аргументы — `python apps/tools/workboard/board.py --help`.

При `start` префикс идентификатора в `--actor` должен соответствовать назначенному исполнителю (`codex:` или `claude:`). Если в задаче задана модель, `--actual-model` должен совпадать с ней. Доска отклонит несовпадение; она не переключает модель за агента. Укажите фактическую модель или согласуйте изменение назначения, не подменяйте значение ради запуска.

Переходы: `queued` → `running` → `review` → `done`. `submit` переводит результат на проверку; принимает его владелец доски в панели. Возврат из `blocked`/`review` согласуется через панель. Отмена задачи не завершает процесс внешнего агента.

Перед `start` агент читает карточку и занимает claim. После `submit` записывает результат в журнал, проверяет inbox и освобождает карточку. При ошибке версии агент перечитывает задачу и согласует изменение, а не подставляет число наугад.

## Несколько компьютеров

Базовый Kit работает локально. Его файловое хранилище и SQLite не являются распределённой базой. Не запускайте несколько независимых копий данных как одну общую систему и не используйте сетевую синхронизацию файлов для имитации блокировок.

Для общей службы отдельно спроектируйте единственный источник состояния, аутентификацию, транспорт, права, резервирование и поведение при разрыве связи. Сначала проверьте конкурирующие изменения и восстановление. Встроенный HTTP API рассчитан на одного локального пользователя; публикация порта в сеть не превращает его в многопользовательский сервер.
