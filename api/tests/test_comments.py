from app.services.comments import _align_draft


def test_align_fills_blank_off_campaign_and_city() -> None:
    snapshot = {
        "campaigns": [
            {
                "id": 1,
                "name": "[TA] BANTER",
                "status": "off",
                "has_cities": False,
                "spend": "£0.00",
                "clicks": 0,
                "tickets": 0,
                "locations": [],
            },
            {
                "id": 2,
                "name": "[TA] ON THE ROAD",
                "status": "live",
                "has_cities": True,
                "spend": "£4,425.00",
                "clicks": 10,
                "tickets": 100,
                "locations": [
                    {"id": 9, "name": "Manchester"},
                    {"id": 10, "name": "Leeds"},
                ],
            },
        ]
    }
    drafted = {
        "campaigns": [
            {"id": 2, "note": "Tour still live.", "performance_summary": "Volume up.", "next_steps": "Hold Leeds."}
        ],
        "locations": [{"id": 10, "note": "Leeds is converting."}],
    }
    result = _align_draft(snapshot, drafted)
    banter = next(row for row in result["campaigns"] if row["id"] == 1)
    assert banter["note"]
    assert banter["performance_summary"]
    assert banter["next_steps"]
    road = next(row for row in result["campaigns"] if row["id"] == 2)
    assert road["performance_summary"] == "Volume up."
    manchester = next(row for row in result["locations"] if row["id"] == 9)
    assert manchester["note"]
    leeds = next(row for row in result["locations"] if row["id"] == 10)
    assert leeds["note"] == "Leeds is converting."
