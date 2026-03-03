package db

import (
	"database/sql"
	"os"
	"path/filepath"
	"testing"
)

func testDB(t *testing.T) (*sql.DB, func()) {
	dir := t.TempDir()
	path := filepath.Join(dir, "test.db")
	db, err := OpenAt(path)
	if err != nil {
		t.Fatal("open:", err)
	}
	if err := Init(db); err != nil {
		db.Close()
		t.Fatal("init:", err)
	}
	cleanup := func() {
		db.Close()
		os.Remove(path)
	}
	return db, cleanup
}

func TestCreatePlan_GetPlan(t *testing.T) {
	db, cleanup := testDB(t)
	defer cleanup()
	tx, err := db.Begin()
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback()

	plan, err := CreatePlan(tx, "Title", "09:00", "17:00", "1,2,3,4,5", "", "file:///mnt/video.mp4", "SEQUENTIAL", false, true)
	if err != nil {
		t.Fatal(err)
	}
	if plan == nil {
		t.Fatal("expected plan")
	}
	if plan["title"] != "Title" {
		t.Errorf("title: got %v", plan["title"])
	}
	if plan["start_time"] != "09:00" {
		t.Errorf("start_time: got %v", plan["start_time"])
	}
	if plan["is_active"] != true {
		t.Errorf("is_active: got %v", plan["is_active"])
	}
	id, _ := plan["id"].(string)
	if id == "" {
		t.Error("id empty")
	}

	got, err := GetPlan(tx, id)
	if err != nil {
		t.Fatal(err)
	}
	if got["title"] != "Title" {
		t.Errorf("get plan title: got %v", got["title"])
	}
}

func TestGetPlans_Empty(t *testing.T) {
	db, cleanup := testDB(t)
	defer cleanup()
	tx, err := db.Begin()
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback()

	plans, err := GetPlans(tx, 0, 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(plans) != 0 {
		t.Errorf("expected 0 plans, got %d", len(plans))
	}
}

func TestUpdatePlan_DeletePlan(t *testing.T) {
	db, cleanup := testDB(t)
	defer cleanup()
	tx, err := db.Begin()
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback()

	plan, err := CreatePlan(tx, "Old", "09:00", "17:00", "1,2,3,4,5", "", "file:///x", "SEQUENTIAL", false, true)
	if err != nil {
		t.Fatal(err)
	}
	id, _ := plan["id"].(string)

	updated, err := UpdatePlan(tx, id, map[string]interface{}{"title": "New"})
	if err != nil {
		t.Fatal(err)
	}
	if updated["title"] != "New" {
		t.Errorf("updated title: got %v", updated["title"])
	}

	ok, err := DeletePlan(tx, id)
	if err != nil {
		t.Fatal(err)
	}
	if !ok {
		t.Error("delete expected true")
	}
	got, _ := GetPlan(tx, id)
	if got != nil {
		t.Error("plan should be nil after delete")
	}
}

func TestCreateDevice_GetDevices_DeleteDevice(t *testing.T) {
	db, cleanup := testDB(t)
	defer cleanup()
	tx, err := db.Begin()
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback()

	dev, err := CreateDevice(tx, "dev-1", "TV", "192.168.1.100", "MediaRenderer", "Samsung", true, 0, "http://192.168.1.100:9197/desc", "DISCOVERED")
	if err != nil {
		t.Fatal(err)
	}
	if dev["name"] != "TV" {
		t.Errorf("device name: got %v", dev["name"])
	}

	list, err := GetDevices(tx)
	if err != nil {
		t.Fatal(err)
	}
	if len(list) != 1 {
		t.Errorf("expected 1 device, got %d", len(list))
	}

	ok, err := DeleteDevice(tx, "dev-1")
	if err != nil {
		t.Fatal(err)
	}
	if !ok {
		t.Error("delete expected true")
	}
	list, _ = GetDevices(tx)
	if len(list) != 0 {
		t.Errorf("expected 0 devices after delete, got %d", len(list))
	}
}

func TestCreateSmbServer_GetSmbServers(t *testing.T) {
	db, cleanup := testDB(t)
	defer cleanup()
	tx, err := db.Begin()
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback()

	server, err := CreateSmbServer(tx, "NAS", "192.168.1.10", 445, "SMB", "user", "pass", "/share")
	if err != nil {
		t.Fatal(err)
	}
	if server["name"] != "NAS" || server["host"] != "192.168.1.10" {
		t.Errorf("server: got %v", server)
	}

	list, err := GetSmbServers(tx)
	if err != nil {
		t.Fatal(err)
	}
	if len(list) != 1 {
		t.Errorf("expected 1 smb server, got %d", len(list))
	}
}

func TestCreatePlaybackHistory_GetPlaybackHistories(t *testing.T) {
	db, cleanup := testDB(t)
	defer cleanup()
	tx, err := db.Begin()
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback()

	h, err := CreatePlaybackHistory(tx, "plan-1", "Plan Title", "dev-1", "TV", "192.168.1.1", "http://x/v.mp4", "video", 3600, "SCHEDULED", "Unknown")
	if err != nil {
		t.Fatal(err)
	}
	if h["plan_id"] != "plan-1" || h["media_name"] != "video" {
		t.Errorf("history: got %v", h)
	}

	total, items, err := GetPlaybackHistories(tx, 0, 10, "")
	if err != nil {
		t.Fatal(err)
	}
	if total != 1 || len(items) != 1 {
		t.Errorf("total=%d items=%d", total, len(items))
	}
}

func TestCreateStudyTask_GetStudyTask(t *testing.T) {
	db, cleanup := testDB(t)
	defer cleanup()
	tx, err := db.Begin()
	if err != nil {
		t.Fatal(err)
	}
	defer tx.Rollback()

	task, err := CreateStudyTask(tx, "Task1", []StudyTaskMediaCreate{
		{MediaURI: "file:///a.mp4", MediaName: "a", Duration: 100, SortOrder: 0, SourceType: "LOCAL", ServerID: ""},
	})
	if err != nil {
		t.Fatal(err)
	}
	if task["name"] != "Task1" {
		t.Errorf("task name: got %v", task["name"])
	}
	mediaItems, _ := task["media_items"].([]map[string]interface{})
	if len(mediaItems) != 1 {
		t.Errorf("expected 1 media item, got %d", len(mediaItems))
	}

	taskID, _ := task["id"].(string)
	got, err := GetStudyTask(tx, taskID)
	if err != nil {
		t.Fatal(err)
	}
	if got["name"] != "Task1" {
		t.Errorf("get task name: got %v", got["name"])
	}
}
