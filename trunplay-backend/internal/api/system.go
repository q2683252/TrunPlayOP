package api

import (
	"net/http"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/trunplay/trunplay-backend/internal/db"
)

func registerSystem(r *gin.RouterGroup) {
	g := r.Group("/system")
	g.GET("/status", systemStatus)
	g.GET("/health", systemHealth)
	g.GET("/config", systemConfig)
}

func systemStatus(c *gin.Context) {
	dbSize := int64(0)
	if fi, err := os.Stat(db.DBPath); err == nil {
		dbSize = fi.Size()
	}
	info := getPlayback(c).GetPlaybackInfo()
	localIP := getMediaServer(c).GetLocalIP()
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"version": "1.0.0", "uptime": time.Now().Unix(), "db_path": db.DBPath, "db_size": dbSize, "playback_status": string(info.Status), "local_ip": localIP, "active_plans": 0, "total_devices": 0})
		return
	}
	defer tx.Rollback()
	plans, _ := db.GetActivePlans(tx)
	devices, _ := db.GetDevices(tx)
	activePlans, totalDevices := 0, 0
	if plans != nil {
		activePlans = len(plans)
	}
	if devices != nil {
		totalDevices = len(devices)
	}
	c.JSON(http.StatusOK, gin.H{
		"version":         "1.0.0",
		"uptime":          time.Now().Unix(),
		"db_path":         db.DBPath,
		"db_size":         dbSize,
		"playback_status": string(info.Status),
		"local_ip":        localIP,
		"active_plans":    activePlans,
		"total_devices":   totalDevices,
	})
}

func systemHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func systemConfig(c *gin.Context) {
	cfg := getConfig(c)
	c.JSON(http.StatusOK, gin.H{
		"api_port":          cfg.APIPort,
		"media_port":        cfg.MediaPort,
		"db_path":           cfg.DBPath,
		"local_media_paths": cfg.LocalMediaPaths,
		"log_level":         cfg.LogLevel,
	})
}
