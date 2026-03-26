def get_user_rights_name(user) -> str:
    if not user or not user.is_authenticated:
        return ""

    if not hasattr(user, "idrights") or user.idrights is None:
        return ""

    return (user.idrights.rightsname or "").strip()

def has_right(user, *allowed_rights) -> bool:
    rights_name = get_user_rights_name(user)
    return rights_name in allowed_rights

def has_student_rights(user) -> bool:
    return has_right(user, "Студент")

def has_teacher_rights(user) -> bool:
    return has_right(user, "Преподаватель")

def has_researcher_rights(user) -> bool:
    return has_right(user, "Исследователь")

def has_admin_rights(user) -> bool:
    return has_right(user, "Администратор")

def has_teacher_or_student_rights(user) -> bool:
    return has_right(user, "Преподаватель", "Студент")


def has_teacher_or_admin_rights(user) -> bool:
    return has_right(user, "Преподаватель", "Администратор")


