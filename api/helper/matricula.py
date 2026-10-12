import re

# Matrícula de Moçambique, formato actual (decisão do utilizador,
# 2026-10-12: só o formato actual é aceite): três letras, três algarismos
# e a sigla da província do primeiro registo, ex: "ABC 123 MC".
_FORMATO = re.compile(r"([A-Z]{3})[ -]?(\d{3})[ -]?([A-Z]{2})")

# Siglas das províncias nas matrículas desde 2011. Cabo Delgado aparece
# como "CA" na maioria das fontes e como "CD" noutra: aceitam-se as duas,
# para nunca recusar uma matrícula verdadeira.
PROVINCIAS = {
    "MC": "Maputo Cidade",
    "MP": "Maputo Província",
    "GZ": "Gaza",
    "IB": "Inhambane",
    "SF": "Sofala",
    "MN": "Manica",
    "TT": "Tete",
    "ZB": "Zambézia",
    "NP": "Nampula",
    "NS": "Niassa",
    "CA": "Cabo Delgado",
    "CD": "Cabo Delgado",
}

MENSAGEM_FORMATO = "Matrícula inválida (formato ABC 123 MC)"


def validar_matricula(texto):
    """Devolve (matrícula, None) na forma única "ABC 123 MC", ou
    (None, mensagem de erro). A forma única é o que permite reconhecer a
    mesma matrícula escrita com ou sem espaços/hífenes."""
    partes = _FORMATO.fullmatch((texto or "").strip().upper())
    if not partes:
        return None, MENSAGEM_FORMATO

    sigla = partes.group(3)
    if sigla not in PROVINCIAS:
        return None, (
            f"Matrícula inválida: \"{sigla}\" não é uma sigla de província. "
            f"Siglas válidas: {', '.join(PROVINCIAS)}."
        )

    return " ".join(partes.groups()), None
