func TestPlans_CreateRejectsEmptyFileMediaPath(t *testing.T) {
	router, _ := testRouter(t)
	body := map[string]interface{}{
		"title":         "Empty File Media",
		"start_time":    "09:00",
		"end_time":      "17:00",
		"repeat_days":   "1,2,3,4,5",
		"skip_holidays": false,
		"media_url":     "file://",
		"is_active":     false,
		"play_mode":     "SEQUENTIAL",
	}
	code, _ := postJSON(t, router, "/api/v1/plans", body)
	if code != 400 {
		t.Fatalf("expected 400 for empty file media path, got %d", code)
	}
}

func TestPlans_CreateRejectsBlankSmbMediaPath(t *testing.T) {
	router, _ := testRouter(t)
	createServerCode, createServerRaw := postJSON(t, router, "/api/v1/smb/servers", map[string]interface{}{
		"name":       "Plan SMB Blank Path",
		"host":       "192.0.2.21",
		"port":       445,
		"username":   "u",
		"password":   "p",
		"share_path": "Data",
	})
	if createServerCode != 200 {
		t.Fatalf("create smb server: code=%d body=%s", createServerCode, createServerRaw)
	}
	serverID, _ := parseJSON(t, createServerRaw)["id"].(string)
	if serverID == "" {
		t.Fatal("missing smb server id")
	}

	body := map[string]interface{}{
		"title":         "SMB Blank Path",
		"start_time":    "09:00",
		"end_time":      "17:00",
		"repeat_days":   "1,2,3,4,5",
		"skip_holidays": false,
		"media_url":     "smb://" + serverID + "/   ",
		"is_active":     false,
		"play_mode":     "SEQUENTIAL",
	}
	code, _ := postJSON(t, router, "/api/v1/plans", body)
	if code != 400 {
		t.Fatalf("expected 400 for blank smb media path, got %d", code)
	}
}
