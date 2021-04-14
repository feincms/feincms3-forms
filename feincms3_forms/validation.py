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


def concrete_descendant_models(plugin_base):
    def _sc(cls):
        for sc in cls.__subclasses__():
            yield sc
            yield from _sc(sc)

    return [
        cls
        for cls in _sc(plugin_base)
        if not cls._meta.abstract and not cls._meta.proxy
    ]


def concrete_descendant_instances(plugin_base, parent):
    return {
        cls: cls.objects.filter(parent=parent)
        for cls in concrete_descendant_models(plugin_base)
    }
