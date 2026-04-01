import json
from functools import reduce
from operator import and_, or_

from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

import re

from core_app.models import (
    Sentence,
    Text,
    TextType,
    Emotion,
    Token,
    ErrorToken,
    PosTag,
    ErrorTag,
    ErrorLevel,
    Reason,
)

def corpus_search(request):
    if not request.user.is_authenticated:
        base_template = 'guest_base.html'
    else:
        if hasattr(request.user, 'idrights'):
            if request.user.idrights.idrights == 2:
                base_template = 'base.html'
            elif request.user.idrights.idrights == 1:
                base_template = 'student_base.html'
            elif request.user.idrights.idrights == 4:
                base_template = 'admin_base.html'
            else:
                base_template = 'guest_base.html'
        else:
            base_template = 'guest_base.html'
    context = {
        'base_template': base_template
    }
    return render(request, "corpus_search.html", context)


@require_GET
def corpus_filters_api(request):
    data = {
        "text_types": list(
            TextType.objects.values("idtexttype", "texttypename").order_by("texttypename")
        ),
        "emotions": list(
            Emotion.objects.values("idemotion", "emotionname").order_by("emotionname")
        ),
        "pos_tags": list(
            PosTag.objects.values("idpostag", "tagtext", "tagtextabbrev").order_by("tagtext")
        ),
        "error_tags": list(
            ErrorTag.objects.values("iderrortag", "tagtext", "tagtextabbrev", "tagtextrussian").order_by("tagtextrussian")
        ),
        "error_levels": list(
            ErrorLevel.objects.values("iderrorlevel", "errorlevelname").order_by("errorlevelname")
        ),
        "reasons": list(
            Reason.objects.values("idreason", "reasonname").order_by("reasonname")
        ),
    }
    return JsonResponse(data)


def _text_ids_by_wordform(value: str):
    return Token.objects.filter(
        tokentext__icontains=value
    ).values_list("idsentence__idtext_id", flat=True).distinct()


def _text_ids_by_pos_tag(pos_tag_id: int):
    return Token.objects.filter(
        idpostag_id=pos_tag_id
    ).values_list("idsentence__idtext_id", flat=True).distinct()


def _text_ids_by_error_tag(error_tag_id: int):
    return ErrorToken.objects.filter(
        iderror__iderrortag_id=error_tag_id
    ).values_list("idtoken__idsentence__idtext_id", flat=True).distinct()


def _text_ids_by_error_level(error_level_id: int):
    return ErrorToken.objects.filter(
        iderror__iderrorlevel_id=error_level_id
    ).values_list("idtoken__idsentence__idtext_id", flat=True).distinct()


def _text_ids_by_reason(reason_id: int):
    return ErrorToken.objects.filter(
        iderror__idreason_id=reason_id
    ).values_list("idtoken__idsentence__idtext_id", flat=True).distinct()


def _text_ids_by_title(value: str):
    return Text.objects.filter(
        header__icontains=value
    ).values_list("idtext", flat=True).distinct()


def _text_ids_by_text_type(text_type_id: int):
    return Text.objects.filter(
        idtexttype_id=text_type_id
    ).values_list("idtext", flat=True).distinct()


def _text_ids_by_emotion(emotion_id: int):
    return Text.objects.filter(
        idemotion_id=emotion_id
    ).values_list("idtext", flat=True).distinct()


def _apply_one_filter(current_q: Q, field_payload: dict, get_ids_func) -> Q:
    if not field_payload:
        return current_q

    value = field_payload.get("value")
    is_not = field_payload.get("not", False)

    if value in [None, "", []]:
        return current_q

    matched_ids = list(get_ids_func(value))
    condition = Q(idtext__in=matched_ids)

    if is_not:
        condition = ~condition

    return current_q & condition


def _build_group_q(group_data: dict) -> Q:
    group_q = Q()

    group_q = _apply_one_filter(group_q, group_data.get("wordform"), _text_ids_by_wordform)
    group_q = _apply_one_filter(group_q, group_data.get("pos_tag_id"), _text_ids_by_pos_tag)
    group_q = _apply_one_filter(group_q, group_data.get("error_tag_id"), _text_ids_by_error_tag)
    group_q = _apply_one_filter(group_q, group_data.get("error_level_id"), _text_ids_by_error_level)
    group_q = _apply_one_filter(group_q, group_data.get("reason_id"), _text_ids_by_reason)
    group_q = _apply_one_filter(group_q, group_data.get("title"), _text_ids_by_title)
    group_q = _apply_one_filter(group_q, group_data.get("text_type_id"), _text_ids_by_text_type)
    group_q = _apply_one_filter(group_q, group_data.get("emotion_id"), _text_ids_by_emotion)

    return group_q


@require_POST
def corpus_search_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Некорректный JSON")

    groups = payload.get("groups", [])
    operators = payload.get("operators", [])
    
    # Пагинация
    page = payload.get("page", 1)
    page_size = payload.get("page_size", 10)

    if not isinstance(groups, list) or not groups:
        return JsonResponse({"results": [], "count": 0})

    group_queries = [_build_group_q(group) for group in groups]

    final_q = group_queries[0]

    for i in range(1, len(group_queries)):
        operator_value = operators[i - 1] if i - 1 < len(operators) else "AND"

        if operator_value == "OR":
            final_q = final_q | group_queries[i]
        else:
            final_q = final_q & group_queries[i]

    texts = (
        Text.objects.select_related("idtexttype", "idemotion")
        .filter(final_q)
        .distinct()
        .order_by("-createdate", "-idtext")
    )

    # Условия для поиска по словоформам, которые будем использовать для подсветки в результатах
    wordform_conditions = []
    for group in groups:
        wordform = group.get("wordform", {})
        if wordform.get("value"):
            wordform_conditions.append({
                "value": wordform["value"].lower(),
                "not": wordform.get("not", False)
            })
    # 

    paginator = Paginator(texts, page_size)
    try:
        paginated_texts = paginator.page(page)
    except PageNotAnInteger:
        paginated_texts = paginator.page(1)
    except EmptyPage:
        paginated_texts = paginator.page(paginator.num_pages)

    results = []
    # for text in texts:
    for text in paginated_texts:
        sentences = list(Sentence.objects.filter(idtext=text).order_by("ordernumber"))
        
        matching_sentences = []
        
        # Проверяем, есть ли в запросе словоформы
        has_wordforms = any(group.get("wordform", {}).get("value") for group in groups)
        
        if has_wordforms:
            # Ищем предложения, соответствующие условиям по словоформам
            for idx, sentence in enumerate(sentences):
                matches, matched_word = _sentence_matches_wordform_conditions(sentence, groups, operators)
                
                if matches:
                    # Получаем соседние предложения
                    prev_sentence = sentences[idx - 1] if idx > 0 else None
                    next_sentence = sentences[idx + 1] if idx + 1 < len(sentences) else None
                    
                    # Подсветка найденного слова
                    highlighted_text = sentence.sentensetext
                    if matched_word:
                        highlighted_text = _highlight_word(sentence.sentensetext, matched_word)
                        # import re
                        # pattern = re.compile(re.escape(matched_word), re.IGNORECASE)
                        # highlighted_text = pattern.sub(
                        #     lambda m: f'<mark class="highlight">{m.group(0)}</mark>',
                        #     sentence.sentensetext
                        # )
                    
                    matching_sentences.append({
                        "current": {
                            "text": sentence.sentensetext,
                            "highlighted_text": highlighted_text,
                            "order": sentence.ordernumber
                        },
                        "previous": {
                            "text": prev_sentence.sentensetext if prev_sentence else None,
                            "order": prev_sentence.ordernumber if prev_sentence else None
                        } if prev_sentence else None,
                        "next": {
                            "text": next_sentence.sentensetext if next_sentence else None,
                            "order": next_sentence.ordernumber if next_sentence else None
                        } if next_sentence else None,
                        "matched_word": matched_word
                    })
        else:
            # Если нет поиска по словоформам, показываем первое предложение как пример
            first_sentence = sentences[0] if sentences else None
            if first_sentence:
                matching_sentences.append({
                    "current": {
                        "text": first_sentence.sentensetext,
                        "highlighted_text": first_sentence.sentensetext,
                        "order": first_sentence.ordernumber
                    },
                    "previous": None,
                    "next": None
                })

        results.append({
            "id": text.idtext,
            "header": text.header,
            "createdate": text.createdate.strftime("%d.%m.%Y") if text.createdate else "",
            "text_type": text.idtexttype.texttypename if text.idtexttype else "Не указано",
            "emotion": text.idemotion.emotionname if text.idemotion else "Не указано",
            "matching_sentences": matching_sentences
        })


        # results.append({
        #     "id": text.idtext,
        #     "header": text.header,
        #     "createdate": text.createdate.strftime("%d.%m.%Y") if text.createdate else "",
        #     "text_type": text.idtexttype.texttypename if text.idtexttype else "Не указано",
        #     "emotion": text.idemotion.emotionname if text.idemotion else "Не указано",
        # })

    is_teacher = False
    if request.user.is_authenticated:
        if hasattr(request.user, 'idrights'):
            if request.user.idrights.idrights == 2:
                is_teacher = True

    return JsonResponse({
        # "count": len(results),
        "is_teacher": is_teacher,
        "results": results,
        "count": paginator.count,
        "page_obj": {
            "number": paginated_texts.number,
            "num_pages": paginator.num_pages,
            "has_previous": paginated_texts.has_previous(),
            "has_next": paginated_texts.has_next(),
            "previous_page_number": paginated_texts.previous_page_number() if paginated_texts.has_previous() else None,
            "next_page_number": paginated_texts.next_page_number() if paginated_texts.has_next() else None,
        }
    })

def _highlight_word(text, word):
    """Подсвечивает целое слово в тексте"""
    if not word:
        return text
    
    # регулярное выражение для поиска целого слова
    # re.IGNORECASE - игнорируем регистр
    # \b - граница слова
    pattern = r'\b(' + re.escape(word) + r')\b'
    
    def replace_func(match):
        return f'<mark class="highlight">{match.group(1)}</mark>'
    
    highlighted = re.sub(pattern, replace_func, text, flags=re.IGNORECASE)
    return highlighted

def _sentence_matches_wordform_conditions(sentence, groups, operators):
    """Проверяет, соответствует ли предложение условиям по словоформам с учетом операторов между блоками"""
    sentence_lower = sentence.sentensetext.lower()
    block_results = []
    
    for group in groups:
        wordform = group.get("wordform", {})
        if not wordform.get("value"):
            # Если в блоке нет словоформы, считаем что блок выполнен (не влияет)
            block_results.append(True)
            continue

        search_word = wordform["value"].lower()
        is_not = wordform.get("not", False)

        pattern = r'\b' + re.escape(search_word) + r'\b'
        found = bool(re.search(pattern, sentence_lower))
        # found = search_word in sentence_lower
        if is_not:
            found = not found
        
        block_results.append(found)
    
    # Применяем операторы между блоками
    if not block_results:
        return False, None
    
    # Первый блок всегда учитываем
    result = block_results[0]
    matched_word = None
    
    # Применяем операторы
    for i, op in enumerate(operators):
        next_result = block_results[i + 1] if i + 1 < len(block_results) else False
        
        if op == "AND":
            result = result and next_result
        elif op == "OR":
            result = result or next_result
    
    # Если результат True, находим слово для подсветки (первое попавшееся)
    if result:
        for group in groups:
            wordform = group.get("wordform", {})
            if wordform.get("value") and not wordform.get("not", False):
                if wordform["value"].lower() in sentence_lower:
                    matched_word = wordform["value"]
                    break
    
    return result, matched_word


@require_GET
def corpus_text_detail(request, text_id):
    text = get_object_or_404(
        Text.objects.select_related("idemotion"),
        idtext=text_id
    )

    sentences = text.sentence_set.all().order_by("ordernumber")
    sentence_data = []

    selected_markup = request.GET.get("markup", "tagtext")

    for sentence in sentences:
        tokens = Token.objects.filter(idsentence=sentence).select_related("idpostag")

        tokens_data = []
        for token in tokens:
            pos_tag = None
            pos_tag_russian = None
            pos_tag_abbrev = None
            pos_tag_color = None

            if token.idpostag:
                pos_tag = token.idpostag.tagtext
                pos_tag_russian = token.idpostag.tagtextrussian
                pos_tag_abbrev = token.idpostag.tagtextabbrev
                pos_tag_color = token.idpostag.tagcolor

            error_tokens = token.errortoken_set.select_related(
                "iderror__iderrortag",
                "iderror__iderrorlevel",
                "iderror__idreason"
            ).all()

            errors_list = []
            for error_token in error_tokens:
                error = error_token.iderror
                if error and error.iderrortag:
                    errors_list.append(
                        {
                            "error_tag": error.iderrortag.tagtext,
                            "error_tag_russian": error.iderrortag.tagtextrussian,
                            "error_tag_abbrev": error.iderrortag.tagtextabbrev,
                            "error_color": error.iderrortag.tagcolor,
                            "error_level": error.iderrorlevel.errorlevelname
                            if error.iderrorlevel
                            else "Не указано",
                            "error_correct": error.correct
                            if error.correct
                            else "Не указано",
                            "error_comment": error.comment
                            if error.comment
                            else "Не указано",
                            "all_errors": errors_list,
                            "error_reason": error.idreason.reasonname if error.idreason else "Не указано",
                        }
                    )

            main_error = errors_list[0] if errors_list else {}

            tokens_data.append(
                {
                    "token": token.tokentext,
                    "pos_tag": pos_tag,
                    "pos_tag_russian": pos_tag_russian,
                    "pos_tag_abbrev": pos_tag_abbrev,
                    "pos_tag_color": pos_tag_color,
                    "error_tag": main_error.get("error_tag"),
                    "error_tag_russian": main_error.get("error_tag_russian"),
                    "error_tag_abbrev": main_error.get("error_tag_abbrev"),
                    "error_color": main_error.get("error_color"),
                    "error_level": main_error.get("error_level"),
                    "error_correct": main_error.get("error_correct"),
                    "error_comment": main_error.get("error_comment"),
                    "all_errors": errors_list,
                    "token_order_number": token.tokenordernumber,
                    "error_reason": main_error.get("error_reason"),
                }
            )

        sentence_data.append(
            {
                "sentence": sentence,
                "tokens": tokens_data,
            }
        )

    context = {
        "text": text,
        "sentence_data": sentence_data,
        "selected_markup": selected_markup,
        "emotion": text.idemotion.emotionname if text.idemotion else "Не указано",
        "pact_language_name": "Deutsch",
    }

    return render(request, "corpus_text_detail.html", context)