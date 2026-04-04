import json
from collections import defaultdict

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

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


BATCH_SIZE = 100


def corpus_search(request):
    if not request.user.is_authenticated:
        base_template = "guest_base.html"
    else:
        if hasattr(request.user, "idrights"):
            if request.user.idrights.idrights == 2:
                base_template = "base.html"
            elif request.user.idrights.idrights == 1:
                base_template = "student_base.html"
            elif request.user.idrights.idrights == 4:
                base_template = "admin_base.html"
            else:
                base_template = "guest_base.html"
        else:
            base_template = "guest_base.html"

    context = {
        "base_template": base_template,
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
            ErrorTag.objects.values(
                "iderrortag", "tagtext", "tagtextabbrev", "tagtextrussian"
            ).order_by("tagtextrussian")
        ),
        "error_levels": list(
            ErrorLevel.objects.values("iderrorlevel", "errorlevelname").order_by("errorlevelname")
        ),
        "reasons": list(
            Reason.objects.values("idreason", "reasonname").order_by("reasonname")
        ),
    }
    return JsonResponse(data)


def _group_has_any_filter(group_data: dict) -> bool:
    for value in group_data.values():
        if not isinstance(value, dict):
            continue
        if value.get("value") not in [None, "", []]:
            return True
    return False


def _text_ids_by_wordform(value: str):
    return Token.objects.filter(
        tokentext__iexact=value
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

    matched_ids_subquery = get_ids_func(value)
    condition = Q(idtext__in=matched_ids_subquery)

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


def _text_matches_title(text_obj, payload: dict) -> bool:
    value = payload.get("value")
    if value in [None, "", []]:
        return True

    found = str(value).lower() in (text_obj.header or "").lower()
    if payload.get("not", False):
        return not found
    return found


def _text_matches_text_type(text_obj, payload: dict) -> bool:
    value = payload.get("value")
    if value in [None, "", []]:
        return True

    found = text_obj.idtexttype_id == value
    if payload.get("not", False):
        return not found
    return found


def _text_matches_emotion(text_obj, payload: dict) -> bool:
    value = payload.get("value")
    if value in [None, "", []]:
        return True

    found = text_obj.idemotion_id == value
    if payload.get("not", False):
        return not found
    return found


def _group_text_level_matches(text_obj, group_data: dict) -> bool:
    return (
        _text_matches_title(text_obj, group_data.get("title", {}))
        and _text_matches_text_type(text_obj, group_data.get("text_type_id", {}))
        and _text_matches_emotion(text_obj, group_data.get("emotion_id", {}))
    )


def _group_has_token_filters(group_data: dict) -> bool:
    return any(
        group_data.get(field_name, {}).get("value") not in [None, "", []]
        for field_name in ["wordform", "pos_tag_id", "error_tag_id", "error_level_id", "reason_id"]
    )


def _token_matches_wordform(token, payload: dict) -> bool:
    value = payload.get("value")
    if value in [None, "", []]:
        return True

    found = (token.tokentext or "").lower() == str(value).lower()
    if payload.get("not", False):
        return not found
    return found


def _token_matches_pos(token, payload: dict) -> bool:
    value = payload.get("value")
    if value in [None, "", []]:
        return True

    found = token.idpostag_id == value
    if payload.get("not", False):
        return not found
    return found


def _token_matches_error_tag(token_meta_item: dict, payload: dict) -> bool:
    value = payload.get("value")
    if value in [None, "", []]:
        return True

    found = value in token_meta_item["error_tag_ids"]
    if payload.get("not", False):
        return not found
    return found


def _token_matches_error_level(token_meta_item: dict, payload: dict) -> bool:
    value = payload.get("value")
    if value in [None, "", []]:
        return True

    found = value in token_meta_item["error_level_ids"]
    if payload.get("not", False):
        return not found
    return found


def _token_matches_reason(token_meta_item: dict, payload: dict) -> bool:
    value = payload.get("value")
    if value in [None, "", []]:
        return True

    found = value in token_meta_item["reason_ids"]
    if payload.get("not", False):
        return not found
    return found


def _token_matches_group(token, token_meta_item: dict, group_data: dict) -> bool:
    return (
        _token_matches_wordform(token, group_data.get("wordform", {}))
        and _token_matches_pos(token, group_data.get("pos_tag_id", {}))
        and _token_matches_error_tag(token_meta_item, group_data.get("error_tag_id", {}))
        and _token_matches_error_level(token_meta_item, group_data.get("error_level_id", {}))
        and _token_matches_reason(token_meta_item, group_data.get("reason_id", {}))
    )


def _build_highlight_flags_for_matched_token(group_data: dict) -> dict:
    flags = {
        "wordform": False,
        "pos": False,
        "error": False,
    }

    wordform_payload = group_data.get("wordform", {})
    if wordform_payload.get("value") not in [None, "", []] and not wordform_payload.get("not", False):
        flags["wordform"] = True

    pos_payload = group_data.get("pos_tag_id", {})
    if pos_payload.get("value") not in [None, "", []] and not pos_payload.get("not", False):
        flags["pos"] = True

    for field_name in ["error_tag_id", "error_level_id", "reason_id"]:
        payload = group_data.get(field_name, {})
        if payload.get("value") not in [None, "", []] and not payload.get("not", False):
            flags["error"] = True
            break

    return flags


def _merge_highlight_flags(base_flags: dict, new_flags: dict) -> dict:
    return {
        "wordform": base_flags["wordform"] or new_flags["wordform"],
        "pos": base_flags["pos"] or new_flags["pos"],
        "error": base_flags["error"] or new_flags["error"],
    }


def _wrap_token_html(token_text: str, flags: dict) -> str:
    text = token_text

    if flags["wordform"] and not flags["pos"]:
        text = f'<span class="highlight-wordform">{text}</span>'

    if flags["pos"]:
        text = f'<span class="highlight-pos">{text}</span>'

    if flags["error"]:
        text = f'<span class="highlight-error">{text}</span>'

    return text


def _render_sentence_with_highlights(tokens, token_flags_map: dict) -> str:
    rendered_parts = []

    for token in tokens:
        flags = token_flags_map.get(
            token.idtoken,
            {"wordform": False, "pos": False, "error": False},
        )
        rendered_parts.append(_wrap_token_html(token.tokentext, flags))

    return " ".join(rendered_parts)


def _iter_batches(sequence, batch_size):
    for start in range(0, len(sequence), batch_size):
        yield sequence[start:start + batch_size]


def _build_batch_runtime_cache(text_batch):
    text_ids = [text.idtext for text in text_batch]
    cache_by_text_id = {}

    for text in text_batch:
        cache_by_text_id[text.idtext] = {
            "text": text,
            "sentences": [],
            "sentence_tokens": defaultdict(list),
            "token_meta": {},
        }

    if not text_ids:
        return cache_by_text_id

    sentences = list(
        Sentence.objects.filter(idtext_id__in=text_ids)
        .select_related("idtext")
        .order_by("idtext_id", "ordernumber")
    )

    sentence_ids = [sentence.idsentence for sentence in sentences]
    sentence_to_text_id = {}

    for sentence in sentences:
        cache_by_text_id[sentence.idtext_id]["sentences"].append(sentence)
        sentence_to_text_id[sentence.idsentence] = sentence.idtext_id

    tokens = list(
        Token.objects.filter(idsentence_id__in=sentence_ids)
        .select_related("idpostag", "idsentence")
        .order_by("idsentence__idtext_id", "idsentence__ordernumber", "tokenordernumber")
    )

    token_ids = []

    for token in tokens:
        text_id = sentence_to_text_id.get(token.idsentence_id)
        if text_id is None:
            continue

        cache_by_text_id[text_id]["sentence_tokens"][token.idsentence_id].append(token)
        cache_by_text_id[text_id]["token_meta"][token.idtoken] = {
            "error_tag_ids": set(),
            "error_level_ids": set(),
            "reason_ids": set(),
        }
        token_ids.append(token.idtoken)

    if token_ids:
        error_links = list(
            ErrorToken.objects.filter(idtoken_id__in=token_ids)
            .select_related("iderror__iderrortag", "iderror__iderrorlevel", "iderror__idreason", "idtoken")
        )

        for error_link in error_links:
            token_id = error_link.idtoken_id
            sentence_id = error_link.idtoken.idsentence_id
            text_id = sentence_to_text_id.get(sentence_id)

            if text_id is None:
                continue

            token_meta = cache_by_text_id[text_id]["token_meta"].setdefault(
                token_id,
                {
                    "error_tag_ids": set(),
                    "error_level_ids": set(),
                    "reason_ids": set(),
                },
            )

            error_obj = error_link.iderror
            if not error_obj:
                continue

            if error_obj.iderrortag_id:
                token_meta["error_tag_ids"].add(error_obj.iderrortag_id)

            if error_obj.iderrorlevel_id:
                token_meta["error_level_ids"].add(error_obj.iderrorlevel_id)

            if error_obj.idreason_id:
                token_meta["reason_ids"].add(error_obj.idreason_id)

    return cache_by_text_id


def _sentence_matches_group(sentence, group_data: dict, cache: dict):
    text_obj = sentence.idtext

    if not _group_text_level_matches(text_obj, group_data):
        return False, {}

    tokens = cache["sentence_tokens"].get(sentence.idsentence, [])
    token_meta = cache["token_meta"]
    token_filters_present = _group_has_token_filters(group_data)

    if not token_filters_present:
        return True, {}

    sentence_flags = {}

    for token in tokens:
        meta_item = token_meta.get(
            token.idtoken,
            {"error_tag_ids": set(), "error_level_ids": set(), "reason_ids": set()},
        )

        if _token_matches_group(token, meta_item, group_data):
            sentence_flags[token.idtoken] = _build_highlight_flags_for_matched_token(group_data)

    if not sentence_flags:
        return False, {}

    return True, sentence_flags


def _find_group_matches_in_text(sentences, group_data: dict, cache: dict):
    matches = []

    for idx, sentence in enumerate(sentences):
        matched, token_flags_map = _sentence_matches_group(sentence, group_data, cache)
        if matched:
            matches.append({
                "index": idx,
                "sentence": sentence,
                "token_flags_map": token_flags_map,
            })

    return matches


def _merge_sentence_match_items(existing_item: dict, new_item: dict) -> dict:
    merged_flags = dict(existing_item["token_flags_map"])

    for token_id, flags in new_item["token_flags_map"].items():
        if token_id in merged_flags:
            merged_flags[token_id] = _merge_highlight_flags(merged_flags[token_id], flags)
        else:
            merged_flags[token_id] = flags

    return {
        "index": existing_item["index"],
        "sentence": existing_item["sentence"],
        "token_flags_map": merged_flags,
    }


def _combine_group_matches(groups_matches, operators):
    if not groups_matches:
        return []

    current_map = {item["index"]: item for item in groups_matches[0]}

    for i in range(1, len(groups_matches)):
        op = operators[i - 1] if i - 1 < len(operators) else "AND"
        next_map = {item["index"]: item for item in groups_matches[i]}

        if op == "OR":
            combined = dict(current_map)

            for idx, item in next_map.items():
                if idx in combined:
                    combined[idx] = _merge_sentence_match_items(combined[idx], item)
                else:
                    combined[idx] = item

            current_map = combined
        else:
            if current_map and next_map:
                combined = dict(current_map)

                for idx, item in next_map.items():
                    if idx in combined:
                        combined[idx] = _merge_sentence_match_items(combined[idx], item)
                    else:
                        combined[idx] = item

                current_map = combined
            else:
                current_map = {}

    return [current_map[idx] for idx in sorted(current_map.keys())]

def _groups_have_only_text_level_filters(groups: list[dict]) -> bool:
    token_fields = ["wordform", "pos_tag_id", "error_tag_id", "error_level_id", "reason_id"]
    text_fields = ["title", "text_type_id", "emotion_id"]

    has_any_text_filter = False

    for group in groups:
        for field in token_fields:
            if group.get(field, {}).get("value") not in [None, "", []]:
                return False

        for field in text_fields:
            if group.get(field, {}).get("value") not in [None, "", []]:
                has_any_text_filter = True

    return has_any_text_filter

def _build_matching_sentence_groups(sentences, groups, operators, cache: dict):
    if not sentences:
        return []

    if _groups_have_only_text_level_filters(groups):
        first_sentence = sentences[0]
        next_sentence = sentences[1] if len(sentences) > 1 else None

        return [{
            "current": {
                "text": first_sentence.sentensetext or "",
                "highlighted_text": first_sentence.sentensetext or "",
                "order": first_sentence.ordernumber,
            },
            "previous": None,
            "next": {
                "text": next_sentence.sentensetext,
                "order": next_sentence.ordernumber,
            } if next_sentence else None,
        }]

    groups_matches = []

    for group in groups:
        group_matches = _find_group_matches_in_text(sentences, group, cache)
        groups_matches.append(group_matches)

    combined_matches = _combine_group_matches(groups_matches, operators)

    if not combined_matches:
        return []

    matched_indexes = [item["index"] for item in combined_matches]
    grouped_ranges = []

    start = matched_indexes[0]
    end = matched_indexes[0]

    for idx in matched_indexes[1:]:
        if idx == end + 1:
            end = idx
        else:
            grouped_ranges.append((start, end))
            start = idx
            end = idx

    grouped_ranges.append((start, end))

    combined_map = {item["index"]: item for item in combined_matches}
    result = []

    for start, end in grouped_ranges:
        prev_sentence = sentences[start - 1] if start > 0 else None
        next_sentence = sentences[end + 1] if end + 1 < len(sentences) else None

        current_parts = []

        for i in range(start, end + 1):
            sentence = sentences[i]
            match_item = combined_map.get(i)
            tokens = cache["sentence_tokens"].get(sentence.idsentence, [])

            if match_item:
                highlighted_html = _render_sentence_with_highlights(tokens, match_item["token_flags_map"])
            else:
                highlighted_html = sentence.sentensetext or ""

            current_parts.append(highlighted_html)

        current_text_joined = "<br>".join(current_parts)

        result.append({
            "current": {
                "text": " ".join(
                    [(sentences[i].sentensetext or "") for i in range(start, end + 1)]
                ),
                "highlighted_text": current_text_joined,
                "order": sentences[start].ordernumber,
            },
            "previous": {
                "text": prev_sentence.sentensetext,
                "order": prev_sentence.ordernumber,
            } if prev_sentence else None,
            "next": {
                "text": next_sentence.sentensetext,
                "order": next_sentence.ordernumber,
            } if next_sentence else None,
        })

    return result


@require_POST
def corpus_search_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Некорректный JSON")

    groups = payload.get("groups", [])
    operators = payload.get("operators", [])
    page = payload.get("page", 1)
    page_size = payload.get("page_size", 10)

    if not isinstance(groups, list):
        return JsonResponse({"results": [], "count": 0})

    groups = [group for group in groups if _group_has_any_filter(group)]

    if not groups:
        return JsonResponse({
            "results": [],
            "count": 0,
            "is_teacher": False,
            "page_obj": {
                "number": 1,
                "num_pages": 1,
                "has_previous": False,
                "has_next": False,
                "previous_page_number": None,
                "next_page_number": None,
            },
        })

    group_queries = [_build_group_q(group) for group in groups]
    final_q = group_queries[0]

    for i in range(1, len(group_queries)):
        operator_value = operators[i - 1] if i - 1 < len(operators) else "AND"

        if operator_value == "OR":
            final_q = final_q | group_queries[i]
        else:
            final_q = final_q & group_queries[i]

    texts = list(
        Text.objects.select_related("idtexttype", "idemotion")
        .filter(final_q)
        .distinct()
        .order_by("-createdate", "-idtext")
    )

    filtered_results = []

    for text_batch in _iter_batches(texts, BATCH_SIZE):
        batch_cache = _build_batch_runtime_cache(text_batch)

        for text in text_batch:
            cache = batch_cache.get(text.idtext)
            if not cache:
                continue

            sentences = cache["sentences"]
            if not sentences:
                continue

            matching_sentences = _build_matching_sentence_groups(
                sentences=sentences,
                groups=groups,
                operators=operators,
                cache=cache,
            )

            if not matching_sentences:
                continue

            filtered_results.append({
                "id": text.idtext,
                "header": text.header,
                "createdate": text.createdate.strftime("%d.%m.%Y") if text.createdate else "",
                "text_type": text.idtexttype.texttypename if text.idtexttype else "Не указано",
                "emotion": text.idemotion.emotionname if text.idemotion else "Не указано",
                "matching_sentences": matching_sentences,
            })

    paginator = Paginator(filtered_results, page_size)

    try:
        paginated_results = paginator.page(page)
    except PageNotAnInteger:
        paginated_results = paginator.page(1)
    except EmptyPage:
        safe_page = paginator.num_pages if paginator.num_pages > 0 else 1
        paginated_results = paginator.page(safe_page)

    is_teacher = False
    if request.user.is_authenticated and hasattr(request.user, "idrights"):
        if request.user.idrights.idrights == 2:
            is_teacher = True

    return JsonResponse({
        "is_teacher": is_teacher,
        "results": list(paginated_results),
        "count": paginator.count,
        "page_obj": {
            "number": paginated_results.number,
            "num_pages": paginator.num_pages,
            "has_previous": paginated_results.has_previous(),
            "has_next": paginated_results.has_next(),
            "previous_page_number": paginated_results.previous_page_number() if paginated_results.has_previous() else None,
            "next_page_number": paginated_results.next_page_number() if paginated_results.has_next() else None,
        },
    })


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