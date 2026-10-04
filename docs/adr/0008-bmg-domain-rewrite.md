# ADR-0008: Перепис доменної моделі під методологію BMG

- **Status:** Superseded by [ADR-0009](0009-stage-graph-and-schemas.md)
- **Date:** 2026-09-26
- **Supersedes:** ADR-0001 (склад і порядок етапів); ADR-0005 §2 у частині `StageMode.PRO_ONLY`
- **Related:** ADR-0005 (агентний режим)

---

## Context

Звірка `chain.py` і блокових моделей з методологічним документом «BizStruct — Методологія генерації (BMG)» показала структурні розбіжності:

1. **Порядок.** `architecture` (епіцентр + патерн) обчислювався *після* канви, хоча за BMG епіцентр (Ideation, стор. 136–141) і патерни (Patterns, стор. 56–119) — вхідні дані канви, а не її прочитання постфактум.
2. **Злиті сутності.** `architecture` поєднував два різні кроки книги — Ideation (епіцентр + «What if») і Patterns (класифікатор структури + рішення А/Б), — і модель мала рівно один патерн, хоча книга допускає 0–5.
3. **Відсутні кроки.** Customer Scenario (Scenarios, тип 1), Team Info і Business Case як опційні входи пітчу.
4. **Колізія імен.** `what_if` позначав Blue Ocean ERRC-крок, а в книзі «What if…?» — техніка Ideation, інший, ранній крок.
5. **`scenario`** був сценарієм «до/після» без опори на розділ Scenarios; у BMG тип 2 — стрес-тест фінальної канви (future scenarios).
6. **`StageMode` у домені.** Режим Basic/Pro визначав валідність графа («BOTH не залежить від PRO»), через що граф з `errc → assessment` (SWOT — Pro) не проходив `validate_dag()`.

Бек і ML-воркер ще не мають production-реалізацій цих етапів, тому домен переписано, а не залатано.

## Decision

### D1. Межа відповідальності пакета

Домен типізує **форму одного проходу**. Поза пакетом, у `bizstruct-be`/`bizstruct-ml`:

- **Множинність** — скільки екземплярів етапу має проєкт (карта емпатії на сегмент, одна або N канв після рішення А/Б) і як вони пов'язані.
- **Цикл Canvas → SWOT → ERRC** — версіонування ітерацій і критерій зупинки (зважена за `importance` сума Weaknesses + Threats). Домен лише несе поля `importance`/`certainty`, нічого не обчислює.
- **Продуктові режими (Basic/Pro).** `StageMode` і `stages_for_mode()` видалено. Домен описує один повний граф; яку підмножину запускати — рішення бека.

`tests/test_contract.py` фіксує цю межу, щоб наступна зміна не повернула її в домен неявно (немає `mode`/`cardinality` на `Stage`, немає експортованих `*Iteration`/`*Variant`/`*Version`).

### D2. Тверді й опційні залежності

`Stage.depends_on` — тверді: без них етап генерувати не можна. `Stage.optional_depends_on` — опційні: підвищують повноту, якщо присутні.

| Функція | Які ребра враховує | Чому |
|---|---|---|
| `topological_order()` | лише тверді | порядок визначають обов'язкові входи; нічия — за позицією в `STAGES` |
| `stage_machine.ready_stages()` | лише тверді | опційний вхід ніколи не блокує запуск |
| `stage_machine.dependents_of()` | тверді + опційні | питання «що застаріло, якщо змінився X»: результат, який міг спожити опційний вхід, застарів разом з ним |
| `validate_dag()` | обидва | невідомі id, дублювання в обох списках, цикли окремо в твердому графі й у графі тверді + опційні |

`STAGES` упорядковано так, що навіть опційні входи йдуть перед споживачами, — тому типовий порядок генерує їх першими, якщо вони взагалі запускаються.

### D3. Новий граф

| id | depends_on | optional_depends_on | source |
|---|---|---|---|
| `brief` | — | — | — |
| `team_info` | — | — | BMG, Outlook → Business Plan (p. 268) |
| `business_case` | brief | — | BMG, Prototyping (p. 165) + Business Plan, Financial Analysis (p. 269) |
| `empathy_map` | brief | — | BMG, Customer Insights |
| `environment_scan` | brief, empathy_map | — | BMG, Business Model Environment |
| `value_map` | empathy_map | — | Value Proposition Design (див. відкрите питання 1) |
| `customer_scenario` | empathy_map | — | BMG, Scenarios, тип 1 (pp. 182–185) |
| `ideation` | brief, empathy_map | — | BMG, Ideation (pp. 136–141) |
| `patterns` | customer_scenario, ideation | — | BMG, Patterns (pp. 56–119) |
| `models_options` | value_map, patterns | — | BMG, Ideation (розширення проєкту, див. відкрите питання 2) |
| `canvas` | empathy_map, value_map, customer_scenario, patterns, models_options | — | BMG, ядро |
| `assessment` | canvas, patterns | environment_scan | BMG, Evaluating Business Models (pp. 212–225) |
| `errc` | canvas, patterns | assessment | BMG, Blue Ocean Strategy (pp. 226–231) |
| `hypotheses` | canvas, errc | — | Testing Business Ideas |
| `scenario` | canvas | — | BMG, Scenarios, тип 2 (pp. 186–189) |
| `pitch` | canvas, errc, scenario | team_info, business_case | BMG, Storytelling (pp. 170–179) + Business Plan (pp. 268–269) |

Перейменування id: `architecture` → `ideation` + `patterns`; `what_if` → `errc`. `scenario` лишає id, але змінює зміст (future scenario).

### D4. Моделі

- **`Ideation`** — `epicenters: list[Epicenter]` (1–4, без повторів) + `what_if_questions` (1–10). Згідно з BMG, епіцентр — лише класифікатор без окремого тексту-обґрунтування.
- **`Epicenter.MULTIPLE_EPICENTER` видалено.** Книга описує «multiple-epicenter driven» як поєднання кількох епіцентрів, а не як п'ятий тип. Множинність виражає довжина `Ideation.epicenters`; окреме значення дублювало б ту саму семантику на двох рівнях і дозволяло б суперечливий стан (`[multiple_epicenter]` без жодного конкретного епіцентру).
- **`Patterns`** — `pattern_tags: list[PatternTag]` (0–5, патерн без повторів; кожен тег із `subtype` та `rationale`, валідатор підтипу перенесено з `Architecture`), `branching_decision: CanvasBranchingDecision`, `branching_rationale`.
  - **`segment_count`** (≥ 1) — кількість пар customer_scenario/ideation, над якими зроблено класифікацію. Це єдине поле, через яке множинність торкається домену, і лише як *вхідний факт*, а не механізм. Без нього неможливі валідатори `multi_sided_platform ⇒ ≥ 2 сегменти` (вимога книги, pp. 76–79) і `b_branching ⇒ ≥ 2 сегменти` (правило проєкту: одна канва на сегмент при одному сегменті — це `a_shared`). Заповнюється викликачем з входів етапу, а не судженням LLM.
  - Шаблони розкладки канви для кожного патерну (напр. pp. 86–87) — статичне довідкове знання, не згенерований вихід, тому не є полем моделі.
- **`CustomerScenario`** — `persona`, `situation`, `open_questions` лише про Channels / Customer Relationships / Revenue Streams, по кожному з трьох — щонайменше одне.
- **`Canvas.detail_level: CanvasDetailLevel`** — типово `elaborated`, тож наявні збережені канви лишаються валідними. У `CanvasGenerated` правило 2–4 картки застосовується до секцій, обов'язкових для рівня: `napkin` — лише VP і R$ (решта 0–4), `elaborated`/`business_case` — усі дев'ять.
- **`Assessment`** — чотири кластери (`SWOTCluster`, відображення на блоки — `SWOT_CLUSTER_SECTIONS`) × S/W/O/T, кожен пункт `SWOTStatement(text, importance 1–10, certainty 1–10)`. Книга задає `importance`/`certainty` для S/W; на O/T вони — **розширення проєкту**, бо критерій зупинки циклу зважує Threats за `importance`. Шкалу 1–5 strong↔weak з книги не винесено окремим полем: напрям уже задає квадрант.
- **`FutureScenario`** — `uncertainty_drivers` (2–4; верхня межа — правило проєкту, книга радить «кілька») і `scenario_matrix` (2–4 `FutureScenarioCase`: назва, наратив, питання адаптації по `ScenarioAdaptationArea` без повторів).
- **`ERRC`** (з `WhatIf`; `ERRCAlternative`, `ERRCGenerated`, `ERRCStatus`) — валідатори без змін. Кількості (3 альтернативи, 3–6 ходів, ≥ 3 різні дії) позначено в докстрінгу як правило проєкту, а не цитату методології.
- **`TeamInfo`** — ввід користувача (учасники, роль, досвід, компетенції, опційне резюме).
- **`BusinessCase`** — бенчмарки (кожен з `source` і `retrieved_at` — вимога ADR-0005 щодо зовнішніх кількісних тверджень), формула беззбитковості, три сценарії продажів у фіксованому порядку, капітальні/операційні витрати, потреба у фінансуванні, прибутковий потенціал.
- Колекції — `list[...]`, а не `tuple[...]`, як у всіх наявних блоках (CRUD у беку мутує списки). JSON Schema однакова. Значення enum у snake_case (`a_shared`, `b_branching`), як усі наявні enum пакета.

### D5. Storytelling не є окремим етапом

BMG описує Storytelling (крок 10, pp. 170–179) як окремий крок, з якого пітч бере наратив. У цьому переписі його **згорнуто в `pitch`**, модель `Pitch` не змінено. Це свідомий борг: якщо наратив (протагоніст, перспектива, ціль, формат подачі) знадобиться окремо від пітчу, це буде новий етап `storytelling` (`depends_on: canvas`) і `pitch` залежатиме від нього.

### D6. Розбіжність, збережена свідомо

`environment_scan` лишається з `depends_on = (brief, empathy_map)`, як вимагає постановка задачі («не чіпати»). BMG описує його входом лише domain/industry з Brief. Якщо це підтвердиться, треба прибрати `empathy_map` — це зробить аналіз середовища доступним раніше, але зміст графа не зміниться.

## Відкриті питання

### 1. `value_map` / Value Proposition Design — **відкладено, лишається як є**

BMG.md заявляє рамку «без VPD», а `value_map` — саме VPD. Варіанти:

- **(а) прибрати `value_map`.** Value Proposition формується прямо в `canvas`; `canvas` і `models_options` втрачають цю залежність. Моделі й генераторів `value_map` ще немає ні в домені, ні в `bizstruct-be`/`bizstruct-ml`, тож вартість мінімальна.
- **(б) лишити як явне розширення** й оновити BMG.md.

Наразі етап лишається з `source="Value Proposition Design"`. Рішення за власником продукту до реалізації генератора `value_map`.

### 2. `models_options` — **відкладено, лишається окремим етапом після `patterns`**

Прямого відповідника в методології немає; найближчий — фінансово орієнтований патерн усередині `patterns`/епіцентр `finance_driven`. Варіанти: (а) лишити окремим етапом (поточний стан: є модель, генератор у ml і user gate у беку); (б) перенести в `patterns`/`ideation`. Етап лишається в графі після `patterns`, `source` позначає його як розширення проєкту. Перенесення також зачіпає двохрівневий пошук з ADR-0005 §4, тому вирішується разом з ним.

### 3. Семантика `optional_depends_on` для споживачів — **вирішено**

Домен лише декларує, що вхід опційний (докстрінг `Stage`, D2). Поза доменом:

- **`bizstruct-be`** вирішує, чи чекати на опційний вхід перед запуском (напр. у Pro чекати на `assessment` перед `errc`, у Basic — ні), і відстежує, чи результат фактично його спожив.
- **`bizstruct-ml`** вирішує, як генерувати без опційного входу: промпт, очікувана повнота (SWOT без environment scan — O/T лише з канви; ERRC без SWOT — менш обґрунтовано; пітч без team_info/business_case — без відповідних розділів).

## Consequences

**Ламаюча зміна для всіх споживачів** (версія 0.11.0). Споживачі закріплені на SHA, тож нічого не ламається до підняття пінів. Перевірено прогоном їхніх тестів проти нового домену:

- **bizstruct-be:** `IMPLEMENTED_BLOCKS` містить `what_if`/`architecture` — `RuntimeError` при імпорті `app.block_chain`. Також: колонка `Project.what_if`, `routers/blocks.py` (CRUD `WhatIf`, `Scenario`), `schemas.py`, `seed.py`, `services/*` (`ready_stages` без `pro`).
- **bizstruct-ml:** `topological_order(pro=False)` у `llm/prompts/_shared.py` — `TypeError`; `generators/base.py` імпортує `blocks.what_if`/`blocks.architecture`; генератори `architecture` і `scenario` (до/після) треба замінити.
- **bizstruct-fe:** регенерувати типи з `schemas/` (`chain.json` без `mode`, з `optional_depends_on`; нові `ideation`/`patterns`/`errc`/…; `architecture.json`/`what_if.json` видалено).

Contract tests споживачів оновлюються разом з міграцією їхнього коду під 0.11.0. Окремо від неї оновлення тестів не має сенсу: проти закріпленої версії вони падатимуть.

## Alternatives considered

- **Типізувати множинність у домені** (`cardinality: SINGLETON | PER_SEGMENT | PER_CANVAS_VARIANT`, `CanvasVariant`, `CanvasIteration`). Відхилено до цього переписування: створення й зв'язування екземплярів — оркестрація, і домен, що її моделює, дублював би стан бека.
- **Лишити `StageMode` і зробити `assessment` BOTH.** Відхилено: режим — продуктове рішення, а не властивість методології. Опційні залежності виражають ту саму асиметрію («SWOT корисний, але не обов'язковий для ERRC») без прив'язки до тарифу.
- **Цикл Canvas → SWOT → ERRC ребром графа.** Відхилено: граф має лишатися ациклічним; цикл — версіонування поверх одного проходу, а не залежність між етапами.
