# Vérifier que l'évènement est actif
def is_event_active(
        event,
        timestamp
):
    return (
        event["start"]
        <= timestamp
        < event["end"]
    )