func TestPlans_UpdateRejectsUnsupportedField(t *testing.T) {
	router, _ := testRouter(t)
	code, raw := postJSON(t, router, "/api/v1/plans", map[string]interface{}{
		"title": "Unsupported Field Plan", "start_time": "09:00", "end_time": "17:00",
		"repeat_days": "1,2,3,4,5", "skip_holidays": false, "media_url": "file:///x",
		"is_active": false, "play_mode": "SEQUENTIAL",
	})
	if code != 200 {
		t.Fatalf("create plan: code=%d body=%s", code, raw)
	}
	planID, _ := parseJSON(t, raw)["id"].(string)
	if planID == "" {
		t.Fatal("missing plan id")
	}

	code, raw = putJSON(t, router, "/api/v1/plans/"+planID, map[string]interface{}{"unknown_field": "x"})
	if code != 400 {
		t.Fatalf("expected 400 for unsupported update field, got %d body=%s", code, raw)
	}
}

func TestPlans_UpdateRejectsLastTriggeredDateMutation(t *testing.T) {
	router, _ := testRouter(t)
	code, raw := postJSON(t, router, "/api/v1/plans", map[string]interface{}{
		"title": "Internal Field Plan", "start_time": "09:00", "end_time": "17:00",
		"repeat_days": "1,2,3,4,5", "skip_holidays": false, "media_url": "file:///x",
		"is_active": false, "play_mode": "SEQUENTIAL",
	})
	if code != 200 {
		t.Fatalf("create plan: code=%d body=%s", code, raw)
	}
	planID, _ := parseJSON(t, raw)["id"].(string)
	if planID == "" {
		t.Fatal("missing plan id")
	}

	code, raw = putJSON(t, router, "/api/v1/plans/"+planID, map[string]interface{}{"last_triggered_date": "2026-02-01"})
	if code != 400 {
		t.Fatalf("expected 400 when mutating last_triggered_date, got %d body=%s", code, raw)
	}
}
