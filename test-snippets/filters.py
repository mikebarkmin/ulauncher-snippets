def replace_with_symbol(text: str, symbol: str) -> str:
    return symbol * len(text)


filters = {
    "replace_with_symbol": replace_with_symbol
}
