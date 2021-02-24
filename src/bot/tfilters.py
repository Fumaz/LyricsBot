from pyrogram import filters


def action(action: str):
    return filters.create(lambda _, __, u: u.user.action == action)


def action_startswith(action: str):
    return filters.create(lambda _, __, u: u.user.action.startswith(action))


def admin():
    return filters.create(lambda _, __, u: u.user.is_admin)
