func TestDevices_AddManualRejectsUnsupportedProtocol(t *testing.T) {
	router, _ := testRouter(t)
	code, body := postJSON(t, router, "/api/v1/devices/add", map[string]interface{}{
		"address":  "192.0.2.9",
		"port":     7000,
		"protocol": "chromecast",
	})
	if code != 400 {
		t.Fatalf("expected 400 for unsupported protocol, got %d body=%s", code, body)
	}
}
