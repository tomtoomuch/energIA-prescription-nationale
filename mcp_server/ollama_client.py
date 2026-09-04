import os

from ollama import Client


OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://llm:11434",
)

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "gemma4:e4b",
)


client = Client(
    host=OLLAMA_HOST,
)


def ask_ollama(prompt):
    """
    Envoie un prompt à Gemma 4 et retourne son texte.
    """
    if not isinstance(prompt, str):
        raise ValueError(
            "Le prompt doit être une chaîne"
        )

    prompt = prompt.strip()

    if not prompt:
        raise ValueError(
            "Le prompt est obligatoire"
        )

    try:
        response = client.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            stream=False,
        )

    except Exception as error:
        raise RuntimeError(
            "Impossible de contacter Ollama : "
            f"{error}"
        ) from error

    answer = response.response

    if not isinstance(answer, str):
        raise RuntimeError(
            "Ollama a retourné une réponse invalide"
        )

    answer = answer.strip()

    if not answer:
        raise RuntimeError(
            "Ollama a retourné une réponse vide"
        )

    return answer


def main():
    question = input(
        "Question pour Gemma 4 : "
    )

    try:
        answer = ask_ollama(question)

        print()
        print("Réponse Gemma 4 :")
        print(answer)

    except (
        ValueError,
        RuntimeError,
    ) as error:
        print(
            f"Erreur : {error}"
        )


if __name__ == "__main__":
    main()