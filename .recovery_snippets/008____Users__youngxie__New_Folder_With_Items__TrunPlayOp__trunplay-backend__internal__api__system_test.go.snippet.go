func TestSystem_StatusReturnsServerErrorWhenDBQueryFails(t *testing.T) {
	router, database := testRouter(t)
	if _, err := database.Exec("DROP TABLE devices"); err != nil {
		t.Fatalf("drop devices table: %v", err)
	}
	code, _ := get(t, router, "/api/v1/system/status")
	if code != 500 {
		t.Fatalf("expected 500 when status query fails, got %d", code)
	}
}
