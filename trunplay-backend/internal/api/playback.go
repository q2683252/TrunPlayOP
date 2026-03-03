package api

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/trunplay/trunplay-backend/internal/db"
)

func registerPlayback(r *gin.RouterGroup) {
	g := r.Group("/playback")
	g.GET("/status", playbackStatus)
	g.POST("/play", playbackPlay)
	g.POST("/pause", playbackPause)
	g.POST("/resume", playbackResume)
	g.POST("/stop", playbackStop)
	g.POST("/seek", playbackSeek)
	g.POST("/volume", playbackSetVolume)
	g.GET("/volume", playbackGetVolume)
	g.GET("/position", playbackGetPosition)
}

func playbackStatus(c *gin.Context) {
	info := getPlayback(c).GetPlaybackInfo()
	c.JSON(http.StatusOK, gin.H{
		"status":      string(info.Status),
		"device_id":   info.DeviceID,
		"device_name": info.DeviceName,
		"plan_id":     info.PlanID,
		"plan_title":  info.PlanTitle,
		"media_url":   info.MediaURL,
		"media_name":  info.MediaName,
		"position":    info.Position,
		"duration":    info.Duration,
		"volume":      info.Volume,
	})
}

func playbackPlay(c *gin.Context) {
	var body struct {
		PlanID        string `json:"plan_id"`
		StartPosition int    `json:"start_position"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		BadRequest(c, err.Error())
		return
	}
	database := getDB(c)
	tx, err := database.Begin()
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	defer tx.Rollback()
	plan, err := db.GetPlan(tx, body.PlanID)
	if err != nil || plan == nil {
		NotFound(c, "Plan not found")
		return
	}
	_ = tx.Commit()
	tx2, _ := database.Begin()
	success, err := getPlayback(c).StartPlayback(c.Request.Context(), tx2, plan, "MANUAL", body.StartPosition)
	if err != nil {
		tx2.Rollback()
		ServerError(c, err.Error())
		return
	}
	_ = tx2.Commit()
	if !success {
		ServerError(c, "Failed to start playback")
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Playback started"})
}

func playbackPause(c *gin.Context) {
	success, err := getPlayback(c).Pause(c.Request.Context())
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !success {
		BadRequest(c, "Cannot pause")
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Playback paused"})
}

func playbackResume(c *gin.Context) {
	success, err := getPlayback(c).Resume(c.Request.Context())
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !success {
		BadRequest(c, "Cannot resume")
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Playback resumed"})
}

func playbackStop(c *gin.Context) {
	database := getDB(c)
	tx, _ := database.Begin()
	_ = getPlayback(c).StopPlayback(c.Request.Context(), tx)
	tx.Commit()
	c.JSON(http.StatusOK, gin.H{"message": "Playback stopped"})
}

func playbackSeek(c *gin.Context) {
	var body struct {
		Position int `json:"position"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		BadRequest(c, err.Error())
		return
	}
	success, err := getPlayback(c).Seek(c.Request.Context(), body.Position)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !success {
		BadRequest(c, "Seek failed")
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Seeked", "position": body.Position})
}

func playbackSetVolume(c *gin.Context) {
	var body struct {
		Level int `json:"level"`
	}
	if err := c.ShouldBindJSON(&body); err != nil {
		BadRequest(c, err.Error())
		return
	}
	if body.Level < 0 || body.Level > 100 {
		BadRequest(c, "level must be 0-100")
		return
	}
	success, err := getPlayback(c).SetVolume(c.Request.Context(), body.Level)
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	if !success {
		BadRequest(c, "Set volume failed")
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Volume set", "level": body.Level})
}

func playbackGetVolume(c *gin.Context) {
	v, err := getPlayback(c).GetVolume(c.Request.Context())
	if err != nil {
		ServerError(c, err.Error())
		return
	}
	c.JSON(http.StatusOK, gin.H{"volume": v})
}

func playbackGetPosition(c *gin.Context) {
	pos, dur, err := getPlayback(c).GetPositionInfo(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"position": 0, "duration": 0})
		return
	}
	c.JSON(http.StatusOK, gin.H{"position": pos, "duration": dur})
}
