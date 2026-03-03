package db

import (
	"database/sql"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
)

var (
	ErrPlanNotFound      = errors.New("plan not found")
	ErrStudyTaskNotFound = errors.New("study task not found")
)

func planToMap(p *Plan, skipHolidays, isActive bool) map[string]interface{} {
	m := map[string]interface{}{
		"id":                      p.ID,
		"title":                   p.Title,
		"start_time":              p.StartTime,
		"end_time":                p.EndTime,
		"repeat_days":             p.RepeatDays,
		"skip_holidays":           skipHolidays,
		"media_url":               p.MediaURL,
		"is_active":               isActive,
		"created_at":              p.CreatedAt,
		"last_playback_position":  p.LastPlaybackPosition,
		"last_playback_media_uri": p.LastPlaybackMediaURI,
		"last_playback_time":      p.LastPlaybackTime,
		"media_duration":          p.MediaDuration,
		"media_name":              p.MediaName,
		"play_mode":               p.PlayMode,
	}
	if p.DeviceID.Valid {
		m["device_id"] = p.DeviceID.String
	} else {
		m["device_id"] = nil
	}
	return m
}

func CreatePlan(tx *sql.Tx, title, startTime, endTime, repeatDays, deviceID, mediaURL, playMode string, skipHolidays, isActive bool) (map[string]interface{}, error) {
	id := uuid.New().String()
	now := time.Now().UnixMilli()
	skip := 0
	if skipHolidays {
		skip = 1
	}
	active := 0
	if isActive {
		active = 1
	}
	_, err := tx.Exec(
		`INSERT INTO plans (id, title, start_time, end_time, repeat_days, skip_holidays, device_id, media_url, is_active, play_mode, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)`,
		id, title, startTime, endTime, repeatDays, skip, nullStr(deviceID), mediaURL, active, playMode, now,
	)
	if err != nil {
		return nil, err
	}
	return GetPlan(tx, id)
}

func GetPlan(tx *sql.Tx, planID string) (map[string]interface{}, error) {
	var p Plan
	var deviceID sql.NullString
	var skipHolidays, isActive int
	err := tx.QueryRow(
		`SELECT id, title, start_time, end_time, repeat_days, skip_holidays, device_id, media_url, is_active, created_at, last_playback_position, last_playback_media_uri, last_playback_time, media_duration, media_name, play_mode FROM plans WHERE id = ?`,
		planID,
	).Scan(
		&p.ID, &p.Title, &p.StartTime, &p.EndTime, &p.RepeatDays,
		&skipHolidays, &deviceID, &p.MediaURL, &isActive, &p.CreatedAt,
		&p.LastPlaybackPosition, &p.LastPlaybackMediaURI, &p.LastPlaybackTime,
		&p.MediaDuration, &p.MediaName, &p.PlayMode,
	)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	p.DeviceID = deviceID
	return planToMap(&p, skipHolidays == 1, isActive == 1), nil
}

func GetPlans(tx *sql.Tx, skip, limit int) ([]map[string]interface{}, error) {
	rows, err := tx.Query(`SELECT id, title, start_time, end_time, repeat_days, skip_holidays, device_id, media_url, is_active, created_at, last_playback_position, last_playback_media_uri, last_playback_time, media_duration, media_name, play_mode FROM plans ORDER BY created_at DESC LIMIT ? OFFSET ?`, limit, skip)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []map[string]interface{}
	for rows.Next() {
		var p Plan
		var deviceID sql.NullString
		var skipHolidays, isActive int
		if err := rows.Scan(&p.ID, &p.Title, &p.StartTime, &p.EndTime, &p.RepeatDays, &skipHolidays, &deviceID, &p.MediaURL, &isActive, &p.CreatedAt, &p.LastPlaybackPosition, &p.LastPlaybackMediaURI, &p.LastPlaybackTime, &p.MediaDuration, &p.MediaName, &p.PlayMode); err != nil {
			return nil, err
		}
		p.DeviceID = deviceID
		out = append(out, planToMap(&p, skipHolidays == 1, isActive == 1))
	}
	return out, nil
}

func GetActivePlans(tx *sql.Tx) ([]map[string]interface{}, error) {
	rows, err := tx.Query(`SELECT id, title, start_time, end_time, repeat_days, skip_holidays, device_id, media_url, is_active, created_at, last_playback_position, last_playback_media_uri, last_playback_time, media_duration, media_name, play_mode FROM plans WHERE is_active = 1`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []map[string]interface{}
	for rows.Next() {
		var p Plan
		var deviceID sql.NullString
		var skipHolidays, isActive int
		if err := rows.Scan(&p.ID, &p.Title, &p.StartTime, &p.EndTime, &p.RepeatDays, &skipHolidays, &deviceID, &p.MediaURL, &isActive, &p.CreatedAt, &p.LastPlaybackPosition, &p.LastPlaybackMediaURI, &p.LastPlaybackTime, &p.MediaDuration, &p.MediaName, &p.PlayMode); err != nil {
			return nil, err
		}
		p.DeviceID = deviceID
		out = append(out, planToMap(&p, skipHolidays == 1, isActive == 1))
	}
	return out, nil
}

func UpdatePlan(tx *sql.Tx, planID string, updates map[string]interface{}) (map[string]interface{}, error) {
	_, err := GetPlan(tx, planID)
	if err != nil || _getPlan(tx, planID) == nil {
		return nil, nil
	}
	// Build SET clause from updates (only allowed fields)
	if v, ok := updates["title"]; ok {
		tx.Exec("UPDATE plans SET title = ? WHERE id = ?", v, planID)
	}
	if v, ok := updates["start_time"]; ok {
		tx.Exec("UPDATE plans SET start_time = ? WHERE id = ?", v, planID)
	}
	if v, ok := updates["end_time"]; ok {
		tx.Exec("UPDATE plans SET end_time = ? WHERE id = ?", v, planID)
	}
	if v, ok := updates["repeat_days"]; ok {
		tx.Exec("UPDATE plans SET repeat_days = ? WHERE id = ?", v, planID)
	}
	if v, ok := updates["skip_holidays"]; ok {
		b := 0
		if bv, ok := v.(bool); ok && bv {
			b = 1
		}
		tx.Exec("UPDATE plans SET skip_holidays = ? WHERE id = ?", b, planID)
	}
	if v, ok := updates["device_id"]; ok {
		tx.Exec("UPDATE plans SET device_id = ? WHERE id = ?", v, planID)
	}
	if v, ok := updates["media_url"]; ok {
		tx.Exec("UPDATE plans SET media_url = ? WHERE id = ?", v, planID)
	}
	if v, ok := updates["is_active"]; ok {
		b := 0
		if bv, ok := v.(bool); ok && bv {
			b = 1
		}
		tx.Exec("UPDATE plans SET is_active = ? WHERE id = ?", b, planID)
	}
	if v, ok := updates["play_mode"]; ok {
		tx.Exec("UPDATE plans SET play_mode = ? WHERE id = ?", v, planID)
	}
	return GetPlan(tx, planID)
}

func _getPlan(tx *sql.Tx, planID string) *Plan {
	var p Plan
	var deviceID sql.NullString
	var skipHolidays, isActive int
	err := tx.QueryRow(`SELECT id FROM plans WHERE id = ?`, planID).Scan(&p.ID)
	if err != nil {
		return nil
	}
	_ = tx.QueryRow(`SELECT id, title, start_time, end_time, repeat_days, skip_holidays, device_id, media_url, is_active, created_at, last_playback_position, last_playback_media_uri, last_playback_time, media_duration, media_name, play_mode FROM plans WHERE id = ?`, planID).Scan(
		&p.ID, &p.Title, &p.StartTime, &p.EndTime, &p.RepeatDays, &skipHolidays, &deviceID, &p.MediaURL, &isActive, &p.CreatedAt, &p.LastPlaybackPosition, &p.LastPlaybackMediaURI, &p.LastPlaybackTime, &p.MediaDuration, &p.MediaName, &p.PlayMode,
	)
	return &p
}

func DeletePlan(tx *sql.Tx, planID string) (bool, error) {
	res, err := tx.Exec("DELETE FROM plans WHERE id = ?", planID)
	if err != nil {
		return false, err
	}
	n, _ := res.RowsAffected()
	return n > 0, nil
}

func UpdatePlanPlaybackProgress(tx *sql.Tx, planID string, position int64, mediaURI string, duration int64) (map[string]interface{}, error) {
	if _getPlan(tx, planID) == nil {
		return nil, nil
	}
	now := time.Now().UnixMilli()
	if duration > 0 {
		_, err := tx.Exec("UPDATE plans SET last_playback_position = ?, last_playback_media_uri = ?, last_playback_time = ?, media_duration = ? WHERE id = ?", position, mediaURI, now, duration, planID)
		if err != nil {
			return nil, err
		}
	} else {
		_, err := tx.Exec("UPDATE plans SET last_playback_position = ?, last_playback_media_uri = ?, last_playback_time = ? WHERE id = ?", position, mediaURI, now, planID)
		if err != nil {
			return nil, err
		}
	}
	return GetPlan(tx, planID)
}

func ResetPlanProgress(tx *sql.Tx, planID string) (map[string]interface{}, error) {
	if _getPlan(tx, planID) == nil {
		return nil, nil
	}
	_, err := tx.Exec("UPDATE plans SET last_playback_position = 0, last_playback_media_uri = '', last_playback_time = 0 WHERE id = ?", planID)
	if err != nil {
		return nil, err
	}
	return GetPlan(tx, planID)
}

func nullStr(s string) interface{} {
	if s == "" {
		return nil
	}
	return s
}

// --- Device CRUD ---
func deviceToMap(d *Device) map[string]interface{} {
	m := map[string]interface{}{
		"id": d.ID, "name": d.Name, "address": d.Address, "type": d.Type, "manufacturer": d.Manufacturer,
		"is_online": d.IsOnline, "last_seen": d.LastSeen, "location_url": d.LocationURL, "source": d.Source,
	}
	return m
}

func CreateDevice(tx *sql.Tx, id, name, address, deviceType, manufacturer string, isOnline bool, lastSeen int64, locationURL, source string) (map[string]interface{}, error) {
	online := 0
	if isOnline {
		online = 1
	}
	_, err := tx.Exec(
		`INSERT INTO devices (id, name, address, type, manufacturer, is_online, last_seen, location_url, source) VALUES (?,?,?,?,?,?,?,?,?)`,
		id, name, address, deviceType, manufacturer, online, lastSeen, locationURL, source,
	)
	if err != nil {
		return nil, err
	}
	return GetDevice(tx, id)
}

func GetDevice(tx *sql.Tx, deviceID string) (map[string]interface{}, error) {
	var d Device
	var isOnline int
	err := tx.QueryRow(`SELECT id, name, address, type, manufacturer, is_online, last_seen, location_url, source FROM devices WHERE id = ?`, deviceID).Scan(
		&d.ID, &d.Name, &d.Address, &d.Type, &d.Manufacturer, &isOnline, &d.LastSeen, &d.LocationURL, &d.Source,
	)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	d.IsOnline = isOnline == 1
	return deviceToMap(&d), nil
}

func GetDevices(tx *sql.Tx) ([]map[string]interface{}, error) {
	rows, err := tx.Query(`SELECT id, name, address, type, manufacturer, is_online, last_seen, location_url, source FROM devices`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []map[string]interface{}
	for rows.Next() {
		var d Device
		var isOnline int
		if err := rows.Scan(&d.ID, &d.Name, &d.Address, &d.Type, &d.Manufacturer, &isOnline, &d.LastSeen, &d.LocationURL, &d.Source); err != nil {
			return nil, err
		}
		d.IsOnline = isOnline == 1
		out = append(out, deviceToMap(&d))
	}
	return out, nil
}

func UpdateDevice(tx *sql.Tx, deviceID string, updates map[string]interface{}) (map[string]interface{}, error) {
	_, err := GetDevice(tx, deviceID)
	if err != nil || _getDevice(tx, deviceID) == nil {
		return nil, nil
	}
	if v, ok := updates["name"]; ok {
		tx.Exec("UPDATE devices SET name = ? WHERE id = ?", v, deviceID)
	}
	if v, ok := updates["address"]; ok {
		tx.Exec("UPDATE devices SET address = ? WHERE id = ?", v, deviceID)
	}
	if v, ok := updates["type"]; ok {
		tx.Exec("UPDATE devices SET type = ? WHERE id = ?", v, deviceID)
	}
	if v, ok := updates["manufacturer"]; ok {
		tx.Exec("UPDATE devices SET manufacturer = ? WHERE id = ?", v, deviceID)
	}
	if v, ok := updates["is_online"]; ok {
		b := 0
		if bv, ok := v.(bool); ok && bv {
			b = 1
		}
		tx.Exec("UPDATE devices SET is_online = ? WHERE id = ?", b, deviceID)
	}
	if v, ok := updates["last_seen"]; ok {
		tx.Exec("UPDATE devices SET last_seen = ? WHERE id = ?", v, deviceID)
	}
	if v, ok := updates["location_url"]; ok {
		tx.Exec("UPDATE devices SET location_url = ? WHERE id = ?", v, deviceID)
	}
	if v, ok := updates["source"]; ok {
		tx.Exec("UPDATE devices SET source = ? WHERE id = ?", v, deviceID)
	}
	return GetDevice(tx, deviceID)
}

func _getDevice(tx *sql.Tx, deviceID string) *Device {
	var d Device
	var isOnline int
	err := tx.QueryRow(`SELECT id, name, address, type, manufacturer, is_online, last_seen, location_url, source FROM devices WHERE id = ?`, deviceID).Scan(
		&d.ID, &d.Name, &d.Address, &d.Type, &d.Manufacturer, &isOnline, &d.LastSeen, &d.LocationURL, &d.Source,
	)
	if err != nil {
		return nil
	}
	d.IsOnline = isOnline == 1
	return &d
}

func UpsertDevice(tx *sql.Tx, id, name, address, deviceType, manufacturer string, isOnline bool, lastSeen int64, locationURL, source string) (map[string]interface{}, error) {
	existing := _getDevice(tx, id)
	online := 0
	if isOnline {
		online = 1
	}
	if deviceType == "" {
		deviceType = "MediaRenderer"
	}
	if source == "" {
		source = "DISCOVERED"
	}
	if existing != nil {
		_, err := tx.Exec("UPDATE devices SET name = ?, address = ?, type = ?, manufacturer = ?, is_online = ?, last_seen = ?, location_url = ?, source = ? WHERE id = ?",
			name, address, deviceType, manufacturer, online, lastSeen, locationURL, source, id)
		if err != nil {
			return nil, err
		}
		return GetDevice(tx, id)
	}
	return CreateDevice(tx, id, name, address, deviceType, manufacturer, isOnline, lastSeen, locationURL, source)
}

func DeleteDevice(tx *sql.Tx, deviceID string) (bool, error) {
	res, err := tx.Exec("DELETE FROM devices WHERE id = ?", deviceID)
	if err != nil {
		return false, err
	}
	n, _ := res.RowsAffected()
	return n > 0, nil
}

// --- SMB Server CRUD ---
func smbToMap(s *SmbServer) map[string]interface{} {
	return map[string]interface{}{
		"id": s.ID, "name": s.Name, "host": s.Host, "port": s.Port, "protocol": s.Protocol,
		"username": s.Username, "password": s.Password, "share_path": s.SharePath,
		"is_connected": s.IsConnected, "last_connected_at": s.LastConnectedAt, "created_at": s.CreatedAt,
		"hostname": s.Hostname,
	}
}

func CreateSmbServer(tx *sql.Tx, name, host string, port int, protocol, username, password, sharePath string) (map[string]interface{}, error) {
	id := uuid.New().String()
	now := time.Now().UnixMilli()
	_, err := tx.Exec(
		`INSERT INTO smb_servers (id, name, host, port, protocol, username, password, share_path, is_connected, last_connected_at, created_at, hostname, last_known_host) VALUES (?,?,?,?,?,?,?,?,0,0,?,'','')`,
		id, name, host, port, protocol, username, password, sharePath, now,
	)
	if err != nil {
		return nil, err
	}
	return GetSmbServer(tx, id)
}

func GetSmbServer(tx *sql.Tx, serverID string) (map[string]interface{}, error) {
	var s SmbServer
	var isConnected int
	err := tx.QueryRow(`SELECT id, name, host, port, protocol, username, password, share_path, is_connected, last_connected_at, created_at, hostname FROM smb_servers WHERE id = ?`, serverID).Scan(
		&s.ID, &s.Name, &s.Host, &s.Port, &s.Protocol, &s.Username, &s.Password, &s.SharePath, &isConnected, &s.LastConnectedAt, &s.CreatedAt, &s.Hostname,
	)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	s.IsConnected = isConnected == 1
	return smbToMap(&s), nil
}

func GetSmbServers(tx *sql.Tx) ([]map[string]interface{}, error) {
	rows, err := tx.Query(`SELECT id, name, host, port, protocol, username, password, share_path, is_connected, last_connected_at, created_at, hostname FROM smb_servers`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []map[string]interface{}
	for rows.Next() {
		var s SmbServer
		var isConnected int
		if err := rows.Scan(&s.ID, &s.Name, &s.Host, &s.Port, &s.Protocol, &s.Username, &s.Password, &s.SharePath, &isConnected, &s.LastConnectedAt, &s.CreatedAt, &s.Hostname); err != nil {
			return nil, err
		}
		s.IsConnected = isConnected == 1
		out = append(out, smbToMap(&s))
	}
	return out, nil
}

func UpdateSmbServer(tx *sql.Tx, serverID string, updates map[string]interface{}) (map[string]interface{}, error) {
	_, err := GetSmbServer(tx, serverID)
	if err != nil || _getSmbServer(tx, serverID) == nil {
		return nil, nil
	}
	if v, ok := updates["name"]; ok {
		tx.Exec("UPDATE smb_servers SET name = ? WHERE id = ?", v, serverID)
	}
	if v, ok := updates["host"]; ok {
		tx.Exec("UPDATE smb_servers SET host = ? WHERE id = ?", v, serverID)
	}
	if v, ok := updates["port"]; ok {
		tx.Exec("UPDATE smb_servers SET port = ? WHERE id = ?", v, serverID)
	}
	if v, ok := updates["username"]; ok {
		tx.Exec("UPDATE smb_servers SET username = ? WHERE id = ?", v, serverID)
	}
	if v, ok := updates["password"]; ok {
		tx.Exec("UPDATE smb_servers SET password = ? WHERE id = ?", v, serverID)
	}
	if v, ok := updates["share_path"]; ok {
		tx.Exec("UPDATE smb_servers SET share_path = ? WHERE id = ?", v, serverID)
	}
	return GetSmbServer(tx, serverID)
}

func _getSmbServer(tx *sql.Tx, serverID string) *SmbServer {
	var s SmbServer
	var isConnected int
	err := tx.QueryRow(`SELECT id FROM smb_servers WHERE id = ?`, serverID).Scan(&s.ID)
	if err != nil {
		return nil
	}
	_ = tx.QueryRow(`SELECT id, name, host, port, protocol, username, password, share_path, is_connected, last_connected_at, created_at, hostname FROM smb_servers WHERE id = ?`, serverID).Scan(
		&s.ID, &s.Name, &s.Host, &s.Port, &s.Protocol, &s.Username, &s.Password, &s.SharePath, &isConnected, &s.LastConnectedAt, &s.CreatedAt, &s.Hostname,
	)
	return &s
}

func DeleteSmbServer(tx *sql.Tx, serverID string) (bool, error) {
	res, err := tx.Exec("DELETE FROM smb_servers WHERE id = ?", serverID)
	if err != nil {
		return false, err
	}
	n, _ := res.RowsAffected()
	return n > 0, nil
}

func UpdateSmbServerConnection(tx *sql.Tx, serverID string, connected bool) (map[string]interface{}, error) {
	if _getSmbServer(tx, serverID) == nil {
		return nil, nil
	}
	now := int64(0)
	if connected {
		now = time.Now().UnixMilli()
	}
	c := 0
	if connected {
		c = 1
	}
	_, err := tx.Exec("UPDATE smb_servers SET is_connected = ?, last_connected_at = ? WHERE id = ?", c, now, serverID)
	if err != nil {
		return nil, err
	}
	return GetSmbServer(tx, serverID)
}

// --- Playback History CRUD ---
func CreatePlaybackHistory(tx *sql.Tx, planID, planTitle, deviceID, deviceName, deviceAddress, mediaURL, mediaName string, mediaDuration int64, triggerType, networkType string) (map[string]interface{}, error) {
	id := uuid.New().String()
	now := time.Now().UnixMilli()
	_, err := tx.Exec(
		`INSERT INTO playback_history (id, plan_id, plan_title, device_id, device_name, device_address, media_url, media_name, media_duration, actual_start_time, trigger_type, network_type, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`,
		id, planID, planTitle, nullStr(deviceID), nullStr(deviceName), nullStr(deviceAddress), mediaURL, mediaName, mediaDuration, now, triggerType, networkType, now,
	)
	if err != nil {
		return nil, err
	}
	return GetPlaybackHistory(tx, id)
}

func GetPlaybackHistory(tx *sql.Tx, historyID string) (map[string]interface{}, error) {
	return scanPlaybackHistory(tx.QueryRow(`SELECT id, plan_id, plan_title, device_id, device_name, device_address, media_url, media_name, media_duration, actual_start_time, actual_end_time, played_duration, played_position, end_status, error_code, error_message, stop_reason, network_type, trigger_type, created_at FROM playback_history WHERE id = ?`, historyID))
}

func GetPlaybackHistories(tx *sql.Tx, skip, limit int, planID string) (total int, items []map[string]interface{}, err error) {
	if planID != "" {
		_ = tx.QueryRow("SELECT COUNT(*) FROM playback_history WHERE plan_id = ?", planID).Scan(&total)
		rows, qerr := tx.Query("SELECT id, plan_id, plan_title, device_id, device_name, device_address, media_url, media_name, media_duration, actual_start_time, actual_end_time, played_duration, played_position, end_status, error_code, error_message, stop_reason, network_type, trigger_type, created_at FROM playback_history WHERE plan_id = ? ORDER BY actual_start_time DESC LIMIT ? OFFSET ?", planID, limit, skip)
		if qerr != nil {
			return 0, nil, qerr
		}
		defer rows.Close()
		items, err = scanPlaybackHistoryRows(rows)
		return total, items, err
	}
	_ = tx.QueryRow("SELECT COUNT(*) FROM playback_history").Scan(&total)
	rows, qerr := tx.Query("SELECT id, plan_id, plan_title, device_id, device_name, device_address, media_url, media_name, media_duration, actual_start_time, actual_end_time, played_duration, played_position, end_status, error_code, error_message, stop_reason, network_type, trigger_type, created_at FROM playback_history ORDER BY actual_start_time DESC LIMIT ? OFFSET ?", limit, skip)
	if qerr != nil {
		return 0, nil, qerr
	}
	defer rows.Close()
	items, err = scanPlaybackHistoryRows(rows)
	return total, items, err
}

func scanPlaybackHistory(r *sql.Row) (map[string]interface{}, error) {
	var h PlaybackHistory
	err := r.Scan(&h.ID, &h.PlanID, &h.PlanTitle, &h.DeviceID, &h.DeviceName, &h.DeviceAddress, &h.MediaURL, &h.MediaName, &h.MediaDuration, &h.ActualStartTime, &h.ActualEndTime, &h.PlayedDuration, &h.PlayedPosition, &h.EndStatus, &h.ErrorCode, &h.ErrorMessage, &h.StopReason, &h.NetworkType, &h.TriggerType, &h.CreatedAt)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return historyToMap(&h), nil
}

func scanPlaybackHistoryRows(rows *sql.Rows) ([]map[string]interface{}, error) {
	var out []map[string]interface{}
	for rows.Next() {
		var h PlaybackHistory
		if err := rows.Scan(&h.ID, &h.PlanID, &h.PlanTitle, &h.DeviceID, &h.DeviceName, &h.DeviceAddress, &h.MediaURL, &h.MediaName, &h.MediaDuration, &h.ActualStartTime, &h.ActualEndTime, &h.PlayedDuration, &h.PlayedPosition, &h.EndStatus, &h.ErrorCode, &h.ErrorMessage, &h.StopReason, &h.NetworkType, &h.TriggerType, &h.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, historyToMap(&h))
	}
	return out, nil
}

func historyToMap(h *PlaybackHistory) map[string]interface{} {
	m := map[string]interface{}{
		"id": h.ID, "plan_id": h.PlanID, "plan_title": h.PlanTitle, "media_url": h.MediaURL, "media_name": h.MediaName,
		"media_duration": h.MediaDuration, "actual_start_time": h.ActualStartTime, "played_duration": h.PlayedDuration,
		"played_position": h.PlayedPosition, "end_status": h.EndStatus, "trigger_type": h.TriggerType, "created_at": h.CreatedAt,
	}
	if h.DeviceID.Valid {
		m["device_id"] = h.DeviceID.String
	} else {
		m["device_id"] = nil
	}
	if h.DeviceName.Valid {
		m["device_name"] = h.DeviceName.String
	} else {
		m["device_name"] = nil
	}
	if h.DeviceAddress.Valid {
		m["device_address"] = h.DeviceAddress.String
	} else {
		m["device_address"] = nil
	}
	if h.ActualEndTime.Valid {
		m["actual_end_time"] = h.ActualEndTime.Int64
	} else {
		m["actual_end_time"] = nil
	}
	if h.ErrorCode.Valid {
		m["error_code"] = h.ErrorCode.String
	} else {
		m["error_code"] = nil
	}
	if h.ErrorMessage.Valid {
		m["error_message"] = h.ErrorMessage.String
	} else {
		m["error_message"] = nil
	}
	if h.StopReason.Valid {
		m["stop_reason"] = h.StopReason.String
	} else {
		m["stop_reason"] = nil
	}
	if h.NetworkType.Valid {
		m["network_type"] = h.NetworkType.String
	} else {
		m["network_type"] = nil
	}
	return m
}

func UpdatePlaybackHistoryProgress(tx *sql.Tx, historyID string, playedDuration, playedPosition int64) (map[string]interface{}, error) {
	if _, err := GetPlaybackHistory(tx, historyID); err != nil {
		return nil, err
	}
	_, err := tx.Exec("UPDATE playback_history SET played_duration = ?, played_position = ? WHERE id = ?", playedDuration, playedPosition, historyID)
	if err != nil {
		return nil, err
	}
	return GetPlaybackHistory(tx, historyID)
}

func EndPlaybackHistory(tx *sql.Tx, historyID string, playedDuration, playedPosition int64, completed bool, errorCode, errorMessage, stopReason string) (map[string]interface{}, error) {
	h, err := GetPlaybackHistory(tx, historyID)
	if err != nil || h == nil {
		return nil, nil
	}
	now := time.Now().UnixMilli()
	status := "STOPPED"
	if errorCode != "" {
		status = "ERROR"
	} else if completed {
		status = "COMPLETED"
	}
	_, err = tx.Exec(
		`UPDATE playback_history SET actual_end_time = ?, played_duration = ?, played_position = ?, end_status = ?, error_code = ?, error_message = ?, stop_reason = ? WHERE id = ?`,
		now, playedDuration, playedPosition, status, nullStr(errorCode), nullStr(errorMessage), nullStr(stopReason), historyID,
	)
	if err != nil {
		return nil, err
	}
	return GetPlaybackHistory(tx, historyID)
}

func DeletePlaybackHistory(tx *sql.Tx, historyID string) (bool, error) {
	res, err := tx.Exec("DELETE FROM playback_history WHERE id = ?", historyID)
	if err != nil {
		return false, err
	}
	n, _ := res.RowsAffected()
	return n > 0, nil
}

func ClearPlaybackHistory(tx *sql.Tx) (int64, error) {
	res, err := tx.Exec("DELETE FROM playback_history")
	if err != nil {
		return 0, err
	}
	return res.RowsAffected()
}

// --- Study Task CRUD ---
func CreateStudyTask(tx *sql.Tx, name string, mediaItems []StudyTaskMediaCreate) (map[string]interface{}, error) {
	tid := uuid.New().String()
	now := time.Now().UnixMilli()
	_, err := tx.Exec("INSERT INTO study_tasks (id, name, total_duration, watched_duration, created_at, updated_at) VALUES (?,?,0,0,?,?)", tid, name, now, now)
	if err != nil {
		return nil, err
	}
	totalDuration := int64(0)
	for i, m := range mediaItems {
		mid := uuid.New().String()
		so := m.SortOrder
		if so < 0 {
			so = i
		}
		totalDuration += m.Duration
		_, err = tx.Exec(
			`INSERT INTO study_task_media (id, study_task_id, media_uri, media_name, duration, sort_order, source_type, server_id) VALUES (?,?,?,?,?,?,?,?)`,
			mid, tid, m.MediaURI, m.MediaName, m.Duration, so, m.SourceType, nullStr(m.ServerID),
		)
		if err != nil {
			return nil, err
		}
	}
	_, err = tx.Exec("UPDATE study_tasks SET total_duration = ? WHERE id = ?", totalDuration, tid)
	if err != nil {
		return nil, err
	}
	return GetStudyTask(tx, tid)
}

type StudyTaskMediaCreate struct {
	MediaURI   string
	MediaName  string
	Duration   int64
	SortOrder  int
	SourceType string
	ServerID   string
}

func GetStudyTask(tx *sql.Tx, taskID string) (map[string]interface{}, error) {
	var t StudyTask
	err := tx.QueryRow("SELECT id, name, total_duration, watched_duration, created_at, updated_at FROM study_tasks WHERE id = ?", taskID).Scan(
		&t.ID, &t.Name, &t.TotalDuration, &t.WatchedDuration, &t.CreatedAt, &t.UpdatedAt,
	)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	m := map[string]interface{}{
		"id": t.ID, "name": t.Name, "total_duration": t.TotalDuration, "watched_duration": t.WatchedDuration,
		"created_at": t.CreatedAt, "updated_at": t.UpdatedAt, "media_items": []map[string]interface{}{},
	}
	rows, err := tx.Query("SELECT id, study_task_id, media_uri, media_name, duration, sort_order, source_type, server_id, thumbnail_path FROM study_task_media WHERE study_task_id = ? ORDER BY sort_order", taskID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var sm StudyTaskMedia
		if err := rows.Scan(&sm.ID, &sm.StudyTaskID, &sm.MediaURI, &sm.MediaName, &sm.Duration, &sm.SortOrder, &sm.SourceType, &sm.ServerID, &sm.ThumbnailPath); err != nil {
			return nil, err
		}
		m["media_items"] = append(m["media_items"].([]map[string]interface{}), studyTaskMediaToMap(&sm))
	}
	return m, nil
}

func studyTaskMediaToMap(sm *StudyTaskMedia) map[string]interface{} {
	m := map[string]interface{}{
		"id": sm.ID, "study_task_id": sm.StudyTaskID, "media_uri": sm.MediaURI, "media_name": sm.MediaName,
		"duration": sm.Duration, "sort_order": sm.SortOrder, "source_type": sm.SourceType,
	}
	if sm.ServerID.Valid {
		m["server_id"] = sm.ServerID.String
	} else {
		m["server_id"] = nil
	}
	if sm.ThumbnailPath.Valid {
		m["thumbnail_path"] = sm.ThumbnailPath.String
	} else {
		m["thumbnail_path"] = nil
	}
	return m
}

func GetStudyTasks(tx *sql.Tx) ([]map[string]interface{}, error) {
	rows, err := tx.Query("SELECT id, name, total_duration, watched_duration, created_at, updated_at FROM study_tasks ORDER BY updated_at DESC")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []map[string]interface{}
	for rows.Next() {
		var t StudyTask
		if err := rows.Scan(&t.ID, &t.Name, &t.TotalDuration, &t.WatchedDuration, &t.CreatedAt, &t.UpdatedAt); err != nil {
			return nil, err
		}
		taskMap, err := GetStudyTask(tx, t.ID)
		if err != nil {
			return nil, err
		}
		out = append(out, taskMap)
	}
	return out, nil
}

func UpdateStudyTask(tx *sql.Tx, taskID, name string) (map[string]interface{}, error) {
	if _getStudyTask(tx, taskID) == nil {
		return nil, nil
	}
	now := time.Now().UnixMilli()
	_, err := tx.Exec("UPDATE study_tasks SET name = ?, updated_at = ? WHERE id = ?", name, now, taskID)
	if err != nil {
		return nil, err
	}
	return GetStudyTask(tx, taskID)
}

func _getStudyTask(tx *sql.Tx, taskID string) *StudyTask {
	var t StudyTask
	err := tx.QueryRow("SELECT id FROM study_tasks WHERE id = ?", taskID).Scan(&t.ID)
	if err != nil {
		return nil
	}
	return &t
}

func DeleteStudyTask(tx *sql.Tx, taskID string) (bool, error) {
	res, err := tx.Exec("DELETE FROM study_tasks WHERE id = ?", taskID)
	if err != nil {
		return false, err
	}
	n, _ := res.RowsAffected()
	return n > 0, nil
}

func ResetStudyTaskProgress(tx *sql.Tx, taskID string) (map[string]interface{}, error) {
	if _getStudyTask(tx, taskID) == nil {
		return nil, nil
	}
	now := time.Now().UnixMilli()
	_, err := tx.Exec("UPDATE study_tasks SET watched_duration = 0, updated_at = ? WHERE id = ?", now, taskID)
	if err != nil {
		return nil, err
	}
	return GetStudyTask(tx, taskID)
}

func AddStudyTaskMedia(tx *sql.Tx, taskID string, m StudyTaskMediaCreate) (map[string]interface{}, error) {
	if _getStudyTask(tx, taskID) == nil {
		return nil, nil
	}
	var count int
	_ = tx.QueryRow("SELECT COUNT(*) FROM study_task_media WHERE study_task_id = ?", taskID).Scan(&count)
	so := m.SortOrder
	if so < 0 {
		so = count
	}
	mid := uuid.New().String()
	_, err := tx.Exec(
		`INSERT INTO study_task_media (id, study_task_id, media_uri, media_name, duration, sort_order, source_type, server_id) VALUES (?,?,?,?,?,?,?,?)`,
		mid, taskID, m.MediaURI, m.MediaName, m.Duration, so, m.SourceType, nullStr(m.ServerID),
	)
	if err != nil {
		return nil, err
	}
	task, _ := GetStudyTask(tx, taskID)
	if task != nil {
		curTotal, _ := task["total_duration"].(int64)
		now := time.Now().UnixMilli()
		tx.Exec("UPDATE study_tasks SET total_duration = ?, updated_at = ? WHERE id = ?", curTotal+m.Duration, now, taskID)
	}
	row := tx.QueryRow("SELECT id, study_task_id, media_uri, media_name, duration, sort_order, source_type, server_id, thumbnail_path FROM study_task_media WHERE id = ?", mid)
	var sm StudyTaskMedia
	_ = row.Scan(&sm.ID, &sm.StudyTaskID, &sm.MediaURI, &sm.MediaName, &sm.Duration, &sm.SortOrder, &sm.SourceType, &sm.ServerID, &sm.ThumbnailPath)
	return studyTaskMediaToMap(&sm), nil
}

func RemoveStudyTaskMedia(tx *sql.Tx, taskID, mediaID string) (bool, error) {
	var duration int64
	err := tx.QueryRow("SELECT duration FROM study_task_media WHERE id = ? AND study_task_id = ?", mediaID, taskID).Scan(&duration)
	if err == sql.ErrNoRows {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	_, err = tx.Exec("DELETE FROM study_task_media WHERE id = ? AND study_task_id = ?", mediaID, taskID)
	if err != nil {
		return false, err
	}
	task, _ := GetStudyTask(tx, taskID)
	if task != nil {
		curTotal, _ := task["total_duration"].(int64)
		newTotal := curTotal - duration
		if newTotal < 0 {
			newTotal = 0
		}
		now := time.Now().UnixMilli()
		tx.Exec("UPDATE study_tasks SET total_duration = ?, updated_at = ? WHERE id = ?", newTotal, now, taskID)
	}
	return true, nil
}

func LinkPlanStudyTask(tx *sql.Tx, planID, studyTaskID string, sortOrder int) (map[string]interface{}, error) {
	var x string
	err := tx.QueryRow("SELECT id FROM plan_study_tasks WHERE plan_id = ? AND study_task_id = ?", planID, studyTaskID).Scan(&x)
	if err == nil {
		return map[string]interface{}{"id": x, "plan_id": planID, "study_task_id": studyTaskID, "sort_order": sortOrder}, nil
	}
	lid := uuid.New().String()
	_, err = tx.Exec("INSERT INTO plan_study_tasks (id, plan_id, study_task_id, sort_order) VALUES (?,?,?,?)", lid, planID, studyTaskID, sortOrder)
	if err != nil {
		return nil, err
	}
	return map[string]interface{}{"id": lid, "plan_id": planID, "study_task_id": studyTaskID, "sort_order": sortOrder}, nil
}

func UnlinkPlanStudyTask(tx *sql.Tx, planID, studyTaskID string) (bool, error) {
	res, err := tx.Exec("DELETE FROM plan_study_tasks WHERE plan_id = ? AND study_task_id = ?", planID, studyTaskID)
	if err != nil {
		return false, err
	}
	n, _ := res.RowsAffected()
	return n > 0, nil
}

func ReplacePlanStudyTasks(tx *sql.Tx, planID string, studyTaskIDs []string) error {
	if _getPlan(tx, planID) == nil {
		return ErrPlanNotFound
	}

	uniqueIDs := make([]string, 0, len(studyTaskIDs))
	seen := make(map[string]struct{}, len(studyTaskIDs))
	for _, taskID := range studyTaskIDs {
		if taskID == "" {
			return fmt.Errorf("%w: empty id", ErrStudyTaskNotFound)
		}
		if _, ok := seen[taskID]; ok {
			continue
		}
		seen[taskID] = struct{}{}

		if _getStudyTask(tx, taskID) == nil {
			return fmt.Errorf("%w: %s", ErrStudyTaskNotFound, taskID)
		}
		uniqueIDs = append(uniqueIDs, taskID)
	}

	if _, err := tx.Exec("DELETE FROM plan_study_tasks WHERE plan_id = ?", planID); err != nil {
		return err
	}

	for sortOrder, taskID := range uniqueIDs {
		if _, err := tx.Exec(
			"INSERT INTO plan_study_tasks (id, plan_id, study_task_id, sort_order) VALUES (?,?,?,?)",
			uuid.New().String(),
			planID,
			taskID,
			sortOrder,
		); err != nil {
			return err
		}
	}

	return nil
}

func GetPlanStudyTasks(tx *sql.Tx, planID string) ([]map[string]interface{}, error) {
	rows, err := tx.Query("SELECT s.id, s.name, s.total_duration, s.watched_duration, s.created_at, s.updated_at FROM study_tasks s JOIN plan_study_tasks p ON s.id = p.study_task_id WHERE p.plan_id = ? ORDER BY p.sort_order", planID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []map[string]interface{}
	for rows.Next() {
		var t StudyTask
		if err := rows.Scan(&t.ID, &t.Name, &t.TotalDuration, &t.WatchedDuration, &t.CreatedAt, &t.UpdatedAt); err != nil {
			return nil, err
		}
		taskMap, _ := GetStudyTask(tx, t.ID)
		if taskMap != nil {
			out = append(out, taskMap)
		}
	}
	return out, nil
}

func GetPlanMediaPlaylist(tx *sql.Tx, planID string) ([]map[string]interface{}, error) {
	tasks, err := GetPlanStudyTasks(tx, planID)
	if err != nil {
		return nil, err
	}
	var mediaList []map[string]interface{}
	for _, task := range tasks {
		tid, _ := task["id"].(string)
		rows, err := tx.Query("SELECT id, study_task_id, media_uri, media_name, duration, sort_order, source_type, server_id, thumbnail_path FROM study_task_media WHERE study_task_id = ? ORDER BY sort_order", tid)
		if err != nil {
			return nil, err
		}
		for rows.Next() {
			var sm StudyTaskMedia
			if err := rows.Scan(&sm.ID, &sm.StudyTaskID, &sm.MediaURI, &sm.MediaName, &sm.Duration, &sm.SortOrder, &sm.SourceType, &sm.ServerID, &sm.ThumbnailPath); err != nil {
				rows.Close()
				return nil, err
			}
			mediaList = append(mediaList, studyTaskMediaToMap(&sm))
		}
		rows.Close()
	}
	return mediaList, nil
}
