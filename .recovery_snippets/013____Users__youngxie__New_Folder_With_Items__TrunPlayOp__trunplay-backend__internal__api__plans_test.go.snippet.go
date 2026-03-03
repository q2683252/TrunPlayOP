func TestPlans_UpdateMediaURLStudyTaskSyncsLinkedTasks(t *testing.T) {
	router, _ := testRouter(t)
	code, raw := postJSON(t, router, "/api/v1/plans", map[string]interface{}{
		"title": "Sync Study Task", "start_time": "09:00", "end_time": "17:00",
		"repeat_days": "1,2,3,4,5", "skip_holidays": false, "media_url": "file:///mnt/old.mp4",
		"is_active": false, "play_mode": "SEQUENTIAL",
	})
	if code != 200 {
		t.Fatalf("create plan: code=%d body=%s", code, raw)
	}
	planID, _ := parseJSON(t, raw)["id"].(string)
	if planID == "" {
		t.Fatal("missing plan id")
	}

	code, raw = postJSON(t, router, "/api/v1/study/tasks", map[string]interface{}{
		"name": "Target Task",
		"media_items": []interface{}{
			map[string]interface{}{
				"media_uri":   "file:///mnt/new.mp4",
				"media_name":  "new.mp4",
				"duration":    0,
				"sort_order":  0,
				"source_type": "LOCAL",
			},
		},
	})
	if code != 200 {
		t.Fatalf("create task: code=%d body=%s", code, raw)
	}
	taskID, _ := parseJSON(t, raw)["id"].(string)
	if taskID == "" {
		t.Fatal("missing task id")
	}

	code, raw = putJSON(t, router, "/api/v1/plans/"+planID, map[string]interface{}{
		"media_url": "study_task://" + taskID,
	})
	if code != 200 {
		t.Fatalf("update plan media_url: code=%d body=%s", code, raw)
	}

	code, raw = get(t, router, "/api/v1/plans/"+planID)
	if code != 200 {
		t.Fatalf("get plan: code=%d body=%s", code, raw)
	}
	got := parseJSON(t, raw)
	if mediaURL, _ := got["media_url"].(string); mediaURL != "study_task://"+taskID {
		t.Fatalf("expected media_url study_task://%s, got %q", taskID, mediaURL)
	}
	studyTasks, _ := got["study_tasks"].([]interface{})
	if len(studyTasks) != 1 {
		t.Fatalf("expected 1 linked study task, got %d", len(studyTasks))
	}
	linkedTask, _ := studyTasks[0].(map[string]interface{})
	if linkedID, _ := linkedTask["id"].(string); linkedID != taskID {
		t.Fatalf("expected linked task id %s, got %s", taskID, linkedID)
	}
}
