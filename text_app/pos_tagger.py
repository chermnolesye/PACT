import json
import os
import shlex
import subprocess
from pathlib import Path
from urllib import parse, request
from uuid import uuid4

from django.conf import settings
from django.db import transaction

from core_app.models import Text, Sentence, Token, PosTag


CORENLP_TREEBANK_TO_DB_TAG = {
    # adjectives / adverbs
    "JJ": "ADJ",
    "JJR": "ADJ",
    "JJS": "ADJ",
    "RB": "ADV",
    "RBR": "ADV",
    "RBS": "ADV",
    "WRB": "ADV",

    # nouns / proper nouns
    "NN": "NOUN",
    "NNS": "NOUN",
    "NNP": "PROPN",
    "NNPS": "PROPN",

    # pronouns
    "PRP": "PRON",
    "PRP$": "PRON",
    "WP": "PRON",
    "WP$": "PRON",
    "EX": "PRON",

    # determiners
    "DT": "DET",
    "WDT": "DET",
    "PDT": "DET",

    # particles
    "RP": "PART",
    "POS": "PART",
    "TO": "PART",

    # numerals
    "CD": "NUM",

    # conjunctions
    "CC": "CCONJ",
    "IN": "SCONJ",

    # verbs / auxiliaries
    "VB": "VERB",
    "VBD": "VERB",
    "VBG": "VERB",
    "VBN": "VERB",
    "VBP": "VERB",
    "VBZ": "VERB",
    "MD": "AUX",

    # interjections / symbols / other
    "UH": "INTJ",
    "SYM": "SYM",
    "FW": "X",
    "LS": "X",

    # punctuation
    ",": "PUNCT",
    ".": "PUNCT",
    ":": "PUNCT",
    "``": "PUNCT",
    "''": "PUNCT",
    "-LRB-": "PUNCT",
    "-RRB-": "PUNCT",
    "-LSB-": "PUNCT",
    "-RSB-": "PUNCT",
    "-LCB-": "PUNCT",
    "-RCB-": "PUNCT",
    "#": "PUNCT",
    "$": "SYM",
}


DIRECT_DB_TAGS = {
    "ADJ",
    "ADP",
    "ADV",
    "AUX",
    "CCONJ",
    "DET",
    "INTJ",
    "NOUN",
    "NUM",
    "PART",
    "PRON",
    "PROPN",
    "PUNCT",
    "SCONJ",
    "SYM",
    "VERB",
    "DET:PART",
    "X",
}


def is_pos_tagger_available() -> bool:
    """
    Проверяет доступность активного POS-разметчика из настроек.
    """
    backend = getattr(settings, "POS_TAGGER_BACKEND", "").lower()

    if backend == "rftagger":
        return is_rftagger_available()

    if backend == "corenlp":
        return is_corenlp_available()

    return False


def is_rftagger_available() -> bool:
    """
    Проверяет, доступен ли RFTagger в текущей среде.
    """
    try:
        if settings.USE_WSL_FOR_RFTAGGER:
            command = (
                f"cd {shlex.quote(settings.RFTAGGER_PATH)} "
                f"&& test -x ./cmd/rftagger-{shlex.quote(settings.RFTAGGER_LANGUAGE)}"
            )
            subprocess.run(
                ["wsl", "bash", "-lc", command],
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            binary_path = os.path.join(
                settings.RFTAGGER_PATH,
                "cmd",
                f"rftagger-{settings.RFTAGGER_LANGUAGE}",
            )
            if not os.path.isfile(binary_path):
                return False

        return True

    except Exception:
        return False


def is_corenlp_available() -> bool:
    """
    Проверяет, отвечает ли CoreNLP сервер.
    """
    try:
        base_url = getattr(settings, "CORENLP_URL", "").rstrip("/")
        if not base_url:
            return False

        _run_corenlp("Bonjour.")
        return True

    except Exception:
        return False


def annotate_text_pos(text_id: int) -> dict:
    """
    Выполняет POS-разметку текста через backend из settings.POS_TAGGER_BACKEND.
    Поддерживает:
    - rftagger
    - corenlp
    """
    backend = getattr(settings, "POS_TAGGER_BACKEND", "").lower()

    if not is_pos_tagger_available():
        return {
            "success": False,
            "message": f"POS-разметчик '{backend}' недоступен в текущей среде",
            "updated_tokens": 0,
            "skipped_tokens": 0,
            "errors": [f"POS-разметчик '{backend}' недоступен, разметка пропущена"],
        }

    text = Text.objects.filter(idtext=text_id).first()
    if not text:
        return {
            "success": False,
            "message": f"Текст с id={text_id} не найден",
            "updated_tokens": 0,
            "skipped_tokens": 0,
            "errors": [],
        }

    sentences = list(
        Sentence.objects.filter(idtext=text).order_by("ordernumber")
    )
    if not sentences:
        return {
            "success": False,
            "message": f"У текста id={text_id} нет предложений",
            "updated_tokens": 0,
            "skipped_tokens": 0,
            "errors": [],
        }

    pos_tag_map = _get_pos_tag_map()
    if not pos_tag_map:
        return {
            "success": False,
            "message": "Таблица PosTag пуста или в ней нет tagtext/tagtextabbrev",
            "updated_tokens": 0,
            "skipped_tokens": 0,
            "errors": [],
        }

    token_objects = list(
        Token.objects.filter(idsentence__idtext=text)
        .select_related("idsentence")
        .order_by("idsentence__ordernumber", "tokenordernumber")
    )

    sentence_tokens = [
        {
            "idtoken": token.idtoken,
            "tokentext": token.tokentext,
            "tokenordernumber": token.tokenordernumber,
        }
        for token in token_objects
    ]

    if not sentence_tokens:
        return {
            "success": False,
            "message": f"У текста id={text_id} нет токенов",
            "updated_tokens": 0,
            "skipped_tokens": 0,
            "errors": [],
        }

    full_text = "\n".join(
        (sentence.sentensetext or "").replace("-EMPTY-", "").strip()
        for sentence in sentences
        if (sentence.sentensetext or "").replace("-EMPTY-", "").strip()
    )

    if not full_text.strip():
        return {
            "success": False,
            "message": f"У текста id={text_id} пустой текст для разметки",
            "updated_tokens": 0,
            "skipped_tokens": 0,
            "errors": [],
        }

    errors = []
    updated_tokens = 0
    skipped_tokens = 0

    try:
        if backend == "rftagger":
            raw_output = _run_rftagger(full_text)
            parsed_tokens = _parse_rftagger_output(raw_output)

        elif backend == "corenlp":
            raw_output = _run_corenlp(full_text)
            parsed_tokens = _parse_corenlp_output(raw_output)

        else:
            return {
                "success": False,
                "message": f"Неизвестный backend POS-разметки: {backend}",
                "updated_tokens": 0,
                "skipped_tokens": 0,
                "errors": [f"Неизвестный backend: {backend}"],
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Ошибка запуска POS-разметчика '{backend}'",
            "updated_tokens": 0,
            "skipped_tokens": 0,
            "errors": [str(e)],
        }

    if not parsed_tokens:
        return {
            "success": False,
            "message": f"{backend} не вернул токены",
            "updated_tokens": 0,
            "skipped_tokens": 0,
            "errors": [f"{backend} вернул пустой результат"],
        }

    map_result, error_score = _fast_map_lists(parsed_tokens, sentence_tokens)

    if map_result is None:
        map_result, error_score = _map_lists(
            parsed_tokens,
            sentence_tokens,
            0,
            0,
            0,
        )

    if error_score > 10:
        errors.append(f"Слишком много ошибок сопоставления токенов: {error_score}")

    if backend == "rftagger":
        converted_result = _convert_rftagger_tags(map_result)
    elif backend == "corenlp":
        converted_result = _convert_corenlp_tags(map_result)
    else:
        converted_result = []

    token_by_id = {token.idtoken: token for token in token_objects}
    changed_tokens = []

    with transaction.atomic():
        Token.objects.filter(idsentence__idtext=text).update(idpostag=None)

        for token_id, final_tag in converted_result:
            pos_tag_obj = pos_tag_map.get(final_tag)

            if not pos_tag_obj:
                skipped_tokens += 1
                errors.append(
                    f"Для token_id={token_id} не найден PosTag для тега '{final_tag}'"
                )
                continue

            token_obj = token_by_id.get(token_id)
            if not token_obj:
                skipped_tokens += 1
                errors.append(f"Не найден токен с id={token_id}")
                continue

            token_obj.idpostag = pos_tag_obj
            changed_tokens.append(token_obj)
            updated_tokens += 1

        if changed_tokens:
            Token.objects.bulk_update(changed_tokens, ["idpostag"])

    success_message = "POS-разметка завершена"
    if skipped_tokens > 0:
        success_message += f" (обновлено: {updated_tokens}, пропущено: {skipped_tokens})"

    return {
        "success": True,
        "message": success_message,
        "updated_tokens": updated_tokens,
        "skipped_tokens": skipped_tokens,
        "errors": errors,
    }


def _get_pos_tag_map() -> dict:
    """
    Собирает словарь POS-тегов.
    """
    result = {}

    for tag in PosTag.objects.all():
        abbrev = (tag.tagtextabbrev or "").strip()
        full_tag = (tag.tagtext or "").strip()

        if abbrev:
            result[abbrev] = tag

        if full_tag:
            result[full_tag] = tag

    return result


def _run_rftagger(text_content: str) -> str:
    """
    Запускает RFTagger на всём тексте.
    """
    tmp_dir = Path(settings.BASE_DIR) / "_rftagger_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    temp_path = tmp_dir / f"{uuid4().hex}.txt"
    temp_path.write_text(text_content + "\n", encoding="utf-8", newline="\n")

    try:
        if settings.USE_WSL_FOR_RFTAGGER:
            wsl_input_path = _windows_path_to_wsl_path(str(temp_path))
            rftagger_path = settings.RFTAGGER_PATH

            command = (
                f"cd {shlex.quote(rftagger_path)} "
                f"&& ./cmd/rftagger-{shlex.quote(settings.RFTAGGER_LANGUAGE)} {shlex.quote(wsl_input_path)}"
            )

            completed = subprocess.run(
                ["wsl", "bash", "-lc", command],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )
        else:
            command = [
                os.path.join(
                    settings.RFTAGGER_PATH,
                    "cmd",
                    f"rftagger-{settings.RFTAGGER_LANGUAGE}",
                ),
                str(temp_path),
            ]

            completed = subprocess.run(
                command,
                cwd=settings.RFTAGGER_PATH,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )

        return completed.stdout

    finally:
        if temp_path.exists():
            temp_path.unlink()


def _run_corenlp(text_content: str) -> dict:
    """
    Отправляет текст в CoreNLP сервер и получает JSON.
    """
    base_url = getattr(settings, "CORENLP_URL", "").rstrip("/")
    annotators = getattr(settings, "CORENLP_ANNOTATORS", "tokenize,ssplit,pos")
    language = getattr(settings, "CORENLP_LANGUAGE", "french")

    if not base_url:
        raise RuntimeError("CORENLP_URL не задан в настройках")

    properties = {
        "annotators": annotators,
        "outputFormat": "json",
        "pipelineLanguage": language,
        "tokenize.language": language,
        "ssplit.isOneSentence": "false",
    }

    query = parse.urlencode({
        "properties": json.dumps(properties, ensure_ascii=False)
    })

    url = f"{base_url}/?{query}"
    data = text_content.encode("utf-8")

    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "text/plain; charset=utf-8"},
        method="POST",
    )

    with request.urlopen(req, timeout=60) as response:
        body = response.read().decode("utf-8")

    return json.loads(body)


def _windows_path_to_wsl_path(windows_path: str) -> str:
    """
    Преобразует путь Windows в путь WSL.
    """
    path = Path(windows_path).resolve()
    drive = path.drive.rstrip(":").lower()
    tail = str(path).replace(path.drive, "").replace("\\", "/")

    return f"/mnt/{drive}{tail}"


def _parse_rftagger_output(raw_output: str) -> list:
    """
    Преобразует stdout RFTagger в список (token_text, raw_tag).
    """
    result = []

    for line in raw_output.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("reading parameter file"):
            continue
        if line == "0" or line == "1":
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        token_text = parts[0]
        raw_tag = parts[1]
        result.append((token_text, raw_tag))

    return result


def _parse_corenlp_output(raw_output: dict) -> list:
    """
    Преобразует JSON CoreNLP в список (token_text, raw_tag).
    """
    result = []

    sentences = raw_output.get("sentences", [])
    for sentence in sentences:
        for token in sentence.get("tokens", []):
            token_text = token.get("originalText") or token.get("word") or ""
            raw_tag = token.get("pos") or ""
            if token_text and raw_tag:
                result.append((token_text, raw_tag))

    return result


def _convert_rftagger_tags(rftagger_map: list) -> list:
    """
    Преобразует теги RFTagger в сокращения, используемые в базе.
    """
    result = []

    for token_id, raw_tag in rftagger_map:
        if raw_tag.startswith("ADJA"):
            result.append((token_id, "ADJA"))
        elif raw_tag.startswith("ADJD"):
            result.append((token_id, "ADJD"))
        elif raw_tag.startswith("ADV"):
            result.append((token_id, "ADV"))
        elif raw_tag.startswith("APPRART"):
            result.append((token_id, "APPRART"))
        elif raw_tag.startswith("APPR"):
            result.append((token_id, "APPR"))
        elif raw_tag.startswith("APPO"):
            result.append((token_id, "APPO"))
        elif raw_tag.startswith("APZR"):
            result.append((token_id, "APZR"))
        elif raw_tag.startswith("ART"):
            result.append((token_id, "ART"))
        elif raw_tag.startswith("CARD"):
            result.append((token_id, "CARD"))
        elif raw_tag.startswith("FM"):
            result.append((token_id, "FM"))
        elif raw_tag.startswith("ITJ"):
            result.append((token_id, "ITJ"))
        elif raw_tag.startswith("CONJ.Coord"):
            result.append((token_id, "KON"))
        elif raw_tag.startswith("CONJ.Comp"):
            result.append((token_id, "KOKOM"))
        elif raw_tag.startswith("CONJ.SubInf"):
            result.append((token_id, "KOUI"))
        elif raw_tag.startswith("CONJ.SubFin"):
            result.append((token_id, "KOUS"))
        elif raw_tag.startswith("N.Reg"):
            result.append((token_id, "NN"))
        elif raw_tag.startswith("N.Name"):
            result.append((token_id, "NE"))
        elif raw_tag.startswith("PRO.Dem.Attr"):
            result.append((token_id, "PDAT"))
        elif raw_tag.startswith("PRO.Dem.Subst"):
            result.append((token_id, "PDS"))
        elif raw_tag.startswith("PRO.Indef.Attr"):
            result.append((token_id, "PIAT"))
        elif raw_tag.startswith("PRO.Indef.Subst"):
            result.append((token_id, "PIS"))
        elif raw_tag.startswith("PRO.Pers"):
            result.append((token_id, "PPER"))
        elif raw_tag.startswith("PRO.Inter.Subst"):
            result.append((token_id, "PWS"))
        elif raw_tag.startswith("PRO.Inter.Attr"):
            result.append((token_id, "PWAT"))
        elif raw_tag.startswith("PRO.Poss.Subst"):
            result.append((token_id, "PPOSS"))
        elif raw_tag.startswith("PRO.Poss.Attr"):
            result.append((token_id, "PPOSAT"))
        elif raw_tag.startswith("PRO.Rel.Subst"):
            result.append((token_id, "PRELS"))
        elif raw_tag.startswith("PRO.Rel.Attr"):
            result.append((token_id, "PRELAT"))
        elif raw_tag.startswith("PRO.Refl"):
            result.append((token_id, "PRF"))
        elif raw_tag.startswith("PROADV"):
            result.append((token_id, "PROAV"))
        elif raw_tag.startswith("PART.Zu"):
            result.append((token_id, "PTKZU"))
        elif raw_tag.startswith("PART.Neg"):
            result.append((token_id, "PTKNEG"))
        elif raw_tag.startswith("PART.Verb"):
            result.append((token_id, "PTKVZ"))
        elif raw_tag.startswith("PART.Ans"):
            result.append((token_id, "PTKANT"))
        elif raw_tag.startswith("PART.Deg"):
            result.append((token_id, "PTKA"))
        elif raw_tag.startswith("TRUNC"):
            result.append((token_id, "TRUNC"))
        elif raw_tag.startswith("VFIN.Aux"):
            result.append((token_id, "VAFIN"))
        elif raw_tag.startswith("VFIN.Mod"):
            result.append((token_id, "VMFIN"))
        elif raw_tag.startswith("VFIN.Sein") or raw_tag.startswith("VFIN.Haben") or raw_tag.startswith("VFIN.Full"):
            result.append((token_id, "VVFIN"))
        elif raw_tag.startswith("VINF.Aux"):
            result.append((token_id, "VAINF"))
        elif raw_tag.startswith("VINF.Mod"):
            result.append((token_id, "VMINF"))
        elif raw_tag.startswith("VINF.Full.zu") or raw_tag.startswith("VINF.Sein.zu") or raw_tag.startswith("VINF.Haben.zu"):
            result.append((token_id, "VVIZU"))
        elif raw_tag.startswith("VINF.Full") or raw_tag.startswith("VINF.Sein") or raw_tag.startswith("VINF.Haben"):
            result.append((token_id, "VVINF"))
        elif raw_tag.startswith("VIMP.Full"):
            result.append((token_id, "VVIMP"))
        elif raw_tag.startswith("VPP.Full"):
            result.append((token_id, "VVPP"))
        elif raw_tag.startswith("VPP.Aux"):
            result.append((token_id, "VAPP"))
        elif raw_tag.startswith("VPP.Mod"):
            result.append((token_id, "VMPP"))
        elif raw_tag.startswith("SYM.Pun.Comma"):
            result.append((token_id, "$,"))
        elif raw_tag.startswith("SYM.Other.XY"):
            result.append((token_id, "XY"))
        elif raw_tag.startswith("SYM.Pun.Sent"):
            result.append((token_id, "$."))
        elif raw_tag.startswith("SYM.Paren") or raw_tag.startswith("SYM.Pun.Hyph") or raw_tag.startswith("SYM.Pun.Colon"):
            result.append((token_id, "$("))

    return result


def _convert_corenlp_tags(corenlp_map: list) -> list:
    """
    Преобразует теги CoreNLP 
    """
    result = []

    for token_id, raw_tag in corenlp_map:
        cleaned_tag = (raw_tag or "").strip()
        if not cleaned_tag:
            continue

        if cleaned_tag in DIRECT_DB_TAGS:
            result.append((token_id, cleaned_tag))
            continue

        mapped_tag = CORENLP_TREEBANK_TO_DB_TAG.get(cleaned_tag)
        if mapped_tag:
            result.append((token_id, mapped_tag))
            continue

        # неизвестные теги уводим в X, чтобы разметка не пропадала совсем
        result.append((token_id, "X"))

    return result


def _fast_map_lists(tagger_tokens: list, sentence_tokens: list):
    """
    Быстрое линейное сопоставление токенов разметчика и токенов из БД.
    """
    result = []

    filtered_sentence_tokens = [
        token for token in sentence_tokens
        if token["tokentext"] != "-EMPTY-"
    ]

    if len(tagger_tokens) != len(filtered_sentence_tokens):
        return None, 1

    for tagger_item, db_item in zip(tagger_tokens, filtered_sentence_tokens):
        tagger_token = tagger_item[0]
        raw_tag = tagger_item[1]
        db_token = db_item["tokentext"]

        if db_token == tagger_token:
            result.append((db_item["idtoken"], raw_tag))
            continue

        return None, 1

    return result, 0


def _map_lists(
    tagger_tokens: list,
    sentence_tokens: list,
    tagger_index: int,
    sentence_index: int,
    error_score: int = 0,
):
    """
    Более гибкое рекурсивное сопоставление токенов.
    """
    ret = []
    error_count = 0

    if sentence_index >= len(sentence_tokens):
        return ret, error_count + len(tagger_tokens) - tagger_index

    while tagger_index < len(tagger_tokens):
        while True:
            if sentence_index >= len(sentence_tokens):
                return ret, error_count + len(tagger_tokens) - tagger_index

            if sentence_tokens[sentence_index]["tokentext"] != "-EMPTY-":
                break

            sentence_index += 1

        db_token = sentence_tokens[sentence_index]["tokentext"]
        tagger_token = tagger_tokens[tagger_index][0]

        if db_token == tagger_token:
            part = tagger_tokens[tagger_index][1]
            ret.append((sentence_tokens[sentence_index]["idtoken"], part))
            tagger_index += 1
            sentence_index += 1

        elif (
            sentence_index + 1 < len(sentence_tokens)
            and sentence_tokens[sentence_index + 1]["tokentext"] == "."
            and sentence_tokens[sentence_index]["tokentext"] + "." == tagger_token
        ):
            part = tagger_tokens[tagger_index][1]
            ret.append((sentence_tokens[sentence_index]["idtoken"], part))
            tagger_index += 1
            sentence_index += 2

        else:
            if error_count + error_score > 10:
                return ret, error_count

            ret1, err1 = _map_lists(
                tagger_tokens,
                sentence_tokens,
                tagger_index + 1,
                sentence_index,
                error_score + 1,
            )
            ret2, err2 = _map_lists(
                tagger_tokens,
                sentence_tokens,
                tagger_index,
                sentence_index + 1,
                error_score + 1,
            )

            if err1 > err2:
                error_count += err2 + 1
                ret.extend(ret2)
            else:
                error_count += err1 + 1
                ret.extend(ret1)

            return ret, error_count

    return ret, error_count