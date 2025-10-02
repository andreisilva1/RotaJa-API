import re


def limpar_resposta(texto: str):
    return re.sub(r"^```json\s*|\s*```$", "", texto, flags=re.MULTILINE)


def formatar_numero(texto: str):
    texto = texto.replace(".", "&")
    texto = texto.replace(",", ".")
    texto = texto.replace("&", ",")
    return texto


def comprimir_pontos_da_rota(pontos, max_ceps: int = 30):
    n = len(pontos)
    if n == 0:
        return []
    if n <= max_ceps:
        return pontos.copy()

    k = max_ceps
    step = (n - 1) / (k - 1)
    indices = []
    for i in range(k):
        idx = int(round(i * step))
        if idx < 0:
            idx = 0
        elif idx > n - 1:
            idx = n - 1
        indices.append(idx)

    seen = set()
    unique_indices = []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            unique_indices.append(idx)
    if unique_indices[0] != 0:
        unique_indices.insert(0, 0)
    if unique_indices[-1] != n - 1:
        unique_indices.append(n - 1)

    filtrado = [pontos[i] for i in unique_indices]
    return filtrado
