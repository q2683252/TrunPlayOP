package db

import "database/sql"

// Plan row (plans table)
type Plan struct {
	ID                   string
	Title                string
	StartTime            string
	EndTime              string
	RepeatDays           string
	SkipHolidays         bool
	DeviceID             sql.NullString
	MediaURL             string
	IsActive             bool
	CreatedAt            int64
	LastPlaybackPosition int64
	LastPlaybackMediaURI string
	LastPlaybackTime     int64
	MediaDuration        int64
	MediaName            string
	PlayMode             string
}

// Device row
type Device struct {
	ID           string
	Name         string
	Address      string
	Type         string
	Manufacturer string
	IsOnline     bool
	LastSeen     int64
	LocationURL  string
	Source       string
}

// SmbServer row
type SmbServer struct {
	ID              string
	Name            string
	Host            string
	Port            int
	Protocol        string
	Username        string
	Password        string
	SharePath       string
	IsConnected     bool
	LastConnectedAt int64
	CreatedAt       int64
	Hostname        string
	LastKnownHost   string
}

// PlaybackHistory row
type PlaybackHistory struct {
	ID              string
	PlanID          string
	PlanTitle       string
	DeviceID        sql.NullString
	DeviceName      sql.NullString
	DeviceAddress   sql.NullString
	MediaURL        string
	MediaName       string
	MediaDuration   int64
	ActualStartTime int64
	ActualEndTime   sql.NullInt64
	PlayedDuration  int64
	PlayedPosition  int64
	EndStatus       string
	ErrorCode       sql.NullString
	ErrorMessage    sql.NullString
	StopReason      sql.NullString
	NetworkType     sql.NullString
	TriggerType     string
	CreatedAt       int64
}

// StudyTask row
type StudyTask struct {
	ID              string
	Name            string
	TotalDuration   int64
	WatchedDuration int64
	CreatedAt       int64
	UpdatedAt       int64
}

// StudyTaskMedia row
type StudyTaskMedia struct {
	ID            string
	StudyTaskID   string
	MediaURI      string
	MediaName     string
	Duration      int64
	SortOrder     int
	SourceType    string
	ServerID      sql.NullString
	ThumbnailPath sql.NullString
}
