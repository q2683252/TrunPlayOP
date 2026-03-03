package db

import (
	"database/sql"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"
)

var DBPath = getDBPath()

func getDBPath() string {
	if p := os.Getenv("TRUNPLAY_DB_PATH"); p != "" {
		return p
	}
	return "/etc/trunplay/trunplay.db"
}

func Open() (*sql.DB, error) {
	dir := filepath.Dir(DBPath)
	if dir != "" {
		_ = os.MkdirAll(dir, 0755)
	}
	return sql.Open("sqlite", DBPath)
}

// OpenAt opens SQLite at the given path (for tests).
func OpenAt(path string) (*sql.DB, error) {
	dir := filepath.Dir(path)
	if dir != "" {
		_ = os.MkdirAll(dir, 0755)
	}
	return sql.Open("sqlite", path)
}

const schemaSQL = `
CREATE TABLE IF NOT EXISTS plans (
	id TEXT PRIMARY KEY,
	title TEXT NOT NULL,
	start_time TEXT NOT NULL,
	end_time TEXT NOT NULL,
	repeat_days TEXT NOT NULL,
	skip_holidays INTEGER DEFAULT 0,
	device_id TEXT REFERENCES devices(id),
	media_url TEXT NOT NULL,
	is_active INTEGER DEFAULT 1,
	created_at INTEGER NOT NULL,
	last_playback_position INTEGER DEFAULT 0,
	last_playback_media_uri TEXT DEFAULT '',
	last_playback_time INTEGER DEFAULT 0,
	media_duration INTEGER DEFAULT 0,
	media_name TEXT DEFAULT '',
	play_mode TEXT DEFAULT 'SEQUENTIAL'
);
CREATE TABLE IF NOT EXISTS devices (
	id TEXT PRIMARY KEY,
	name TEXT NOT NULL,
	address TEXT NOT NULL,
	type TEXT DEFAULT 'MediaRenderer',
	manufacturer TEXT DEFAULT '',
	is_online INTEGER DEFAULT 0,
	last_seen INTEGER DEFAULT 0,
	location_url TEXT DEFAULT '',
	source TEXT DEFAULT 'DISCOVERED'
);
CREATE TABLE IF NOT EXISTS smb_servers (
	id TEXT PRIMARY KEY,
	name TEXT NOT NULL,
	host TEXT NOT NULL,
	port INTEGER DEFAULT 445,
	protocol TEXT DEFAULT 'SMB',
	username TEXT DEFAULT '',
	password TEXT DEFAULT '',
	share_path TEXT DEFAULT '',
	is_connected INTEGER DEFAULT 0,
	last_connected_at INTEGER DEFAULT 0,
	created_at INTEGER NOT NULL,
	hostname TEXT DEFAULT '',
	last_known_host TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS playback_history (
	id TEXT PRIMARY KEY,
	plan_id TEXT NOT NULL,
	plan_title TEXT NOT NULL,
	device_id TEXT,
	device_name TEXT,
	device_address TEXT,
	media_url TEXT NOT NULL,
	media_name TEXT NOT NULL,
	media_duration INTEGER DEFAULT 0,
	actual_start_time INTEGER NOT NULL,
	actual_end_time INTEGER,
	played_duration INTEGER DEFAULT 0,
	played_position INTEGER DEFAULT 0,
	end_status TEXT DEFAULT 'IN_PROGRESS',
	error_code TEXT,
	error_message TEXT,
	stop_reason TEXT,
	network_type TEXT,
	trigger_type TEXT DEFAULT 'SCHEDULED',
	created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_plan_id ON playback_history(plan_id);
CREATE INDEX IF NOT EXISTS idx_history_start_time ON playback_history(actual_start_time);
CREATE INDEX IF NOT EXISTS idx_history_end_status ON playback_history(end_status);
CREATE TABLE IF NOT EXISTS study_tasks (
	id TEXT PRIMARY KEY,
	name TEXT NOT NULL,
	total_duration INTEGER DEFAULT 0,
	watched_duration INTEGER DEFAULT 0,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS study_task_media (
	id TEXT PRIMARY KEY,
	study_task_id TEXT NOT NULL REFERENCES study_tasks(id) ON DELETE CASCADE,
	media_uri TEXT NOT NULL,
	media_name TEXT NOT NULL,
	duration INTEGER DEFAULT 0,
	sort_order INTEGER DEFAULT 0,
	source_type TEXT DEFAULT 'LOCAL',
	server_id TEXT,
	thumbnail_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_study_media_task_id ON study_task_media(study_task_id);
CREATE INDEX IF NOT EXISTS idx_study_media_sort_order ON study_task_media(sort_order);
CREATE TABLE IF NOT EXISTS plan_study_tasks (
	id TEXT PRIMARY KEY,
	plan_id TEXT NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
	study_task_id TEXT NOT NULL REFERENCES study_tasks(id) ON DELETE CASCADE,
	sort_order INTEGER DEFAULT 0,
	UNIQUE(plan_id, study_task_id)
);
CREATE INDEX IF NOT EXISTS idx_plan_study_tasks_plan ON plan_study_tasks(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_study_tasks_study_task ON plan_study_tasks(study_task_id);
`

func Init(db *sql.DB) error {
	for _, s := range splitSchema(schemaSQL) {
		if s == "" {
			continue
		}
		if _, err := db.Exec(s); err != nil {
			return err
		}
	}
	return nil
}

func splitSchema(s string) []string {
	var out []string
	var cur string
	for _, line := range splitLines(s) {
		cur += line + "\n"
		if len(line) > 0 && line[len(line)-1] == ';' {
			out = append(out, trimSpace(cur))
			cur = ""
		}
	}
	if trimSpace(cur) != "" {
		out = append(out, trimSpace(cur))
	}
	return out
}

func splitLines(s string) []string {
	var out []string
	start := 0
	for i := 0; i <= len(s); i++ {
		if i == len(s) || s[i] == '\n' {
			out = append(out, s[start:i])
			start = i + 1
		}
	}
	return out
}

func trimSpace(s string) string {
	for len(s) > 0 && (s[0] == ' ' || s[0] == '\n' || s[0] == '\t') {
		s = s[1:]
	}
	for len(s) > 0 && (s[len(s)-1] == ' ' || s[len(s)-1] == '\n' || s[len(s)-1] == '\t') {
		s = s[:len(s)-1]
	}
	return s
}
