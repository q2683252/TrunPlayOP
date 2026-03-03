package services

import (
	"context"
	"database/sql"
	"net/url"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"github.com/trunplay/trunplay-backend/internal/db"
)

type PlaybackStatus string

const (
	PlaybackStopped PlaybackStatus = "STOPPED"
	PlaybackLoading PlaybackStatus = "LOADING"
	PlaybackPlaying PlaybackStatus = "PLAYING"
	PlaybackPaused  PlaybackStatus = "PAUSED"
	PlaybackError   PlaybackStatus = "ERROR"
)

type PlaybackInfo struct {
	Status     PlaybackStatus
	DeviceID   string
	DeviceName string
	PlanID     string
	PlanTitle  string
	MediaURL   string
	MediaName  string
	Position   int
	Duration   int
	Volume     int
}

type PlaybackService struct {
	mu               sync.RWMutex
	dlna             *DlnaManager
	media            *MediaServer
	smb              *SmbClient
	db               *sql.DB
	status           PlaybackStatus
	deviceID         string
	planID           string
	planTitle        string
	mediaURL         string
	mediaName        string
	currentMediaID   string
	currentHistoryID string
	position         int
	duration         int
	volume           int
}

func NewPlaybackService(dlna *DlnaManager, media *MediaServer, smb *SmbClient, db *sql.DB) *PlaybackService {
	return &PlaybackService{
		dlna:   dlna,
		media:  media,
		smb:    smb,
		db:     db,
		status: PlaybackStopped,
		volume: 50,
	}
}

func (p *PlaybackService) GetPlaybackInfo() PlaybackInfo {
	p.mu.RLock()
	defer p.mu.RUnlock()
	deviceName := ""
	if p.deviceID != "" {
		if d := p.dlna.GetDevice(p.deviceID); d != nil {
			deviceName = d.Name
		}
	}
	return PlaybackInfo{
		Status:     p.status,
		DeviceID:   p.deviceID,
		DeviceName: deviceName,
		PlanID:     p.planID,
		PlanTitle:  p.planTitle,
		MediaURL:   p.mediaURL,
		MediaName:  p.mediaName,
		Position:   p.position,
		Duration:   p.duration,
		Volume:     p.volume,
	}
}

func smbPortFromMap(server map[string]interface{}) int {
	if server == nil {
		return 445
	}
	switch v := server["port"].(type) {
	case int:
		if v > 0 {
			return v
		}
	case int64:
		if v > 0 {
			return int(v)
		}
	case float64:
		if v > 0 {
			return int(v)
		}
	}
	return 445
}

func (p *PlaybackService) StartPlayback(ctx context.Context, tx *sql.Tx, plan map[string]interface{}, triggerType string, startPosition int) (bool, error) {
	planID, _ := plan["id"].(string)
	planTitle, _ := plan["title"].(string)
	mediaURL, _ := plan["media_url"].(string)
	mediaName, _ := plan["media_name"].(string)
	if mediaName == "" {
		mediaName = planTitle
	}
	var deviceID string
	if v, ok := plan["device_id"].(string); ok && v != "" {
		deviceID = v
	}
	if deviceID == "" {
		return false, nil
	}
	ok, _ := p.dlna.CheckDeviceOnline(ctx, deviceID)
	if !ok {
		return false, nil
	}
	var mediaID, filename, streamURL string
	networkType := "LOCAL"
	if strings.HasPrefix(mediaURL, "file://") {
		path := strings.TrimPrefix(mediaURL, "file://")
		filename = filepath.Base(path)
		var err error
		mediaID, err = p.media.RegisterLocalMedia(path, filename)
		if err != nil {
			return false, err
		}
	} else if strings.HasPrefix(mediaURL, "smb://") {
		rest := strings.TrimPrefix(mediaURL, "smb://")
		parts := strings.SplitN(rest, "/", 2)
		if len(parts) < 2 {
			return false, nil
		}
		serverID := parts[0]
		pathOnShare := parts[1]
		server, err := db.GetSmbServer(tx, serverID)
		if err != nil || server == nil {
			return false, err
		}
		host, _ := server["host"].(string)
		port := smbPortFromMap(server)
		username, _ := server["username"].(string)
		password, _ := server["password"].(string)
		sharePath, _ := server["share_path"].(string)
		filename = filepath.Base(pathOnShare)
		mediaID, err = p.media.RegisterSmbMedia(pathOnShare, filename, 0, host, port, username, password, sharePath)
		if err != nil {
			return false, err
		}
		networkType = "SMB"
	} else {
		return false, nil
	}
	baseURL := "http://" + p.media.GetLocalIP() + ":" + strconv.Itoa(p.media.Port()) + "/stream/" + url.PathEscape(mediaID) + "/" + url.PathEscape(filename)
	streamURL = baseURL
	meta := ""
	if err := p.dlna.SetAVTransportURI(ctx, deviceID, streamURL, meta); err != nil {
		p.media.UnregisterMedia(mediaID)
		return false, err
	}
	if err := p.dlna.Play(ctx, deviceID); err != nil {
		p.media.UnregisterMedia(mediaID)
		return false, err
	}
	dev := p.dlna.GetDevice(deviceID)
	deviceName := ""
	deviceAddress := ""
	if dev != nil {
		deviceName = dev.Name
		deviceAddress = dev.Address
	}
	history, err := db.CreatePlaybackHistory(tx, planID, planTitle, deviceID, deviceName, deviceAddress, streamURL, mediaName, 0, triggerType, networkType)
	if err != nil {
		p.media.UnregisterMedia(mediaID)
		return false, err
	}
	historyID, _ := history["id"].(string)
	if startPosition > 0 {
		_ = p.dlna.Seek(ctx, deviceID, startPosition)
	}
	pos, dur, _ := p.dlna.GetPositionInfo(ctx, deviceID)
	p.mu.Lock()
	p.status = PlaybackPlaying
	p.deviceID = deviceID
	p.planID = planID
	p.planTitle = planTitle
	p.mediaURL = streamURL
	p.mediaName = mediaName
	p.currentMediaID = mediaID
	p.currentHistoryID = historyID
	p.position = pos
	p.duration = dur
	p.mu.Unlock()
	return true, nil
}

func (p *PlaybackService) StopPlayback(ctx context.Context, tx *sql.Tx) error {
	p.mu.Lock()
	deviceID := p.deviceID
	mediaID := p.currentMediaID
	historyID := p.currentHistoryID
	p.mu.Unlock()
	if deviceID != "" {
		_ = p.dlna.Stop(ctx, deviceID)
	}
	if mediaID != "" {
		p.media.UnregisterMedia(mediaID)
	}
	if historyID != "" && tx != nil {
		pos, dur, _ := p.dlna.GetPositionInfo(ctx, deviceID)
		_, _ = db.EndPlaybackHistory(tx, historyID, int64(dur), int64(pos), false, "", "", "USER_STOP")
	}
	p.mu.Lock()
	p.status = PlaybackStopped
	p.deviceID = ""
	p.planID = ""
	p.planTitle = ""
	p.mediaURL = ""
	p.mediaName = ""
	p.currentMediaID = ""
	p.currentHistoryID = ""
	p.position = 0
	p.duration = 0
	p.mu.Unlock()
	return nil
}

func (p *PlaybackService) Pause(ctx context.Context) (bool, error) {
	p.mu.RLock()
	deviceID := p.deviceID
	p.mu.RUnlock()
	if deviceID == "" {
		return false, nil
	}
	if err := p.dlna.Pause(ctx, deviceID); err != nil {
		return false, err
	}
	p.mu.Lock()
	p.status = PlaybackPaused
	p.mu.Unlock()
	return true, nil
}

func (p *PlaybackService) Resume(ctx context.Context) (bool, error) {
	p.mu.RLock()
	deviceID := p.deviceID
	p.mu.RUnlock()
	if deviceID == "" {
		return false, nil
	}
	if err := p.dlna.Play(ctx, deviceID); err != nil {
		return false, err
	}
	p.mu.Lock()
	p.status = PlaybackPlaying
	p.mu.Unlock()
	return true, nil
}

func (p *PlaybackService) Seek(ctx context.Context, position int) (bool, error) {
	p.mu.RLock()
	deviceID := p.deviceID
	p.mu.RUnlock()
	if deviceID == "" {
		return false, nil
	}
	if err := p.dlna.Seek(ctx, deviceID, position); err != nil {
		return false, err
	}
	p.mu.Lock()
	p.position = position
	p.mu.Unlock()
	return true, nil
}

func (p *PlaybackService) SetVolume(ctx context.Context, level int) (bool, error) {
	if level < 0 {
		level = 0
	}
	if level > 100 {
		level = 100
	}
	p.mu.RLock()
	deviceID := p.deviceID
	p.mu.RUnlock()
	if deviceID != "" {
		if err := p.dlna.SetVolume(ctx, deviceID, level); err != nil {
			return false, err
		}
	}
	p.mu.Lock()
	p.volume = level
	p.mu.Unlock()
	return true, nil
}

func (p *PlaybackService) GetVolume(ctx context.Context) (int, error) {
	p.mu.RLock()
	deviceID := p.deviceID
	p.mu.RUnlock()
	if deviceID != "" {
		if v, err := p.dlna.GetVolume(ctx, deviceID); err == nil {
			p.mu.Lock()
			p.volume = v
			p.mu.Unlock()
			return v, nil
		}
	}
	p.mu.RLock()
	v := p.volume
	p.mu.RUnlock()
	return v, nil
}

func (p *PlaybackService) GetPositionInfo(ctx context.Context) (position, duration int, err error) {
	p.mu.RLock()
	deviceID := p.deviceID
	p.mu.RUnlock()
	if deviceID != "" {
		if pos, dur, err := p.dlna.GetPositionInfo(ctx, deviceID); err == nil {
			p.mu.Lock()
			p.position = pos
			p.duration = dur
			p.mu.Unlock()
			return pos, dur, nil
		}
	}
	p.mu.RLock()
	position, duration = p.position, p.duration
	p.mu.RUnlock()
	return position, duration, nil
}
