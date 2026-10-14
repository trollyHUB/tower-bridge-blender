# Разработка и Git

Команды ниже описывают текущую реализацию v0.1.0. Будущая реорганизация и переход к 60-секундному сценарию раскрыты в [архитектуре](ARCHITECTURE.md); она ещё не выполнена. Общий порядок новых работ находится в [плане разработки](PROJECT_PLAN.md) и [очереди задач](BACKLOG.md).

## Требования

- Git и Git LFS.
- Blender 5.2.1 LTS — проверенная версия.
- PowerShell для `scripts/project.ps1` либо прямой запуск Blender из терминала.
- Обычный Python 3.11+ нужен только для упаковки ZIP и проверки синтаксиса.
- OptiX-совместимая NVIDIA нужна для текущих режимов `Stills`, `Benchmark` и `Finalize`. Остальные режимы не требуют настройки OptiX; готовая сцена использует CPU в Cycles.

Все пути основных скриптов вычисляются относительно корня проекта. Учебные документы и исходные FBX/GLB из внешних папок не нужны для сборки.

## Сборка и проверка

Запускайте из корня репозитория. Для проверки существующей сцены:

```powershell
./scripts/project.ps1 -Action Validate
```

Для создания сцены с нуля и сохранения настроенного проекта:

```powershell
./scripts/project.ps1 -Action Build
./scripts/project.ps1 -Action Finalize
./scripts/project.ps1 -Action Validate
```

`Build` перезаписывает `Tower_Bridge/Tower_Bridge.blend` и создаёт статистику и примечания. Перед сборкой сохраните ручные правки сцены под другим именем. `Finalize` устанавливает анимированную камеру, первый кадр и добавляет русскую инструкцию в файл.

Прямой запуск без PowerShell-обёртки:

```bash
blender --background --python-exit-code 1 --python build_tower_bridge.py
blender --background --python-exit-code 1 --python render_tower_bridge.py -- validate
```

## Изображения и видео

```powershell
./scripts/project.ps1 -Action Stills
./scripts/project.ps1 -Action Animation -StartFrame 1 -EndFrame 720
./scripts/project.ps1 -Action Encode
./scripts/project.ps1 -Action VideoCheck
```

`Stills` сохраняет три PNG в `Tower_Bridge/renders/`. `Animation` создаёт кадры в `research/animation_frames/`, `Encode` собирает MP4, `VideoCheck` декодирует три контрольных кадра в `research/`.

Рендер анимации пропускает уже существующие кадры, что позволяет продолжить прерванный расчёт. После изменения сцены используйте свежую папку кадров: старые PNG не пересчитываются автоматически. Удобный способ сохранить их — переименовать `research/animation_frames/` перед новым расчётом.

## Рабочий процесс Git

Основная ветка — `main`. Для отдельной задачи создайте ветку:

```bash
git switch -c feat/traffic
git status
git add build_tower_bridge.py render_tower_bridge.py docs/ROADMAP.md
git commit -m "Add traffic routes and bridge stop sequence"
git push -u origin feat/traffic
```

Добавляйте только нужные изменения. После изменения сцены добавьте её явно:

```bash
git add Tower_Bridge/Tower_Bridge.blend
git lfs ls-files
```

`.blend`, `.fbx`, `.glb`, `.hdr` и `.exr` настроены для Git LFS. PNG-превью хранятся в обычном Git. Логи, исследование, промежуточные кадры, MP4, ZIP и резервные копии Blender не попадают в коммиты.

Blender-файл нельзя объединять как текст. При конфликте двух версий сцены согласуйте изменения в Blender или восстановите нужную сцену из источников; не пытайтесь вручную объединить бинарный файл. Разделение будущих крупных компонентов на отдельные `.blend` уменьшит такие конфликты.

В текущем репозитории настроен GitHub-адрес `noreply` для автора коммитов. Глобальные настройки имени, почты и доступа к Git не менялись.

## Проверки на GitHub

Workflow `Project checks` проверяет синтаксис Python, синтаксис PowerShell и чтение JSON. Проверка не запускает Blender и не оценивает внешний вид рендера. Саму сцену проверяйте через режим `Validate` и контрольные изображения после изменений геометрии или анимации.

## Релизы

После проверки проекта и видео:

```bash
python tools/package_release.py
```

Архив содержит сцену, изображения, видео, документацию и исходники. В него не входят `.git`, кадры анимации, локальное исследование и credentials. Для следующего релиза можно использовать GitHub CLI:

```bash
gh release create v0.2.0 Tower_Bridge_Project.zip Tower_Bridge/Tower_Bridge_Animation.mp4 --title "Tower Bridge v0.2.0" --notes-file release-notes.txt
```

Перед выполнением подготовьте реальные примечания и выберите версию согласно выполненным изменениям. Публичный репозиторий уже создан в аккаунте `trollyHUB`; самостоятельно создавать его повторно не нужно.
