# ADR-0011: Контракт обміну між bizstruct-be і bizstruct-ml (wire contract)

- **Status:** Proposed
- **Date:** 2026-10-04
- **Supersedes:** —
- **Related:** ADR-0009 (граф, `ready_stages`, консистентність), ADR-0010 (контракти генерації, перевірки узгодженості в ml)

> Це **лише дизайн**. Жодних моделей не реалізовано. Документ чекає на затвердження; після нього окремий PR додає моделі з розділу «Моделі, які треба додати в домен».

---

## Context

Форми повідомлень між `bizstruct-be` і `bizstruct-ml` сьогодні дубльовано в обох репозиторіях (у ml — `schemas/messages.py` і `schemas/project.py`, у be — власні Pydantic-схеми й ORM). Прочитано: `bizstruct-ml@main` (`schemas/messages.py`, `schemas/project.py`, `handler.py`, `backend_client.py`, `experiments/http.py`, `experiments/runner.py`) і локальну копію `bizstruct-be` (`app/models/stage.py`, `app/services/*`, `app/routers/internal.py`; це гілка зі `StageService`, не обов'язково `main`).

### Що є зараз

| Форма | Де | Поля |
|---|---|---|
| `QueueMessage` | ml | `project_id`, `block`, `payload`, `force`, `language` |
| `HookPayload` | ml → be | `project_id`, `block`, `status: success\|failed`, `data`, `error` |
| `PubSubEvent` | ml → fe через pubsub | `type="block_generated"`, `project_id`, `block`, `status` |
| `ProjectState` | be → ml (`GET /api/internal/projects/{id}`) | `id`, `title`, `idea`, `status`, `language`, `translation_key` і по одному полю-словнику на **назву блоку** (`canvas`, `empathy_map`, …) |
| `Stage` (ORM) | be | `id` (uuid7), `project_id`, `type`, `status`, `retry_count`, `error_code`, `error`, `started_at`, `finished_at`, `approved_at`; **`UNIQUE(project_id, type)`** |

Поведінка: ml сам перевіряє ідемпотентність (`project.get_block(block) is not None` ⇒ `already_generated`, якщо не `force`); відповідь `422` на hook ⇒ повідомлення йде в dead-letter без повторів; `5xx`/таймаут ⇒ `abandon` і повторна доставка; після hook ml сам публікує pubsub-подію; `validate_model` — окремий спеціальний «блок». Інструмент експериментів (`experiments/`) ходить лише у **публічний** API (`POST /api/generation`, `GET /api/projects/{id}`), опитує `status == completed|failed` і читає блоки за назвою.

### Що це означає для нового графа

1. **Один блок на проєкт на назву** не вміщує багатоекземплярні етапи (`empathy_map`, `customer_scenario`, `ideation` мають `allows_multiple_instances=True`). `UNIQUE(project_id, type)` у be треба зняти.
2. **Знахідка в домені (потребує окремого рішення).** `STAGE_REGISTRY` має `allows_multiple_instances=False` для `canvas`, `swot_errc_cycle`, `storytelling`, `future_scenario`, `pitch`, хоча `Canvas.group_id` і зовнішні ключі `canvas_id` у `Swot`/`Storytelling`/`FutureScenario`/`Pitch` означають по екземпляру на групу, коли `Patterns` вирішує `split_model`. Для `pitch` це неоднозначно (`canvas_id` + `swot_id` + `storytelling_id`): один на проєкт чи один на канву — питання до продукту. Поки прапорці не виправлено, `ready_stages` і цей контракт описують не весь реальний граф.
3. **Ідентифікатори.** Домен використовує `str`, які видає бекенд; ORM — `uuid7`. На дроті — рядки.
4. **`ready_stages` у домені працює на рівні типу** (ADR-0009 D2) і консервативний: прогрес по сегментах не виражається. Контракт нижче дає змогу виразити його через `refs`.

### Гіпотеза, яку критикую

Одиниця роботи — **рядок етапу**; `be` створює рядки (`pending`) до генерації, по одному на екземпляр, видає id і записує, з яких рядків кожен тягне вхід (`refs`: етап → id рядків). `QueueMessage`: `project_id`, `stage_row_id`, `stage`, `force`, `language`, `params`. `ProjectSnapshot` для ml: усі рядки з `id`, `stage`, `status`, `refs`, артефактом, плюс поля проєкту. `StageResult` (hook): `stage_row_id`, `status`, `artifact`, `error`, опційний `ConsistencyReport`. ml ніколи не пише статуси.

**Що я залишаю:** рядок як одиницю роботи; `refs`; «ml не пише статуси» (переходи стейт-машини застосовує лише be); `ConsistencyReport` у результаті.
**Що пропоную змінити:** `force` → `attempt_id` (Q4); `artifact` → `artifacts: list` (рядок `swot_errc_cycle` дає кілька артефактів, Q6); повідомлення з **кількома цілями** замість одного рядка (agent mode, Q5); `refs` має валідуватися доменом і давати готовність **на рівні рядка**, а не типу (Q2); `block` → `stage`/`stage_row_id` усюди.

## Decision (пропозиція, по питаннях)

### Q1. Ідентичність рядка й артефакту: одне значення?

| Варіант | Суть | Мінуси |
|---|---|---|
| A. Так, `artifact.id == stage_row_id` | рядок = один артефакт | `swot_errc_cycle` дає Swot, Errc і нові версії Canvas; розбити на кілька рядків суперечить «один вузол» (ADR-0009 D1) |
| B. Ні, окремі; be **резервує** id артефактів при створенні рядка | uniform; ml бере id із повідомлення | треба резервувати пул для циклу |
| C. Збігаються для первинного артефакту, решта резервується | менше id | два правила замість одного |

**Рекомендація: B.** Рядок — стан і робота; артефакт — вміст, на який посилаються зовнішні ключі (`empathy_map_id`, `canvas_id`, …). Id артефактів видає be **при створенні рядка** і зберігає на ньому, тож повторна доставка й перегенерація використовують ті самі id (ідемпотентний upsert; зовнішні ключі нижчих етапів лишаються чинними, а застарілість позначає `dependents_of`). Пул для рядка визначає граф: один артефакт для більшості етапів; для циклу — до 5 Swot, 4 Errc і 4 нових версій Canvas (версії 1..5). Домен надає чисту функцію `reserved_artifact_counts(stage)`.

### Q2. Як задаються `refs` для багатоекземплярних етапів

`refs: dict[Stage, list[str]]` — id рядків, з яких тягне цей рядок. be створює рядки **поступово**, коли відомі кількості (варіант «усе наперед» неможливий: кількість груп/канв відома лише після `patterns`):

| рядок | `refs` |
|---|---|
| `empathy_map` (по сегменту) | `{brief: [brief]}` |
| `customer_scenario`, `ideation` (по рядку empathy_map) | `{empathy_map: [той самий рядок]}` — 1:1 |
| `patterns` | `{customer_scenario: [усі], ideation: [усі]}` |
| `canvas` (по групі) | `{brief, empathy_map: [рядки групи], customer_scenario: […], ideation: […], patterns}` |

Домен перевіряє `refs` чистою функцією `validate_row_refs(stage, refs)`: ключі ⊆ `depends_on ∪ optional_depends_on`, кожна тверда залежність непорожня. Готовність обчислюється **на рівні рядка**: `ready_rows(rows, enabled_optional)` — рядок `PENDING` і всі рядки з його `refs` для твердих залежностей `DONE` (увімкнена незавершена опційна залежність блокує, як у ADR-0009 D2). Це знімає консервативність `ready_stages`; `ready_stages` лишається для сумісності. Аналогічно `dependent_rows(row_id, rows)` для позначення застарілих рядків.

### Q3. Як ml націлюється на екземпляр

За `stage_row_id`. ml бере рядок із `ProjectSnapshot`, читає `refs`, збирає вхідні артефакти. Альтернатива «етап + ключ екземпляра» (наприклад, сегмент) крихка, бо ключа немає в домені. Для обмеження розміру відповіді — опційний параметр `?row=<id>`: повертає лише цей рядок і транзитивне замикання його `refs`.

### Q4. Повторні спроби й ідемпотентність (`force`, повторна доставка)

| Варіант | Суть | Проблема |
|---|---|---|
| A. `force: bool` (гіпотеза) | як сьогодні | повторна доставка повідомлення з `force=true` після успіху перегенерує вдруге й перезапише результат |
| B. `attempt_id` | be видає новий `attempt_id` при кожній **своїй** спробі (перший запуск, перегенерація, `needs_retry`) і зберігає на рядку; повторна доставка того самого повідомлення має той самий `attempt_id` | трохи більше стану в be |

**Рекомендація: B.** ml при отриманні дивиться на рядок: `attempt_id` у повідомленні ≠ `row.attempt_id` ⇒ повідомлення застаріло (замінене новішою спробою) ⇒ завершити без роботи; рядок `DONE` з тим самим `attempt_id` ⇒ уже застосовано ⇒ завершити. Hook несе `attempt_id`; be застосовує результат лише якщо `attempt_id` збігається і рядок `RUNNING`; дубль того самого результату — `200` без змін; застарілий — `409`. Прапорець `force` зникає (перегенерація = нова спроба, рішення be).

### Q5. Agent mode: одне повідомлення — багато рядків

| Варіант | Суть |
|---|---|
| A. Повідомлення на рядок, агент усередині ml нічим не відрізняється для be | не виражає, що агент сам планує й виконує підграф за один прохід |
| B. Повідомлення з `targets: list[RowTarget]` | pipeline — один target; agent — кілька |

**Рекомендація: B.** `RowTarget = {stage_row_id, stage, attempt_id, artifact_ids}`. Статуси пише лише be: першу ціль be переводить у `RUNNING` при відправленні; решту ml сигналізує подією `StageProgress(event="started")`, і be застосовує `PENDING → RUNNING`. Проміжні артефакти (чернетки, ітерації) ml надсилає як `StageProgress(event="artifact", artifact=…)` — be робить upsert за id артефакту без зміни статусу. Фінальний `StageResult` надсилається **по кожному рядку**, щойно він готовий, у порядку залежностей. Відкрите питання: чи потрібен ліміт на розмір `targets`.

### Q6. Версії Canvas усередині `swot_errc_cycle`: рядки чи версії артефакту?

| Варіант | Суть | Мінус |
|---|---|---|
| A. Кожна ітерація — окремі рядки | рядки на кожну версію | суперечить «один вузол», ламає стейт-машину й граф |
| B. Один рядок циклу; версії — артефакти (`Canvas.version`, `previous_version_id`, `Swot.canvas_version`, `Errc.from_version`/`to_version`) | цикл — оркестрація всередині рядка | рядок довго `RUNNING`; прогрес лише через `StageProgress` |

**Рекомендація: B.** Версії уже є полями моделей; кількість ітерацій і критерій зупинки — оркестрація ml (ADR-0009). Кожен проміжний Swot/Errc/Canvas надсилається як `StageProgress(artifact)`; фінальний `StageResult` містить повний набір (`artifacts`). Рядок стає `DONE`, коли цикл завершено; стартова версія Canvas (v1) належить рядку `canvas`, версії 2..5 — рядку циклу. Зверніть увагу: якщо `canvas` стане багатоекземплярним (див. знахідку 2), цикл також виконується по канві.

### Q7. Що потрібно інструменту експериментів від публічного API

Інструмент використовує лише публічний API. Йому потрібен той самий `ProjectSnapshot` (одна модель на ml-внутрішній і публічний шляхи), з опційними `started_at`/`finished_at` на рядках: (1) завершеність проєкту; (2) тривалість етапів; (3) причина збою (`error_code`, `error`); (4) усі артефакти за типом, включно з екземплярами й проміжними версіями циклу; (5) `ConsistencyReport` рядків. Стан проєкту виводиться, а не зберігається: `project_status(rows, enabled_optional)` — `completed`, коли всі потрібні рядки `DONE`; `failed`, коли є рядок `ERROR` без шляху вперед. Відкрите питання: camelCase/snake_case у публічній відповіді (fe читає camelCase, внутрішній канал — snake_case).

### Q8. Що валідується де (поведінка 422)

| Крок | Хто | Чим |
|---|---|---|
| вихід LLM | ml | контракт генерації (`GENERATION_CONTRACTS`, ADR-0010) |
| конвертація | ml | `X.from_generated(…)`; `ValidationError` ⇒ збій генерації |
| конверт повідомлення/результату | be | моделі дроту (`QueueMessage`, `StageResult`, …) |
| вміст артефактів | be | `ARTIFACT_MODELS[type].model_validate(data)` для кожного артефакту |
| міжартефактні правила | ml | `ConsistencyRule`/`JudgeCheck` (ADR-0010 D6) |
| `refs`, готовність, переходи | be | `validate_row_refs`, `ready_rows`, `is_valid_transition` |

Відповіді на hook: `200` — застосовано або дубль; `404` — проєкт/рядок зник (ml: dead-letter); **`422` — результат не проходить схему: be сам переводить рядок у `ERROR` (`generation_failed`, текст — зведення помилок) і відповідає `422`; ml завершує повідомлення в dead-letter, повторів немає**. Це закриває сьогоднішню прогалину: після dead-letter рядок не залишається вічно `RUNNING`. `409` — застаріла спроба або рядок уже не `RUNNING` (ml: завершити повідомлення). `5xx`/таймаут — `abandon`, повторна доставка (hook ідемпотентний завдяки `attempt_id`).

## Моделі, які треба додати в домен

Нова група `schemas/wire.py`, експорт із `bizstruct_domain.schemas`; усі успадковують `SanitizedModel`; ідентифікатори — `str`.

1. **`ArtifactType(StrEnum)`** — 14 значень (`brief`, `empathy_map`, `customer_scenario`, `ideation`, `patterns`, `canvas`, `swot`, `errc`, `storytelling`, `future_scenario`, `pitch`, `team_info`, `business_case`, `environment_scan`); `ARTIFACT_STAGE: dict[ArtifactType, Stage]`; `ARTIFACT_MODELS: dict[ArtifactType, type[BaseModel]]`.
2. **`ArtifactRecord`** — `id: str`, `type: ArtifactType`, `data: dict[str, Any]`; чиста `parse_artifact(record)` (валідація моделлю `ARTIFACT_MODELS[type]`).
3. **`StageRow`** — `id`, `stage: Stage`, `status: StageStatus`, `attempt_id: str | None`, `refs: dict[Stage, list[str]]`, `artifacts: list[ArtifactRecord]`, `retry_count: int`, `error_code: StageErrorCode | None`, `error: str | None`, `started_at`/`finished_at` (опційні).
4. **`ProjectSnapshot`** — `project_id`, `idea`, `language`, `enabled_optional: list[Stage]`, `rows: list[StageRow]`.
5. **`RowTarget`** — `stage_row_id`, `stage`, `attempt_id`, `artifact_ids: dict[ArtifactType, list[str]]`.
6. **`QueueMessage`** — `project_id`, `language`, `targets: list[RowTarget]` (≥ 1), `params: QueueParams` (`enabled_optional: list[Stage]`).
7. **`StageFailure`** — `code: StageErrorCode`, `message: str`.
8. **`StageResult`** — `project_id`, `stage_row_id`, `attempt_id`, `status: Literal["success","failed"]`, `artifacts: list[ArtifactRecord]`, `error: StageFailure | None`, `consistency: ConsistencyReport | None`.
9. **`StageProgress`** — `project_id`, `stage_row_id`, `attempt_id`, `event: Literal["started","artifact"]`, `artifact: ArtifactRecord | None`.
10. **`StageEvent`** (pubsub; публікує be після застосування переходу) — `type`, `project_id`, `stage_row_id`, `stage`, `status`.
11. Чисті функції: `reserved_artifact_counts(stage)`, `validate_row_refs(stage, refs)`, `ready_rows(rows, enabled_optional)`, `dependent_rows(row_id, rows)`, `project_status(rows, enabled_optional)`.

Це заміняє в ml `QueueMessage`, `HookPayload`, `PubSubEvent`, `ProjectState`; специфіка ml (LLM-клієнт, трейсинг) лишається в ml. Моделі дроту — мінорна зміна версії (додавання API).

## Відкриті питання

1. **Виправлення `allows_multiple_instances`** для `canvas`, `swot_errc_cycle`, `storytelling`, `future_scenario` (і, за рішенням продукту, `pitch`) — окремий PR до цього контракту.
2. **Пул резервованих id для циклу** (5/4/4) — чи достатньо, і чи резервувати при створенні рядка, чи при старті спроби.
3. **Розмір `targets` в agent mode** і чи може результат одного рядка залежати від проміжного артефакту іншого рядка того самого повідомлення.
4. **`validate_model`** лишається поза цим контрактом (ADR-0009: чекає на рішення продукту).
5. **Публічна форма** (camelCase vs snake_case) і чи віддавати артефакти повністю у публічному `GET`.
6. Хто призначає `ConsistencyViolation.artifact_ids` → рядки для переходів «порушення у цьому/вищому етапі»: потрібна відповідність артефакт → рядок у be.

## Consequences

- Стан і зміст розділено: be володіє рядками, статусами й id; ml володіє генерацією й перевірками.
- Ідемпотентність не залежить від прапорця й від читання чужого поля: вирішується `attempt_id` і станом рядка.
- Готовність на рівні рядка дає паралелізм по сегментах, якого не мав `ready_stages`.
- be мусить змінити схему БД (зняти `UNIQUE(project_id, type)`, додати `attempt_id`, `refs`, резерв id), а ml — перейти з блоків на рядки.
- Є ризик вузького місця: повний `ProjectSnapshot` на кожне повідомлення; пом'якшення — `?row=<id>`.

## Alternatives considered

- **Лишити `block` як ключ і додати індекс екземпляра** (`empathy_map[2]`): не дає ідентичності для `refs`, `attempt_id` і зовнішніх ключів.
- **ml записує статуси сам:** відхилено — стейт-машина і транзакції вже в be; два автори статусу дають розбіжності.
- **Кожна ітерація циклу — рядок:** відхилено (Q6).
- **`force` замість `attempt_id`:** відхилено (Q4).
