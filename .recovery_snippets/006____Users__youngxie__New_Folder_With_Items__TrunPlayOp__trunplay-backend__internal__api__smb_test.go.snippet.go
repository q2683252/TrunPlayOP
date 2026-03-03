func TestSmb_DiscoverRejectsInvalidTimeout(t *testing.T) {
	router, _ := testRouter(t)
	paths := []string{
		"/api/v1/smb/discover?timeout=-1",
		"/api/v1/smb/discover?timeout=0",
		"/api/v1/smb/discover?timeout=500",
		"/api/v1/smb/discover?timeout=bad",
	}
	for _, p := range paths {
		code, body := postJSON(t, router, p, nil)
		if code != 400 {
			t.Fatalf("expected 400 for %s, got %d body=%s", p, code, body)
		}
	}
	code, body := postJSON(t, router, "/api/v1/smb/discover", map[string]interface{}{"timeout_seconds": -1})
	if code != 400 {
		t.Fatalf("expected 400 for negative timeout_seconds, got %d body=%s", code, body)
	}
	code, body = postJSON(t, router, "/api/v1/smb/discover", map[string]interface{}{"timeout_seconds": 200})
	if code != 400 {
		t.Fatalf("expected 400 for oversized timeout_seconds, got %d body=%s", code, body)
	}
}
