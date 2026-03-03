package services

import (
	"context"
	"fmt"
	"net/url"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/huin/goupnp/dcps/av1"
)

type DlnaDevice struct {
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

type DlnaManager struct {
	mu      sync.RWMutex
	devices map[string]*DlnaDevice
}

func NewDlnaManager() *DlnaManager {
	return &DlnaManager{devices: make(map[string]*DlnaDevice)}
}

func (m *DlnaManager) StartDiscovery(ctx context.Context, timeout time.Duration) ([]*DlnaDevice, error) {
	// Use goupnp av1 to discover AVTransport (MediaRenderer) clients
	ctx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()
	clients, errs, err := av1.NewAVTransport1ClientsCtx(ctx)
	if err != nil {
		return m.Devices(), err
	}
	seen := make(map[string]struct{})
	for i, client := range clients {
		if errs != nil && i < len(errs) && errs[i] != nil {
			continue
		}
		loc := client.Location
		if loc == nil {
			continue
		}
		locStr := loc.String()
		if _, ok := seen[locStr]; ok {
			continue
		}
		seen[locStr] = struct{}{}
		root := client.RootDevice
		if root == nil {
			continue
		}
		dev := &root.Device
		name := strings.TrimSpace(dev.FriendlyName)
		if name == "" {
			name = "MediaRenderer"
		}
		udn := strings.TrimSpace(dev.UDN)
		if udn == "" {
			udn = "uuid:" + locStr
		}
		addr := loc.Hostname()
		if addr == "" {
			addr = "unknown"
		}
		d := &DlnaDevice{
			ID:           udn,
			Name:         name,
			Address:      addr,
			Type:         "MediaRenderer",
			Manufacturer: strings.TrimSpace(dev.Manufacturer),
			IsOnline:     true,
			LastSeen:     time.Now().UnixMilli(),
			LocationURL:  locStr,
			Source:       "DISCOVERED",
		}
		m.mu.Lock()
		m.devices[d.ID] = d
		m.mu.Unlock()
	}
	return m.Devices(), nil
}

func (m *DlnaManager) AddDeviceManually(ctx context.Context, address string, port int) (*DlnaDevice, error) {
	if port <= 0 {
		port = 9197
	}
	locStr := "http://" + address + ":" + strconv.Itoa(port) + "/"
	loc, err := url.Parse(locStr)
	if err != nil {
		return nil, err
	}
	clients, err := av1.NewAVTransport1ClientsByURLCtx(ctx, loc)
	if err != nil || len(clients) == 0 {
		d := &DlnaDevice{ID: "manual-" + address, Name: "MediaRenderer", Address: address, Type: "MediaRenderer", IsOnline: true, LastSeen: time.Now().UnixMilli(), LocationURL: locStr, Source: "MANUAL"}
		m.PutDevice(d)
		return d, nil
	}
	avClient := clients[0]
	root := avClient.RootDevice
	if root == nil {
		d := &DlnaDevice{ID: "manual-" + address, Name: "MediaRenderer", Address: address, Type: "MediaRenderer", IsOnline: true, LastSeen: time.Now().UnixMilli(), LocationURL: locStr, Source: "MANUAL"}
		m.PutDevice(d)
		return d, nil
	}
	dev := &root.Device
	name := strings.TrimSpace(dev.FriendlyName)
	if name == "" {
		name = "MediaRenderer"
	}
	udn := strings.TrimSpace(dev.UDN)
	if udn == "" {
		udn = "manual-" + address
	}
	d := &DlnaDevice{
		ID:           udn,
		Name:         name,
		Address:      address,
		Type:         "MediaRenderer",
		Manufacturer: strings.TrimSpace(dev.Manufacturer),
		IsOnline:     true,
		LastSeen:     time.Now().UnixMilli(),
		LocationURL:  locStr,
		Source:       "MANUAL",
	}
	m.PutDevice(d)
	return d, nil
}

func (m *DlnaManager) Devices() []*DlnaDevice {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]*DlnaDevice, 0, len(m.devices))
	for _, d := range m.devices {
		out = append(out, d)
	}
	return out
}

func (m *DlnaManager) GetDevice(id string) *DlnaDevice {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.devices[id]
}

func (m *DlnaManager) PutDevice(d *DlnaDevice) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.devices[d.ID] = d
}

func (m *DlnaManager) RemoveDevice(id string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.devices, id)
}

func (m *DlnaManager) CheckDeviceOnline(ctx context.Context, deviceID string) (bool, error) {
	d := m.GetDevice(deviceID)
	if d == nil {
		return false, nil
	}
	loc, err := url.Parse(d.LocationURL)
	if err != nil {
		return false, nil
	}
	clients, err := av1.NewAVTransport1ClientsByURLCtx(ctx, loc)
	if err != nil || len(clients) == 0 {
		return false, nil
	}
	return true, nil
}

const avTransportInstanceID = 0
const renderingControlInstanceID = 0
const renderingControlChannel = "Master"

func (m *DlnaManager) getAVTransportClient(deviceID string) (*av1.AVTransport1, error) {
	d := m.GetDevice(deviceID)
	if d == nil {
		return nil, fmt.Errorf("device not found: %s", deviceID)
	}
	loc, err := url.Parse(d.LocationURL)
	if err != nil {
		return nil, err
	}
	clients, err := av1.NewAVTransport1ClientsByURLCtx(context.Background(), loc)
	if err != nil || len(clients) == 0 {
		return nil, fmt.Errorf("no AVTransport client: %w", err)
	}
	return clients[0], nil
}

func (m *DlnaManager) getRenderingControlClient(deviceID string) (*av1.RenderingControl1, error) {
	d := m.GetDevice(deviceID)
	if d == nil {
		return nil, fmt.Errorf("device not found: %s", deviceID)
	}
	loc, err := url.Parse(d.LocationURL)
	if err != nil {
		return nil, err
	}
	clients, err := av1.NewRenderingControl1ClientsByURLCtx(context.Background(), loc)
	if err != nil || len(clients) == 0 {
		return nil, fmt.Errorf("no RenderingControl client: %w", err)
	}
	return clients[0], nil
}

func (m *DlnaManager) SetAVTransportURI(ctx context.Context, deviceID, uri, meta string) error {
	client, err := m.getAVTransportClient(deviceID)
	if err != nil {
		return err
	}
	return client.SetAVTransportURICtx(ctx, avTransportInstanceID, uri, meta)
}

func (m *DlnaManager) Play(ctx context.Context, deviceID string) error {
	client, err := m.getAVTransportClient(deviceID)
	if err != nil {
		return err
	}
	return client.PlayCtx(ctx, avTransportInstanceID, "1")
}

func (m *DlnaManager) Pause(ctx context.Context, deviceID string) error {
	client, err := m.getAVTransportClient(deviceID)
	if err != nil {
		return err
	}
	return client.PauseCtx(ctx, avTransportInstanceID)
}

func (m *DlnaManager) Stop(ctx context.Context, deviceID string) error {
	client, err := m.getAVTransportClient(deviceID)
	if err != nil {
		return err
	}
	return client.StopCtx(ctx, avTransportInstanceID)
}

// parseUPnPTime converts "H:MM:SS" or "HH:MM:SS" to seconds.
func parseUPnPTime(s string) int {
	s = strings.TrimSpace(s)
	if s == "" || s == "NOT_IMPLEMENTED" {
		return 0
	}
	var h, m, sec int
	n, _ := fmt.Sscanf(s, "%d:%d:%d", &h, &m, &sec)
	if n < 3 {
		return 0
	}
	return h*3600 + m*60 + sec
}

// formatUPnPTime converts seconds to "H:MM:SS".
func formatUPnPTime(seconds int) string {
	if seconds < 0 {
		seconds = 0
	}
	h := seconds / 3600
	m := (seconds % 3600) / 60
	s := seconds % 60
	return fmt.Sprintf("%d:%02d:%02d", h, m, s)
}

func (m *DlnaManager) GetPositionInfo(ctx context.Context, deviceID string) (position, duration int, err error) {
	client, err := m.getAVTransportClient(deviceID)
	if err != nil {
		return 0, 0, err
	}
	_, trackDuration, _, _, relTime, _, _, _, err := client.GetPositionInfoCtx(ctx, avTransportInstanceID)
	if err != nil {
		return 0, 0, err
	}
	return parseUPnPTime(relTime), parseUPnPTime(trackDuration), nil
}

func (m *DlnaManager) SetVolume(ctx context.Context, deviceID string, level int) error {
	if level < 0 {
		level = 0
	}
	if level > 100 {
		level = 100
	}
	client, err := m.getRenderingControlClient(deviceID)
	if err != nil {
		return err
	}
	return client.SetVolumeCtx(ctx, renderingControlInstanceID, renderingControlChannel, uint16(level))
}

func (m *DlnaManager) GetVolume(ctx context.Context, deviceID string) (int, error) {
	client, err := m.getRenderingControlClient(deviceID)
	if err != nil {
		return 50, err
	}
	v, err := client.GetVolumeCtx(ctx, renderingControlInstanceID, renderingControlChannel)
	if err != nil {
		return 50, err
	}
	return int(v), nil
}

func (m *DlnaManager) Seek(ctx context.Context, deviceID string, position int) error {
	client, err := m.getAVTransportClient(deviceID)
	if err != nil {
		return err
	}
	target := formatUPnPTime(position)
	return client.SeekCtx(ctx, avTransportInstanceID, "REL_TIME", target)
}
