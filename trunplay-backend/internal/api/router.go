package api

import (
	"database/sql"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/trunplay/trunplay-backend/internal/config"
	"github.com/trunplay/trunplay-backend/internal/services"
)

func NewRouter(db *sql.DB, cfg *config.Config, dlna *services.DlnaManager, smb *services.SmbClient, sched *services.Scheduler, playback *services.PlaybackService, mediaServer *services.MediaServer) *gin.Engine {
	r := gin.Default()
	r.Use(func(c *gin.Context) {
		c.Set("db", db)
		c.Set("config", cfg)
		c.Set("dlna", dlna)
		c.Set("smb", smb)
		c.Set("scheduler", sched)
		c.Set("playback", playback)
		c.Set("media_server", mediaServer)
		c.Next()
	})
	r.Use(corsMiddleware(cfg))

	r.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"name": "TrunPlay API", "version": "1.0.0", "status": "running"})
	})
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	v1 := r.Group("/api/v1")
	{
		registerPlans(v1)
		registerDevices(v1)
		registerSmb(v1)
		registerMedia(v1)
		registerPlayback(v1)
		registerStudy(v1)
		registerHistory(v1)
		registerSystem(v1)
	}
	return r
}

func corsMiddleware(cfg *config.Config) gin.HandlerFunc {
	origins := cfg.AllowedOrigins
	if len(origins) == 0 {
		origins = []string{"http://localhost", "http://127.0.0.1"}
	}
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", origins[0])
		if len(origins) > 1 {
			for _, o := range origins[1:] {
				c.Writer.Header().Add("Access-Control-Allow-Origin", o)
			}
		}
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "*")
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		c.Next()
	}
}

func getDB(c *gin.Context) *sql.DB {
	v, _ := c.Get("db")
	return v.(*sql.DB)
}
func getConfig(c *gin.Context) *config.Config {
	v, _ := c.Get("config")
	return v.(*config.Config)
}
func getDlna(c *gin.Context) *services.DlnaManager {
	v, _ := c.Get("dlna")
	return v.(*services.DlnaManager)
}
func getSmb(c *gin.Context) *services.SmbClient {
	v, _ := c.Get("smb")
	return v.(*services.SmbClient)
}
func getScheduler(c *gin.Context) *services.Scheduler {
	v, _ := c.Get("scheduler")
	return v.(*services.Scheduler)
}
func getPlayback(c *gin.Context) *services.PlaybackService {
	v, _ := c.Get("playback")
	return v.(*services.PlaybackService)
}
func getMediaServer(c *gin.Context) *services.MediaServer {
	v, _ := c.Get("media_server")
	return v.(*services.MediaServer)
}
