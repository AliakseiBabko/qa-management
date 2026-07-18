# Промпт: базовые метрики из репозитория автотестов

Назначение: дать QA-инженеру на проекте готовый промпт, который можно
скормить любому доступному ему кодинг-агенту (Claude Code, Cursor,
Copilot Workspace и т.п.) прямо в своей рабочей среде — против
собственного репозитория с автотестами — чтобы получить черновик двух
Core-метрик `qa_process_metrics` без ручного подсчёта. M2 не может
запустить это из репозитория qa-management — там нет доступа к кодовой
базе клиентских проектов; промпт существует специально для того, чтобы
это мог сделать сам QA-инженер в своём окружении, с тем доступом, который
у него уже есть.

Не заменяет остальные Core-метрики (pass rate, flaky-ощущение, снимок
багов) — те по-прежнему заполняются человеком за минуту, не автоматически.

## Промпт (копировать как есть, можно на английском или русском — агент поймёт оба)

```
Explore this repository's automated test code. Adapt patterns to whatever
this stack actually uses (examples: *.test.*, *.spec.*, __tests__/**,
cypress/e2e/**/*.cy.*, src/test/java/**/*Test.java, playwright tests,
etc.) — don't assume one framework.

1. Count all automated test files, and a rough count of individual test
   cases/scenarios within them (function/method/`it(...)` count is fine).
2. Separately, estimate this app's rough functional surface — pages,
   routes, components, or API endpoints, whichever unit fits this stack
   best — and count those units.
3. Compute (automated test count) / (functional surface count) as a rough
   coverage-proxy ratio. State explicitly that this is an approximation,
   not a certified coverage percentage - it doesn't account for tests
   covering multiple units or units covered by several tests.
4. Report which test framework(s) are in use, and whether a CI pipeline
   runs these tests automatically (check for CI config files - .github
   /workflows, Jenkinsfile, .gitlab-ci.yml, etc.) - just note presence/
   absence, don't try to compute pass rate from CI logs unless they're
   trivially available in the repo itself.

Output a short markdown table: test file count, test case count,
functional surface count and what unit you used, the ratio, framework(s),
CI presence (yes/no). Add one line noting any assumption you had to make
because the stack wasn't obvious.
```

## Как использовать результат

- Строка **Покрытие (грубая оценка)** в `qa_process_metrics`: `Показатель`
  = посчитанное соотношение, `Пояснение` = "оценка через промпт-скрипт по
  тест-репозиторию, не сертифицированный %, метод: <какой юнит агент взял
  за функциональную единицу>".
- Строка **Количество автотестов**: `Показатель` = число тест-кейсов из
  вывода. В следующем месяце — перезапустить тот же промпт, чтобы был
  тренд, не разовое число.
- Если агент не смог однозначно определить функциональную единицу (стек
  незнакомый/нетипичный) — это нормальный результат, не ошибка: отметь
  как есть в `Пояснение`, не дожимай агента до точной цифры.
