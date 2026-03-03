package api

import (
	"database/sql"
	"net/http"
	"net/url"
	"strings"

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
		origin := c.GetHeader("Origin")
		if origin != "" && isOriginAllowed(origin, origins) {
			// Echo back a single matching origin so browsers accept credentialed CORS.
			c.Writer.Header().Set("Access-Control-Allow-Origin", origin)
			c.Writer.Header().Set("Vary", "Origin")
		} else if len(origins) > 0 {
			// Non-browser clients (no Origin header) keep the legacy default.
			c.Writer.Header().Set("Access-Control-Allow-Origin", origins[0])
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

func isOriginAllowed(origin string, allowed []string) bool {
	for _, item := range allowed {
		if originMatchesAllowRule(origin, item) {
			return true
		}
	}
	return false
}

func originMatchesAllowRule(origin, allowRule string) bool {
	origin = strings.TrimSpace(origin)
	allowRule = strings.TrimSpace(allowRule)
	if origin == "" || allowRule == "" {
		return false
	}
	if strings.EqualFold(origin, allowRule) {
		return true
	}

	originURL, err1 := url.Parse(origin)
	allowURL, err2 := url.Parse(allowRule)
	if err1 != nil || err2 != nil || originURL.Scheme == "" || allowURL.Scheme == "" {
		return false
	}
	if !strings.EqualFold(originURL.Scheme, allowURL.Scheme) {
		return false
	}
	if !strings.EqualFold(originURL.Hostname(), allowURL.Hostname()) {
		return false
	}
	// Rule without explicit port accepts any port on the same host.
	if allowURL.Port() == "" {
		return true
	}
	return originURL.Port() == allowURL.Port()
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
