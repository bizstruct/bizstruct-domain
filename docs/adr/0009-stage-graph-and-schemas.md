# ADR-0009: Граф із 13 етапів, схеми артефактів і модуль узгодженості

- **Status:** Accepted (відкриті питання — див. нижче)
- **Date:** 2026-10-04
- **Supersedes:** ADR-0008 (перепис доменної моделі під BMG); через нього — ADR-0001
- **Related:** ADR-0005 (агентний режим; вимога джерела й дати для зовнішніх кількісних тверджень)

---

## Context

ADR-0008 переписав домен під методологію BMG, але залишив три речі, які не витримали подальшого проєктування моделей:

1. **Граф із 16 етапів містив зайве й не містив потрібного.** `value_map` і `models_options` були відкладеними питаннями 1–2; `assessment` і `errc` — два вузли для одного циклу; `storytelling` згорнуто в `pitch` як «свідомий борг».
2. **Моделі й граф жили в двох паралельних деревах.** Нова модель артефактів (`schemas/`) проєктувалась і рев'юїлась по одному файлу, але нічого не тестувала й не експортувала: `blocks/`, кореневі `chain.py` і `enums.py` залишалися «публічним» API, а `schemas/__init__.py` був порожнім.
3. **Не було перевірки між артефактами.** Валідатор моделі бачить лише поля цієї моделі. Питання «чи `Patterns` — вірний наслідок із `CustomerScenario`/`Ideation`, з яких його згенеровано?» потребує кількох артефактів одразу.

Крім того, частина обмежень існує лише як `model_validator`, який **не потрапляє в JSON Schema** і тому невидимий для генератора (`response_format`). Їх потрібно було перелічити явно (розділ «Constraints that are validator-only»).

Цей ADR замінює ADR-0008 і фіксує стан після PR #4–#10: граф із 13 етапів, 14 моделей артефактів (13 етапів; `swot_errc_cycle` містить `Swot` та `Errc`), модуль `consistency`, публічний API `bizstruct_domain.schemas`, `SanitizedModel`, видалення попереднього дизайну (0.12.0).

## Decision

### D1. Граф із 13 етапів

| id | depends_on | optional_depends_on | кілька екземплярів | опційний |
|---|---|---|---|---|
| `brief` | — | — | | |
| `empathy_map` | brief | — | так | |
| `customer_scenario` | empathy_map | — | так | |
| `ideation` | empathy_map | — | так | |
| `patterns` | customer_scenario, ideation | — | | |
| `canvas` | brief, empathy_map, customer_scenario, ideation, patterns | — | | |
| `swot_errc_cycle` | canvas | environment_scan | | |
| `storytelling` | swot_errc_cycle | — | | |
| `future_scenario` | swot_errc_cycle | — | | |
| `pitch` | storytelling, swot_errc_cycle | team_info, business_case | | |
| `team_info` | — | — | | так |
| `business_case` | brief | — | | так |
| `environment_scan` | brief | — | | так |

Рішення, що стоять за графом:

- **Режимів немає.** `StageMode`/Pro видалено остаточно; усі етапи доступні і конвеєру, і агенту. Яку підмножину запускати — рішення бека.
  `environment_scan` і `business_case` використовують зовнішні джерела в **обох** стратегіях (конвеєр і агент), тому `sources` і `retrieved_at` обов'язкові для обох етапів незалежно від способу запуску.
- **`swot_errc_cycle` — один вузол.** Цикл (до 5 ітерацій, відносний критерій зупинки за `weighted_weakness_threat_score`) — оркестрація, а не ребро графа. Граф ациклічний.
- **Ідентифікатори — звичайні `str`, видаються бекендом**, а не генератором.
- **Canvas** залежить від brief, empathy_map, customer_scenario, ideation і patterns; `business_case` та `environment_scan` — лише від brief.
- **`value_map`, `models_options`, `hypotheses`, `assessment`** з графа видалено; Value Proposition Design і Testing Business Ideas більше не використовуються.
- **Структура, а не презентація.** `StageDefinition` має рівно п'ять полів: `id`, `depends_on`, `optional_depends_on`, `allows_multiple_instances`, `is_optional`. Назви етапів (локалізована презентація) і user gate (властивість стратегії обходу, а не етапу) лишаються на стороні споживачів. `bizstruct-fe` бере структуру зі `stages.json` і тримає власну мапу `id → назва` з тестом, який падає на будь-якому id етапу без назви.

### D2. Семантика `optional_depends_on`

Тверді залежності (`depends_on`) блокують етап. Опційні — збагачують результат, якщо присутні, і **блокують споживача лише доти, доки вони водночас увімкнені й не завершені**. Опційний етап (`is_optional=True`) з'являється в `next_available` тільки якщо його перелічено в `enabled_optional`; передати туди неопційний етап — `ValueError`.

| Функція | Які ребра враховує |
|---|---|
| `STAGE_REGISTRY.topological_order()` | обидва види: опційний вхід іде перед споживачем |
| `STAGE_REGISTRY.next_available(completed, enabled_optional)` | тверді завжди; увімкнені незавершені опційні блокують споживача |
| реєстр: валідатори | немає відсутніх етапів, `key == id`, тверда залежність не вказує на опційний етап, опційна — лише на опційний, цикли (також через опційне ребро) |
| `stage_machine.dependents_of()` | обидва: результат, що міг спожити змінений опційний вхід, застарів |
| `stage_machine.ready_stages(rows, enabled_optional)` | рівень *типу* етапу (нижче) |

**`ready_stages` працює на рівні типу.** Рядки можуть ділити тип, якщо `allows_multiple_instances`. Тип *завершений* ⇔ має хоча б один рядок і всі його рядки `DONE`. Тип *готовий* ⇔ має хоча б один `PENDING`-рядок і всі типи твердих залежностей завершені; опційний етап готовий лише якщо увімкнений; увімкнена опційна залежність, що не завершена (зокрема ще без жодного рядка), блокує споживача. Це **свідомо консервативно**: прогрес по сегментах не виражається, бо в графі немає зв'язків між екземплярами.

### D3. Canvas: збережена форма й форма генерації

- **`Canvas`** — збережена форма: `id`, `group_id`, `empathy_map_ids`, `version` (1–5), `previous_version_id`, `is_final`, `is_generated`, `sections` (дев'ять секцій карток `{id, text, errc_marker}`). Секції названо за `CanvasSection` (`key_partnerships`, не `key_partners`); імена секцій у `CanvasSection`, `CanvasSections` і `CanvasSectionsGenerated` звіряються при імпорті.
- **`CanvasGenerated`** — контракт часу генерації: лише текстові картки (`CanvasCardDraft`), 2–4 на секцію, виражено як `minItems`/`maxItems` у JSON Schema, тож межа доходить до моделі через `response_format`. Ідентифікатори, `group_id`, `version` генератор не видає.
- **`Canvas.generated_card_count`** (валідатор збереженої форми) лишається як є — див. відкрите питання 1.

### D4. Моделі артефактів

- **Epicenter.** `MULTIPLE_EPICENTER` повернено (його було видалено в ADR-0008) з **двобічним правилом**: конкретні теги (усі, крім маркера) унікальні й їх 1–4; маркер присутній ⇔ конкретних тегів ≥ 2. Ідеація несе `EpicenterClassification {tags, rationale}`, а не голий список.
- **Patterns.** `segment_count` замінено на `groups` (`CanvasGroup`: `empathy_map_ids`, `relation_type` — multi-sided/segmented/diversified) і `pairwise_scores`. `branch_decision` (`unified_model`/`split_model`) має відповідати кількості груп; `MULTI_SIDED_PLATFORM` вимагає групи, що **одночасно** `MULTI_SIDED` і має ≥ 2 карти емпатії; кожен патерн тегується не більш ніж раз.
- **NetScore.** `PairwiseSegmentScore`: `synergy` 0..5, `conflict` −7..0, `net_score = synergy + conflict`. Пороги з документа BMG (напр. multi-sided при net ≥ +3) відкалібровано під ці межі; розширення діапазону їх знецінює.
- **Canvas** — детальний рівень (`detail_level`) прибрано.
- **Swot** (замість `Assessment`): чотири кластери (`SwotCluster`, відображення на секції — `SWOT_CLUSTER_SECTIONS`, множини не перетинаються й разом дають усі дев'ять секцій), кожен із твердженнями осі (`score` −5..5 ≠ 0, `importance`/`certainty` 1–10), `opportunities` і `threats` (`SwotOpportunityThreat`, `score` 1–5). Книга (pp. 220–223) шкалу 1–5 не підписує; **робоча інтерпретація — «наскільки це стосується моделі»** (1 — ледве, 5 — дуже сильно), зафіксована в описі поля. `weighted_weakness_threat_score` = Σ `importance·|score|` за негативними твердженнями + Σ `score` усіх загроз.
- **Errc.** `moves` (`ErrcMove`: дія, секція, `target_card_text`/`new_text` за дією, наслідок для протилежної сторони, обґрунтування), `from_version`/`to_version` (`to = from + 1`, `to ≥ 2`), `result_canvas_id`, обов'язковий `swot_id`.
- **Версії.** `Canvas.version`, `Swot.canvas_version`, `Errc.from_version`/`to_version` — 1..5. Версіонування й критерій зупинки лишаються оркестрацією; домен несе значення.
- **Storytelling** — окремий етап: `perspective`, `goal`, `format`, `narrative_text`, `canvas_references` (≥ 1, секція + нотатка).
- **FutureScenario** — `uncertainty_drivers` та `variants` (2–4), кожен варіант із ≥ 1 питанням адаптації по секції.
- **Pitch** — `team_section` ⇔ `team_info_id`, `financial_analysis_section` ⇔ `business_case_id`.
- **BusinessCase / EnvironmentScan** — джерела на рівні кейса (`sources`, `min_length=1`; генерація без джерел — невдала). Кожне `Source` має `retrieved_at` (дата) — вимога ADR-0005 щодо джерела й дати біля кожного зовнішнього кількісного твердження.
- **Межі довжини списків** (правила проєкту; джерела — ADR-0008 D4 і кількість питань у книзі, pp. 220–223): `Ideation.what_if_questions` 1–10; `FutureScenario.uncertainty_drivers` 2–4; `Errc.moves` 1–6; `SwotClusterResult.axis_statements` 2–5; `threats` 1–7; `opportunities` 1–7. Межі однакові для всіх кластерів, хоча в книзі списки різні (загроз: 2, 5, 7, 7): межа для окремого кластера потребувала б валідатора, а генератор його не бачить.
- **Рядки без `max_length`.** Нові схеми не обмежують довжину рядків, тож проблема передчасного обрізання (PR #1) не виникає; піднімати нічого.

### D5. Модуль `consistency`

Валідатор моделі бачить лише її поля; перевірка *між* артефактами — окремий модуль.

- **Два рівні.** *Tier 1 (same referent):* кілька артефактів про одне й те саме (напр. `EmpathyMap` + `CustomerScenario` однієї персони) не суперечать один одному. *Tier 2 (derivation):* вихід етапу перевіряється проти входів, від яких він залежить (`depends_on`) — чи їх використано вірно, а не ігноровано чи вигадано.
- **Дві незалежні осі.** Рівень (Tier 1/2) і спосіб перевірки: **детерміноване правило** (`ConsistencyRule`: чиста функція без I/O й LLM) або **judge check** (`JudgeCheck`: декларація з текстом `instruction`, яку виконує `bizstruct-ml`). Правило може бути будь-якого рівня й будь-якого способу.
- **Чия відповідальність.** Домен: правила, декларації, форма результату (`ConsistencyViolation`, `ConsistencyReport`), `RuleInput` (етап + арність ONE/MANY + `optional`). `bizstruct-be`: збирає екземпляри зі сховища й вирішує групування. `bizstruct-ml`: викликає judge-модель (іншого сімейства, ніж генератор) і розбирає відповідь у `ConsistencyReport`.
- **Виявлення.** `is_checkable(completed)`: усі не-опційні входи завершені; якщо правило оголошує опційні входи, хоча б один із них теж завершений. (Виправлено помилку: два judge-чеки з опційними входами не знаходились за «усі етапи завершені».) Відсутній опційний вхід викликач передає як `None` (ONE) або порожній список (MANY).
- Зараз: 6 детермінованих правил і 6 judge-чеків.

### D6. Санітизація

`SanitizedModel` (`schemas/fields.py`) — база **кожної** моделі пакета (список винятків порожній): перед будь-якою іншою валідацією прибирає NUL та інші керівні символи (залишає `\t\n\r`). Причина — NUL від LLM проходить pydantic, але PostgreSQL `text` його відхиляє, і дефект генерації маскується під тимчасову 5xx. Валідатор повертає **той самий об'єкт**, якщо нічого прибирати, тож значення `StrEnum` і ключі словників лишаються членами enum, а `strict=True` працює. Тест вимагає, щоб кожна модель успадковувала базу.

### D7. Публічний API й контракт з нефронтовими споживачами

- `bizstruct_domain` реекспортує `bizstruct_domain.schemas` (усі моделі, enum, `StageDefinition`, `StageRegistry`, `STAGE_REGISTRY`, типи й реєстри consistency, `CanvasGenerated`) та API стейт-машини (`STAGE_IDS`, `STAGE_TRANSITIONS`, `is_valid_transition`, `dependents_of`, `ready_stages`, `available_actions`). `StageStatus`, `StageErrorCode`, `StageAction` живуть у `schemas/enums.py`.
- **`validate_model`** (`ValidateModelResult`, `FieldFeedback`) збережено як незалежний контракт, не пов'язаний із графом. **У нього немає моделі-предмета**: `BusinessModelOption`/`models_options`, для яких його написано, з графа видалено, тому `FieldFeedback.field` — довільний `str`. Функція чекає на продуктове рішення, що саме вона має валідувати.
- `scripts/export_schemas.py` генерує `<артефакт>.json`, `canvas_generated.json`, `stages.json`, `stage_states.json`, `validate_model.json`; тест порівнює згенероване з закоміченим і вимагає, щоб кожен інший `.json` був у `LEGACY_SCHEMA_FILES` (зараз порожній).

## Що сталося з рішеннями ADR-0008

| Рішення ADR-0008 | Доля | Що тепер |
|---|---|---|
| D1. Межа відповідальності | частково змінено | `Canvas`, `Swot`, `Errc` несуть `version` 1..5, `Swot` має `weighted_weakness_threat_score`; ітерування й зупинка лишаються оркестрацією. Режимів немає (без змін) |
| D2. Тверді й опційні залежності | змінено | `topological_order` враховує обидва види ребер; `ready_stages`: увімкнена опційна залежність блокує споживача |
| D3. Граф із 16 етапів | замінено | 13 етапів (D1 цього ADR) |
| D4. Моделі | здебільшого замінено | `MULTIPLE_EPICENTER` повернено з двобічним правилом; `Patterns` — групи й попарні оцінки замість `segment_count`; `detail_level` немає; `Assessment` → `Swot` з оцінками 1–5 на можливостях/загрозах; бенчмарки з джерелом кожен → `sources` на рівні кейса |
| D5. Storytelling не є етапом | скасовано | `storytelling` — окремий етап |
| D6. `environment_scan` залежить від `empathy_map` | вирішено | залежить лише від `brief` |
| Відкрите питання 1 (`value_map`) | вирішено | видалено |
| Відкрите питання 2 (`models_options`) | вирішено | видалено |
| Відкрите питання 3 (семантика `optional_depends_on`) | лишається вирішеним | домен декларує; `ready_stages` додатково враховує увімкнені опційні входи |

## Constraints that are validator-only

Стан **після** PR #9 і #10. «Видиме генератору» = потрапляє в JSON Schema (`response_format`). Лише `Field`-обмеження (`ge`/`le`/`min_length`/`max_length`) видимі. Нижче — обмеження, які **не** виражено в схемі; це рекомендації, **схеми не змінено**.

| model.field | обмеження | де забезпечується | видиме генератору | рекомендація |
|---|---|---|---|---|
| `SwotAxisStatement.score` | ≠ 0 | `field_validator`; `Field` дозволяє 0 (діапазон −5..5) | ні | `Literal[-5..-1, 1..5]` (відкрите питання 2) |
| `Swot.clusters` | чотири різні типи кластерів | `Field` (рівно 4) + `model_validator`; унікальність невидима | кількість — так, унікальність — ні | у контракті генерації — чотири іменовані поля за `SwotCluster`, як `CanvasGenerated` |
| `Patterns.branch_decision` | відповідає кількості груп (1 ↔ unified, >1 ↔ split) | `model_validator` | ні | не генерувати: виводити з кількості груп оркестратором |
| `Patterns.pattern_tags` | кожен `pattern` не більш ніж раз | `model_validator` (`Field`: лише `max_length=5`) | частково (довжина) | дискримінований вхід за `pattern` або дедуплікація в оркестраторі |
| `Patterns.pattern_tags` | `MULTI_SIDED_PLATFORM` ⇒ група `MULTI_SIDED` з ≥ 2 картами | `model_validator` | ні | перевірка й повтор у ML; опційно — описати в `description` |
| `PatternTag.subtype` | тип підтипу залежить від `pattern` | `model_validator` | ні | дискримінований union: тег на кожен `pattern` зі своїм enum підтипу |
| `EpicenterClassification.tags` | двобічне правило маркера, унікальність, ≥ 1 конкретний | `model_validator` | ні (лише в `description`) | генерувати `concrete` (1–4, унікальні), а маркер виводити з його довжини |
| `ErrcMove` | `action` ↔ `new_text`/`target_card_text` | `model_validator` | ні | дискримінований union за `action` (CREATE: `new_text`; інші: `target_card_text`) |
| `Errc.to_version` | `from_version + 1` | `model_validator` (`Field`: `ge=2`, `le=5`) | частково | не генерувати версії: призначає бекенд |
| `SegmentPair.empathy_map_id_a/b` | різні | `model_validator` | ні | оркестратор будує пари з комбінацій; генератор оцінює готові пари |
| `Pitch.team_section`, `financial_analysis_section` | присутні ⇔ відповідний `*_id` | `model_validator` | ні | контракт генерації залежно від доступних входів (без поля, якщо входу немає) |
| `Canvas` (збережена форма) | 2–4 картки на секцію, якщо `is_generated` | `model_validator` | ні; для генератора покрито `CanvasGenerated` (`minItems`/`maxItems`) | прибрати валідатор, лишити 2–4 лише в `CanvasGenerated` (відкрите питання 1) |

Не потрапляють у таблицю: статичні валідатори `StageRegistry` (конфігурація, не вихід LLM), та міжартефактні перевірки (`consistency`).

## Consumer migration notes

Усі три споживачі закріплені на старих SHA/тегах, тож нічого не ламається до підняття пінів.

**Ідентифікатори етапів, 16 → 13**

| було | стало |
|---|---|
| brief, team_info, business_case, empathy_map, environment_scan, customer_scenario, ideation, patterns, canvas, pitch | без змін |
| assessment + errc | `swot_errc_cycle` (один вузол) |
| scenario | `future_scenario` |
| value_map, models_options, hypotheses | видалено, відповідника немає |
| — | `storytelling` (новий) |

**Артефакти:** видалено `Hypotheses`/`Hypothesis`, `ModelsOptions`/`BusinessModelOption`, `Assessment` (→ `Swot`), `ERRC*` (→ `Errc`/`ErrcMove`, без `*Generated`), `FutureScenarioCase` (→ `FutureScenarioVariant`), `CostItem`, `MarketBenchmark`, `ScenarioQuestion`. `Ideation.epicenters` → `epicenter`; `Patterns` змінено (групи, попарні оцінки).

**`Canvas.sections`:** дев'ять секцій більше не поля верхнього рівня — вони в `sections`; картки `{id: str, text, errc_marker}`; нові `group_id`, `version`, `is_final`, `is_generated`. **`CanvasSection.key_partners` → `key_partnerships`.** `CanvasGenerated` — лише текстові чернетки, 2–4 на секцію.

**Enum:** `SWOTCluster` → `SwotCluster`; `ERRCAction` → `ERRCActionType`; `CanvasBranchingDecision` (`a_shared`/`b_branching`) → `CanvasBranch` (`unified_model`/`split_model`); `PatternSubtype` → `FreePatternSubtype` + `OpenBusinessModelPatternSubtype`; `Epicenter` отримав `multiple_epicenter`; видалено `HypothesisCategory`, `Quadrant`, `ERRCStatus`, `PitchAudience`, `MonetizationType`, `ScenarioAdaptationArea`, `CanvasDetailLevel`. Кореневий `Stage` (pydantic-модель із `STAGES`, `topological_order`, `validate_dag`) тепер `Stage` (`StrEnum`) + `STAGE_REGISTRY`. Шляхи `bizstruct_domain.blocks.*`, `.chain`, `.enums`, `.sanitize`, `.validate_model` більше не існують.

**bizstruct-be:** рядки зі старими типами етапів падатимуть з `unknown stage id` (`ready_stages`, `dependents_of`), а збережений JSON канв має старі ключі секцій (`key_partners`, пласка структура) — **потрібна міграція даних** (мапа етапів вище; JSON канви перебудувати в `sections`, `key_partners` → `key_partnerships`). `ready_stages` отримав `enabled_optional` і правило рівня типу, повертає члени `Stage`.

**bizstruct-fe:** перейти з `chain.json` на `stages.json` (лише структура); тримати мапу `id → назва` і gates у fe з тестом на повноту; перегенерувати типи з нових файлів.

**bizstruct-ml:** `ValidateModelResult` тепер у `bizstruct_domain.ValidateModelResult` (`field` — `str`); генератори переводяться на нові моделі.

## Відкриті питання

1. **`Canvas.generated_card_count`.** Коли ERRC редагує канву, секція може законно мати 1 або 5 карток, тому валідатор змушує `is_generated=False` для таких версій, і прапорець змішує «відредаговано людиною» та «відредаговано ERRC». Рекомендація: прибрати валідатор, лишити правило 2–4 лише в `CanvasGenerated`. Наразі лишається як є.
2. **`SwotAxisStatement.score`:** лишити `int` + валідатор чи перейти на `Literal[-5..-1, 1..5]`, щоб схема забороняла 0. Наразі лишається як є.
3. **Порівнянність `weighted_weakness_threat_score` між ітераціями.** Межа 1–7 загроз на кластер не робить суму порівнянною: вона залежить від кількості загроз, які модель вирішила перелічити. Варіанти: порівнювати середнє на загрозу або оцінювати фіксований каталог із 21 питання про загрози з книги.
4. **Предмет `validate_model`** (D7): що саме функція має валідувати після видалення `models_options`. Рішення за власником продукту.

## Consequences

- **Твердження ADR-0005, що конвеєр не має зовнішніх джерел даних, для `environment_scan` і `business_case` застаріло:** ці два етапи звертаються до зовнішніх джерел і в конвеєрі, тож джерело й дата є частиною їхнього контракту.
- **Одне дерево моделей.** Є один публічний шлях імпорту й одне місце, де перелічено enum, моделі й граф; `blocks/` і кореневі `chain.py`/`enums.py` видалено.
- **Міжартефактні перевірки відокремлено від валідаторів моделі** й від I/O: правила чисті, judge-чеки декларативні.
- **Частина обмежень невидима генератору** (таблиця вище): їхнє порушення виявляється після генерації й вимагає повтору. Рекомендації в таблиці — спосіб перенести їх у схему, не змінюючи доменних правил.
- **Ламаюча зміна** (0.12.0): форма канви, ключ секції, ідентифікатори етапів, імена enum. Потрібні міграції даних у бекенді й регенерація типів у фронтенді.
- **Критерій зупинки ще не порівнянний між ітераціями** (питання 3), тож оркестрація не може покладатися на абсолютне значення.

## Alternatives considered

- **Лишити режими Basic/Pro.** Відхилено (як і в ADR-0008): режим — продуктове рішення, а не властивість методології; опційні залежності виражають ту саму асиметрію.
- **Тримати `assessment` і `errc` окремими вузлами.** Відхилено: це один цикл; два вузли змушували б граф описувати ітерацію.
- **Робити межі списків специфічними для кластера валідаторами.** Відхилено: генератор валідаторів не бачить, а різні межі по кластерах потребували б їх.
- **Санітизація через `Annotated`-тип рядка.** Відхилено: треба пам'ятати про кожне поле (`str | None`, `list[str]`, вкладені структури), а базовий клас покриває все автоматично і перевіряється одним тестом.
- **Розв'язувати готовність етапу на рівні екземплярів.** Відхилено на цьому етапі: у графа немає зв'язків між екземплярами; рівень типу консервативний, але чесний щодо наявних даних.
- **Підтримувати лише валідатори без контрактів генерації.** Відхилено для канви (`CanvasGenerated`): межу краще передавати моделі через `response_format`, ніж виявляти після факту.
