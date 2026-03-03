package config

import (
	"os"
	"testing"
)

func TestLoad_Defaults(t *testing.T) {
	os.Unsetenv("TRUNPLAY_API_PORT")
	os.Unsetenv("TRUNPLAY_DB_PATH")
	cfg := Load()
	if cfg.APIPort != 8088 {
		t.Errorf("APIPort: got %d", cfg.APIPort)
	}
	if cfg.MediaPort != 8089 {
		t.Errorf("MediaPort: got %d", cfg.MediaPort)
	}
	if cfg.DBPath != "/etc/trunplay/trunplay.db" {
		t.Errorf("DBPath: got %s", cfg.DBPath)
	}
}

func TestLoad_EnvOverride(t *testing.T) {
	os.Setenv("TRUNPLAY_API_PORT", "9000")
	os.Setenv("TRUNPLAY_MEDIA_PORT", "9001")
	os.Setenv("TRUNPLAY_DB_PATH", "/tmp/db")
	defer func() {
		os.Unsetenv("TRUNPLAY_API_PORT")
		os.Unsetenv("TRUNPLAY_MEDIA_PORT")
		os.Unsetenv("TRUNPLAY_DB_PATH")
	}()
	cfg := Load()
	if cfg.APIPort != 9000 {
		t.Errorf("APIPort: got %d", cfg.APIPort)
	}
	if cfg.MediaPort != 9001 {
		t.Errorf("MediaPort: got %d", cfg.MediaPort)
	}
	if cfg.DBPath != "/tmp/db" {
		t.Errorf("DBPath: got %s", cfg.DBPath)
	}
}
