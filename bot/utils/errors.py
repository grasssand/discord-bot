class SetuCogError(Exception):
    pass


class GenshinCogError(Exception):
    pass


class GenshinNoCharacterNameError(GenshinCogError):
    pass


class GenshinTooMuchCharacterError(GenshinCogError):
    pass
