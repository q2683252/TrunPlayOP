func TestEnsureSingleMediaStudyTaskForPlan_RejectsMissingSmbServer(t *testing.T) {
	database := openSchedulerTestDB(t)
	tx, err := database.Begin()
	if err != nil {
		t.Fatalf("begin create tx: %v", err)
	}
	plan, err := dbstore.CreatePlan(tx, "Missing SMB", "09:00", "", "1,2,3,4,5", "", "smb://missing/video.mp4", "SEQUENTIAL", false, false)
	if err != nil {
		t.Fatalf("create plan: %v", err)
	}
	if err := tx.Commit(); err != nil {
		t.Fatalf("commit create tx: %v", err)
	}
	planID, _ := plan["id"].(string)
	if planID == "" {
		t.Fatal("missing plan id")
	}

	tx, err = database.Begin()
	if err != nil {
		t.Fatalf("begin ensure tx: %v", err)
	}
	defer tx.Rollback()
	if _, err := ensureSingleMediaStudyTaskForPlan(tx, planID, "Missing SMB", "smb://missing/video.mp4"); err == nil {
		t.Fatal("expected error for missing SMB server")
	}
}

func TestEnsureSingleMediaStudyTaskForPlan_RejectsEmptyLocalPath(t *testing.T) {
	database := openSchedulerTestDB(t)
	tx, err := database.Begin()
	if err != nil {
		t.Fatalf("begin create tx: %v", err)
	}
	plan, err := dbstore.CreatePlan(tx, "Bad Local", "09:00", "", "1,2,3,4,5", "", "file://", "SEQUENTIAL", false, false)
	if err != nil {
		t.Fatalf("create plan: %v", err)
	}
	if err := tx.Commit(); err != nil {
		t.Fatalf("commit create tx: %v", err)
	}
	planID, _ := plan["id"].(string)
	if planID == "" {
		t.Fatal("missing plan id")
	}

	tx, err = database.Begin()
	if err != nil {
		t.Fatalf("begin ensure tx: %v", err)
	}
	defer tx.Rollback()
	if _, err := ensureSingleMediaStudyTaskForPlan(tx, planID, "Bad Local", "file://"); err == nil {
		t.Fatal("expected error for empty local media path")
	}
}
