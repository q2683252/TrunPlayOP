package services

import (
	"context"
	"io"
	"net"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/hirochachacha/go-smb2"
)

type SmbShareInfo struct {
	Name string
	Path string
}

type SmbFileItem struct {
	ID           string
	Name         string
	Path         string
	URI          string
	Type         string
	SourceType   string
	ServerID     string
	Size         int64
	LastModified int64
}

type SmbClient struct {
	mu sync.RWMutex
}

func NewSmbClient() *SmbClient {
	return &SmbClient{}
}

func (c *SmbClient) TestConnection(ctx context.Context, host string, port int, username, password string) (bool, string) {
	addr := net.JoinHostPort(host, portStr(port))
	conn, err := net.DialTimeout("tcp", addr, 5*time.Second)
	if err != nil {
		return false, err.Error()
	}
	defer conn.Close()
	d := &smb2.Dialer{
		Initiator: &smb2.NTLMInitiator{
			User:     username,
			Password: password,
		},
	}
	s, err := d.Dial(conn)
	if err != nil {
		return false, err.Error()
	}
	defer s.Logoff()
	return true, "OK"
}

func portStr(port int) string {
	if port <= 0 {
		return "445"
	}
	return strconv.Itoa(port)
}

func (c *SmbClient) ListShares(ctx context.Context, host string, port int, username, password string) ([]SmbShareInfo, error) {
	addr := net.JoinHostPort(host, portStr(port))
	conn, err := net.DialTimeout("tcp", addr, 10*time.Second)
	if err != nil {
		return nil, err
	}
	defer conn.Close()
	d := &smb2.Dialer{
		Initiator: &smb2.NTLMInitiator{
			User:     username,
			Password: password,
		},
	}
	s, err := d.Dial(conn)
	if err != nil {
		return nil, err
	}
	defer s.Logoff()
	names, err := s.ListSharenames()
	if err != nil {
		return nil, err
	}
	out := make([]SmbShareInfo, 0, len(names))
	for _, n := range names {
		out = append(out, SmbShareInfo{Name: n, Path: n})
	}
	return out, nil
}

func (c *SmbClient) ListFiles(ctx context.Context, serverID, host string, port int, username, password, sharePath, path string) ([]SmbFileItem, error) {
	addr := net.JoinHostPort(host, portStr(port))
	conn, err := net.DialTimeout("tcp", addr, 10*time.Second)
	if err != nil {
		return nil, err
	}
	defer conn.Close()
	d := &smb2.Dialer{
		Initiator: &smb2.NTLMInitiator{
			User:     username,
			Password: password,
		},
	}
	s, err := d.Dial(conn)
	if err != nil {
		return nil, err
	}
	defer s.Logoff()
	fs, err := s.Mount(sharePath)
	if err != nil {
		return nil, err
	}
	defer fs.Umount()
	if path == "" {
		path = "."
	}
	entries, err := fs.ReadDir(path)
	if err != nil {
		return nil, err
	}
	out := make([]SmbFileItem, 0, len(entries))
	for _, e := range entries {
		name := e.Name()
		if strings.HasPrefix(name, ".") {
			continue
		}
		fullPath := path
		if fullPath != "" && fullPath != "." {
			fullPath = fullPath + "/" + name
		} else {
			fullPath = name
		}
		item := SmbFileItem{
			ID:         uuid.New().String(),
			Name:       name,
			Path:       fullPath,
			URI:        "smb://" + host + "/" + sharePath + "/" + fullPath,
			SourceType: "SMB",
			ServerID:   serverID,
		}
		if e.IsDir() {
			item.Type = "FOLDER"
		} else {
			item.Type = mediaTypeFromName(name)
			item.Size = e.Size()
			item.LastModified = e.ModTime().UnixMilli()
		}
		out = append(out, item)
	}
	return out, nil
}

func mediaTypeFromName(name string) string {
	ext := ""
	if i := strings.LastIndex(name, "."); i >= 0 {
		ext = strings.ToLower(name[i+1:])
	}
	switch ext {
	case "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v", "3gp", "ts":
		return "VIDEO"
	case "jpg", "jpeg", "png", "gif", "webp":
		return "IMAGE"
	case "mp3", "aac", "flac", "wav", "ogg", "m4a":
		return "AUDIO"
	}
	return "UNKNOWN"
}

func (c *SmbClient) ReadFileRange(ctx context.Context, host string, port int, username, password, sharePath, path string, offset, length int64) ([]byte, error) {
	if length <= 0 {
		return []byte{}, nil
	}
	addr := net.JoinHostPort(host, portStr(port))
	conn, err := net.DialTimeout("tcp", addr, 10*time.Second)
	if err != nil {
		return nil, err
	}
	defer conn.Close()
	d := &smb2.Dialer{
		Initiator: &smb2.NTLMInitiator{
			User:     username,
			Password: password,
		},
	}
	s, err := d.Dial(conn)
	if err != nil {
		return nil, err
	}
	defer s.Logoff()
	fs, err := s.Mount(sharePath)
	if err != nil {
		return nil, err
	}
	defer fs.Umount()
	if path == "" {
		path = "."
	}
	f, err := fs.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	buf := make([]byte, length)
	n, err := f.ReadAt(buf, offset)
	if err != nil && err != io.EOF {
		return nil, err
	}
	return buf[:n], nil
}

func (c *SmbClient) CloseAll() {}
