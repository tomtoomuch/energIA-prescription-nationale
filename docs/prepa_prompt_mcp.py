@mcp.prompt()
def prompt_demande_repartition(
    question: str, 
    ton: str = "professionnel", 
    inclure_emojis: bool = False
) -> str:
    """
    Génère un prompt structuré pour interroger notre moteur prescriptif.

    Args:
        question: La question à laquelle répondre.
        ton: Le ton à adopter (ex: créatif, corporate, amical,professionnel).
        inclure_emojis: Indique si l'IA doit ajouter des émojis visuels.
    """
    # Construction du texte du prompt
    emoji_instruction = "Utilise des émojis pertinents pour illustrer le texte." if inclure_emojis else "N'utilise aucun émoji."
    
    return f""" Tu es un spécialiste des réseaux de transport d'électricité. 
    
    Rédige une réponse pertinente et construite avec les données qui te sont fournies par l'API pour répondre à la question{question}
    sur le thème suivant : "{theme}".
    
    Contraintes strictes à respecter :
    - Ton à adopter : {ton}
    - Style visuel : {emoji_instruction}
    - Structure : Une introduction accrocheuse, 3 points clés, et un appel à l'action clair.
    """