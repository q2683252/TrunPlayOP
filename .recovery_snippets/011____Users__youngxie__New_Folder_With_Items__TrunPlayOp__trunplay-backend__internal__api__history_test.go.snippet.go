func TestHistory_ListRejectsInvalidPagination(t *testing.T) {
	router, _ := testRouter(t)
	paths := []string{
		"/api/v1/history?page=abc",
		"/api/v1/history?page=0",
		"/api/v1/history?page_size=0",
		"/api/v1/history?page_size=101",
		"/api/v1/history?page_size=bad",
	}
	for _, path := range paths {
		code, body := get(t, router, path)
		if code != 400 {
			t.Fatalf("expected 400 for %s, got %d body=%s", path, code, body)
		}
	}
}
