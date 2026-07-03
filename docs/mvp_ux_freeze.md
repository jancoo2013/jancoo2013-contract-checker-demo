# MVP UX freeze

This document freezes the user-facing UX target for the closed Streamlit MVP.

The goal is not to describe the internal pipeline. The goal is to keep the testing flow understandable for a user who uploads one or more rental-contract pages and wants a Russian report.

## Core UX principle

The main page must tell the user what to do next, not expose how the system is built.

Current internal pipeline concepts such as prepared pages, cache status, raw Gemini responses, prompt versions, and OCR internals must remain available only in collapsed Advanced or developer-only sections.

## App-level constraints

- Do not add intelligence to `app.py`.
- Keep `app.py` as Streamlit UI/session glue.
- Testable privacy/OCR/analysis logic should live in small modules under `contract_checker/`.
- Do not add broad refactors while making UX changes.
- Prefer small, focused PRs.
- Do not change privacy, OCR, Gemini, schema, cache, evidence validation, or report behavior as part of a UX-only patch.

## Target user-facing flow

The normal MVP flow should have four visible sections:

1. Upload
2. Mask & review
3. OCR
4. Analysis & report

The user should be able to test one contract page without opening any Advanced section.

## Section 1: Upload

User-facing title:

```text
1. Загрузка договора
```

Primary action:

```text
Загрузи фото или изображение страницы договора
```

After upload, show a compact status such as:

```text
Загружено страниц: 1
```

Do not show hashes, content types, internal signatures, or session details outside Advanced sections.

## Section 2: Mask & review

User-facing title:

```text
2. Закрой личные данные
```

Short instruction:

```text
Закрой имена, ת.ז., телефоны, адреса, банковские данные, подписи и рукописные вставки.
```

Allowed visible actions:

```text
Добавить маску по клику
Добавить прямоугольную маску
Отменить последнюю маску
Очистить маски на странице
```

Required user confirmation:

```text
Я проверил страницу: личные данные закрыты или отсутствуют
```

Technical mask details should stay collapsed under:

```text
Advanced: технические детали масок
```

## Section 3: OCR

User-facing title:

```text
3. Распознать текст
```

There should be one primary OCR action:

```text
Распознать замаскированные страницы
```

This action may internally prepare redacted OCR pages and run Temporary Gemini OCR. The user should not have to perform a separate visible step called `Create redacted OCR pages`.

If pages are not confirmed, show a direct blocking message:

```text
Сначала отметь страницу как проверенную в блоке 2.
```

After OCR succeeds:

```text
Текст распознан. Проверь качество ниже.
```

Raw OCR text, OCR cache status, prepared-page details, and OCR technical metrics must stay collapsed under Advanced sections.

## Section 4: Analysis & report

User-facing title:

```text
4. Анализ и отчёт
```

Primary action:

```text
Запустить анализ договора
```

After analysis, show the report under:

```text
Отчёт
```

Advanced model settings, raw Gemini responses, validation metrics, and debug JSON must stay collapsed.

## Warnings and disclaimers

Keep one short warning near the top:

```text
Прототип: не юридическая консультация. Проверяет только загруженный текст.
```

Longer legal, privacy, prototype, and model-limit warnings should be placed under a collapsed section:

```text
Advanced: ограничения прототипа
```

Do not repeat the legal disclaimer throughout the normal path unless a specific action requires it.

## Sidebar policy

The normal MVP should not show legacy or developer pages in the Streamlit sidebar.

Developer pages may be kept outside Streamlit's auto-discovered `pages/` directory, for example under:

```text
dev_pages_disabled/
```

## Privacy wording

The app may tell the user to mask personal data, but it must not rely on a checkbox as the only privacy protection.

Safe wording:

```text
Я проверил страницу: личные данные закрыты или отсутствуют
```

Avoid wording that claims the page is legally safe, fully anonymous, or free of all personal data.

The UI may show risk zones or region hints, but it must not expose extracted personal values.

## Forbidden UX outcomes

Do not make the user do the following in the normal path:

- manually create prepared OCR pages;
- understand cache internals;
- understand Gemini prompt/config details;
- open legacy sidebar pages;
- read repeated legal disclaimers;
- choose a model before the first successful OCR test;
- use manual text fallback for the normal photo/image flow;
- open Advanced sections to complete a basic one-page test.

## Manual smoke test: one page

A successful one-page test should work as follows:

1. Open the app.
2. Confirm the sidebar does not show legacy/developer pages.
3. See the four visible sections:
   - `1. Загрузка договора`
   - `2. Закрой личные данные`
   - `3. Распознать текст`
   - `4. Анализ и отчёт`
4. Upload one image.
5. Add at least one mask if the page contains personal or handwritten data.
6. Check:
   `Я проверил страницу: личные данные закрыты или отсутствуют`
7. Click:
   `Распознать замаскированные страницы`
8. Do not manually search for a separate prepare-pages step.
9. Review OCR quality if the app surfaces a visible issue.
10. Click:
    `Запустить анализ договора`
11. Receive the report.
12. Complete the path without opening any Advanced section.

If a tester must open Advanced to complete this path, the UX is still too complex.

## PR sequencing

Preferred sequence:

1. Hide legacy sidebar pages.
2. Add this UX freeze.
3. Simplify the main testing flow into four sections.
4. Add read-only handwriting-risk status display.
5. Add conservative privacy gate only after template-safe handling is clear.
6. Add auto-mask suggestions later, not as part of the first UX cleanup.
