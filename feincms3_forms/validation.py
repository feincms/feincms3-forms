from collections import Counter

from django.contrib.messages import constants
from django.utils.translation import gettext as _


class Message:
    def __init__(self, level, message):
        self.level = level
        self.message = message

    def __str__(self):
        return str(self.message)

    def __repr__(self):
        return f"<{self.__class__.__name__}: message={self.message!r}>"

    def __eq__(self, other):
        return (
            isinstance(other, self.__class__)
            and self.level == other.level
            and self.message == other.message
        )


class Warning(Message):
    def __init__(self, *args, **kwargs):
        super().__init__(constants.WARNING, *args, **kwargs)


class Error(Message):
    def __init__(self, *args, **kwargs):
        super().__init__(constants.ERROR, *args, **kwargs)


def validate_uniqueness(fields):
    counts = Counter(field[0] for field in fields)
    if repeated := [pair for pair in counts.items() if pair[1] > 1]:
        return [
            Warning(
                _("Fields exist more than once: %s")
                % ", ".join(f"{name} ({count})" for name, count in sorted(repeated))
            )
        ]
    return []


def validate_required_fields(fields, required):
    if missing := set(required) - {field[0] for field in fields}:
        return [
            Error(_("Required fields are missing: %s") % ", ".join(sorted(missing)))
        ]
    return []


def validate_types(field_types, types):
    errors = []
    for field, type in types.items():
        if field not in field_types:
            errors.append(
                Warning(
                    _("Field {field} with expected type {type} doesn't exist").format(
                        field=field, type=type
                    )
                )
            )
        elif field_types[field] != type:
            errors.append(
                Error(
                    _("Field {field} doesn't have expected type {type}").format(
                        field=field, type=type
                    )
                )
            )
    return errors
