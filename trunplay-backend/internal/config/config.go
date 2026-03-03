package config

import (
	"encoding/json"
	"os"
	"strconv"
)

const DefaultConfigPath = "/etc/trunplay/config.json"

type Config struct {
	APIPort           int      `json:"api_port"`
	MediaPort         int      `json:"media_port"`
	DBPath            string   `json:"db_path"`
	LocalMediaPaths   []string `json:"local_media_paths"`
	LogLevel          string   `json:"log_level"`
	AllowedOrigins    []string `json:"allowed_origins"`
	SSDPMulticastAddr string   `json:"ssdp_multicast_addr"`
	SSDPPort          int      `json:"ssdp_port"`
	CrontabFile       string   `json:"crontab_file"`
	TriggerScript     string   `json:"trigger_script"`
	MediaChunkSize    int      `json:"media_chunk_size"`
}

var defaultConfig = Config{
	APIPort:           8088,
	MediaPort:         8089,
	DBPath:            "/etc/trunplay/trunplay.db",
	LocalMediaPaths:   []string{"/mnt", "/tmp"},
	LogLevel:          "INFO",
	AllowedOrigins:    []string{"http://localhost", "http://127.0.0.1"},
	SSDPMulticastAddr: "239.255.255.250",
	SSDPPort:          1900,
	CrontabFile:       "/etc/crontabs/root",
	TriggerScript:     "/usr/bin/trunplay-trigger",
	MediaChunkSize:    1048576,
}

func Load() *Config {
	c := defaultConfig
	path := os.Getenv("TRUNPLAY_CONFIG_PATH")
	if path == "" {
		path = DefaultConfigPath
	}
	data, err := os.ReadFile(path)
	if err == nil {
		_ = json.Unmarshal(data, &c)
	}
	if v := os.Getenv("TRUNPLAY_API_PORT"); v != "" {
		if p, err := strconv.Atoi(v); err == nil {
			c.APIPort = p
		}
	}
	if v := os.Getenv("TRUNPLAY_MEDIA_PORT"); v != "" {
		if p, err := strconv.Atoi(v); err == nil {
			c.MediaPort = p
		}
	}
	if v := os.Getenv("TRUNPLAY_DB_PATH"); v != "" {
		c.DBPath = v
	}
	if v := os.Getenv("TRUNPLAY_LOG_LEVEL"); v != "" {
		c.LogLevel = v
	}
	if v := os.Getenv("TRUNPLAY_CRONTAB_FILE"); v != "" {
		c.CrontabFile = v
	}
	return &c
}
