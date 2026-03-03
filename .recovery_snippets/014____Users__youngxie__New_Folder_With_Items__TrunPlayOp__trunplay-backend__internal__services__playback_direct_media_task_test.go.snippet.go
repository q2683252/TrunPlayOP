func TestEnsureSingleMediaStudyTaskForPlan_PrunesExtraLinkedTasksWhenMatchFound(t *testing.T) {
	database := openSchedulerTestDB(t)

	tx, err := database.Begin()
	if err != nil {
		t.Fatalf("begin tx: %v", err)
	}
	plan, err := dbstore.CreatePlan(tx, "Prune Links", "09:00", "", "1,2,3,4,5", "", "file:///same.mp4", "SEQUENTIAL", false, false)
	if err != nil {
		t.Fatalf("create plan: %v", err)
	}
	planID, _ := plan["id"].(string)
	if planID == "" {
		t.Fatal("missing plan id")
	}

	taskA, err := dbstore.CreateStudyTask(tx, "task-a", []dbstore.StudyTaskMediaCreate{{
		MediaURI:   "/same.mp4",
		MediaName:  "same.mp4",
		Duration:   0,
		SortOrder:  0,
		SourceType: "LOCAL",
	}})
	if err != nil {
		t.Fatalf("create task-a: %v", err)
	}
	taskB, err := dbstore.CreateStudyTask(tx, "task-b", []dbstore.StudyTaskMediaCreate{{
		MediaURI:   "/other.mp4",
		MediaName:  "other.mp4",
		Duration:   0,
		SortOrder:  0,
		SourceType: "LOCAL",
	}})
	if err != nil {
		t.Fatalf("create task-b: %v", err)
	}
	taskAID, _ := taskA["id"].(string)
	taskBID, _ := taskB["id"].(string)
	if taskAID == "" || taskBID == "" {
		t.Fatal("missing task ids")
	}
	if err := dbstore.ReplaceAllPlanStudyTasks(tx, planID, []string{taskAID, taskBID}); err != nil {
		t.Fatalf("link tasks to plan: %v", err)
	}

	resolvedTaskID, err := ensureSingleMediaStudyTaskForPlan(tx, planID, "Prune Links", "file:///same.mp4")
	if err != nil {
		t.Fatalf("ensure single task: %v", err)
	}
	if resolvedTaskID != taskAID {
		t.Fatalf("expected resolved task %s, got %s", taskAID, resolvedTaskID)
	}

	linkedTasks, err := dbstore.GetPlanStudyTasks(tx, planID)
	if err != nil {
		t.Fatalf("get linked tasks: %v", err)
	}
	if len(linkedTasks) != 1 {
		t.Fatalf("expected pruned linked tasks len=1, got %d", len(linkedTasks))
	}
	linkedID, _ := linkedTasks[0]["id"].(string)
	if linkedID != taskAID {
		t.Fatalf("expected linked task %s after prune, got %s", taskAID, linkedID)
	}

	updatedPlan, err := dbstore.GetPlan(tx, planID)
	if err != nil {
		t.Fatalf("get updated plan: %v", err)
	}
	if mediaURL, _ := updatedPlan["media_url"].(string); mediaURL != "study_task://"+taskAID {
		t.Fatalf("expected media_url study_task://%s, got %q", taskAID, mediaURL)
	}

	if err := tx.Commit(); err != nil {
		t.Fatalf("commit tx: %v", err)
	}
}
