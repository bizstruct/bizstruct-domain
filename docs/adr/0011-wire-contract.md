# ADR-0011: Контракт обміну між bizstruct-be і bizstruct-ml (wire contract)

- **Status:** Accepted
- **Date:** 2026-10-04
- **Supersedes:** —
- **Related:** ADR-0009 (граф, `ready_stages`, консистентність), ADR-0010 (контракти генерації, перевірки узгодженості в ml)

> Рішення підтверджено мейнтейнером. Моделі й функції з розділу «Моделі й функції» **ще не реалізовано**: їх додає окремий PR (`schemas/wire.py`). Попередня редакція була в статусі Proposed (PR #17); цей текст її замінює.

---

## Context

Форми повідомлень між `bizstruct-be` і `bizstruct-ml` дубльовано в обох репозиторіях (у ml — `schemas/messages.py` і `schemas/project.py`, у be — власні Pydantic-схеми й ORM). Прочитано: `bizstruct-ml@main` (`schemas/messages.py`, `schemas/project.py`, `handler.py`, `backend_client.py`, `consumer.py`, `experiments/http.py`, `experiments/runner.py`) і локальну копію `bizstruct-be` (`app/models/stage.py`, `app/services/*`, `app/routers/internal.py`).

### Що є зараз

| Форма | Де | Поля |
|---|---|---|
| `QueueMessage` | ml | `project_id`, `block`, `payload`, `force`, `language` |
| `HookPayload` | ml → be | `project_id`, `block`, `status: success\|failed`, `data`, `error` |
| `PubSubEvent` | ml → fe через pubsub | `type="block_generated"`, `project_id`, `block`, `status` |
| `ProjectState` | be → ml (`GET /api/internal/projects/{id}`) | `id`, `title`, `idea`, `status`, `language`, `translation_key` і по одному полю-словнику на **назву блоку** |
| `Stage` (ORM) | be | `id` (uuid7), `project_id`, `type`, `status`, `retry_count`, `error_code`, `error`, `started_at`, `finished_at`, `approved_at`; **`UNIQUE(project_id, type)`** |

Поведінка: ml сам перевіряє ідемпотентність (`project.get_block(block) is not None` ⇒ `already_generated`, якщо не `force`); відповідь `422` на hook ⇒ dead-letter без повторів, і рядок лишається `RUNNING`; `5xx`/таймаут ⇒ `abandon` і повторна доставка; після hook ml сам публікує pubsub-подію; `validate_model` — окремий спеціальний «блок». Інструмент експериментів ходить лише у **публічний** API (`POST /api/generation`, `GET /api/projects/{id}`) і опитує `status == completed|failed`.

### Рішення мейнтейнера, на яких побудовано контракт

1. **Pitch — по одному на канву**, зі спільними на проєкт `team_info` і `business_case`.
2. **Кратність екземплярів** (ADR-0009, «Decisions made after acceptance», п. 4; `allows_multiple_instances` у домені 0.14.0):

   | етап | кількість рядків |
   |---|---|
   | `brief` | 1 |
   | `empathy_map` | по одному на кандидата сегмента (не більше `MAX_SEGMENTS = 3`) |
   | `customer_scenario`, `ideation` | по одному на рядок `empathy_map` |
   | `patterns` | 1 |
   | `canvas` | по одному на групу `Patterns` |
   | `swot_errc_cycle`, `storytelling`, `future_scenario`, `pitch` | по одному на канву |
   | `team_info`, `business_case`, `environment_scan` | по одному на проєкт (лише якщо етап увімкнено) |

3. **Спрощення:** id артефактів ml виводить детерміновано (uuid5), резервування в be немає; `StageProgress` і семантика багатьох цілей відкладені на фазу агента (список `targets` у формі повідомлення лишається, пайплайн надсилає рівно одну ціль); цикл повторів узгодженості (до 2 перегенерацій, повідомлення про порушення — як зворотний зв'язок) виконується **всередині ml** в одному повідомленні, be бачить лише фінальний результат; винним завжди вважається свіжозгенерований рядок (звинувачення вищого етапу відкладено).
4. **be скидає базу даних** (без міграції даних) і прибирає `UNIQUE(project_id, type)`.
5. **На `422` hook-у be сам переводить рядок у `ERROR`** (`generation_failed`).
6. **Моделі дроту — snake_case**; camelCase належить публічним DTO бекенду.

## Decision

Одиниця роботи — **рядок етапу** (`StageRow`). be створює рядки (`pending`) і записує, з яких рядків кожен тягне вхід (`refs`: етап → id рядків). ml отримує повідомлення про рядок, читає знімок проєкту, генерує, перевіряє узгодженість і повертає результат; **ml ніколи не пише статуси**, переходи стейт-машини застосовує лише be.

### Q1. Ідентичність рядка й артефакту; ідентифікатори артефактів

Рядок — стан і робота; артефакт — вміст, на який посилаються зовнішні ключі (`empathy_map_id`, `canvas_id`, …). Це різні ідентифікатори. Ідентифікатор артефакту виводить **ml** чистою функцією домену:

```
derive_artifact_id(stage_row_id: str, artifact_type: ArtifactType, index: int = 0) -> str
```

`uuid5` у фіксованому просторі імен (константа домену) від `f"{stage_row_id}:{artifact_type}:{index}"`. Значення `index`: `0` для рядків з одним артефактом; для `canvas` і `swot_errc_cycle` це **версія канви**: стартова `Canvas` v1 належить рядку `canvas` (`index=1`); версії 2..5 належать рядку циклу (`index=version`); `Swot` має `index = Swot.canvas_version`, `Errc` — `index = Errc.from_version`.

**Чому так:** перегенерація рядка дає ті самі id, тож зовнішні ключі нижчих етапів лишаються чинними (а застарілість позначає `dependent_rows`); повторна доставка ідемпотентна без координації з be; резервування id у be не потрібне. Наслідок: коли перегенерація дає меншу кількість версій, be **замінює весь набір артефактів рядка** (видаляє ті, яких у новому результаті немає).

Відхилено: резервування id у be (див. Alternatives).

### Q2. `refs` для кожного етапу й створення рядків

be створює рядки **поступово**, коли відомі кількості (кількість груп відома лише після `patterns`). Рядки для **увімкнених опційних етапів** be створює одразу. Кожен рядок має `instance_index` (0-based порядок серед рядків того самого етапу під тим самим батьком): для `empathy_map` рядок k покриває кандидата `Brief.customer_segment_candidates[k]`.

- Для етапів рівно з одним рядком на батька (`customer_scenario`, `ideation`, `swot_errc_cycle`, `storytelling`, `future_scenario`, `pitch`) `instance_index` завжди `0`; сегмент чи канву, до якої належить рядок, можна визначити **лише через `refs`**, але не через його власний індекс.
- Для `canvas` `instance_index` — позиція групи в `Patterns.groups`; be створює рядки `canvas` у тому порядку, в якому їх повертає `canvas_rows_for`.

| рядок | `refs` |
|---|---|
| `brief` | `{}` |
| `empathy_map` (k-й сегмент) | `{brief: [brief]}` |
| `customer_scenario`, `ideation` (по рядку empathy_map) | `{empathy_map: [відповідний рядок]}` |
| `patterns` | `{customer_scenario: [усі], ideation: [усі]}` |
| `canvas` (по групі) | `{brief: [brief], empathy_map: [рядки групи], customer_scenario: [рядки групи], ideation: [рядки групи], patterns: [patterns]}` |
| `swot_errc_cycle` (по канві) | `{canvas: [рядок канви]}`; якщо `environment_scan` увімкнено — ще `{environment_scan: [рядок]}` |
| `storytelling`, `future_scenario` (по канві) | `{swot_errc_cycle: [рядок циклу тієї самої канви]}` |
| `pitch` (по канві) | `{storytelling: [рядок тієї самої канви], swot_errc_cycle: [рядок тієї самої канви]}`; для увімкнених — ще `{team_info: [спільний рядок], business_case: [спільний рядок]}` |
| `team_info` | `{}` (користувацький ввід: be створює рядок одразу в `DONE`, див. нижче) |
| `business_case`, `environment_scan` | `{brief: [brief]}` |

Домен перевіряє `refs` чистою `validate_row_refs(stage, refs)`: ключі ⊆ `depends_on ∪ optional_depends_on`; кожна **тверда** залежність має непорожній список. Рядки канв будуються з `Patterns`: `canvas_rows_for(patterns) -> list[CanvasRowSpec]` (`CanvasRowSpec`: `group_id`, `empathy_map_ids`); відповідність id артефакту → рядок дає `row_of_artifact(rows, artifact_id)`.

**`ready_rows(rows, enabled_optional)`** — точно: рядок готовий, якщо (1) його статус `PENDING`; (2) його `refs` проходять `validate_row_refs`; (3) для кожної твердої залежності всі рядки з `refs[dep]` існують у `rows` і мають статус `DONE`; (4) для кожної опційної залежності, що **увімкнена**, `refs[dep]` непорожній і всі ці рядки `DONE` — увімкнена опційна залежність, що не `DONE` (або рядка для якої ще немає), блокує споживача; (5) рядок опційного етапу, що не входить до `enabled_optional`, не готовий; (5b) `PENDING`-рядок етапу, якого немає в `GENERATION_CONTRACTS` (тобто `team_info`), **ніколи не готовий** — його ніхто не генерує; **вимкнений** опційний етап не має рядка й ігнорується (навіть якщо `refs` його згадують). Результат — id рядків у порядку графа, далі в порядку входу. `ready_stages` лишається для сумісності. `dependent_rows(row_id, rows)` — транзитивні залежні рядки за `refs` (тверді й опційні ребра) для позначення застарілих.

**`team_info` — ввід користувача.** Контракту генерації немає (ADR-0010), а стейт-машина забороняє `PENDING → DONE`. Тому be створює рядок `team_info` **одразу в `DONE`** (з артефактом `TeamInfo`), коли користувач надсилає дані; до цього моменту рядка немає. Якщо `team_info` увімкнено, але користувач ще нічого не надіслав, рядка немає, і за правилом (4) споживач (`pitch`) заблоковано. Правило (5b) страхує від помилки: якщо рядок `team_info` все ж створено в `PENDING`, він не потрапить до черги.

**`project_status(rows, enabled_optional)`** повертає `completed | failed | running`:
- `failed` — є хоча б один рядок `ERROR`. Обґрунтування: за стейт-машиною `error` лишають лише через дію користувача (`error → pending`), тож без втручання проєкт не просунеться, а рядок без нащадків (наприклад, `future_scenario`) також не дозволяє досягти `completed`.
- `completed` — немає рядків `ERROR`, усі рядки `DONE`, **і** розгортання завершено: кожен очікуваний етап має очікувану кількість рядків (одиничні етапи — 1, увімкнені опційні — 1, `empathy_map` ≥ 1, `customer_scenario` і `ideation` = кількість рядків `empathy_map`, `canvas` ≥ 1, `swot_errc_cycle`/`storytelling`/`future_scenario`/`pitch` = кількість рядків `canvas`). Без цієї умови проєкт із самим `brief` у стані `DONE` вважався б завершеним.
- `running` — усе інше, зокрема рядки в `AWAITING_DECISION` (проєкт чекає користувача) і неповне розгортання.

### Q3. Як ml націлюється на екземпляр

За `stage_row_id`. ml бере рядок зі знімка, читає `refs`, збирає вхідні артефакти. Запит знімка підтримує `?row=<id>` **з самого початку**: повертає цей рядок і транзитивне замикання його `refs` (плюс поля проєкту). Замикання достатнє для перевірок узгодженості: усі входи правил `MANY` лежать у замиканні (наприклад, усі версії Canvas — у рядку канви й рядку циклу).

### Q4. Повторні спроби й ідемпотентність

be видає новий `attempt_id` при кожній **своїй** спробі (перший запуск, перегенерація, повтор) і зберігає його на рядку; повторна доставка того самого повідомлення має той самий `attempt_id`. ml при отриманні дивиться на рядок: `attempt_id` у повідомленні ≠ `row.attempt_id` ⇒ повідомлення застаріло ⇒ завершити без роботи; рядок `DONE` з тим самим `attempt_id` ⇒ уже застосовано ⇒ завершити. Hook несе `attempt_id`: be застосовує результат лише якщо збігається `attempt_id` і рядок `RUNNING`; дубль — `200` без змін; застарілий — `409`. Прапорця `force` немає (перегенерація = нова спроба, рішення be).

### Q5. Повідомлення й цілі

`QueueMessage.targets: list[RowTarget]` (≥ 1). **Пайплайн надсилає рівно одну ціль.** `StageProgress` і семантика багатьох цілей **зарезервовані для фази агента** і в цій версії не реалізуються. Цикл `swot_errc_cycle` у пайплайні повертає **усі версії** в `StageResult.artifacts` одним результатом.

### Q6. Версії Canvas усередині `swot_errc_cycle`

Один рядок циклу на канву; версії — артефакти (`Canvas.version`/`previous_version_id`, `Swot.canvas_version`, `Errc.from_version`/`to_version`). Кількість ітерацій і критерій зупинки — оркестрація ml (ADR-0009). Стартова v1 належить рядку `canvas`, версії 2..5 — рядку циклу (Q1).

### Q7. Узгодженість і повтори всередині ml

Після генерації ml виконує детерміновані правила й judge-чеки, застосовні до свіжого рядка (ADR-0010 D6; входи `MANY` беруться із замикання `refs`). Якщо є порушення рівня `error`, ml **до 2 разів** перегенерує, подаючи тексти порушень у промпт; повторів у be не видно. Фінальний `ConsistencyReport` іде в `StageResult.consistency`. be застосовує **`RUNNING → CONSISTENCY_CHECK → DONE`**, якщо немає порушень рівня `error` (попередження не блокують), інакше **`RUNNING → CONSISTENCY_CHECK → AWAITING_DECISION`** (порушення додано до рядка). Перевірено за `stage_machine`: `RUNNING→CONSISTENCY_CHECK`, `CONSISTENCY_CHECK→DONE`, `CONSISTENCY_CHECK→AWAITING_DECISION` дозволені (тоді як `RUNNING→DONE` напряму — ні), тому be застосовує два переходи послідовно. `StageRow.consistency` зберігає останній звіт: ml читає його при ініційованому користувачем повторі, інструмент експериментів — для аналізу. Винним завжди вважається **свіжозгенерований рядок**; звинувачення вищого етапу відкладено. Ліміт повторів ml (2) не збільшує `retry_count` у be.

### Q8. Інструмент експериментів

Використовує лише публічний API й той самий `ProjectSnapshot` (з опційними `started_at`/`finished_at`, `error_code`, `error`, `consistency`, усіма артефактами за типом, включно з екземплярами й версіями циклу); статус проєкту виводить `project_status`. Публічна форма віддається у camelCase (DTO бекенду); моделі дроту — snake_case.

### Q9. Що валідується де (поведінка 422)

| Крок | Хто | Чим |
|---|---|---|
| вихід LLM | ml | контракт генерації (`GENERATION_CONTRACTS`, ADR-0010) |
| конвертація | ml | `X.from_generated(…)`; `ValidationError` ⇒ збій генерації |
| конверт повідомлення/результату | be | моделі дроту |
| вміст артефактів | be | `ARTIFACT_MODELS[type].model_validate(data)` |
| міжартефактні правила | ml | `ConsistencyRule`/`JudgeCheck` |
| `refs`, готовність, переходи | be | `validate_row_refs`, `ready_rows`, `is_valid_transition` |

Відповіді на hook: `200` — застосовано або дубль; `404` — проєкт/рядок зник (ml: dead-letter); **`422` — результат не проходить схему: be сам переводить рядок у `ERROR` (`generation_failed`, текст — зведення помилок) і відповідає `422`; ml завершує повідомлення в dead-letter**; `409` — застаріла спроба або рядок уже не `RUNNING` (ml завершує повідомлення); `5xx`/таймаут — `abandon`, повторна доставка (hook ідемпотентний через `attempt_id`).

## Моделі й функції, які треба додати в домен

Нова група `schemas/wire.py`, експорт із `bizstruct_domain.schemas`; усі успадковують `SanitizedModel`; ідентифікатори — `str`; часові мітки — `datetime | None`; поля — snake_case.

**Моделі й enum:**
1. `ArtifactType(StrEnum)` — 14 значень; `ARTIFACT_STAGE: dict[ArtifactType, Stage]`; `ARTIFACT_MODELS: dict[ArtifactType, type[BaseModel]]` (збережені моделі).
2. `ArtifactRecord` — `id`, `type: ArtifactType`, `data: dict[str, Any]`.
3. `StageRow` — `id`, `stage: Stage`, `instance_index: int`, `status: StageStatus`, `attempt_id: str | None`, `refs: dict[Stage, list[str]]`, `artifacts: list[ArtifactRecord]`, `consistency: ConsistencyReport | None`, `retry_count: int`, `error_code: StageErrorCode | None`, `error: str | None`, `started_at`, `finished_at`.
4. `ProjectSnapshot` — `project_id`, `idea`, `language`, `enabled_optional: list[Stage]`, `rows: list[StageRow]`.
5. `RowTarget` — `stage_row_id`, `stage`, `attempt_id`.
6. `QueueMessage` — `project_id`, `language`, `targets: list[RowTarget]` (≥ 1). `enabled_optional` живе лише в `ProjectSnapshot` (ml і так читає знімок); окремих параметрів повідомлення немає.
7. `StageFailure` — `code: StageErrorCode`, `message`.
8. `StageResult` — `project_id`, `stage_row_id`, `attempt_id`, `status: Literal["success","failed"]`, `artifacts`, `error: StageFailure | None`, `consistency: ConsistencyReport | None`; узгодженість: `failed` вимагає `error`, `success` вимагає непорожніх `artifacts`.
9. `StageEvent` (pubsub, публікує be після застосування переходу) — `type`, `project_id`, `stage_row_id`, `stage`, `status`.
10. `CanvasRowSpec` — `group_id`, `empathy_map_ids`.

**Чисті функції:** `derive_artifact_id`, `validate_row_refs`, `ready_rows`, `dependent_rows`, `project_status`, `canvas_rows_for`, `row_of_artifact`, `parse_artifact`.

**Не входять у цю версію:** `StageProgress`, `reserved_artifact_counts`, `artifact_ids` у `RowTarget`.

Це заміняє в ml `QueueMessage`, `HookPayload`, `PubSubEvent`, `ProjectState`; специфіка ml (LLM-клієнт, трейсинг) лишається в ml.

## Відкриті питання

1. **`validate_model`** лишається поза цим контрактом (ADR-0009: чекає на рішення продукту).
2. **Фаза агента:** `StageProgress`, повідомлення з кількома цілями, подальший порядок результатів — окремий ADR.
3. **Звинувачення вищого етапу** при порушеннях (відповідність артефакт → рядок уже є, але правило звинувачення відкладено).
4. **Єдиний пітч компанії** (не по канві) — можливий пізніший етап, не зараз.
5. **Які знахідки judge мають рівень `error`** (блокують `DONE` і запускають повтор усередині ml). Доки не вирішено, знахідки judge **дорадчі**, а повтори запускають лише детерміновані помилки. Вирішити на першому зрізі ml.

## Ризики

- **Тривалість рядка циклу проти блокування повідомлення.** Рядок `swot_errc_cycle` у пайплайні може виконуватись хвилинами, а `AutoLockRenewer` у ml жорстко обмежено `max_lock_renewal_duration=300` (`consumer.py`, рядки 75 і 83). Продовження блокування треба збільшити або зробити конфігурованим. Що саме відбувається при спливі блокування (повторна доставка іншому споживачеві, помилка при завершенні повідомлення), **не стверджується тут як факт**: це треба перевірити на Service Bus під час реалізації; `attempt_id` робить повторну доставку безпечною, але не прибирає зайвої роботи.
- Знімок проєкту на кожне повідомлення: пом'якшується `?row=<id>` (Q3).

## Consequences

- Стан і зміст розділено: be володіє рядками, статусами й переходами; ml — генерацією, перевірками й виведенням id артефактів.
- Ідемпотентність не залежить від прапорця: вирішується `attempt_id` і станом рядка; id артефактів стабільні при перегенерації.
- Готовність на рівні рядка дає паралелізм по сегментах і по канвах, якого не мав `ready_stages`.
- **Для be:** нова схема рядків етапів (`instance_index`, `attempt_id`, `refs`, `consistency`, артефакти рядка); зняти `UNIQUE(project_id, type)`; створювати рядки поступово (після `brief`, після `patterns`) і одразу для увімкнених опційних етапів; hook відповідає `200/404/409/422` за Q9 і сам переводить рядок у `ERROR` при `422`; застосовувати `RUNNING → CONSISTENCY_CHECK → DONE|AWAITING_DECISION`; **БД скидається, міграції даних немає**.
- **Для ml:** перейти з блоків на рядки; виводити id артефактів; виконувати повтори узгодженості всередині повідомлення; продовження блокування повідомлення (Ризики).

## Alternatives considered

- **Резервування id артефактів у be** (пул на рядок): відхилено — потребує розміру пулу для циклу (5/4/4) і зберігання на рядку; детерміноване виведення дає ті самі властивості без координації.
- **Цикл повторів узгодженості через be** (кожна перегенерація — нове повідомлення): відхилено — be мусив би тримати проміжні стани й лічильники, а ml усе одно має повний контекст.
- **Лишити `block` як ключ і додати індекс екземпляра** (`empathy_map[2]`): не дає ідентичності для `refs`, `attempt_id` і зовнішніх ключів.
- **ml записує статуси сам:** відхилено — стейт-машина і транзакції вже в be.
- **Кожна ітерація циклу — окремі рядки:** відхилено — суперечить «один вузол» (ADR-0009 D1) і ламає стейт-машину.
- **`force` замість `attempt_id`:** відхилено — повторна доставка `force`-повідомлення перегенерувала б вдруге.
