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
#gemma4:e4b

client = Client(
    host=OLLAMA_HOST
)


def ask_ollama(question):

    if not isinstance(question, str):
        raise ValueError(
            "La question doit être une chaîne"
        )

    question = question.strip()

    if not question:
        raise ValueError(
            "La question est obligatoire"
        )

    try:
        response = client.generate(
            model=OLLAMA_MODEL,
            prompt=question,
        )

        return response.response

    except Exception as error:
        raise RuntimeError(
            "Impossible de contacter Ollama : "
            f"{error}"
        ) from error


def main():
    try:
        question = input(
            "Question pour Ollama : "
        )

        response = ask_ollama(question)

        print()
        print("Réponse Ollama :")
        print(response)

    except (
        ValueError,
        RuntimeError,
    ) as error:
        print(f"Erreur : {error}")


if __name__ == "__main__":
    main()