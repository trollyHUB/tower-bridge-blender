# Разработка и проверка

Команды применяются к исходникам v1.1.0 на 15 октября 2026 года; результаты приёмки новой версии зафиксированы в отчёте. Фактические результаты и границы проверок см. в [отчёте v1.1.0](IMPLEMENTATION_REPORT_v1.1.0.md).

Нужны Blender 5.2.1 LTS, Git LFS и Python для тестов без Blender. `bpy` отдельно устанавливать не нужно. Cycles поддерживает CPU; совместимый GPU необязателен. Перед редактированием сохраните ручные изменения сцены отдельно.

## Полная последовательность

```powershell
./scripts/project.ps1 -Action Build
./scripts/project.ps1 -Action Finalize
./scripts/project.ps1 -Action Validate
python -m unittest discover -s tests -v
./scripts/project.ps1 -Action Preview
./scripts/project.ps1 -Action PreviewEncode
./scripts/project.ps1 -Action Benchmark
./scripts/project.ps1 -Action Stills
python tools/verify_stills.py
./scripts/project.ps1 -Action Animation
./scripts/project.ps1 -Action Encode
./scripts/project.ps1 -Action VideoCheck
python tools/package_release.py
python tools/check_release.py
```

При нестандартной установке добавьте `-BlenderPath 'D:\Apps\Blender\blender.exe'`. Диапазон по умолчанию берётся из конфигурации. Для частичного расчёта: `-Action Animation -StartFrame 481 -EndFrame 960`; Preview принимает тот же диапазон. Для полного PreviewEncode нужны все 1440 preview-кадров. Режим Benchmark рассчитывает начало, середину и конец и сохраняет время; если пик памяти недоступен, это явно отмечается в JSON.

Build создаёт сцену заново. Finalize обновляет встроенную инструкцию и сохраняет `.blend`; выполните его до всех итоговых кадров. Validate обращается к `scene_components.validation`. Stills создаёт пять основных изображений Open/Closed/City/Water/Evening и дополнительный Detail.

`tools/check_release.py` распаковывает ZIP в отдельную локальную папку и открывает
сцену в Blender без сохранения. Для другой установки Blender используйте аргумент
`--blender`. Для фактической проверки CPU и памяти запустите Blender в фоне с
`--python tools/diagnose_scene.py`; результат попадёт в `Tower_Bridge/diagnostics.json`.

## Кеш и артефакты

Кадры лежат в `research/render_runs/<identity>/`. Манифест учитывает SHA-256 сцены, конфигурации, скрипта рендера и helper-кода, версию Blender и профиль. Preview не подменяет финальные кадры. Повторный запуск продолжает совместимый диапазон, проверяя PNG; повреждённый файл требует пересчёта. Изменения источников следует завершить до долгого рендера.

Encode проверяет полноту PNG, создаёт `Tower_Bridge/Tower_Bridge_Animation.mp4` и `video_validation.json`. PreviewEncode создаёт отдельные `Tower_Bridge_Preview.mp4` и `preview_validation.json`. VideoCheck проверяет финальный MP4 и декодирует семь контрольных фаз. Упаковщик проверяет текущие хеши, число кадров, fps и размеры из актуальной конфигурации, а также полный проход декодирования кодека и результаты проверок перед созданием `Tower_Bridge_Project.zip`.

Файлы в рабочей папке могут остаться от прежней сборки: окончательный статус берётся из отчёта реализации и проверочных JSON. Само существование `.mp4` или `.png` не доказывает актуальность.

## Git и проверки

После клонирования выполните `git lfs install --local` и `git lfs pull`. `.blend` — бинарный LFS-файл; его нельзя сливать как текст. При конфликте восстановите сцену из согласованных исходников. `research/`, видео, ZIP, Python-кеш и резервные копии Blender исключены из Git.

Тесты `tests/` выполняются без Blender. Проверка синтаксиса и JSON не подтверждает геометрические зазоры и визуальное качество. До релиза отдельно пройти A01–A12 и весь ролик. E01–E05 остаются последующими дополнениями.
