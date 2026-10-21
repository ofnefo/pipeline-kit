# Подборка скиллов для агентов

125 скиллов по 12 направлениям: **69 авторских**, 1 базовый из `skills/` и **55 сторонних**, которые мы сами используем в пайплайнах. Скилл — папка с `SKILL.md`: инструкция, приёмы и чек-лист приёмки, которые Codex и Claude Code подгружают под задачу.

- **Наши** лежат в [catalog/skills](../catalog/skills) (8 базовых — в [skills](../skills)). Из них убраны пути, имена хостов, клиенты и внутренние сервисы; вместо путей стоят заполнители вроде `<PROJECT_ROOT>`.
- **Сторонние** не копируются в репозиторий: ссылка ведёт на авторский репозиторий, закреплённый на проверенном коммите. Ставьте их оттуда и соблюдайте лицензию автора.
- Машиночитаемый список: [catalog/index.json](../catalog/index.json).

## Установка

Наш скилл ставится по имени, без перезаписи ваших файлов (сначала план, затем `--apply`):

```bash
python tools/setup_skills.py --project <абсолютный путь> --client both --panel none --skills web-qa ru-text
```

Скилл попадёт в `.agents/skills/<имя>` (Codex) и `.claude/skills/<имя>` (Claude Code). Если там уже лежит другая версия, установка остановится и ничего не изменит. Сторонний скилл скрипт не ставит, а покажет ссылку: скопируйте папку скилла из апстрима в те же каталоги.

Скилл — это инструкция, а не программа. Те, что работают с внешними программами (Blender, DaVinci Resolve, Adobe, ComfyUI, Godot), требуют установленной программы и вашей проверки результата.

## Содержание

- [Общие — для любого пайплайна](#core) — 26
- [Дизайн, графика и 3D](#design) — 18
- [Офис и документы](#office) — 6
- [Музыка и звук](#music) — 9
- [Видео и моушн](#video) — 11
- [Игры](#game) — 17
- [Веб](#web) — 23
- [Telegram](#telegram) — 6
- [SMM и контент](#smm) — 2
- [Android (ADB)](#android) — 1
- [OSINT](#osint) — 1
- [Безопасность кода](#security) — 5

<a id="core"></a>
## Общие — для любого пайплайна

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`change-review`](../catalog/skills/core/change-review/SKILL.md) | Ревью изменений до коммита и деплоя: уровни L0/L1/L2 по реальному изменению, ревьюер из другого семейства моделей, JSON-вердикт с цитатами, гейт и квитанции. | Перед коммитом или деплоем общего кода, инструментов, скиллов, прод-выкаток, клиентских материалов и переносов данных. | наш; идея цикла ревью из Zeroshot (MIT), без копирования, см. NOTICE.md |
| [`open-creative-tools`](../catalog/skills/core/open-creative-tools/SKILL.md) | Открытые замены Adobe и Office (GIMP, Krita, Inkscape, Scribus, Natron, Glaxnimate, darktable, Shotcut/melt, Audacity) с проверенными CLI-рецептами. | Когда Adobe или Office заняты, недоступны или нужен пакетный headless-прогон. | наш |
| [`ru-instructions`](../catalog/skills/core/ru-instructions/SKILL.md) | Русские инструкции, ТЗ, чек-листы, регламенты и промпты для ботов: цель и адресат сначала, одно действие на шаг; ТЗ из голосовых. | Когда пишешь текст, по которому другие люди будут действовать. | наш; идеи из kisa-stack (MIT), без копирования, см. NOTICE.md |
| [`ru-lyrics`](../catalog/skills/core/ru-lyrics/SKILL.md) | Русские тексты песен и рэпа: бриф, размер по ударениям, рифма и флоу, проверка на «нейросетевость», формат для ACE-Step. | Когда нужно написать или разобрать текст песни, куплет, припев или рэп-партию. | наш; идеи из открытых скиллов для текстов песен (MIT), без копирования, см. NOTICE.md |
| [`ru-promo`](../catalog/skills/core/ru-promo/SKILL.md) | Продающие тексты на русском: лендинг, оффер, первый экран, заголовки, CTA, FAQ, анонсы событий, объявления Яндекс Директ и VK Рекламы. | Когда нужно написать или проверить продающую страницу, анонс или рекламу. | наш; адаптирует redaktura-skills (CC BY 4.0), см. NOTICE.md |
| [`ru-seo`](../catalog/skills/core/ru-seo/SKILL.md) | SEO для русскоязычных сайтов: сначала Яндекс, затем Google и ИИ-ответы (GEO); метаданные, индексация, robots с Clean-param, sitemap, JSON-LD, IndexNow, проверки перед деплоем. | Аудит и подготовка SEO-правок русскоязычного сайта. | наш; адаптирует google-yandex-seo-skill (MIT), см. NOTICE.md |
| [`ru-text`](../catalog/skills/core/ru-text/SKILL.md) | Редактура русского текста для людей: канцелярит, признаки нейросетевого текста, типографика, жанры (письмо, пост, кейс, UX-тексты); скрипты проверки. | Когда текст для клиентов, пользователей или аудитории нужно написать, вычитать или проверить. | наш; включает код milchin и Humanizer_RU (MIT) и адаптирует redaktura-skills (CC BY 4.0), см. NOTICE.md |
| [`ru-voiceover`](../catalog/skills/core/ru-voiceover/SKILL.md) | Подготовка русских текстов для озвучки и TTS: фразы на выдох, числа и имена словами, ё и ударения, омографы, паузы. | Закадр, диктор, объявления в зале, текст для синтеза речи. | наш; идеи из открытых TTS-проектов (MIT), без копирования, см. NOTICE.md |
| [`video-watch`](../catalog/skills/core/video-watch/SKILL.md) | Агент «смотрит» видео: ключевые кадры, подписанные контактные листы, локальная расшифровка и индекс «кадр ↔ строка текста» одним скриптом без зависимостей. | Ревью рендера или монтажа, сравнение двух версий, пересказ локального или публичного ролика. | наш |
| [`work-kits`](../catalog/skills/core/work-kits/SKILL.md) | Старт творческой или продуктовой работы: выбор направления и ролей (создатель, дизайнер, разработчик, продакшн, автор, ревьюер) и скиллов на каждом этапе. | В начале любого заметного проекта: концепт, айдентика, сайт, ролик, трек, пост. | наш |
| [`accessibility-audit`](https://github.com/rampstackco/claude-skills/tree/3d4510a94a76ead80122c691b5c480f92f3fbe40/skills/accessibility-audit) | Аудит доступности по WCAG: восприятие, управление, понятность, совместимость. | Когда нужно проверить или исправить доступность интерфейса. | сторонний · MIT |
| [`archify`](https://github.com/tt-a1i/archify/tree/7158026e852f3aa6578c741e673b46d7878c92c1/archify) | Схемы архитектуры, инфраструктуры, потоков данных, последовательностей и процессов. | Когда нужно наглядно нарисовать систему или процесс. | сторонний · MIT |
| [`design-taste-frontend`](https://github.com/Leonxlnx/taste-skill/tree/ce26fc25c0e5e8cab638f883de62d9a86ee5e45b/skills/taste-skill) | Правила вкуса для фронтенда: типографика, сетка, цвет, без шаблонных решений. | Когда нужно уйти от шаблонного вида при сборке интерфейса. | сторонний · MIT |
| [`emil-design-eng`](https://github.com/emilkowalski/skills/tree/2d228630ba1446365f614a108cb8252f1feda202/skills/emil-design-eng) | UI-компоненты и анимации: отзывчивость, прерываемость, фокус, reduced motion. | При создании или ревью кнопок, меню, диалогов, тостов, жестов. | сторонний · MIT |
| [`impeccable`](https://github.com/pbakaus/impeccable/tree/dad8dbb3aac21ad1fa236c110315ef4abece23e8/.claude/skills/impeccable) | Критика и доводка готового веб-интерфейса: иерархия, шум, дефекты. | Когда интерфейс собран и его нужно отполировать без смены направления. | сторонний · Apache-2.0 |
| [`interface-design`](https://github.com/Dammyjay93/interface-design/tree/2f9be3206855bcb2d1d0af262c8bae25cba6658d/.claude/skills/interface-design) | Проектирование интерфейсов панелей, дашбордов и приложений с памятью решений. | При дизайне продуктового UI, а не лендинга. | сторонний · MIT |
| [`jev`](https://github.com/wuyoscar/jev-skill/tree/86b19a2c9856cc908ad29b5cf02ff1c4e7323c09/skills/jev) | Процессы, где решение да/нет, метка или рубрика приходит от сервиса Jev. | Когда повторяемое суждение по тексту или JSON нужно получать структурно. | сторонний · MIT · нужен платный внешний сервис |
| [`jev-eval`](https://github.com/wuyoscar/jev-skill/tree/86b19a2c9856cc908ad29b5cf02ff1c4e7323c09/skills/jev-eval) | Оценка готовых результатов по явным критериям через Jev, включая ревью изменений. | Для рубрик, пакетной оценки и доказательных ревью. | сторонний · MIT · нужен платный внешний сервис |
| [`jev-triage`](https://github.com/wuyoscar/jev-skill/tree/86b19a2c9856cc908ad29b5cf02ff1c4e7323c09/skills/jev-triage) | Классификация и приоритизация входящих (тикеты, отзывы, записи) через Jev. | Для массовой сортировки записей по заданным правилам. | сторонний · MIT · нужен платный внешний сервис |
| [`mcp-builder`](https://github.com/anthropics/skills/tree/8a1541c4a3ffa5a20a5a91de0dcf3f0bab1d1ef4/skills/mcp-builder) | Руководство по созданию MCP-серверов с хорошо спроектированными инструментами. | При разработке MCP-сервера для внешнего API или сервиса. | сторонний · Apache-2.0 · лицензия в LICENSE.txt самого скилла |
| [`performance-optimization`](https://github.com/rampstackco/claude-skills/tree/3d4510a94a76ead80122c691b5c480f92f3fbe40/skills/performance-optimization) | Поиск и исправление проблем скорости: Core Web Vitals, бандл, ассеты, рендер. | Когда страница медленная или проседают LCP/INP/CLS. | сторонний · MIT |
| [`rag-evaluation-harness`](https://github.com/davepoon/buildwithclaude/tree/d75454c7a1187dc7f5f7fb671b009b6e42c9cedb/plugins/all-skills/skills/rag-evaluation-harness) | Офлайн-оценка RAG: Recall@K, ранги, точность контекста, покрытие и валидность цитат. | Когда нужно измерить качество поиска и цитирования в RAG. | сторонний · MIT |
| [`security-baseline`](https://github.com/rampstackco/claude-skills/tree/3d4510a94a76ead80122c691b5c480f92f3fbe40/skills/security-baseline) | Базовая безопасность сайта: HTTPS/TLS, заголовки, CSP, секреты, быстрый аудит. | Перед запуском сайта или при усилении защиты веб-приложения. | сторонний · MIT |
| [`systematic-debugging`](https://github.com/obra/superpowers/tree/bb92a77741419a4ab5f06e711a283343f1ada0c3/skills/systematic-debugging) | Системная отладка: контракт, изоляция причины, одна гипотеза за раз, проверка. | При воспроизводимом баге, падающем тесте, регрессии или флаки. | сторонний · MIT |
| [`typesafe-ai`](https://github.com/typesafe-ai/skills/tree/65a39f393687675ce170e6094757de20370365b9/skills/typesafe-ai) | Замена связки «промпт + парсинг» на маленькие типизированные AI-решения TypeSafe. | Когда фиче нужен «здравый смысл» модели в виде структурного решения. | сторонний · MIT · нужен платный внешний сервис |
| [`ui-ux-pro-max`](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/tree/50d8a7de0900119855614541f15a1a616691eb33/.claude/skills/ui-ux-pro-max) | База палитр, шрифтовых пар, стилей, типов графиков и UX-правил с поиском. | При выборе стиля, шрифтов, палитры или структуры экрана. | сторонний · MIT |

<a id="design"></a>
## Дизайн, графика и 3D

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`blender-production`](../catalog/skills/design/blender-production/SKILL.md) | Пространственные сцены в Blender: блокауты, сцены по планам, материалы и рендер, оптимизация и экспорт, проверка по референсам. | Когда нужна 3D-сцена стенда или интерьера, блокаут по чертежу или экспорт GLB/FBX. | наш; идеи из 4 открытых Blender-скиллов (GPL-3.0, MIT, Apache-2.0), без копирования текста, см. NOTICE.md |
| [`cad-production`](../catalog/skills/design/cad-production/SKILL.md) | Параметрические детали и экспорт STEP/DXF/STL для производства; маршрутизация CAD-инструментов. | Когда нужна изготавливаемая деталь, крепёж или чертёж для резки и фрезеровки. | наш |
| [`comfy`](../catalog/skills/design/comfy/SKILL.md) | Работа с локальным ComfyUI через HTTP API: поиск узлов и моделей по /object_info, валидация графа, /prompt, ожидание, /view, /free, размещение весов, квитанции. | Когда агенту нужно запустить, проверить или отладить workflow ComfyUI или разместить новые веса. | наш; идеи из Comfy-Org/comfy-cli (GPL-3.0), без копирования текста, см. NOTICE.md |
| [`design-comfy-generation`](../catalog/skills/design/design-comfy-generation/SKILL.md) | Локальные цепочки ComfyUI для дизайна: Z-Image Turbo, Qwen-Image-Edit-2511, BiRefNet, CodeFormer, SeedVR2, плюс векторизация VTracer и поиск иконок со свободной лицензией; квитанция на каждый прогон. | Когда нужно сгенерировать концепт или текстуру, отредактировать изображение, вырезать фон, восстановить лицо, апскейлить для печати или векторизовать. | наш |
| [`design-graphic-compositor`](../catalog/skills/design/design-graphic-compositor/SKILL.md) | Сборка брендированной растровой графики: инвентаризация ассетов, контактные листы, детерминированная сборка слоёв по JSON-спеке на Pillow. | Когда нужен баннер, key visual, широкоформатная графика или разбор брендбука. | наш |
| [`design-pipeline`](../catalog/skills/design/design-pipeline/SKILL.md) | Каркас многопроектного пайплайна пространственного дизайна: поиск PROJECT.yaml, профили, опрос по объёму работ, 7 гейтов, маршрутизация по скиллам, диагностика переноса. | Когда нужно создать или подключить проект, найти активный проект, проверить перенесённое рабочее пространство или понять, какой скилл берёт задачу. | наш |
| [`design-pipeline-chat`](../catalog/skills/design/design-pipeline-chat/SKILL.md) | Ведение одного проекта в чате: общее состояние, утверждения со статусами confirmed/assumption/contradiction/open_question, гейты, компактная передача в конце каждого хода. | Когда оператор просит начать или продолжить конкретный дизайн-проект или узнать следующий шаг. | наш |
| [`design-production-preflight`](../catalog/skills/design/design-production-preflight/SKILL.md) | Предпечатная проверка: размеры, вылеты, разрешение, цветовые профили, шрифты; скрипт preflight_print.py с кодами выхода и тестами. | Перед отправкой файлов в печать или производство. | наш |
| [`design-render-refiner`](../catalog/skills/design/design-render-refiner/SKILL.md) | Улучшение утверждённого рендера с зафиксированной основой: материалы, графика, свет без изменения геометрии; шаблон промпта. | Когда геометрия рендера утверждена и нужен только визуальный финиш. | наш |
| [`design-style-director`](../catalog/skills/design/design-style-director/SKILL.md) | Выбор и защита визуального направления: мудборды, варианты hero / реализуемый / оптимизированный, стоп-листы. | Когда нужно предложить или зафиксировать стиль проекта до продакшена. | наш |
| [`illustrator-production`](../catalog/skills/design/illustrator-production/SKILL.md) | Векторные мастер-файлы в Illustrator: артборды, вывески, высечки, чистка вектора, экспорт SVG/PDF. | Когда нужен точный векторный макет, вывеска, высечка или экспорт для печати. | наш |
| [`image-to-scene`](../catalog/skills/design/image-to-scene/SKILL.md) | Из одного фото — черновая 3D-сцена: список объектов, маски SAM, чистая подложка через Qwen-Edit, меши SF3D, глубина и камера MoGe-2, сборка в Blender; статус и квитанция на каждый этап. | Когда нужно разобрать фото или рендер на объекты и получить редактируемый блокаут для превиза. | наш |
| [`photoshop-production`](../catalog/skills/design/photoshop-production/SKILL.md) | Растровые мастер-файлы в Photoshop: маски, ретушь, неразрушающий композитинг, QA экспорта, скриптовое удаление фона. | Когда нужны маски, ретушь, слоёный PSD-мастер или вырезка фона через Photoshop. | наш |
| [`3d-modeling`](https://github.com/ghsi011/3d-modeling-skill/tree/ae5951c23818af3f5d471e509860b16604b2e5f9/skills/3d-modeling) | Проектирование и проверка деталей для 3D-печати: размеры, допуски, экспорт. | Когда нужно смоделировать или подготовить к печати физический предмет. | сторонний · MIT |
| [`comfy-debug`](https://github.com/Comfy-Org/comfy-cli/tree/1ae8f4057dca21d18b56dd56e37ba77f060d1004/comfy_cli/skills/comfy-debug) | Отладка comfy CLI: упавшие воркфлоу, зависшие задачи, ошибки. | Когда задача ComfyUI или команда comfy CLI падает или зависает. | сторонний · GPL-3.0 |
| [`illustrator-com`](https://github.com/Moksa1123/illustrator-com-skill/tree/59e268cc21be9567db41bb78f1e20de78aaf759f) | Управление Adobe Illustrator на Windows через COM/ExtendScript без диалогов. | Для автоматизации Illustrator из агента. | сторонний · MIT |
| [`image-prompt-library`](https://github.com/YouMind-OpenLab/ai-image-prompts-skill/tree/50a570801fb8eb03365663d74eff2668bce50843) | Офлайн-библиотека шаблонов промптов для изображений с поиском. | Когда нужна идея или шаблон промпта для постера, обложки, ассета. | сторонний · MIT |
| [`ux-heuristics`](https://github.com/wondelai/skills/tree/c172996495bed0fcd26896a9416b2093fd7073f0/ux-heuristics) | Эвристический аудит юзабилити (Нильсен, когнитивный проход). | Когда пользователи путаются в форме, навигации или сценарии. | сторонний · MIT |

Также полезны здесь: `emil-design-eng`, `impeccable`, `ui-ux-pro-max`, `extract-design-md`.

<a id="office"></a>
## Офис и документы

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`commercial-document-production`](../catalog/skills/office/commercial-document-production/SKILL.md) | Подготовка коммерческих документов (КП, договоры, счета, акты, ТрН/ЭТрН): реестр статусов, печати и подписи, закрывающие документы. | Когда нужно собрать или проверить комплект коммерческих и закрывающих документов. | наш |
| [`estimate-production`](../catalog/skills/office/estimate-production/SKILL.md) | Сметы с проверкой расчётным движком: десятичные суммы, каскад НДС/налогов/ФОТ/маржи, кредит DAYS360, внутренняя и клиентская версии, лист рычагов. | Когда нужно посчитать, пересчитать или проверить смету проекта и её финансовую модель. | наш |
| [`meeting-transcription`](../catalog/skills/office/meeting-transcription/SKILL.md) | Локальная расшифровка встреч: ASR (GigaAM-v3 / faster-whisper), диаризация, имена спикеров по подписям видеозвонка, протокол, правила приватности. | Когда есть запись созвона или встречи и нужны стенограмма со спикерами и протокол. | наш |
| [`office-document-intake`](../catalog/skills/office/office-document-intake/SKILL.md) | Приём и инвентаризация исходных документов: опись с хешами, классификация, извлечение текста и таблиц в неизменяемые пакеты. | Когда пришла папка с договорами, сметами, сканами или таблицами и нужно понять, что в ней лежит, и извлечь данные. | наш |
| [`office-pipeline`](../catalog/skills/office/office-pipeline/SKILL.md) | Каркас офисного конвейера: 5 гейтов (приём, фиксация сметы, план документов, проверка, выдача), пакеты извлечения с адресацией по хешу, маршрутизация артефактов и передача дел. | Когда нужно провести офисный проект (смета, КП, договор, акты) от исходников до выдачи с проверяемым следом. | наш |
| [`office-preflight`](../catalog/skills/office/office-preflight/SKILL.md) | Предвыдачная проверка офисных документов в 5 слоёв: суммы, формулы, реквизиты, оформление, соответствие плану, с блокерами. | Перед отправкой сметы, договора или комплекта документов клиенту. | наш |

<a id="music"></a>
## Музыка и звук

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`audio-production`](../catalog/skills/music/audio-production/SKILL.md) | Анализ и обработка аудио: BPM/тональность как гипотезы, LUFS/true peak, стемы (RoFormer/HTDemucs), технический мастер по профилям громкости, отчёты до/после. | Когда нужно измерить, почистить, разделить, нормализовать или проверить аудиофайл. | наш |
| [`flstudio-production`](../catalog/skills/music/flstudio-production/SKILL.md) | Работа с FL Studio через офлайн-FLP (PyFLP), живой мост и скрипты Piano Roll: осмотр перед записью, снапшоты, сверка после изменений. | Когда нужно собрать, разобрать или автоматизировать проект FL Studio. | наш |
| [`music-midi-composition`](../catalog/skills/music/music-midi-composition/SKILL.md) | MIDI по ролям (барабаны, бас, гармония, мелодия, маркеры), грув прежде всего, осмысленная хуманизация, аудио в MIDI через стемы и Basic Pitch. | Когда нужно написать, извлечь или подготовить MIDI-партии для DAW. | наш |
| [`music-neural-audio-lab`](../catalog/skills/music/music-neural-audio-lab/SKILL.md) | Маршрутизация нейро-инструментов: ACE-Step (генерация, ремикс, продление, перерисовка строки), стемы, аудио в MIDI, TTS, контракт рендера и матрица вариантов. | Когда нужно сгенерировать, перестилизовать, продлить или поправить трек нейросетью. | наш |
| [`music-songwriting`](../catalog/skills/music/music-songwriting/SKILL.md) | Тексты песен и рэпа: один конфликт, банк деталей, просодия и рифма под карман, редактура в три прохода, эвристическая проверка текста скриптом. | Когда нужно написать или отредактировать текст песни, куплет, припев или рэп-партию. | наш |
| [`music-track-director`](../catalog/skills/music/music-track-director/SKILL.md) | Ведение трека целиком: этапы 00–80, карточка проекта, гейты, иерархия решений, журнал рендеров, правила релиза. | Когда начинаешь, продолжаешь или проверяешь проект песни и решаешь, что делать дальше. | наш |
| [`music-track-editor`](../catalog/skills/music/music-track-editor/SKILL.md) | Редактура трека: 8 проходов аудита (идентичность, структура, текст, исполнение, аранжировка, микс, мастер, продукт) и метки решений по вариантам. | Когда нужно выбрать вариант, понять, почему трек звучит безлико, или решить, готов ли он к релизу. | наш |
| [`music-vocal-production`](../catalog/skills/music/music-vocal-production/SKILL.md) | Вокальный продакшн: запись, комп, чистка, компрессия и де-эссинг, минимальный тюнинг, пространство, экспорт стемов; согласие на клон голоса. | Когда нужно записать, почистить или обработать певческий или рэп-вокал. | наш |
| [`voiceover-dubbing`](../catalog/skills/music/voiceover-dubbing/SKILL.md) | Озвучка и дубляж: скрипт, локальный TTS (клон с согласием или описанный голос), подгонка под тайминги субтитров, проверка WER, сведение с даккингом. | Когда нужен диктор, закадр, дубляж или переозвучка ролика. | наш |

Также полезны здесь: `comfy`, `comfy-debug`.

<a id="video"></a>
## Видео и моушн

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`after-effects-production`](../catalog/skills/video/after-effects-production/SKILL.md) | After Effects через MCP-мост или JSX, рендер aerender: настройка доступа, цикл композиции, версионные рендеры, известные подвохи. | Есть .aep, шаблон или плагин AE, который нужно собрать, поправить или отрендерить. | наш |
| [`comfy-motion-recipes`](../catalog/skills/video/comfy-motion-recipes/SKILL.md) | Разбор трендовых приёмов (HUD-разметка, морф, 3D-острова, шторка стилей, глитч, фейковые катсцены) на локальные цепочки ComfyUI с доводкой в AE/Blender/TD. | Показали референс-ролик и просят «так же». | наш |
| [`motion-graphics`](../catalog/skills/video/motion-graphics/SKILL.md) | Моушн-графика без After Effects: титры, нижние трети, Lottie, HTML/canvas-рендер; маршруты со ссылками на открытые проекты; шрифты и альфа. | Нужны титры, плашки, кинетическая типографика или анимированная графика кодом. | наш |
| [`neural-video`](../catalog/skills/video/neural-video/SKILL.md) | Генерация и починка нейровидео: локальные графы Wan 2.2/LTX в ComfyUI, правила кадров и разрешений, структура промпта, разбор брака, ремонт сегментов. | Нужно сгенерировать или починить шот: I2V, первый/последний кадр, длинный дубль, апскейл. | наш; идеи из открытых режиссёрских и промпт-скиллов (MIT, CC BY 4.0) и Wan2.2 (Apache-2.0), см. NOTICE.md |
| [`resolve-production`](../catalog/skills/video/resolve-production/SKILL.md) | Монтаж и сдача в DaVinci Resolve: бесплатная версия против Studio, OTIO → otioconvert → импорт, скриптовый цикл в Studio, проверки сдачи. | Работа с таймлайном Resolve, конформ, цвет, экспорт мастера. | наш |
| [`touchdesigner-production`](../catalog/skills/video/touchdesigner-production/SKILL.md) | Проекты TouchDesigner: граф по семействам операторов, аудиореактив, лупы, GLSL, лимиты лицензии, проверка экспорта. | Запрос про TouchDesigner или есть .toe/.tox. | наш |
| [`video-direction`](../catalog/skills/video/video-direction/SKILL.md) | Режиссура: грамматика кадра, движения камеры, драматургия сцены, библия непрерывности, превиз в Blender, рубрика ревью. | Нужны раскадровка, шот-лист, превиз или режиссёрский разбор ролика до генерации или съёмки. | наш; идеи из открытых режиссёрских и промпт-скиллов (MIT, CC BY 4.0), см. NOTICE.md |
| [`video-editing`](../skills/video-editing/SKILL.md) | Просмотр исходников, аннотации, таймлайн и экспорт монтажных ревизий. | При монтаже в Studio → Montage и скриптовой сборке ролика. | наш |
| [`video-pipeline`](../catalog/skills/video/video-pipeline/SKILL.md) | Маршрутизатор видеопайплайна: бриф → референсы → проверка исходников → выбор маршрута → проверка; версии выходов, громкость, техконтроль отдельно от творческой оценки. | Любая видеозадача, когда непонятно, какой скилл брать: монтаж, нейровидео, моушн, субтитры, сдача. | наш |
| [`video-transcription`](../catalog/skills/video/video-transcription/SKILL.md) | Расшифровка видео и аудио: ffmpeg → WAV 16 кГц, сначала готовые субтитры, затем faster-whisper/GigaAM; TXT/SRT/VTT/JSON с пословными таймингами. | Нужны текст, субтитры или тайминги слов из видео или аудио. | наш |
| [`vvvv-production`](../catalog/skills/video/vvvv-production/SKILL.md) | Патчи vvvv gamma: realtime-визуал, аудиореактив, VJ-лупы, инсталляции; экспорт и его приёмка. | Запрос про vvvv или есть проект .vl/.v4p. | наш |

Также полезны здесь: `comfy`, `comfy-debug`, `image-prompt-library`.

<a id="game"></a>
## Игры

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`game-art-production`](../catalog/skills/game/game-art-production/SKILL.md) | Игровой арт от геймплейного требования до проверки в движке: карточка происхождения ассета, силуэт, контраст, масштаб, импорт. | Нужны спрайты, тайлы, текстуры, иконки или концепт, которые должны работать в игре. | наш |
| [`game-pipeline`](../catalog/skills/game/game-pipeline/SKILL.md) | Маршрут игрового проекта: выбор движка (Godot/Babylon.js/Unreal), стадии, раскладка, заказ и приёмка ассетов по manifest.json, сборка и экспорт. | Новая игра или прототип, ассеты для игры, проверка или сборка игры. | наш |
| [`game-ui-ux`](../catalog/skills/game/game-ui-ux/SKILL.md) | UI/UX игры: пять вопросов игрока, правила HUD и меню, клавиатура/мышь и геймпад, проверка на нескольких разрешениях в живой игре. | Проектирование или ревью HUD, меню, подсказок и обратной связи в игре. | наш |
| [`godot-development`](../catalog/skills/game/godot-development/SKILL.md) | Разработка на Godot 4: осмотр → план → реализация → headless-тест → запуск → исправление; типизированный GDScript, сигналы, Resources, сохранения. | Нужно изменить сцены, скрипты, ввод, сохранения или отладить игру на Godot. | наш |
| [`playtest-qa`](../catalog/skills/game/playtest-qa/SKILL.md) | Плейтест: сборка → автотесты → запуск → игра → воспроизведение → фикс → повтор; минимальное покрытие и отчёт с шагами воспроизведения. | Нужно протестировать сборку или найти баги перед релизом. | наш |
| [`asset-pipeline`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/asset-pipeline) | Конвейер импорта и конвертации ассетов для модов. | При подготовке ассетов под формат игры. | сторонний · MIT |
| [`fal-assets`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/fal-assets) | Генерация игровых ассетов через fal.ai. | Когда моду нужны новые ассеты. | сторонний · MIT · нужен платный внешний сервис |
| [`game-automation`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/game-automation) | Автоматизация действий в игре для проверки модов. | Для автотестов и воспроизведения сценариев в игре. | сторонний · MIT |
| [`game-recon`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/game-recon) | Разведка: движок игры, готовые инструменты и способы моддинга. | В начале любой задачи моддинга. | сторонний · MIT |
| [`game-research-websearch`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/game-research-websearch) | Поиск сведений об игре и её моддинге в вебе. | Когда нужны внешние данные об игре. | сторонний · MIT |
| [`mashup-mods`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/mashup-mods) | Перенос механик, врагов или миров из одной игры в другую. | Когда нужно скрестить две игры. | сторонний · MIT |
| [`mod-any-game`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/mod-any-game) | Сквозной сценарий моддинга установленной PC-игры. | Когда нужно модифицировать или расширить игру. | сторонний · MIT |
| [`publish-mod`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/publish-mod) | Упаковка и публикация мода. | Когда мод готов к выпуску. | сторонний · MIT |
| [`reverse-engineering`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/reverse-engineering) | Реверс форматов и бинарников игр. | Когда без разбора форматов мод не сделать. | сторонний · MIT |
| [`save-systems`](https://github.com/gamedev-skills/awesome-gamedev-agent-skills/tree/d4b0e35550c55ae70bdfcab4ef5a0e94610438a9/skills/disciplines/save-systems) | Системы сохранений в играх: формат, версии, миграции, надёжность. | При разработке сохранения и загрузки в игре. | сторонний · Apache-2.0 |
| [`share-field-notes`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/share-field-notes) | Запись и публикация заметок по итогам моддинга и реверса. | До начала работы над игрой и в конце сессии. | сторонний · MIT |
| [`showcase-video`](https://github.com/rehan-remade/universal-modder/tree/8370faa8e114baf33acdb23079aff552a7728c4b/skills/showcase-video) | Запись демонстрационного видео мода. | Когда нужно показать результат моддинга. | сторонний · MIT |

Также полезны здесь: `comfy`, `comfy-debug`.

<a id="web"></a>
## Веб

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`backend-baseline`](../catalog/skills/web/backend-baseline/SKILL.md) | Базовые правила бэкенда: Postgres, миграции expand/contract, идемпотентные вебхуки, очереди, безопасность. | Проектирование или ревью бэкенда сайта или сервиса. | наш; адаптирует supabase/agent-skills (MIT) и futurice/backend-best-practices (CC BY 4.0), см. NOTICE.md |
| [`web-immersive`](../catalog/skills/web/web-immersive/SKILL.md) | Кинематографичные сайты: GSAP, Lenis, three.js, рецепты, мобильная версия и доступность, запись превью-видео. | Иммерсивный лендинг или портфолио с анимацией и 3D. | наш |
| [`web-pipeline`](../catalog/skills/web/web-pipeline/SKILL.md) | Маршрутизатор веб-работ: этапы дизайна, медиа, финиша и приёмки. | Любая работа над сайтом, когда нужно выбрать маршрут. | наш |
| [`web-qa`](../catalog/skills/web/web-qa/SKILL.md) | QA сайта: прогоны Playwright, axe, Lighthouse, визуальные диффы, путь пользователя. | Проверка сайта перед сдачей или релизом. | наш; идеи из anthropics/skills webapp-testing (Apache-2.0) и lackeyjb/playwright-skill (MIT), см. NOTICE.md |
| [`web-release`](../catalog/skills/web/web-release/SKILL.md) | Релиз сайта без привязки к провайдеру: сборка, sha256, бэкап, поэтапный деплой, smoke-проверка, откат. | Выкатка сайта; прод — только по явной просьбе владельца сайта. | наш |
| [`web-seo-growth`](../catalog/skills/web/web-seo-growth/SKILL.md) | SEO-рост: кластеры интентов, брифы, измерения, GEO; офлайн-аудит HTML и сборщик UTM-меток. | Развитие SEO сверх базовых метаданных. | наш |
| [`extract-design-md`](https://github.com/google-labs-code/stitch-skills/tree/0337446dadde6f8c94210444e2aa9d546126480f/plugins/stitch-design/skills/extract-design-md) | Извлечение дизайн-системы проекта в DESIGN.md. | Когда нужно зафиксировать стиль существующего проекта для агента. | сторонний · Apache-2.0 |
| [`react-best-practices`](https://github.com/vercel-labs/agent-skills/tree/063bee94c3f4df8453406c830b0a7df0f2860278/skills/react-best-practices) | Правила производительности React/Next.js от Vercel. | При написании и ревью кода на React/Next.js. | сторонний · MIT · MIT указан во frontmatter скилла |
| [`redesign-existing-projects`](https://github.com/Leonxlnx/taste-skill/tree/ce26fc25c0e5e8cab638f883de62d9a86ee5e45b/skills/redesign-skill) | Редизайн существующего сайта или приложения без поломки функций. | Когда нужно обновить вид готового проекта. | сторонний · MIT |
| [`replica-architect`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-architect) | Серия Replica (клон продукта по образцу): архитектура проекта. | При планировании структуры. | сторонний · MIT |
| [`replica-backend`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-backend) | Серия Replica (клон продукта по образцу): серверная часть. | При сборке бэкенда. | сторонний · MIT |
| [`replica-brand`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-brand) | Серия Replica (клон продукта по образцу): бренд, название, тон. | При создании айдентики. | сторонний · MIT |
| [`replica-build`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-build) | Серия Replica (клон продукта по образцу): сборка по плану. | На этапе реализации. | сторонний · MIT |
| [`replica-deploy`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-deploy) | Серия Replica (клон продукта по образцу): деплой. | При выкладке. | сторонний · MIT |
| [`replica-design`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-design) | Серия Replica (клон продукта по образцу): дизайн экранов. | При проектировании интерфейса. | сторонний · MIT |
| [`replica-diff`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-diff) | Серия Replica (клон продукта по образцу): сравнение с образцом. | Для проверки полноты. | сторонний · MIT |
| [`replica-entrepreneur`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-entrepreneur) | Серия Replica (клон продукта по образцу): бизнес-модель и позиционирование. | При оценке идеи продукта. | сторонний · MIT |
| [`replica-launch`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-launch) | Серия Replica (клон продукта по образцу): запуск и продвижение. | Перед публичным запуском. | сторонний · MIT |
| [`replica-recon`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-recon) | Серия Replica (клон продукта по образцу): разведка продукта-образца. | В начале проекта-реплики. | сторонний · MIT |
| [`replica-test`](https://github.com/Jakeschincariol/replica-skill/tree/77c9436fb3d18c3d58169efb8caf4fe906b0dc51/replica-test) | Серия Replica (клон продукта по образцу): тестирование. | Перед выпуском. | сторонний · MIT |
| [`shadcn`](https://github.com/shadcn-ui/ui/tree/0e3abd65a97707f4a9cc3ed07bf5006e1cb67b13/skills/shadcn) | Работа с компонентами shadcn/ui: установка, композиция, темы. | В проектах на shadcn/ui. | сторонний · MIT |
| [`supabase-postgres-best-practices`](https://github.com/supabase/agent-skills/tree/c9be0e931b7930f7d02126d04774d904c381e7d7/skills/supabase-postgres-best-practices) | Лучшие практики Postgres в Supabase: схемы, индексы, RLS, запросы. | При проектировании и оптимизации базы в Supabase. | сторонний · MIT |
| [`web-design-guidelines`](https://github.com/vercel-labs/agent-skills/tree/063bee94c3f4df8453406c830b0a7df0f2860278/skills/web-design-guidelines) | Проверка UI-кода по Web Interface Guidelines. | Для ревью интерфейса на соответствие лучшим практикам. | сторонний · MIT · в самом скилле лицензия не указана; соседний скилл репозитория — MIT |

Также полезны здесь: `accessibility-audit`, `design-taste-frontend`, `emil-design-eng`, `impeccable`, `interface-design`, `performance-optimization`, `security-baseline`, `ui-ux-pro-max`, `ux-heuristics`.

<a id="telegram"></a>
## Telegram

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`telegram-api-modernization`](../catalog/skills/telegram/telegram-api-modernization/SKILL.md) | Поддержка новых возможностей Bot API: матрица возможностей, флаги с фолбэком, типизированные методы, тесты адаптера. | Новые методы Telegram, выбор библиотеки, идеи из open-source. | наш; адаптирует serejaris/telegram-skills (MIT), см. NOTICE.md |
| [`telegram-contact-organizer`](../catalog/skills/telegram/telegram-contact-organizer/SKILL.md) | Контакты и папки: импорт как доказательство, локальный слой правок, ревью неоднозначных совпадений, превью массовых изменений. | Разбор контактов, коллекций, тегов и папок. | наш |
| [`telegram-group-topics`](../catalog/skills/telegram/telegram-group-topics/SKILL.md) | Топики форума и лички бота: проверка прав, минимальный набор, карта «назначение → message_thread_id». | Создание, переименование и маршрутизация топиков. | наш |
| [`telegram-inbox-briefing`](../catalog/skills/telegram/telegram-inbox-briefing/SKILL.md) | Сводка по чатам в фиксированных корзинах со ссылками на сообщения и локальными черновиками ответов. | «Что в телеге», разбор входящих. | наш |
| [`telegram-storage-cleanup`](../catalog/skills/telegram/telegram-storage-cleanup/SKILL.md) | Освобождение места: инвентаризация, манифест по группам, карантин, хеши, smoke-тест. | «Почисти место», аудит диска ассистента. | наш |
| [`telegram-task-capture`](../catalog/skills/telegram/telegram-task-capture/SKILL.md) | Задачи из сообщений и заметок: извлечение фактов, пакетное превью, запись после подтверждения с квитанцией. | «Создай задачу», смена статуса, анонс задачи в Telegram. | наш |

<a id="smm"></a>
## SMM и контент

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`smm-content-ops`](../catalog/skills/smm/smm-content-ops/SKILL.md) | Из одобренного мастер-материала — варианты постов: рилсы, карусели, Telegram, брифы, чек-лист перед публикацией. | Нарезка кейса или ролика в посты под площадки. | наш |
| [`smm-pipeline`](../catalog/skills/smm/smm-pipeline/SKILL.md) | SMM: стратегия, контент-план и календарь, учёт аккаунтов, гейт согласования, публикация, измерения. | Планирование и ведение соцсетей бренда. | наш |

<a id="android"></a>
## Android (ADB)

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`adb-pipeline`](../catalog/skills/android/adb-pipeline/SKILL.md) | ADB только для своих устройств: точный serial, локальный сервер, read-only диагностика, квитанции с откатом. | Инвентаризация, настройка и установка приложений на своё Android-устройство. | наш |

<a id="osint"></a>
## OSINT

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`osint-case`](../catalog/skills/osint/osint-case/SKILL.md) | OSINT-дело: рамки и авторизация, пассивный сбор, журнал доказательств JSONL с хешами, офлайн-отчёт. | Самоаудит и разрешённая разведка своих, авторизованных или публичных организаций (не частных лиц). | наш |

<a id="security"></a>
## Безопасность кода

| Скилл | Что делает | Когда брать | Чей · лицензия |
| --- | --- | --- | --- |
| [`codeql`](https://github.com/trailofbits/skills/tree/82fe8226252622fa807643bdca1710901198553a/plugins/static-analysis/skills/codeql) | Статический анализ через CodeQL. | Для глубокого анализа потоков данных в коде. | сторонний · CC-BY-SA-4.0 |
| [`differential-review`](https://github.com/trailofbits/skills/tree/82fe8226252622fa807643bdca1710901198553a/plugins/differential-review/skills/differential-review) | Ревью изменений с фокусом на безопасность. | Перед слиянием PR или выпуском изменений. | сторонний · CC-BY-SA-4.0 |
| [`sarif-parsing`](https://github.com/trailofbits/skills/tree/82fe8226252622fa807643bdca1710901198553a/plugins/static-analysis/skills/sarif-parsing) | Разбор и сводка отчётов SARIF. | Когда нужно обработать результаты сканеров в формате SARIF. | сторонний · CC-BY-SA-4.0 |
| [`semgrep`](https://github.com/trailofbits/skills/tree/82fe8226252622fa807643bdca1710901198553a/plugins/static-analysis/skills/semgrep) | Статический анализ кода через Semgrep. | Для поиска уязвимостей и типовых ошибок в коде. | сторонний · CC-BY-SA-4.0 |
| [`supply-chain-risk-auditor`](https://github.com/trailofbits/skills/tree/82fe8226252622fa807643bdca1710901198553a/plugins/supply-chain-risk-auditor/skills/supply-chain-risk-auditor) | Аудит рисков цепочки поставок зависимостей. | Перед добавлением или обновлением зависимостей. | сторонний · CC-BY-SA-4.0 |

## Что не вошло

Пять наших скиллов не публикуются: они описывают частную инфраструктуру и маршрутизацию между нашими машинами, личный авторский голос, эксплуатацию и интерфейс собственного бота и закрытый игровой проект. Общие приёмы из них перенесены в опубликованные скиллы.

## Лицензии и атрибуция

- Наши скиллы публикуются на тех же условиях, что и остальной исходный код комплекта ([THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)).
- Наши скиллы, в которые вошли чужие тексты или код, хранят `NOTICE.md` и исходную лицензию автора внутри папки скилла; эти компоненты перечислены в [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
- У сторонних скиллов лицензия указана по их репозиторию на закреплённом коммите. Перед использованием проверьте её у автора: условия могут измениться в новых версиях.
- Скиллы с пометкой «нужен платный внешний сервис» без ключа и оплаты не работают.
