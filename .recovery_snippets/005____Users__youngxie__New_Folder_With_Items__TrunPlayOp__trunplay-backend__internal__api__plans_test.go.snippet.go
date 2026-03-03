func TestPlans_UpdateRejectsInvalidBooleanFields(t *testing.T) {
	router, _ := testRouter(t)
	code, raw := postJSON(t, router, "/api/v1/plans", map[string]interface{}{
		"title": "Bool Type Plan", "start_time": "09:00", "end_time": "17:00",
		"repeat_days": "1,2,3,4,5", "skip_holidays": false, "media_url": "file:///x",
		"is_active": false, "play_mode": "SEQUENTIAL",
	})
	if code != 200 {
		t.Fatalf("create: code=%d body=%s", code, raw)
	}
	planID, _ := parseJSON(t, raw)["id"].(string)
	if planID == "" {
		t.Fatal("missing plan id")
	}

	code, raw = putJSON(t, router, "/api/v1/plans/"+planID, map[string]interface{}{"is_active": "true"})
	if code != 400 {
		t.Fatalf("expected 400 for non-boolean is_active, got %d body=%s", code, raw)
	}
	code, raw = putJSON(t, router, "/api/v1/plans/"+planID, map[string]interface{}{"skip_holidays": 1})
	if code != 400 {
		t.Fatalf("expected 400 for non-boolean skip_holidays, got %d body=%s", code, raw)
	}
}

func TestPlans_UpdateRejectsInvalidMediaURL(t *testing.T) {
	router, _ := testRouter(t)
	code, raw := postJSON(t, router, "/api/v1/plans", map[string]interface{}{
		"title": "Media URL Update", "start_time": "09:00", "end_time": "17:00",
		"repeat_days": "1,2,3,4,5", "skip_holidays": false, "media_url": "file:///x",
		"is_active": false, "play_mode": "SEQUENTIAL",
	})
	if code != 200 {
		t.Fatalf("create: code=%d body=%s", code, raw)
	}
	planID, _ := parseJSON(t, raw)["id"].(string)
	if planID == "" {
		t.Fatal("missing plan id")
	}

	cases := []map[string]interface{}{
		{"media_url": 123},
		{"media_url": "ftp://example.com/a.mp4"},
		{"media_url": "file://"},
		{"media_url": "smb://missing-server/video.mp4"},
		{"media_url": "study_task://missing-task"},
	}
	for i, body := range cases {
		code, raw = putJSON(t, router, "/api/v1/plans/"+planID, body)
		if code != 400 {
			t.Fatalf("case %d expected 400, got %d body=%s", i, code, raw)
		}
	}
}
