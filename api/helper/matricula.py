import re

# Matrícula de Moçambique, formato actual (decisão do utilizador,
# 2026-10-12: só o formato actual é aceite): três letras, três algarismos
# e as duas letras da província, ex: "ABC 123 MC".
_FORMATO = re.compile(r"([A-Z]{3})[ -]?(\d{3})[ -]?([A-Z]{2})")

MENSAGEM_FORMATO = "Matrícula inválida (formato ABC 123 MC)"


def normalizar_matricula(texto):
    """Devolve a matrícula na forma única "ABC 123 MC", ou None se não for
    válida. A forma única é o que permite reconhecer a mesma matrícula
    escrita com ou sem espaços/hífenes."""
    matricula = _FORMATO.fullmatch((texto or "").strip().upper())
    return " ".join(matricula.groups()) if matricula else None
