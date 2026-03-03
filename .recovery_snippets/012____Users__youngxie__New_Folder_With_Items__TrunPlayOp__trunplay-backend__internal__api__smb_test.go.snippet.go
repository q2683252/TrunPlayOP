func TestSmb_CreateRejectsUnsupportedProtocol(t *testing.T) {
	router, _ := testRouter(t)
	code, raw := postJSON(t, router, "/api/v1/smb/servers", map[string]interface{}{
		"name":      "Bad Protocol SMB",
		"host":      "192.0.2.66",
		"port":      445,
		"protocol":  "NFS",
		"username":  "u",
		"password":  "p",
		"share_path": "Data",
	})
	if code != 400 {
		t.Fatalf("expected 400 for unsupported smb protocol, got %d body=%s", code, raw)
	}
}
