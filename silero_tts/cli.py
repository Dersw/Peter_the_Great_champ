"""Интерактивный CLI-интерфейс."""

import time
from loguru import logger

from .config import MODELS, DEFAULT_VOLUME, DEFAULT_SPEED, VOLUME_RANGE, SPEED_RANGE
from .audio import play_audio
from .utils import adjust_speed


def interactive_loop(tts_instance, speaker: str = "xenia") -> None:
    """Запускает интерактивный режим: ввод → синтез → воспроизведение."""
    global SPEED, VOLUME
    SPEED, VOLUME = DEFAULT_SPEED, DEFAULT_VOLUME

    logger.info("Интерактивный режим. Введите текст или команду.")
    logger.info("Команды: exit, speakers, lang <key>, vol <0.1-2.0>, speed <0.5-2.0>")

    cfg = MODELS[tts_instance.current_lang]
    current_speaker = speaker or cfg["speakers"][0]
    valid_speakers_lower = {s.lower() for s in cfg["speakers"]}

    while True:
        try:
            user_input = input(f"[{tts_instance.current_lang}/{current_speaker}] ▶ ").strip()
            if not user_input:
                continue
            cmd = user_input.lower()

            if cmd in ("exit", "quit", "q", "выход"):
                logger.info("Завершение работы")
                break

            if cmd in ("help", "h", "справка"):
                _print_help()
                continue

            if cmd == "speakers":
                _print_speakers(tts_instance.current_lang)
                continue

            if cmd.startswith("vol "):
                _handle_volume(cmd)
                continue

            if cmd.startswith("speed "):
                _handle_speed(cmd)
                continue

            if cmd.startswith("lang "):
                _handle_language(tts_instance, cmd)
                cfg = MODELS[tts_instance.current_lang]
                current_speaker = cfg["speakers"][0]
                valid_speakers_lower = {s.lower() for s in cfg["speakers"]}
                continue

            if cmd in valid_speakers_lower:
                current_speaker = next(s for s in cfg["speakers"] if s.lower() == cmd)
                logger.info(f" Голос: {current_speaker}")
                continue

            # Синтез и воспроизведение
            start = time.time()
            logger.info(" Синтез...")
            try:
                audio = tts_instance.synthesize(
                    text=user_input.lower().replace("я", "йа") + "...", speaker=current_speaker, put_accent=True, put_yo=False
                )
                latency = time.time() - start
                logger.info(f"Воспроизведение заняло: {latency:.3f}с)...")
                native_sr = MODELS[tts_instance.current_lang]["native_sr"]
                audio_adj = adjust_speed(audio, speed=SPEED)
                play_audio(audio_adj, sample_rate=native_sr, volume=VOLUME)
            except Exception as e:
                logger.error(f" Ошибка: {type(e).__name__}: {e}")

        except KeyboardInterrupt:
            print("\n Прервано. Введите 'exit' для выхода.")
        except EOFError:
            logger.info("\n Конец ввода.")
            break
        except Exception as e:
            logger.error(f" Критическая ошибка: {e}")


def _print_help() -> None:
    """Выводит справку по командам."""
    print(
        "\nКоманды:\n"
        "  exit/quit/q  — выход\n"
        "  speakers     — список голосов\n"
        "  lang <key>   — сменить язык (ru, en)\n"
        "  vol <0.1-2.0> — громкость (по умолч. 0.8)\n"
        "  speed <0.5-2.0> — скорость (по умолч. 1.0)\n"
        "  <имя_голоса> — сменить голос"
    )


def _print_speakers(lang_key: str) -> None:
    """Показывает доступные голоса для языка."""
    speakers = MODELS[lang_key]["speakers"]
    print(f"{lang_key}: {', '.join(speakers)}")


def _handle_volume(cmd: str) -> None:
    """Обрабатывает команду изменения громкости."""
    global VOLUME
    try:
        vol = float(cmd.split(" ", 1)[1])
        if VOLUME_RANGE[0] <= vol <= VOLUME_RANGE[1]:
            VOLUME = vol
            logger.info(f" Громкость: {vol}")
        else:
            logger.warning(f"Диапазон: {VOLUME_RANGE[0]} - {VOLUME_RANGE[1]}")
    except:
        logger.warning("Используй: vol 0.7")


def _handle_speed(cmd: str) -> None:
    """Обрабатывает команду изменения скорости."""
    global SPEED
    try:
        spd = float(cmd.split(" ", 1)[1])
        if SPEED_RANGE[0] <= spd <= SPEED_RANGE[1]:
            SPEED = spd
            logger.info(f" Скорость: {spd}x")
        else:
            logger.warning(f"Диапазон: {SPEED_RANGE[0]} - {SPEED_RANGE[1]}")
    except:
        logger.warning("Используй: speed 1.2")


def _handle_language(tts_instance, cmd: str) -> None:
    """Обрабатывает команду смены языка."""
    try:
        tts_instance.switch_language(cmd.split(" ", 1)[1].strip())
    except ValueError as ve:
        logger.error(str(ve))