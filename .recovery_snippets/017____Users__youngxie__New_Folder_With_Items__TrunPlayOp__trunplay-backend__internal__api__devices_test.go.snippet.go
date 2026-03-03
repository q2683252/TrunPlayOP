func TestDevices_DiscoverRejectsMalformedChunkedJSON(t *testing.T) {
	router, _ := testRouter(t)
	req := httptest.NewRequest(http.MethodPost, "/api/v1/devices/discover", strings.NewReader("{"))
	req.Header.Set("Content-Type", "application/json")
	req.ContentLength = -1
	req.TransferEncoding = []string{"chunked"}
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	if w.Code != 400 {
		t.Fatalf("expected 400 for malformed chunked JSON, got %d body=%s", w.Code, w.Body.Bytes())
	}
}
