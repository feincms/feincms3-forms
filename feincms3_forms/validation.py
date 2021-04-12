from django.contrib.messages import api, constants


class Message:
    def __init__(self, level, message):
        self.level = level
        self.message = message

    def __str__(self):
        return str(self.message)

    def add_to(self, request):
        api.add_message(request, self.level, self.message)


class Warning(Message):
    def __init__(self, *args, **kwargs):
        super().__init__(constants.WARNING, *args, **kwargs)


class Error(Message):
    def __init__(self, *args, **kwargs):
        super().__init__(constants.ERROR, *args, **kwargs)
