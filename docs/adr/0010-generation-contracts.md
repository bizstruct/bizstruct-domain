# ADR-0010: Контракти генерації та правило системних полів

- **Status:** Accepted
- **Date:** 2026-10-04
- **Supersedes:** —
- **Related:** ADR-0009 (граф, схеми, модуль узгодженості; цей ADR уточнює його D5), ADR-0005 (джерело й дата для зовнішніх кількісних тверджень)

---

## Context

`bizstruct-ml` переписується поверх цього пакета (транспорт — черга, без FastAPI). LLM отримує JSON Schema моделі як `response_format`. До цього ADR лише `Canvas` мав окрему модель часу генерації (`CanvasGenerated`). Усі інші артефакти вимагають системних полів — ідентифікаторів, зовнішніх ключів, версій, — які LLM не повинна вигадувати. Перевірена кількість таких полів у збереженій моделі:

| артефакт | системних полів |
|---|---|
| EmpathyMap | 2 |
| CustomerScenario | 2 |
| Ideation | 2 |
| Patterns | 2 (+ ідентифікатори груп) |
| Swot | 4 |
| Errc | 6 |
| Storytelling | 2 |
| FutureScenario | 2 |
| Pitch | 7 |
| BusinessCase | 2 |
| EnvironmentScan | 2 |
| TeamInfo | 2 |

Якби LLM отримувала збережену модель як схему, вона мусила б вигадувати ці значення; помилка не виявлялася б валідаторами моделі (рядок є рядком), а потрапляла б у зовнішні ключі та версії. Окремо: `sources` у `BusinessCase`/`EnvironmentScan` разом із `retrieved_at` — факти кроку пошуку, а не продукт генерації, і LLM не має їх писати.

## Decision

### D1. Правило системних полів

**Контракт генерації містить лише те, що пише LLM.** З нього виключено: `id`, `*_id`, `*_ids`, поля версій, `is_final`, `is_generated` і будь-яке значення, що має надходити з реального джерела (`sources`, `retrieved_at`). JSON Schema контракту — це `response_format`.

### D2. Зміст визначено один раз; валідатори розділено

Поля змісту оголошуються в моделі генерації. Збережена модель **розширює** її й додає системні поля (`EmpathyMap(EmpathyMapGenerated)` додає `id`, `project_id`). Валідатори, яким потрібні лише поля змісту, живуть на моделі генерації — тому спрацьовують, коли розбирається вихід LLM (`SwotGenerated.clusters_cover_all_types`). Валідатори, що зачіпають системні поля, лишаються на збереженій моделі (`Errc.version_increments`, `Pitch.optional_sections_match_ids`). Вкладені моделі (`ErrcMove`, `PatternTag`, `EpicenterClassification`, …) спільні для обох.

| етап | контракт генерації | системні поля збереженої моделі |
|---|---|---|
| `brief` | `Brief` (власний контракт, системних полів немає) | — |
| `empathy_map` | `EmpathyMapGenerated` | `id`, `project_id` |
| `customer_scenario` | `CustomerScenarioGenerated` | `id`, `empathy_map_id` |
| `ideation` | `IdeationGenerated` | `id`, `empathy_map_id` |
| `patterns` | `PatternsGenerated` (без успадкування, див. D4) | `id`, `project_id`, `branch_decision`, ідентифікатори груп |
| `canvas` | `CanvasGenerated` (без змін) | `id`, `group_id`, `empathy_map_ids`, `version`, `previous_version_id`, `is_final`, `is_generated`, id карток |
| `swot_errc_cycle` | `SwotGenerated` (кластери) і `ErrcGenerated` (ходи) | Swot: `id`, `canvas_id`, `canvas_version`, `environment_scan_id`; Errc: `id`, `canvas_id`, `swot_id`, `from_version`, `to_version`, `result_canvas_id` |
| `storytelling` | `StorytellingGenerated` | `id`, `canvas_id` |
| `future_scenario` | `FutureScenarioGenerated` | `id`, `canvas_id` |
| `pitch` | `PitchGenerated` | `id`, `project_id`, `storytelling_id`, `canvas_id`, `swot_id`, `team_info_id`, `business_case_id` |
| `business_case` | `BusinessCaseGenerated` | `id`, `project_id`, `sources` |
| `environment_scan` | `EnvironmentScanGenerated` | `id`, `project_id`, `sources` |
| `team_info` | немає: ввід користувача | — |

Публічна відповідність `GENERATION_CONTRACTS: dict[Stage, tuple[type, ...]]` містить кожен етап, крім `team_info`; у `swot_errc_cycle` два контракти, в інших один. У `PitchGenerated` поля `team_section` і `financial_analysis_section` мають тип `str | None`; невідповідність «секція ⇔ id» виявляє збережена модель під час конвертації.

### D3. Хто що постачає

| джерело | значення |
|---|---|
| **система** (`bizstruct-be` / оркестратор) | `id`, зовнішні ключі, версії, `is_final`, `is_generated`, ідентифікатори груп і карток |
| **крок пошуку** | `sources` разом із `retrieved_at` (`BusinessCase`, `EnvironmentScan`); LLM ніколи не пише `retrieved_at` |
| **виводиться** | `Patterns.branch_decision` (одна група — `unified_model`, інакше `split_model`) |

### D4. Patterns: аліаси сегментів

Структура `Patterns` відрізняється від збереженої (посилання на сегменти, групи без `id`), тому успадкування тут не працює. `PatternsGenerated` містить `pairwise_scores`, `groups` і `pattern_tags`, де сегменти задано **аліасами** — рядками на кшталт `"S1"`, які визначає промпт, — а не реальними ідентифікаторами. Причини: LLM не повинна копіювати або вигадувати довгі ідентифікатори (помилка в одному символі дає висячу посилку, яку не бачить жоден валідатор); аліаси дозволяють перевіряти контент (пара з двох різних аліасів, група `MULTI_SIDED` із ≥ 2 сегментами) до того, як відомі реальні id; відповідність аліас → id належить системі. Ідентифікатори груп і `branch_decision` — системні.

Валідатори на `PatternsGenerated`: два аліаси пари різні; `MULTI_SIDED_PLATFORM` вимагає групи, що **одночасно** `MULTI_SIDED` і має ≥ 2 сегментів; кожен патерн позначено не більш ніж раз; правило підтипу — це `PatternTag` без змін. Правила спільні зі збереженою `Patterns` (одні й ті самі функції).

### D5. Конвертація

Чиста функція, без I/O; ідентифікатори передає викликач.

- `X.from_generated(generated, **system_fields)` на збережених моделях: `model_validate({**generated.model_dump(), **system})`, тож усі валідатори збереженої моделі спрацьовують; `ValidationError` — сигнал невідповідності.
- `Canvas.from_generated(generated, *, id, group_id, empathy_map_ids, version=1, previous_version_id=None, new_card_id)`: `new_card_id` викликається один раз на картку в порядку секцій; `errc_marker` порожній, `is_generated` істинний.
- `patterns_from_generated(generated, *, id, project_id, segment_ids, group_ids) -> Patterns`: відображає аліаси на id, `ValueError` на невідомий аліас або коли `len(group_ids)` не збігається з кількістю груп, виводить `branch_decision`.

### D6. Перевірки узгодженості виконує `bizstruct-ml` (уточнює ADR-0009 D5)

ADR-0009 D5 покладав збирання екземплярів зі сховища на `bizstruct-be`, а judge-модель — на `bizstruct-ml`. Тепер `bizstruct-ml` отримує повний стан проєкту, тому **і детерміновані правила, і judge-чеки виконує ml**: має всі екземпляри й сам вирішує групування. `bizstruct-be` зберігає результат (`ConsistencyReport`) і застосовує переходи стейт-машини. Межа домену не змінюється: правила — чисті функції, judge-чеки — декларації, жодного I/O чи LLM у пакеті.

### D7. Експорт

Для кожного контракту є `schemas/<артефакт>_generated.json` (як `canvas_generated.json`); `brief.json` — контракт `brief`. Схеми збережених моделей не змінилися, крім порядку елементів масиву `required` (поля змісту тепер ідуть перед системними).

## Consumer migration notes (0.13.0)

Зміна додає API та не змінює форму збережених даних, тож версія — мінорна.

- **bizstruct-ml:** брати `response_format` з `GENERATION_CONTRACTS[stage]` (а не зі збережених моделей); після розбору викликати `from_generated`, передаючи системні поля; для `patterns` — визначити в промпті аліаси та викликати `patterns_from_generated`; для `business_case`/`environment_scan` постачати `sources` із кроку пошуку; виконувати перевірки узгодженості (D6).
- **bizstruct-be:** видавати ідентифікатори, версії та `new_card_id`; зберігати `ConsistencyReport`, що надходить від ml; більше не збирати екземпляри для перевірок узгодженості.
- **bizstruct-fe:** нових обов'язкових змін немає; з'явилися файли `*_generated.json`, їх можна ігнорувати (контракт між ml і доменом). Типи збережених моделей збігаються з попередніми, крім порядку `required`.

## Відкриті питання

1. **Формат аліасів і текст промпту** належать `bizstruct-ml`; домен перевіряє лише, що аліас непорожній і пара складається з різних аліасів.
2. **Точний каталог загроз у `SwotGenerated`** лишається валідатором (ADR-0009: рекомендація — контракт із чотирма іменованими полями кластерів); у схемі видно лише діапазон 2..7 та enum із 21 значення.
3. **Звірка аліасів між `pairwise_scores` і `groups`** (чи кожен аліас пари належить якійсь групі) не входить у `PatternsGenerated`; її можна додати як правило узгодженості, якщо ml цього потребуватиме.

## Consequences

- LLM більше не бачить і не пише системних полів: їхні помилки неможливі за конструкцією, а не виявляються постфактум.
- Збережена модель «є» моделлю генерації плюс системні поля; зміст оголошено один раз, тож контракт і збережена форма не розходяться.
- Обидві форми Patterns (збережена й генерації) використовують спільні функції правил; зміна правила діє на обидві.
- Перевірки узгодженості переїжджають до ml: be не потребує знання про групування для цих перевірок, але залежить від ml у частині `ConsistencyReport`.

## Alternatives considered

- **Одна модель із необов'язковими системними полями.** Відхилено: схема показувала б LLM поля `id`, які вона мала б залишати порожніми; обов'язковість у збереженій формі втрачалась би.
- **Виключати системні поля під час серіалізації (`exclude`).** Відхилено: `exclude` не змінює JSON Schema, тож `response_format` усе одно містив би їх.
- **Реальні id у промпті для Patterns.** Відхилено: довгі ідентифікатори LLM копіює з помилками; аліаси роблять контент перевірюваним до відомих id.
- **Окремі дубльовані моделі без успадкування для всіх артефактів.** Відхилено: зміст довелося б підтримувати у двох місцях; успадкування залишає одне оголошення.

## Decisions made after acceptance

**2026-10-08, версія 0.16.0** (ADR-0012). `Canvas.is_final` видалено з моделі: фінальну версію виводять функції `schemas/cycle.py`. Рядки таблиць вище, що називають `is_final` серед системних полів, лишено як історію; у збереженій `Canvas` цього поля більше немає, а `CanvasGenerated` його ніколи не містив.
