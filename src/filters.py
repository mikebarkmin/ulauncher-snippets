def camelcase(text):
    """
    >>> camelcase("A Test title")
    'aTestTitle'
    """
    words = text.split()
    first = False
    for word in words:
        if not first:
            text = word.lower()
            first = True
        elif len(word) > 1:
            text += word[:1].upper() + word[1:]
        elif len(word) == 1:
            text += word[:1].upper()
    return text


def pascalcase(text):
    """
    >>> pascalcase("A Test title")
    'ATestTitle'
    """
    text = camelcase(text)

    if len(text) > 1:
        return text[0].upper() + text[1:]
    elif len(text) == 1:
        return text[0].upper()

    return text


def snakecase(text: str):
    """
    >>> snakecase("A Test title")
    'a_test_title'
    """
    text = text.lower()
    text = text.replace(" ", "_")
    return text


def kebabcase(text: str):
    """
    >>> kebabcase("A Test title")
    'a-test-title'
    """
    return snakecase(text).replace("_", "-")


if __name__ == "__main__":
    import doctest
    doctest.testmod()
