func TestHistory_ListUniqueFlagIsCaseInsensitive(t *testing.T) {
	router, database := testRouter(t)
	tx, err := database.Begin()
	if err != nil {
		t.Fatalf("begin tx: %v", err)
	}
	if _, err := db.CreatePlaybackHistory(tx, "plan-a", "Plan A", "", "", "", "http://stream/a", "episode-1", 0, "MANUAL", "LOCAL", "", "", ""); err != nil {
		t.Fatalf("create history #1: %v", err)
	}
	if _, err := db.CreatePlaybackHistory(tx, "plan-a", "Plan A", "", "", "", "http://stream/b", "episode-1", 0, "MANUAL", "LOCAL", "", "", ""); err != nil {
		t.Fatalf("create history #2: %v", err)
	}
	if err := tx.Commit(); err != nil {
		t.Fatalf("commit tx: %v", err)
	}

	code, body := get(t, router, "/api/v1/history?unique=TRUE")
	if code != 200 {
		t.Fatalf("GET /api/v1/history?unique=TRUE: code=%d body=%s", code, body)
	}
	resp := parseJSON(t, body)
	if total, _ := resp["total"].(float64); total != 1 {
		t.Fatalf("expected deduped total=1, got %v", resp["total"])
	}
	items, _ := resp["items"].([]interface{})
	if len(items) != 1 {
		t.Fatalf("expected deduped items len=1, got %d", len(items))
	}
}
