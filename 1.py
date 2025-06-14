# ИСПРАВЛЕННАЯ ОФЛАЙН ВЕРСИЯ: video_transcriber_offline_fixed.py
import whisper
import os
import subprocess
import tempfile
import pyttsx3
import shutil
import argostranslate.package
import argostranslate.translate


def install_language_packages():
    """Автоматическая установка языковых пакетов для argostranslate"""
    try:
        print("Проверяем и устанавливаем языковые пакеты...")

        # Проверяем, есть ли уже установленные пакеты
        installed_languages = argostranslate.translate.get_installed_languages()
        from_lang_obj = next((l for l in installed_languages if l.code == "en"), None)
        to_lang_obj = next((l for l in installed_languages if l.code == "ru"), None)

        if from_lang_obj and to_lang_obj:
            print("Языковые пакеты уже установлены")
            return True

        # Обновляем индекс пакетов
        print("Обновляем индекс пакетов...")
        argostranslate.package.update_package_index()

        # Получаем список доступных пакетов
        available_packages = argostranslate.package.get_available_packages()

        # Находим пакет для перевода с английского на русский
        package_to_install = next(
            (pkg for pkg in available_packages
             if pkg.from_code == "en" and pkg.to_code == "ru"),
            None
        )

        if package_to_install:
            print(f"Найден пакет: {package_to_install}")
            print("Скачиваем и устанавливаем пакет...")
            argostranslate.package.install_from_path(package_to_install.download())
            print("Пакет установлен успешно!")
            return True
        else:
            print("Пакет en->ru не найден в доступных пакетах")
            return False

    except Exception as e:
        print(f"Ошибка при установке пакетов: {e}")
        return False


def translate_segments_with_fallback(segments, from_lang="en", to_lang="ru"):
    """Перевод с резервным вариантом через Google Translate"""

    # Сначала пробуем argostranslate
    print("Пытаемся использовать argostranslate...")
    try:
        installed_languages = argostranslate.translate.get_installed_languages()
        print(f"Установленные языки: {[lang.code for lang in installed_languages]}")

        from_lang_obj = next((l for l in installed_languages if l.code == from_lang), None)
        to_lang_obj = next((l for l in installed_languages if l.code == to_lang), None)

        if from_lang_obj and to_lang_obj:
            translation = from_lang_obj.get_translation(to_lang_obj)
            if translation:
                print("Используем argostranslate для перевода...")
                translated_segments = []
                for i, segment in enumerate(segments):
                    try:
                        translated_text = translation.translate(segment['text'])
                        segment['translated_text'] = translated_text
                        translated_segments.append(segment)
                        print(f"Переведен сегмент {i + 1}/{len(segments)}: {segment['text'][:50]}...")
                    except Exception as e:
                        print(f"Ошибка перевода сегмента {i + 1}: {e}")
                        segment['translated_text'] = segment['text']  # Оставляем оригинал
                        translated_segments.append(segment)

                print("Перевод через argostranslate завершен успешно!")
                return translated_segments
            else:
                raise Exception("Не удалось создать переводчик")
        else:
            raise Exception("Языковые пакеты не найдены")

    except Exception as e:
        print(f"Ошибка argostranslate: {e}")
        print("Переключаемся на Google Translate...")

        # Резервный вариант - googletrans
        try:
            from googletrans import Translator
            translator = Translator()

            print("Используем Google Translate для перевода...")
            translated_segments = []
            for i, segment in enumerate(segments):
                try:
                    result = translator.translate(segment['text'], src=from_lang, dest=to_lang)
                    segment['translated_text'] = result.text
                    translated_segments.append(segment)
                    print(f"Переведен сегмент {i + 1}/{len(segments)}: {segment['text'][:50]}...")
                except Exception as translate_error:
                    print(f"Ошибка перевода сегмента {i + 1}: {translate_error}")
                    segment['translated_text'] = segment['text']  # Оставляем оригинал
                    translated_segments.append(segment)

            print("Перевод через Google Translate завершен!")
            return translated_segments

        except ImportError:
            print("ERROR: googletrans не установлен!")
            print("Установите его командой: pip install googletrans==4.0.0-rc1")
            return None
        except Exception as e:
            print(f"Ошибка Google Translate: {e}")
            return None


def extract_audio_from_video(video_path, audio_path):
    """Извлечение аудио из видео"""
    if not os.path.exists(video_path):
        print(f"Ошибка: Видеофайл {video_path} не найден")
        return False

    print(f"Извлекаем аудио из {video_path}...")
    command = f'ffmpeg -i "{video_path}" -q:a 0 -map a "{audio_path}" -y'
    result = subprocess.call(command, shell=True)

    if result == 0 and os.path.exists(audio_path):
        print("Аудио успешно извлечено!")
        return True
    else:
        print("Ошибка при извлечении аудио")
        return False


def transcribe_audio_with_timestamps(audio_path):
    """Транскрибация аудио с временными метками"""
    if not os.path.exists(audio_path):
        print(f"Ошибка: Аудиофайл {audio_path} не найден")
        return None

    print("Загружаем модель Whisper...")
    model = whisper.load_model("base")

    print("Начинаем транскрибацию...")
    result = model.transcribe(audio_path, word_timestamps=True)

    print("Транскрибация завершена!")
    return result


def save_audio_with_pyttsx3(text, filepath):
    """Сохранение текста в аудиофайл с увеличенной громкостью"""
    try:
        engine = pyttsx3.init()
        
        # Увеличиваем громкость (0.0-1.0)
        engine.setProperty('volume', 0.9)  # Увеличено с 0.7 по умолчанию
        
        # Оптимальная скорость речи
        engine.setProperty('rate', 160)
        
        # Используем лучший голос (если доступен)
        voices = engine.getProperty('voices')
        if len(voices) > 0:
            engine.setProperty('voice', voices[0].id)
        
        engine.save_to_file(text, filepath)
        engine.runAndWait()
        return True
    except Exception as e:
        print(f"Ошибка при создании аудио: {e}")
        return False


def get_audio_duration(audio_path):
    """Получение длительности аудиофайла"""
    try:
        cmd = f'ffprobe -v quiet -show_entries format=duration -of csv=p=0 "{audio_path}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except:
        return 0.0


def normalize_audio(input_path, output_path):
    """Нормализация громкости аудио"""
    cmd = f'ffmpeg -i "{input_path}" -filter:a "loudnorm=I=-16:LRA=11:TP=-1.5" "{output_path}" -y'
    subprocess.call(cmd, shell=True)
    return os.path.exists(output_path)


def create_synchronized_translation(translated_segments, output_path, original_audio_path):
    """Создание синхронизированного аудио перевода с нормализацией громкости"""
    print("Создаем синхронизированный аудио перевод с привязкой к субтитрам...")

    temp_dir = tempfile.mkdtemp()
    batch_size = 50
    intermediate_files = []

    try:
        total_duration = get_audio_duration(original_audio_path)
        if total_duration == 0:
            print("Не удалось определить длительность оригинального аудио")
            return False

        print(f"Общая длительность аудио: {total_duration:.2f} секунд")

        # Process segments in batches
        for batch_start in range(0, len(translated_segments), batch_size):
            batch_end = min(batch_start + batch_size, len(translated_segments))
            batch = translated_segments[batch_start:batch_end]

            batch_files = []
            filter_parts = []

            for i, segment in enumerate(batch):
                segment_file = os.path.join(temp_dir, f"batch_{batch_start}_segment_{i}.wav")
                print(f"Создаем аудио для сегмента {batch_start + i + 1}/{len(translated_segments)}")

                if save_audio_with_pyttsx3(segment['translated_text'], segment_file):
                    segment_duration = get_audio_duration(segment_file)
                    original_duration = segment['end'] - segment['start']

                    if segment_duration > original_duration:
                        speed_factor = segment_duration / original_duration
                        speeded_file = os.path.join(temp_dir, f"speeded_batch_{batch_start}_segment_{i}.wav")
                        speed_cmd = f'ffmpeg -i "{segment_file}" -filter:a "atempo={speed_factor}" "{speeded_file}" -y'
                        subprocess.call(speed_cmd, shell=True)
                        if os.path.exists(speeded_file):
                            os.remove(segment_file)
                            segment_file = speeded_file

                    batch_files.append(segment_file)
                    filter_parts.append(
                        f"[{i}]adelay={int(segment['start'] * 1000)}|{int(segment['start'] * 1000)}[delayed{i}]")

            if not batch_files:
                continue

            # Process this batch
            batch_output = os.path.join(temp_dir, f"batch_{batch_start}.wav")
            input_args = ' '.join([f'-i "{f}"' for f in batch_files])

            if len(batch_files) == 1:
                cmd = f'ffmpeg {input_args} -filter_complex "{filter_parts[0]}" -map "[delayed0]" -t {total_duration} "{batch_output}" -y'
            else:
                mix_filter = ';'.join(filter_parts)
                delayed_inputs = ''.join([f'[delayed{i}]' for i in range(len(batch_files))])
                cmd = f'ffmpeg {input_args} -filter_complex "{mix_filter};{delayed_inputs}amix=inputs={len(batch_files)}:duration=longest,volume=2.0" -t {total_duration} "{batch_output}" -y'

            subprocess.call(cmd, shell=True)
            intermediate_files.append(batch_output)

        # Merge all batches
        if not intermediate_files:
            print("Не удалось создать ни одного аудио сегмента")
            return False

        temp_output = os.path.join(temp_dir, "pre_normalized.wav")
        
        if len(intermediate_files) == 1:
            os.rename(intermediate_files[0], temp_output)
        else:
            input_args = ' '.join([f'-i "{f}"' for f in intermediate_files])
            cmd = f'ffmpeg {input_args} -filter_complex "amix=inputs={len(intermediate_files)}:duration=longest,volume=1.5" -t {total_duration} "{temp_output}" -y'
            subprocess.call(cmd, shell=True)

        # Нормализуем громкость
        if not normalize_audio(temp_output, output_path):
            print("Не удалось нормализовать громкость")
            return False

        return os.path.exists(output_path)

    except Exception as e:
        print(f"Ошибка при создании синхронизированного аудио: {e}")
        return False
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            print(f"Ошибка при очистке временных файлов: {e}")


def create_enhanced_subtitle_file(translated_segments, output_path):
    """Создание улучшенного файла субтитров с более точной синхронизацией"""
    print("Создаем файл субтитров с улучшенной синхронизацией...")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(translated_segments):
                f.write(f"{i + 1}\n")

                # Более точное форматирование времени
                start_time = format_time_precise(segment['start'])
                end_time = format_time_precise(segment['end'])

                f.write(f"{start_time} --> {end_time}\n")

                # Разбиваем длинные строки на части для лучшей читаемости
                text = segment['translated_text']
                if len(text) > 60:
                    # Разбиваем на строки по 60 символов
                    words = text.split()
                    lines = []
                    current_line = []
                    current_length = 0

                    for word in words:
                        if current_length + len(word) + 1 <= 60:
                            current_line.append(word)
                            current_length += len(word) + 1
                        else:
                            if current_line:
                                lines.append(' '.join(current_line))
                            current_line = [word]
                            current_length = len(word)

                    if current_line:
                        lines.append(' '.join(current_line))

                    f.write('\n'.join(lines) + '\n\n')
                else:
                    f.write(f"{text}\n\n")

        print("Файл субтитров создан успешно!")
        return True
    except Exception as e:
        print(f"Ошибка при создании субтитров: {e}")
        return False


def format_time_precise(seconds):
    """Более точное форматирование времени для субтитров"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_remainder = seconds % 60
    milliseconds = int((seconds_remainder - int(seconds_remainder)) * 1000)
    return f"{hours:02}:{minutes:02}:{int(seconds_remainder):02},{milliseconds:03}"


def format_time(seconds):
    """Форматирование времени для субтитров"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds_remainder = seconds % 60
    milliseconds = int((seconds_remainder - int(seconds_remainder)) * 1000)
    return f"{hours:02}:{minutes:02}:{int(seconds_remainder):02},{milliseconds:03}"


def merge_video_audio_subtitles_precise(video_path, translated_audio_path, subtitle_path, output_path):
    """Точное объединение видео, переведенного аудио и субтитров с балансировкой громкости"""
    print("Объединяем видео с переводом и субтитрами (точная синхронизация)...")

    # Сначала заменяем аудиодорожку с нормализацией громкости
    print("Заменяем аудиодорожку с нормализацией громкости...")
    temp_video = "temp_video_precise.mp4"
    temp_audio = "temp_audio_normalized.wav"

    # Нормализуем громкость перевода перед объединением
    if not normalize_audio(translated_audio_path, temp_audio):
        print("Не удалось нормализовать громкость перевода")
        return False

    # Объединяем видео с нормализованным аудио
    audio_cmd = f'ffmpeg -i "{video_path}" -i "{temp_audio}" -c:v copy -c:a aac -b:a 192k -af "volume=1.5" -async 1 -vsync 1 -map 0:v:0 -map 1:a:0 "{temp_video}" -y'
    result1 = subprocess.call(audio_cmd, shell=True)

    if result1 != 0:
        print("Ошибка при замене аудиодорожки")
        return False

    # Добавляем субтитры
    print("Добавляем субтитры с точной синхронизацией...")
    subtitle_path_escaped = subtitle_path.replace('\\', '\\\\').replace(':', '\\:')

    subtitle_cmd = f'ffmpeg -i "{temp_video}" -vf "subtitles=\'{subtitle_path_escaped}\':force_style=\'FontSize=20,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,Shadow=1\'" -c:a copy "{output_path}" -y'
    result2 = subprocess.call(subtitle_cmd, shell=True)

    # Удаляем временные файлы
    for temp_file in [temp_video, temp_audio]:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

    success = result2 == 0 and os.path.exists(output_path)
    if success:
        print("Финальное видео с точной синхронизацией создано успешно!")
    else:
        print("Ошибка при создании финального видео")

    return success


def main():
    """Основная функция"""
    print("=== ВИДЕО ПЕРЕВОДЧИК ===")
    print("Начинаем обработку...")

    # Пути к файлам
    video_path = "1.mp4"
    audio_path = "audio.wav"
    translated_audio_path = "translated.wav"
    subtitle_path = "subtitles.srt"
    output_video_path = "video_with_translation.mp4"

    # Проверяем наличие исходного видео
    if not os.path.exists(video_path):
        print(f"Ошибка: Видеофайл {video_path} не найден!")
        return

    # Устанавливаем языковые пакеты
    install_success = install_language_packages()
    if not install_success:
        print("Внимание: Не удалось установить языковые пакеты argostranslate")
        print("Будем использовать Google Translate")

    # Извлекаем аудио из видео
    if not extract_audio_from_video(video_path, audio_path):
        print("Не удалось извлечь аудио. Завершение работы.")
        return

    # Транскрибируем аудио
    transcription_result = transcribe_audio_with_timestamps(audio_path)
    if not transcription_result:
        print("Не удалось транскрибировать аудио. Завершение работы.")
        return

    # Сохраняем транскрипцию
    with open("transcription.txt", "w", encoding="utf-8") as f:
        f.write(transcription_result['text'])
    print("Транскрипция сохранена в transcription.txt")

    # Переводим сегменты
    translated_segments = translate_segments_with_fallback(transcription_result['segments'])
    if not translated_segments:
        print("Не удалось перевести текст. Завершение работы.")
        return

    # Сохраняем перевод
    with open("translation.txt", "w", encoding="utf-8") as f:
        f.write(" ".join([s['translated_text'] for s in translated_segments]))
    print("Перевод сохранен в translation.txt")

    # Создаем улучшенные субтитры
    if not create_enhanced_subtitle_file(translated_segments, subtitle_path):
        print("Не удалось создать субтитры. Завершение работы.")
        return

    # Создаем синхронизированное аудио с привязкой к субтитрам
    if not create_synchronized_translation(translated_segments, translated_audio_path, audio_path):
        print("Не удалось создать синхронизированное аудио. Завершение работы.")
        return

    # Объединяем все в финальное видео с точной синхронизацией
    if merge_video_audio_subtitles_precise(video_path, translated_audio_path, subtitle_path, output_video_path):
        print(f"\n=== ГОТОВО! ===")
        print(f"Переведенное видео сохранено: {output_video_path}")
        print(f"Транскрипция: transcription.txt")
        print(f"Перевод: translation.txt")
        print(f"Субтитры: {subtitle_path}")
    else:
        print("Не удалось создать финальное видео")

    # Очищаем временные файлы
    temp_files = [audio_path, translated_audio_path]
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
                print(f"Удален временный файл: {temp_file}")
            except Exception as e:
                print(f"Не удалось удалить {temp_file}: {e}")


if __name__ == "__main__":
    main()