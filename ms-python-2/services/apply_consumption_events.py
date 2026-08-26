def is_event_active(
    event,
    timestamp
):
    return (
        event["start"]
        <= timestamp
        < event["end"]
    )


def calculate_event_delta_mw(
    reference_consumption_mw,
    event
):
    if "delta_mw" in event:
        return float(
            event["delta_mw"]
        )

    return (
        float(reference_consumption_mw)
        * float(event["delta_percent"])
        / 100
    )


def apply_consumption_events(
    regional_consumption,
    timestamp,
    events
):
    modified_consumption = (
        regional_consumption.copy()
    )

    regional_deltas = {
        region_id: 0.0
        for region_id in regional_consumption
    }

    active_events = []

    for event in events:
        if not is_event_active(
            event,
            timestamp
        ):
            continue

        region_id = event[
            "region_id"
        ]

        if region_id not in regional_consumption:
            raise ValueError(
                "Région inconnue dans un événement : "
                f"{region_id}"
            )

        reference_consumption_mw = (
            regional_consumption[
                region_id
            ]
        )

        delta_mw = (
            calculate_event_delta_mw(
                reference_consumption_mw,
                event,
            )
        )

        regional_deltas[
            region_id
        ] += delta_mw

        active_event = event.copy()

        active_event[
            "calculated_delta_mw"
        ] = round(
            delta_mw,
            3
        )

        active_events.append(
            active_event
        )

    for (
        region_id,
        delta_mw
    ) in regional_deltas.items():
        modified_consumption[
            region_id
        ] = max(
            0.0,
            regional_consumption[
                region_id
            ] + delta_mw
        )

    total_delta_mw = sum(
        modified_consumption[
            region_id
        ]
        - regional_consumption[
            region_id
        ]
        for region_id in regional_consumption
    )

    return {
        "regional_consumption_mw":
            modified_consumption,

        "regional_delta_mw":
            regional_deltas,

        "total_delta_mw":
            total_delta_mw,

        "active_events":
            active_events,
    }