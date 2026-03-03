package services

import (
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"github.com/google/uuid"
)

type MediaInfo struct {
	MediaID       string
	FilePath      string
	FileName      string
	MimeType      string
	FileSize      int64
	IsSMB         bool
	SmbHost       string
	SmbPort       int
	SmbUsername   string
	SmbPassword   string
	SmbServerName string
}

type MediaServer struct {
	mu       sync.RWMutex
	port     int
	registry map[string]*MediaInfo
	smb      *SmbClient
}

func NewMediaServer(port int, smb *SmbClient) *MediaServer {
	return &MediaServer{port: port, registry: make(map[string]*MediaInfo), smb: smb}
}

func (s *MediaServer) Port() int { return s.port }

func (s *MediaServer) GetLocalIP() string {
	conn, err := net.Dial("udp", "8.8.8.8:80")
	if err != nil {
		// Fallback: first non-loopback IPv4 from interfaces
		ifaces, err := net.Interfaces()
		if err != nil {
			return "127.0.0.1"
		}
		for _, iface := range ifaces {
			if iface.Flags&net.FlagUp == 0 || iface.Flags&net.FlagLoopback != 0 {
				continue
			}
			addrs, _ := iface.Addrs()
			for _, a := range addrs {
				if ipnet, ok := a.(*net.IPNet); ok && !ipnet.IP.IsLoopback() && ipnet.IP.To4() != nil {
					return ipnet.IP.String()
				}
			}
		}
		return "127.0.0.1"
	}
	defer conn.Close()
	addr := conn.LocalAddr().(*net.UDPAddr)
	return addr.IP.String()
}

func mimeFromFilename(name string) string {
	ext := strings.ToLower(filepath.Ext(name))
	switch ext {
	case ".mp4", ".m4v":
		return "video/mp4"
	case ".mkv":
		return "video/x-matroska"
	case ".avi":
		return "video/x-msvideo"
	case ".mov":
		return "video/quicktime"
	case ".wmv":
		return "video/x-ms-wmv"
	case ".webm":
		return "video/webm"
	case ".mp3":
		return "audio/mpeg"
	case ".m4a", ".aac":
		return "audio/mp4"
	case ".flac":
		return "audio/flac"
	case ".wav":
		return "audio/wav"
	case ".ogg":
		return "audio/ogg"
	case ".jpg", ".jpeg":
		return "image/jpeg"
	case ".png":
		return "image/png"
	case ".gif":
		return "image/gif"
	case ".webp":
		return "image/webp"
	}
	return "application/octet-stream"
}

func (s *MediaServer) RegisterLocalMedia(filePath, fileName string) (string, error) {
	mediaID := uuid.New().String()
	info := &MediaInfo{
		MediaID:  mediaID,
		FilePath: filePath,
		FileName: fileName,
		MimeType: mimeFromFilename(fileName),
		IsSMB:    false,
	}
	if fi, err := os.Stat(filePath); err == nil {
		info.FileSize = fi.Size()
	}
	s.mu.Lock()
	s.registry[mediaID] = info
	s.mu.Unlock()
	return mediaID, nil
}

func (s *MediaServer) RegisterSmbMedia(smbPath, fileName string, fileSize int64, host string, port int, username, password, serverName string) (string, error) {
	mediaID := uuid.New().String()
	info := &MediaInfo{
		MediaID:       mediaID,
		FilePath:      smbPath,
		FileName:      fileName,
		MimeType:      mimeFromFilename(fileName),
		FileSize:      fileSize,
		IsSMB:         true,
		SmbHost:       host,
		SmbPort:       port,
		SmbUsername:   username,
		SmbPassword:   password,
		SmbServerName: serverName,
	}
	s.mu.Lock()
	s.registry[mediaID] = info
	s.mu.Unlock()
	return mediaID, nil
}

func (s *MediaServer) UnregisterMedia(mediaID string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.registry, mediaID)
}

func (s *MediaServer) GetMediaInfo(mediaID string) *MediaInfo {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.registry[mediaID]
}

const streamPrefix = "/stream/"

func (s *MediaServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		http.Error(w, "Method Not Allowed", http.StatusMethodNotAllowed)
		return
	}
	path := r.URL.Path
	if !strings.HasPrefix(path, streamPrefix) {
		http.NotFound(w, r)
		return
	}
	rest := strings.TrimPrefix(path, streamPrefix)
	parts := strings.SplitN(rest, "/", 2)
	if len(parts) < 2 {
		http.NotFound(w, r)
		return
	}
	mediaID := parts[0]
	filename := parts[1]
	if mediaID == "" || filename == "" {
		http.NotFound(w, r)
		return
	}
	info := s.GetMediaInfo(mediaID)
	if info == nil {
		http.NotFound(w, r)
		return
	}
	size := info.FileSize
	if size < 0 {
		size = 0
	}
	var start, end int64 = 0, size - 1
	if size == 0 {
		end = 0
	}
	if ra := r.Header.Get("Range"); ra != "" {
		if strings.HasPrefix(ra, "bytes=") {
			ra = strings.TrimPrefix(ra, "bytes=")
			ra = strings.TrimSpace(ra)
			if idx := strings.Index(ra, "-"); idx >= 0 {
				startStr := strings.TrimSpace(ra[:idx])
				endStr := strings.TrimSpace(ra[idx+1:])
				if startStr != "" {
					if v, err := strconv.ParseInt(startStr, 10, 64); err == nil && v >= 0 {
						start = v
					}
				}
				if endStr != "" {
					if v, err := strconv.ParseInt(endStr, 10, 64); err == nil && v >= 0 {
						end = v
					}
				} else {
					// bytes=-N means last N bytes
					if v, err := strconv.ParseInt(endStr, 10, 64); err == nil && v > 0 {
						start = size - v
						if start < 0 {
							start = 0
						}
						end = size - 1
					}
				}
			}
		}
		if start > end || start >= size {
			w.Header().Set("Content-Range", "bytes */"+strconv.FormatInt(size, 10))
			http.Error(w, "Requested Range Not Satisfiable", http.StatusRequestedRangeNotSatisfiable)
			return
		}
		if end >= size {
			end = size - 1
		}
	}
	contentLength := end - start + 1
	w.Header().Set("Accept-Ranges", "bytes")
	w.Header().Set("Content-Type", info.MimeType)
	if start != 0 || end != size-1 || size == 0 {
		w.Header().Set("Content-Range", "bytes "+strconv.FormatInt(start, 10)+"-"+strconv.FormatInt(end, 10)+"/"+strconv.FormatInt(size, 10))
		w.WriteHeader(http.StatusPartialContent)
	}
	w.Header().Set("Content-Length", strconv.FormatInt(contentLength, 10))
	if r.Method == http.MethodHead {
		return
	}
	if info.IsSMB {
		if s.smb == nil {
			http.Error(w, "SMB client not available", http.StatusInternalServerError)
			return
		}
		data, err := s.smb.ReadFileRange(r.Context(), info.SmbHost, info.SmbPort, info.SmbUsername, info.SmbPassword, info.SmbServerName, info.FilePath, start, contentLength)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		_, _ = w.Write(data)
		return
	}
	f, err := os.Open(info.FilePath)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer f.Close()
	if _, err := f.Seek(start, io.SeekStart); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	_, _ = io.CopyN(w, f, contentLength)
}

func (s *MediaServer) Handler() http.Handler {
	return http.HandlerFunc(s.ServeHTTP)
}
