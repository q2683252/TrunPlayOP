package services

import (
	"testing"

	dbstore "github.com/trunplay/trunplay-backend/internal/db"
)

func TestEnsureSingleMediaStudyTaskForPlan_ReplacesMismatchedLinkedTask(t *testing.T) {
	database := openSchedulerTestDB(t)

	tx, err := database.Begin()
	if err != nil {
		t.Fatalf("begin create tx: %v", err)
	}
	plan, err := dbstore.CreatePlan(tx, "Direct Media", "09:00", "", "1,2,3,4,5", "", "file:///old.mp4", "SEQUENTIAL", false, false)
	if err != nil {
		t.Fatalf("create plan: %v", err)
	}
	planID, _ := plan["id"].(string)
	if planID == "" {
		t.Fatal("missing plan id")
	}
	if err := tx.Commit(); err != nil {
		t.Fatalf("commit create tx: %v", err)
	}

	tx, err = database.Begin()
	if err != nil {
		t.Fatalf("begin ensure old tx: %v", err)
	}
	oldTaskID, err := ensureSingleMediaStudyTaskForPlan(tx, planID, "Direct Media", "file:///old.mp4")
	if err != nil {
		t.Fatalf("ensure old task: %v", err)
	}
	if oldTaskID == "" {
		t.Fatal("missing old task id")
	}
	if err := tx.Commit(); err != nil {
		t.Fatalf("commit ensure old tx: %v", err)
	}

	tx, err = database.Begin()
	if err != nil {
		t.Fatalf("begin ensure new tx: %v", err)
	}
	newTaskID, err := ensureSingleMediaStudyTaskForPlan(tx, planID, "Direct Media", "file:///new.mp4")
	if err != nil {
		t.Fatalf("ensure new task: %v", err)
	}
	if newTaskID == "" {
		t.Fatal("missing new task id")
	}
	if newTaskID == oldTaskID {
		t.Fatalf("expected a new task when media changes, got same id %s", newTaskID)
	}

	linkedTasks, err := dbstore.GetPlanStudyTasks(tx, planID)
	if err != nil {
		t.Fatalf("get plan study tasks: %v", err)
	}
	if len(linkedTasks) != 1 {
		t.Fatalf("expected single linked task after replace, got %d", len(linkedTasks))
	}
	linkedID, _ := linkedTasks[0]["id"].(string)
	if linkedID != newTaskID {
		t.Fatalf("expected linked task %s, got %s", newTaskID, linkedID)
	}

	refreshedPlan, err := dbstore.GetPlan(tx, planID)
	if err != nil {
		t.Fatalf("get plan: %v", err)
	}
	mediaURL, _ := refreshedPlan["media_url"].(string)
	if mediaURL != "study_task://"+newTaskID {
		t.Fatalf("expected media_url rewritten to study_task://%s, got %q", newTaskID, mediaURL)
	}

	newTask, err := dbstore.GetStudyTask(tx, newTaskID)
	if err != nil {
		t.Fatalf("get new study task: %v", err)
	}
	items, _ := newTask["media_items"].([]map[string]interface{})
	if len(items) != 1 {
		t.Fatalf("expected one media item in new study task, got %d", len(items))
	}
	if gotURI, _ := items[0]["media_uri"].(string); gotURI != "/new.mp4" {
		t.Fatalf("expected new media uri /new.mp4, got %q", gotURI)
	}

	if err := tx.Commit(); err != nil {
		t.Fatalf("commit ensure new tx: %v", err)
	}
}
