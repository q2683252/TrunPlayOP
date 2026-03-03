func TestStudy_CreateRejectsMismatchedMediaSourceType(t *testing.T) {
	router, _ := testRouter(t)
	tests := []map[string]interface{}{
		{
			"name": "local-with-smb-uri",
			"media_items": []interface{}{
				map[string]interface{}{
					"media_uri":   "smb://192.0.2.10/share/video.mp4",
					"media_name":  "video.mp4",
					"duration":    0,
					"sort_order":  0,
					"source_type": "LOCAL",
				},
			},
		},
		{
			"name": "smb-with-file-uri",
			"media_items": []interface{}{
				map[string]interface{}{
					"media_uri":   "file:///mnt/video.mp4",
					"media_name":  "video.mp4",
					"duration":    0,
					"sort_order":  0,
					"source_type": "SMB",
					"server_id":   "dummy",
				},
			},
		},
	}
	for i, body := range tests {
		code, raw := postJSON(t, router, "/api/v1/study/tasks", body)
		if code != 400 {
			t.Fatalf("case %d expected 400, got %d body=%s", i, code, raw)
		}
	}
}

func TestStudy_UpdateRejectsLocalSourceWithSmbURI(t *testing.T) {
	router, _ := testRouter(t)
	code, raw := postJSON(t, router, "/api/v1/study/tasks", map[string]interface{}{
		"name": "update-source-check",
		"media_items": []interface{}{
			map[string]interface{}{
				"media_uri":   "file:///mnt/a.mp4",
				"media_name":  "a.mp4",
				"duration":    0,
				"sort_order":  0,
				"source_type": "LOCAL",
			},
		},
	})
	if code != 200 {
		t.Fatalf("create: code=%d body=%s", code, raw)
	}
	taskID, _ := parseJSON(t, raw)["id"].(string)
	if taskID == "" {
		t.Fatal("missing task id")
	}

	code, raw = putJSON(t, router, "/api/v1/study/tasks/"+taskID, map[string]interface{}{
		"media_items": []interface{}{
			map[string]interface{}{
				"media_uri":   "smb://192.0.2.99/share/video.mp4",
				"media_name":  "video.mp4",
				"duration":    0,
				"sort_order":  0,
				"source_type": "LOCAL",
			},
		},
	})
	if code != 400 {
		t.Fatalf("expected 400 for mismatched update source, got %d body=%s", code, raw)
	}
}

func TestStudy_AddMediaRejectsLocalSourceWithSmbURI(t *testing.T) {
	router, _ := testRouter(t)
	code, raw := postJSON(t, router, "/api/v1/study/tasks", map[string]interface{}{
		"name":        "add-source-check",
		"media_items": []interface{}{},
	})
	if code != 200 {
		t.Fatalf("create task: code=%d body=%s", code, raw)
	}
	taskID, _ := parseJSON(t, raw)["id"].(string)
	if taskID == "" {
		t.Fatal("missing task id")
	}

	code, raw = postJSON(t, router, "/api/v1/study/tasks/"+taskID+"/media", map[string]interface{}{
		"media_uri":   "smb://192.0.2.11/share/video.mp4",
		"media_name":  "video.mp4",
		"duration":    0,
		"sort_order":  0,
		"source_type": "LOCAL",
	})
	if code != 400 {
		t.Fatalf("expected 400 for mismatched add media source, got %d body=%s", code, raw)
	}
}
