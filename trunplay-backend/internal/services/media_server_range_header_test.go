package services

import (
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
)

func prepareLocalStreamFixture(t *testing.T) (*MediaServer, string, string, int) {
	t.Helper()
	dir := t.TempDir()
	name := "sample.mp4"
	path := filepath.Join(dir, name)
	content := []byte("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
	if err := os.WriteFile(path, content, 0o644); err != nil {
		t.Fatalf("write temp media: %v", err)
	}
	srv := NewMediaServer(8089, nil, nil, 0)
	mediaID, err := srv.RegisterLocalMedia(path, name)
	if err != nil {
		t.Fatalf("register media: %v", err)
	}
	return srv, mediaID, name, len(content)
}

func TestServeHTTP_IgnoresUnsupportedRangeUnit(t *testing.T) {
	srv, mediaID, name, contentLen := prepareLocalStreamFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/stream/"+mediaID+"/"+name, nil)
	req.Header.Set("Range", "items=0-10")
	rec := httptest.NewRecorder()

	srv.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d, want=%d", rec.Code, http.StatusOK)
	}
	if got := rec.Header().Get("Content-Range"); got != "" {
		t.Fatalf("Content-Range=%q, want empty", got)
	}
	if got := rec.Body.Len(); got != contentLen {
		t.Fatalf("body length=%d, want=%d", got, contentLen)
	}
}

func TestServeHTTP_IgnoresMalformedBytesRange(t *testing.T) {
	srv, mediaID, name, contentLen := prepareLocalStreamFixture(t)
	req := httptest.NewRequest(http.MethodGet, "/stream/"+mediaID+"/"+name, nil)
	req.Header.Set("Range", "bytes=abc")
	rec := httptest.NewRecorder()

	srv.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status=%d, want=%d", rec.Code, http.StatusOK)
	}
	if got := rec.Header().Get("Content-Range"); got != "" {
		t.Fatalf("Content-Range=%q, want empty", got)
	}
	if got := rec.Body.Len(); got != contentLen {
		t.Fatalf("body length=%d, want=%d", got, contentLen)
	}
}
